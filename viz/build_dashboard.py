"""
Generates docs/dashboard.html -- an interactive Plotly dashboard reproducing the
key figures/table from the ICRAT 2022 paper (Eskenazi, Butler, Joshi & Ryerson,
"Democratizing Aviation Emissions Estimation") using this repo's own real computed
output, not simulated data.

Reads:   results/OnTimeEmissions2021_9.csv (September 2021 -- closest available
         match to the paper's July-Sept 2021 Q3 analysis)
Writes:  docs/dashboard.html

Usage:
    python viz/build_dashboard.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

ROOT        = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results"
DOCS_DIR    = ROOT / "docs"
OUTPUT_HTML = DOCS_DIR / "dashboard.html"
DATA_CSV    = RESULTS_DIR / "OnTimeEmissions2021_9.csv"
PERIOD_LABEL = "September 2021"

GREEN     = "#2e7d32"
GREEN_DK  = "#1a3a1c"
GREEN_LT  = "#a5d6a7"
INK       = "#1a1a1a"
INK2      = "#6b7280"
INK3      = "#9ca3af"
BORDER    = "#e0e4e8"

CATEGORICAL = ["#2e7d32", "#0891b2", "#ea580c", "#7c3aed",
               "#dc2626", "#0369a1", "#b45309", "#16a34a"]

AIRLINE_NAMES = {
    "AA": "American", "AS": "Alaska", "B6": "JetBlue", "DL": "Delta",
    "F9": "Frontier", "G4": "Allegiant", "HA": "Hawaiian", "MQ": "Envoy",
    "NK": "Spirit", "OH": "PSA", "OO": "SkyWest", "QX": "Horizon",
    "UA": "United", "WN": "Southwest", "YV": "Mesa", "YX": "Republic", "9E": "Endeavor",
}

HC_GWP, CO_GWP, NOX_GWP = 84, 1.57, 298  # CO2-equivalency factors, same as README

FONT = dict(family='"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            color=INK2, size=12)

BASE_LAYOUT = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    font=FONT,
    hoverlabel=dict(bgcolor="#ffffff", bordercolor=BORDER,
                     font=dict(family=FONT["family"], size=12, color=INK)),
)
DEFAULT_MARGIN = dict(l=55, r=20, t=10, b=45)
DEFAULT_LEGEND = dict(font=dict(size=11))


def load_data() -> pd.DataFrame:
    usecols = ["IATA_CODE_Reporting_Airline", "Distance", "Number Seats",
               "Total CO2", "Total CO2E",
               "Total_HC_lto", "Total_CO_lto", "Total_NOx_lto", "Total_CO2_lto",
               "Total_CO2_ccd", "Total_NOx_ccd", "Total_CO_ccd", "Total_HC_ccd"]
    df = pd.read_csv(DATA_CSV, usecols=usecols, low_memory=False)
    return df


def fig_airline_ranking(em: pd.DataFrame) -> go.Figure:
    """Reproduces the paper's Table IV: CO2 per seat-mile, ranked by airline."""
    d = em[(em["Number Seats"] > 0) & (em["Distance"] > 0)].copy()
    d["co2_per_seat_mile"] = d["Total CO2"] / (d["Number Seats"] * d["Distance"])
    g = d.groupby("IATA_CODE_Reporting_Airline")["co2_per_seat_mile"].mean().sort_values()
    labels = [f"{AIRLINE_NAMES.get(c, c)}" for c in g.index]

    fig = go.Figure(go.Bar(
        x=g.values.tolist(), y=labels, orientation="h",
        marker=dict(color=g.values.tolist(), colorscale=[[0, GREEN_LT], [1, GREEN_DK]]),
        hovertemplate="%{y}: %{x:.3f} kg CO₂/seat-mile<extra></extra>",
    ))
    fig.update_layout(**BASE_LAYOUT, margin=dict(l=80, r=20, t=10, b=45),
                       xaxis=dict(title="kg CO₂ per seat-mile", gridcolor=BORDER),
                       yaxis=dict(gridcolor=BORDER))
    return fig


