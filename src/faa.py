import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'new_data'

# Load FAA MASTER.txt and return one row per tail with its FAA engine code
# and aircraft model code.
#   - tail_number    : str — N-prefixed tail, e.g. 'N815DN'
#   - faa_engine_code: int — joins to ENGINE.txt, e.g. 13078
#   - mfr_mdl        : str — joins to ACFTREF.txt, e.g. '138488K'
def _load_master() -> pd.DataFrame:
    df = pd.read_csv(
        DATA_DIR / 'ReleasableAircraft' / 'MASTER.txt',
        usecols=['N-NUMBER', 'ENG MFR MDL', 'MFR MDL CODE'],
        low_memory=False,
    )
    df['tail_number']     = 'N' + df['N-NUMBER'].astype(str).str.strip()
    df['faa_engine_code'] = pd.to_numeric(df['ENG MFR MDL'], errors='coerce')
    df['mfr_mdl']         = df['MFR MDL CODE'].astype(str).str.strip()
    df = df[['tail_number', 'faa_engine_code', 'mfr_mdl']].dropna(subset=['faa_engine_code'])
    df['faa_engine_code'] = df['faa_engine_code'].astype(int)
    return df


# Load FAA ENGINE.txt and return a mapping from FAA engine code to engine model name.
#   - faa_engine_code: int — primary key, e.g. 13078
#   - engine_model   : str — ICAO-matchable name, e.g. 'CFM56-7B27E'
def _load_engine_ref() -> pd.DataFrame:
    df = pd.read_csv(
        DATA_DIR / 'ReleasableAircraft' / 'ENGINE.txt',
        usecols=['CODE', 'MODEL'],
        low_memory=False,
    )
    df = df.rename(columns={'CODE': 'faa_engine_code', 'MODEL': 'engine_model'})
    df['faa_engine_code'] = df['faa_engine_code'].astype(int)
    df['engine_model']    = df['engine_model'].astype(str).str.strip()
    return df


# Load FAA ACFTREF.txt and return a mapping from aircraft model code to manufacturer, model, and seat count.
#   - mfr_mdl        : str — primary key, e.g. '138488K'
#   - aircraft_mfr   : str — manufacturer name, e.g. 'BOEING'
#   - aircraft_model : str — model name, e.g. '737-932ER'
#   - seats          : int — certified maximum seat count, e.g. 222
def _load_acftref() -> pd.DataFrame:
    df = pd.read_csv(
        DATA_DIR / 'ReleasableAircraft' / 'ACFTREF.txt',
        usecols=['CODE', 'MFR', 'MODEL', 'NO-SEATS'],
        low_memory=False,
    )
    df = df.drop_duplicates('CODE').rename(columns={
        'CODE':     'mfr_mdl',
        'MFR':      'aircraft_mfr',
        'MODEL':    'aircraft_model',
        'NO-SEATS': 'seats',
    })
    df['mfr_mdl']        = df['mfr_mdl'].astype(str).str.strip()
    df['aircraft_mfr']   = df['aircraft_mfr'].astype(str).str.strip()
    df['aircraft_model'] = df['aircraft_model'].astype(str).str.strip()
    return df


# Build a tail-number -> engine and aircraft mapping from the FAA registry.
#
# Joins MASTER -> ENGINE -> ACFTREF without filtering, so every registered tail
# is preserved. Returns:
#   - tail_number    : str — N-prefixed tail, e.g. 'N815DN'
#   - engine_model   : str — engine name from ENGINE.txt, e.g. 'CFM56-7B27E'
#   - faa_engine_code: int — FAA engine code, e.g. 13078
#   - mfr_mdl        : str — aircraft model code from MASTER.txt, e.g. '138488K'
#   - aircraft_mfr   : str — manufacturer name from ACFTREF.txt, e.g. 'BOEING'
#   - aircraft_model : str — model name from ACFTREF.txt, e.g. '737-932ER'
#   - seats          : int — certified maximum seat count, e.g. 222
def build_aircraft_mapping() -> pd.DataFrame:
    mapping = (
        _load_master()
        .merge(_load_engine_ref(), on='faa_engine_code', how='left')
        .merge(_load_acftref(),    on='mfr_mdl',         how='left')
    )
    return mapping[['tail_number', 'engine_model', 'faa_engine_code', 'mfr_mdl', 'aircraft_mfr', 'aircraft_model', 'seats']]
