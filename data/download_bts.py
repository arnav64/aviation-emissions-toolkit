"""
Download BTS Airline On-Time Performance data for a given year and quarter.
Files are saved directly into the data/ directory, ready for the pipeline.

Usage:
    python data/download_bts.py <year> <quarter>
    python data/download_bts.py 2026 1    # downloads Jan, Feb, Mar 2026

Note: BTS typically publishes data 1-2 months after the month ends.
If a month is not yet available, the script will raise an HTTP error.
"""
import sys
import zipfile
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = Path(__file__).parent

QUARTER_MONTHS = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}


def download_quarter(year: int, quarter: int):
    for month in QUARTER_MONTHS[quarter]:
        url = (
            f"https://transtats.bts.gov/PREZIP/"
            f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
        )
        zip_path = DATA_DIR / f"bts_{year}_{month}.zip"

        print(f"Downloading {year}-{month:02d}...")
        r = requests.get(url, allow_redirects=True, verify=False)
        r.raise_for_status()

        zip_path.write_bytes(r.content)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(DATA_DIR)
        zip_path.unlink()

        csv = f"On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_{year}_{month}.csv"
        print(f"  Saved {csv}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python data/download_bts.py <year> <quarter>")
        sys.exit(1)

    year, quarter = int(sys.argv[1]), int(sys.argv[2])

    if quarter not in QUARTER_MONTHS:
        print("Quarter must be 1, 2, 3, or 4")
        sys.exit(1)

    download_quarter(year, quarter)
