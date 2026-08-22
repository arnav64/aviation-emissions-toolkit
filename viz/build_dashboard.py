"""
Generates docs/dashboard.html -- the interactive results dashboard for the
aviation emissions toolkit. Two views, switched by tabs:

  1. Route Map    -- the airport-level emissions map (reuses build_viz.py's
                      data-loading and figure-building functions directly, so
                      there's one source of truth for the map).
  2. Analysis     -- reproduces the key figures/table from the ICRAT 2022 paper
                      (Eskenazi, Butler, Joshi & Ryerson, "Democratizing Aviation
                      Emissions Estimation") using this repo's own real computed
                      output.

Reads:   results/OnTimeEmissions*.csv (map: newest available; analysis: September
         2021, the closest match to the paper's July-Sept 2021 Q3 period)
Writes:  docs/dashboard.html

Usage:
    python viz/build_dashboard.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from build_viz import (
    fetch_airports,
    find_latest_results,
    label_from_csv,
    load_and_aggregate,
    build_figure as build_map_figure,
    TOP_SIDEBAR,
)

ROOT        = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results"
DOCS_DIR    = ROOT / "docs"
OUTPUT_HTML = DOCS_DIR / "dashboard.html"
ANALYSIS_CSV = RESULTS_DIR / "OnTimeEmissions2021_9.csv"
ANALYSIS_PERIOD = "September 2021"

GREEN     = "#2e7d32"
GREEN_DK  = "#1a3a1c"
GREEN_LT  = "#a5d6a7"
INK       = "#1a1a1a"
INK2      = "#6b7280"
INK3      = "#9ca3af"
BORDER    = "#e0e4e8"

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


# ---------------------------------------------------------------------------
# View 1: Route Map (reuses build_viz.py's own data + figure functions)
# ---------------------------------------------------------------------------

def build_map_view():
    csv_path = find_latest_results()
    period_label = label_from_csv(csv_path)
    airports = fetch_airports(refresh=False)
    airports_geo, em = load_and_aggregate(csv_path, airports)
    fig = build_map_figure(airports_geo)

    total_flights   = len(em)
    valid           = em.dropna(subset=["co2_total"])
    total_co2_kt    = valid["co2_total"].sum() / 1e6
    unique_airports = len(airports_geo)
    avg_kg_flight   = valid["co2_total"].mean()

    top_ap  = airports_geo.nlargest(TOP_SIDEBAR, "total_co2")
    max_co2 = top_ap["total_co2"].max()
    rows = []
    for _, r in top_ap.iterrows():
        pct  = 100 * r["total_co2"] / max_co2
        kt   = r["total_co2"] / 1e6
        city = str(r["city"]) if pd.notna(r["city"]) else ""
        rows.append(f"""
          <div class="ap-row">
            <div class="ap-header">
              <span class="ap-code">{r['iata']}</span>
              <span class="ap-kt">{kt:.0f} kt</span>
            </div>
            <div class="ap-city">{city}</div>
            <div class="bar-bg"><div class="bar-fill" style="width:{pct:.0f}%"></div></div>
          </div>""")

    stats = {
        "flights": f"{total_flights / 1e3:.0f}k",
        "co2_kt": f"{total_co2_kt:,.0f}",
        "airports": f"{unique_airports}",
        "avg_t": f"{avg_kg_flight / 1e3:.1f}t",
    }
    return fig, "\n".join(rows), stats, period_label


# ---------------------------------------------------------------------------
# View 2: Analysis (reproduces ICRAT 2022 paper figures)
# ---------------------------------------------------------------------------

def load_analysis_data() -> pd.DataFrame:
    usecols = ["IATA_CODE_Reporting_Airline", "Distance", "Number Seats",
               "Total CO2", "Total CO2E",
               "Total_HC_lto", "Total_CO_lto", "Total_NOx_lto", "Total_CO2_lto",
               "Total_CO2_ccd", "Total_NOx_ccd", "Total_CO_ccd", "Total_HC_ccd"]
    return pd.read_csv(ANALYSIS_CSV, usecols=usecols, low_memory=False)


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
    map_fig, map_rows_html, map_stats, map_period = build_map_view()

    df = load_analysis_data()
    total_rows = len(df)
    em = df.dropna(subset=["Total CO2"])
    em = em[(em["Number Seats"] > 0) & (em["Distance"] > 0)]
    coverage_pct = 100 * len(em) / total_rows
    total_co2e_kt = em["Total CO2E"].sum() / 1e6

    figs = {
        "mapView":      map_fig,
        "airlineRank":  fig_airline_ranking(em),
        "distScatter":  fig_distance_scatter(em),
        "seatMileDist": fig_seat_mile_vs_distance(em),
        "ltoCcd":       fig_lto_ccd_ghg(df),
    }
    fig_json = {k: pio.to_json(v) for k, v in figs.items()}
    plot_calls = "\n".join(f'charts["{k}"] = {fig_json[k]};' for k in figs)

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

  header {{ background: #ffffff; border-bottom: 1px solid {BORDER}; padding: 1rem 2rem 0; }}
  .hdr-inner {{ max-width: 1400px; margin: 0 auto; display: flex; align-items: center;
                justify-content: space-between; flex-wrap: wrap; gap: .75rem; }}
  header h1 {{ font-size: 1.25rem; font-weight: 700; letter-spacing: -0.3px; color: {INK}; }}
  header .back {{ font-size: .85rem; font-weight: 600; color: {INK2}; }}

  .tabs {{ max-width: 1400px; margin: .75rem auto 0; display: flex; gap: .25rem; }}
  .tab-btn {{
    background: none; border: none; cursor: pointer; font-family: inherit;
    font-size: .9rem; font-weight: 600; color: {INK3};
    padding: .6rem 1rem; border-bottom: 2px solid transparent;
  }}
  .tab-btn.active {{ color: {GREEN}; border-bottom-color: {GREEN}; }}
  .tab-btn:hover:not(.active) {{ color: {INK2}; }}

  .view {{ display: none; }}
  .view.active {{ display: block; }}

  main {{ max-width: 1400px; margin: 0 auto; padding: 1.5rem 2rem 2rem; }}
  .period-note {{ font-size: .8rem; color: {INK3}; margin-bottom: 1.25rem; }}

  /* ── Analysis view ── */
  .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }}
  .kpi {{ background: #ffffff; border: 1px solid {BORDER}; border-radius: 8px; padding: 1rem 1.2rem; }}
  .kpi .n {{ font-weight: 700; font-size: 1.5rem; color: {GREEN}; font-feature-settings: "tnum" 1; }}
  .kpi .l {{ font-size: .78rem; color: {INK2}; margin-top: .25rem; line-height: 1.4; }}

  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }}
  .panel {{ background: #ffffff; border: 1px solid {BORDER}; border-radius: 8px; padding: 1.3rem 1.4rem 1rem; }}
  .panel h2 {{ font-size: .95rem; font-weight: 700; color: {INK}; margin-bottom: .15rem; }}
  .panel .psub {{ font-size: .78rem; color: {INK3}; margin-bottom: .9rem; }}
  .panel .chart {{ width: 100%; height: 320px; }}
  .panel.wide {{ grid-column: 1 / -1; }}

  /* ── Map view (mirrors the standalone map's layout) ── */
  #map-body {{ display: flex; border: 1px solid {BORDER}; border-radius: 8px; overflow: hidden; background: #fff; }}
  #map-wrap {{ flex: 1; min-width: 0; }}
  #mapView {{ width: 100%; height: 640px; }}
  #map-sidebar {{ width: 270px; flex-shrink: 0; border-left: 1px solid {BORDER}; display: flex; flex-direction: column; }}
  .blk {{ padding: 16px; border-bottom: 1px solid #eaecef; }}
  .blk h3 {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .9px; color: {INK3}; margin-bottom: 12px; }}
  .m-stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .m-stat {{ background: #f7f8f9; border: 1px solid #e8eaed; border-radius: 7px; padding: 10px 11px; }}
  .m-stat .n {{ font-size: 18px; font-weight: 700; color: {GREEN}; font-feature-settings: "tnum" 1; }}
  .m-stat .l {{ font-size: 10.5px; color: {INK2}; margin-top: 3px; }}
  .ap-row {{ margin-bottom: 12px; }}
  .ap-header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2px; }}
  .ap-code {{ font-size: 13px; font-weight: 700; color: #111; font-feature-settings: "tnum" 1; }}
  .ap-kt {{ font-size: 11px; font-weight: 600; color: {GREEN}; font-feature-settings: "tnum" 1; }}
  .ap-city {{ font-size: 10.5px; color: {INK3}; margin-bottom: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .bar-bg {{ background: #e8f5e9; border-radius: 3px; height: 4px; }}
  .bar-fill {{ height: 4px; background: linear-gradient(90deg, #a5d6a7 0%, #4caf50 50%, {GREEN_DK} 100%); border-radius: 3px; }}
  .ap-list {{ flex: 1; overflow-y: auto; max-height: 480px; }}

  footer {{ text-align: center; padding: 2rem; font-size: .8rem; color: {INK3}; }}

  @media (max-width: 980px) {{
    .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
    .grid {{ grid-template-columns: 1fr; }}
    #map-body {{ flex-direction: column; }}
    #map-sidebar {{ width: 100%; border-left: none; border-top: 1px solid {BORDER}; }}
  }}
</style>
</head>
<body>

<header>
  <div class="hdr-inner">
    <h1>Aviation Emissions Toolkit &mdash; Results Dashboard</h1>
    <a class="back" href="https://github.com/arnav64/aviation-emissions-toolkit" target="_blank">View on GitHub &#8599;</a>
  </div>
  <div class="tabs">
    <button class="tab-btn active" data-view="view-map" onclick="showView('view-map', this)">Route Map</button>
    <button class="tab-btn" data-view="view-analysis" onclick="showView('view-analysis', this)">Emissions Analysis</button>
  </div>
</header>

<main>
  <div id="view-map" class="view active">
    <div class="period-note">{map_period} &middot; most recent processed month &middot; bubble size &amp; color proportional to airport CO&#8322; throughput</div>
    <div id="map-body">
      <div id="map-wrap"><div id="mapView"></div></div>
      <div id="map-sidebar">
        <div class="blk">
          <h3>{map_period}</h3>
          <div class="m-stats">
            <div class="m-stat"><div class="n">{map_stats['flights']}</div><div class="l">Total flights</div></div>
            <div class="m-stat"><div class="n">{map_stats['co2_kt']}</div><div class="l">kt CO&#8322; total</div></div>
            <div class="m-stat"><div class="n">{map_stats['airports']}</div><div class="l">Airports</div></div>
            <div class="m-stat"><div class="n">{map_stats['avg_t']}</div><div class="l">avg CO&#8322; / flight</div></div>
          </div>
        </div>
        <div class="blk ap-list">
          <h3>Top {TOP_SIDEBAR} Airports by CO&#8322;</h3>
          {map_rows_html}
        </div>
      </div>
    </div>
  </div>

  <div id="view-analysis" class="view">
    <div class="period-note">{ANALYSIS_PERIOD} &middot; matches the ICRAT 2022 paper's analysis period &middot; reproduces its key figures/table from this repo's real computed output</div>
    <div class="kpi-row">
      <div class="kpi"><div class="n">{len(em):,}</div><div class="l">Flights with computed emissions</div></div>
      <div class="kpi"><div class="n">{coverage_pct:.1f}%</div><div class="l">Of BTS on-time rows retained after data-quality filtering</div></div>
      <div class="kpi"><div class="n">{total_co2e_kt:,.0f} kt</div><div class="l">Total CO&#8322;e emitted</div></div>
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
  </div>
</main>

<footer>
  Built from real pipeline output &middot; Methodology:
  <a href="https://arxiv.org/abs/2202.11208" target="_blank">Eskenazi, Butler, Joshi &amp; Ryerson, ICRAT 2022</a>
  &middot; <a href="https://github.com/arnav64/aviation-emissions-toolkit" target="_blank">Source on GitHub</a>
</footer>

<script>
var PLOTCFG = {{ responsive: true, displaylogo: false,
                  modeBarButtonsToRemove: ["toImage","sendDataToCloud","select2d","lasso2d"] }};
var charts = {{}};
var rendered = {{}};
{plot_calls}

function renderChart(id) {{
  if (rendered[id]) return;
  var el = document.getElementById(id);
  if (!el || !charts[id]) return;
  Plotly.newPlot(id, charts[id].data, charts[id].layout, PLOTCFG);
  charts[id] = null; // free the reference once rendered
  rendered[id] = true;
}}

function showView(viewId, btn) {{
  document.querySelectorAll(".view").forEach(function(v) {{ v.classList.remove("active"); }});
  document.querySelectorAll(".tab-btn").forEach(function(b) {{ b.classList.remove("active"); }});
  document.getElementById(viewId).classList.add("active");
  btn.classList.add("active");
  document.querySelectorAll("#" + viewId + " [id]").forEach(function(el) {{
    if (charts[el.id]) {{
      renderChart(el.id);
      Plotly.Plots.resize(el.id);
    }}
  }});
}}

renderChart("mapView");
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
