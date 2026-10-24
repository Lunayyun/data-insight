# DataInsight

一个面向汇报场景的 **AI + 数据可视化** 平台。上传数据后一站式完成清洗、可视化分析、趋势预测、AI 洞察，并一键导出可直接放入 PPT 的图表与 16:9 汇报文件。

视觉系统参考 [lieflat-charts](https://github.com/larashero3-dotcom/lieflat-charts)：四套配色（Mono / Porcelain 青瓷蓝 / Palm 椰林绿 / Wire 编辑部红）+ 三种叙事模式（Basics / Glance / Lupi），发丝线网格、旁注、来源行、可数刻度。

## 运行

```bash
uv venv
uv pip install -r requirements.txt
streamlit run app.py
```

## 功能

### 数据上传与清洗
- 支持 CSV / XLSX / XLS
- 缺失值策略：保留原样 / 中位数填充 / 均值填充 / 删除
- 重复行一键去除
- 清洗前后行数对比、字段概况、缺失率

### 可视化图表
- 折线图、柱状图、散点图、面积图、饼图、热力图、分类分布
- 基于字段类型**自动推荐图表**
- lieflat 主题：标题 + 旁注 + 来源行 + 发丝线网格
- 一键导出 **PNG（150 DPI，适合 PPT）** 与 HTML

### 趋势预测
- 线性回归
- 指数平滑（Holt）
- 季节性朴素
- 历史折线 + 预测虚线 + 95% 置信区间带

### AI 洞察
- 调用阿里云百炼 **qwen-plus**（OpenAI 兼容接口）生成 3-5 条关键发现
- 未配置 API Key 时自动降级为规则摘要
- 支持在侧边栏输入 Key 或设置环境变量 `DASHSCOPE_API_KEY`

### 报告导出
- **Markdown 报告**：数据摘要、字段概况、缺失明细、数据样例
- **PPTX 汇报（16:9）**：封面页 + 数据摘要页（指标卡 + AI 发现）+ 图表页 + 表格页，每页含标题、来源行
- **美化表格 PNG**：primary 色表头、斑马纹、发丝线分隔，可直接插入 PPT

## 配置

```bash
export DASHSCOPE_API_KEY="your-key"
# 也可在应用侧边栏直接输入
```

## 目录结构

```
app.py                # Streamlit 主应用
core/
  charts.py           # lieflat 主题图表、推荐、PNG 导出
  forecast.py         # 三种趋势预测模型
  ai.py               # AI 洞察 + 规则降级
  table.py            # lieflat 风格表格 PNG
  report.py           # Markdown + PPTX 报告生成
  cleaning.py         # 数据清洗
  data_loader.py      # 文件加载
  profiler.py         # 数据画像
data/                 # 示例数据
tests/                # 单元测试
```
