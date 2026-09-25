"""
SQLite 数据库模块
管理所有数据表的创建、读写操作
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DB_DIR / "market_data.db"


class Database:
    """市场数据库管理类"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """初始化所有数据表"""
        with self._get_conn() as conn:
            conn.executescript("""
                -- 股票代码清单
                CREATE TABLE IF NOT EXISTS stocks (
                    symbol TEXT PRIMARY KEY,       -- 代码格式: sh000001 / 000001.SZ / AAPL
                    name TEXT NOT NULL,             -- 股票名称
                    market TEXT NOT NULL,           -- A / HK / US
                    exchange TEXT,                  -- SSE / SZSE / BSE / HKEX / NYSE / NASDAQ
                    industry TEXT,                  -- 行业分类
                    listed_date TEXT,               -- 上市日期
                    is_active INTEGER DEFAULT 1     -- 是否仍上市
                );

                -- 日线行情 (OHLCV)
                CREATE TABLE IF NOT EXISTS daily_prices (
                    date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    amount REAL,
                    turnover REAL,                 -- 换手率(%)
                    change_pct REAL,               -- 涨跌幅(%)
                    PRIMARY KEY (date, symbol),
                    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
                );

                -- 估值数据 (每日)
                CREATE TABLE IF NOT EXISTS daily_valuation (
                    date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    pe REAL,                        -- 市盈率
                    pe_ttm REAL,                    -- 滚动市盈率
                    pb REAL,                        -- 市净率
                    ps REAL,                        -- 市销率
                    dividend_yield REAL,            -- 股息率(%)
                    total_mv REAL,                  -- 总市值(亿)
                    circ_mv REAL,                   -- 流通市值(亿)
                    PRIMARY KEY (date, symbol),
                    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
                );

                -- 资金流向 (北向/南向)
                CREATE TABLE IF NOT EXISTS fund_flow (
                    date TEXT NOT NULL,
                    flow_type TEXT NOT NULL,        -- north / south
                    net_flow REAL,                  -- 净流入(亿)
                    buy_amount REAL,                -- 买入金额(亿)
                    sell_amount REAL,               -- 卖出金额(亿)
                    balance REAL,                   -- 累计余额(亿)
                    PRIMARY KEY (date, flow_type)
                );

                -- VIX 恐慌指数
                CREATE TABLE IF NOT EXISTS vix_data (
                    date TEXT NOT NULL PRIMARY KEY,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL
                );

                -- 市场情绪统计 (涨跌比等)
                CREATE TABLE IF NOT EXISTS market_breadth (
                    date TEXT NOT NULL,
                    market TEXT NOT NULL,           -- A / HK / US
                    up_count INTEGER,               -- 上涨家数
                    down_count INTEGER,             -- 下跌家数
                    flat_count INTEGER,             -- 平盘家数
                    limit_up INTEGER,               -- 涨停家数
                    limit_down INTEGER,             -- 跌停家数
                    total_volume REAL,              -- 总成交额(亿)
                    PRIMARY KEY (date, market)
                );

                -- 财务数据 (季度)
                CREATE TABLE IF NOT EXISTS financials (
                    symbol TEXT NOT NULL,
                    report_date TEXT NOT NULL,       -- 报告期: 2024Q4
                    eps REAL,                        -- 每股收益
                    roe REAL,                        -- ROE(%)
                    revenue REAL,                    -- 营业收入(亿)
                    revenue_yoy REAL,               -- 营收同比增长(%)
                    net_profit REAL,                 -- 净利润(亿)
                    net_profit_yoy REAL,             -- 净利润同比增长(%)
                    debt_ratio REAL,                 -- 资产负债率(%)
                    free_cash_flow REAL,             -- 自由现金流(亿)
                    gross_margin REAL,               -- 毛利率(%)
                    PRIMARY KEY (symbol, report_date),
                    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
                );

                -- 自选股
                CREATE TABLE IF NOT EXISTS watchlist (
                    symbol TEXT PRIMARY KEY,
                    added_date TEXT DEFAULT (date('now')),
                    note TEXT,
                    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
                );

                -- 采集日志
                CREATE TABLE IF NOT EXISTS collect_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    start_time TEXT,
                    end_time TEXT,
                    status TEXT,                    -- success / failed
                    records_count INTEGER,
                    error_msg TEXT
                );
            """)
            logger.info("数据库表初始化完成")

    # ===== 写入方法 =====

    def upsert_stocks(self, df: pd.DataFrame):
        """批量插入/更新股票信息"""
        with self._get_conn() as conn:
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO stocks (symbol, name, market, exchange, industry, listed_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (row.get('symbol'), row.get('name'), row.get('market'),
                      row.get('exchange'), row.get('industry'), row.get('listed_date'),
                      row.get('is_active', 1)))

    def insert_daily_prices(self, df: pd.DataFrame):
        """批量插入日线数据"""
        with self._get_conn() as conn:
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO daily_prices (date, symbol, open, high, low, close, volume, amount, turnover, change_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(row['date']), row['symbol'], row.get('open'), row.get('high'),
                      row.get('low'), row.get('close'), row.get('volume'), row.get('amount'),
                      row.get('turnover'), row.get('change_pct')))

    def insert_daily_valuation(self, df: pd.DataFrame):
        """批量插入估值数据"""
        with self._get_conn() as conn:
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO daily_valuation (date, symbol, pe, pe_ttm, pb, ps, dividend_yield, total_mv, circ_mv)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(row['date']), row['symbol'], row.get('pe'), row.get('pe_ttm'),
                      row.get('pb'), row.get('ps'), row.get('dividend_yield'),
                      row.get('total_mv'), row.get('circ_mv')))

    def insert_fund_flow(self, date: str, flow_type: str, data: dict):
        """插入资金流向数据"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO fund_flow (date, flow_type, net_flow, buy_amount, sell_amount, balance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date, flow_type, data.get('net_flow'), data.get('buy_amount'),
                  data.get('sell_amount'), data.get('balance')))

    def insert_market_breadth(self, date: str, market: str, data: dict):
        """插入市场情绪数据"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO market_breadth (date, market, up_count, down_count, flat_count, limit_up, limit_down, total_volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (date, market, data.get('up_count'), data.get('down_count'),
                  data.get('flat_count'), data.get('limit_up'), data.get('limit_down'),
                  data.get('total_volume')))

    def insert_vix(self, df: pd.DataFrame):
        """插入VIX数据"""
        with self._get_conn() as conn:
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO vix_data (date, open, high, low, close)
                    VALUES (?, ?, ?, ?, ?)
                """, (str(row['date']), row.get('open'), row.get('high'),
                      row.get('low'), row.get('close')))

    def insert_financials(self, df: pd.DataFrame):
        """插入财务数据"""
        with self._get_conn() as conn:
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO financials (symbol, report_date, eps, roe, revenue, revenue_yoy, net_profit, net_profit_yoy, debt_ratio, free_cash_flow, gross_margin)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (row['symbol'], row['report_date'], row.get('eps'), row.get('roe'),
                      row.get('revenue'), row.get('revenue_yoy'), row.get('net_profit'),
                      row.get('net_profit_yoy'), row.get('debt_ratio'), row.get('free_cash_flow'),
                      row.get('gross_margin')))

    def log_collect(self, task_name: str, start_time: str, end_time: str, status: str, records: int, error: str = None):
        """记录采集日志"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO collect_log (task_name, start_time, end_time, status, records_count, error_msg)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (task_name, start_time, end_time, status, records, error))

    # ===== 查询方法 =====

    def get_stocks(self, market: str = None, active_only: bool = True) -> pd.DataFrame:
        """获取股票列表"""
        query = "SELECT * FROM stocks WHERE 1=1"
        params = []
        if market:
            query += " AND market = ?"
            params.append(market)
        if active_only:
            query += " AND is_active = 1"
        with self._get_conn() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def get_daily_prices(self, symbol: str, start: str = None, end: str = None) -> pd.DataFrame:
        """获取某只股票的日线数据"""
        query = "SELECT * FROM daily_prices WHERE symbol = ?"
        params = [symbol]
        if start:
            query += " AND date >= ?"
            params.append(start)
        if end:
            query += " AND date <= ?"
            params.append(end)
        query += " ORDER BY date ASC"
        with self._get_conn() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def get_latest_valuation(self, market: str = None, limit: int = 100) -> pd.DataFrame:
        """获取最新估值数据（按PE排序）"""
        query = """
            SELECT v.*, s.name, s.market, s.industry
            FROM daily_valuation v
            JOIN stocks s ON v.symbol = s.symbol
            WHERE v.date = (SELECT MAX(date) FROM daily_valuation)
              AND v.pe > 0
        """
        params = []
        if market:
            query += " AND s.market = ?"
            params.append(market)
        query += " ORDER BY v.pe ASC LIMIT ?"
        params.append(limit)
        with self._get_conn() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def get_fund_flow(self, days: int = 30) -> pd.DataFrame:
        """获取近期北向资金"""
        with self._get_conn() as conn:
            return pd.read_sql_query("""
                SELECT * FROM fund_flow ORDER BY date DESC LIMIT ?
            """, conn, params=[days])

    def get_market_breadth(self, market: str = 'A', days: int = 30) -> pd.DataFrame:
        """获取市场涨跌统计"""
        with self._get_conn() as conn:
            return pd.read_sql_query("""
                SELECT * FROM market_breadth WHERE market = ? ORDER BY date DESC LIMIT ?
            """, conn, params=[market, days])

    def get_vix(self, days: int = 30) -> pd.DataFrame:
        """获取VIX数据"""
        with self._get_conn() as conn:
            return pd.read_sql_query("""
                SELECT * FROM vix_data ORDER BY date DESC LIMIT ?
            """, conn, params=[days])

    def get_watchlist(self) -> pd.DataFrame:
        """获取自选股列表"""
        with self._get_conn() as conn:
            return pd.read_sql_query("""
                SELECT w.*, s.name, s.market
                FROM watchlist w JOIN stocks s ON w.symbol = s.symbol
            """, conn)

    def add_watchlist(self, symbol: str, note: str = None):
        """添加自选股"""
        with self._get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO watchlist (symbol, note) VALUES (?, ?)", (symbol, note))

    def remove_watchlist(self, symbol: str):
        """移除自选股"""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))

    def get_collect_log(self, limit: int = 5) -> pd.DataFrame:
        """获取最近采集日志"""
        with self._get_conn() as conn:
            return pd.read_sql_query("""
                SELECT task_name, start_time, end_time, status, records_count, error_msg
                FROM collect_log ORDER BY id DESC LIMIT ?
            """, conn, params=[limit])
