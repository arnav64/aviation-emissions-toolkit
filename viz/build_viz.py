"""
Builds an interactive Plotly map of U.S. aviation emissions by origin-destination
airport pair. The map itself lives as the "Route Map" view inside
docs/dashboard.html (built by build_dashboard.py, which imports the functions
below); this script's own docs/map_standalone.html output is a standalone
fallback, not the published page.

Usage:
    python viz/build_viz.py                        # auto-detects newest results CSV
    python viz/build_viz.py --csv results/foo.csv  # use specific file
    python viz/build_viz.py --refresh              # re-download airport coordinates

Reads:   results/OnTimeEmissions*.csv (newest by default)
Fetches: viz/airports.csv (cached from OurAirports on first run)
Writes:  docs/map_standalone.html

Supports both pipeline formats:
  Legacy:  Origin, Dest, OriginCityName, DestCityName, Total CO2, Total CO2E
  Current: origin, dest, origin_city, dest_city, co2_total, co2e_total
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import requests

ROOT = Path(__file__).parent.parent
AIRPORTS_CSV = Path(__file__).parent / "airports.csv"
DOCS_DIR = ROOT / "docs"
OUTPUT_HTML = DOCS_DIR / "map_standalone.html"
RESULTS_DIR = ROOT / "results"

AIRPORTS_URL = "https://ourairports.com/data/airports.csv"

TOP_SIDEBAR = 15

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

# Light green → dark green sequential scale
GREEN_COLORSCALE = [
    [0.00, "#e8f5e9"],
    [0.25, "#a5d6a7"],
    [0.50, "#4caf50"],
    [0.75, "#2e7d32"],
    [1.00, "#1a3a1c"],
]


def find_latest_results() -> Path:
    candidates = sorted(RESULTS_DIR.glob("OnTimeEmissions*.csv"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print("ERROR: No OnTimeEmissions*.csv found in results/")
        print("Run: python -m src.calculate_emissions  or  python examples/monthly_batch.py")
        sys.exit(1)
    return candidates[0]


def label_from_csv(path: Path) -> str:
    name = path.stem

    m = re.match(r"OnTimeEmissions(\d{4})_([A-Za-z]+)-([A-Za-z]+)$", name)
    if m:
        return f"{m.group(2)}–{m.group(3)} {m.group(1)}"

    m = re.match(r"OnTimeEmissions(\d{4})_(\d{1,2})$", name)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        return f"{MONTHS[month - 1]} {year}"

    m2 = re.search(r"(\d{4})", name)
    year = m2.group(1) if m2 else "?"
    qm = re.search(r"Q(\d)", name, re.IGNORECASE)
    if qm:
        return f"Q{qm.group(1)} {year}"
    return name.replace("OnTimeEmissions", "").replace("_", " ").strip()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    legacy_map = {
        "Origin":         "origin",
        "Dest":           "dest",
        "OriginCityName": "origin_city",
        "DestCityName":   "dest_city",
        "Total CO2":      "co2_total",
        "Total CO2E":     "co2e_total",
    }
    return df.rename(columns={k: v for k, v in legacy_map.items() if k in df.columns})


def fetch_airports(refresh: bool = False) -> pd.DataFrame:
    if AIRPORTS_CSV.exists() and not refresh:
        print(f"Using cached airport coordinates: {AIRPORTS_CSV}")
    else:
        print("Downloading airport coordinates from OurAirports...")
        r = requests.get(AIRPORTS_URL, timeout=30)
        r.raise_for_status()
        AIRPORTS_CSV.parent.mkdir(parents=True, exist_ok=True)
        AIRPORTS_CSV.write_bytes(r.content)
        print(f"  Saved to {AIRPORTS_CSV}")

    df = pd.read_csv(AIRPORTS_CSV, low_memory=False)
    df = df[
        (df["iso_country"] == "US")
        & df["iata_code"].notna()
        & (df["iata_code"].str.len() == 3)
        & df["type"].isin(["large_airport", "medium_airport"])
    ][["iata_code", "name", "municipality", "latitude_deg", "longitude_deg"]].copy()
    df = df.drop_duplicates("iata_code").reset_index(drop=True)
    df.columns = ["iata", "airport_name", "city", "lat", "lon"]
    print(f"  {len(df)} US airports with IATA codes")
    return df


def load_and_aggregate(csv_path: Path, airports: pd.DataFrame):
    print(f"Loading {csv_path.name}...")

    sample = pd.read_csv(csv_path, nrows=0)
    has_legacy = "Total CO2" in sample.columns
    col_co2  = "Total CO2"      if has_legacy else "co2_total"
    col_co2e = "Total CO2E"     if has_legacy else "co2e_total"
    col_orig = "Origin"         if has_legacy else "origin"
    col_dest = "Dest"           if has_legacy else "dest"
    col_orig_city = "OriginCityName" if has_legacy else "origin_city"
    col_dest_city = "DestCityName"   if has_legacy else "dest_city"

    df = pd.read_csv(csv_path, low_memory=False,
                     usecols=[col_orig, col_dest, col_orig_city, col_dest_city,
                              col_co2, col_co2e])
    df = normalize_columns(df)
    print(f"  {len(df):,} total rows")

    em = df.dropna(subset=["co2_total"])
    print(f"  {len(em):,} flights with emission estimates ({100*len(em)/len(df):.1f}%)")

    orig_agg = em.groupby("origin", as_index=False).agg(
        flights_out=("co2_total", "count"), co2_out=("co2_total", "sum")
    ).rename(columns={"origin": "iata"})
    dest_agg = em.groupby("dest", as_index=False).agg(
        flights_in=("co2_total", "count"), co2_in=("co2_total", "sum")
    ).rename(columns={"dest": "iata"})
    airport_em = orig_agg.merge(dest_agg, on="iata", how="outer").fillna(0)
    airport_em["total_co2"]     = airport_em["co2_out"]     + airport_em["co2_in"]
    airport_em["total_flights"] = airport_em["flights_out"] + airport_em["flights_in"]

    airports_geo = airports.merge(airport_em, on="iata", how="inner")
    print(f"  {len(airports_geo)} airports with emission data")
    return airports_geo, em


def build_figure(airports_geo: pd.DataFrame) -> go.Figure:
    ap = airports_geo.copy()

    # sizemode="area" so we encode area, not diameter
    sqrt_co2 = np.sqrt(ap["total_co2"].values)
    lo, hi = sqrt_co2.min(), sqrt_co2.max()
    sizes = 10 + 70 * (sqrt_co2 - lo) / max(hi - lo, 1e-9)

    hover_ap = (
        "<b>" + ap["airport_name"] + "</b><br>"
        + ap["city"].fillna("") + "<br>"
        + "CO₂: " + (ap["total_co2"] / 1e6).map(lambda x: f"{x:.1f} kt") + "<br>"
        + "Flights: " + ap["total_flights"].astype(int).map(lambda x: f"{x:,}")
    )

    trace = go.Scattergeo(
        lat=ap["lat"].tolist(),
        lon=ap["lon"].tolist(),
        mode="markers",
        marker=dict(
            size=sizes.tolist(),
            sizemode="area",
            color=ap["total_co2"].tolist(),
            colorscale=GREEN_COLORSCALE,
            cmin=float(ap["total_co2"].quantile(0.05)),
            cmax=float(ap["total_co2"].quantile(0.95)),
            opacity=0.88,
            line=dict(width=1.0, color="rgba(0,0,0,0.18)"),
            colorbar=dict(
                title=dict(text="CO₂ (kg)", side="right",
                           font=dict(size=11, color="#555")),
                thickness=12,
                len=0.50,
                y=0.5,
                x=1.005,
                tickfont=dict(size=11, color="#555"),
                outlinewidth=0,
            ),
        ),
        hoverinfo="text",
        hovertext=hover_ap.tolist(),
        showlegend=False,
    )

    fig = go.Figure(data=[trace])
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        geo=dict(
            scope="usa",
            projection_type="albers usa",
            showland=True,        landcolor="#f4f4f2",
            showocean=True,       oceancolor="#dce8f0",
            showlakes=True,       lakecolor="#dce8f0",
            showrivers=False,
            showcoastlines=True,  coastlinecolor="#aab8c2", coastlinewidth=0.7,
            showsubunits=True,    subunitcolor="#c8d0d8",   subunitwidth=0.5,
            showcountries=False,
            showframe=False,
            bgcolor="#ffffff",
            lataxis=dict(showgrid=False),
            lonaxis=dict(showgrid=False),
        ),
        hoverlabel=dict(
            bgcolor="#ffffff",
            font=dict(size=13, color="#222",
                      family='"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'),
            bordercolor="#ccc",
        ),
    )
    return fig


def build_html(fig: go.Figure, airports_geo: pd.DataFrame,
               em: pd.DataFrame, period_label: str) -> str:
    fig_json = pio.to_json(fig)

    total_flights   = len(em)
    valid           = em.dropna(subset=["co2_total"])
    total_co2_kt    = valid["co2_total"].sum() / 1e6
    unique_airports = len(airports_geo)
    avg_kg_flight   = valid["co2_total"].mean()

    top_ap  = airports_geo.nlargest(TOP_SIDEBAR, "total_co2")
    max_co2 = top_ap["total_co2"].max()

    rows_html = []
    for _, r in top_ap.iterrows():
        pct  = 100 * r["total_co2"] / max_co2
        kt   = r["total_co2"] / 1e6
        city = str(r["city"]) if pd.notna(r["city"]) else ""
        rows_html.append(f"""
          <div class="ap-row">
            <div class="ap-header">
              <span class="ap-code">{r['iata']}</span>
              <span class="ap-kt">{kt:.0f} kt</span>
            </div>
            <div class="ap-city">{city}</div>
            <div class="bar-bg"><div class="bar-fill" style="width:{pct:.0f}%"></div></div>
          </div>""")

    airports_html = "\n".join(rows_html)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>U.S. Aviation Emissions &mdash; {period_label}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.plot.ly/plotly-2.26.0.min.js" charset="utf-8"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      background: #f7f8f9;
      color: #1a1a1a;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      font-size: 13px;
    }}
    a {{ color: #2e7d32; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    /* ── Header ── */
    #hdr {{
      background: #ffffff;
      border-bottom: 1px solid #e0e4e8;
      padding: 14px 24px 12px;
      display: flex;
      align-items: baseline;
      gap: 14px;
      flex-wrap: wrap;
    }}
    #hdr .dash-link {{
      margin-left: auto;
      font-size: 12px;
      font-weight: 600;
      color: #2e7d32;
      white-space: nowrap;
    }}
    #hdr h1 {{
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.4px;
      color: #111;
      white-space: nowrap;
    }}
    #hdr .sub {{
      font-size: 12px;
      color: #6b7280;
      line-height: 1.6;
    }}
    .badge {{
      display: inline-block;
      background: #f0faf0;
      border: 1px solid #a5d6a7;
      border-radius: 4px;
      padding: 1px 7px;
      font-size: 10.5px;
      color: #2e7d32;
      font-weight: 600;
      vertical-align: middle;
      white-space: nowrap;
    }}

    /* ── Body layout ── */
    #body {{
      display: flex;
      flex: 1;
      min-height: 0;
    }}
    #map-wrap {{
      flex: 1;
      min-width: 0;
      background: #ffffff;
    }}
    #map {{
      width: 100%;
      height: calc(100vh - 128px);
      min-height: 420px;
    }}

    /* ── Sidebar ── */
    #sidebar {{
      width: 270px;
      flex-shrink: 0;
      background: #ffffff;
      border-left: 1px solid #e0e4e8;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
    }}
    .blk {{
      padding: 16px;
      border-bottom: 1px solid #eaecef;
    }}
    .blk h3 {{
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.9px;
      color: #9ca3af;
      margin-bottom: 12px;
    }}

    /* Stats grid */
    .stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }}
    .stat {{
      background: #f7f8f9;
      border: 1px solid #e8eaed;
      border-radius: 7px;
      padding: 10px 11px;
    }}
    .stat-n {{
      font-size: 20px;
      font-weight: 700;
      color: #2e7d32;
      line-height: 1.15;
      letter-spacing: -0.5px;
      font-feature-settings: "tnum" 1;
    }}
    .stat-l {{
      font-size: 11px;
      color: #6b7280;
      margin-top: 3px;
    }}

    /* Airport list */
    .ap-row {{ margin-bottom: 12px; }}
    .ap-header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 2px;
    }}
    .ap-code {{
      font-size: 13px;
      font-weight: 700;
      color: #111;
      font-feature-settings: "tnum" 1;
      letter-spacing: 0.2px;
    }}
    .ap-kt {{
      font-size: 11px;
      font-weight: 600;
      color: #2e7d32;
      font-feature-settings: "tnum" 1;
    }}
    .ap-city {{
      font-size: 10.5px;
      color: #9ca3af;
      margin-bottom: 5px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .bar-bg {{
      background: #e8f5e9;
      border-radius: 3px;
      height: 4px;
    }}
    .bar-fill {{
      height: 4px;
      background: linear-gradient(90deg, #a5d6a7 0%, #4caf50 50%, #1a3a1c 100%);
      border-radius: 3px;
    }}

    /* Legend */
    .legend {{
      padding: 12px 16px;
      margin-top: auto;
      border-top: 1px solid #eaecef;
    }}
    .legend h3 {{
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.9px;
      color: #9ca3af;
      margin-bottom: 8px;
    }}
    .legend-bar {{
      height: 7px;
      border-radius: 3px;
      background: linear-gradient(90deg, #e8f5e9, #a5d6a7, #4caf50, #2e7d32, #1a3a1c);
      margin-bottom: 5px;
    }}
    .legend-labels {{
      display: flex;
      justify-content: space-between;
      font-size: 10px;
      color: #9ca3af;
      font-feature-settings: "tnum" 1;
    }}

    /* ── Footer ── */
    #footer {{
      background: #ffffff;
      border-top: 1px solid #e0e4e8;
      padding: 9px 24px;
      font-size: 11px;
      color: #9ca3af;
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
    }}
    #footer strong {{ color: #6b7280; }}
    #footer a {{ color: #2e7d32; }}

    @media (max-width: 820px) {{
      #sidebar {{ display: none; }}
    }}
  </style>
</head>
<body>

<div id="hdr">
  <h1>U.S. Aviation Emissions &mdash; {period_label} <span class="badge">Interactive</span></h1>
  <div class="sub">
    Per-flight CO&#8322; from engine certification data (ICAO EEDB) &bull;
    Bubble size &amp; color proportional to airport CO&#8322; throughput &bull;
    Hover for details
  </div>
  <a class="dash-link" href="dashboard.html">Results Dashboard &rarr;</a>
</div>

<div id="body">
  <div id="map-wrap">
    <div id="map"></div>
  </div>

  <div id="sidebar">
    <div class="blk">
      <h3>{period_label}</h3>
      <div class="stats">
        <div class="stat">
          <div class="stat-n">{total_flights / 1e3:.0f}k</div>
          <div class="stat-l">Total flights</div>
        </div>
        <div class="stat">
          <div class="stat-n">{total_co2_kt:,.0f}</div>
          <div class="stat-l">kt CO&#8322; total</div>
        </div>
        <div class="stat">
          <div class="stat-n">{unique_airports}</div>
          <div class="stat-l">Airports</div>
        </div>
        <div class="stat">
          <div class="stat-n">{avg_kg_flight / 1e3:.1f}t</div>
          <div class="stat-l">avg CO&#8322; / flight</div>
        </div>
      </div>
    </div>

    <div class="blk" style="flex:1;overflow-y:auto">
      <h3>Top {TOP_SIDEBAR} Airports by CO&#8322;</h3>
      {airports_html}
    </div>

    <div class="legend">
      <h3>Airport CO&#8322; Throughput</h3>
      <div class="legend-bar"></div>
      <div class="legend-labels"><span>Lower</span><span>Higher</span></div>
    </div>
  </div>
</div>

<div id="footer">
  <span><strong>Data:</strong> BTS On-Time Performance &bull; FAA Aircraft Registry &bull; ICAO EEDB v32 &bull; BADA Fuel Consumption</span>
  <span><strong>Method:</strong> <a href="https://www.icrat.org/previous-conferences/10th-international-conference/papers/">Eskenazi, Butler, Joshi &amp; Ryerson &mdash; ICRAT 2022</a></span>
  <span>Coords: <a href="https://ourairports.com">OurAirports</a> (public domain)</span>
</div>

<script>
  var figData = {fig_json};
  Plotly.newPlot("map", figData.data, figData.layout, {{
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["toImage", "sendDataToCloud", "select2d", "lasso2d"],
  }});
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Build aviation emissions map")
    parser.add_argument("--csv", type=Path, default=None,
                        help="Path to results CSV (default: newest OnTimeEmissions*.csv)")
    parser.add_argument("--refresh", action="store_true",
                        help="Re-download airport coordinates")
    args = parser.parse_args()

    csv_path = args.csv if args.csv else find_latest_results()
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found.")
        sys.exit(1)

    period_label = label_from_csv(csv_path)
    print(f"Data: {csv_path.name}  ({period_label})")

    airports = fetch_airports(refresh=args.refresh)
    airports_geo, em = load_and_aggregate(csv_path, airports)

    print("Building Plotly figure...")
    fig = build_figure(airports_geo)

    print("Generating HTML...")
    DOCS_DIR.mkdir(exist_ok=True)
    html = build_html(fig, airports_geo, em, period_label)
    OUTPUT_HTML.write_text(html, encoding="utf-8")

    size_kb = OUTPUT_HTML.stat().st_size / 1024
    print(f"\nWritten: {OUTPUT_HTML}  ({size_kb:.0f} KB)")
    print("\nTo publish on GitHub Pages:")
    print("  Settings → Pages → Source: main branch, /docs folder")


if __name__ == "__main__":
    main()
