# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the code

```bash
# Install dependencies
pip install -r requirements.txt

# Download BTS on-time data for a given quarter (e.g. Q1 2026)
python data/download_bts.py 2026 1

# Run the pipeline for a given month
python -m src.calculate_emissions      # update year/month in __main__ block
```

There are no tests yet.

## Architecture

### Pipeline (`src/bts.py` → `src/faa.py` → `src/icao.py` → `src/bada.py` → `src/calculate_emissions.py`)

Each module is independent and returns a DataFrame:

- **`bts.py`** — loads a BTS on-time CSV for a given year/month, keeps `tail_number`, `air_time`, `taxi_in`, `taxi_out`, drops cancelled rows (no `AirTime`).
- **`faa.py`** — joins FAA `MASTER.txt` → `ENGINE.txt` → `ACFTREF.txt` to produce a tail → `(engine_model, faa_engine_code, mfr_mdl, aircraft_mfr, aircraft_model, seats)` mapping.
- **`icao.py`** — reads ICAO EEDB v32, matches each FAA engine code to one or more ICAO UIDs via a 4-tier name cascade (exact → strip-series → prefix → slash-stripped) plus a manual override table for naming mismatches (RB211/Trent branding, spacing, etc.). Averages emission indices across matched variants and returns one row per `faa_engine_code` with kg/s rates for HC, CO, NOx, CO2 at each LTO phase.
- **`bada.py`** — maps FAA aircraft types to BADA standard codes via regex rules and interpolates CCD emissions (fuel, CO2, NOx, SOx, H2O, CO, HC) from the Engine Fuel Consumption table.
- **`calculate_emissions.py`** — left-joins BTS → FAA → ICAO → BADA, computes LTO and CCD emissions for every flight, and outputs `co2_lto`, `co2_ccd`, `co2_total`, `co2e_total` (plus HC, CO, NOx breakdowns). Final output retains ~88.7% of original BTS rows.

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
