# 量化投研系统 · Stock Dashboard

A 股 / 港股 / 美股行情分析与技术指标研究平台。前后端分离，Docker 一键部署。

> A market research dashboard covering Chinese, Hong Kong and US equities, with 31 self-implemented technical indicators and a 4-panel synchronized chart. FastAPI + Vue 3 + ECharts.

<!-- 截图建议：把首页 + 技术指标页两张截图放到 docs/screenshots/ 并在此引用 -->
<!-- ![行情总览](docs/screenshots/overview.png) -->
<!-- ![技术指标](docs/screenshots/technical.png) -->

---

## 功能

| 页面 | 内容 |
|---|---|
| **行情总览** | 指数卡片、涨跌统计、北向资金、VIX |
| **估值分析** | PE / PB 排名、估值分布直方图 |
| **技术指标** | 4 面板联动 K 线图（K 线 + 成交量 + MACD + RSI/KDJ），十字光标联动，33 种信号检测 |
| **市场情绪** | 4 因子情绪评分（0-100）、北向资金趋势、涨跌比、VIX |
| **基本面筛选** | PE / PB / ROE / 营收增长 / 净利润增长 / 股息率 / 市值 多条件组合 |
| **自选股** | 自选股管理 + 估值概览 |

---

## 技术亮点

### 31 个自研技术指标引擎

`backend/analytics/technical.py`（863 行）用 pandas / NumPy 手写实现，不依赖 TA-Lib：

`SMA / EMA / WMA / HMA / MACD / RSI / Bollinger Bands / KDJ / ATR / OBV / SAR / ADX / CCI / SuperTrend / Stochastic / Williams %R / ROC / Momentum / Keltner Channels / Donchian / Ichimoku / VWAP / MFI / CMF / Squeeze Momentum / WaveTrend / VFI / Impulse MACD / Elder Impulse / VMA / Heikin-Ashi`

单次 `calc_all()` 输出 60+ 列，对标 TradingView 社区的指标实现。

### 33 种信号检测

金叉 / 死叉、MACD 零轴上穿、RSI 超买超卖与顶背离、布林突破 / 收窄、Squeeze 释放（多/空）、WaveTrend 交叉、ADX 趋势强度、均线多头 / 空头排列、SuperTrend 转向、Elder 信号等。

### 三级数据源降级容错

`akshare`（主）→ `baostock`（备）→ `yfinance`（港美股）

单一数据源失败自动降级，不会导致整条采集链路中断。APScheduler 调度 12 个定时任务，采集日志入库（`collect_log` 表）。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12+ · FastAPI · SQLite · pandas / NumPy · APScheduler |
| 前端 | Vue 3 · Vite · ECharts · TailwindCSS |
| 数据源 | akshare · baostock · yfinance |
| 部署 | Docker Compose（nginx + uvicorn）· 健康检查 · 数据卷持久化 |

---

## 快速开始

### 方式一：Docker（推荐）

```bash
docker compose up -d
# 前端 http://localhost:5173
# 后端 API 文档 http://localhost:8000/docs
```

### 方式二：本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
python -m api                    # http://localhost:8000

# 前端（另开一个终端）
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

### 采集数据

仓库自带一份演示数据库（`data/market_data.db`，截至 2026-06），clone 后可直接启动查看。

要更新数据 / 采集全量：

```bash
cd backend
python -c "from data_engine.collector import DataCollector; DataCollector().collect_all()"
```

或调用 API：`POST /api/system/collect`

**采集任务包含**：A 股日线行情、历史 K 线回补（baostock 250 天）、实时估值、多报告期财务数据（8 个季度）、市场情绪指标、北向资金。

---

## 项目结构

```
stock-dashboard/
├── backend/
│   ├── api/__init__.py           # FastAPI 应用（17 个端点）
│   ├── analytics/
│   │   ├── technical.py          # 31 个技术指标引擎
│   │   ├── screener.py           # 基本面多条件筛选
│   │   ├── sentiment.py          # 市场情绪评分
│   │   └── valuation.py          # 估值分析
│   ├── data_engine/
│   │   ├── collector.py          # 多源数据采集（akshare/baostock/yfinance）
│   │   ├── db.py                 # SQLite 数据访问层
│   │   └── scheduler_jobs.py     # APScheduler 定时任务
│   └── tests/                    # pytest 测试
├── frontend/
│   └── src/
│       ├── views/                # 6 个功能页面
│       ├── components/KLineChart.vue   # 4 面板联动图表
│       └── api/index.js          # API 封装
├── data/market_data.db           # SQLite 数据库（演示数据）
└── docker-compose.yml
```

---

## API 端点

```
GET  /api/overview                     行情总览
GET  /api/quote/{symbol}               个股行情
GET  /api/kline/{symbol}               K 线数据
GET  /api/valuation/rank               估值排名
GET  /api/valuation/distribution       估值分布
GET  /api/valuation/{symbol}           个股估值
GET  /api/sentiment/summary            情绪评分
GET  /api/sentiment/fund-flow          北向资金
GET  /api/sentiment/breadth            涨跌比
GET  /api/sentiment/vix                VIX
GET  /api/screener                     基本面筛选
GET  /api/watchlist                    自选股列表
POST /api/watchlist                    添加自选股
DEL  /api/watchlist                    删除自选股
GET  /api/watchlist/analysis           自选股分析
GET  /api/system/status                系统状态
POST /api/system/collect               触发采集
```

---

## 已知限制

这个项目定位是**个人研究与技术验证**，不是生产级交易系统。如实说明几点：

- **数据是快照**：仓库自带数据库截至 2026-06，非实时行情。实时数据需自行触发采集。
- **港美股行情数据不完整**：股票列表含港股 20 只、美股 37 只，但日线行情主要覆盖 A 股。
- **无鉴权**：API 未做认证，仅适合本地 / 内网单机使用，请勿直接暴露到公网。
- **无回测与策略引擎**：提供指标计算与信号检测，不含回测、组合管理、实盘对接。
- **数据源限制**：依赖公开免费接口（akshare / baostock / yfinance），东方财富接口可能被 WAF 阻断，估值数据偶有不全。
- **`stocks` 表含约 5,970 只新三板公司**：财务数据取自东方财富业绩报表，该接口同时覆盖北交所与新三板，因此 `stocks` 表比 A 股实际上市公司数偏大。这些公司没有行情与估值数据，**不会进入选股结果**（选股器从 `daily_valuation` 出发），但直接 `SELECT` 全表时需注意。
- **353 只 `920xxx` 代码被标为 `sh`/`SSE`**：`920xxx` 是北交所新代码段，`_a_code_to_symbol()` 目前按「9 开头 → 上海」处理，归属有误。`market` 字段仍是 `A`，不影响筛选逻辑，但按交易所统计时会偏。修正需要同步迁移 4 张表，暂未处理。
- **Python 版本**：建议 3.12；3.14 下部分依赖库兼容性待验证。
- **仅供研究学习**：本项目不构成任何投资建议。

---

## 测试

```bash
cd backend
pip install pytest
pytest tests/ -v
```

---

## License

MIT License — 详见 [LICENSE](LICENSE)

## 数据来源声明

行情与财务数据来自公开免费接口（akshare、baostock、yfinance），版权归原始数据提供方所有。本项目仅用于技术研究与学习。
