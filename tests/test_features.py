import io

import pandas as pd
import pytest

from core.charts import build_chart, export_chart_png, lieflat_chart_html, recommend_chart_type
from core.data_loader import load_dataframe
from core.forecast import FORECAST_MODELS
from core.ai import generate_insights
from core.profiler import profile_dataframe


def _frame():
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=12),
            "sales": range(12),
            "category": list("ABABABABABAB"),
        }
    )


def test_recommend_time_numeric_returns_line():
    df = _frame()
    assert recommend_chart_type(df, "date", "sales") == "折线图"


def test_recommend_category_numeric_returns_bar():
    df = _frame()
    assert recommend_chart_type(df, "category", "sales") == "柱状图"


@pytest.mark.parametrize(
    ("chart_type", "expected_js_type", "group_column"),
    [
        ("折线图", "line", "sales"),
        ("柱状图", "bar", "sales"),
        ("散点图", "scatter", "category"),
        ("面积图", "line", "category"),
        ("饼图", "doughnut", "category"),
        ("热力图", "heatmap", "category"),
        ("分类分布", "bar", "category"),
    ],
)
def test_all_chart_types_render_when_selected_fields_overlap(chart_type, expected_js_type, group_column):
    df = _frame()
    html = lieflat_chart_html(df, chart_type, "category", "sales", group_column)
    figure = build_chart(df, chart_type, "category", "sales", group_column)

    assert f'"chartType": "{expected_js_type}"' in html
    assert "const cfg=" in html
    assert len(figure.data) > 0


def test_chart_renderers_handle_duplicate_input_headers():
    df = pd.DataFrame([[1, 10], [2, 20], [3, 30]], columns=["value", "value"])

    html = lieflat_chart_html(df, "折线图", "value", "value", "value")
    figure = build_chart(df, "折线图", "value", "value", "value")

    assert '"chartType": "line"' in html
    assert len(figure.data) > 0


def test_csv_loader_renames_duplicate_headers():
    upload = io.BytesIO(b"value,value,category\n1,10,A\n2,20,B\n")
    upload.name = "duplicate.csv"

    frame = load_dataframe(upload)

    assert frame.columns.tolist() == ["value", "value.1", "category"]


def test_chart_png_export_has_min_size():
    df = _frame()
    fig = build_chart(df, "折线图", "date", "sales")
    path = export_chart_png(fig, "/tmp/di_chart.png")
    from PIL import Image
    img = Image.open(path)
    assert img.size[0] >= 1200


def test_forecast_models_return_three_traces():
    df = _frame()
    for name, fn in FORECAST_MODELS.items():
        fig = fn(df, "date", "sales", 5)
        assert len(fig.data) == 3, name


def test_ai_fallback_without_key():
    df = _frame()
    profile = profile_dataframe(df)
    insights, used_ai = generate_insights(df, profile, api_key="")
    assert used_ai is False
    assert len(insights) >= 2
    assert all(isinstance(i, str) and i for i in insights)
