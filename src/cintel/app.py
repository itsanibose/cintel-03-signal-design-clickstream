"""app.py - Reactive marimo app for this project.

Marimo adds reactive controls.
Every function below is a marimo cell.

RUN LOCALLY:

  uv run marimo edit src/cintel/app.py     # edit
  uv run marimo run  src/cintel/app.py     # run as an app (CTRL+c quits)

WASM DEPENDENCIES:

Under WebAssembly (emscripten) the browser has no project environment.
This app uses polars in addition to marimo, so the first cell installs
polars with micropip when running under WASM.

The full January clickstream file (~500 MB) is too large to ship to a
browser, so under WASM the app reads the small sample
public/example-data.csv instead (copy it from data/example-data.csv).

NO LOGGING:

A browser-based WASM app has no persistent Python server to store log files,
so this notebook configures no logging.

PLAN CELLS FIRST

1. Imports (installs WASM deps, returns shared imports)
2. Opening title and introduction (Markdown)
3. Load session signals (prefers artifacts/metrics.csv from signal_design.py,
   otherwise computes them from the raw clickstream via cintel.utils_system)
4. Headline funnel KPIs
5. Shared chart styling
6. Bar chart: sessions reaching each funnel stage
7. Bar chart: sessions started per day
8. Signal picker (numeric signals only)
9. Top sessions, sorted by the chosen signal
10. Closing (Markdown)

Note: marimo triggers @app.cell functions automatically; we never call them.
The names starting with "_" are for our own organization; the engine ignores
them.
"""

# === ONLY THIS AT THE TOP OF THE FILE ===

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
async def _():
    import sys

    if sys.platform == "emscripten":
        import micropip

        await micropip.install(["polars", "altair"])

    import altair as alt
    import marimo as mo
    import polars as pl

    from cintel.utils_system import design_clickstream_metrics, load_clickstream

    return alt, design_clickstream_metrics, load_clickstream, mo, pl, sys


@app.cell
def _(mo):
    mo.md(r"""
    # Signal Design: Clickstream Sessions

    Raw clickstream events (`event_time`, `event_type`, `product_id`,
    `category_id`, `category_code`, `brand`, `price`, `user_id`,
    `user_session`) are hard to read one row at a time. This app groups
    events into **sessions** and derives signals that tell a clearer story:

    - **Activity:** `total_events`, `views`, `carts`, `remove_from_carts`,
      `purchases`, `session_duration_sec`
    - **Funnel ratios:** `cart_to_view_ratio`, `purchase_to_cart_ratio`,
      `session_conversion_rate`
    - **Problem flag:** `abandoned_cart` (carted but never purchased)

    Pick a signal below to see the sessions where it is highest.
    """)


