# Aviation Emissions Modeling Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Citation Count](https://img.shields.io/badge/Cited%20by-9-green.svg)](https://scholar.google.com/scholar?oi=bibs&hl=en&cites=7178136927124764561&as_sdt=5)

**An open-source, data-driven framework for system-wide aviation emissions accounting, designed to support transparency in climate impact assessment and U.S. infrastructure optimization.**

---

## 🏛️ Alignment with U.S. National Priorities
This toolkit provides the high-fidelity computational framework required to support and execute current federal decarbonization mandates:

* **[U.S. Aviation Climate Action Plan](https://www.transportation.gov/priorities/climate-change/us-aviation-climate-action-plan):** This toolkit directly supports the 2050 Net-Zero goal for the U.S. aviation sector by providing the reproducible emissions accounting methodology necessary for industry-wide adoption.
* **[U.S. National Blueprint for Transportation Decarbonization](https://www.energy.gov/eere/us-national-blueprint-transportation-decarbonization):** By standardizing emissions estimation, this toolkit aligns with the Blueprint’s whole-of-government strategy to transform the transportation sector and eliminate greenhouse gas emissions by 2050.

## 🏆 Recognition & Impact
This methodology originated from award-winning research at the **10th International Conference on Research in Air Transportation (ICRAT)**, co-organized by the FAA and EUROCONTROL.

> 🏆 **Best Paper Award: Economics, Policy, and Equity**
> *Democratizing Aviation Emissions Estimation: Development of an Open-Source, Data-Driven Methodology* > **Authors:** Andy G. Eskenazi, Landon G. Butler, **Arnav P. Joshi**, Megan S. Ryerson
> [**View Official ICRAT Award Results**](https://www.icrat.org/previous-conferences/10th-international-conference/papers/)

Our methodology has been formally adopted and cited by **9 independent academic publications**, demonstrating its role as a recognized standard in environmental accounting for the aviation sector.

## 🔄 Evolution & Maintenance
This repository serves as the modernized, actively maintained successor to [AirlineEmissionCalculations](https://github.com/landonbutler/AirlineEmissionCalculations/tree/main), originally developed by Landon G. Butler. 

**Key Updates for 2026:**
* **Data Modernization:** Updated to process the latest available BTS and FAA data streams, ensuring alignment with current industry standards.
* **Modular Architecture:** Refactored for scalability, allowing researchers to integrate disparate datasets (e.g., ICAO Engine Emissions Databank, EUROCONTROL BADA) with minimal overhead.
* **Reproducibility:** Updated dependencies and added end-to-end notebooks, ensuring that findings can be validated by external auditors and policymakers.

## Repository Structure
- `src/` – Core modules for emissions calculation and data fusion.
- `examples/` – Runnable notebooks demonstrating reproducible emissions estimation.
- `docs/` – Methodology documentation aligned with established aviation climate research.

## Citation
If you utilize this toolkit in your research or policy analysis, please cite our ICRAT methodology:

```bibtex
@inproceedings{eskenazi2022democratizing,
  title={Democratizing aviation emissions estimation: Development of an open-source, data-driven methodology},
  author={Eskenazi, Andy G and Butler, Landon G and Joshi, Arnav P and Ryerson, Megan S},
  booktitle={10th International Conference on Research in Air Transportation (ICRAT)},
  year={2022}
}
