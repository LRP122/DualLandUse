import sys, os

# Must be set before any matplotlib/pyplot import
os.environ.setdefault("MPLBACKEND", "Agg")
# Prevent rasterio/PROJ from making network requests on startup
os.environ["PROJ_NETWORK"] = "OFF"

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

print("AgriPV: loading libraries…", flush=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot  # noqa: E402 — must follow matplotlib.use()

import base64
from io import BytesIO

import numpy as np
import matplotlib.colors as mcolors
from flask import Flask, render_template, jsonify, request

from src.data_loader import (
    LAYERS, LANDUSE_CATEGORIES, CATEGORY_DETAIL_FILE, SOLAR_DIR,
    get_total_by_category, get_production_by_state, get_crop_detail_by_state,
)
from src.scenario_calculations import calculate_agrivoltaic_scenario

print("AgriPV: ready — open http://localhost:8080", flush=True)

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

_solar_png_cache: dict = {}


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


# ── API: Solar map ─────────────────────────────────────────────────────────────

_LAYER_CMAPS = {"GHI": "YlOrRd", "PVOUT": "YlGn", "DNI": "YlOrRd", "TEMP": "coolwarm"}

@app.route("/api/solar/<layer>")
def api_solar(layer):
    if layer not in LAYERS:
        return jsonify({"error": "Invalid layer"}), 400

    if layer in _solar_png_cache:
        return jsonify(_solar_png_cache[layer])

    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import transform_bounds

    tif = os.path.join(SOLAR_DIR, f"{layer}.tif")
    with rasterio.open(tif) as src:
        scale = 4
        data = src.read(
            1,
            out_shape=(max(src.height // scale, 50), max(src.width // scale, 50)),
            resampling=Resampling.bilinear,
        ).astype(float)
        if src.nodata is not None:
            data[data == src.nodata] = np.nan
        west, south, east, north = transform_bounds(
            src.crs, "EPSG:4326",
            src.bounds.left, src.bounds.bottom,
            src.bounds.right, src.bounds.top,
        )

    vmin, vmax = float(np.nanmin(data)), float(np.nanmax(data))
    cmap = matplotlib.colormaps[_LAYER_CMAPS[layer]]
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    rgba = cmap(norm(np.where(np.isnan(data), 0.0, data)))
    rgba[np.isnan(data), 3] = 0.0  # transparent nodata

    buf = BytesIO()
    matplotlib.pyplot.imsave(buf, rgba, format="png")
    buf.seek(0)

    result = {
        "image": "data:image/png;base64," + base64.b64encode(buf.read()).decode(),
        "bounds": [[south, west], [north, east]],
        "min": round(vmin, 2), "max": round(vmax, 2),
        "label": LAYER_LABELS[layer],
    }
    _solar_png_cache[layer] = result
    return jsonify(result)


# ── API: Land use ──────────────────────────────────────────────────────────────

@app.route("/api/landuse/<category>")
def api_landuse(category):
    if category not in LANDUSE_CATEGORIES:
        return jsonify({"error": "Invalid category"}), 400
    df = get_production_by_state(category).sort_values("area_ha", ascending=False)
    return jsonify({"labels": df["state"].tolist(), "values": df["area_ha"].tolist()})

@app.route("/api/landuse/<category>/<state>")
def api_landuse_detail(category, state):
    df = get_crop_detail_by_state(category, state)
    if df.empty:
        return jsonify({"error": "No detail data"}), 404
    df = df.dropna(subset=["crop", "area_ha"])
    df = df.sort_values("area_ha", ascending=False)
    return jsonify({"labels": df["crop"].tolist(), "values": df["area_ha"].tolist()})

@app.route("/api/landuse-overview")
def api_landuse_overview():
    df = get_total_by_category()
    df = df[~df["category"].isin([
        "Forest", "Forestry area", "Unproductive areas",
        "Grassland intensive", "Grassland extensive",
    ])].sort_values("area_ha", ascending=False)
    return jsonify({"labels": df["category"].tolist(), "values": df["area_ha"].tolist()})


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
        os.path.dirname(os.path.abspath(__file__)), "..", "References", "datasets", "Solar"))

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
        except Exception as e:
            print(f"GHI lookup error [{name}]: {e}", flush=True)
            results[name.lower()] = None

    return jsonify({**results, "lat": lat, "lon": lon})


# ── API: Calculate ─────────────────────────────────────────────────────────────

@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    data = request.get_json()
    result = calculate_agrivoltaic_scenario(
        area_ha=max(float(data.get("area_ha", 10)), 0.1),
        crop_key=data.get("crop", "winter_wheat"),
        ghi=float(data.get("ghi", 0.0)),
        tariff=float(data.get("tariff", 0.08)),
    )
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
