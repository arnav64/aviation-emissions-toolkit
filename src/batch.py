"""
Legacy pipeline. Downloads a BTS on-time ZIP, runs per-flight emissions via emissions_calc.py,
and writes results to results/OnTimeEmissions{year}_{month}.csv.

Use calculate_emissions.py for the current vectorised pipeline.
"""
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import urllib3
from tqdm import tqdm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .emissions_calc import emissions_calc
from .reference_tables import load_reference_tables

RESULTS_DIR = Path(__file__).parent.parent / 'results'


def _download_bts(year, month):
    url = (f"https://transtats.bts.gov/PREZIP/"
           f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip")
    zip_path = RESULTS_DIR / f"On_Time_{year}_{month}.zip"
    print(f"Downloading BTS on-time data for {year}-{month:02d}...")
    r = requests.get(url, allow_redirects=True, verify=False)
    r.raise_for_status()
    zip_path.write_bytes(r.content)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(RESULTS_DIR)
    csv_name = (f"On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)"
                f"_{year}_{month}.csv")
    return RESULTS_DIR / csv_name


def _run_batch(on_time, eng_table_dict, lto_table_dict, ccd_table, backup_dict):
    cols = {
        'Total CO2': [], 'Total CO2E': [], 'Number Seats': [],
        'Origin LTO CO2': [], 'Origin LTO CO2e': [],
        'Destination LTO CO2': [], 'Destination LTO CO2e': [],
        'Total_HC_lto': [], 'Total_CO_lto': [], 'Total_NOx_lto': [], 'Total_CO2_lto': [],
        'Total_CO2_ccd': [], 'Total_NOx_ccd': [], 'Total_SOx_ccd': [],
        'Total_H2O_ccd': [], 'Total_CO_ccd': [], 'Total_HC_ccd': [],
    }

    for _, row in tqdm(on_time.iterrows(), total=len(on_time)):
        tail = row['Tail_Number']
        if tail in eng_table_dict and not pd.isna(row['AirTime']):
            faa_code = eng_table_dict[tail]['FAA Engine Code']
            airplane = eng_table_dict[tail]['Standard Code']
            time_takeoff  = 42
            time_climb    = 132
            time_approach = 240
            time_taxi_in  = 60 * row['TaxiIn']
            time_taxi_out = 60 * row['TaxiOut']
            time_ccd = row['AirTime'] - (time_takeoff + time_climb + time_approach) / 60

            result = emissions_calc(faa_code, airplane, time_takeoff, time_climb, time_approach,
                                    time_taxi_in, time_taxi_out, time_ccd,
                                    lto_table_dict, ccd_table, backup_dict)

            (co2, co2e, orig, orig_eq, dest, dest_eq,
             hc_lto, co_lto, nox_lto, co2_lto,
             co2_ccd, nox_ccd, sox_ccd, h2o_ccd, co_ccd, hc_ccd) = result

            cols['Total CO2'].append(co2)
            cols['Total CO2E'].append(co2e)
            cols['Number Seats'].append(eng_table_dict[tail]['Number of Seats'])
            cols['Origin LTO CO2'].append(orig)
            cols['Origin LTO CO2e'].append(orig_eq)
            cols['Destination LTO CO2'].append(dest)
            cols['Destination LTO CO2e'].append(dest_eq)
            cols['Total_HC_lto'].append(hc_lto)
            cols['Total_CO_lto'].append(co_lto)
            cols['Total_NOx_lto'].append(nox_lto)
            cols['Total_CO2_lto'].append(co2_lto)
            cols['Total_CO2_ccd'].append(co2_ccd)
            cols['Total_NOx_ccd'].append(nox_ccd)
            cols['Total_SOx_ccd'].append(sox_ccd)
            cols['Total_H2O_ccd'].append(h2o_ccd)
            cols['Total_CO_ccd'].append(co_ccd)
            cols['Total_HC_ccd'].append(hc_ccd)
        else:
            for key in cols:
                cols[key].append(np.nan)

    for col, values in cols.items():
        on_time[col] = values
    return on_time


def run(year, month):
    RESULTS_DIR.mkdir(exist_ok=True)
    csv_path = _download_bts(year, month)
    print("Reading into DataFrame...")
    on_time = pd.read_csv(csv_path, low_memory=False)
    print("Loading reference tables...")
    lto_table_dict, ccd_table, eng_table_dict, backup_dict = load_reference_tables()
    print("Calculating emissions...")
    result = _run_batch(on_time, eng_table_dict, lto_table_dict, ccd_table, backup_dict)
    out_path = RESULTS_DIR / f"OnTimeEmissions{year}_{month}.csv"
    result.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")
    return result
