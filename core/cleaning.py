"""Deterministic data cleaning operations used by the UI."""

import pandas as pd


def clean_dataframe(df: pd.DataFrame, missing_strategy: str, remove_duplicates: bool) -> pd.DataFrame:
    """Return a cleaned copy without mutating the uploaded frame."""
    cleaned = df.copy()
    numeric_columns = cleaned.select_dtypes(include="number").columns
    text_columns = cleaned.select_dtypes(exclude="number").columns
    if missing_strategy == "删除含缺失值的行":
        cleaned = cleaned.dropna()
    elif missing_strategy in {"数值列填充中位数", "数值列填充均值"}:
        for column in numeric_columns:
            value = cleaned[column].median() if missing_strategy.endswith("中位数") else cleaned[column].mean()
            cleaned[column] = cleaned[column].fillna(value)
        for column in text_columns:
            cleaned[column] = cleaned[column].fillna("未填写")
    if remove_duplicates:
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    return cleaned
