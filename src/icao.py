import numpy as np
import pandas as pd
from pathlib import Path
from .faa import _load_engine_ref

DATA_DIR = Path(__file__).parent.parent / 'data'

_CO2_PER_KG_FUEL = 3.16  # kg CO2 per kg jet-A fuel (ICAO standard)

# Maps FAA engine names to ICAO search strings (exact name or prefix for family average).
# Each entry is documented with the assumption being made.
_MANUAL_NAME_OVERRIDES = {
    # --- V2500 family ---
    # FAA uses "V2500SERIES" as a generic catch-all; no specific variant is known.
    # Assumption: average emissions across ALL IAE V25xx variants in ICAO (V2500-A1
    # through V2533-A5). This is a reasonable surrogate for the A320-family fleet.
    # Source: ICAO EEDB v32 contains 27 V25xx entries (UIDs 1IA001–04P10IA027).
    'v2500series':    'v25',
    # FAA "V2500E-A5" omits the thrust-class digit used in ICAO naming.
    # Assumption: mapped to V2527E-A5 (the standard enhanced A5 variant, 26,500 lbf).
    # Source: IAE TCDS EASA.IM.E.069 confirms V2527E-A5 is the principal E-series variant.
    'v2500e-a5':      'v2527e-a5',

    # --- PW4000 family ---
    # FAA uses "PW4000 SER" as a generic catch-all; no specific thrust rating is known.
    # Assumption: average emissions across ALL PW4xxx variants in ICAO (PW4056–PW4170,
    # covering 94", 100", and 112" fan-diameter series used on 747/767/777/A330).
    # Source: ICAO EEDB v32 contains 43 PW4xxx entries (UIDs 1PW041–12PW102).
    # Note: PW4000 IS in the ICAO databank; the matching failure was purely a naming mismatch.
    'pw4000 ser':     'pw4',

    # --- RB211 / Trent naming split ---
    # Rolls-Royce rebranded high-bypass variants of the RB211 as "Trent" for commercial use,
    # but FAA still registers them under the RB211 designation. ICAO uses the Trent name.
    # Source: RR product naming history; ICAO EEDB v32 has no "RB211 772" entry but does
    # have "Trent 772" and "Trent 892" covering those thrust classes.
    'rb211 772-60':   'trent 772',
    'rb211 772b-60':  'trent 772',
    'rr772b-60':      'trent 772',
    'rb211-892-17':   'trent 892',
    'rb211 892b-17':  'trent 892',

    # RB211-535 and RB211-524 variants: FAA appends certification suffixes not used by ICAO.
    # Assumption: strip suffix and prefix-match to the nearest ICAO entry.
    'rb211-535e437':  'rb211-535e4',   # → ICAO RB211-535E4 / RB211-535E4B
    'rb211535e4b37':  'rb211-535e4b',  # → ICAO RB211-535E4B
    'rb211-524h-36':  'rb211-524h',    # → ICAO RB211-524H / RB211-524H-T
    'rb211-524ht36':  'rb211-524h-t',  # → ICAO RB211-524H-T
    'rb211-524g-22':  'rb211-524g',    # → ICAO RB211-524G / RB211-524G-T
    'rb-211 series':  'rb211',         # → average all RB211-xxx variants

    # --- LEAP-1A33 ---
    # FAA uses LEAP-1A33 as a standalone designator; ICAO groups it with related variants
    # under a single combined certification entry.
    # Assumption: mapped to the ICAO combined entry LEAP-1A35A/33/33B2/32/30.
    'leap-1a33':      'leap-1a35a/33',

    # --- BR700 family ---
    # FAA uses generic "BR 700 SERIES" with a space and no hyphen; ICAO uses "BR700-7xx" format.
    # Assumption: average all BR700 variants (710/715/725/730 series) covering 737BBJ, 717, Global Express.
    'br 700 series':  'br700',
    # FAA drops the internal hyphen in the thrust-class suffix (e.g. A130 vs A1-30).
    # Source: ICAO EEDB v32 uses BR700-715A1-30, B1-30, C1-30 for the 717-200 fleet.
    'br700-715a130':  'br700-715a1-30',
    'br700-715b130':  'br700-715b1-30',
    'br700-715c130':  'br700-715c1-30',

    # --- CF34-3B1 ---
    # FAA uses "CF34-3B1" as a standalone designator; ICAO combines it with the -3B base
    # variant under "CF34-3B/-3B1". Prefix-match to "cf34-3b" covers both.
    'cf34-3b1':       'cf34-3b',

    # --- AE 3007 family ---
    # FAA inserts a space ("AE 3007A") that ICAO omits ("AE3007A"). Simple name normalisation.
    'ae 3007a':       'ae3007a',
    'ae 3007a1p':     'ae3007a1p',

    # --- PW1500G (Geared Turbofan, A220) ---
    # FAA uses generic "PW1500G SER" with no thrust class; ICAO lists individual variants
    # PW1519G / PW1521G / PW1524G / PW1525G. Averaging all is appropriate for a fleet-level model.
    # FAA also uses "PW1521G SERIE" and "PW1524G SERIE" for specific variants; strip the suffix.
    'pw1500g ser':    'pw15',
    'pw1521g serie':  'pw1521g',
    'pw1524g serie':  'pw1524g',

    # --- Trent 772B-60 ---
    # FAA appends a "-60" certification suffix not used by ICAO.
    # Distinct from rb211 772b-60 override above; this entry already uses the Trent brand name.
    'trent 772b-60':  'trent 772',

    # --- Trent 7000 (A330neo) ---
    # FAA uses "TRENT 7000-72" with a space; ICAO uses "Trent7000-72" without a space.
    'trent 7000-72':  'trent7000-72',

    # --- TAY family ---
    # FAA appends certification suffixes (-54, -8) not used by ICAO.
    # TAY MK 610-8 is the original certification name; ICAO updated designation is TAY Mk611-8.
    # Source: RR Tay certification history; Mk610 and Mk611 are the same core engine.
    'tay 651-54':     'tay 651',
    'tay mk 610-8':   'tay mk611-8',

    # --- RB211-22 ---
    # FAA uses "RB-211-22" with a hyphen after RB; ICAO uses "RB211-22B".
    'rb-211-22':      'rb211-22b',

    # --- Trent 892 / Trent 800 ---
    # FAA uses a hyphen "TRENT-892" instead of the ICAO space "Trent 892".
    'trent-892':      'trent 892',
    # FAA uses the family brand name "TRENT 800"; ICAO lists individual variants
    # Trent 875/877/884/892/895 (all 777 engines). Averaging across the family is appropriate.
    'trent 800':      'trent 8',

    # --- PW4052 ---
    # PW4052 (49,000 lbf) is a lower-thrust variant of the PW4000 94" fan used on early 767-200ER.
    # ICAO EEDB v32 does not have a PW4052 entry; nearest certified variant is PW4056 (56,000 lbf).
    # Assumption: PW4056 emission indices are used as a surrogate — same combustor design, ~8% thrust delta.
    'pw4052':         'pw4056',

    # --- CFM56-7B27E variants ---
    # FAA concatenates the ICAO slash-separated variant suffix (e.g. "B3" instead of "/B3").
    # Prefix-matching to "cfm56-7b27e" averages across all /B1, /B3, /F variants.
    'cfm56-7b27eb3':  'cfm56-7b27e',
}


