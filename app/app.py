import sys, os

# Must be set before any matplotlib/pyplot import
os.environ.setdefault("MPLBACKEND", "Agg")
# Prevent rasterio/PROJ from making network requests on startup
os.environ["PROJ_NETWORK"] = "OFF"

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

print("AgroSolar: loading libraries…", flush=True)

import matplotlib
matplotlib.use("Agg")

from flask import Flask, render_template, jsonify, request
import plotly.graph_objects as go
import plotly.utils
import json

from src.data_analysis import (
    load_solar_data, LAYERS,
    get_production_by_state, get_crop_detail_by_state,
    get_total_by_category, LANDUSE_CATEGORIES, CATEGORY_DETAIL_FILE,
)

print("AgroSolar: ready — open http://localhost:8080", flush=True)

app = Flask(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

LAYER_LABELS = {
    "GHI":   "Global Horizontal Irradiance (kWh/m²/day)",
    "PVOUT": "PV Power Output (kWh/kWp/day)",
    "DNI":   "Direct Normal Irradiance (kWh/m²/day)",
    "TEMP":  "Temperature (°C)",
}

MAP_CATEGORIES = [c for c in LANDUSE_CATEGORIES if c not in (
    "Forest", "Forestry area", "Unproductive areas",
    "Grassland intensive", "Grassland extensive",
)]

_solar_df = None
def get_solar_df():
    global _solar_df
    if _solar_df is None:
        _solar_df = load_solar_data(reduced_data=True)
    return _solar_df


# ── Pages ──────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/calculator")
def calculator():
    return render_template("calculator.html")

@app.route("/map")
def map_page():
    return render_template("map_page.html",
                           layers=LAYERS,
                           layer_labels=LAYER_LABELS,
                           categories=MAP_CATEGORIES)

@app.route("/sources")
def sources():
    return render_template("sources.html")


# ── API helpers ────────────────────────────────────────────────────────────────

def _plotly_theme():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "color": "#374151"},
        margin={"t": 50, "r": 10, "l": 10, "b": 100},
    )

def _fig_json(fig):
    return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))


# ── API: Solar map ─────────────────────────────────────────────────────────────

