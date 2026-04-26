import re
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / 'data'

# Rules: (mfr_pattern, model_pattern, bada_standard_code)
# Applied in order; first match wins. Both patterns are matched case-insensitively via re.search.
# More specific rules must appear before broader ones for the same family.
_BADA_RULES = [
    # --- Boeing narrow-body ---
    # MAX variants: FAA stores them as exactly '737-8' / '737-9' with no customer suffix.
    # Must come before the CEO series rules below, which also start with '737-8' / '737-9'.
    ('boeing', r'^737-8$',              7378),
    ('boeing', r'^737-9$',              7379),
    ('boeing', r'^737-2',               737200),
    ('boeing', r'^737-3',               737300),
    ('boeing', r'^737-4',               737400),
    ('boeing', r'^737-5',               737500),
    ('boeing', r'^737-6',               737600),
    ('boeing', r'^737-7',               737700),
    ('boeing', r'^737-8',               737800),
    ('boeing', r'^737-9',               737900),
    ('boeing', r'^727-1',               727100),
    ('boeing', r'^727-2',               727200),
    ('boeing', r'^717-2',               717200),

    # --- Boeing wide-body ---
    # 747SP uses 'SP' in the model name; must come before the series-digit rules.
    ('boeing', r'^747.*sp',             747100),
    ('boeing', r'^747-1',               747100),
    ('boeing', r'^747-2',               747200),
    ('boeing', r'^747-3',               747300),
    ('boeing', r'^747-4',               747400),
    ('boeing', r'^747-8',               747800),
    ('boeing', r'^757-2',               757200),
    ('boeing', r'^757-3',               757300),
    ('boeing', r'^767-2',               767200),
    ('boeing', r'^767-3',               767300),
    ('boeing', r'^767-4',               767400),
    # 777-300ER: FAA model has literal 'ER' suffix (e.g. '777-323ER'). Must come before
    # the generic 777-3xx rule so ER variants aren't mapped to the non-ER standard code.
    ('boeing', r'^777-3\S*er',          777301),
    ('boeing', r'^777-2',               777200),
    ('boeing', r'^777-3',               777300),
    ('boeing', r'^787-8',               787800),
    ('boeing', r'^787-(?:9|10)',         787900),

    # --- MD / Douglas family (Boeing after 1997 merger; also pre-merger MFR names) ---
    ('boeing|mcdonnell|douglas', r'^md-8\d',        80),
    ('boeing|mcdonnell|douglas', r'^md-90',         90),
    ('boeing|mcdonnell|douglas', r'^md-11',         11),
    # MD-10 is a DC-10 freighter conversion — same airframe, same BADA type.
    ('boeing|mcdonnell|douglas', r'^md-10|^dc-10',  10),
    ('boeing|mcdonnell|douglas', r'^dc-8',           8),

    # --- Airbus narrow-body ---
    ('airbus', r'^a318',                318100),
    ('airbus', r'^a319',                319100),
    # NEO variants carry an 'N' (or 'NX') suffix after the customer code, e.g. 'A320-251N'.
    # Must come before the CEO rules, which match on the family prefix alone.
    ('airbus', r'^a320-\d+nx?',         3202),
    ('airbus', r'^a320',                320200),
    ('airbus', r'^a321-\d+nx?',         3212),
    ('airbus', r'^a321',                321200),

    # --- Airbus wide-body ---
    ('airbus', r'^a300',                300600),
    ('airbus', r'^a310',                310300),
    # A330 NEO uses 9xx variant codes (e.g. 'A330-941'); must come before generic A330 rules.
    ('airbus', r'^a330-9',              330900),
    ('airbus', r'^a330-2',              330200),
    ('airbus', r'^a330-3',              330300),
    ('airbus', r'^a340-2',              340200),
    ('airbus', r'^a340-3',              340300),
    ('airbus', r'^a340-5',              340500),
    ('airbus', r'^a340-6',              340600),
    ('airbus', r'^a350',                350900),
    ('airbus', r'^a380',                380800),

    # --- A220 (originally Bombardier C Series; FAA MFR is 'Airbus Canada' or 'C Series') ---
    ('airbus canada|c series', r'^bd-500', 220300),

    # --- Embraer regional jets ---
    # E135BJ is the Legacy 600 business jet — excluded via negative lookahead so it doesn't
    # accidentally match the ERJ-135 regional jet rule.
    ('embraer', r'^emb-?120',                       120),
    ('embraer', r'^(?:emb|erj)-?135(?!bj)',         135),
    ('embraer', r'^(?:emb|erj)-?145',               145),
    # E175 has no BADA entry; E170 is the same family and is the closest available surrogate.
    # Yabora Industria is a Brazilian sub-assembler that delivers E175s — same aircraft type.
    ('embraer|yabora', r'^erj.?17[05]|^emb.?170',   170),
    ('embraer', r'^erj.?190-?100|^erj.?190 100',    190),
    ('embraer', r'^erj.?190-?200|^erj.?195',        195),

    # --- Bombardier CRJ ---
    # FAA uses Canadair model designations, not the 'CRJ' marketing name.
    # CRJ-200 (2B19) has no BADA entry; CRJ-700 is used as a surrogate. The CRJ-200 seats
    # ~50 vs ~70 for the CRJ-700, but they share the same airframe lineage and cruise regime,
    # making CRJ-700 the closest available type. This slightly overestimates CCD emissions.
    ('bombardier|canadair', r'^cl-600-2b19',         700),   # CRJ-200 → CRJ-700 surrogate
    ('bombardier|canadair', r'^cl-600-2c1',          700),   # CRJ-700 and CRJ-700ER (2C10, 2C11)
    ('bombardier|canadair', r'^cl-600-2d24',         900),   # CRJ-900

    # --- De Havilland Q series (Dash 8) ---
    ('dehavilland|bombardier', r'^dhc-8',            8400),

    # --- ATR ---
    ('aerospatiale|atr', r'^atr.?42',                42),
    ('aerospatiale|atr', r'^atr.?72',                72),

    # --- Fokker ---
    ('fokker', r'^f.?100',                           1),

    # --- SAAB ---
    ('saab', r'^saab.?340',                          340),
]

