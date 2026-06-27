"""great-tables views for the LLM Radar dashboard."""
from __future__ import annotations

import pandas as pd
from great_tables import GT, loc, style, md

# Brand palette (editorial: navy ink + clay accent)
NAVY = "#1f3a5f"
INK = "#16202e"
CLAY = "#a8482b"
PAPER = "#faf7f1"


def _flags(row: pd.Series) -> str:
    f = []
    if row["reasoning"]:
        f.append("🧠")
    if row["multimodal"]:
        f.append("🖼️")
    if row["tools"]:
        f.append("🔧")
    return " ".join(f) if f else "—"


def _fmt_price(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    if v == 0:
        return "free"
    return f"${v:,.2f}"


def _view(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["flags"] = out.apply(_flags, axis=1)
    out["context_disp"] = out["context_k"].map(lambda k: f"{k:,}K")
    out["in_disp"] = out["price_in"].map(_fmt_price)
    out["out_disp"] = out["price_out"].map(_fmt_price)
    return out[
        ["name", "provider", "context_disp", "in_disp", "out_disp", "flags", "created_str"]
    ]


def build_table(df: pd.DataFrame, title: str, subtitle: str) -> GT:
    """Styled great-tables table from a (already-sliced) models DataFrame."""
    view = _view(df)
    gt = (
        GT(view)
        .tab_header(title=title, subtitle=subtitle)
        .cols_label(
            name="Model",
            provider="Provider",
            context_disp="Context",
            in_disp="$/1M in",
            out_disp="$/1M out",
            flags="Caps",
            created_str="Added",
        )
        .cols_align("right", columns=["context_disp", "in_disp", "out_disp"])
        .cols_align("center", columns=["flags"])
        .tab_source_note(
            md("🧠 reasoning · 🖼️ multimodal · 🔧 tools · Data: [OpenRouter](https://openrouter.ai)")
        )
        .opt_table_font(font="IBM Plex Sans")
        .tab_options(
            table_background_color=PAPER,
            heading_title_font_size="20px",
            heading_title_font_weight="600",
            heading_subtitle_font_size="13px",
            column_labels_background_color=NAVY,
            column_labels_font_weight="600",
            table_font_size="13px",
            row_striping_include_table_body=True,
        )
    )
    gt = gt.tab_style(
        style=style.text(color=NAVY, weight="600"),
        locations=loc.body(columns=["name"]),
    )
    return gt


def newest_table(df: pd.DataFrame, n: int = 12) -> GT:
    return build_table(
        df.sort_values("created", ascending=False).head(n),
        title="Newest models",
        subtitle="Most recently added to the OpenRouter catalog",
    )


def cheapest_capable_table(df: pd.DataFrame, n: int = 12) -> GT:
    cap = df[(df["price_in"].notna()) & (df["price_in"] > 0) & (df["context_k"] >= 100)]
    return build_table(
        cap.sort_values("price_in").head(n),
        title="Cheapest capable models",
        subtitle="≥100K context, lowest input price ($/1M tokens)",
    )
