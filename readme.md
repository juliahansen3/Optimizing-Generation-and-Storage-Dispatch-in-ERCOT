# Optimizing Generation and Storage Dispatch in ERCOT

Course project for **MIT 15.C57 – Optimization Methods**.

The goal is to model the ERCOT (Texas) power grid as an optimization problem: deciding how to dispatch generators and battery storage hour by hour to meet electricity demand at minimum cost, subject to capacity and operational constraints.

## Repository Structure

```
.
├── Data Processing/
│   └── Data/
│       ├── Generator_Y2025.csv     # EIA-860 Schedule 3: generator-level data
│       ├── Plant_Y2025.csv         # EIA-860 Schedule 2: plant-level data
│       └── Native_Load_2025.csv    # ERCOT hourly native load by weather zone
└── readme.md
```

## Data

| File | Source | Description |
|------|--------|-------------|
| `Generator_Y2025.csv` | [EIA Form 860](https://www.eia.gov/electricity/data/eia860/), 2025, Schedule 3 | Operable generating units in the US: technology, prime mover, nameplate/summer/winter capacity, minimum load, operating status, and more. Linked to plants by `Plant Code`. |
| `Plant_Y2025.csv` | [EIA Form 860](https://www.eia.gov/electricity/data/eia860/), 2025, Schedule 2 | Plant-level data: location (state, county, lat/long), NERC region, balancing authority, and regulatory status. Filter on `Balancing Authority Code == ERCO` to select ERCOT plants. |
| `Native_Load_2025.csv` | [ERCOT Hourly Load Data Archives](https://www.ercot.com/gridinfo/load/load_hist) | Hourly native load (MW) for 2025 across ERCOT's 8 weather zones (`COAST`, `EAST`, `FWEST`, `NORTH`, `NCENT`, `SOUTH`, `SCENT`, `WEST`) plus the system total (`ERCOT`). |

### Notes on reading the data

- The two EIA-860 files have a **title row** above the header — skip the first row when loading (e.g. `pd.read_csv(path, skiprows=1)`).
- The files contain a UTF-8 byte-order mark; use `encoding="utf-8-sig"` if column names look off.
- Load values in `Native_Load_2025.csv` use comma thousands separators (e.g. `"43,223.86"`); use `thousands=","` when reading.
- `Hour Ending` timestamps are in `MM/DD/YYYY HH:MM` format.

```python
import pandas as pd

gens   = pd.read_csv("Data Processing/Data/Generator_Y2025.csv", skiprows=1, encoding="utf-8-sig")
plants = pd.read_csv("Data Processing/Data/Plant_Y2025.csv", skiprows=1, encoding="utf-8-sig")
load   = pd.read_csv("Data Processing/Data/Native_Load_2025.csv", thousands=",", encoding="utf-8-sig")

# Restrict generators to ERCOT
ercot_plants = plants.loc[plants["Balancing Authority Code"] == "ERCO", "Plant Code"]
ercot_gens = gens[gens["Plant Code"].isin(ercot_plants)]
```

## Project Status

- [x] Collect generator, plant, and load data
- [ ] Clean data and build ERCOT generator fleet
- [ ] Formulate dispatch / storage optimization model
- [ ] Solve and analyze results
