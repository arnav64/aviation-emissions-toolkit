import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'new_data'

# Load BTS Airline On-Time Performance data for a given year and month.
#
# Source: Bureau of Transportation Statistics Transtats database.
# URL: https://transtats.bts.gov/PREZIP/
#      On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip
#
# Only the four columns needed for emissions calculation are kept:
#   - tail_number : str   — aircraft tail number, e.g. 'N815DN'
#   - air_time    : float — actual minutes airborne (wheels-off to wheels-on), e.g. 124.0
#   - taxi_out    : float — minutes taxiing from gate to wheels-off, e.g. 15.0
#   - taxi_in     : float — minutes taxiing from wheels-on to gate, e.g. 7.0
#
# Rows missing air_time (cancelled / diverted flights) are dropped because
# there is no meaningful emissions calculation without a flight duration.
def load_bts_ontime(year: int, month: int) -> pd.DataFrame:
    csv_name = (
        f"On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)"
        f"_{year}_{month}.csv"
    )
    path = DATA_DIR / csv_name
    if not path.exists():
        raise FileNotFoundError(
            f"BTS on-time CSV not found at {path}.\n"
            f"Run batch.py or download manually from BTS Transtats."
        )

    df = pd.read_csv(path, usecols=['Tail_Number', 'AirTime', 'TaxiIn', 'TaxiOut'], low_memory=False)
    df = df.dropna(subset=['AirTime'])
    df = df.rename(columns={
        'Tail_Number': 'tail_number',
        'AirTime':     'air_time',
        'TaxiIn':      'taxi_in',
        'TaxiOut':     'taxi_out',
    })
    df['tail_number'] = df['tail_number'].astype(str).str.strip()
    return df.reset_index(drop=True)
