"""
FastAPI 后端入口
提供 REST API 供 Vue 前端调用
"""
import sys
from pathlib import Path

# 确保 backend 目录在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import numpy as np
import logging

from data_engine.db import Database
from data_engine.collector import DataCollector
from data_engine.scheduler_jobs import MarketScheduler
from analytics.technical import TechnicalAnalyzer
from analytics.valuation import ValuationAnalyzer
from analytics.sentiment import SentimentAnalyzer
from analytics.screener import StockScreener

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_last_collect():
    """从 collect_log 读取最后一次采集时间"""
    try:
        if db:
            log_df = db.get_collect_log(limit=1)
            if not log_df.empty:
                row = log_df.iloc[0]
                return {
                    'task': row.get('task_name', 'unknown'),
                    'time': str(row.get('start_time', '')),
                    'status': row.get('status', 'unknown'),
                }
    except Exception:
        pass
    return None


def df_to_json(df: pd.DataFrame) -> list:
    """DataFrame 转 JSON-safe dict，NaN → None"""
    result = []
    for _, row in df.iterrows():
        d = {}
        for k, v in row.items():
            if v is None or (isinstance(v, float) and pd.isna(v)):
                d[k] = None
            elif isinstance(v, (np.integer, np.floating)):
                d[k] = float(v) if not pd.isna(v) else None
            else:
                d[k] = v
        result.append(d)
    return result

# 全局实例
db: Optional[Database] = None
scheduler: Optional[MarketScheduler] = None
collector: Optional[DataCollector] = None
tech_analyzer: Optional[TechnicalAnalyzer] = None
val_analyzer: Optional[ValuationAnalyzer] = None
sent_analyzer: Optional[SentimentAnalyzer] = None
screener: Optional[StockScreener] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global db, scheduler, collector, tech_analyzer, val_analyzer, sent_analyzer, screener

    logger.info("正在初始化数据库和调度器...")
    db = Database()
    collector = DataCollector(db)
    tech_analyzer = TechnicalAnalyzer()
    val_analyzer = ValuationAnalyzer(db)
    sent_analyzer = SentimentAnalyzer(db)
    screener = StockScreener(db)

    # 首次启动时后台异步采集（不阻塞启动）
    stocks = db.get_stocks(market='A', active_only=True)
    if stocks.empty:
        logger.info("首次运行，后台初始化数据...")
        import threading
        def _init_data():
            try:
                collector.collect_all()
                logger.info("初始数据采集完成")
            except Exception as e:
                logger.warning(f"初始数据采集部分失败: {e}")
        threading.Thread(target=_init_data, daemon=True).start()
        logger.info("服务已就绪，数据正在后台采集中...")

    # 启动定时调度器
    scheduler = MarketScheduler(db)
    scheduler.start()

    yield

    # 关闭
    scheduler.stop()
    logger.info("应用已关闭")


