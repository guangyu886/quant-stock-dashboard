"""
基本面筛选模块
多条件组合筛选：PE/PB/ROE/增长率/市值/股息率
"""
import pandas as pd
from typing import Optional


class StockScreener:
    """股票筛选器"""

    def __init__(self, db=None):
        if db is None:
            from data_engine.db import Database
            db = Database()
        self.db = db

    def screen(self,
               market: str = 'A',
               pe_max: float = None,
               pb_max: float = None,
               roe_min: float = None,
               revenue_growth_min: float = None,
               net_profit_growth_min: float = None,
               dividend_yield_min: float = None,
               market_cap_min: float = None,
               market_cap_max: float = None,
               limit: int = 200) -> pd.DataFrame:
        """
        多条件基本面筛选

        参数:
            market: 'A' | 'HK' | 'US'
            pe_max: 市盈率上限
            pb_max: 市净率上限
            roe_min: ROE 下限(%)
            revenue_growth_min: 营收增长率下限(%)
            net_profit_growth_min: 净利润增长率下限(%)
            dividend_yield_min: 股息率下限(%)
            market_cap_min/max: 市值范围(亿)
            limit: 返回最大数量
        """
        # 获取最新估值数据
        valuation = self.db.get_latest_valuation(market=market, limit=10000)

        if valuation.empty:
            return pd.DataFrame()

        result = valuation.copy()

        # 应用筛选条件
        mask = pd.Series(True, index=result.index)

        if pe_max is not None:
            mask &= (result['pe'] > 0) & (result['pe'] <= pe_max)

        if pb_max is not None:
            mask &= (result['pb'] > 0) & (result['pb'] <= pb_max)

        if market_cap_min is not None:
            mask &= (result['total_mv'] >= market_cap_min)

        if market_cap_max is not None:
            mask &= (result['total_mv'] <= market_cap_max)

        if dividend_yield_min is not None:
            mask &= (result['dividend_yield'] >= dividend_yield_min)

        result = result[mask]

        # 财务指标筛选（需要 join financials 表）
        if any([roe_min, revenue_growth_min, net_profit_growth_min]):
            result = self._apply_financial_filters(
                result, roe_min, revenue_growth_min, net_profit_growth_min
            )

        # 排序：按 PE 从低到高
        if not result.empty and 'pe' in result.columns:
            result = result.sort_values('pe')

        return result.head(limit)

    def _apply_financial_filters(self, df: pd.DataFrame,
                                  roe_min: float = None,
                                  revenue_growth_min: float = None,
                                  net_profit_growth_min: float = None) -> pd.DataFrame:
        """应用财务指标筛选"""
        from data_engine.db import DB_PATH
        import sqlite3

        if df.empty:
            return df

        symbols = tuple(df['symbol'].tolist())
        placeholders = ','.join(['?'] * len(symbols))

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row

        query = f"""
            SELECT symbol, MAX(report_date) as latest_report,
                   eps, roe, revenue_yoy, net_profit_yoy
            FROM financials
            WHERE symbol IN ({placeholders})
            GROUP BY symbol
        """
        fin_df = pd.read_sql_query(query, conn, params=symbols)
        conn.close()

        if fin_df.empty:
            return df

        # Merge
        merged = df.merge(fin_df, on='symbol', how='left')

        if roe_min is not None:
            merged = merged[merged['roe'] >= roe_min]
        if revenue_growth_min is not None:
            merged = merged[merged['revenue_yoy'] >= revenue_growth_min]
        if net_profit_growth_min is not None:
            merged = merged[merged['net_profit_yoy'] >= net_profit_growth_min]

        return merged

    def get_watchlist_analysis(self) -> pd.DataFrame:
        """自选股全面分析（估值 + 技术信号）"""
        watchlist = self.db.get_watchlist()
        if watchlist.empty:
            return pd.DataFrame()

        valuation = self.db.get_latest_valuation(limit=10000)
        merged = watchlist.merge(valuation, on='symbol', how='left')

        columns = ['symbol', 'name', 'market', 'pe', 'pe_ttm', 'pb', 'total_mv',
                   'dividend_yield']
        available = [c for c in columns if c in merged.columns]
        return merged[available]