def fig_distance_scatter(em: pd.DataFrame) -> go.Figure:
    """Reproduces the paper's Figure 6: CO2e vs. flight distance."""
    d = em.dropna(subset=["Distance", "Total CO2E"]).copy()
    d["decile"] = pd.qcut(d["Distance"], 10, labels=False, duplicates="drop")
    sample = d.groupby("decile", group_keys=False).apply(
        lambda x: x.sample(min(len(x), 500), random_state=42)
    )
    fig = go.Figure(go.Scattergl(
        x=sample["Distance"].tolist(), y=(sample["Total CO2E"] / 1000).tolist(),
        mode="markers", marker=dict(size=4, color=GREEN, opacity=0.35),
        hovertemplate="Distance: %{x} mi<br>CO₂e: %{y:.1f} t<extra></extra>",
    ))
    fig.update_layout(**BASE_LAYOUT, margin=DEFAULT_MARGIN,
                       xaxis=dict(title="Flight Distance (miles)", gridcolor=BORDER),
                       yaxis=dict(title="CO₂e (metric tons)", gridcolor=BORDER))
    return fig


def fig_seat_mile_vs_distance(em: pd.DataFrame) -> go.Figure:
    """Reproduces the paper's Figure 7: CO2/seat-mile vs. distance, binned."""
    d = em[(em["Number Seats"] > 0) & (em["Distance"] > 0)].copy()
    d["co2_per_seat_mile"] = d["Total CO2"] / (d["Number Seats"] * d["Distance"])
    bins = np.arange(0, d["Distance"].max() + 100, 100)
    d["bin"] = pd.cut(d["Distance"], bins)
    binned = d.groupby("bin", observed=True).agg(
        distance=("Distance", "mean"), co2_sm=("co2_per_seat_mile", "mean"), n=("Distance", "size")
    )
    binned = binned[binned["n"] >= 5]

    fig = go.Figure(go.Scatter(
        x=binned["distance"].tolist(), y=binned["co2_sm"].tolist(),
        mode="lines+markers", line=dict(color=GREEN, width=2.5), marker=dict(size=5),
        hovertemplate="~%{x:.0f} mi: %{y:.3f} kg CO₂/seat-mile<extra></extra>",
    ))
    fig.update_layout(**BASE_LAYOUT, margin=DEFAULT_MARGIN,
                       xaxis=dict(title="Flight Distance (miles)", gridcolor=BORDER),
                       yaxis=dict(title="kg CO₂ / seat-mile", gridcolor=BORDER, rangemode="tozero"))
    return fig


def fig_lto_ccd_ghg(df: pd.DataFrame) -> go.Figure:
    """Reproduces the paper's Figures 4 & 5: LTO/CCD GHG contributions in CO2e terms."""
    d = df.dropna(subset=["Total_CO2_lto"])
    lto = {
        "CO₂": d["Total_CO2_lto"].sum() / 1e6,
        "NOx (as CO₂e)": (d["Total_NOx_lto"] * NOX_GWP).sum() / 1e6,
        "CO (as CO₂e)": (d["Total_CO_lto"] * CO_GWP).sum() / 1e6,
        "HC (as CO₂e)": (d["Total_HC_lto"] * HC_GWP).sum() / 1e6,
    }
    ccd = {
        "CO₂": d["Total_CO2_ccd"].sum() / 1e6,
        "NOx (as CO₂e)": (d["Total_NOx_ccd"] * NOX_GWP).sum() / 1e6,
        "CO (as CO₂e)": (d["Total_CO_ccd"] * CO_GWP).sum() / 1e6,
        "HC (as CO₂e)": (d["Total_HC_ccd"] * HC_GWP).sum() / 1e6,
    }
    cats = list(lto.keys())
    fig = go.Figure()
    fig.add_trace(go.Bar(x=cats, y=[lto[c] for c in cats], name="LTO",
                          marker=dict(color=GREEN_LT),
                          hovertemplate="LTO %{x}: %{y:.1f} kt<extra></extra>"))
    fig.add_trace(go.Bar(x=cats, y=[ccd[c] for c in cats], name="CCD",
                          marker=dict(color=GREEN_DK),
                          hovertemplate="CCD %{x}: %{y:.1f} kt<extra></extra>"))
    fig.update_layout(**BASE_LAYOUT, barmode="group", margin=DEFAULT_MARGIN,
                       legend=DEFAULT_LEGEND,
                       xaxis=dict(gridcolor=BORDER),
                       yaxis=dict(title="Metric kilotons (log scale)", type="log", gridcolor=BORDER))
    return fig


