"""DataInsight: a polished, presentation-ready data visualization studio."""

import io
import os
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from core.ai import generate_insights
from core.charts import STYLE_PRESETS, build_chart, chart_to_pil, export_chart_png, lieflat_chart_html, recommend_chart_type
from core.cleaning import clean_dataframe
from core.data_loader import load_dataframe
from core.forecast import FORECAST_MODELS
from core.profiler import profile_dataframe
from core.report import SlideChart, SlideTable, build_markdown_report, build_pptx_report
from core.table import style_dataframe, table_to_png_bytes


st.set_page_config(page_title="DataInsight Studio", page_icon="DI", layout="wide", initial_sidebar_state="expanded")
SAMPLE_FILE = __import__('pathlib').Path(__file__).parent / "data" / "sample_sales.csv"


with st.sidebar:
    st.markdown("### 工作区")
    uploaded_file = st.file_uploader(
        "上传 CSV / Excel",
        type=["csv", "xlsx", "xls"],
        help="支持 .csv、.xlsx 和 .xls 文件",
    )
    st.caption("文件只在当前本地会话中处理。")
    st.divider()
    st.markdown("### 视觉系统")
    visual_style = st.selectbox("色彩预设", list(STYLE_PRESETS), index=1, key="visual_style")
    chart_mode = st.selectbox("叙事模式", ["Basics", "Glance", "Lupi"], index=0)
    mode_help = {
        "Basics": "结构清楚的基础分析",
        "Glance": "适合周报和快速判断",
        "Lupi": "适合逐条阅读和编辑叙事",
    }
    st.caption(mode_help[chart_mode])


if uploaded_file is None and not st.session_state.get("use_sample_data", False):
    st.markdown(
        """
        <style>
        html, body, [class*="css"] { font-family:'Inter', sans-serif; }
        h1, h2, h3 { font-family:'Space Grotesk', sans-serif; letter-spacing:-.025em; }
        .block-container { padding-top:1.8rem; max-width:1440px; }
        .hero { position:relative; isolation:isolate; overflow:hidden; padding:2rem 2.15rem; border:1px solid #DEDDD6; background:linear-gradient(135deg,#F7F2EB 0%,#FFFDF9 100%); border-radius:26px; margin-bottom:1.35rem; animation:hero-enter .7s cubic-bezier(.2,.7,.3,1) both; }
        .hero:after { content:""; position:absolute; z-index:-1; width:230px; height:230px; right:7%; top:-135px; border:1px solid #DEDDD6; border-radius:50%; box-shadow:0 0 0 28px #F7F2EB,0 0 0 29px #DEDDD6,0 0 0 58px #F7F2EB,0 0 0 59px #DEDDD6; opacity:.65; animation:orbit-in 1.2s ease-out both; }
        .hero-kicker { color:#081F5C; text-transform:uppercase; letter-spacing:.13em; font-size:.72rem; font-weight:700; display:flex; align-items:center; gap:.45rem; }
        .hero h1 { font-size:clamp(2.1rem,4vw,3rem); margin:.35rem 0 .4rem; font-weight:700; }
        .hero p { color:#7096D1; margin:0; font-size:.98rem; max-width:680px; }
        @keyframes hero-enter { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
        @keyframes orbit-in { from { opacity:0; transform:scale(.78) rotate(-16deg); } to { opacity:.65; transform:scale(1) rotate(0); } }
        @media (prefers-reduced-motion: reduce) { *,*::before,*::after { animation-duration:.01ms !important; animation-iteration-count:1 !important; transition-duration:.01ms !important; } }
        </style>
        <div class="hero"><div class="hero-kicker">✦ AI DATA PRODUCT STUDIO</div>
        <h1>DataInsight</h1><p>把原始数据整理成清楚、可信、可直接汇报的发现。</p></div>
        """,
        unsafe_allow_html=True,
    )
    st.info("从左侧上传数据后，开始构建你的分析页面。", icon=":material/upload_file:")
    if st.button("先看示例数据", icon=":material/visibility:", type="secondary"):
        st.session_state["use_sample_data"] = True
        st.rerun()
    st.subheader("一个工作区，完成整套数据分析", icon=":material/route:")
    st.markdown(
        ":blue-badge[:material/table_chart: 数据整理]  "
        ":violet-badge[:material/monitoring: 图表分析]  "
        ":green-badge[:material/query_stats: 趋势预测]  "
        ":orange-badge[:material/auto_awesome: AI 洞察]  "
        ":gray-badge[:material/slideshow: 汇报导出]"
    )
    st.caption("上传后可以继续调整清洗策略、图表类型、配色和叙事模式。")
    st.stop()