# Return (list_of_uids, match_type) for a FAA engine model name.
# Tries in order: exact -> strip-series-suffix -> prefix -> slash-stripped -> no_match.
def _match_engine_to_icao(faa_model, icao_ids_lower, icao_df):
    name = str(faa_model).strip().lower()

    if name in _MANUAL_NAME_OVERRIDES:
        name = _MANUAL_NAME_OVERRIDES[name]

    # Tier 1: exact — e.g. FAA 'CFM56-7B27E' == ICAO 'CFM56-7B27E'
    mask = icao_ids_lower == name
    if mask.any():
        return icao_df.loc[mask, 'UID No'].tolist(), 'exact'

    # Tier 2: strip trailing ' series' / ' ser' then prefix match
    # e.g. FAA 'CFM56-5B series' -> strip -> 'CFM56-5B' matches ICAO 'CFM56-5B4', 'CFM56-5B6', ...
    for suffix in (' series', ' ser'):
        if name.endswith(suffix):
            norm = name[: -len(suffix)].strip()
            mask = icao_ids_lower.str.startswith(norm)
            if mask.any():
                return icao_df.loc[mask, 'UID No'].tolist(), 'strip_series'
            break

    # Tier 3: prefix — FAA name is a prefix of the ICAO name
    # e.g. FAA 'CFM56-7B27' matches ICAO 'CFM56-7B27A', 'CFM56-7B27B', 'CFM56-7B27E', ...
    mask = icao_ids_lower.str.startswith(name)
    if mask.any():
        return icao_df.loc[mask, 'UID No'].tolist(), 'prefix'

    # Tier 4: strip everything after '/' then prefix match
    # e.g. FAA 'LEAP-1A35A/33' -> strip -> 'LEAP-1A35A' matches ICAO 'LEAP-1A35A/33/33B2/32/30'
    if '/' in name:
        prefix = name.split('/')[0]
        mask = icao_ids_lower.str.startswith(prefix)
        if mask.any():
            return icao_df.loc[mask, 'UID No'].tolist(), 'slash_stripped'

    return [], 'no_match'