_COMPILED_BADA_RULES = [
    (re.compile(mfr, re.IGNORECASE), re.compile(mdl, re.IGNORECASE), code)
    for mfr, mdl, code in _BADA_RULES
]


# Return the BADA standard code for an aircraft given its FAA manufacturer and model strings,
# or None if no rule matches.
#   - mfr  : str      — FAA manufacturer name from ACFTREF.txt, e.g. 'BOEING'
#   - model: str      — FAA model name from ACFTREF.txt, e.g. '737-932ER'
#   - returns: int|None — BADA standard code, e.g. 737900
def _derive_standard_code(mfr: str, model: str) -> Optional[int]:
    for mfr_pat, mdl_pat, code in _COMPILED_BADA_RULES:
        if mfr_pat.search(mfr) and mdl_pat.search(model):
            return code
    return None


# Source column names from Engine Fuel Consumption.xlsx mapped to output column names.
# Note: 'H20' uses a zero not the letter O; 'HC  (kg)' has two spaces — must match exactly.
_SRC_COLS = ['Fuel Burnt (kg)', 'CO2 (kg)', 'NOX (kg)', 'SOX (kg)', 'H20 (kg)', 'CO (kg)', 'HC  (kg)']
_OUT_COLS = ['fuel_ccd',        'co2_ccd',  'nox_ccd',  'sox_ccd',  'h2o_ccd',  'co_ccd',  'hc_ccd']


# Build a CCD emissions DataFrame indexed to merged, without modifying merged.
# Loads Engine Fuel Consumption.xlsx, interpolates each flight's emissions at its time_ccd,
# and returns a new DataFrame with the same index as merged.
#
# time_ccd = air_time - (lto_takeoff_s + lto_climbout_s + lto_approach_s) / 60, clipped at 0.
#
# Reads from merged (read-only):
#   - aircraft_mfr  : str   — FAA manufacturer name, e.g. 'BOEING'
#   - aircraft_model: str   — FAA model name, e.g. '737-932ER'
#   - air_time      : float — minutes airborne from BTS, e.g. 124.0
#
# Returns a DataFrame with columns:
#   - standard_code: int|None — BADA aircraft type derived from aircraft_mfr/aircraft_model, e.g. 737900
#   - time_ccd     : float    — CCD phase duration in minutes, e.g. 117.0
#   - fuel_ccd     : float    — fuel burned in CCD phase, kg, e.g. 5231.4
#   - co2_ccd      : float    — CO2 emitted in CCD phase, kg, e.g. 16530.0
#   - nox_ccd      : float    — NOx emitted in CCD phase, kg, e.g. 78.4
#   - sox_ccd      : float    — SOx emitted in CCD phase, kg, e.g. 4.4
#   - h2o_ccd      : float    — H2O emitted in CCD phase, kg, e.g. 6434.6
#   - co_ccd       : float    — CO emitted in CCD phase, kg, e.g. 14.2
#   - hc_ccd       : float    — HC emitted in CCD phase, kg, e.g. 2.1
# Rows with no standard_code match have NaN for all emission columns.
def build_ccd_emissions(
    merged: pd.DataFrame,
    lto_takeoff_s: float,
    lto_climbout_s: float,
    lto_approach_s: float,
) -> pd.DataFrame:
    # Load BADA CCD table and build a dict mapping each standard_code to its emissions rows sorted by duration.
    raw = pd.read_excel(DATA_DIR / 'Engine Fuel Consumption.xlsx')
    raw = raw[['Standard Code', 'Duration (min)'] + _SRC_COLS].fillna(0)
    raw = raw.sort_values(['Standard Code', 'Duration (min)'])
    ccd_lookup = {
        int(code): group.reset_index(drop=True)
        for code, group in raw.groupby('Standard Code')
    }

    # Build the output frame with standard_code (derived from aircraft type) and time_ccd (air_time minus LTO phases).
    lto_minutes = (lto_takeoff_s + lto_climbout_s + lto_approach_s) / 60
    out = pd.DataFrame(index=merged.index)
    out['standard_code'] = merged.apply(
        lambda r: _derive_standard_code(r['aircraft_mfr'], r['aircraft_model']), axis=1
    )
    out['time_ccd'] = (merged['air_time'] - lto_minutes).clip(lower=0)

    # Pre-fill all emission columns with NaN; rows with no standard_code match will stay NaN.
    for col in _OUT_COLS:
        out[col] = float('nan')

    # Iterate over each unique standard_code and interpolate all emission columns for that group of flights.
    for code, group_idx in out.groupby('standard_code', dropna=True).groups.items():
        code = int(code)
        if code not in ccd_lookup:
            continue
        ccd = ccd_lookup[code]
        durations = ccd['Duration (min)'].to_numpy()
        t = out.loc[group_idx, 'time_ccd'].to_numpy()
        
        # np.interp linearly interpolates each flight's time_ccd against the BADA duration checkpoints,
        # clamping to the first/last row for flights shorter or longer than the table range.
        for src, col in zip(_SRC_COLS, _OUT_COLS):
            out.loc[group_idx, col] = np.interp(t, durations, ccd[src].to_numpy())

    return out