if uploaded_file is not None:
    st.session_state["use_sample_data"] = False
    source_name = uploaded_file.name
    file_source = uploaded_file
else:
    source_name = SAMPLE_FILE.name
    file_source = SAMPLE_FILE.open("rb")

try:
    raw_df = load_dataframe(file_source)
finally:
    if uploaded_file is None:
        file_source.close()

with st.sidebar:
    st.divider()
    st.markdown("### :material/cleaning_services: 清洗设置")
    missing_strategy = st.selectbox(
        "缺失值处理",
        ["保留原样", "数值列填充中位数", "数值列填充均值", "删除含缺失值的行"],
        key="missing_strategy",
    )
    remove_duplicates = st.checkbox("删除重复行", value=True, key="remove_duplicates")
    st.divider()
    st.markdown("### :material/auto_awesome: AI 配置")
    ai_key = st.text_input(
        "百炼 / OpenAI API Key",
        type="password",
        value=os.getenv("DASHSCOPE_API_KEY", ""),
        help="只在点击生成洞察时使用，不会写入文件。",
    )
    st.caption("留空则使用规则摘要 · qwen-plus 兼容模式")


cleaned_df = clean_dataframe(raw_df, missing_strategy, remove_duplicates)
profile = profile_dataframe(cleaned_df)
all_columns = cleaned_df.columns.tolist()
numeric_columns = profile.numeric_columns
sparkline = cleaned_df[numeric_columns[0]].dropna().head(24).tolist() if numeric_columns else None

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{ font-family:'Inter', sans-serif; }}
    h1, h2, h3 {{ font-family:'Space Grotesk', sans-serif; color:{STYLE_PRESETS[visual_style]['ink']}; letter-spacing:-.025em; }}
    .block-container {{ padding-top:1.8rem; max-width:1440px; }}
    .hero {{ position:relative; isolation:isolate; overflow:hidden; padding:1.8rem 2rem; border:1px solid {STYLE_PRESETS[visual_style]['grid']}; background:linear-gradient(135deg,{STYLE_PRESETS[visual_style]['background']} 0%,#FFFDF9 100%); border-radius:26px; margin-bottom:1.35rem; animation:hero-enter .7s cubic-bezier(.2,.7,.3,1) both; }}
    .hero:after {{ content:""; position:absolute; z-index:-1; width:230px; height:230px; right:7%; top:-135px; border:1px solid {STYLE_PRESETS[visual_style]['grid']}; border-radius:50%; box-shadow:0 0 0 28px {STYLE_PRESETS[visual_style]['background']},0 0 0 29px {STYLE_PRESETS[visual_style]['grid']},0 0 0 58px {STYLE_PRESETS[visual_style]['background']},0 0 0 59px {STYLE_PRESETS[visual_style]['grid']}; opacity:.65; animation:orbit-in 1.2s ease-out both; }}
    .hero-kicker {{ color:{STYLE_PRESETS[visual_style]['accent']}; text-transform:uppercase; letter-spacing:.13em; font-size:.72rem; font-weight:700; display:flex; align-items:center; gap:.45rem; }}
    .hero h1 {{ font-size:clamp(2.1rem,4vw,3rem); margin:.35rem 0 .4rem; font-weight:700; }}
    .hero p {{ color:{STYLE_PRESETS[visual_style]['muted']}; margin:0; font-size:.98rem; max-width:680px; }}
    [data-testid="stMetric"] {{ border:1px solid {STYLE_PRESETS[visual_style]['grid']}; padding:1rem 1.05rem; border-radius:18px; background:#FFFDF9; transition:transform .22s ease,border-color .22s ease; animation:hero-enter .55s cubic-bezier(.2,.7,.3,1) both; }}
    [data-testid="stMetric"]:hover {{ transform:translateY(-3px); border-color:{STYLE_PRESETS[visual_style]['secondary']}; }}
    [data-testid="stMetricLabel"] {{ color:{STYLE_PRESETS[visual_style]['muted']}; }}
    [data-testid="stMetricValue"] {{ color:{STYLE_PRESETS[visual_style]['ink']}; font-weight:800; }}
    div[data-baseweb="tab-list"] {{ gap:.5rem; padding:.3rem; background:{STYLE_PRESETS[visual_style]['zebra']}; border-radius:15px; }}
    button[data-baseweb="tab"] {{ font-weight:600; border-radius:11px; transition:color .18s ease,background .18s ease; }}
    button[data-baseweb="tab"]:hover {{ color:{STYLE_PRESETS[visual_style]['primary']}; }}
    [data-testid="stDownloadButton"] button, [data-testid="stButton"] button {{ transition:transform .18s ease,box-shadow .18s ease; }}
    [data-testid="stDownloadButton"] button:hover, [data-testid="stButton"] button:hover {{ transform:translateY(-1px); }}
    .insight-card {{ padding:1rem 1.2rem; border-left:3px solid {STYLE_PRESETS[visual_style]['primary']}; background:{STYLE_PRESETS[visual_style]['zebra']}; border-radius:8px; margin:.5rem 0; animation:hero-enter .45s ease both; }}
    @keyframes hero-enter {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @keyframes orbit-in {{ from {{ opacity:0; transform:scale(.78) rotate(-16deg); }} to {{ opacity:.65; transform:scale(1) rotate(0); }} }}
    @media (prefers-reduced-motion: reduce) {{ *,*::before,*::after {{ animation-duration:.01ms !important; animation-iteration-count:1 !important; scroll-behavior:auto !important; transition-duration:.01ms !important; }} }}
    </style>
    <div class="hero"><div class="hero-kicker">✦ AI DATA PRODUCT STUDIO</div>
    <h1>DataInsight</h1><p>把 {escape(source_name)} 整理成清楚、可信、可直接汇报的发现。</p></div>
    """,
    unsafe_allow_html=True,
)

st.caption(f":material/description: 当前文件：{source_name} · 清洗后 {len(cleaned_df):,} 行")
metrics = st.columns(4)
metrics[0].metric("有效记录", f"{profile.rows:,}", icon=":material/format_list_numbered:", border=True, chart_data=sparkline, chart_type="line")
metrics[1].metric("字段", f"{profile.columns:,}", icon=":material/view_column:", border=True)
metrics[2].metric("缺失单元格", f"{profile.missing_cells:,}", delta="已处理" if missing_strategy != "保留原样" else None, icon=":material/scan_delete:", border=True)
metrics[3].metric("重复行", f"{profile.duplicate_rows:,}", delta="已删除" if remove_duplicates else None, icon=":material/content_copy:", border=True)

overview, explore, forecast_tab, ai_tab, report = st.tabs(
    [
        ":material/database: 数据概览",
        ":material/insert_chart: 图表分析",
        ":material/trending_up: 趋势预测",
        ":material/auto_awesome: AI 洞察",
        ":material/description: 分析报告",
    ],
    on_change="rerun",
    key="analysis_tabs",
)

if overview.open:
    with overview:
        left, right = st.columns([1.35, 1])
        with left:
            st.subheader("字段概况", icon=":material/view_column:")
            st.table(style_dataframe(profile.column_summary, visual_style), width="stretch", hide_index=True, border=False, alt="字段概况表")
            st.download_button(
                "导出表格 PNG",
                table_to_png_bytes(profile.column_summary, preset=visual_style, title="字段概况"),
                "datainsight_columns.png",
                "image/png",
                icon=":material/download:",
            )
        with right:
            st.subheader("数据质量", icon=":material/verified:")
            if profile.missing_summary.empty:
                st.success("没有发现缺失值。", icon=":material/check_circle:")
            else:
                st.table(style_dataframe(profile.missing_summary, visual_style), width="stretch", hide_index=True, border=False, alt="数据质量与缺失值表")
            st.subheader("数据预览", icon=":material/preview:")
            st.table(style_dataframe(cleaned_df.head(12), visual_style), width="stretch", hide_index=True, border=False, alt="清洗后数据预览表")
        st.download_button(
            "下载清洗后数据",
            cleaned_df.to_csv(index=False).encode("utf-8-sig"),
            "datainsight_cleaned.csv",
            "text/csv",
            icon=":material/download:",
        )

if explore.open:
    with explore:
        st.subheader("构建适合汇报的图表", icon=":material/insert_chart:")
        if not numeric_columns:
            st.warning("当前数据没有数值字段，暂时无法生成数值图表。", icon=":material/warning:")
        else:
            controls = st.columns([1, 1, 1, 1])
            chart_types = ["折线图", "柱状图", "散点图", "面积图", "饼图", "热力图", "分类分布"]
            x_default = next((index for index, column in enumerate(all_columns) if column not in numeric_columns), 0)
            suggested = recommend_chart_type(cleaned_df, all_columns[x_default], numeric_columns[0])
            st.caption(f":material/lightbulb: 根据字段类型，推荐图表：**{suggested}**")
            chart_type = controls[0].selectbox("图表类型", chart_types, index=chart_types.index(suggested) if suggested in chart_types else 0)
            x_column = controls[1].selectbox("横轴 / 分类", all_columns, index=x_default)
            y_column = controls[2].selectbox("指标字段", numeric_columns)
            group_options = ["不分组"] + [c for c in all_columns if c not in {x_column, y_column}]
            group_choice = controls[3].selectbox("分组字段", group_options)
            group_column = None if group_choice == "不分组" else group_choice
            components.html(
                lieflat_chart_html(cleaned_df, chart_type, x_column, y_column, group_column, visual_style, chart_mode, source_name),
                height=440,
                scrolling=False,
            )
            try:
                figure = build_chart(cleaned_df, chart_type, x_column, y_column, group_column, visual_style, chart_mode, source=source_name)
                st.download_button(
                    "下载图表 HTML",
                    figure.to_html(include_plotlyjs="cdn", full_html=True),
                    "datainsight_chart.html",
                    "text/html",
                    icon=":material/code:",
                )
                try:
                    png_buf = io.BytesIO()
                    figure.write_image(png_buf, format="png", width=1600, height=900, scale=2)
                    st.download_button("下载图表 PNG（适合 PPT）", png_buf.getvalue(), "datainsight_chart.png", "image/png", icon=":material/image:")
                except Exception:
                    st.caption("交互图表已可用；当前环境未配置 PNG 导出引擎。")
            except Exception as error:
                st.caption(f"Lieflat 交互图表已显示，备用 Plotly 导出不可用：{error}")
            st.caption(f":material/tune: {visual_style} · {chart_mode} · Lieflat 交互模板")

if forecast_tab.open:
    with forecast_tab:
        st.subheader("趋势预测", icon=":material/trending_up:")
        date_candidates = [c for c in all_columns if "date" in c.lower() or "日期" in c]
        date_column = st.selectbox("时间字段", date_candidates or all_columns)
        forecast_value = st.selectbox("预测指标", numeric_columns if numeric_columns else all_columns)
        model_name = st.selectbox("预测模型", list(FORECAST_MODELS))
        horizon = st.slider("预测未来天数", 3, 90, 14)
        if st.button("生成趋势预测", type="primary", icon=":material/auto_graph:"):
            with st.status("正在拟合趋势模型…", expanded=False) as status:
                try:
                    forecast_figure = FORECAST_MODELS[model_name](cleaned_df, date_column, forecast_value, horizon, visual_style, chart_mode)
                    st.plotly_chart(forecast_figure, width="stretch")
                    fbuf = io.BytesIO()
                    forecast_figure.write_image(fbuf, format="png", width=1600, height=900, scale=2)
                    st.download_button("下载预测图 PNG", fbuf.getvalue(), "datainsight_forecast.png", "image/png", icon=":material/download:")
                    status.update(label="趋势预测已完成", state="complete")
                except Exception as error:
                    status.update(label="趋势预测未完成", state="error")
                    st.error(str(error))

if ai_tab.open:
    with ai_tab:
        st.subheader("AI 数据洞察", icon=":material/auto_awesome:")
        st.caption("调用大模型分析数据结构、数值趋势与缺失情况，输出关键发现。")
        if st.button("生成 AI 洞察", type="primary", icon=":material/auto_awesome:"):
            with st.status("正在分析数据…", expanded=False) as status:
                insights, used_ai = generate_insights(cleaned_df, profile, api_key=ai_key or None)
                status.update(label="AI 洞察已生成" if used_ai else "规则摘要已生成", state="complete")
            if used_ai:
                st.success("已使用 AI 生成洞察。", icon=":material/check_circle:")
            else:
                st.info("未配置 API Key，当前使用规则摘要。", icon=":material/info:")
            for ins in insights:
                st.markdown(f'<div class="insight-card">{escape(ins)}</div>', unsafe_allow_html=True)
            st.session_state["ai_insights"] = insights

if report.open:
    with report:
        st.subheader("生成分析报告", icon=":material/description:")
        report_title = st.text_input("报告标题", f"{source_name} 数据分析报告")
        insights = st.session_state.get("ai_insights", [])
        st.markdown("**Markdown 报告**")
        markdown_report = build_markdown_report(cleaned_df, profile, report_title)
        st.download_button("下载 Markdown 报告", markdown_report, "datainsight_report.md", "text/markdown", icon=":material/markdown:")
        with st.expander("预览 Markdown", icon=":material/visibility:"):
            st.code(markdown_report[:1800], language="markdown")
        st.divider()
        st.markdown("**PPTX 汇报（16:9，含图表与表格）**")
        if st.button("生成并下载 PPTX 报告", type="primary", icon=":material/slideshow:"):
            with st.status("正在组装汇报文件…", expanded=False) as status:
                charts_payload = []
                if numeric_columns:
                    try:
                        fig = build_chart(cleaned_df, recommend_chart_type(cleaned_df, all_columns[0], numeric_columns[0]), all_columns[0], numeric_columns[0], None, visual_style, chart_mode, source=source_name)
                        cbuf = io.BytesIO()
                        fig.write_image(cbuf, format="png", width=1600, height=900, scale=2)
                        charts_payload.append(SlideChart(cbuf.getvalue(), f"{numeric_columns[0]} 趋势", f"数据来源：{source_name}"))
                    except Exception:
                        pass
                tables_payload = [SlideTable(profile.column_summary, "字段概况", table_to_png_bytes(profile.column_summary, preset=visual_style, title="字段概况"))]
                pptx_bytes = build_pptx_report(report_title, profile, charts_payload, tables_payload, insights=insights or None, preset=visual_style)
                st.download_button("下载 PPTX 报告", pptx_bytes, "datainsight_report.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", icon=":material/download:")
                status.update(label="PPTX 已生成", state="complete")
            st.success(f"PPTX 已生成，共包含封面、摘要、{len(charts_payload)} 张图表、{len(tables_payload)} 张表格。", icon=":material/check_circle:")
