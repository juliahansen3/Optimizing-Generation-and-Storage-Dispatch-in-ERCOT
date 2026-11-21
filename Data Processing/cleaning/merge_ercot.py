"""Build the August 4–10, 2025 ERCOT fleet. Requires Python 3.10+ and pandas.

Each output row gets a short, stable `id`:
  generators: <FUEL>_<first plant code>, e.g. NGCC_3559, SOLAR_65661
  batteries:  BAT_<plant code>_<n>, n numbered within the plant, e.g. BAT_56961_1
"""
import argparse
from pathlib import Path

import pandas as pd

KEY = ["Plant Code", "Generator ID"]
LOCATION = ["Latitude", "Longitude"]
CAPACITY = ["Nameplate Capacity (MW)", "Summer Capacity (MW)", "Winter Capacity (MW)"]
STORAGE = ["Nameplate Energy Capacity (MWh)", "Maximum Charge Rate (MW)",
           "Maximum Discharge Rate (MW)"]
FUEL = {"SUN": "Solar", "WND": "Wind", "WAT": "Hydro", "NUC": "Nuclear",
        "LIG": "Coal", "SUB": "Coal"}
GAS = {**dict.fromkeys(["CA", "CT", "CS"], "Natural Gas - Combined Cycle"),
       **dict.fromkeys(["GT", "IC", "ST"], "Natural Gas - Non-Combined Cycle")}
FUEL_CODE = {"Natural Gas - Combined Cycle": "NGCC", "Natural Gas - Non-Combined Cycle": "NGCT",
             "Coal": "COAL", "Nuclear": "NUC", "Wind": "WIND", "Solar": "SOLAR", "Hydro": "HYDRO"}
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def read_eia(path, columns):
    data = pd.read_csv(path, skiprows=1, encoding="cp1252", dtype=str,
                       usecols=columns, keep_default_na=False)
    return data.apply(lambda col: col.str.strip())


def numeric(data, columns):
    for column in columns:
        data[column] = pd.to_numeric(data[column].str.replace(",", "", regex=False),
                                     errors="raise")
    if data[columns].isna().any().any():
        raise ValueError(f"Missing numeric data in {columns}")


def build(input_dir, output_dir, values_path):
    plants = read_eia(input_dir / "Plant_Y2025.csv",
                      ["Plant Code", "Balancing Authority Code", *LOCATION])
    units = read_eia(input_dir / "Generator_Y2025.csv",
                     [*KEY, "Technology", "Prime Mover", "Energy Source 1", "Status",
                      "Operating Year", "Operating Month", *CAPACITY])
    storage = read_eia(input_dir / "Energy_Storage_Y2025.csv", KEY + STORAGE)
    ercot = plants.loc[plants["Balancing Authority Code"].eq("ERCO"),
                       ["Plant Code", *LOCATION]]
    fleet = units.merge(ercot, on="Plant Code", validate="many_to_one")
    fleet = fleet.loc[fleet["Status"].eq("OP")].copy()
    numeric(fleet, ["Operating Year", "Operating Month", *LOCATION])
    # Exclude August starts because EIA gives only the commissioning month.
    fleet = fleet.loc[100 * fleet["Operating Year"] + fleet["Operating Month"] < 202508]
    if fleet.duplicated(KEY).any():
        raise ValueError("Duplicate generator key in ERCOT fleet")

    is_battery = fleet["Technology"].eq("Batteries")
    batteries = fleet.loc[is_battery, KEY + LOCATION].merge(
        storage, on=KEY, how="left", validate="one_to_one", indicator=True)
    if not batteries.pop("_merge").eq("both").all():
        raise ValueError("Missing storage record for an ERCOT battery")
    numeric(batteries, STORAGE)
    if not batteries[STORAGE].gt(0).all().all():
        raise ValueError("Battery limits must be positive")

    gen = fleet.loc[~is_battery].copy()
    gen["Energy Source"] = gen["Energy Source 1"].map(FUEL)
    is_gas = gen["Energy Source 1"].eq("NG")
    gas_types = gen.loc[is_gas, "Prime Mover"].map(GAS)
    if gas_types.isna().any():
        raise ValueError("Unmapped natural gas prime mover")
    gen.loc[is_gas, "Energy Source"] = gas_types
    gen = gen.dropna(subset=["Energy Source"]).copy()
    numeric(gen, CAPACITY)
    grouped = gen.groupby(LOCATION + ["Energy Source"], as_index=False).agg(**{
        "Plant Code": ("Plant Code", lambda s: "|".join(sorted(set(s), key=int))),
        **{col: (col, "sum") for col in CAPACITY},
        "Generator Count": ("Generator ID", "size"),
    })
    grouped["id"] = (grouped["Energy Source"].map(FUEL_CODE) + "_"
                     + grouped["Plant Code"].str.split("|").str[0])
    grouped = grouped[["id", "Plant Code", *LOCATION, "Energy Source", *CAPACITY,
                       "Generator Count"]]

    batteries = batteries.sort_values(KEY, key=lambda s: s.map(int) if s.name == "Plant Code" else s)
    batteries.insert(0, "id", "BAT_" + batteries["Plant Code"] + "_"
                     + (batteries.groupby("Plant Code").cumcount() + 1).astype(str))
    for name, df in [("generator", grouped), ("battery", batteries)]:
        if df["id"].isna().any() or df["id"].duplicated().any():
            raise ValueError(f"Missing or duplicate {name} id")

    # Optional chart lookup. The screenshot supplies no unit for 'value'.
    if values_path:
        values = pd.read_csv(values_path).rename(columns={"energy_source": "Energy Source"})
        grouped = grouped.merge(values[["Energy Source", "value"]], on="Energy Source",
                                how="left", validate="many_to_one")
        if grouped["value"].isna().any():
            raise ValueError("Missing chart value for a generator category")

    output_dir.mkdir(parents=True, exist_ok=True)
    grouped.to_csv(output_dir / "generators_2025-08-04.csv", index=False)
    batteries[["id", *KEY, *LOCATION, *STORAGE]].to_csv(
        output_dir / "energy_storage_2025_08_04.csv", index=False)
    print(f"{len(gen)} generators in {len(grouped)} groups; {len(batteries)} batteries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR / "cleaned_data")
    parser.add_argument("--values", type=Path, help="Optional energy_source_values.csv")
    args = parser.parse_args()
    build(args.input_dir, args.output_dir, args.values)
