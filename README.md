# Aviation Emissions Modeling Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Citation Count](https://img.shields.io/badge/Cited%20by-11-green.svg)](https://scholar.google.com/scholar?oi=bibs&hl=en&cites=7178136927124764561&as_sdt=5)
[![Emissions Map](https://img.shields.io/badge/Live%20Map-View%20Visualization-orange)](https://arnav64.github.io/aviation-emissions-toolkit/)

**An open-source, data-driven framework for system-wide aviation emissions accounting, designed to support transparency in climate impact assessment and U.S. infrastructure optimization.**

---

## 🏛️ Key Motivation
This toolkit provides the high-fidelity computational framework required to support and execute current federal decarbonization mandates:

* **[U.S. Aviation Climate Action Plan](https://www.transportation.gov/priorities/climate-change/us-aviation-climate-action-plan):** This toolkit directly supports the 2050 Net-Zero goal for the U.S. aviation sector by providing the reproducible emissions accounting methodology necessary for industry-wide adoption.
* **[U.S. National Blueprint for Transportation Decarbonization](https://www.energy.gov/eere/us-national-blueprint-transportation-decarbonization):** By standardizing emissions estimation, this toolkit aligns with the Blueprint’s whole-of-government strategy to transform the transportation sector and eliminate greenhouse gas emissions by 2050.

## 🏆 Recognition & Impact
This methodology originated from award-winning research at the **10th International Conference on Research in Air Transportation (ICRAT)**, co-organized by the FAA and EUROCONTROL.

> 🏆 **Best Paper Award: Economics, Policy, and Equity**
> *Democratizing Aviation Emissions Estimation: Development of an Open-Source, Data-Driven Methodology* > **Authors:** Andy G. Eskenazi, Landon G. Butler, **Arnav P. Joshi**, Megan S. Ryerson
> [**View Official ICRAT Award Results**](https://www.icrat.org/previous-conferences/10th-international-conference/papers/)

Our methodology has been formally adopted and cited by **9 independent academic publications**, demonstrating its role as a recognized standard in environmental accounting for the aviation sector.

### 📖 Research Documentation

This methodology was developed and peer-reviewed for the 10th ICRAT. You can access the full research paper via the open-access preprint:

[**Read the Full Paper on arXiv**](https://arxiv.org/abs/2202.11208)

## 🔄 Evolution & Maintenance
This repository serves as the modernized, actively maintained successor to [AirlineEmissionCalculations](https://github.com/landonbutler/AirlineEmissionCalculations/tree/main), originally developed by Landon G. Butler. 

### Key Updates for 2026

* **Temporal Modernization (2021–2026):** Fully migrated from 2021 baselines to 2026-current data streams (BTS/FAA), ensuring the framework is calibrated to the latest industry metrics and policy standards.
* **Modular Performance:** Transitioned to a decoupled, modular processing pipeline. By isolating dataset handling, the toolkit now achieves significantly higher computational speed and data reliability compared to monolithic legacy approaches.
* **Reproducibility:** Updated dependencies and validated end-to-end pipelines, ensuring that findings meet the rigorous standards required by external auditors and policymakers.

## Repository Structure
- `src/` – Core modules for emissions calculation and data fusion.
- `data/` – Instructions on downloading open-source data for emissions calculation provided by US and European federal agencies.
- `viz/` – Visualization scripts for building the interactive emissions map.
- `examples/` – Example scripts for single flights, monthly batches, and city-pair analysis.

## Getting Started

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

## Visualization

```bash
# Build the interactive emissions map (generates docs/index.html)
python viz/build_viz.py

# Force-refresh the airport coordinates cache
python viz/build_viz.py --refresh
```

`viz/build_viz.py` reads `results/OnTimeEmissions{year}_{month}.csv`, downloads US airport coordinates from OurAirports (cached at `viz/airports.csv`), aggregates emissions by route and airport, and writes a self-contained Plotly HTML to `docs/index.html`.

To publish: enable GitHub Pages in repo Settings → Pages → Source: main branch, `/docs` folder.

## Architecture

### Pipeline (`src/bts.py` → `src/faa.py` → `src/icao.py` → `src/bada.py` → `src/calculate_emissions.py`)

Each module is independent and returns a DataFrame:

- **`bts.py`** — loads a BTS on-time CSV for a given year/month, keeps `tail_number`, `air_time`, `taxi_in`, `taxi_out`, `origin`, `dest`, `origin_city`, `dest_city`, `distance_miles`; drops cancelled rows.
- **`faa.py`** — joins FAA `MASTER.txt` → `ENGINE.txt` → `ACFTREF.txt` to produce a tail → `(engine_model, faa_engine_code, mfr_mdl, aircraft_mfr, aircraft_model, seats)` mapping.
- **`icao.py`** — reads ICAO EEDB v32, matches each FAA engine code to one or more ICAO UIDs via a 4-tier name cascade (exact → strip-series → prefix → slash-stripped) plus a manual override table. Averages emission indices across matched variants and returns one row per `faa_engine_code` with kg/s rates for HC, CO, NOx, CO2 at each LTO phase.
- **`bada.py`** — maps FAA aircraft types to BADA standard codes via regex rules and interpolates CCD emissions (fuel, CO2, NOx, SOx, H2O, CO, HC) from the Engine Fuel Consumption table.
- **`calculate_emissions.py`** — left-joins BTS → FAA → ICAO → BADA, computes LTO and CCD emissions for every flight, and outputs `co2_lto`, `co2_ccd`, `co2_total`, `co2e_total` (plus HC, CO, NOx breakdowns). Final output retains ~88.7% of original BTS rows.

### Key Domain Constants

| Constant | Value | Notes |
|---|---|---|
| ICAO LTO phase durations | T/O = 42 s, C/O = 132 s, App = 240 s | Idle = actual BTS taxi times |
| CO2 derivation | `fuel_flow (kg/s) × 3.16` | Carbon mass balance of Jet-A |
| `time_ccd` | `air_time (min) − (42 + 132 + 240) / 60` | Flight time above 3,000 ft |
| GWPs (CO2-equivalent) | HC = 84, CO = 1.57, NOx = 298 | Used for `co2e_total` |

## Data Sources

See `data/SOURCES.md` for download links. Expected files in `data/`:

| File | What it is |
|---|---|
| `On_Time_*_{year}_{month}.csv` | BTS on-time performance (one per month) |
| `ReleasableAircraft/MASTER.txt` | FAA registry: tail → engine code + aircraft model code |
| `ReleasableAircraft/ENGINE.txt` | FAA engine reference: code → model name |
| `ReleasableAircraft/ACFTREF.txt` | FAA aircraft reference: model code → manufacturer, model, seats |
| `edb-emissions-databank_v32__web_.xlsx` | ICAO EEDB v32: certified LTO emission indices per engine UID |
| `Engine Fuel Consumption.xlsx` | BADA CCD table: fuel + emissions by aircraft type and flight duration |

## Citation
If you utilize this toolkit in your research or policy analysis, please cite our ICRAT methodology:

```bibtex
@inproceedings{eskenazi2022democratizing,
  title={Democratizing aviation emissions estimation: Development of an open-source, data-driven methodology},
  author={Eskenazi, Andy G and Butler, Landon G and Joshi, Arnav P and Ryerson, Megan S},
  booktitle={10th International Conference on Research in Air Transportation (ICRAT)},
  year={2022}
}
