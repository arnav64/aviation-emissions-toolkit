# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the code

```bash
# Install dependencies
pip install -r requirements.txt

# Download BTS on-time data for a given quarter (e.g. Q1 2026 → downloads Jan, Feb, Mar)
python data/download_bts.py 2026 1

# Run the pipeline for a given month (edit year/month in __main__ block)
python -m src.calculate_emissions

# Run an example script
python examples/single_flight.py
python examples/monthly_batch.py 2021 9
python examples/city_pair_analysis.py   # requires monthly_batch output first
```

There are no tests yet.

## Visualization

```bash
# Build the interactive emissions map (generates docs/index.html)
python viz/build_viz.py

# Force-refresh the airport coordinates cache
python viz/build_viz.py --refresh
```

`viz/build_viz.py` reads `results/OnTimeEmissions2021_9.csv`, downloads US airport coordinates from OurAirports (cached at `viz/airports.csv`), aggregates emissions by route and airport, and writes a self-contained Plotly HTML to `docs/index.html`.

To publish: enable GitHub Pages in repo Settings → Pages → Source: main branch, `/docs` folder.

## Architecture

### Current pipeline (`src/bts.py` → `src/faa.py` → `src/icao.py` → `src/bada.py` → `src/calculate_emissions.py`)

Each module is independent and returns a DataFrame:

- **`bts.py`** — loads a BTS on-time CSV for a given year/month, keeps `tail_number`, `air_time`, `taxi_in`, `taxi_out`, `origin`, `dest`, `origin_city`, `dest_city`, `distance_miles`; drops cancelled rows (no `AirTime`).
- **`faa.py`** — joins FAA `MASTER.txt` → `ENGINE.txt` → `ACFTREF.txt` to produce a tail → `(engine_model, faa_engine_code, mfr_mdl, aircraft_mfr, aircraft_model, seats)` mapping.
- **`icao.py`** — reads ICAO EEDB v32, matches each FAA engine code to one or more ICAO UIDs via a 4-tier name cascade (exact → strip-series → prefix → slash-stripped) plus a manual override table for naming mismatches (RB211/Trent branding, spacing, etc.). Averages emission indices across matched variants and returns one row per `faa_engine_code` with kg/s rates for HC, CO, NOx, CO2 at each LTO phase.
- **`bada.py`** — maps FAA aircraft types to BADA standard codes via regex rules and interpolates CCD emissions (fuel, CO2, NOx, SOx, H2O, CO, HC) from the Engine Fuel Consumption table.
- **`calculate_emissions.py`** — left-joins BTS → FAA → ICAO → BADA, computes LTO and CCD emissions for every flight, and outputs `co2_lto`, `co2_ccd`, `co2_total`, `co2e_total` (plus HC, CO, NOx breakdowns). Final output retains ~88.7% of original BTS rows.

### Legacy pipeline (`src/batch.py`, `src/emissions_calc.py`, `src/reference_tables.py`)

Row-by-row loop over a tqdm progress bar; downloads BTS data itself and writes to `results/OnTimeEmissions{year}_{month}.csv`. Superseded by the vectorised pipeline above but still functional. The `examples/monthly_batch.py` and `examples/city_pair_analysis.py` scripts use this legacy path.

### Data sources (`data/`)

See `data/SOURCES.md` for download links. Expected files:

| File | What it is |
|---|---|
| `On_Time_*_{year}_{month}.csv` | BTS on-time performance (one per month) |
| `ReleasableAircraft/MASTER.txt` | FAA registry: tail → engine code + aircraft model code |
| `ReleasableAircraft/ENGINE.txt` | FAA engine reference: code → model name |
| `ReleasableAircraft/ACFTREF.txt` | FAA aircraft reference: model code → manufacturer, model, seats |
| `edb-emissions-databank_v32__web_.xlsx` | ICAO EEDB v32: certified LTO emission indices per engine UID |
| `Engine Fuel Consumption.xlsx` | BADA CCD table: fuel + emissions by aircraft type and flight duration |

### Key domain constants

- **ICAO LTO phase durations:** T/O = 42 s, C/O = 132 s, App = 240 s; Idle = actual BTS taxi times
- **CO2 derivation:** `fuel_flow (kg/s) × 3.16` — carbon mass balance of jet-A, not directly measured
- **time_ccd:** `air_time (min) − (42 + 132 + 240) / 60` — flight time above 3,000 ft
- **GWPs for CO2-equivalent:** HC = 84, CO = 1.57, NOx = 298
