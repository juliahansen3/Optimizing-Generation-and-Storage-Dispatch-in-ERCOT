"""Build great-circle (haversine) distance matrices in km between ERCOT generators,
battery storage units, and demand zones (zone_coords.csv).

Outputs (in the cleaned_data folder):
  distance_generator_zone.csv     generator_id x zone_id
  distance_generator_storage.csv  generator_id x battery_id
  distance_storage_zone.csv       battery_id   x zone_id

Ids come from the `id` column written by merge_ercot.py (e.g. NGCC_3559, BAT_56961_1)
and the `zone` column of zone_coords.csv (e.g. COAST). Load with
pd.read_csv(path, index_col=0).
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0
DEFAULT_DIR = Path(__file__).resolve().parent.parent / "data" / "cleaned_data"


def haversine_matrix(lat1, lon1, lat2, lon2):
    """Pairwise distance (km) between points set 1 (rows) and set 2 (columns)."""
    lat1, lon1 = np.radians(lat1)[:, None], np.radians(lon1)[:, None]
    lat2, lon2 = np.radians(lat2)[None, :], np.radians(lon2)[None, :]
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def points(df, id_col, lat="Latitude", lon="Longitude"):
    """Return a frame indexed by the id column with numeric lat/lon."""
    ids = df[id_col].astype(str)
    if ids.duplicated().any():
        raise ValueError(f"Duplicate {id_col} values: {ids[ids.duplicated()].tolist()[:5]}")
    out = pd.DataFrame({"lat": df[lat].astype(float).values,
                        "lon": df[lon].astype(float).values}, index=ids.values)
    if out.isna().any().any():
        raise ValueError(f"Missing coordinates for {out.index[out.isna().any(axis=1)].tolist()[:5]}")
    return out


def matrix(rows, cols, row_name, col_name):
    d = haversine_matrix(rows["lat"].values, rows["lon"].values,
                         cols["lat"].values, cols["lon"].values)
    return pd.DataFrame(d.round(3), index=pd.Index(rows.index, name=row_name),
                        columns=pd.Index(cols.index, name=col_name))


def build(data_dir, output_dir):
    gens = pd.read_csv(data_dir / "generators_2025-08-04.csv")
    batts = pd.read_csv(data_dir / "energy_storage_2025_08_04.csv")
    zones = pd.read_csv(data_dir / "zone_coords.csv")
    for name, df in [("generators", gens), ("batteries", batts)]:
        if "id" not in df.columns:
            raise ValueError(f"No 'id' column in {name} file; rerun merge_ercot.py first")

    gen_pts = points(gens, "id")
    batt_pts = points(batts, "id")
    zone_pts = points(zones, "zone", lat="latitude", lon="longitude")

    outputs = {
        "distance_generator_zone.csv": matrix(gen_pts, zone_pts, "generator_id", "zone_id"),
        "distance_generator_storage.csv": matrix(gen_pts, batt_pts, "generator_id", "battery_id"),
        "distance_storage_zone.csv": matrix(batt_pts, zone_pts, "battery_id", "zone_id"),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, df in outputs.items():
        df.to_csv(output_dir / name)
        print(f"{name}: {df.shape[0]} x {df.shape[1]}, "
              f"{df.values.min():,.1f}-{df.values.max():,.1f} km")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()
    build(args.data_dir, args.output_dir)
