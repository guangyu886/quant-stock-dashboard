"""
数据采集器
统一封装 akshare / baostock / yfinance 的数据获取接口
A股优先 akshare，失败自动降级到 baostock
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# 延迟导入，避免依赖未安装时崩溃
try:
    import akshare as ak
except ImportError:
    ak = None
    logger.warning("akshare 未安装，A股/港股数据采集不可用")

try:
    import yfinance as yf
except ImportError:
    yf = None
    logger.warning("yfinance 未安装，美股数据采集不可用")

from .db import Database
from .symbols import (
    A_INDEX_SYMBOLS, HK_INDEX_SYMBOLS, US_INDEX_SYMBOLS,
    US_STARTER_SYMBOLS, HK_STARTER_SYMBOLS
)


class DataCollector:
    """统一数据采集器"""

    def __init__(self, db: Database = None):
        self.db = db or Database()
        self._log_dir = Path(__file__).parent.parent.parent / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def _log_task(self, task_name: str, func, *args, **kwargs):
        """带日志记录的任务包装器"""
        start = datetime.now().isoformat()
        records = 0
        status = "success"
        error = None
        try:
            records = func(*args, **kwargs)
        except Exception as e:
            status = "failed"
            error = str(e)
            logger.error(f"[{task_name}] 采集失败: {e}", exc_info=True)
        finally:
            end = datetime.now().isoformat()
            self.db.log_collect(task_name, start, end, status, records, error)
        return records

    # ============================================================
    # A股数据采集
    # ============================================================

    def collect_a_stock_list(self) -> int:
        """采集 A 股全市场股票列表（akshare 优先，失败降级 baostock）"""
        try:
            return self._collect_a_stock_list_akshare()
        except Exception as e:
            logger.warning(f"akshare 股票列表失败: {e}，降级到 baostock")
            return self._collect_a_stock_list_baostock()

    def _collect_a_stock_list_akshare(self) -> int:

        logger.info("正在采集 A 股股票列表...")
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            logger.warning("A 股股票列表为空")
            return 0

        records = []
        for _, row in df.iterrows():
            code = str(row.get('代码', ''))
            if not code:
                continue

            # 判断交易所
            if code.startswith('6') or code.startswith('9'):
                exchange = 'SSE'
                symbol = f"sh{code}"
            elif code.startswith('0') or code.startswith('3') or code.startswith('1'):
                exchange = 'SZSE'
                symbol = f"sz{code}"
            elif code.startswith('8') or code.startswith('4'):
                exchange = 'BSE'
                symbol = f"bj{code}"
            else:
                exchange = 'SSE'
                symbol = f"sh{code}"

            records.append({
                'symbol': symbol,
                'name': str(row.get('名称', '')),
                'market': 'A',
                'exchange': exchange,
                'industry': str(row.get('所属行业', '')),
                'listed_date': None,
                'is_active': 1,
            })

        result_df = pd.DataFrame(records)
        self.db.upsert_stocks(result_df)
        logger.info(f"A 股股票列表采集完成: {len(records)} 只")
        return len(records)

    def collect_a_daily_prices(self, date: str = None) -> int:
        """采集 A 股全市场日线行情（akshare优先，失败降级baostock）"""
        try:
            return self._collect_a_daily_prices_akshare(date)
        except Exception as e:
            logger.warning(f"akshare 日线失败: {e}，降级到 baostock")
            return self._collect_a_daily_prices_baostock()

    def _collect_a_daily_prices_akshare(self, date: str = None) -> int:

        date = date or datetime.now().strftime('%Y-%m-%d')
        logger.info(f"正在采集 A 股日线行情: {date}")

        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as e:
            logger.error(f"获取 A 股行情失败: {e}")
            raise

        if df is None or df.empty:
            return 0

        records = []
        for _, row in df.iterrows():
            code = str(row.get('代码', ''))
            if not code:
                continue

            symbol = self._a_code_to_symbol(code)

            records.append({
                'date': date,
                'symbol': symbol,
                'open': self._safe_float(row.get('今开')),
                'high': self._safe_float(row.get('最高')),
                'low': self._safe_float(row.get('最低')),
                'close': self._safe_float(row.get('最新价')),
                'volume': self._safe_float(row.get('成交量')),
                'amount': self._safe_float(row.get('成交额')),
                'turnover': self._safe_float(row.get('换手率')),
                'change_pct': self._safe_float(row.get('涨跌幅')),
            })

        result_df = pd.DataFrame(records)
        self.db.insert_daily_prices(result_df)
        logger.info(f"A 股日线采集完成: {len(records)} 条")
        return len(records)

    def collect_a_valuation(self) -> int:
        """采集 A 股估值数据（akshare优先，失败降级baostock）"""
        try:
            return self._collect_a_valuation_akshare()
        except Exception as e:
            logger.warning(f"akshare 估值失败: {e}，降级到 baostock")
            return self._collect_a_valuation_baostock()

    def _collect_a_valuation_akshare(self) -> int:

        logger.info("正在采集 A 股估值数据...")

        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as e:
            logger.error(f"获取 A 股估值失败: {e}")
            raise

        if df is None or df.empty:
            return 0

        date = datetime.now().strftime('%Y-%m-%d')
        records = []
        for _, row in df.iterrows():
            code = str(row.get('代码', ''))
            if not code:
                continue

            symbol = self._a_code_to_symbol(code)

            # 计算总市值和流通市值（统一为亿）
            total_mv = self._safe_float(row.get('总市值'))
            circ_mv = self._safe_float(row.get('流通市值'))

            records.append({
                'date': date,
                'symbol': symbol,
                'pe': self._safe_float(row.get('市盈率-动态')),
                'pe_ttm': self._safe_float(row.get('市盈率-静态')),
                'pb': self._safe_float(row.get('市净率')),
                'ps': None,  # 需要从财报接口获取
                'dividend_yield': None,  # 需要从分红接口获取
                'total_mv': total_mv,
                'circ_mv': circ_mv,
            })

        result_df = pd.DataFrame(records)
        self.db.insert_daily_valuation(result_df)
        logger.info(f"A 股估值采集完成: {len(records)} 条")
        return len(records)

    def collect_a_fund_flow(self) -> int:
        """采集北向资金流向"""

        if ak is None:
            raise ImportError("akshare 未安装")

        logger.info("正在采集北向资金数据...")

        try:
            df = ak.stock_hsgt_hist_em()
        except Exception:
            # 备选：北向资金汇总
            df = ak.stock_hsgt_fund_flow_summary_em()

        if df is None or df.empty:
            return 0

        records = 0
        today = datetime.now().strftime('%Y-%m-%d')

        # 获取最新一行
        latest = df.iloc[-1] if not df.empty else None
        if latest is not None:
            self.db.insert_fund_flow(today, 'north', {
                'net_flow': self._safe_float(latest.get('净买额') or latest.get('当日资金流向')),
                'buy_amount': self._safe_float(latest.get('买入金额')),
                'sell_amount': self._safe_float(latest.get('卖出金额')),
                'balance': self._safe_float(latest.get('累计资金流向')),
            })
            records = 1

        logger.info(f"北向资金采集完成: {records} 条")
        return records

    def collect_a_market_breadth(self) -> int:
        """采集 A 股市场情绪（涨跌比/成交额）"""

        if ak is None:
            raise ImportError("akshare 未安装")

        logger.info("正在采集市场情绪数据...")
        date = datetime.now().strftime('%Y-%m-%d')

        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as e:
            logger.error(f"获取市场情绪失败: {e}")
            return 0

        if df is None or df.empty:
            return 0

        up_count = int((df['涨跌幅'] > 0).sum())
        down_count = int((df['涨跌幅'] < 0).sum())
        flat_count = int((df['涨跌幅'] == 0).sum())
        total_volume = df['成交额'].astype(float).sum() / 1e8  # 转为亿

        # 涨停/跌停统计
        limit_up = int((df['涨跌幅'] >= 9.9).sum())
        limit_down = int((df['涨跌幅'] <= -9.9).sum())

        self.db.insert_market_breadth(date, 'A', {
            'up_count': up_count,
            'down_count': down_count,
            'flat_count': flat_count,
            'limit_up': limit_up,
            'limit_down': limit_down,
            'total_volume': round(total_volume, 2),
        })

        logger.info(f"市场情绪采集完成: 涨{up_count} 跌{down_count} 平{flat_count}")
        return 1

    def collect_a_financials(self, symbol: str = None) -> int:
        """采集 A 股财务数据（业绩报表）"""

        if ak is None:
            raise ImportError("akshare 未安装")

        logger.info("正在采集财务数据...")

        try:
            df = ak.stock_yjbb_em(date=str(datetime.now().year) + "0331")
        except Exception:
            try:
                df = ak.stock_yjbb_em(date=str(datetime.now().year - 1) + "1231")
            except Exception as e:
                logger.error(f"获取财务数据失败: {e}")
                return 0

        if df is None or df.empty:
            return 0

        records = []
        for _, row in df.iterrows():
            code = str(row.get('代码', ''))
            if not code:
                continue
            symbol = self._a_code_to_symbol(code)

            records.append({
                'symbol': symbol,
                'report_date': str(row.get('报告期', '')),
                'eps': self._safe_float(row.get('基本每股收益')),
                'roe': self._safe_float(row.get('净资产收益率')),
                'revenue': self._safe_float(row.get('营业总收入')),
                'revenue_yoy': self._safe_float(row.get('营业收入同比增长')),
                'net_profit': self._safe_float(row.get('净利润')),
                'net_profit_yoy': self._safe_float(row.get('净利润同比增长')),
                'debt_ratio': self._safe_float(row.get('资产负债率')),
                'free_cash_flow': None,
                'gross_margin': self._safe_float(row.get('销售毛利率')),
            })

        result_df = pd.DataFrame(records)
        self.db.insert_financials(result_df)
        logger.info(f"财务数据采集完成: {len(records)} 条")
        return len(records)

    # ============================================================
    # A股 baostock 降级采集（当 akshare 网络不通时）
    # ============================================================

    def _collect_a_stock_list_baostock(self) -> int:
        """baostock 采集 A 股全市场股票列表"""
        import baostock as bs
        bs.login()
        try:
            rs = bs.query_stock_basic()
            records = []
            while (rs.error_code == '0') & rs.next():
                row = rs.get_row_data()
                code = row[0]
                name = row[1]
                # 判断交易所
                if code.startswith('sh.6') or code.startswith('sh.9'):
                    exchange, symbol = 'SSE', code.replace('sh.', 'sh')
                elif code.startswith('sz.0') or code.startswith('sz.3') or code.startswith('sz.1'):
                    exchange, symbol = 'SZSE', code.replace('sz.', 'sz')
                elif code.startswith('sz.2'):
                    exchange, symbol = 'SZSE', code.replace('sz.', 'sz')
                elif code.startswith('bj.'):
                    exchange, symbol = 'BSE', code.replace('bj.', 'bj')
                else:
                    exchange, symbol = 'SSE', code

                records.append({
                    'symbol': symbol, 'name': name, 'market': 'A',
                    'exchange': exchange, 'industry': '', 'listed_date': None, 'is_active': 1,
                })

            result_df = pd.DataFrame(records)
            self.db.upsert_stocks(result_df)
            logger.info(f"baostock A股列表: {len(records)} 只")
            return len(records)
        finally:
            bs.logout()

    def _collect_a_daily_prices_baostock(self) -> int:
        """baostock 采集 A 股日线行情"""
        import baostock as bs
        from datetime import datetime, timedelta
        bs.login()
        try:
            date = datetime.now().strftime('%Y-%m-%d')
            stocks = self.db.get_stocks(market='A', active_only=True)
            if stocks.empty:
                # 先采集股票列表
                self._collect_a_stock_list_baostock()
                stocks = self.db.get_stocks(market='A', active_only=True)

            records = []
            total = min(len(stocks), 500)  # 限制每次最多500只
            for _, stock in stocks.head(total).iterrows():
                try:
                    sym = stock['symbol']
                    bs_sym = sym.replace('sh', 'sh.').replace('sz', 'sz.').replace('bj', 'bj.')
                    rs = bs.query_history_k_data_plus(bs_sym,
                        'date,open,high,low,close,volume,amount,turn',
                        start_date=(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                        end_date=date, frequency='d')
                    while (rs.error_code == '0') & rs.next():
                        row = rs.get_row_data()
                        records.append({
                            'date': row[0], 'symbol': sym,
                            'open': self._safe_float(row[1]), 'high': self._safe_float(row[2]),
                            'low': self._safe_float(row[3]), 'close': self._safe_float(row[4]),
                            'volume': self._safe_float(row[5]), 'amount': self._safe_float(row[6]),
                            'turnover': self._safe_float(row[7]), 'change_pct': None,
                        })
                except Exception:
                    continue

            if records:
                result_df = pd.DataFrame(records)
                self.db.insert_daily_prices(result_df)
            logger.info(f"baostock A股日线: {len(records)} 条")
            return len(records)
        finally:
            bs.logout()

    def _collect_a_valuation_baostock(self) -> int:
        """baostock 采集 A 股估值数据（日线 + 市值估算）"""
        import baostock as bs
        from datetime import datetime
        bs.login()
        try:
            date = datetime.now().strftime('%Y-%m-%d')
            stocks = self.db.get_stocks(market='A', active_only=True)
            if stocks.empty:
                return 0

            records = []
            total = min(len(stocks), 1000)
            for _, stock in stocks.head(total).iterrows():
                try:
                    sym = stock['symbol']
                    bs_sym = sym.replace('sh', 'sh.').replace('sz', 'sz.').replace('bj', 'bj.')
                    # 用日线数据计算近似PE/PB（需要财务数据，baostock有query_history_k_data_plus）
                    rs = bs.query_history_k_data_plus(bs_sym,
                        'date,close,peTTM,pbMRQ',
                        start_date=date, end_date=date, frequency='d')
                    while (rs.error_code == '0') & rs.next():
                        row = rs.get_row_data()
                        records.append({
                            'date': row[0], 'symbol': sym,
                            'pe': self._safe_float(row[2]) if len(row) > 2 else None,
                            'pe_ttm': self._safe_float(row[2]) if len(row) > 2 else None,
                            'pb': self._safe_float(row[3]) if len(row) > 3 else None,
                            'ps': None, 'dividend_yield': None,
                            'total_mv': None, 'circ_mv': None,
                        })
                except Exception:
                    continue

            if records:
                result_df = pd.DataFrame(records)
                self.db.insert_daily_valuation(result_df)
            logger.info(f"baostock A股估值: {len(records)} 条")
            return len(records)
        finally:
            bs.logout()

    # ============================================================
    # 美股数据采集 (yfinance)
    # ============================================================

    def collect_us_stock_list(self) -> int:
        """初始化美股自选股列表到数据库"""

        if yf is None:
            raise ImportError("yfinance 未安装")

        records = []
        # 先加指数
        for sym, name in US_INDEX_SYMBOLS.items():
            records.append({
                'symbol': sym,
                'name': name,
                'market': 'US',
                'exchange': 'INDEX',
                'industry': '',
                'listed_date': None,
                'is_active': 1,
            })

        # 加自选股票
        for sym in US_STARTER_SYMBOLS:
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info or {}
                name = info.get('longName') or info.get('shortName') or sym
                exchange = info.get('exchange', '')
                industry = info.get('industry', '')
            except Exception:
                name = sym
                exchange = ''
                industry = ''

            records.append({
                'symbol': sym,
                'name': name,
                'market': 'US',
                'exchange': exchange,
                'industry': industry,
                'listed_date': None,
                'is_active': 1,
            })

        result_df = pd.DataFrame(records)
        self.db.upsert_stocks(result_df)
        logger.info(f"美股列表初始化完成: {len(records)} 只")
        return len(records)

    def collect_us_daily_prices(self, date: str = None) -> int:
        """采集美股日线数据（自选股列表）"""

        if yf is None:
            raise ImportError("yfinance 未安装")

        date = date or datetime.now().strftime('%Y-%m-%d')
        logger.info(f"正在采集美股日线: {date}")

        symbols = US_INDEX_SYMBOLS.copy()
        symbols.update({s: s for s in US_STARTER_SYMBOLS})
        all_syms = list(US_INDEX_SYMBOLS.keys()) + US_STARTER_SYMBOLS

        records = []
        for sym in all_syms:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="5d")
                if hist.empty:
                    continue

                latest = hist.iloc[-1]
                hist_date = hist.index[-1].strftime('%Y-%m-%d')

                records.append({
                    'date': hist_date,
                    'symbol': sym,
                    'open': round(float(latest['Open']), 4),
                    'high': round(float(latest['High']), 4),
                    'low': round(float(latest['Low']), 4),
                    'close': round(float(latest['Close']), 4),
                    'volume': int(latest['Volume']),
                    'amount': None,
                    'turnover': None,
                    'change_pct': None,
                })
                time.sleep(0.2)  # 避免请求过快
            except Exception as e:
                logger.warning(f"采集美股 {sym} 失败: {e}")
                continue

        if records:
            result_df = pd.DataFrame(records)
            # 计算涨跌幅
            self.db.insert_daily_prices(result_df)
        logger.info(f"美股日线采集完成: {len(records)} 条")
        return len(records)

    def collect_vix(self) -> int:
        """采集 VIX 恐慌指数"""

        if yf is None:
            raise ImportError("yfinance 未安装")

        logger.info("正在采集 VIX 数据...")

        try:
            ticker = yf.Ticker("^VIX")
            hist = ticker.history(period="1mo")
            if hist.empty:
                return 0

            records = []
            for idx, row in hist.iterrows():
                records.append({
                    'date': idx.strftime('%Y-%m-%d'),
                    'open': round(float(row['Open']), 2),
                    'high': round(float(row['High']), 2),
                    'low': round(float(row['Low']), 2),
                    'close': round(float(row['Close']), 2),
                })

            result_df = pd.DataFrame(records)
            self.db.insert_vix(result_df)
            logger.info(f"VIX 采集完成: {len(records)} 条")
            return len(records)
        except Exception as e:
            logger.error(f"VIX 采集失败: {e}")
            return 0

    # ============================================================
    # 港股数据采集
    # ============================================================

    def collect_hk_stock_list(self) -> int:
        """初始化港股自选股列表"""

        if ak is None:
            raise ImportError("akshare 未安装")

        records = []
        # 加指数（用 yfinance 取）
        for sym, name in HK_INDEX_SYMBOLS.items():
            records.append({
                'symbol': sym,
                'name': name,
                'market': 'HK',
                'exchange': 'INDEX',
                'industry': '',
                'listed_date': None,
                'is_active': 1,
            })

        # 加自选股票（尝试从 akshare 获取港股实时行情）
        try:
            hk_spot = ak.stock_hk_spot_em()
            if hk_spot is not None and not hk_spot.empty:
                for _, row in hk_spot.iterrows():
                    code = str(row.get('代码', ''))
                    if code in HK_STARTER_SYMBOLS:
                        records.append({
                            'symbol': code,
                            'name': str(row.get('名称', code)),
                            'market': 'HK',
                            'exchange': 'HKEX',
                            'industry': '',
                            'listed_date': None,
                            'is_active': 1,
                        })
        except Exception as e:
            logger.warning(f"获取港股列表失败: {e}，使用默认名称")
            for sym in HK_STARTER_SYMBOLS:
                if not any(r['symbol'] == sym for r in records):
                    records.append({
                        'symbol': sym,
                        'name': sym,
                        'market': 'HK',
                        'exchange': 'HKEX',
                        'industry': '',
                        'listed_date': None,
                        'is_active': 1,
                    })

        result_df = pd.DataFrame(records)
        self.db.upsert_stocks(result_df)
        logger.info(f"港股列表初始化完成: {len(records)} 只")
        return len(records)

    def collect_hk_daily_prices(self, date: str = None) -> int:
        """采集港股日线数据（通过 yfinance）"""

        if yf is None:
            raise ImportError("yfinance 未安装")

        date = date or datetime.now().strftime('%Y-%m-%d')
        logger.info(f"正在采集港股日线: {date}")

        records = []
        for sym in HK_STARTER_SYMBOLS:
            yf_sym = f"{sym.lstrip('0')}.HK"
            try:
                ticker = yf.Ticker(yf_sym)
                hist = ticker.history(period="5d")
                if hist.empty:
                    continue

                latest = hist.iloc[-1]
                hist_date = hist.index[-1].strftime('%Y-%m-%d')

                records.append({
                    'date': hist_date,
                    'symbol': sym,
                    'open': round(float(latest['Open']), 4),
                    'high': round(float(latest['High']), 4),
                    'low': round(float(latest['Low']), 4),
                    'close': round(float(latest['Close']), 4),
                    'volume': int(latest['Volume']),
                    'amount': None,
                    'turnover': None,
                    'change_pct': None,
                })
                time.sleep(0.2)
            except Exception as e:
                logger.warning(f"采集港股 {sym} 失败: {e}")
                continue

        if records:
            result_df = pd.DataFrame(records)
            self.db.insert_daily_prices(result_df)
        logger.info(f"港股日线采集完成: {len(records)} 条")
        return len(records)

    # ============================================================
    # 历史 K 线批量采集
    # ============================================================

    def collect_a_historical_kline(self, symbol: str = None, days: int = 250) -> int:
        """采集 A 股历史日线 K 线（逐只拉取完整历史，用于回补数据）

        参数:
            symbol: 指定股票代码，不传则采集全部 A 股
            days: 每只股票拉取的历史天数
        """
        import baostock as bs
        from datetime import timedelta

        bs.login()
        try:
            stocks = self.db.get_stocks(market='A', active_only=True)
            if stocks.empty:
                self.collect_a_stock_list()
                stocks = self.db.get_stocks(market='A', active_only=True)

            if symbol:
                stocks = stocks[stocks['symbol'] == symbol]
                if stocks.empty:
                    logger.warning(f"未找到股票: {symbol}")
                    return 0

            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            all_records = []

            for i, (_, stock) in enumerate(stocks.iterrows()):
                sym = stock['symbol']
                try:
                    bs_sym = sym.replace('sh', 'sh.').replace('sz', 'sz.').replace('bj', 'bj.')
                    rs = bs.query_history_k_data_plus(
                        bs_sym,
                        'date,open,high,low,close,volume,amount,turn,pctChg',
                        start_date=start_date, end_date=end_date, frequency='d'
                    )
                    while (rs.error_code == '0') & rs.next():
                        row = rs.get_row_data()
                        all_records.append({
                            'date': row[0], 'symbol': sym,
                            'open': self._safe_float(row[1]),
                            'high': self._safe_float(row[2]),
                            'low': self._safe_float(row[3]),
                            'close': self._safe_float(row[4]),
                            'volume': self._safe_float(row[5]),
                            'amount': self._safe_float(row[6]),
                            'turnover': self._safe_float(row[7]),
                            'change_pct': self._safe_float(row[8]),
                        })
                except Exception as e:
                    logger.debug(f"历史K线 {sym} 失败: {e}")
                    continue

                if (i + 1) % 50 == 0:
                    logger.info(f"  历史K线进度: {i+1}/{len(stocks)}")

            if all_records:
                result_df = pd.DataFrame(all_records)
                self.db.insert_daily_prices(result_df)
                logger.info(f"A 股历史 K 线采集完成: {len(all_records)} 条, {stocks['symbol'].nunique()} 只股票")
            return len(all_records)
        finally:
            bs.logout()

    def collect_a_historical_valuation(self, symbol: str = None, days: int = 250) -> int:
        """采集 A 股历史估值数据（PE/PB TTM 序列）"""
        import baostock as bs
        from datetime import timedelta

        bs.login()
        try:
            stocks = self.db.get_stocks(market='A', active_only=True)
            if stocks.empty:
                return 0

            if symbol:
                stocks = stocks[stocks['symbol'] == symbol]
                if stocks.empty:
                    return 0

            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            all_records = []

            for i, (_, stock) in enumerate(stocks.iterrows()):
                sym = stock['symbol']
                try:
                    bs_sym = sym.replace('sh', 'sh.').replace('sz', 'sz.').replace('bj', 'bj.')
                    rs = bs.query_history_k_data_plus(
                        bs_sym,
                        'date,close,peTTM,pbMRQ',
                        start_date=start_date, end_date=end_date, frequency='d'
                    )
                    while (rs.error_code == '0') & rs.next():
                        row = rs.get_row_data()
                        pe_val = self._safe_float(row[2])
                        pb_val = self._safe_float(row[3])
                        if pe_val or pb_val:
                            all_records.append({
                                'date': row[0], 'symbol': sym,
                                'pe': pe_val, 'pe_ttm': pe_val,
                                'pb': pb_val,
                                'ps': None, 'dividend_yield': None,
                                'total_mv': None, 'circ_mv': None,
                            })
                except Exception:
                    continue

                if (i + 1) % 50 == 0:
                    logger.info(f"  历史估值进度: {i+1}/{len(stocks)}")

            if all_records:
                result_df = pd.DataFrame(all_records)
                self.db.insert_daily_valuation(result_df)
                logger.info(f"A 股历史估值采集完成: {len(all_records)} 条")
            return len(all_records)
        finally:
            bs.logout()

    def collect_a_financials_deep(self, symbol: str = None) -> int:
        """采集 A 股多年财报数据（最近 8 个季度，跨 2 年）

        解决原 collect_a_financials 只取单一报告期的问题
        """
        return self._collect_a_financials_quarters()

    def _collect_a_financials_quarters(self) -> int:
        """使用 akshare 采集多个报告期的财务数据"""
        if ak is None:
            return 0

        def pick(row, *names):
            """akshare 各版本返回的列名不一致，按候选列名依次取值"""
            for n in names:
                v = row.get(n)
                if v is not None and not (isinstance(v, float) and pd.isna(v)):
                    return v
            return None

        all_records = []
        current_year = datetime.now().year

        for year in [current_year, current_year - 1]:
            for suffix in ['0331', '0630', '0930', '1231']:
                report_date_str = f"{year}{suffix}"
                report_date = f"{year}-{suffix[:2]}-{suffix[2:]}"
                try:
                    df = ak.stock_yjbb_em(date=report_date_str)
                    if df is None or df.empty:
                        continue

                    for _, row in df.iterrows():
                        code = str(pick(row, '股票代码', '代码') or '')
                        if not code or code in ('nan', 'None'):
                            continue
                        symbol = self._a_code_to_symbol(code)
                        all_records.append({
                            'symbol': symbol,
                            'name': str(pick(row, '股票简称', '名称') or ''),
                            'report_date': str(pick(row, '报告期') or report_date),
                            'eps': self._safe_float(pick(row, '每股收益', '基本每股收益')),
                            'roe': self._safe_float(pick(row, '净资产收益率')),
                            'revenue': self._safe_float(pick(row, '营业总收入-营业总收入', '营业总收入')),
                            'revenue_yoy': self._safe_float(pick(row, '营业总收入-同比增长', '营业收入同比增长')),
                            'net_profit': self._safe_float(pick(row, '净利润-净利润', '净利润')),
                            'net_profit_yoy': self._safe_float(pick(row, '净利润-同比增长', '净利润同比增长')),
                            'debt_ratio': self._safe_float(pick(row, '资产负债率')),
                            'free_cash_flow': None,
                            'gross_margin': self._safe_float(pick(row, '销售毛利率')),
                        })
                    logger.info(f"  财务 {report_date_str}: {len(df)} 条")
                    time.sleep(0.5)
                except Exception as e:
                    logger.debug(f"  财务 {report_date_str} 失败: {e}")
                    continue

        if all_records:
            result_df = pd.DataFrame(all_records)
            # 去重（同一 symbol + report_date）
            result_df = result_df.drop_duplicates(subset=['symbol', 'report_date'], keep='last')

            # financials.symbol 对 stocks.symbol 有外键约束（db 里开了 PRAGMA foreign_keys=ON），
            # 而股票清单来自 baostock（不含北交所），业绩报表却覆盖北交所，
            # 不补齐会让整批财务数据因外键失败而全部丢弃。
            try:
                known = set(self.db.get_stocks(active_only=False)['symbol'])
                new_stocks = (result_df.loc[~result_df['symbol'].isin(known), ['symbol', 'name']]
                              .drop_duplicates(subset='symbol')
                              .copy())
                if not new_stocks.empty:
                    new_stocks['market'] = 'A'
                    new_stocks['exchange'] = new_stocks['symbol'].map(
                        lambda s: 'BSE' if s.startswith('bj')
                        else ('SSE' if s.startswith('sh') else 'SZSE'))
                    self.db.upsert_stocks(new_stocks)
                    logger.info(f"  补齐股票清单: 新增 {len(new_stocks)} 只（北交所等）")
            except Exception as e:
                logger.warning(f"  补齐股票清单失败，财务数据仍按已有清单写入: {e}")

            self.db.insert_financials(result_df)
            logger.info(f"多季度财务数据采集完成: {len(result_df)} 条")
        return len(all_records)

    # ============================================================
    # 一键全采
    # ============================================================

    def collect_all(self):
        """一键采集所有市场的所有数据"""
        logger.info("===== 开始全量数据采集 =====")

        tasks = [
            ("A股-股票列表", self.collect_a_stock_list),
            ("A股-日线行情", self.collect_a_daily_prices),
            ("A股-历史K线", self.collect_a_historical_kline),
            ("A股-估值数据", self.collect_a_valuation),
            ("A股-历史估值", self.collect_a_historical_valuation),
            ("A股-北向资金", self.collect_a_fund_flow),
            ("A股-市场情绪", self.collect_a_market_breadth),
            ("A股-财务数据", self.collect_a_financials),
            ("A股-深度财务", self._collect_a_financials_quarters),
            ("美股-股票列表", self.collect_us_stock_list),
            ("美股-日线行情", self.collect_us_daily_prices),
            ("美股-VIX", self.collect_vix),
            ("港股-股票列表", self.collect_hk_stock_list),
            ("港股-日线行情", self.collect_hk_daily_prices),
        ]

        total = 0
        for name, func in tasks:
            try:
                n = self._log_task(name, func)
                total += n or 0
                logger.info(f"  ✓ {name}: {n} 条")
            except Exception as e:
                logger.error(f"  ✗ {name}: {e}")

        logger.info(f"===== 全量采集完成，共 {total} 条记录 =====")
        return total

    # ============================================================
    # 辅助方法
    # ============================================================

    @staticmethod
    def _a_code_to_symbol(code: str) -> str:
        code = str(code)
        if code.startswith('6') or code.startswith('9'):
            return f"sh{code}"
        elif code.startswith('0') or code.startswith('3') or code.startswith('1'):
            return f"sz{code}"
        elif code.startswith('8') or code.startswith('4'):
            return f"bj{code}"
        return f"sh{code}"

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        try:
            if val is None or val == '' or val == '-':
                return None
            return float(val)
        except (ValueError, TypeError):
            return None