@app.route("/api/solar/<layer>")
def api_solar(layer):
    if layer not in LAYERS:
        return jsonify({"error": "Invalid layer"}), 400
    df = get_solar_df()
    scale = "RdBu_r" if layer == "TEMP" else "YlOrRd"
    fig = go.Figure(go.Scattermap(
        lat=df["lat"], lon=df["lon"],
        mode="markers",
        marker=dict(
            color=df[layer],
            colorscale=scale,
            size=4,
            opacity=0.5,
            colorbar=dict(title=LAYER_LABELS[layer]),
        ),
        hovertemplate=f"{LAYER_LABELS[layer]}: %{{marker.color:.2f}}<extra></extra>",
    ))
    fig.update_layout(
        map_style="open-street-map",
        map_center={"lat": 47.5, "lon": 13.5},
        map_zoom=6,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return _fig_json(fig)


# ── API: Land use ──────────────────────────────────────────────────────────────

def _bar_fig(x, y, title, tickangle=-30):
    colors = [f"rgba(22,{100 + int(v/max(y)*120) if max(y) > 0 else 100},34,0.8)" for v in y]
    fig = go.Figure(go.Bar(
        x=x, y=y,
        marker_color=colors,
        hovertemplate="%{x}: %{y:,.0f} ha<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        xaxis=dict(tickangle=tickangle, title=""),
        yaxis=dict(title="Area (ha)"),
        **_plotly_theme(),
    )
    return fig

@app.route("/api/landuse/<category>")
def api_landuse(category):
    if category not in LANDUSE_CATEGORIES:
        return jsonify({"error": "Invalid category"}), 400
    df = get_production_by_state(category).sort_values("area_ha", ascending=False)
    fig = _bar_fig(df["state"].tolist(), df["area_ha"].tolist(),
                   f"{category} — Area by State")
    return _fig_json(fig)

@app.route("/api/landuse/<category>/<state>")
def api_landuse_detail(category, state):
    df = get_crop_detail_by_state(category, state)
    if df.empty:
        return jsonify({"error": "No detail data"}), 404
    df = df.sort_values("area_ha", ascending=False)
    fig = _bar_fig(df["crop"].tolist(), df["area_ha"].tolist(),
                   f"{category} breakdown — {state}", tickangle=-35)
    return _fig_json(fig)

@app.route("/api/landuse-overview")
def api_landuse_overview():
    df = get_total_by_category()
    df = df[~df["category"].isin([
        "Forest", "Forestry area", "Unproductive areas",
        "Grassland intensive", "Grassland extensive",
    ])].sort_values("area_ha", ascending=False)
    fig = _bar_fig(df["category"].tolist(), df["area_ha"].tolist(),
                   "Total Agricultural Land Use — Austria")
    return _fig_json(fig)


# ── API: GHI lookup ────────────────────────────────────────────────────────────

@app.route("/api/ghi-at-location")
def api_ghi_at_location():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400

    import rasterio
    solar_dir = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..", "References", "datasets", "Solar"))

    results = {}
    for name in ("GHI", "PVOUT"):
        try:
            with rasterio.open(os.path.join(solar_dir, f"{name}.tif")) as src:
                row, col = src.index(lon, lat)
                if row < 0 or col < 0 or row >= src.height or col >= src.width:
                    results[name.lower()] = None
                    continue
                val = float(src.read(1)[row, col])
                nodata = src.nodata
                results[name.lower()] = None if (nodata is not None and val == nodata) else round(val, 3)
        except Exception:
            results[name.lower()] = None

    return jsonify({**results, "lat": lat, "lon": lon})


# ── API: Calculate ─────────────────────────────────────────────────────────────

CROP_PARAMS = {
    "lettuce_herbs": {"label": "Lettuce / Herbs",     "shade": "High",        "delta":  0.05, "margin": 3500, "hail": "medium"},
    "potatoes":      {"label": "Potatoes",             "shade": "Medium-High", "delta":  0.00, "margin": 2200, "hail": "low"},
    "wheat_barley":  {"label": "Wheat / Barley",       "shade": "Medium",      "delta": -0.15, "margin":  800, "hail": "low"},
    "maize":         {"label": "Maize",                "shade": "Low",         "delta": -0.30, "margin":  900, "hail": "medium"},
    "strawberries":  {"label": "Strawberries",         "shade": "Medium",      "delta":  0.05, "margin": 8000, "hail": "high"},
    "apples_fruit":  {"label": "Apples / Tree Fruit",  "shade": "Medium",      "delta":  0.00, "margin": 5000, "hail": "high"},
    "grapes":        {"label": "Grapes / Vines",       "shade": "Medium",      "delta": -0.05, "margin": 4000, "hail": "high"},
    "vegetables":    {"label": "Vegetables",           "shade": "Medium-High", "delta": -0.05, "margin": 3000, "hail": "medium"},
}
LER_BY_SHADE     = {"High": 1.60, "Medium-High": 1.45, "Medium": 1.35, "Low": 1.20}
HAIL_PER_HA      = {"high": 400, "medium": 150, "low": 30}
RISK_FLOOR_PCT   = {"high": 51,  "medium": 25,  "low": 10}

@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    data     = request.get_json()
    area_ha  = max(float(data.get("area_ha", 10)), 0.1)
    crop_key = data.get("crop", "wheat_barley")
    ghi      = float(data.get("ghi", 3.5))
    irrigates= bool(data.get("irrigates", False))
    tariff   = float(data.get("tariff", 0.08))

    cp = CROP_PARAMS.get(crop_key, CROP_PARAMS["wheat_barley"])

    coverage        = 0.15
    pv_yield_mwh    = ghi * 365 * area_ha * 10_000 * coverage * 0.20 * 0.80 / 1000
    pv_capacity_kwp = area_ha * 350
    pv_revenue      = pv_yield_mwh * 1000 * tariff

    epsilon     = 0.05
    base_margin = cp["margin"] * area_ha
    av_margin   = cp["margin"] * area_ha * (1 - epsilon) * (1 + cp["delta"])
    delta_agri  = av_margin - base_margin

    ler            = LER_BY_SHADE[cp["shade"]]
    irr_reduction  = min(coverage * 1.8, 0.30)
    water_saved_m3 = area_ha * 3500 * irr_reduction if irrigates else 0
    water_value    = water_saved_m3 * 0.50
    hail_value     = HAIL_PER_HA[cp["hail"]] * area_ha
    risk_pct       = RISK_FLOOR_PCT[cp["hail"]]

    capex    = pv_capacity_kwp * 650
    disc, yrs = 0.05, 25
    crf      = disc * (1 + disc)**yrs / ((1 + disc)**yrs - 1)
    lcoe_ct  = (capex * crf / (pv_yield_mwh * 1000)) * 100 if pv_yield_mwh > 0 else 0
    payback  = capex / pv_revenue if pv_revenue > 0 else 999

    score = int(min(ghi / 5.0 * 40, 40)
                + (1 + cp["delta"]) * 30
                + max(min((1 - lcoe_ct / 15) * 30, 30), 0))
    label = "High" if score >= 70 else "Medium" if score >= 45 else "Low"
    color = "green" if score >= 70 else "amber" if score >= 45 else "red"

    factors = [0.35,0.50,0.72,0.95,1.15,1.25,1.20,1.10,0.88,0.62,0.38,0.30]
    monthly = [round(pv_yield_mwh * f / sum(factors) * 12, 2) for f in factors]

    return jsonify({
        "score": score, "label": label, "color": color,
        "pv_capacity_kwp": round(pv_capacity_kwp),
        "pv_yield_mwh": round(pv_yield_mwh, 1),
        "pv_revenue": round(pv_revenue),
        "base_margin": round(base_margin),
        "av_margin": round(av_margin),
        "delta_agri": round(delta_agri),
        "yield_delta_pct": int(cp["delta"] * 100),
        "crop_label": cp["label"],
        "shade_tolerance": cp["shade"],
        "ler": ler,
        "water_saved_m3": round(water_saved_m3),
        "water_value": round(water_value),
        "irr_reduction_pct": round(irr_reduction * 100),
        "hail_value": round(hail_value),
        "risk_pct": risk_pct,
        "hail_level": cp["hail"],
        "capex": round(capex),
        "lcoe_ct": round(lcoe_ct, 2),
        "payback": round(payback, 1),
        "total_benefit": round(pv_revenue + delta_agri + water_value + hail_value),
        "area_ha": area_ha,
        "ghi_daily": round(ghi, 2),
        "monthly_mwh": monthly,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False, use_reloader=False)
