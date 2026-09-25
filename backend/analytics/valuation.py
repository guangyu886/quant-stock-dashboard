"""
估值分析模块
PE/PB/PS 分位数、全市场排名、估值水位
"""
import pandas as pd
import numpy as np
from typing import Optional


class ValuationAnalyzer:
    """估值分析器"""

    def __init__(self, db=None):
        if db is None:
            from data_engine.db import Database
            db = Database()
        self.db = db

    def get_valuation_rank(self, market: str = 'A', metric: str = 'pe', limit: int = 50) -> pd.DataFrame:
        """按估值指标全市场排名（从低到高）"""
        df = self.db.get_latest_valuation(market=market, limit=limit)
        valid_col = metric if metric in df.columns else 'pe'
        return df[df[valid_col] > 0].sort_values(valid_col).head(limit)

    def get_valuation_distribution(self, market: str = 'A') -> dict:
        """全市场估值分布统计"""
        df = self.db.get_latest_valuation(market=market, limit=10000)
        pe = df[df['pe'] > 0]['pe']
        pb = df[df['pb'] > 0]['pb']

        def _bins(series: pd.Series) -> dict:
            if series.empty:
                return {}
            return {
                'min': round(float(series.min()), 2),
                'p25': round(float(series.quantile(0.25)), 2),
                'median': round(float(series.median()), 2),
                'p75': round(float(series.quantile(0.75)), 2),
                'max': round(float(series.max()), 2),
                'mean': round(float(series.mean()), 2),
                'count': int(len(series)),
            }

        return {
            'pe': _bins(pe),
            'pb': _bins(pb),
            'total_stocks': len(df),
        }

    @staticmethod
    def calc_pe_percentile(current_pe: float, pe_history: pd.Series) -> float:
        """计算当前 PE 在历史中的分位数"""
        if pe_history.empty or current_pe is None:
            return 0.5
        return round(float((pe_history < current_pe).sum() / len(pe_history)), 4)

    @staticmethod
    def valuation_level(pe: float, industry_avg: float = None) -> str:
        """
        判断估值水位
        < 10: 低估, 10-20: 合理, 20-30: 偏高, > 30: 高估
        """
        if pe <= 0:
            return '亏损'
        if pe < 10:
            return '低估'
        if pe < 20:
            return '合理'
        if pe < 30:
            return '偏高'
        return '高估'

    def get_stock_valuation_detail(self, symbol: str) -> dict:
        """获取单只股票的估值详情"""
        prices = self.db.get_daily_prices(symbol)
        valuations = self.db.get_latest_valuation(limit=10000)
        stock_val = valuations[valuations['symbol'] == symbol]

        result = {
            'symbol': symbol,
            'pe': None, 'pb': None, 'ps': None,
            'pe_percentile': None,
            'level': 'N/A',
        }

        if not stock_val.empty:
            latest = stock_val.iloc[-1]
            result['pe'] = latest.get('pe')
            result['pb'] = latest.get('pb')
            result['ps'] = latest.get('ps')
            result['level'] = self.valuation_level(latest.get('pe'))

        if not prices.empty and result['pe']:
            # 用价格序列近似 PE 历史分位（若有真实 PE 历史数据则更精确）
            # 这里用价格分位作为近似
            latest_close = float(prices['close'].iloc[-1])
            percentile = (prices['close'] < latest_close).sum() / len(prices)
            result['pe_percentile'] = round(percentile, 4)

        return result
