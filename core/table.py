"""Lieflat-styled data tables rendered to PNG for PPT embedding."""

from __future__ import annotations

import io
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

from core.charts import STYLE_PRESETS, FONT

_RGBA_RE = re.compile(r"rgba?\(([^)]+)\)")


def _to_mpl_color(color: str) -> tuple:
    """Convert CSS #hex or rgba(r,g,b,a) strings into matplotlib-compatible tuples."""
    if isinstance(color, tuple):
        return color
    m = _RGBA_RE.match(str(color).strip())
    if m:
        parts = [float(p.strip()) for p in m.group(1).split(",")]
        if len(parts) == 3:
            parts.append(1.0)
        r, g, b, a = parts
        return (r / 255.0, g / 255.0, b / 255.0, a)
    return color


def _available_font() -> str:
    for name in ["Inter", "Noto Sans SC", "PingFang SC", "Arial Unicode MS", "Heiti SC", "Arial"]:
        try:
            font_manager.findfont(name, fallback_to_default=False)
            return name
        except Exception:
            continue
    return "DejaVu Sans"


def _is_total_row(value) -> bool:
    """Recognize explicit total labels used by Lieflat's ledger table."""
    return str(value).strip().casefold() in {"合计", "总计", "total"}


def style_dataframe(df: pd.DataFrame, preset: str = "Porcelain"):
    """Apply Lieflat's clean ledger typography to a native Streamlit dataframe."""
    theme = STYLE_PRESETS.get(preset, STYLE_PRESETS["Porcelain"])
    quiet = theme.get("quiet", theme["grid"])
    lab = theme.get("label", theme["muted"])
    styles = [
        {
            "selector": "thead th",
            "props": [
                ("font-family", "Inter, Noto Sans SC, sans-serif"),
                ("font-size", "8.5px"),
                ("font-weight", "700"),
                ("letter-spacing", ".12em"),
                ("color", theme["muted"]),
                ("background-color", theme["background"]),
                ("border", "0"),
                ("border-bottom", f"1px solid {theme['ink']}"),
                ("padding", "0 0 7px"),
                ("text-align", "right"),
            ],
        },
        {
            "selector": "thead th:first-child, tbody th",
            "props": [("text-align", "left"), ("color", lab)],
        },
        {
            "selector": "tbody td",
            "props": [
                ("font-family", "Inter, Noto Sans SC, sans-serif"),
                ("font-size", "10.5px"),
                ("padding", "6.5px 0"),
                ("border-top", "0"),
                ("border-left", "0"),
                ("border-right", "0"),
                ("border-bottom", f"1px dotted {quiet}"),
                ("text-align", "right"),
            ],
        },
        {
            "selector": "tbody td:first-child",
            "props": [
                ("text-align", "left"),
                ("color", lab),
                ("font-size", "9px"),
                ("font-weight", "700"),
                ("letter-spacing", ".1em"),
            ],
        },
    ]
    styled = (
        df.style.set_table_styles(styles, overwrite=False)
        .set_properties(**{
            "background-color": theme["background"],
            "color": theme["ink"],
            "font-family": "Inter, Noto Sans SC, sans-serif",
            "font-size": "10.5px",
            "font-weight": "600",
            "font-variant-numeric": "tabular-nums lining-nums",
        })
    )

    # The source table gives its final total row one ink rule and a single
    # preset-colored emphasis. Keep that semantic treatment when present.
    if len(df.columns):
        def total_row_style(row):
            if _is_total_row(row.iloc[0]):
                return [
                    f"border-top: 1px solid {theme['ink']}; border-bottom: 0; "
                    f"font-weight: 800; color: {theme['primary']}"
                ] * len(row)
            return [""] * len(row)

        styled = styled.apply(total_row_style, axis=1)
    return styled


def style_table(df: pd.DataFrame, preset: str = "Porcelain", title: str = "", max_rows: int = 30):
    """Render a DataFrame as a Lieflat-styled matplotlib figure."""
    theme = STYLE_PRESETS.get(preset, STYLE_PRESETS["Porcelain"])
    font = _available_font()
    plt.rcParams["font.family"] = font
    plt.rcParams["axes.unicode_minus"] = False

    show_df = df.head(max_rows).copy()
    n_rows, n_cols = show_df.shape
    fig_w = max(6, n_cols * 1.6)
    fig_h = max(2.5, (n_rows + 1) * 0.45 + (1.2 if title else 0.6))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    ax.set_axis_off()

    cell_text = show_df.astype(str).values.tolist()
    col_labels = [str(c) for c in show_df.columns]

    table = ax.table(
        cellText=cell_text, colLabels=col_labels, cellLoc="right", loc="center",
        colWidths=[1 / n_cols] * n_cols,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10.5)
    table.scale(1, 1.42)
    paper = _to_mpl_color(theme["background"])
    rule = _to_mpl_color(theme.get("quiet", theme["grid"]))
    ink = _to_mpl_color(theme["ink"])
    muted = _to_mpl_color(theme["muted"])
    label = _to_mpl_color(theme.get("label", theme["muted"]))
    fig.patch.set_facecolor(paper)
    ax.set_facecolor(paper)

    # Lieflat report ledger: no colored header block or box grid; a strong
    # header rule and dotted row separators carry the table structure.
    for j in range(n_cols):
        cell = table[0, j]
        cell.set_facecolor(paper)
        cell.visible_edges = "B"
        cell.set_edgecolor(ink)
        cell.set_linewidth(1.0)
        cell.set_text_props(color=muted, fontweight="bold", fontsize=8.5)
        cell.get_text().set_ha("left" if j == 0 else "right")

    # Body: generous whitespace, first column as row label, dotted hairlines.
    for i in range(1, n_rows + 1):
        for j in range(n_cols):
            cell = table[i, j]
            cell.set_facecolor(paper)
            cell.visible_edges = "B"
            cell.set_edgecolor(rule)
            cell.set_linewidth(0.6)
            cell.set_linestyle(":")
            is_total = _is_total_row(show_df.iloc[i - 1, 0]) if n_cols else False
            if is_total:
                cell.visible_edges = "T"
                cell.set_edgecolor(ink)
                cell.set_linewidth(1.0)
                cell.set_linestyle("-")
                cell.set_text_props(color=_to_mpl_color(theme["primary"]), fontsize=9 if j == 0 else 10.5, fontweight="bold")
            else:
                cell.set_text_props(color=label if j == 0 else ink, fontsize=9 if j == 0 else 10.5, fontweight="bold" if j == 0 else "medium")
            cell.get_text().set_ha("left" if j == 0 else "right")

    title_y = 1.02 if title else 0.96
    if title:
        ax.set_title(title, fontsize=16.5, fontweight="bold", color=ink, pad=12, loc="left")
    # Source line
    fig.text(0.02, 0.01, "来源：DATAINSIGHT", fontsize=8.5, color=_to_mpl_color(theme["faint"]), weight="medium", ha="left")

    fig.tight_layout(rect=[0, 0.03, 1, title_y])
    return fig


def export_table_png(df: pd.DataFrame, path: str, preset: str = "Porcelain", title: str = "", max_rows: int = 30) -> str:
    fig = style_table(df, preset, title, max_rows)
    fig.savefig(path, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def table_to_png_bytes(df: pd.DataFrame, preset: str = "Porcelain", title: str = "", max_rows: int = 30) -> bytes:
    fig = style_table(df, preset, title, max_rows)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()
