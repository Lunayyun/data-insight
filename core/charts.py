"""Presentation-ready Plotly charts following the Lieflat visual grammar.

Color tokens are ported 1:1 from lieflat-charts `mono-tokens.js` (Mono) and
`color-presets.js` (Porcelain / Palm / Wire) — the canonical source of truth.
"""

from __future__ import annotations

from io import BytesIO
import json
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image

# Exact lieflat colors (see /Users/luna/Desktop/lieflat-charts/color-presets.js)
COLORS = ["#334EAC", "#D4A017", "#F5572F", "#43593B", "#081F5C"]

# Layout tokens from mono-tokens.js
CARD_RADIUS = 24      # SHAPE.cardRadius
BAR_RADIUS = 99       # SHAPE.barRadius (capsule bar ends)

STYLE_PRESETS = {
    # ── Mono: 纸灰底 + 炭黑墨，明度即数据 ──
    "Mono": {
        "background": "#F0EFEB",   # PAPER
        "ink": "#1C1C1A",          # INK
        "muted": "#8F8E88",        # MUTED
        "faint": "#C6C5BF",        # FAINT (source line)
        "grid": "#DEDDD6",         # GRID (hairline)
        "primary": "#1C1C1A",      # INK
        "secondary": "#8F8E88",
        "accent": "#4A4944",       # L[1]
        "palette": ["#1C1C1A", "#4A4944", "#6A6963", "#8F8E88", "#B0AFA9", "#C6C5BF", "#D8D7D1"],
        "categories": ["#1C1C1A", "#4A4944", "#8F8E88", "#C6C5BF"],
        "heat": ["#1C1C1A", "#6A6963", "#B0AFA9"],
        "highlight_first_category": False,
        "label": "#8F8E88",
        "floor": "#C6C5BF",
        "quiet": "#C6C5BF",
        "track": "#CFCEC7",
        "zebra": "#E6E5DE",
    },
    # ── Porcelain 青瓷蓝: 单色相蓝阶，明度=数值 ──
    "Porcelain": {
        "background": "#F7F2EB",   # BG
        "ink": "#081F5C",          # TXT (deep navy)
        "muted": "rgba(8,31,92,.60)",  # MUT
        "faint": "rgba(8,31,92,.32)",
        "grid": "rgba(8,31,92,.16)",
        "primary": "#334EAC",      # DATA
        "secondary": "#7096D1",    # DATA2
        "accent": "#081F5C",       # HERO
        "palette": ["#334EAC", "#081F5C", "#7096D1", "#BAD6EB", "#D0E3FF", "rgba(51,78,172,.4)"],
        "categories": ["#081F5C", "#334EAC", "#7096D1", "#BAD6EB"],
        "label": "rgba(8,31,92,.72)",
        "floor": "rgba(8,31,92,.24)",
        "quiet": "rgba(8,31,92,.15)",
        "track": "rgba(8,31,92,.12)",
        "heat": ["#334EAC", "#7096D1", "#BAD6EB"],
        "highlight_first_category": False,
        "zebra": "#ECE6DB",
    },
    # ── Palm 椰林绿: 色相=类目，琥珀=唯一重点 ──
    "Palm": {
        "background": "#F0EFEB",   # BG
        "ink": "#58402E",          # TXT (deep brown)
        "muted": "rgba(88,64,46,.60)",
        "faint": "rgba(88,64,46,.32)",
        "grid": "rgba(88,64,46,.16)",
        "primary": "#43593B",      # DATA (deep green)
        "secondary": "#77835A",
        "accent": "#D4A017",       # HERO (amber)
        "palette": ["#43593B", "#D4A017", "#77835A", "#F2D17E", "#ACAD79", "#58402E"],
        "categories": ["#43593B", "#77835A", "#ACAD79", "#F2D17E"],
        "label": "rgba(88,64,46,.72)",
        "floor": "rgba(88,64,46,.24)",
        "quiet": "rgba(88,64,46,.15)",
        "track": "rgba(88,64,46,.12)",
        "heat": ["#43593B", "#929960", "#F2D17E"],
        "highlight_first_category": False,
        "zebra": "#E8E7E0",
    },
    # ── Wire 编辑部红: 灰阶 + 一个荧光橙视线落点 ──
    "Wire": {
        "background": "#F0F0EE",   # BG
        "ink": "#1F1E1C",          # TXT
        "muted": "rgba(31,30,28,.60)",
        "faint": "rgba(31,30,28,.32)",
        "grid": "rgba(31,30,28,.16)",
        "primary": "#22211F",      # DATA
        "secondary": "#8F8E86",    # DATA2
        "accent": "#F5572F",       # HERO (fluorescent orange, one element only)
        "palette": ["#22211F", "#8F8E86", "#C0BFB7", "rgba(34,33,31,.52)", "#DBDAD3", "rgba(34,33,31,.3)"],
        "categories": ["#F5572F", "#22211F", "#8F8E86", "#C0BFB7"],
        "label": "rgba(31,30,28,.72)",
        "floor": "rgba(31,30,28,.24)",
        "quiet": "rgba(31,30,28,.15)",
        "track": "rgba(31,30,28,.12)",
        "heat": ["#F5572F", "#6E6D66", "#C0BFB7"],
        "highlight_first_category": True,
        "zebra": "#E6E5E1",
    },
}

FONT = "Inter, Arial, sans-serif"


def _preset(preset: str) -> dict:
    return STYLE_PRESETS.get(preset, STYLE_PRESETS["Porcelain"])


def _stable_noise(index: int, key: int) -> float:
    """Match the deterministic ``rnd`` helper in lieflat's mono-tokens.js."""
    return abs(((int(index) * 73856093) ^ (int(key) * 19349663)) % 1000) / 1000.0


