"""DataFrame profiling models and pure profiling logic."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DataProfile:
    rows: int
    columns: int
    missing_cells: int
    duplicate_rows: int
    column_summary: pd.DataFrame
    missing_summary: pd.DataFrame
    numeric_columns: list[str]


def profile_dataframe(df: pd.DataFrame) -> DataProfile:
    """Build the summary data used by the app and tests."""
    missing_count = df.isna().sum()
    summary = pd.DataFrame(
        {
            "字段": df.columns,
            "类型": [str(dtype) for dtype in df.dtypes],
            "非空值": [int(df[column].notna().sum()) for column in df.columns],
            "缺失值": [int(missing_count[column]) for column in df.columns],
            "唯一值": [int(df[column].nunique(dropna=True)) for column in df.columns],
        }
    )
    missing_summary = summary.loc[summary["缺失值"] > 0].copy()
    missing_summary["缺失率"] = (
        missing_summary["缺失值"] / max(len(df), 1)
    ).map(lambda value: f"{value:.1%}")
    return DataProfile(
        rows=len(df),
        columns=len(df.columns),
        missing_cells=int(missing_count.sum()),
        duplicate_rows=int(df.duplicated().sum()),
        column_summary=summary,
        missing_summary=missing_summary,
        numeric_columns=df.select_dtypes(include="number").columns.tolist(),
    )