app = FastAPI(
    title="Stock Dashboard API",
    description="个人股票市场每日分析系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 行情接口
# ============================================================

@app.get("/api/quote/{symbol}")
async def get_quote(symbol: str, market: str = 'A'):
    """获取个股最新报价"""
    prices = db.get_daily_prices(symbol)
    if prices.empty:
        raise HTTPException(404, f"未找到股票: {symbol}")

    latest = prices.iloc[-1]
    prev = prices.iloc[-2] if len(prices) > 1 else latest

    return {
        'symbol': symbol,
        'date': str(latest['date']),
        'open': latest['open'],
        'high': latest['high'],
        'low': latest['low'],
        'close': latest['close'],
        'volume': latest['volume'],
        'amount': latest['amount'],
        'change_pct': latest['change_pct'],
        'change': round(float(latest['close']) - float(prev['close']), 4) if prev['close'] else 0,
    }


@app.get("/api/kline/{symbol}")
async def get_kline(
    symbol: str,
    period: str = Query('daily', description="daily | weekly | monthly"),
    limit: int = Query(250, description="数据条数"),
    indicators: str = Query('', description="逗号分隔: ma,macd,rsi,boll,kdj"),
):
    """获取 K 线数据（含技术指标）"""
    prices = db.get_daily_prices(symbol)
    if prices.empty:
        raise HTTPException(404, f"未找到股票: {symbol}")

    df = prices.tail(limit).copy()
    df['date'] = df['date'].astype(str)

    # 计算技术指标
    try:
        df = TechnicalAnalyzer.calc_all(df[['date', 'open', 'high', 'low', 'close', 'volume']])
    except Exception as e:
        logger.warning(f"技术指标计算失败: {e}")

    # 替换 NaN 为 None（JSON 兼容）
    result = []
    for _, row in df.iterrows():
        d = {}
        for k, v in row.items():
            if isinstance(v, float) and pd.isna(v):
                d[k] = None
            elif isinstance(v, (np.integer, np.floating)):
                d[k] = float(v) if not pd.isna(v) else None
            else:
                d[k] = v if not (isinstance(v, float) and pd.isna(v)) else None
        result.append(d)

    # 检测信号
    signals = TechnicalAnalyzer.detect_signals(df)

    return {
        'symbol': symbol,
        'period': period,
        'data': result,
        'signals': signals[-5:] if signals else [],
    }


# ============================================================
# 估值接口
# ============================================================

@app.get("/api/valuation/rank")
async def get_valuation_rank(
    market: str = Query('A', description="A | HK | US"),
    metric: str = Query('pe', description="pe | pb | ps"),
    limit: int = Query(50),
):
    """全市场估值排名"""
    df = val_analyzer.get_valuation_rank(market=market, metric=metric, limit=limit)
    return df.pipe(df_to_json)


@app.get("/api/valuation/distribution")
async def get_valuation_distribution(market: str = 'A'):
    """全市场估值分布"""
    return val_analyzer.get_valuation_distribution(market=market)


@app.get("/api/valuation/{symbol}")
async def get_valuation_detail(symbol: str):
    """个股估值详情"""
    return val_analyzer.get_stock_valuation_detail(symbol)


# ============================================================
# 市场情绪接口
# ============================================================

@app.get("/api/sentiment/summary")
async def get_sentiment_summary():
    """市场情绪综合评分"""
    return sent_analyzer.get_market_sentiment_summary()


@app.get("/api/sentiment/fund-flow")
async def get_fund_flow(days: int = 30):
    """北向资金流向"""
    df = sent_analyzer.get_north_flow_trend(days=days)
    if df.empty:
        return []
    return df.pipe(df_to_json)


@app.get("/api/sentiment/breadth")
async def get_market_breadth(market: str = 'A', days: int = 30):
    """市场涨跌统计"""
    df = sent_analyzer.get_market_breadth_trend(market=market, days=days)
    if df.empty:
        return []
    return df.pipe(df_to_json)


@app.get("/api/sentiment/vix")
async def get_vix(days: int = 30):
    """VIX 恐慌指数"""
    df = sent_analyzer.get_vix_trend(days=days)
    if df.empty:
        return []
    return df.pipe(df_to_json)


# ============================================================
# 筛选接口
# ============================================================

@app.get("/api/screener")
async def screen_stocks(
    market: str = Query('A'),
    pe_max: float = Query(None),
    pb_max: float = Query(None),
    roe_min: float = Query(None),
    revenue_growth_min: float = Query(None),
    net_profit_growth_min: float = Query(None),
    dividend_yield_min: float = Query(None),
    market_cap_min: float = Query(None),
    market_cap_max: float = Query(None),
    limit: int = Query(200),
):
    """多条件基本面筛选"""
    df = screener.screen(
        market=market,
        pe_max=pe_max,
        pb_max=pb_max,
        roe_min=roe_min,
        revenue_growth_min=revenue_growth_min,
        net_profit_growth_min=net_profit_growth_min,
        dividend_yield_min=dividend_yield_min,
        market_cap_min=market_cap_min,
        market_cap_max=market_cap_max,
        limit=limit,
    )
    if df.empty:
        return []
    return df.pipe(df_to_json)


# ============================================================
# 自选股接口
# ============================================================

@app.get("/api/watchlist")
async def get_watchlist():
    """获取自选股列表"""
    df = db.get_watchlist()
    if df.empty:
        return []
    return df.to_dict(orient='records')


@app.post("/api/watchlist/{symbol}")
async def add_watchlist(symbol: str, note: str = None):
    """添加自选股"""
    db.add_watchlist(symbol, note)
    return {"success": True, "symbol": symbol}


@app.delete("/api/watchlist/{symbol}")
async def remove_watchlist(symbol: str):
    """移除自选股"""
    db.remove_watchlist(symbol)
    return {"success": True, "symbol": symbol}


@app.get("/api/watchlist/analysis")
async def get_watchlist_analysis():
    """自选股分析概览"""
    df = screener.get_watchlist_analysis()
    if df.empty:
        return []
    return df.pipe(df_to_json)


# ============================================================
# 系统接口
# ============================================================

@app.get("/api/system/status")
async def get_system_status():
    """系统运行状态"""
    scheduler_status = scheduler.get_status() if scheduler else {}
    return {
        'database': str(db.db_path) if db else 'N/A',
        'scheduler': scheduler_status,
        'last_collect': _get_last_collect(),
    }


@app.post("/api/system/collect")
async def trigger_collect(task: str = Query(None, description="指定任务名，不填则全量采集")):
    """手动触发数据采集"""
    if not collector:
        raise HTTPException(503, "采集器未初始化")
    try:
        if task:
            scheduler.run_now(task)
        else:
            collector.collect_all()
        return {"success": True, "task": task or "all"}
    except Exception as e:
        raise HTTPException(500, f"采集失败: {str(e)}")


# ============================================================
# 首页概览
# ============================================================

@app.get("/api/overview")
async def get_overview():
    """首页仪表盘数据聚合"""
    overview = {
        'indices': {}, 'market_breadth': {}, 'north_flow': {}, 'vix': {},
        'updated': datetime.now().isoformat(),
    }
    try:
        indices = {
            '上证指数': 'sh000001', '深证成指': 'sz399001', '创业板指': 'sz399006',
            '科创50': 'sh000688', '沪深300': 'sh000300', '中证500': 'sh000905',
        }
        for name, sym in indices.items():
            prices = db.get_daily_prices(sym)
            if not prices.empty:
                latest = prices.iloc[-1]
                chg = latest.get('change_pct')
                chg = float(chg) if chg is not None and not pd.isna(chg) else 0.0
                overview['indices'][name] = {
                    'close': float(latest['close']),
                    'change_pct': chg,
                }
        breadth_df = db.get_market_breadth(market='A', days=1)
        if not breadth_df.empty:
            row = breadth_df.iloc[0]
            overview['market_breadth'] = {
                'up': int(row['up_count']), 'down': int(row['down_count']),
                'flat': int(row['flat_count']), 'limit_up': int(row['limit_up']),
                'limit_down': int(row['limit_down']), 'total_volume': float(row['total_volume']),
            }
        flow_df = db.get_fund_flow(days=1)
        if not flow_df.empty:
            row = flow_df.iloc[0]
            overview['north_flow'] = {'net_flow': float(row['net_flow'])}
        vix_df = db.get_vix(days=1)
        if not vix_df.empty:
            row = vix_df.iloc[0]
            overview['vix'] = {'close': float(row['close'])}
        for name, sym in {'标普500': '^GSPC', '纳斯达克': '^IXIC', '道琼斯': '^DJI'}.items():
            prices = db.get_daily_prices(sym)
            if not prices.empty:
                overview['indices'][name] = {
                    'close': float(prices.iloc[-1]['close']),
                    'change_pct': float(prices.iloc[-1].get('change_pct')) if prices.iloc[-1].get('change_pct') is not None and not pd.isna(prices.iloc[-1].get('change_pct')) else 0.0,
                }
        for name, sym in {'恒生指数': '^HSI', '恒生科技': '^HSTECH'}.items():
            prices = db.get_daily_prices(sym)
            if not prices.empty:
                overview['indices'][name] = {
                    'close': float(prices.iloc[-1]['close']),
                    'change_pct': float(prices.iloc[-1].get('change_pct')) if prices.iloc[-1].get('change_pct') is not None and not pd.isna(prices.iloc[-1].get('change_pct')) else 0.0,
                }
    except Exception as e:
        logger.error(f"Overview error: {e}")
    return overview


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