def build_html() -> str:
    df = load_data()
    total_rows = len(df)
    em = df.dropna(subset=["Total CO2"])
    em = em[(em["Number Seats"] > 0) & (em["Distance"] > 0)]
    coverage_pct = 100 * len(em) / total_rows
    total_co2e_kt = em["Total CO2E"].sum() / 1e6

    figs = {
        "airlineRank": fig_airline_ranking(em),
        "distScatter": fig_distance_scatter(em),
        "seatMileDist": fig_seat_mile_vs_distance(em),
        "ltoCcd":       fig_lto_ccd_ghg(df),
    }
    fig_json = {k: pio.to_json(v) for k, v in figs.items()}
    plot_calls = "\n".join(
        f'Plotly.newPlot("{k}", {fig_json[k]}.data, {fig_json[k]}.layout, PLOTCFG);'
        for k in figs
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Aviation Emissions &mdash; Results Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.26.0.min.js" charset="utf-8"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #f7f8f9; color: {INK}; line-height: 1.5;
  }}
  a {{ color: {GREEN}; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  header {{ background: #ffffff; border-bottom: 1px solid {BORDER}; padding: 1.4rem 2rem; }}
  .hdr-inner {{ max-width: 1320px; margin: 0 auto; display: flex; align-items: baseline;
                justify-content: space-between; flex-wrap: wrap; gap: .75rem; }}
  header h1 {{ font-size: 1.3rem; font-weight: 700; letter-spacing: -0.3px; color: {INK}; }}
  header .back {{ font-size: .85rem; font-weight: 600; color: {INK2}; }}
  .badge {{
    display:inline-block; background:#f0faf0; border:1px solid {GREEN_LT};
    color:{GREEN}; font-size:.7rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase;
    padding:.2rem .6rem; border-radius:4px; margin-left:.6rem; vertical-align:middle;
  }}
  .sub {{ font-size: .8rem; color: {INK3}; margin-top: .2rem; }}

  main {{ max-width: 1320px; margin: 0 auto; padding: 2rem; }}

  .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }}
  .kpi {{ background: #ffffff; border: 1px solid {BORDER}; border-radius: 8px; padding: 1rem 1.2rem; }}
  .kpi .n {{ font-weight: 700; font-size: 1.5rem; color: {GREEN}; font-feature-settings: "tnum" 1; }}
  .kpi .l {{ font-size: .78rem; color: {INK2}; margin-top: .25rem; line-height: 1.4; }}

  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }}
  .panel {{ background: #ffffff; border: 1px solid {BORDER}; border-radius: 8px; padding: 1.3rem 1.4rem 1rem; }}
  .panel h2 {{ font-size: .95rem; font-weight: 700; color: {INK}; margin-bottom: .15rem; }}
  .panel .psub {{ font-size: .78rem; color: {INK3}; margin-bottom: .9rem; }}
  .panel .chart {{ width: 100%; height: 320px; }}
  .panel.wide {{ grid-column: 1 / -1; }}

  .map-card {{
    background: #f0faf0; border: 1px solid {GREEN_LT}; border-radius: 8px;
    padding: 1.2rem 1.4rem; margin-top: 1.25rem; display: flex; align-items: center;
    justify-content: space-between; flex-wrap: wrap; gap: .75rem;
  }}
  .map-card span {{ font-size: .88rem; color: {INK2}; }}
  .map-card a {{ font-weight: 700; }}

  footer {{ text-align: center; padding: 2rem; font-size: .8rem; color: {INK3}; }}

  @media (max-width: 980px) {{
    .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
    .grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<header>
  <div class="hdr-inner">
    <div>
      <h1>Aviation Emissions <span class="badge">Results Dashboard</span></h1>
      <div class="sub">Reproducing the ICRAT 2022 paper's key figures with this repo's real computed output &middot; {PERIOD_LABEL}</div>
    </div>
    <a class="back" href="./">&larr; Live Route Map</a>
  </div>
</header>

<main>
  <div class="kpi-row">
    <div class="kpi"><div class="n">{len(em):,}</div><div class="l">Flights with computed emissions, {PERIOD_LABEL}</div></div>
    <div class="kpi"><div class="n">{coverage_pct:.1f}%</div><div class="l">Of BTS on-time rows retained after data-quality filtering</div></div>
    <div class="kpi"><div class="n">{total_co2e_kt:,.0f} kt</div><div class="l">Total CO&#8322;e emitted, {PERIOD_LABEL}</div></div>
    <div class="kpi"><div class="n">17</div><div class="l">U.S. mainline + regional carriers covered</div></div>
  </div>

  <div class="grid">
    <div class="panel wide">
      <h2>CO&#8322; per Seat-Mile by Airline</h2>
      <div class="psub">Reproduces the paper's Table IV. Frontier and Spirit rank lowest here, matching the paper's finding, though exact values differ slightly since this is one month (September 2021) vs. the paper's full Q3.</div>
      <div class="chart" id="airlineRank"></div>
    </div>
    <div class="panel">
      <h2>CO&#8322;e vs. Flight Distance</h2>
      <div class="psub">Reproduces Figure 6 &middot; stratified sample across distance deciles &middot; the visible split reflects different aircraft types serving short- vs. long-haul routes</div>
      <div class="chart" id="distScatter"></div>
    </div>
    <div class="panel">
      <h2>CO&#8322;/Seat-Mile vs. Distance</h2>
      <div class="psub">Reproduces Figure 7 &middot; binned mean, 100-mile buckets &middot; short flights carry the highest per-seat-mile footprint</div>
      <div class="chart" id="seatMileDist"></div>
    </div>
    <div class="panel wide">
      <h2>LTO vs. CCD Greenhouse Gas Contribution (CO&#8322;e terms)</h2>
      <div class="psub">Reproduces Figures 4 &amp; 5 &middot; NOx converted to CO&#8322;-equivalent (&times;298) exceeds CO&#8322; alone in both flight stages, matching the paper's headline finding &middot; log scale</div>
      <div class="chart" id="ltoCcd"></div>
    </div>
  </div>

  <div class="map-card">
    <span>For the airport-level geographic view (the paper's Figure 3 equivalent), see the interactive route map.</span>
    <a href="./">View Live Map &rarr;</a>
  </div>
</main>

<footer>
  Built from real pipeline output, {PERIOD_LABEL} &middot; Methodology:
  <a href="https://arxiv.org/abs/2202.11208" target="_blank">Eskenazi, Butler, Joshi &amp; Ryerson, ICRAT 2022</a>
  &middot; <a href="https://github.com/arnav64/aviation-emissions-toolkit" target="_blank">Source on GitHub</a>
</footer>

<script>
var PLOTCFG = {{ responsive: true, displaylogo: false,
                  modeBarButtonsToRemove: ["toImage","sendDataToCloud","select2d","lasso2d"] }};
{plot_calls}
</script>
</body>
</html>"""


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    html = build_html()
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Written: {OUTPUT_HTML} ({OUTPUT_HTML.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