def apply_theme(
    fig: go.Figure,
    title: str,
    subtitle: str = "",
    source: str = "",
    preset: str = "Porcelain",
    mode: str = "Basics",
) -> go.Figure:
    """Apply the Lieflat visual grammar: hairline grid, source line, subtitle, generous margin."""
    theme = _preset(preset)
    compact = mode == "Glance"
    editorial = mode == "Lupi"

    # Lieflat mono-tokens: card title 16.5px/700, sub 11.5px, axis 9.5px, source 9.5px.
    title_full = f"<b>{title}</b>"
    if subtitle:
        title_full += f'<br><span style="font-size:11.5px;color:{theme["muted"]};font-weight:400;">{subtitle}</span>'

    fig.update_layout(
        title={
            "text": title_full,
            "x": 0.0, "xanchor": "left",
            "y": 0.98, "yanchor": "top",
            "font": {"size": 22 if compact else 16.5, "weight": "bold", "color": theme["ink"], "family": FONT},
        },
        font={"family": FONT, "color": theme["ink"], "size": 12},
        paper_bgcolor=theme["background"],
        plot_bgcolor=theme["background"],
        margin={"l": 28, "r": 28, "t": 72 if subtitle else 48, "b": 48},
        colorway=theme["palette"],
        legend={
            "orientation": "h", "y": 1.02, "x": 0,
            "font": {"color": theme["muted"], "size": 11.5},
            "bgcolor": "rgba(0,0,0,0)",
        },
        hoverlabel={"bgcolor": theme["ink"], "font": {"color": theme["background"], "family": FONT}},
    )
    # Hairline grid (Lieflat: countable ticks, 0.5px equivalent, no zeroline)
    fig.update_xaxes(
        showline=True, linecolor=theme["grid"], linewidth=1,
        gridcolor=theme["grid"], gridwidth=1, zeroline=False,
        tickfont={"color": theme["muted"], "size": 9.5},
        showticklabels=not editorial,
        title_font={"color": theme["muted"], "size": 10},
    )
    fig.update_yaxes(
        showline=False,
        gridcolor=theme["grid"], gridwidth=1, zeroline=False,
        tickfont={"color": theme["muted"], "size": 9.5},
        title_font={"color": theme["muted"], "size": 10},
    )
    # Source line: lieflat 9.5px, letter-spacing .08em, uppercase
    if source:
        fig.add_annotation(
            text=f"来源：{source}".upper(),
            xref="paper", yref="paper", x=0.0, y=-0.13,
            showarrow=False,
            font={"color": theme["faint"], "size": 9.5, "family": FONT},
        )
    # Mode-specific trace styling (Glance bold, Lupi hairline)
    if compact:
        fig.update_traces(marker={"line": {"width": 0}}, line={"width": 3.2}, selector={"type": "scatter"})
    elif editorial:
        fig.update_traces(line={"width": 1.2}, marker={"size": 6}, selector={"type": "scatter"})
    return fig


def recommend_chart_type(df: pd.DataFrame, x_column: str, y_column: str | None = None) -> str:
    """Recommend a chart type based on the column dtypes."""
    x_values = _column_series(df, x_column)
    x_dtype = x_values.dtype
    is_time = pd.api.types.is_datetime64_any_dtype(x_values) or "date" in x_column.lower() or "日期" in x_column
    is_numeric_x = pd.api.types.is_numeric_dtype(x_values)
    n_unique = x_values.nunique(dropna=True)

    if is_time:
        return "折线图"
    if y_column and pd.api.types.is_numeric_dtype(_column_series(df, y_column)) and n_unique <= 15:
        return "柱状图"
    if y_column and pd.api.types.is_numeric_dtype(_column_series(df, y_column)) and is_numeric_x and n_unique > 15:
        return "散点图"
    if n_unique <= 15:
        return "分类分布"
    if is_numeric_x and y_column and pd.api.types.is_numeric_dtype(_column_series(df, y_column)):
        return "散点图"
    return "柱状图"


def _column_series(df: pd.DataFrame, column: str) -> pd.Series:
    """Return the first matching column even when an input file has duplicate headers."""
    positions = [index for index, name in enumerate(df.columns) if name == column]
    if not positions:
        raise ValueError(f"找不到字段：{column}")
    return df.iloc[:, positions[0]]


def build_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_column: str,
    y_column: str,
    group_column: str | None = None,
    preset: str = "Porcelain",
    mode: str = "Basics",
    source: str = "DataInsight",
) -> go.Figure:
    # Give every selected role a unique internal name. A user may choose the
    # same column as x, y, or group; selecting it more than once by label makes
    # pandas return a DataFrame instead of a Series and breaks every renderer.
    chart_data = pd.DataFrame({"_x": _column_series(df, x_column), "_y": _column_series(df, y_column)})
    if group_column:
        chart_data["_group"] = _column_series(df, group_column)
    chart_data["_y"] = pd.to_numeric(chart_data["_y"], errors="coerce")
    chart_data = chart_data.dropna(subset=["_x", "_y"])
    color_column = "_group" if group_column else None
    if chart_type == "折线图":
        fig = px.line(chart_data.sort_values("_x"), x="_x", y="_y", color=color_column, markers=True)
    elif chart_type == "柱状图":
        keys = ["_x"] + (["_group"] if group_column else [])
        grouped = chart_data.groupby(keys, dropna=False, as_index=False)["_y"].sum()
        fig = px.bar(grouped, x="_x", y="_y", color=color_column or "_x", text_auto=".2s", barmode="group")
        # Lieflat barRadius=99: capsule top ends only
        fig.update_traces(marker_line_width=0, marker={"cornerradius": [BAR_RADIUS] * len(grouped)})
    elif chart_type == "散点图":
        # Plotly's OLS trendline requires a numeric x-axis. Lieflat still
        # supports categorical scatter data, so only request OLS when valid.
        if pd.api.types.is_numeric_dtype(chart_data["_x"]):
            fig = px.scatter(chart_data, x="_x", y="_y", color=color_column, trendline="ols")
        else:
            fig = px.scatter(chart_data, x="_x", y="_y", color=color_column)
    elif chart_type == "面积图":
        fig = px.area(chart_data.sort_values("_x"), x="_x", y="_y", color=color_column)
    elif chart_type == "饼图":
        counts = chart_data["_x"].value_counts().head(8).rename_axis("_x").reset_index(name="数量")
        fig = px.pie(counts, names="_x", values="数量", hole=0.45)
        fig.update_traces(textposition="outside", textinfo="percent+label")
    elif chart_type == "热力图":
        if group_column:
            pivot = chart_data.pivot_table(index="_group", columns="_x", values="_y", aggfunc="sum", fill_value=0)
        else:
            # With no grouping field, show the distribution of y values across
            # x categories using quantile bands instead of a mostly-diagonal
            # y-by-y pivot.
            unique_y = chart_data["_y"].nunique()
            if unique_y > 1:
                chart_data["_band"] = pd.qcut(chart_data["_y"], q=min(5, unique_y), duplicates="drop")
            else:
                chart_data["_band"] = "值"
            pivot = chart_data.pivot_table(index="_band", columns="_x", values="_y", aggfunc="count", fill_value=0, observed=True)
        fig = px.imshow(pivot, aspect="auto", text_auto=".2s")
    else:  # 分类分布
        counts = chart_data["_x"].value_counts().head(12).rename_axis("_x").reset_index(name="数量")
        fig = px.bar(counts, x="_x", y="数量", color="_x", text_auto=True)
    return apply_theme(fig, f"{y_column} · {chart_type}", source=source, preset=preset, mode=mode)


