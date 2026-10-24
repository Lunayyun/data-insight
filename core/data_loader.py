"""File loading functions kept separate from the Streamlit UI."""

from typing import BinaryIO

import pandas as pd


def _ensure_unique_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make repeated spreadsheet headers selectable as distinct fields."""
    used: set[str] = set()
    columns: list[str] = []
    for original in df.columns:
        base = str(original)
        candidate = base
        suffix = 1
        while candidate in used:
            candidate = f"{base}.{suffix}"
            suffix += 1
        used.add(candidate)
        columns.append(candidate)
    result = df.copy()
    result.columns = columns
    return result


def load_dataframe(uploaded_file: BinaryIO) -> pd.DataFrame:
    """Load a supported uploaded file into a DataFrame."""
    file_name = getattr(uploaded_file, "name", "").lower()
    if file_name.endswith(".csv"):
        frame = pd.read_csv(uploaded_file)
    elif file_name.endswith((".xlsx", ".xls")):
        try:
            frame = pd.read_excel(uploaded_file)
        except ImportError as error:
            raise ValueError(
                "读取 Excel 需要安装 openpyxl：uv pip install openpyxl"
            ) from error
    else:
        raise ValueError("目前仅支持 CSV、XLSX 和 XLS 文件。")
    return _ensure_unique_columns(frame)
