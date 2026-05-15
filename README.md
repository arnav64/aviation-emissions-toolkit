# Aviation Emissions Modeling Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Citation Count](https://img.shields.io/badge/Cited%20by-9-green.svg)](https://scholar.google.com/scholar?oi=bibs&hl=en&cites=7178136927124764561&as_sdt=5)
[![Emissions Map](https://img.shields.io/badge/Live%20Map-View%20Visualization-orange)](https://arnav64.github.io/aviation-emissions-toolkit/)

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

### Key Updates for 2026

* **Temporal Modernization (2021–2026):** Fully migrated from 2021 baselines to 2026-current data streams (BTS/FAA), ensuring the framework is calibrated to the latest industry metrics and policy standards.
* **Modular Performance:** Transitioned to a decoupled, modular processing pipeline. By isolating dataset handling, the toolkit now achieves significantly higher computational speed and data reliability compared to monolithic legacy approaches.
* **AI-Native Research Workflow:** Integrated `claude.md` specifications, optimizing the codebase for interoperability with AI research agents, allowing for autonomous, large-scale emissions analysis.
* **Reproducibility:** Updated dependencies and validated end-to-end notebooks, ensuring that findings meet the rigorous standards required by external auditors and policymakers.

## Repository Structure
- `src/` – Core modules for emissions calculation and data fusion.
- `data/` – Instructions on downloading open-source data for emissions calculation provided by US and European federal agencies.

## Citation
If you utilize this toolkit in your research or policy analysis, please cite our ICRAT methodology:

```bibtex
@inproceedings{eskenazi2022democratizing,
  title={Democratizing aviation emissions estimation: Development of an open-source, data-driven methodology},
  author={Eskenazi, Andy G and Butler, Landon G and Joshi, Arnav P and Ryerson, Megan S},
  booktitle={10th International Conference on Research in Air Transportation (ICRAT)},
  year={2022}
}
