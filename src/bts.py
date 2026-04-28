"""
Loads BTS Airline On-Time Performance data for a given year/month.
Source: https://transtats.bts.gov/PREZIP/
        On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip

Returns tail_number, air_time, taxi_out, taxi_in (all times in minutes),
plus origin and destination airport, city, and state.
Cancelled and diverted flights with no AirTime are dropped.
"""
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'

# Load BTS Airline On-Time Performance data for a given year and month.
#
# Source: Bureau of Transportation Statistics Transtats database.
# URL: https://transtats.bts.gov/PREZIP/
#      On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip
#
# Columns loaded from the BTS CSV:
#   - tail_number      : str   — aircraft tail number, e.g. 'N815DN'
#   - air_time         : float — actual minutes airborne (wheels-off to wheels-on), e.g. 124.0
#   - taxi_out         : float — minutes taxiing from gate to wheels-off, e.g. 15.0
#   - taxi_in          : float — minutes taxiing from wheels-on to gate, e.g. 7.0
#   - origin           : str   — origin airport IATA code, e.g. 'JFK'
#   - origin_city      : str   — origin city and state, e.g. 'New York, NY'
#   - origin_state     : str   — origin state abbreviation, e.g. 'NY'
#   - dest             : str   — destination airport IATA code, e.g. 'LAX'
#   - dest_city        : str   — destination city and state, e.g. 'Los Angeles, CA'
#   - dest_state       : str   — destination state abbreviation, e.g. 'CA'
#
# Rows missing air_time (cancelled / diverted flights) are dropped.
def load_bts_ontime(year: int, month: int) -> pd.DataFrame:
    csv_name = (
        f"On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)"
        f"_{year}_{month}.csv"
    )
    path = DATA_DIR / csv_name
    if not path.exists():
        raise FileNotFoundError(
            f"BTS on-time CSV not found at {path}.\n"
            f"Download manually from BTS Transtats or run: python data/download_bts.py <year> <quarter>"
        )

    df = pd.read_csv(
        path,
        usecols=['Tail_Number', 'AirTime', 'TaxiIn', 'TaxiOut',
                 'Origin', 'OriginCityName', 'OriginState',
                 'Dest', 'DestCityName', 'DestState'],
        low_memory=False,
    )
    df = df.dropna(subset=['AirTime'])
    df = df.rename(columns={
        'Tail_Number':    'tail_number',
        'AirTime':        'air_time',
        'TaxiIn':         'taxi_in',
        'TaxiOut':        'taxi_out',
        'Origin':         'origin',
        'OriginCityName': 'origin_city',
        'OriginState':    'origin_state',
        'Dest':           'dest',
        'DestCityName':   'dest_city',
        'DestState':      'dest_state',
    })
    df['tail_number'] = df['tail_number'].astype(str).str.strip()
    return df.reset_index(drop=True)