def export_chart_png(fig: go.Figure, path: str, width: int = 1600, height: int = 900) -> str:
    """Export a chart to a high-resolution PNG (≥150 DPI equivalent)."""
    try:
        fig.write_image(path, format="png", width=width, height=height, scale=2)
    except Exception:
        # Kaleido needs a separately installed browser. Keep the local app's
        # export action useful when that optional binary is unavailable.
        _fallback_chart_png(fig, path, width, height)
    return path


def chart_to_pil(fig: go.Figure, width: int = 1600, height: int = 900) -> Image.Image:
    """Return the chart as a PIL Image for PPTX embedding."""
    buffer = BytesIO()
    try:
        fig.write_image(buffer, format="png", width=width, height=height, scale=2)
    except Exception:
        _fallback_chart_png(fig, buffer, width, height)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def _fallback_chart_png(fig: go.Figure, destination, width: int, height: int) -> None:
    """Draw a small dependency-free preview when Plotly's browser export fails."""
    from PIL import ImageDraw, ImageFont

    paper = STYLE_PRESETS["Porcelain"]["background"]
    ink = STYLE_PRESETS["Porcelain"]["ink"]
    # PIL accepts hex/rgb colors but not CSS rgba() strings used by the SVG.
    grid = "#D0E3FF"
    palette = STYLE_PRESETS["Porcelain"]["palette"]
    image = Image.new("RGB", (width, height), paper)
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 30)
        label_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    except OSError:
        title_font = label_font = ImageFont.load_default()
    title = str(getattr(fig.layout.title, "text", "DataInsight chart") or "DataInsight chart")
    draw.text((48, 34), title.replace("<br>", " · ").replace("<b>", "").replace("</b>", ""), fill=ink, font=title_font)
    l, t, r, b = 90, 120, width - 55, height - 95
    for i in range(5):
        y = b - (b - t) * i / 4
        draw.line((l, y, r, y), fill=grid, width=2)
    for index, trace in enumerate(fig.data):
        raw_values = getattr(trace, "y", None)
        if raw_values is None or len(raw_values) == 0:
            raw_values = getattr(trace, "values", None)
        values = list(raw_values) if raw_values is not None else []
        if not values:
            continue
        numeric = []
        for value in values:
            try:
                numeric.append(float(value))
            except (TypeError, ValueError):
                numeric.append(0.0)
        maximum = max(max(numeric), 1e-9)
        kind = str(getattr(trace, "type", "scatter"))
        color = palette[index % len(palette)]
        if kind in {"bar", "histogram"}:
            slot = (r - l) / max(len(numeric), 1)
            for i, value in enumerate(numeric):
                x0 = l + i * slot + slot * .18
                x1 = l + (i + 1) * slot - slot * .18
                y0 = b
                y1 = b - (b - t) * value / maximum
                draw.rounded_rectangle((x0, y1, x1, y0), radius=8, fill=color)
        elif kind in {"pie", "funnelarea"}:
            total = sum(max(value, 0) for value in numeric) or 1
            start = 0
            box = (l + 180, t + 12, l + 520, t + 352)
            for i, value in enumerate(numeric):
                extent = 360 * max(value, 0) / total
                draw.pieslice(box, start, start + extent, fill=palette[i % len(palette)])
                start += extent
        else:
            points = []
            for i, value in enumerate(numeric):
                x = l + (r - l) * i / max(len(numeric) - 1, 1)
                y = b - (b - t) * value / maximum
                points.append((x, y))
            if len(points) > 1:
                draw.line(points, fill=color, width=4, joint="curve")
            for x, y in points:
                draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=paper, outline=color, width=3)
    draw.text((l, height - 56), "Lieflat SVG/Plotly preview · 数据仍在本地处理", fill=ink, font=label_font)
    if hasattr(destination, "write"):
        image.save(destination, format="PNG")
    else:
        image.save(destination, format="PNG")


