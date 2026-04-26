# Aviation Emissions Modeling Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Citation Count](https://img.shields.io/badge/Cited%20by-9-green.svg)](https://scholar.google.com/scholar?oi=bibs&hl=en&cites=7178136927124764561&as_sdt=5)

**An open-source, data-driven framework for system-wide aviation emissions accounting, designed to support transparency in climate impact assessment and U.S. infrastructure optimization.**

---

## 🏛️ Alignment with U.S. National Priorities
This toolkit provides the high-fidelity computational framework required to monitor and execute the **U.S. Aviation Climate Action Plan’s 2050 Net-Zero mandate**. By enabling reproducible, system-wide emissions tracking, this project supports:
* **The U.S. National Blueprint for Transportation Decarbonization:** Providing empirical evidence for net-zero policy decisions.
* **DOT/FAA Sustainability Goals:** Enhancing transparency in carbon and non-CO2 climate impact monitoring for the domestic aviation fleet.

## 🏆 Recognition & Impact
This methodology originated from award-winning research at the **10th International Conference on Research in Air Transportation (ICRAT)**, co-organized by the FAA and EUROCONTROL.

> 🏆 **Best Paper Award: Economics, Policy, and Equity**
> *Democratizing Aviation Emissions Estimation: Development of an Open-Source, Data-Driven Methodology* > **Authors:** Andy G. Eskenazi, Landon G. Butler, **Arnav P. Joshi**, Megan S. Ryerson.

Our methodology has been formally adopted and cited by **9 independent academic publications**, demonstrating its role as a recognized standard in environmental accounting for the aviation sector.

## 🔄 Evolution & Maintenance
This repository serves as the modernized, actively maintained successor to previous open-source research work in aviation emissions estimation (originally initiated by Landon G. Butler). 

**Key Updates for 2026:**
* **Data Modernization:** Updated to process the latest available BTS and FAA data streams.
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
