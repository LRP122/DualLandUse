# Various Sources
# Frauenhofer
# Austria Agriculture Portals
CROP_PARAMS = {
    "potatoes":     {"label": "Potatoes",     "yield_dt_ha": 316, "price_dt": 30, "delta_hot":  0.11, "delta_cold": -0.16},
    "summer_wheat": {"label": "Summer Wheat", "yield_dt_ha":  44, "price_dt": 20, "delta_hot":  0.03, "delta_cold": -0.18},
    "winter_wheat": {"label": "Winter Wheat", "yield_dt_ha":  58, "price_dt": 20, "delta_hot":  0.03, "delta_cold": -0.18},
    "apples":       {"label": "Apples",       "yield_dt_ha": 250, "price_dt": 80, "delta_hot":  0.02, "delta_cold": -0.03},
    "vegetables":   {"label": "Vegetables",   "yield_dt_ha": 350, "price_dt": 70, "delta_hot":  0.12, "delta_cold": -0.18},
    "maize":        {"label": "Maize",        "yield_dt_ha":  99, "price_dt": 18, "delta_hot": -0.25, "delta_cold": -0.35},
}

# Fraunhofer ISE 2024 — overhead agrivoltaic system (> 4 m stilted)
PV_CAPACITY_PER_HA = 600  # kWp/ha

# Component cost breakdown (€/kWp):
#   PV modules:                      300
#   Inverter:                         25
#   Mounting system:                 375
#   Electrics:                        25
#   Project planning:                 50
#   Grid connection:                  60
#   Surface and Installation          225
#   Other costs:                      45
CAPEX_PER_KWP = 1105  # €/kWp — sum of above components

# Fraunhofer ISE 2024 LCOE components
LCOE_CAPEX = 6.88  # ct/kWh — annualised capital cost
LCOE_OPEX  = 1.26  # ct/kWh — O&M

# Project WACC assumption
DISCOUNT_RATE = 0.057

# Wikifarmer — Austrian irrigated crops need 6–9 t/ha total supplemental water per season
IRRIGATION_LITERS_PER_HA = 7_000
# Elamri et al. 2018 — agrivoltaic shade reduces crop evapotranspiration by ~20%
IRRIGATION_REDUCTION = 0.2

# Frauenhofer
MOUNTING_LAND_LOSS = 0.1

# Used for website
SCORE_HIGH   = 55
SCORE_MEDIUM = 35

# Scenarios differ only in which crop yield delta is applied.
SCENARIOS = {
    "hot_dry":    {"label": "Hot & Dry Year",    "delta_key": "delta_hot"},
    "cold_humid": {"label": "Cold & Humid Year", "delta_key": "delta_cold"},
}

def _run_scenario(area_ha, cp, ghi, tariff, climate):
    s         = SCENARIOS[climate]
    adj_delta = cp[s["delta_key"]]

    # PV energy: kWp × GHI_daily × 365 × PR / 1000 → MWh/year
    # GHI (kWh/m²/day) numerically equals peak sun hours/day when panels are rated at 1 kW/m²

    pv_capacity_kwp = area_ha * PV_CAPACITY_PER_HA
    # Account for loss in GHI 0.8
    pv_yield_mwh    = pv_capacity_kwp * ghi * 365 / 1000 * 0.8
    pv_revenue      = pv_yield_mwh * 1000 * tariff

    base_revenue    = cp["yield_dt_ha"] * cp["price_dt"] * area_ha
    av_revenue      = base_revenue * (1 - MOUNTING_LAND_LOSS) * (1 + adj_delta)
    delta_agri      = round(av_revenue - base_revenue)
    yield_delta_pct = round(((1 - MOUNTING_LAND_LOSS) * (1 + adj_delta) - 1) * 100)


    pv_yield_kwh = pv_yield_mwh * 1000
    capex        = pv_capacity_kwp * CAPEX_PER_KWP
    opex_annual  = (LCOE_OPEX * 0.01) * pv_yield_kwh
    net_annual   = pv_revenue - opex_annual + delta_agri
    payback      = capex / net_annual if net_annual > 0 else 999

    # Water savings (Elamri et al. 2018)
    # Hot/dry years have higher evapotranspiration → more water saved; cold/humid → less
    et_climate_factor = 1.20 if climate == "hot_dry" else 0.80
    water_saved_L     = round(area_ha * IRRIGATION_LITERS_PER_HA * IRRIGATION_REDUCTION * et_climate_factor)

    # Viability score: GHI (0–40) + crop delta (0–30) + payback (0–30)
    # Payback ≤ 8 yr → full 30 pts; ≥ 20 yr → 0 pts
    ghi_score     = min(ghi / 5.0 * 40, 40)
    crop_score    = min(max((1 + adj_delta) * 30, 0), 30)
    payback_score = max(min((20 - payback) / (20 - 8) * 30, 30), 0)
    score         = int(ghi_score + crop_score + payback_score)
    if score >= SCORE_HIGH:
        s_label, color = "High", "green"
    elif score >= SCORE_MEDIUM:
        s_label, color = "Medium", "amber"
    else:
        s_label, color = "Low", "red"

    return {
        "scenario_key":    climate,
        "scenario_label":  SCENARIOS[climate]["label"],
        "score":           score,
        "label":           s_label,
        "color":           color,
        "pv_capacity_kwp": round(pv_capacity_kwp),
        "pv_yield_mwh":    round(pv_yield_mwh, 1),
        "pv_revenue":      round(pv_revenue),
        "base_revenue":    round(base_revenue),
        "av_revenue":      round(av_revenue),
        "delta_agri":      delta_agri,
        "yield_delta_pct": yield_delta_pct,
        "crop_label":      cp["label"],
        "yield_dt_ha":     cp["yield_dt_ha"],
        "price_dt":        cp["price_dt"],
        "capex":           round(capex),
        "opex_annual":     round(opex_annual),
        "lcoe_ct":         round(LCOE_CAPEX + LCOE_OPEX, 2),
        "payback":         round(payback, 1),
        "total_benefit":   round(net_annual),
        "area_ha":         area_ha,
        "ghi_daily":       round(ghi, 2),
        "water_saved_L":   water_saved_L,
    }


def calculate_agrivoltaic_scenario(area_ha, crop_key, ghi, tariff):
    area_ha = max(float(area_ha), 0.1)
    ghi     = float(ghi)
    tariff  = float(tariff)
    cp      = CROP_PARAMS.get(crop_key, CROP_PARAMS["winter_wheat"])

    if crop_key == "maize":
        return {
            "unprofitable": True,
            "crop_label":   cp["label"],
            "reason":       "Maize is a C4 plant with very low shade tolerance. "
                            "The yield loss under agrivoltaic partial shade consistently "
                            "outweighs PV revenue at realistic system densities.",
        }

    return {
        "unprofitable": False,
        "crop_label":   cp["label"],
        "hot_dry":      _run_scenario(area_ha, cp, ghi, tariff, "hot_dry"),
        "cold_humid":   _run_scenario(area_ha, cp, ghi, tariff, "cold_humid"),
    }
