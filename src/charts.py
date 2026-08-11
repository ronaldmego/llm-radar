"""Interactive scatter views — the analytical layer of the dashboard.

Tables answer "what is model X?"; these answer "what does the landscape look
like?". Two charts, one question each:

* :func:`cost_vs_context` — the hosted market. Where a model sits on the
  price/context plane, coloured by what it can be fed.
* :func:`traction_vs_age` — the open-weights side. Community traction against
  release date, with the size of the installed base as the bubble. A model that
  is new and loved but not yet downloaded reads immediately: high, right, small.

Encoding rules that are not negotiable here:

* Categorical hues are assigned in a fixed order and never cycled, so a model
  keeps its colour when a filter changes the series count.
* The palette is validated (lightness band, chroma floor, colour-vision
  separation, contrast) — the brand navy is deliberately *not* in it: it is ink,
  it reads gray as a data colour and fails both the lightness and chroma checks.
* Log axes wherever a range spans orders of magnitude, which is both of them.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

# Validated categorical palette (see module docstring). Fixed order.
PALETTE = ("#4a7fd4", "#c85a2e", "#2a9d8f", "#9b59b6")
# `responsive` keeps the plot area matched to the card as it resizes; the modebar
# stays (380 overlapping points are worth zooming into) minus the vendor logo.
CHART_CONFIG = {"responsive": True, "displaylogo": False}

INK = "#16202e"
MUTED = "#5c6b7f"
GRID = "#dfe4ec"
SURFACE = "#ffffff"
FONT = "IBM Plex Sans, system-ui, sans-serif"

_LAYOUT = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(family=FONT, size=12, color=INK),
    margin=dict(l=8, r=8, t=16, b=8),
    hoverlabel=dict(
        bgcolor=SURFACE, bordercolor=GRID, font=dict(family=FONT, color=INK, size=12)
    ),
    # The legend is HTML, drawn by `category_key()` under the card title, and the
    # plot's own is off. Reason: Quarto lays the figure out at the card's initial
    # narrow width and then stretches it — the plot area re-flows, the legend does
    # not. Horizontally it prints the entries on top of each other; moved outside
    # to the right it gets clipped by the margin. Neither is visible when the
    # figure is opened on its own, which is what makes this worth writing down.
    # An HTML key sidesteps the whole thing and wraps by itself on a phone.
    showlegend=False,
    autosize=True,
)


def category_key(categories: tuple[str, ...], note: str = "") -> str:
    """The chart legend, as HTML — see the `showlegend` comment in ``_LAYOUT``.

    Colours come from the same fixed-order palette the traces use, so the key and
    the marks cannot drift apart.
    """
    items = "".join(
        f'<span class="ck-item"><i style="background:{PALETTE[i % len(PALETTE)]}">'
        f"</i>{cat}</span>"
        for i, cat in enumerate(categories)
    )
    tail = f'<span class="ck-note">{note}</span>' if note else ""
    return f'<div class="chart-key">{items}{tail}</div>'


def _axis(**kwargs) -> dict:
    """Recessive axis: hairline grid, no zero-line, muted ticks."""
    base = dict(
        gridcolor=GRID,
        griddash="dot",
        zeroline=False,
        showline=False,
        ticks="outside",
        ticklen=4,
        tickcolor=GRID,
        tickfont=dict(size=11, color=MUTED),
        title_font=dict(size=12, color=MUTED),
        automargin=True,
    )
    base.update(kwargs)
    return base


def _ctx_label(k: int) -> str:
    return f"{k / 1000:.0f}M" if k >= 1000 else f"{k:,}K"


def cost_vs_context(df: pd.DataFrame, categories: tuple[str, ...]) -> go.Figure:
    """Hosted models on the price/context plane, coloured by input category.

    Free models and the routers OpenRouter prices at ``-1`` cannot sit on a
    logarithmic price axis, so they are excluded here and counted in the caption
    instead of being silently dropped.
    """
    plot = df[(df["price_out"].notna()) & (df["price_out"] > 0) & (df["context"] > 0)]
    fig = go.Figure()
    for i, cat in enumerate(categories):
        d = plot[plot["category"] == cat]
        if d.empty:
            continue
        hue = PALETTE[i % len(PALETTE)]
        # Open weights available vs closed: a real signal with full coverage
        # (OpenRouter publishes the Hub repo when there is one), so it carries a
        # second, non-colour encoding — filled for open, hollow for closed.
        first = True
        for open_w in (True, False):
            sub = d[d["open_weights"] == open_w]
            if sub.empty:
                continue
            marker = (
                dict(size=9, color=hue, opacity=0.8, line=dict(width=0))
                if open_w
                else dict(
                    size=9,
                    color="rgba(0,0,0,0)",
                    line=dict(width=1.6, color=hue),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=sub["context"],
                    y=sub["price_out"],
                    mode="markers",
                    name=cat,
                    legendgroup=cat,
                    showlegend=first,
                    marker=marker,
                    customdata=sub[["provider", "context_k", "price_in"]].to_numpy(),
                    text=sub["name"],
                    hovertemplate=(
                        "<b>%{text}</b><br>%{customdata[0]}"
                        "<br>Context %{customdata[1]:,}K"
                        "<br>$%{customdata[2]:.2f} in · $%{y:.2f} out per 1M"
                        "<extra></extra>"
                    ),
                )
            )
            first = False
    ticks = [4_000, 32_000, 128_000, 512_000, 2_000_000]
    fig.update_layout(
        **_LAYOUT,
        xaxis=_axis(
            type="log",
            title="Context window",
            tickvals=ticks,
            ticktext=[_ctx_label(t // 1000) for t in ticks],
        ),
        yaxis=_axis(
            type="log",
            title="$ per 1M output tokens",
            tickvals=[0.01, 0.1, 1, 10, 100],
            ticktext=["$0.01", "$0.10", "$1", "$10", "$100"],
        ),
    )
    return fig


def traction_vs_age(df: pd.DataFrame, categories: tuple[str, ...]) -> go.Figure:
    """Open-weight models: community likes against release date, sized by downloads.

    The bubble is 30-day downloads, so a model published this week is *small and
    high* — loved before it is installed. That corner is what a download-ranked
    table can never show.
    """
    plot = df[(df["likes"] > 0) & df["created"].notna()].copy()
    # Area-proportional bubbles: radius would exaggerate the big repos ~30x.
    biggest = max(int(plot["downloads"].max()), 1)
    fig = go.Figure()
    for i, cat in enumerate(categories):
        d = plot[plot["category"] == cat]
        if d.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=d["created"],
                y=d["likes"],
                mode="markers",
                name=cat,
                marker=dict(
                    size=d["downloads"],
                    sizemode="area",
                    sizeref=2.0 * biggest / (44.0**2),
                    sizemin=5,
                    color=PALETTE[i % len(PALETTE)],
                    opacity=0.75,
                    line=dict(width=1.5, color=SURFACE),
                ),
                customdata=d[["org", "downloads_disp", "license"]].to_numpy(),
                text=d["name"],
                hovertemplate=(
                    "<b>%{text}</b><br>%{customdata[0]}"
                    "<br>%{y:,} likes · %{customdata[1]} downloads (30d)"
                    "<br>License %{customdata[2]}"
                    "<br>Published %{x|%Y-%m-%d}"
                    "<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        **_LAYOUT,
        xaxis=_axis(title="Published", tickformat="%b %Y"),
        # A log axis left to itself labels every minor tick (2, 5, 2, 5…), which
        # reads as noise. One label per decade, written the way people say it.
        yaxis=_axis(
            type="log",
            title="Likes",
            tickvals=[1, 10, 100, 1_000, 10_000],
            ticktext=["1", "10", "100", "1k", "10k"],
        ),
    )
    return fig
