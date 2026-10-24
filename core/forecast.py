"""Transparent baseline forecasting helpers: linear, Holt exponential smoothing, seasonal naive."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from core.charts import STYLE_PRESETS, apply_theme


def _prepare(df: pd.DataFrame, date_column: str, value_column: str) -> pd.DataFrame:
    data = df[[date_column, value_column]].copy()
    data[date_column] = pd.to_datetime(data[date_column], errors="coerce")
    data[value_column] = pd.to_numeric(data[value_column], errors="coerce")
    data = data.dropna().sort_values(date_column).groupby(date_column, as_index=False)[value_column].sum()
    if len(data) < 2:
        raise ValueError("趋势预测至少需要两个有效时间点。")
    return data


def _confidence_band(future_dates, predicted, residual_std: float, z: float = 1.96):
    margin = z * residual_std * np.sqrt(np.arange(1, len(predicted) + 1))
    return predicted + margin, predicted - margin


def linear_forecast(df, date_column, value_column, periods, preset="Porcelain", mode="Basics") -> go.Figure:
    data = _prepare(df, date_column, value_column)
    x = (data[date_column] - data[date_column].min()).dt.days.astype(float).values
    coef = np.polyfit(x, data[value_column].values, 1)
    fitted = coef[0] * x + coef[1]
    residual_std = float(np.std(data[value_column].values - fitted))
    future_dates = pd.date_range(data[date_column].max(), periods=periods + 1, freq="D")[1:]
    future_x = (future_dates - data[date_column].min()).days.astype(float).values
    predicted = coef[0] * future_x + coef[1]
    upper, lower = _confidence_band(future_dates, predicted, residual_std)
    return _forecast_figure(data, future_dates, predicted, upper, lower, value_column, "线性回归", preset, mode)


def exponential_forecast(df, date_column, value_column, periods, preset="Porcelain", mode="Basics") -> go.Figure:
    from statsmodels.tsa.holtwinters import Holt

    data = _prepare(df, date_column, value_column)
    series = data.set_index(date_column)[value_column].asfreq("D").interpolate()
    if len(series) < 3:
        raise ValueError("指数平滑至少需要 3 个有效时间点。")
    model = Holt(series, initialization_method="estimated").fit()
    future_dates = pd.date_range(series.index.max(), periods=periods + 1, freq="D")[1:]
    forecast_result = model.forecast(periods)
    predicted = forecast_result.values
    # Approximate confidence from in-sample residuals
    fitted = model.fittedvalues
    residual_std = float(np.std(series.values - fitted.values))
    upper, lower = _confidence_band(future_dates, predicted, residual_std)
    return _forecast_figure(data, future_dates, predicted, upper, lower, value_column, "指数平滑 (Holt)", preset, mode)


def seasonal_naive_forecast(df, date_column, value_column, periods, season_length=7, preset="Porcelain", mode="Basics") -> go.Figure:
    data = _prepare(df, date_column, value_column)
    values = data[value_column].values
    if len(values) < season_length + 1:
        season_length = max(1, len(values) - 1)
    future_dates = pd.date_range(data[date_column].max(), periods=periods + 1, freq="D")[1:]
    predicted = np.array([values[-(season_length - i % season_length)] for i in range(periods)])
    # Residual std from lag-season errors
    errors = values[season_length:] - values[:-season_length]
    residual_std = float(np.std(errors)) if len(errors) > 0 else float(np.std(values))
    upper, lower = _confidence_band(future_dates, predicted, residual_std)
    return _forecast_figure(data, future_dates, predicted, upper, lower, value_column, f"季节性朴素 (周期={season_length})", preset, mode)


def _forecast_figure(data, future_dates, predicted, upper, lower, value_column, method, preset, mode) -> go.Figure:
    theme = STYLE_PRESETS.get(preset, STYLE_PRESETS["Porcelain"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.iloc[:, 0], y=data[value_column], name="历史", mode="lines+markers",
        line={"color": theme["primary"], "width": 2},
    ))
    fig.add_trace(go.Scatter(
        x=future_dates, y=predicted, name=method, mode="lines+markers",
        line={"color": theme["accent"], "width": 2.4, "dash": "dash"},
    ))
    fig.add_trace(go.Scatter(
        x=list(future_dates) + list(reversed(future_dates)),
        y=list(upper) + list(reversed(lower)),
        fill="toself", fillcolor=theme["accent"] + "33", line={"width": 0},
        name="95% 置信区间", showlegend=True,
    ))
    return apply_theme(fig, f"{value_column} · {method} 趋势预测", subtitle=f"预测未来 {len(future_dates)} 天", source="DataInsight", preset=preset, mode=mode)


FORECAST_MODELS = {
    "线性回归": linear_forecast,
    "指数平滑": exponential_forecast,
    "季节性朴素": seasonal_naive_forecast,
}
