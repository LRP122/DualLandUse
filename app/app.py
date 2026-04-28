import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
from src.data_analysis import load_solar_data, LAYERS, get_production_by_state, get_crop_detail_by_state, get_total_by_category, LANDUSE_CATEGORIES, CATEGORY_DETAIL_FILE

app = dash.Dash(__name__)

_df_totals = get_total_by_category()
_df_totals = _df_totals[~_df_totals["category"].isin(["Forest", "Forestry area", "Unproductive areas","Grassland intensive","Grassland extensive"])]
_fig_totals = px.bar(
    _df_totals.sort_values("area_ha", ascending=False),
    x="category", y="area_ha",
    labels={"category": "Land Use Type", "area_ha": "Total Area (ha)"},
    title="Total Land Use by Category — Austria",
)
_fig_totals.update_layout(xaxis_tickangle=-30)

LAYER_LABELS = {
    "GHI":   "Global Horizontal Irradiance (kWh/m²/day)",
    "PVOUT": "PV Power Output (kWh/kWp/day)",
    "DNI":   "Direct Normal Irradiance (kWh/m²/day)",
    "TEMP":  "Temperature (°C)",
}

app.layout = html.Div([
    html.H1("Agrivoltaics Potential — Austria", style={"textAlign": "center"}),

    # --- Solar map section ---
    dcc.Dropdown(
        id="layer-selector",
        options=[{"label": LAYER_LABELS[l], "value": l} for l in LAYERS],
        value="GHI",
        clearable=False,
        style={"width": "50%", "margin": "0 auto 16px"}
    ),
    dcc.Graph(id="map", style={"height": "80vh"}),

    # --- Land use bar chart section ---
    html.H2("Land Use by State", style={"textAlign": "center", "marginTop": "32px"}),
    dcc.Dropdown(
        id="category-selector",
        options=[{"label": c, "value": c} for c in LANDUSE_CATEGORIES],
        value="Cereals",
        clearable=False,
        style={"width": "50%", "margin": "0 auto 16px"}
    ),
    dcc.Graph(id="bar-chart"),

    # --- Drill-down: shown after clicking a bar ---
    dcc.Graph(id="detail-chart"),

    # --- Total land use overview ---
    html.H2("Total Land Use by Category — Austria", style={"textAlign": "center", "marginTop": "32px"}),
    dcc.Graph(id="total-category-chart", figure=_fig_totals),
])

@app.callback(Output("map", "figure"), Input("layer-selector", "value"))
def update_map(layer):
    df_solar = load_solar_data(reduced_data=True)
    fig = px.scatter_map(
        df_solar, lat="lat", lon="lon", color=layer,
        labels={layer: LAYER_LABELS[layer]},
        center={"lat": 47.5, "lon": 13.5},
        zoom=6, map_style="open-street-map",
        opacity=0.4,
    )
    fig.update_traces(marker={"size": 4})
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig

@app.callback(Output("bar-chart", "figure"), Input("category-selector", "value"))
def update_bar_chart(category):
    df_land = get_production_by_state(category)
    fig = px.bar(
        df_land, x="state", y="area_ha",
        labels={"state": "State", "area_ha": "Area (ha)"},
        title=f"{category} — Area by State"
    )
    return fig

@app.callback(
    Output("detail-chart", "figure"),
    Input("bar-chart", "clickData"),
    Input("category-selector", "value"),
)
def update_detail_chart(click_data, category):
    # No bar clicked yet, or category has no detail file → empty chart
    if click_data is None or category not in CATEGORY_DETAIL_FILE:
        return {}

    state = click_data["points"][0]["x"]   # the state name from the bar's x-axis
    df_detail = get_crop_detail_by_state(category, state)

    fig = px.bar(
        df_detail, x="crop", y="area_ha",
        labels={"crop": "Crop", "area_ha": "Area (ha)"},
        title=f"{category} breakdown — {state}"
    )
    fig.update_layout(xaxis_tickangle=-30)
    return fig

if __name__ == "__main__":
    app.run(debug=True)
