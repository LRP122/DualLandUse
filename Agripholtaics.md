# Agrivoltaics Project

## Motivation

Agrivoltaics is the process of combining agriculture and photovoltaics.
This has a number of advantages over limiting land use to either agriculture or photovoltaics.

- Energy production due to solar panels
- Agricultural production
- Increased land use
- Less irrigation due to less evaporation
- Protection from extreme heat
- Possible IoT base stations to monitor weather, soil, crop quality
- Possible protection from hail

This process is becoming more and more important due to a number of reasons:

- Higher temperatures leading to more evaporation
- More extreme weather events such as hailstorms
- Cheap and reliable solar panels
- High energy demand and prices, leading to opportunities for farmers with high energy need
- Diversification for farms with higher protection from harvest misses

![Agrivoltaics 101](References/images/Agrivoltaics101.png)


## Project: Agrivoltaic Potential Calculator — Web Application

A Flask web application with four pages: a landing page, data maps, the calculator, and a sources page.
It runs in Docker (see [HowToRun.md](HowToRun.md)).

### Data maps (`/map`)

Climatic and agricultural data for Austria:

- **Solar resource map:** Leaflet overlay of the GHI, PVOUT, DNI and temperature rasters (GeoTIFF, rendered server-side to PNG and cached).
- **Land use by state:** Chart.js bar charts of area per land-use category and Austrian state.
- **Crop breakdown:** drill-down into sub-crops for a selected category and state.
- **Total land use:** overview of agricultural categories (forest, grassland and unproductive areas are excluded).

### Agrivoltaics calculator (`/calculator`)

The heart of the application, meant as a first feasibility check for farmers. It has three steps:

**Step 1 — Location**
- Click on a Leaflet/OpenStreetMap map of Austria.
- The app looks up GHI and PV output (PVOUT) from the raster data at that point.
- If the point has no data, it falls back to 3.5 kWh/m²/day and shows a notice.

**Step 2 — Farm details**
- Farm area (ha)
- Primary crop: winter wheat, summer wheat, potatoes, apples, vegetables, maize
- Feed-in tariff (€/kWh, default 0.08)

**Step 3 — Results**
- Two scenarios in tabs: *Hot & dry year* and *Cold & humid year*
- Viability score (0–100) with a High / Medium / Low rating
- Energy: installed capacity (kWp), yield (MWh/yr), PV revenue (€/yr)
- Financials: CAPEX, annual O&M, LCOE, annual net benefit, payback period
- Crop impact: yield change (%) and change in agricultural revenue compared to a conventional field
- Estimated water savings from partial shade
- Annual benefit breakdown (PV revenue, O&M cost, agricultural margin change)
- Maize is reported as unsuitable (low shade tolerance) instead of being calculated

### Calculation model (`src/scenario_calculations.py`)

| Item | Assumption |
|---|---|
| PV capacity | 600 kWp/ha (Fraunhofer ISE 2024, overhead system > 4 m) |
| PV yield | kWp × PVOUT × 365 / 1000 (PVOUT already includes losses and tilt); falls back to GHI × 0.8 if PVOUT is missing |
| CAPEX | 1,105 €/kWp (sum of module, inverter, mounting, electrics, planning, grid, installation, other) |
| O&M | 1.26 ct/kWh; LCOE shown as 6.88 + 1.26 ct/kWh (Fraunhofer ISE 2024) |
| Land loss | 10 % of cropland lost to mounting structures |
| Crop yield change | Per-crop delta for hot/dry and cold/humid years; yield and price from Austrian averages |
| Water savings | 20 % less irrigation (Elamri et al. 2018), scaled ×1.2 (hot/dry) or ×0.8 (cold/humid) |
| Score | GHI (0–40) + crop delta (0–30) + payback (0–30); High ≥ 55, Medium ≥ 35 |

The model is a simplified estimate. It ignores discounting, panel degradation, subsidies and self-consumption.

### Sources and further information (`/sources`)

Lists the papers, reports and datasets behind the numbers.

### Tech stack

| Layer | Technology |
|---|---|
| Frontend | Server-rendered Jinja2 templates, vanilla JavaScript |
| Styling | Tailwind CSS (CDN) |
| Map | Leaflet.js + OpenStreetMap tiles |
| Charts | Chart.js |
| Backend | Python, Flask |
| Data processing | rasterio, pandas, numpy, matplotlib |
| Container | Docker, Docker Compose |

The frontend loads Tailwind, Leaflet, Chart.js, fonts and map tiles from CDNs, so an internet connection is required.

### Data sources used

| Dataset | Purpose | Source |
|---|---|---|
| GHI, PVOUT, DNI, temperature rasters | Energy yield calculation and solar map | Global Solar Atlas / Solargis (`References/datasets/Solar`) |
| Land use by state and crop | Land use charts | Statistik Austria (`References/datasets/Landuse`) |
| Crop yields, prices, shade effects | Agricultural impact | Fraunhofer ISE, Austrian agriculture portals, literature (see Sources page) |

### Not implemented (ideas)

- Address or postal code search
- Hail and weather risk score, LER gauge, PDF report
- Advanced system configuration (coverage ratio, self-consumption)
- Parcel validation against Agraratlas / INVEKOS, tariffs from E-Control

### What to improve

- Field testing: find out what farmers actually need, how much this can help them, which information is missing, and where to get it.
- Crop yield change data was not too abundant; further research is required here.
- Contact different solar park operators on cost and feasibility of such systems, build times, and other options.

This could be further explored in the context of a thesis.