def lieflat_chart_html(
    df: pd.DataFrame,
    chart_type: str,
    x_column: str,
    y_column: str,
    group_column: str | None = None,
    preset: str = "Porcelain",
    mode: str = "Basics",
    source: str = "DataInsight",
) -> str:
    """Create a self-contained SVG chart using the real Lieflat Basics structures.

    The component deliberately has no CDN dependency, so it keeps working in
    Streamlit's sandboxed iframe and when the browser cannot reach a chart CDN.
    """
    theme = _preset(preset)
    data = pd.DataFrame({"_x": _column_series(df, x_column), "_y": _column_series(df, y_column)})
    data["_y"] = pd.to_numeric(data["_y"], errors="coerce")
    if group_column:
        data["_group"] = _column_series(df, group_column).fillna("未填写").astype(str)
    data = data.dropna(subset=["_x", "_y"]).head(500).copy()
    data["_label"] = data["_x"].map(str)
    numeric_x = pd.api.types.is_numeric_dtype(data["_x"])
    time_x = pd.api.types.is_datetime64_any_dtype(data["_x"]) or "date" in x_column.lower() or "日期" in x_column
    if time_x:
        data = data.sort_values("_x", kind="stable")
    labels = list(dict.fromkeys(data["_label"].tolist()))
    groups = list(dict.fromkeys(data["_group"].tolist())) if group_column else []

    # Keep grouped charts readable while preserving the tail as a real aggregate.
    if len(groups) > 6:
        totals = data.groupby("_group", sort=False)["_y"].sum().sort_values(ascending=False)
        kept = totals.index[:5].tolist()
        data["_group"] = data["_group"].where(data["_group"].isin(kept), "其他分组")
        groups = list(dict.fromkeys(data["_group"].tolist()))

    datasets = []
    cells = []
    row_labels = []
    note = "悬停查看明细 · 点击重播动效"
    group_keys = groups if groups else [None]

    if chart_type in {"饼图", "分类分布"}:
        if chart_type == "分类分布":
            counts = data.groupby("_label", sort=False).size().sort_values(ascending=False)
            if len(counts) > 6:
                other_count = len(counts) - 5
                other_total = int(counts.iloc[5:].sum())
                counts = counts.iloc[:5].copy()
                counts.loc["其他（%d 类）" % other_count] = other_total
            labels = counts.index.astype(str).tolist()
            datasets = [{"label": "记录数", "values": [int(v) for v in counts.values]}]
            note = "横档表示相对记录数 · 精确数量见标签"
        else:
            totals = data.groupby("_label", sort=False)["_y"].sum().sort_values(ascending=False)
            totals = totals[totals > 0]
            if len(totals) > 6:
                other = float(totals.iloc[5:].sum())
                totals = totals.iloc[:5].copy()
                totals.loc["其他（%d 类）" % (len(data.groupby("_label")) - 5)] = other
            labels = totals.index.astype(str).tolist()
            datasets = [{"label": y_column, "values": [float(v) for v in totals.values]}]
            note = "每一档约等于 1% · 悬停查看精确占比"
    elif chart_type == "散点图":
        if numeric_x:
            data["_plot_x"] = pd.to_numeric(data["_x"], errors="coerce")
            x_labels = []
        else:
            x_labels = labels
            x_map = {label: index for index, label in enumerate(x_labels)}
            data["_plot_x"] = data["_label"].map(x_map)
        for group in group_keys:
            rows = data if group is None else data[data["_group"] == group]
            points = []
            for _, row in rows.iterrows():
                if pd.notna(row["_plot_x"]):
                    label = str(group) if group is not None else y_column
                    points.append({
                        "x": float(row["_plot_x"]),
                        "y": float(row["_y"]),
                        "tip": "%s · %s=%s · %s=%s" % (
                            label, x_column, row["_label"], y_column, format(float(row["_y"]), ".5g")
                        ),
                    })
            datasets.append({"label": str(group) if group is not None else y_column, "points": points})
        note = "每个点代表一条记录 · 细线垂至横轴读取 X 值"
    elif chart_type == "热力图":
        if group_column:
            row_labels = groups
            heat_data = data.assign(_row=data["_group"])
            aggregate = "sum"
            note = "圆点面积表示聚合值 · 悬停读取精确数值"
        else:
            unique = int(data["_y"].nunique())
            if unique > 1:
                bins = min(5, unique)
                heat_data = data.assign(_row=pd.qcut(data["_y"], q=bins, duplicates="drop").astype(str))
            else:
                heat_data = data.assign(_row="全部记录")
            row_labels = list(dict.fromkeys(heat_data["_row"].tolist()))
            aggregate = "count"
            note = "行按指标值分段 · 圆点面积表示记录数"
        # Limit the matrix width; the omitted categories are combined as one honest tail bucket.
        if len(labels) > 18:
            totals = data.groupby("_label", sort=False)["_y"].sum().sort_values(ascending=False)
            kept = totals.index[:17].tolist()
            data["_label"] = data["_label"].where(data["_label"].isin(kept), "其他类别")
            heat_data["_label"] = heat_data["_label"].where(heat_data["_label"].isin(kept), "其他类别")
            labels = kept + (["其他类别"] if len(totals) > 17 else [])
        for yi, row_label in enumerate(row_labels):
            for xi, label in enumerate(labels):
                selected = heat_data[(heat_data["_row"] == row_label) & (heat_data["_label"] == label)]
                value = float(selected["_y"].sum()) if aggregate == "sum" else int(len(selected))
                cells.append({"x": xi, "y": yi, "v": value, "row": str(row_label), "label": label})
    else:
        # Continuous series keep their original order; category comparisons use a
        # stable value ranking and a readable tail bucket when there are many.
        if chart_type == "柱状图":
            totals = data.groupby("_label", sort=False)["_y"].sum().sort_values(ascending=False)
            if len(totals) > 18:
                kept = totals.index[:17].tolist()
                data["_label"] = data["_label"].where(data["_label"].isin(kept), "其他类别")
                labels = kept + ["其他类别"]
            else:
                labels = totals.index.astype(str).tolist()
        for group in group_keys:
            rows = data if group is None else data[data["_group"] == group]
            aggregated = rows.groupby("_label", sort=False)["_y"].sum()
            datasets.append({"label": str(group) if group is not None else y_column,
                             "values": [float(aggregated[label]) if label in aggregated else None for label in labels]})
        note = "横档表示相对大小 · 标签保留精确值"
        if chart_type == "折线图":
            note = "逐点保留数据 · 点击可重播绘制动画"
        elif chart_type == "面积图":
            note = "发丝刻线构成面积 · 数据走势由顶边表示"

    # Basics gallery uses a 400×320 card canvas. Keeping this viewBox fixed is
    # what makes the hairline, label and tick proportions match the source
    # implementation at every iframe width.
    W, H = 400, 320
    left, right, top, bottom = 28, 22, 22, 54
    plot_w, plot_h = W - left - right, H - top - bottom
    svg_parts = ['<svg class="plot-svg" viewBox="0 0 %d %d" role="img" aria-label="%s" xmlns="http://www.w3.org/2000/svg">' % (W, H, escape(y_column + " " + chart_type, quote=True))]
    colors = theme["palette"] or [theme["primary"]]
    group_colors = {name: colors[index % len(colors)] for index, name in enumerate([dataset["label"] for dataset in datasets])}

    def fnum(value):
        return ("%.2f" % float(value)).rstrip("0").rstrip(".")

    def mark(tag, attrs, tip_text, css="fade"):
        attrs = dict(attrs)
        attrs.update({"class": css, "tabindex": "0", "role": "img", "data-tip": tip_text})
        attr_text = " ".join('%s="%s"' % (key, escape(str(value), quote=True)) for key, value in attrs.items())
        return "<%s %s><title>%s</title></%s>" % (tag, attr_text, escape(tip_text), tag)

    def axis_label(text, x, y, anchor="middle", rotate=None):
        transform = ' transform="rotate(%s %s %s)"' % (rotate, fnum(x), fnum(y)) if rotate is not None else ""
        return '<text x="%s" y="%s" text-anchor="%s" fill="%s" font-size="10"%s>%s</text>' % (fnum(x), fnum(y), anchor, theme["muted"], transform, escape(str(text)[:24]))

    if not data.empty and chart_type == "分类分布":
        # C1 · tick rows — the gallery's horizontal queue, one tick per record.
        values = datasets[0]["values"] if datasets else []
        max_value = max([float(v or 0) for v in values] + [1])
        row_gap = min(44, 220 / max(1, len(labels) - 1))
        x0, rung_gap, max_rungs = 104, 6.9, 34
        tick_unit = max(1, max_value / max_rungs)
        row_colors = theme.get("categories", colors)
        for i, (label, value) in enumerate(zip(labels, values)):
            y = 52 + i * row_gap
            shade = theme["accent"] if theme.get("highlight_first_category") and i == 0 else theme["primary"]
            svg_parts.append('<text x="94" y="%s" text-anchor="end" fill="%s" font-size="8" font-weight="700" letter-spacing=".08em" class="fade">%s</text>' % (fnum(y+3), theme.get("label", theme["muted"]), escape(str(label)[:16].upper())))
            svg_parts.append('<line x1="%s" y1="%s" x2="338" y2="%s" stroke="%s" stroke-width=".6" class="fade"/>' % (x0, fnum(y+9), fnum(y+9), theme["grid"]))
            count = max(0, int(round(float(value or 0) / tick_unit)))
            for k in range(count):
                x = x0 + (k + .5) * rung_gap
                height = 9 + _stable_noise(k + 1, i + 2) * 6
                tip_text = "%s · %s：%s" % (label, y_column, format(float(value or 0), ".6g"))
                svg_parts.append(mark("line", {"x1": fnum(x), "y1": fnum(y+9), "x2": fnum(x), "y2": fnum(y+9-height), "stroke": shade, "stroke-width": "1.7" if preset != "Mono" else ".9", "opacity": fnum(.85 + _stable_noise(k+3, i+5)*.15), "data-series": datasets[0]["label"], "style": "animation-delay:%ss" % fnum(i*.08+k*.012)}, tip_text, "fade"))
                if k % 5 == 4:
                    svg_parts.append('<circle cx="%s" cy="%s" r=".8" fill="%s" class="fade"/>' % (fnum(x), fnum(y+13), theme["faint"]))
            svg_parts.append(mark("text", {"x": fnum(x0 + count * rung_gap + 10), "y": fnum(y+4), "font-size": "11", "font-weight": "800", "fill": theme["ink"], "data-series": datasets[0]["label"]}, str(value), "fade"))
        note = "ONE TICK ≈ %s RECORDS · DOT MARKS EVERY FIFTH" % format(tick_unit, ".3g")
        svg_parts.append('<text x="200" y="308" text-anchor="middle" fill="%s" font-size="7" font-weight="600" letter-spacing=".12em" class="fade">%s</text>' % (theme["faint"], escape(note.upper())))
    elif not data.empty and chart_type == "柱状图":
        # B1 · rung bars — exact Basics geometry, with grouped rungs when a
        # series column is selected.
        vals = [float(v or 0) for dataset in datasets for v in dataset["values"]]
        max_value = max(vals + [1.0])
        scale = max_value / 38.0
        step = 5.6
        base = 266
        cat_n = max(1, len(labels))
        x_at = lambda i: 56 + i * (288 / max(1, cat_n - 1)) if cat_n > 1 else 200
        series_n = max(1, len(datasets))
        for i, label in enumerate(labels):
            for si, dataset in enumerate(datasets):
                value = float(dataset["values"][i] or 0)
                if value <= 0:
                    continue
                offset = (si - (series_n - 1) / 2) * min(20, 30 / series_n)
                x = x_at(i) + offset
                count = max(1, min(38, int(round(value / scale))))
                shade = group_colors[dataset["label"]]
                if preset == "Wire" and len(datasets) == 1 and i == 0:
                    shade = theme["accent"]
                rung_width = min(14, max(7, 24 / series_n))
                tip_text = "%s · %s：%s" % (dataset["label"], label, format(value, ".6g"))
                for k in range(count):
                    yy = base - k * step
                    width = rung_width - 1.5 + _stable_noise(k + 1, i + si + 2) * 3
                    svg_parts.append(mark("line", {"x1": fnum(x-width), "y1": fnum(yy), "x2": fnum(x+width), "y2": fnum(yy), "stroke": shade, "stroke-width": "1.8" if preset != "Mono" else "1", "opacity": fnum(.85 + _stable_noise(k+2, i+si+4)*.15) if preset != "Mono" else fnum(.5 + _stable_noise(k+2, i+si+4)*.5), "data-series": dataset["label"], "style": "animation-delay:%ss" % fnum(i*.08+k*.012)}, tip_text, "fade"))
                    if k % 5 == 4:
                        svg_parts.append('<circle cx="%s" cy="%s" r=".8" fill="%s" class="fade"/>' % (fnum(x+rung_width+4.5), fnum(yy), theme["faint"]))
                top_y = base - (count - 1) * step
                svg_parts.append(mark("text", {"x": fnum(x), "y": fnum(top_y-10), "font-size": "11", "font-weight": "800", "fill": theme["ink"], "text-anchor": "middle", "data-series": dataset["label"]}, format(value, ".6g"), "fade"))
            svg_parts.append('<text x="%s" y="284" text-anchor="middle" fill="%s" font-size="7.5" font-weight="700" letter-spacing=".08em" class="fade">%s</text>' % (fnum(x_at(i)), theme["muted"], escape(str(label)[:16].upper())))
        svg_parts.append('<line x1="28" y1="270" x2="372" y2="270" stroke="%s" stroke-width=".8" class="fade"/>' % theme["grid"])
        note = "ONE RUNG ≈ %s %s · DOT MARKS EVERY FIFTH" % (format(scale, ".3g"), y_column.upper())
        svg_parts.append('<text x="200" y="306" text-anchor="middle" fill="%s" font-size="7" font-weight="600" letter-spacing=".12em" class="fade">%s</text>' % (theme["faint"], escape(note)))
    elif not data.empty and chart_type in {"折线图", "面积图"}:
        vals = [float(v) for dataset in datasets for v in dataset["values"] if v is not None]
        ymin = min([0.0] + vals); ymax = max(vals) if vals else 1.0
        if ymax <= ymin: ymax = ymin + 1
        baseline = 262
        low_y, high_y = 72, baseline - 4
        map_y = lambda value: high_y - (float(value)-ymin)/(ymax-ymin)*(high_y-low_y)
        cat_n = len(labels)
        x_at = lambda i: 30 + (340 * i / max(1, cat_n-1) if cat_n > 1 else 170)
        # B2/B3 use a barcode floor instead of a conventional axis grid.
        for i, label in enumerate(labels):
            x = x_at(i)
            tick_color = theme.get("track", theme["grid"])
            svg_parts.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width=".6" class="fade" style="animation-delay:%ss"/>' % (fnum(x), baseline, fnum(x), baseline-7, tick_color, fnum(i*.008)))
        svg_parts.append('<line x1="24" y1="262" x2="376" y2="262" stroke="%s" stroke-width=".8" class="fade"/>' % theme["grid"])
        best_points = []
        for si, dataset in enumerate(datasets):
            shade = group_colors[dataset["label"]]
            points = [(x_at(i), map_y(value), value, labels[i]) for i, value in enumerate(dataset["values"]) if value is not None]
            if chart_type == "面积图":
                peak_value = max((point[2] for point in points), default=None)
                for x, yy, value, label in points:
                    is_peak = peak_value is not None and float(value) == float(peak_value)
                    opacity = .8 + _stable_noise(len(best_points)+1, si+7)*.2 if preset != "Mono" else .5 + _stable_noise(len(best_points)+1, si+7)*.5
                    svg_parts.append(mark("line", {"x1": fnum(x), "y1": "262", "x2": fnum(x), "y2": fnum(yy), "stroke": theme["accent"] if is_peak else shade, "stroke-width": "1.6" if is_peak and preset != "Mono" else "1" if preset != "Mono" else ".55", "opacity": fnum(opacity), "data-series": dataset["label"], "style": "animation-delay:%ss" % fnum(si*.08 + len(best_points)*.014)}, "%s · %s：%s" % (dataset["label"], label, format(float(value), ".6g")), "fade"))
                    best_points.append((float(value), x, yy, label, dataset["label"], si))
            if len(points) > 1:
                path = "M" + " L".join("%s %s" % (fnum(x), fnum(yy)) for x, yy, _, _ in points)
                svg_parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round" pathLength="1" class="draw" data-series="%s" style="animation-delay:%ss"/>' % (path, shade, "2.16" if preset != "Mono" else "1.2", escape(dataset["label"], quote=True), fnum(si*.15)))
            for pi, (x, yy, value, label) in enumerate(points):
                tip_text = "%s · %s：%s" % (dataset["label"], label, format(float(value), ".6g"))
                is_weekend = False
                if time_x:
                    try:
                        original = pd.to_datetime(label, errors="coerce")
                        is_weekend = pd.notna(original) and original.dayofweek >= 5
                    except (TypeError, ValueError):
                        is_weekend = False
                # Gallery F2: solid weekday points, hollow weekend points.
                fill = theme["background"] if is_weekend else shade
                stroke_width = 1.8 if preset != "Mono" else 1
                dot_radius = 3.1 if preset != "Mono" else 2.1
                svg_parts.append(mark("circle", {"cx": fnum(x), "cy": fnum(yy), "r": fnum(dot_radius), "fill": fill, "stroke": shade, "stroke-width": fnum(stroke_width if is_weekend else 0), "data-series": dataset["label"], "style": "animation-delay:%ss" % fnum(.2 + pi*.03)}, tip_text, "pop"))
                best_points.append((float(value), x, yy, label, dataset["label"], si))
        if best_points:
            peaks = []
            peak_limit = 2 if chart_type == "折线图" else 1
            for point in sorted(best_points, key=lambda item: item[0], reverse=True):
                if all(abs(point[1]-other[1]) > 25 for other in peaks):
                    peaks.append(point)
                if len(peaks) == peak_limit:
                    break
            for value, x, yy, label, series, si in peaks:
                shade = theme["accent"] if preset in {"Porcelain", "Palm", "Wire"} else theme["ink"]
                svg_parts.append(mark("circle", {"cx": fnum(x), "cy": fnum(yy), "r": "5.2" if preset != "Mono" else "4.2", "fill": shade, "data-series": series}, "%s · %s：%s" % (series, label, format(value, ".6g")), "pop"))
                svg_parts.append('<text x="%s" y="%s" text-anchor="middle" fill="%s" font-size="9.5" font-weight="800" style="paint-order:stroke;stroke:%s;stroke-width:3px" class="fade">%s</text>' % (fnum(x), fnum(yy-11), shade, theme["background"], escape(format(value, ".4g"))))
        if cat_n:
            dates = []
            candidate_indices = sorted(set([0, cat_n//2, cat_n-1]))
            for i in candidate_indices:
                if time_x:
                    date = pd.to_datetime(labels[i], errors="coerce")
                    dates.append(date.strftime("%b %-d").upper() if pd.notna(date) else str(labels[i])[:10])
                else:
                    dates.append(str(labels[i])[:12].upper())
                x = x_at(i)
                anchor = "start" if i == 0 else "end" if i == cat_n-1 else "middle"
                svg_parts.append('<text x="%s" y="280" text-anchor="%s" fill="%s" font-size="7.5" font-weight="600" letter-spacing=".1em" class="fade">%s</text>' % (fnum(x), anchor, theme.get("label", theme["muted"]), escape(dates[-1])))
        note = "ONE DOT = ONE RECORD · HOLLOW = WEEKEND" if chart_type == "折线图" and time_x else (
            "ONE HAIRLINE = ONE RECORD · FLOOR TO PEAK" if chart_type == "面积图" else
            "ONE DOT = ONE RECORD · FLOOR-TO-PEAK BARCODE"
        )
    elif not data.empty and chart_type == "散点图":
        points = [point for dataset in datasets for point in dataset["points"]]
        xs = [point["x"] for point in points]; ys = [point["y"] for point in points]
        xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
        if xmax <= xmin: xmax = xmin + 1
        if ymax <= ymin: ymax = ymin + 1
        x0, x1, base = 48, 368, 258
        map_x = lambda value: x0 + (value-xmin)/(xmax-xmin)*(x1-x0)
        map_y = lambda value: base - (value-ymin)/(ymax-ymin)*202
        for tick in range(21):
            xx = x0 + tick/20*(x1-x0)
            height = 7 if tick % 5 == 0 else 4
            svg_parts.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width=".6" class="fade"/>' % (fnum(xx), base, fnum(xx), base-height, theme.get("track", theme["grid"])))
        svg_parts.append('<line x1="42" y1="258" x2="374" y2="258" stroke="%s" stroke-width=".8" class="fade"/>' % theme["grid"])
        x_start = escape(str(min(labels, key=lambda value: data.loc[data["_label"] == value, "_plot_x"].min()))[:12].upper()) if labels and not numeric_x else format(xmin, ".4g")
        x_end = escape(str(max(labels, key=lambda value: data.loc[data["_label"] == value, "_plot_x"].max()))[:12].upper()) if labels and not numeric_x else format(xmax, ".4g")
        svg_parts.append('<text x="%s" y="274" fill="%s" font-size="7" font-weight="600" letter-spacing=".08em" class="fade">%s</text>' % (x0, theme["faint"], x_start))
        svg_parts.append('<text x="%s" y="274" text-anchor="end" fill="%s" font-size="7" font-weight="600" letter-spacing=".08em" class="fade">%s</text>' % (x1, theme["faint"], x_end))
        svg_parts.append('<text x="26" y="%s" transform="rotate(-90 26 %s)" text-anchor="end" fill="%s" font-size="7" font-weight="600" letter-spacing=".08em" class="fade">%s ↑</text>' % (fnum(map_y(ymax)), fnum(map_y(ymax)), theme["faint"], escape(y_column.upper()[:20])))
        standout = set(id(p) for p in (min(points, key=lambda point: point["y"]), max(points, key=lambda point: point["y"])))
        for dataset in datasets:
            shade = group_colors[dataset["label"]]
            for point in dataset["points"]:
                xx, yy = map_x(point["x"]), map_y(point["y"])
                hero = id(point) in standout
                svg_parts.append(mark("line", {"x1": fnum(xx), "y1": base, "x2": fnum(xx), "y2": fnum(yy), "stroke": theme["secondary"], "stroke-width": ".55", "opacity": ".6", "data-series": dataset["label"]}, point["tip"], "fade"))
                svg_parts.append(mark("circle", {"cx": fnum(xx), "cy": fnum(yy), "r": "4.6" if hero else "2.6", "fill": theme["accent"] if hero else shade, "data-series": dataset["label"]}, point["tip"], "pop"))
                if hero:
                    name = point["tip"].split(" · ", 1)[-1].split("=", 1)[-1].split(" · ", 1)[0]
                    svg_parts.append('<text x="%s" y="%s" text-anchor="middle" fill="%s" font-size="8.5" font-weight="800" style="paint-order:stroke;stroke:%s;stroke-width:3px" class="fade">%s · %s</text>' % (fnum(xx), fnum(yy-10), theme["ink"], theme["background"], escape(name[:12]), format(point["y"], ".4g")))
        svg_parts.append('<text x="200" y="306" text-anchor="middle" fill="%s" font-size="7" font-weight="600" letter-spacing=".12em" class="fade">EVERY DOT HANGS A PLUMB LINE · X READS AT THE FLOOR</text>' % theme["faint"])
    elif not data.empty and chart_type == "饼图":
        values = datasets[0]["values"]
        total = sum(max(0, value) for value in values)
        if total > 0:
            cx, cy, r0 = W/2, 148, 64
            k0 = 0
            # F4 Tick Donut: one small radial mark per percentage point.
            for si, (label, value) in enumerate(zip(labels, values)):
                pct = 100 * max(0, value) / total
                count = int(pct)
                datasets[0].setdefault("pct", []).append(pct)
                for k in range(count):
                    idx = k0 + k
                    angle = (idx + .5) * 3.6 - 90
                    import math
                    a = math.radians(angle)
                    r1 = r0; r2 = r0 + 10 + ((k * 17 + si * 13) % 7)
                    tip_text = "%s · %s：%.2f%%（%s=%s）" % (label, y_column, pct, y_column, format(float(value), ".6g"))
                    svg_parts.append(mark("line", {"x1": fnum(cx+r1*math.cos(a)), "y1": fnum(cy+r1*math.sin(a)), "x2": fnum(cx+r2*math.cos(a)), "y2": fnum(cy+r2*math.sin(a)), "stroke": colors[si % len(colors)], "stroke-width": "1.8", "data-series": label, "style": "animation-delay:%ss" % fnum(idx*.012)}, tip_text, "fade"))
                mid = (k0 + count / 2) * 3.6 - 90
                a_mid = math.radians(mid)
                gx, gy = cx + (r0 + 20) * math.cos(a_mid), cy + (r0 + 20) * math.sin(a_mid)
                lx, ly = cx + (r0 + 38) * math.cos(a_mid), cy + (r0 + 38) * math.sin(a_mid)
                svg_parts.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width=".7" stroke-dasharray="1 3" class="fade"/>' % (fnum(gx), fnum(gy), fnum(lx), fnum(ly), theme["faint"]))
                anchor = "start" if math.cos(a_mid) > .3 else "end" if math.cos(a_mid) < -.3 else "middle"
                svg_parts.append('<text x="%s" y="%s" text-anchor="%s" fill="%s" font-size="8" font-weight="800" letter-spacing=".06em" class="fade">%s · %.0f</text>' % (fnum(lx), fnum(ly+3), anchor, colors[si % len(colors)], escape(label[:16]), pct))
                k0 += count
            svg_parts.append('<circle cx="%s" cy="%s" r="48" fill="%s"/>' % (cx, cy, theme["background"]))
            svg_parts.append('<text x="%s" y="%s" text-anchor="middle" fill="%s" font-size="22" font-weight="800" class="fade">100</text>' % (cx, cy-2, theme["ink"]))
            svg_parts.append('<text x="%s" y="%s" text-anchor="middle" fill="%s" font-size="7" letter-spacing=".1em" class="fade">TICKS · ONE = 1%%</text>' % (cx, cy+14, theme["muted"]))
            for i, (label, pct) in enumerate(zip(labels, datasets[0].get("pct", []))):
                x = left + (i % 2) * 190; y = H-30 - (i // 2) * 16
                tip_text = "%s：%.2f%%" % (label, pct)
                svg_parts.append(mark("circle", {"cx": fnum(x), "cy": fnum(y-3), "r": "2.5", "fill": colors[i % len(colors)], "data-series": label}, tip_text, "fade"))
                svg_parts.append('<text x="%s" y="%s" fill="%s" font-size="8" font-weight="800" letter-spacing=".06em" data-series="%s">%s · %.1f</text>' % (fnum(x+8), fnum(y), colors[i % len(colors)], escape(label, quote=True), escape(label[:16]), pct))
    elif not data.empty and chart_type == "热力图":
        # C6 · dot heat — the gallery's 7×12 punch-card grid. The dot area,
        # rather than opacity or a filled square, carries the measure.
        row_n, col_n = max(1, len(row_labels)), max(1, len(labels))
        cell_w = min(27, 312 / max(1, col_n - 1))
        cell_h = min(30, 178 / max(1, row_n - 1))
        heat_x0, heat_y0 = 64, 58
        maximum = max([cell["v"] for cell in cells] + [1])
        for yi, row in enumerate(row_labels):
            svg_parts.append('<text x="50" y="%s" text-anchor="end" fill="%s" font-size="7.5" font-weight="700" letter-spacing=".08em" class="fade">%s</text>' % (fnum(heat_y0+yi*cell_h+3), theme.get("label", theme["muted"]), escape(str(row)[:12].upper())))
        for xi, label in enumerate(labels):
            if xi % 2 == 0 or xi == col_n-1:
                svg_parts.append('<text x="%s" y="%s" text-anchor="middle" fill="%s" font-size="7" font-weight="600" class="fade">%s</text>' % (fnum(heat_x0+xi*cell_w), fnum(heat_y0+(row_n-1)*cell_h+26), theme["faint"], escape(str(label)[:8])))
        for cell in cells:
            cx = heat_x0 + cell["x"]*cell_w
            cy = heat_y0 + cell["y"]*cell_h
            radius = 1.2 + (max(0, cell["v"])/maximum*22)**.5 * 2.1
            tip_text = "%s · %s：%s" % (cell["row"], cell["label"], format(float(cell["v"]), ".6g"))
            if cell["v"] <= 0:
                svg_parts.append('<circle cx="%s" cy="%s" r=".8" fill="%s" class="pop"/>' % (fnum(cx), fnum(cy), theme["faint"]))
            else:
                ratio = float(cell["v"]) / maximum
                heat = theme.get("heat", [theme["ink"], theme["secondary"], theme["muted"]])
                shade = heat[0] if ratio > .66 else heat[1] if ratio > .33 else heat[2]
                svg_parts.append(mark("circle", {"cx": fnum(cx), "cy": fnum(cy), "r": fnum(radius), "fill": shade, "data-series": cell["row"]}, tip_text, "pop"))
        if cells:
            peak = max(cells, key=lambda cell: cell["v"])
            px = heat_x0 + peak["x"]*cell_w
            py = heat_y0 + peak["y"]*cell_h
            radius = 1.2 + (max(0, peak["v"])/maximum*22)**.5 * 2.1
            svg_parts.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="1" stroke-dasharray="2 3" class="fade"/>' % (fnum(px), fnum(py), fnum(radius+3.4), theme["accent"]))
        svg_parts.append('<text x="200" y="306" text-anchor="middle" fill="%s" font-size="7" font-weight="600" letter-spacing=".12em" class="fade">DOT AREA = %s · SILENCE STAYS VISIBLE</text>' % (theme["faint"], escape(y_column.upper()[:18])))
    else:
        note = "所选字段没有可显示的有效数据"

    svg_parts.append("</svg>")
    chart_svg = "".join(svg_parts)
    chart_type_js = {"折线图": "line", "面积图": "line", "柱状图": "bar", "饼图": "doughnut", "分类分布": "bar", "散点图": "scatter", "热力图": "heatmap"}.get(chart_type, "bar")
    legend = ""
    if len(datasets) > 1:
        note = "系列：" + " · ".join(map(str, group_colors)) + " · " + note
    escaped_svg_json = json.dumps(chart_svg, ensure_ascii=False).replace("</", "<\\/")
    config_json = json.dumps({"chartType": chart_type_js}, ensure_ascii=False)
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}body{margin:0;background:%%BG%%;color:%%INK%%;font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased}
.card{padding:28px 28px 20px;border-radius:24px;background:%%BG%%;overflow:hidden}header{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}
h2{font-size:16.5px;line-height:1.25;margin:0 0 3px;letter-spacing:-.02em;font-weight:700}.sub{font-size:11.5px;font-weight:400;color:%%MUTED%%;margin-bottom:14px}.legend{display:flex;flex-wrap:wrap;gap:5px 13px;margin:2px 0 4px}
.chart{height:320px;position:relative;cursor:pointer}.plot-svg{display:block;width:100%;height:auto;max-height:330px;margin:0 auto;overflow:visible}svg text{font-family:'Inter',sans-serif}.src{font-size:9.5px;font-weight:500;color:%%FAINT%%;letter-spacing:.08em;margin-top:10px;text-transform:uppercase}
.fade{animation:fade .9s ease both}.pop{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.2,.7,.3,1.3) both}.draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1s cubic-bezier(.4,0,.2,1) both}
@keyframes fade{from{opacity:0}}@keyframes pop{from{transform:scale(0)}to{transform:none}}@keyframes draw{to{stroke-dashoffset:0}}
.plot-svg [data-tip]{cursor:pointer;outline:none}.plot-svg [data-tip]:focus-visible{outline:2px solid %%INK%%;outline-offset:2px}
@media(prefers-reduced-motion:reduce){.pop,.fade{animation:none}.draw{animation:none;stroke-dasharray:none;stroke-dashoffset:0}}
</style></head><body><script type="application/json" id="chart-config">%%CONFIG%%</script><section class="card" id="card"><header><div><h2>%%TITLE%% · %%TYPE%%</h2><div class="sub">%%MODE%% · %%NOTE%%</div></div></header>
%%LEGEND%%<div class="chart" id="chart"></div><div class="src">来源：%%SOURCE%% · LIEFLAT BASICS</div></section>
<script>
const cfg=%%CONFIG%%;
var chart=document.getElementById('chart'), markup=%%SVGJSON%%;
function replay(){chart.innerHTML=markup}
chart.addEventListener('click',replay);
if('IntersectionObserver' in window){var observer=new IntersectionObserver(function(entries){if(entries[0].isIntersecting){replay();observer.disconnect()}},{threshold:.3});observer.observe(document.getElementById('card'))}else{replay()}
</script></body></html>""".replace("%%BG%%", theme["background"]).replace("%%INK%%", theme["ink"]).replace("%%MUTED%%", theme["muted"]).replace("%%GRID%%", theme["grid"]).replace("%%FAINT%%", theme["faint"]).replace("%%PRIMARY%%", theme["primary"]).replace("%%TITLE%%", escape(y_column)).replace("%%TYPE%%", escape(chart_type)).replace("%%MODE%%", escape(mode)).replace("%%NOTE%%", escape(note)).replace("%%LEGEND%%", legend).replace("%%SVG%%", chart_svg).replace("%%SOURCE%%", escape(source)).replace("%%SVGJSON%%", escaped_svg_json).replace("%%CONFIG%%", config_json)
