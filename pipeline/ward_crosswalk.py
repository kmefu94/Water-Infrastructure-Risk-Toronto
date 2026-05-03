import geopandas as gpd
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data/RawData"
OUTPUT_PATH = ROOT / "ward_profiles_output"
OUTPUT_PATH.mkdir(exist_ok=True)

SHP_NEIGHBOURHOODS = DATA_PATH / "neighbourhoods/Neighbourhoods - 4326.shp"
SHP_25WARD = DATA_PATH / "city-wards/25ward/WARD_WGS84.shp"
SHP_44WARD = DATA_PATH / "city-wards/44ward/gcc/Projects/Open Data/Files/Data Upload - May 2010/May2010_WGS84/icitw_wgs84.shp"


def load_layers():
    neighbourhoods = gpd.read_file(SHP_NEIGHBOURHOODS)[["AREA_SH5", "AREA_NA7", "geometry"]]
    neighbourhoods.columns = ["neighbourhood_code", "neighbourhood_name", "geometry"]

    wards_25 = gpd.read_file(SHP_25WARD)[["AREA_S_CD", "AREA_NAME", "geometry"]]
    wards_25.columns = ["ward_25_number", "ward_25_name", "geometry"]
    wards_25["ward_25_number"] = wards_25["ward_25_number"].astype(int)

    wards_44 = gpd.read_file(SHP_44WARD)[["SCODE_NAME", "NAME", "geometry"]]
    wards_44.columns = ["ward_44_number", "ward_44_name", "geometry"]
    wards_44["ward_44_number"] = wards_44["ward_44_number"].astype(int)

    return neighbourhoods, wards_25, wards_44


def build_crosswalk(neighbourhoods, wards_25, wards_44):
    # Use neighbourhood centroids for the spatial join — each neighbourhood
    # should fall cleanly within one ward in both models
    centroids = neighbourhoods.copy()
    centroids["geometry"] = neighbourhoods.geometry.centroid

    # Join neighbourhoods → 25-ward
    n_to_25 = gpd.sjoin(centroids, wards_25, how="left", predicate="within")
    n_to_25 = n_to_25[["neighbourhood_code", "neighbourhood_name", "ward_25_number", "ward_25_name"]]

    # Join neighbourhoods → 44-ward
    n_to_44 = gpd.sjoin(centroids, wards_44, how="left", predicate="within")
    n_to_44 = n_to_44[["neighbourhood_code", "ward_44_number", "ward_44_name"]]

    # Merge to produce neighbourhood-level crosswalk
    crosswalk = n_to_25.merge(n_to_44, on="neighbourhood_code", how="left")

    # Aggregate to ward-level: 44-ward → 25-ward(s)
    # A single 44-ward may map to multiple 25-wards (if it was split)
    # Take the majority ward (most neighbourhoods) as the primary mapping
    ward_map = (
        crosswalk.groupby(["ward_44_number", "ward_44_name", "ward_25_number", "ward_25_name"])
        .size()
        .reset_index(name="neighbourhood_count")
        .sort_values(["ward_44_number", "neighbourhood_count"], ascending=[True, False])
    )

    # Primary mapping: highest neighbourhood count per old ward
    primary_map = ward_map.drop_duplicates(subset="ward_44_number", keep="first").drop(columns="neighbourhood_count")

    return crosswalk, primary_map


def main():
    print("Loading shapefiles...")
    neighbourhoods, wards_25, wards_44 = load_layers()
    print(f"  Neighbourhoods: {len(neighbourhoods)}")
    print(f"  25-ward model:  {len(wards_25)} wards")
    print(f"  44-ward model:  {len(wards_44)} wards")

    print("\nBuilding crosswalk...")
    crosswalk, primary_map = build_crosswalk(neighbourhoods, wards_25, wards_44)

    # Report any unmapped entries
    unmapped_25 = crosswalk["ward_25_number"].isna().sum()
    unmapped_44 = crosswalk["ward_44_number"].isna().sum()
    if unmapped_25 > 0:
        print(f"  WARNING: {unmapped_25} neighbourhoods not mapped to a 25-ward")
    if unmapped_44 > 0:
        print(f"  WARNING: {unmapped_44} neighbourhoods not mapped to a 44-ward")

    # Save outputs
    crosswalk_path = OUTPUT_PATH / "neighbourhood_ward_crosswalk.csv"
    primary_map_path = OUTPUT_PATH / "ward_44_to_25_primary.csv"

    crosswalk.to_csv(crosswalk_path, index=False)
    primary_map.to_csv(primary_map_path, index=False)

    print(f"\nNeighbourhood crosswalk ({len(crosswalk)} rows) -> {crosswalk_path}")
    print(f"44->25 primary map ({len(primary_map)} rows) -> {primary_map_path}")

    print("\nSample 44->25 primary map:")
    print(primary_map.head(15).to_string(index=False))

    return crosswalk, primary_map


if __name__ == "__main__":
    crosswalk, primary_map = main()
