import pandas as pd

from core.profiler import profile_dataframe
from core.cleaning import clean_dataframe


def test_profile_dataframe_reports_quality_metrics() -> None:
    frame = pd.DataFrame(
        {
            "amount": [10, 10, None],
            "category": ["A", "A", "B"],
        }
    )

    profile = profile_dataframe(frame)

    assert profile.rows == 3
    assert profile.columns == 2
    assert profile.missing_cells == 1
    assert profile.duplicate_rows == 1
    assert profile.numeric_columns == ["amount"]
    assert profile.missing_summary.iloc[0]["缺失率"] == "33.3%"


def test_clean_dataframe_fills_missing_values_and_drops_duplicates() -> None:
    frame = pd.DataFrame({"amount": [10, 10, None], "category": ["A", "A", None]})
    cleaned = clean_dataframe(frame, "数值列填充中位数", True)
    assert len(cleaned) == 2
    assert cleaned.isna().sum().sum() == 0
