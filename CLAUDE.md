# 量化投研系统

## 技术栈
- 后端: Python FastAPI + SQLite
- 前端: Vue 3 + Vite + ECharts + TailwindCSS
- 数据源: 新浪财经(akshare, 稳定) + yfinance(港股美股) + baostock(股票列表)
- 技术指标: 自研 Python 引擎(30+指标，对标 TradingView)

## 启动
双击桌面快捷方式「量化投研系统」，或:
- 后端: `python -m api`
- 前端: `npx vite`
- 浏览器: http://localhost:5173

## 页面
1. 行情总览 - 指数卡片、涨跌统计、北向资金、VIX
2. 估值分析 - PE/PB排名、估值分布
3. 技术指标 - K线图(主图+成交量+MACD+RSI副图)、信号检测
4. 市场情绪 - 评分、北向趋势图、涨跌比图、VIX图
5. 基本面筛选 - PE/PB/ROE/增长率多条件组合筛选
6. 自选股 - 添加/删除/管理自选股，估值概览

## 数据
- 527只A股 + 20只港股 + 37只美股 日线
- 30+技术指标: Squeeze Momentum, WaveTrend, MACD, RSI, KDJ, 布林带, 一目均衡等
- 信号检测: 金叉/死叉/背离/Squeeze释放/WaveTrend交叉
- **历史K线回补**: `collector.collect_a_historical_kline()` — baostock 逐只拉取 250 天历史
- **历史估值回补**: `collector.collect_a_historical_valuation()` — baostock PE/PB 序列
- **深度财务**: `collector._collect_a_financials_quarters()` — 多报告期财务数据
- 一键采集: `collector.collect_all()` 或 API `POST /api/system/collect`
- 定时调度器: 每日收盘后自动采集

## 部署
- Docker: `docker compose up -d` — 前端 nginx + 后端 uvicorn
- 手动: `python -m api` (后端) + `npx vite --host 0.0.0.0 --port 5173` (前端)

## 测试
- 后端: `cd backend && pytest tests/ -v`
- 覆盖: 技术指标计算、估值分析、API 端点冒烟、信号检测边界

## 已知问题
- 东方财富API可能被WAF阻断，估值数据有时不完整
- 北向资金和VIX数据依赖网络，可能不实时
- Python 3.14 部分库不兼容，建议用 3.12
