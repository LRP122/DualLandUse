import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


PATH_TO_DATASETS = "/Users/luis/Desktop/Master/SS26/SensorNetworks/AgripholtiacsProject/References/datasets"
SOLAR_DIR = PATH_TO_DATASETS + "/Solar"
LANDUSE_DIR = PATH_TO_DATASETS + "/Landuse"

DATASET_TO_TEST = "landuse"

LAYERS = ["GHI", "PVOUT", "DNI", "TEMP"]

def load_solar_data(reduced_data):
    import rasterio
    import rasterio.transform
    from rasterio.vrt import WarpedVRT

    # Build base grid from GHI
    with rasterio.open(f"{SOLAR_DIR}/GHI.tif") as ghi:
        ghi_data = ghi.read(1).astype(float)
        ghi_data[ghi_data == ghi.nodata] = np.nan
        transform = ghi.transform
        crs = ghi.crs
        height, width = ghi.height, ghi.width

    rows, cols = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
    xs, ys = rasterio.transform.xy(transform, rows.ravel(), cols.ravel())

    df = pd.DataFrame({"lon": xs, "lat": ys, "GHI": ghi_data.ravel()})
    df = df[df["GHI"].notna()].reset_index(drop=True)
    mask = ~np.isnan(ghi_data)

    # Reproject other rasters to GHI grid in one read
    for name in ["PVOUT", "DNI", "TEMP"]:
        with rasterio.open(f"{SOLAR_DIR}/{name}.tif") as src:
            with WarpedVRT(src, crs=crs, transform=transform, width=width, height=height) as vrt:
                data = vrt.read(1).astype(float)
                if vrt.nodata is not None:
                    data[data == vrt.nodata] = np.nan
        df[name] = data[mask]

    if reduced_data:
        df = df.iloc[::20].reset_index(drop=True)

    return df

LANDUSE_CATEGORIES = [
    "Cereals", "Protein crops", "Root crops", "Oilseeds",
    "Forage cropping", "Industrial crops", "Other arable crops",
    "House & kitchen gardens", "Permanent crops",
    "Grassland intensive", "Grassland extensive",
    "Forest", "Forestry area", "Unproductive areas"
]

# Maps categories that have a detail CSV to their filename
CATEGORY_DETAIL_FILE = {
    "Cereals":           "Cereals.csv",
    "Protein crops":     "ProteinCrops.csv",
    "Root crops":        "RootCrops.csv",
    "Oilseeds":          "OilSeeds.csv",
    "Forage cropping":   "ForageCrops.csv",
    "Industrial crops":  "IndustrialCrops.csv",
    "Other arable crops":"Others.csv",
}


def get_total_by_category():
    """Return total area (ha) per land-use category summed across all Austrian states."""
    df = pd.read_csv(LANDUSE_DIR + "/LandUseGeneralByState.csv", header=None)
    state_rows = df.iloc[3:12]  # 9 states, skip "Not classifiable"

    totals = []
    for i, category in enumerate(LANDUSE_CATEGORIES):
        area_col = 1 + i * 4
        areas = pd.to_numeric(state_rows.iloc[:, area_col], errors="coerce")
        totals.append(areas.sum())

    return pd.DataFrame({"category": LANDUSE_CATEGORIES, "area_ha": totals})


def get_production_by_state(category):
    col_index = LANDUSE_CATEGORIES.index(category)
    area_col = 1 + col_index * 4  # area columns are every 4th, starting at 1

    df = pd.read_csv(LANDUSE_DIR + "/LandUseGeneralByState.csv", header=None)
    # rows 3–11 are the 9 Austrian states (row 12 is "Not classifiable", skip it)
    state_rows = df.iloc[3:12]
    states = state_rows.iloc[:, 0].str.replace(r"\s*<[^>]+>", "", regex=True)
    areas = pd.to_numeric(state_rows.iloc[:, area_col], errors="coerce")

    return pd.DataFrame({"state": states.values, "area_ha": areas.values})


def get_crop_detail_by_state(category, state):
    """Return the sub-crop breakdown for a given category and state name."""
    filename = CATEGORY_DETAIL_FILE.get(category)
    if filename is None:
        return pd.DataFrame()

    raw = pd.read_csv(LANDUSE_DIR + "/" + filename, header=None)

    # Row 0 holds the sub-crop names at every 4th column starting at col 1
    crop_names = raw.iloc[0, 1::4].tolist()

    # Find the state row by matching the start of the first column
    # (state names in the CSV look like "Lower Austria <AT12>")
    state_mask = raw.iloc[:, 0].str.startswith(state)
    state_row = raw[state_mask]
    if state_row.empty:
        return pd.DataFrame()

    areas = pd.to_numeric(state_row.iloc[0, 1::4], errors="coerce").tolist()
    return pd.DataFrame({"crop": crop_names, "area_ha": areas})


if __name__ == "__main__":
    pass