@app.cell
def _(design_clickstream_metrics, load_clickstream, mo, pl, sys):
    """Load session signals. Two environments, one cell.

    Locally, reuse artifacts/metrics.csv (written by signal_design.py) when it
    exists, because recomputing from the ~500 MB raw file is slow. Otherwise
    compute the signals from data/2020-Jan.csv.
    Under WASM (emscripten), Pyodide's open_url() fetches the small sample
    CSV from public/ and the signals are computed from it.
    """
    notebook_location = mo.notebook_location()

    if notebook_location is None:
        raise RuntimeError("Unable to determine notebook location.")

    if sys.platform == "emscripten":
        from pyodide.http import open_url  # ty: ignore[unresolved-import]

        data_url = notebook_location / "public" / "example-data.csv"
        metrics_df = design_clickstream_metrics(
            load_clickstream(open_url(str(data_url)))
        )
        source = "public/example-data.csv (sample)"
    else:
        repo_root = notebook_location.parents[1]
        artifact_path = repo_root / "artifacts" / "metrics.csv"
        if artifact_path.exists():
            metrics_df = pl.read_csv(artifact_path, try_parse_dates=True)
            source = "artifacts/metrics.csv"
        else:
            raw_path = repo_root / "data" / "2020-Jan.csv"
            metrics_df = design_clickstream_metrics(load_clickstream(raw_path))
            source = "data/2020-Jan.csv"

    # Numeric duration so it can be sorted, plus a readable display string
    # replacing the ISO 8601 text from utils (e.g. "PT17M6S" -> "00:17:06",
    # "P30DT12H45M36S" -> "30d 12:45:36").
    _secs = pl.col("session_duration_sec")

    def _two_digits(expr):
        return expr.cast(pl.String).str.zfill(2)

    _clock = pl.format(
        "{}:{}:{}",
        _two_digits(_secs % 86400 // 3600),
        _two_digits(_secs % 3600 // 60),
        _two_digits(_secs % 60),
    )

    metrics_df = metrics_df.with_columns(
        (pl.col("session_end_time") - pl.col("session_start_time"))
        .dt.total_seconds()
        .alias("session_duration_sec")
    ).with_columns(
        pl.when(_secs >= 86400)
        .then(pl.format("{}d {}", _secs // 86400, _clock))
        .otherwise(_clock)
        .alias("session_duration")
    )

    mo.md(f"Loaded **{metrics_df.height:,}** sessions from `{source}`.")
    return (metrics_df,)


@app.cell
def _(metrics_df, mo, pl):
    _sessions = metrics_df.height
    _kpis = metrics_df.select(
        (pl.col("purchases") > 0).mean().alias("conversion"),
        pl.col("abandoned_cart")
        .filter(pl.col("carts") > 0)
        .mean()
        .alias("abandonment"),
        pl.col("total_events").mean().alias("avg_events"),
    ).row(0, named=True)

    mo.hstack(
        [
            mo.stat(value=f"{_sessions:,}", label="Sessions"),
            mo.stat(
                value=f"{_kpis['conversion']:.2%}",
                label="Sessions with a purchase",
            ),
            mo.stat(
                value=f"{(_kpis['abandonment'] or 0):.2%}",
                label="Cart abandonment rate",
                caption="of sessions that added to cart",
            ),
            mo.stat(
                value=f"{_kpis['avg_events']:.1f}",
                label="Avg events per session",
            ),
        ],
        justify="space-around",
    )


@app.cell
def _():
    # Shared chart styling: one series per chart, so one hue (categorical
    # slot 1 of the reference palette). Thin bars, 4px rounded data-end.
    BAR_COLOR = "#2a78d6"
    BAR_SIZE = 22
    BAR_RADIUS = 4

    def style_chart(chart):
        """Readable text sizes, left-aligned titles, no box around the plot.

        Charts are shown as plain altair output (not mo.ui.altair_chart):
        we need no selection, and marimo's selection wrapper stops bars with
        cornerRadiusEnd from drawing at all.
        """
        return (
            chart.configure_axis(
                labelFontSize=12,
                titleFontSize=12,
                titleFontWeight="normal",
                domain=False,
                ticks=False,
                labelPadding=6,
            )
            .configure_title(fontSize=15, anchor="start", offset=12)
            .configure_view(stroke=None)
        )

    return BAR_COLOR, BAR_RADIUS, BAR_SIZE, style_chart


@app.cell
def _(BAR_COLOR, BAR_RADIUS, BAR_SIZE, alt, metrics_df, pl, style_chart):
    """Funnel: how many sessions reach each stage (view -> cart -> purchase)."""
    _total = metrics_df.height
    _stages = {
        "Viewed a product": metrics_df.filter(pl.col("views") > 0).height,
        "Added to cart": metrics_df.filter(pl.col("carts") > 0).height,
        "Purchased": metrics_df.filter(pl.col("purchases") > 0).height,
    }
    _funnel = pl.DataFrame(
        {
            "stage": list(_stages),
            "sessions": list(_stages.values()),
            "share": [n / _total for n in _stages.values()],
            "label": [f"{n:,} ({n / _total:.1%})" for n in _stages.values()],
        }
    )

    _bars = (
        alt.Chart(_funnel)
        .mark_bar(
            color=BAR_COLOR,
            size=BAR_SIZE,
            cornerRadiusEnd=BAR_RADIUS,
        )
        .encode(
            x=alt.X(
                "sessions:Q",
                # Every bar is labelled at its tip, so the axis would only add noise.
                axis=None,
                # Headroom so the value label at the longest bar's tip fits.
                scale=alt.Scale(domain=[0, max(_stages.values()) * 1.3]),
            ),
            y=alt.Y("stage:N", sort=None, title=None),
            tooltip=[
                alt.Tooltip("stage:N", title="Stage"),
                alt.Tooltip("sessions:Q", title="Sessions", format=","),
                alt.Tooltip("share:Q", title="Share of all sessions", format=".1%"),
            ],
        )
    )
    # Value label at each bar tip, in the theme's text color (not the bar color).
    _labels = _bars.mark_text(align="left", dx=6, fontSize=12).encode(text="label:N")
    _chart = (_bars + _labels).properties(
        title="Shopping funnel: sessions reaching each stage",
        width="container",
        height=150,
    )

    style_chart(_chart)


@app.cell
def _(BAR_COLOR, BAR_RADIUS, alt, metrics_df, pl, style_chart):
    """Sessions started per day, with that day's purchase rate in the tooltip."""
    _daily = (
        metrics_df.group_by(pl.col("session_start_time").dt.date().alias("day"))
        .agg(
            pl.len().alias("sessions"),
            (pl.col("purchases") > 0).mean().alias("purchase_rate"),
        )
        .sort("day")
    )

    _chart = (
        alt.Chart(_daily)
        .mark_bar(color=BAR_COLOR, cornerRadiusEnd=BAR_RADIUS)
        .encode(
            # Ordinal days -> one centered band per day, label under its bar.
            x=alt.X(
                "monthdate(day):O",
                title=None,
                scale=alt.Scale(paddingInner=0.2),
                # Label every 5th day (Jan 1, 6, 11, ...) so the axis stays readable.
                axis=alt.Axis(
                    labelAngle=0,
                    labelExpr=(
                        "(date(datum.value) - 1) % 5 == 0"
                        " ? timeFormat(datum.value, '%b %d') : ''"
                    ),
                ),
            ),
            y=alt.Y(
                "sessions:Q",
                title="Sessions",
                axis=alt.Axis(
                    labelExpr="datum.value == 0 ? '0' : format(datum.value, '~s')"
                ),
            ),
            tooltip=[
                alt.Tooltip("day:T", title="Day", format="%a %b %d"),
                alt.Tooltip("sessions:Q", title="Sessions", format=","),
                alt.Tooltip(
                    "purchase_rate:Q", title="Sessions with a purchase", format=".2%"
                ),
            ],
        )
        .properties(
            title="Sessions started per day",
            width="container",
            height=240,
        )
    )

    style_chart(_chart)


@app.cell
def _(metrics_df, mo):
    numeric_columns = [
        name for name, dtype in metrics_df.schema.items() if dtype.is_numeric()
    ]
    column_picker = mo.ui.dropdown(
        options=numeric_columns,
        value="cart_to_view_ratio",
        label="Signal to inspect",
    )
    column_picker  # noqa: B018 (marimo often uses standalone expressions)
    return (column_picker,)


@app.cell
def _(column_picker, metrics_df, mo):
    col = column_picker.value
    _top_n = 1000
    mo.vstack(
        [
            mo.md(f"**Top {_top_n:,} sessions by `{col}`:**"),
            mo.ui.table(metrics_df.sort(col, descending=True).head(_top_n)),
        ]
    )


@app.cell
def _(mo):
    mo.md(r"""
    ---
    [😊 Learn more at marimo.io](https://marimo.io/)
    ---

    **Running locally?**
    To stop the app, click in the VS Code terminal,
    then press **CTRL** and **c** together (CTRL+c).
    When it asks "Are you sure you want to quit? (y/N)",
    type **y** and press **Enter**.
    ---
    """)


if __name__ == "__main__":
    app.run()
