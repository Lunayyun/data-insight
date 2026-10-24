"""AI-powered data insights with rule-based fallback."""

from __future__ import annotations

import json
import os

import pandas as pd

from core.profiler import DataProfile


def _rule_based_insights(df: pd.DataFrame, profile: DataProfile) -> list[str]:
    """Generate deterministic insights without an LLM."""
    insights: list[str] = []
    insights.append(f"数据集共 {profile.rows:,} 行、{profile.columns} 个字段，其中数值字段 {len(profile.numeric_columns)} 个。")

    if profile.numeric_columns:
        for col in profile.numeric_columns[:3]:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if series.empty:
                continue
            insights.append(
                f"「{col}」均值 {series.mean():.2f}，最大值 {series.max():.2f}，最小值 {series.min():.2f}，"
                f"呈{'上升' if series.iloc[-1] > series.iloc[0] else '下降'}趋势。"
            )
    if not profile.missing_summary.empty:
        top = profile.missing_summary.sort_values("缺失值", ascending=False).iloc[0]
        insights.append(f"缺失最严重的字段是「{top['字段']}」，缺失率 {top['缺失率']}，建议重点处理。")
    if profile.duplicate_rows > 0:
        insights.append(f"检测到 {profile.duplicate_rows:,} 行重复数据，已按当前设置处理。")
    return insights


def _build_prompt(df: pd.DataFrame, profile: DataProfile) -> str:
    sample = df.head(10).to_string(index=False)
    numeric_stats = ""
    if profile.numeric_columns:
        desc = df[profile.numeric_columns].describe().round(2).to_string()
        numeric_stats = f"\n数值字段统计：\n{desc}"
    return (
        "你是一名资深数据分析师。请根据以下数据生成 3-5 条关键发现（insights），"
        "每条不超过 50 字，要具体、有数据支撑，不要空泛。\n\n"
        f"数据概览：{profile.rows:,} 行 × {profile.columns} 列，数值字段 {len(profile.numeric_columns)} 个，"
        f"缺失单元格 {profile.missing_cells:,}。\n"
        f"字段概况：\n{profile.column_summary.to_string(index=False)}\n"
        f"{numeric_stats}\n\n"
        f"数据样例：\n{sample}\n\n"
        "请以 JSON 数组返回，格式为 [\"发现1\", \"发现2\", ...]，只返回 JSON，不要其他文字。"
    )


def generate_insights(
    df: pd.DataFrame,
    profile: DataProfile,
    api_key: str | None = None,
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
    model: str = "qwen-plus",
) -> tuple[list[str], bool]:
    """Return (insights, used_ai). Falls back to rule-based when no key or on error."""
    key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        return _rule_based_insights(df, profile), False

    try:
        from openai import OpenAI

        client = OpenAI(api_key=key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": _build_prompt(df, profile)}],
            temperature=0.3,
            timeout=30,
        )
        content = response.choices[0].message.content.strip()
        # Tolerate markdown code fences
        if content.startswith("```"):
            content = content.strip("`")
            content = content.replace("json", "", 1).strip()
        parsed = json.loads(content)
        if isinstance(parsed, list) and len(parsed) >= 2:
            return [str(item) for item in parsed][:6], True
    except Exception:
        pass

    return _rule_based_insights(df, profile), False
