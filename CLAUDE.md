# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the code

```bash
# Install dependencies
pip install -r requirements.txt

# Run the new pipeline (BTS + FAA + ICAO merge)
python -m src.calculate_emissions      # runs __main__ block for 2021-09

# Run a single-flight example (old pipeline)
python examples/single_flight.py

# Run the full batch pipeline (old pipeline, downloads BTS data)
python -c "from src.batch import run; run(2021, 9)"
```

There are no tests yet.

## Architecture

Two parallel pipelines exist. The **new pipeline** (`calculate_emissions.py`) is the intended source of truth going forward; the **old pipeline** (`batch.py` + `reference_tables.py` + `emissions_calc.py`) is legacy.

### New pipeline (`src/bts.py` → `src/faa.py` → `src/icao.py` → `src/calculate_emissions.py`)

Each module is independent and returns a DataFrame:

- **`bts.py`** — loads a BTS on-time CSV for a given year/month, keeps `tail_number`, `air_time`, `taxi_in`, `taxi_out`, drops cancelled rows (no `AirTime`).
- **`faa.py`** — joins FAA `MASTER.txt` → `ENGINE.txt` → `ACFTREF.txt` to produce a tail → `(engine_model, faa_engine_code, mfr_mdl, aircraft_mfr, aircraft_model, seats)` mapping.
- **`icao.py`** — reads ICAO EEDB v32, matches each FAA engine code to one or more ICAO UIDs via a 4-tier name cascade (exact → strip-series → prefix → slash-stripped) plus a manual override table for naming mismatches (RB211/Trent branding, spacing, etc.). Averages emission indices across matched variants and returns one row per `faa_engine_code` with kg/s rates for HC, CO, NOx, CO2 at each LTO phase.
- **`calculate_emissions.py`** — left-joins BTS → FAA → ICAO → BADA, computes LTO and CCD emissions for every flight, and outputs `co2_lto`, `co2_ccd`, `co2_total`, `co2e_total` (plus HC, CO, NOx breakdowns). Final output retains ~88.7% of original BTS rows.

### Old pipeline (`src/batch.py`)

- **`batch.py`** — downloads BTS zip from BTS Transtats, ran `emissions_calc` row-by-row in a loop, wrote results CSV. `emissions_calc.py` and `reference_tables.py` have been deleted; this file is no longer functional and will be removed.

### Data sources (`new_data/`)

| File | What it is |
|---|---|
| `On_Time_*_{year}_{month}.csv` | BTS on-time performance (one per month) |
| `ReleasableAircraft/MASTER.txt` | FAA registry: tail → engine code + aircraft model code |
| `ReleasableAircraft/ENGINE.txt` | FAA engine reference: code → model name |
| `ReleasableAircraft/ACFTREF.txt` | FAA aircraft reference: model code → manufacturer, model, seats |
| `edb-emissions-databank_v32__web_.xlsx` | ICAO EEDB v32: certified LTO emission indices per engine UID |
| `model_standard_code_map.csv` | Maps FAA `MFR_MDL_CODE` → BADA Standard Code |
| `Engine Fuel Consumption.xlsx` | BADA CCD table: fuel + emissions by aircraft Standard Code and flight duration |
| `LTO Backup.xlsx` | Fallback: Standard Code → FAA engine code for tails not in FAA registry |

### Key domain constants

- **ICAO LTO phase durations:** T/O = 42 s, C/O = 132 s, App = 240 s; Idle = actual BTS taxi times
- **CO2 derivation:** `fuel_flow (kg/s) × 3.16` — carbon mass balance of jet-A, not directly measured
- **time_ccd:** `air_time (min) − (42 + 132 + 240) / 60` — flight time above 3,000 ft
- **`reference_tables.py` has duplicate logic** from `icao.py` (`_MANUAL_NAME_OVERRIDES`, `_match_engine_to_icao`, `_rates_from_icao_row`) — these should eventually be consolidated into `icao.py`
