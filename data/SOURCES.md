# Data Sources

Place all files listed below in this directory before running the pipeline.

---

## BTS On-Time Performance

**Used by:** `src/bts.py`  
**Download:** https://transtats.bts.gov/PREZIP/ or run `download_bts.py` (see below)

```
python data/download_bts.py <year> <quarter>
python data/download_bts.py 2026 1    # downloads Jan, Feb, Mar 2026
```

**Expected files** (one per month):
```
On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_{year}_{month}.csv
```

---

## FAA Aircraft Registration Database

**Used by:** `src/faa.py`  
**Download:** https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/releasable_aircraft_download

Download the full zip and extract into `ReleasableAircraft/`. Only three files are used:

**Expected files:**
```
ReleasableAircraft/MASTER.txt     — tail number → engine code + aircraft model code
ReleasableAircraft/ENGINE.txt     — engine code → engine model name
ReleasableAircraft/ACFTREF.txt    — aircraft model code → manufacturer, model, seats
```

---

## ICAO Engine Emissions Databank (EEDB)

**Used by:** `src/icao.py`  
**Download:** https://www.easa.europa.eu/en/domains/environment/icao-aircraft-engine-emissions-databank

Download the latest version of the databank (Excel). Update the filename in `src/icao.py` if the version number changes.

**Expected file:**
```
edb-emissions-databank_v32__web_.xlsx
```

---

## BADA Engine Fuel Consumption

**Used by:** `src/bada.py`  
**Download:** https://www.eurocontrol.int/model/bada (registration required)

**Expected file:**
```
Engine Fuel Consumption.xlsx
```
