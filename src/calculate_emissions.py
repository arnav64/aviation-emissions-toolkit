"""
Step 1 & 2 of the emissions pipeline:
  1. Read BTS on-time performance data for a given year/month.
  2. Build a tail-number -> aircraft/engine mapping from the FAA registry.
  3. Merge the two so every flight row has the engine and aircraft info
     needed for emissions calculation.

Output is a DataFrame ready to be passed to the emissions calculator.
Flights whose tail number cannot be matched to a known engine and aircraft
type are flagged in a separate coverage report.
"""
import pandas as pd
from .bts import load_bts_ontime
from .faa import build_aircraft_mapping
from .icao import build_lto_rates
from .bada import build_ccd_emissions

# ICAO standard LTO phase durations in seconds.
LTO_TAKEOFF_S  = 42
LTO_CLIMBOUT_S = 132
LTO_APPROACH_S = 240

# Global warming potentials used to convert LTO pollutants to CO2-equivalent mass.
HC_GWP  = 84
CO_GWP  = 1.57
NOX_GWP = 298


# ---------------------------------------------------------------------------
# Step 3 — Merge and coverage report
# ---------------------------------------------------------------------------

# Merge BTS on-time flight data with the FAA aircraft/engine mapping.
#
# Returns a DataFrame where every row is a flight that has both the
# timing data needed (air_time, taxi_in, taxi_out) and the aircraft info
# needed (engine_model, seats) and CCD emissions (standard_code, co2_ccd, etc.).
#
# Flights whose tail number has no matching engine/aircraft record are
# written to results/coverage_report_{year}_{month}.csv for inspection.
def prepare_flights(year: int, month: int) -> pd.DataFrame:
    print(f"Loading BTS on-time data for {year}-{month:02d}...")
    flights = load_bts_ontime(year, month)
    n_bts = len(flights)
    print(f"  {n_bts:,} flights loaded")

    print("Building FAA aircraft/engine mapping...")
    mapping = build_aircraft_mapping()

    # Left join BTS onto FAA mapping. ~11.1% of flights will have no FAA match and are dropped.
    # Three reasons a tail may be missing from the FAA mapping:
    #   1. Tail not in MASTER.txt at all — foreign-registered aircraft on domestic routes,
    #      recently deregistered tails still appearing in BTS, or malformed tail numbers (e.g. '234NV').
    #   2. Tail in MASTER.txt but ENG MFR MDL is blank — no engine code, dropped during FAA load.
    #   3. Tail uses a non-N-number format — FAA registry only covers N-registered (US) aircraft.
    merged = flights.merge(mapping, on='tail_number', how='left')
    merged = merged.dropna(subset=['mfr_mdl'])
    print(f"  After FAA join: {len(merged):,} ({len(merged)/n_bts:.1%} of BTS, dropped {n_bts-len(merged):,})")

    print("Joining ICAO LTO emission rates...")
    lto = build_lto_rates()

    # Left join ICAO LTO rates onto the merged flights. An additional ~0.2% of flights are dropped.
    # These are engines in the FAA registry with no ICAO match — turboprops (e.g. PW150A, DART RDA-10),
    # engines below the ICAO 26.7 kN certification threshold, or engines with unknown/missing FAA names.
    # After both joins, ~88.7% of the original BTS flights are retained.
    merged = merged.merge(lto, on='faa_engine_code', how='left')
    merged = merged.dropna(subset=['HC T/O (kg/s)'])
    print(f"  After ICAO join: {len(merged):,} ({len(merged)/n_bts:.1%} of BTS, dropped {n_bts-len(merged):,})")

    print("Interpolating BADA CCD emissions...")
    ccd = build_ccd_emissions(merged, LTO_TAKEOFF_S, LTO_CLIMBOUT_S, LTO_APPROACH_S)

    # Left join BADA emissions onto the merged flights.
    # No rows dropped — every engine-matched tail has a BADA standard_code
    merged = merged.join(ccd)
    n_before_ccd = len(merged)
    merged = merged.dropna(subset=['co2_ccd'])
    print(f"  After BADA CCD join: {len(merged):,} ({len(merged)/n_bts:.1%} of BTS, dropped {n_before_ccd-len(merged):,})")

    print("Calculating LTO emissions...")
    # taxi_in/taxi_out from BTS are in minutes; phase durations are in seconds — convert idle to seconds.
    taxi_idle_s = (merged['taxi_in'] + merged['taxi_out']) * 60

    def _lto_kg(pollutant):
        return (
            LTO_TAKEOFF_S  * merged[f'{pollutant} T/O (kg/s)'] +
            LTO_CLIMBOUT_S * merged[f'{pollutant} C/O (kg/s)'] +
            LTO_APPROACH_S * merged[f'{pollutant} App (kg/s)'] +
            taxi_idle_s    * merged[f'{pollutant} Idle (kg/s)']
        )

    merged['hc_lto']  = _lto_kg('HC')
    merged['co_lto']  = _lto_kg('CO')
    merged['nox_lto'] = _lto_kg('NOx')
    merged['co2_lto'] = _lto_kg('CO2')

    merged['co2e_lto']   = HC_GWP * merged['hc_lto']  + CO_GWP * merged['co_lto']  + NOX_GWP * merged['nox_lto']  + merged['co2_lto']
    merged['co2e_ccd']   = HC_GWP * merged['hc_ccd']  + CO_GWP * merged['co_ccd']  + NOX_GWP * merged['nox_ccd']  + merged['co2_ccd']
    merged['co2_total']  = merged['co2_lto']  + merged['co2_ccd']
    merged['co2e_total'] = merged['co2e_lto'] + merged['co2e_ccd']

    return merged.reset_index(drop=True)


if __name__ == '__main__':
    flights = prepare_flights(2021, 9)
    print(f"\nSample output:")
    print(flights[['tail_number', 'engine_model', 'standard_code', 'air_time', 'co2_lto', 'co2_ccd', 'co2_total', 'co2e_total']].head(5).to_string(index=False))