# Compute per-phase kg/s emission rates from a single ICAO EEDB row.
# Returns None if any fuel flow or EI value is null — incomplete certification data.
def _rates_from_icao_row(row):
    ff_to   = row['Fuel Flow T/O (kg/sec)']
    ff_co   = row['Fuel Flow C/O (kg/sec)']
    ff_app  = row['Fuel Flow App (kg/sec)']
    ff_idle = row['Fuel Flow Idle (kg/sec)']

    ei_cols = [
        row['HC EI T/O (g/kg)'],  row['HC EI C/O (g/kg)'],  row['HC EI App (g/kg)'],  row['HC EI Idle (g/kg)'],
        row['CO EI T/O (g/kg)'],  row['CO EI C/O (g/kg)'],  row['CO EI App (g/kg)'],  row['CO EI Idle (g/kg)'],
        row['NOx EI T/O (g/kg)'], row['NOx EI C/O (g/kg)'], row['NOx EI App (g/kg)'], row['NOx EI Idle (g/kg)'],
        ff_to, ff_co, ff_app, ff_idle,
    ]
    if any(pd.isna(v) for v in ei_cols):
        return None

    def rate(ei, ff):
        return float(ei) * float(ff) / 1000.0

    return {
        # HC, CO, NOx are physically measured in ICAO certification tests as emission indices (g/kg fuel).
        # Convert to kg/s: EI (g/kg) × fuel_flow (kg/s) / 1000 = emission_rate (kg/s)
        'HC T/O (kg/s)':           rate(row['HC EI T/O (g/kg)'],  ff_to),
        'HC C/O (kg/s)':           rate(row['HC EI C/O (g/kg)'],  ff_co),
        'HC App (kg/s)':           rate(row['HC EI App (g/kg)'],   ff_app),
        'HC Idle (kg/s)':          rate(row['HC EI Idle (g/kg)'],  ff_idle),
        'CO T/O (kg/s)':           rate(row['CO EI T/O (g/kg)'],  ff_to),
        'CO C/O (kg/s)':           rate(row['CO EI C/O (g/kg)'],  ff_co),
        'CO App (kg/s)':           rate(row['CO EI App (g/kg)'],   ff_app),
        'CO Idle (kg/s)':          rate(row['CO EI Idle (g/kg)'],  ff_idle),
        'NOx T/O (kg/s)':          rate(row['NOx EI T/O (g/kg)'], ff_to),
        'NOx C/O (kg/s)':          rate(row['NOx EI C/O (g/kg)'], ff_co),
        'NOx App (kg/s)':          rate(row['NOx EI App (g/kg)'],  ff_app),
        'NOx Idle (kg/s)':         rate(row['NOx EI Idle (g/kg)'], ff_idle),
        # CO2 is not measured — it is derived from fuel burn via carbon mass balance of jet-A:
        # fuel_flow (kg/s) × 3.16 (kg CO2/kg jet-A) = CO2 rate (kg/s)
        'CO2 T/O (kg/s)':          float(ff_to)   * _CO2_PER_KG_FUEL,
        'CO2 C/O (kg/s)':          float(ff_co)   * _CO2_PER_KG_FUEL,
        'CO2 App (kg/s)':          float(ff_app)  * _CO2_PER_KG_FUEL,
        'CO2 Idle (kg/s)':         float(ff_idle) * _CO2_PER_KG_FUEL,
    }


# Load the ICAO Engine Exhaust Emissions Databank (EEDB v32) and return one row
# per unique FAA engine code with averaged LTO emission rates across all ICAO UIDs
# that matched the engine name.
#
# Returns one row per faa_engine_code with columns:
#   - faa_engine_code    : int — FAA engine code, e.g. 13078
#   - match_type         : str — how the ICAO match was made, e.g. 'exact', 'prefix', 'no_match'
#   - HC T/O (kg/s)      : float — HC emission rate at takeoff
#   - HC C/O (kg/s)      : float — HC emissions rate at climb-out
#   - HC App (kg/s)      : float — HC emissions rate at approach
#   - HC Idle (kg/s)     : float — HC emissions rate at idle (taxi)
#   - CO T/O (kg/s) ... CO2 Idle (kg/s) : float — same structure for CO, NOx, Fuel Flow, CO2
def build_lto_rates() -> pd.DataFrame:
    # Read in ICAO LTO emissions data and clean engine model information
    icao_df = pd.read_excel(
        DATA_DIR / 'edb-emissions-databank_v32__web_.xlsx',
        sheet_name='Gaseous Emissions and Smoke',
    )
    icao_df['_id_lower'] = icao_df['Engine Identification'].astype(str).str.strip().str.lower()
    icao_ids_lower = icao_df['_id_lower']

    # Map FAA engine code -> engine name; name is used to match ICAO, code to join back to tails
    engine_ref = _load_engine_ref()
    code_to_name = dict(zip(engine_ref['faa_engine_code'], engine_ref['engine_model']))

    # Match each FAA engine name to its corresponding ICAO engine entry
    rows = []
    for faa_code, engine_name in code_to_name.items():
        uids, match_type = _match_engine_to_icao(engine_name, icao_ids_lower, icao_df)

        # no ICAO match — record the code so coverage gaps are visible in the output
        if not uids:
            rows.append({'faa_engine_code': faa_code, 'match_type': match_type})
            continue

        rates_list = [
            _rates_from_icao_row(icao_df[icao_df['UID No'] == uid].iloc[0])
            for uid in uids
        ]
        rates_list = [r for r in rates_list if r is not None]
        if not rates_list:
            rows.append({'faa_engine_code': faa_code, 'match_type': 'no_match'})
            continue
        avg_rates = {k: np.mean([r[k] for r in rates_list]) for k in rates_list[0]}
        rows.append({'faa_engine_code': faa_code, 'match_type': match_type, **avg_rates})

    return pd.DataFrame(rows)
