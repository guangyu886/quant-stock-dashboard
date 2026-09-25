"""
市场情绪分析模块
北向资金、涨跌比、VIX、成交额趋势
"""
import pandas as pd
import numpy as np
from typing import Optional


class SentimentAnalyzer:
    """市场情绪分析器"""

    def __init__(self, db=None):
        if db is None:
            from data_engine.db import Database
            db = Database()
        self.db = db

    def get_north_flow_trend(self, days: int = 30) -> pd.DataFrame:
        """北向资金流向趋势"""
        df = self.db.get_fund_flow(days=days)
        if df.empty:
            return pd.DataFrame()
        df = df.sort_values('date')
        df['cumulative'] = df['net_flow'].cumsum()
        return df

    def get_market_breadth_trend(self, market: str = 'A', days: int = 30) -> pd.DataFrame:
        """市场涨跌统计趋势"""
        df = self.db.get_market_breadth(market=market, days=days)
        if df.empty:
            return pd.DataFrame()
        df = df.sort_values('date')
        total = df['up_count'] + df['down_count'] + df['flat_count']
        df['up_ratio'] = df['up_count'] / total
        df['down_ratio'] = df['down_count'] / total
        return df

    def get_vix_trend(self, days: int = 30) -> pd.DataFrame:
        """VIX 恐慌指数趋势"""
        df = self.db.get_vix(days=days)
        if df.empty:
            return pd.DataFrame()
        return df.sort_values('date')

    def get_market_sentiment_summary(self) -> dict:
        """
        市场情绪综合评估
        返回评分: 0(极度恐慌) ~ 100(极度贪婪)
        """
        score = 50  # 中性起步

        # 1. 北向资金信号 (权重 25%)
        flow = self.db.get_fund_flow(days=5)
        if not flow.empty:
            recent_flow = flow['net_flow'].sum()
            if recent_flow > 100:
                score += 15
            elif recent_flow > 50:
                score += 8
            elif recent_flow < -100:
                score -= 15
            elif recent_flow < -50:
                score -= 8

        # 2. 涨跌比信号 (权重 25%)
        breadth = self.db.get_market_breadth(market='A', days=5)
        if not breadth.empty:
            avg_up_ratio = ((breadth['up_count'] / (breadth['up_count'] + breadth['down_count'] + 1)) * 100).mean()
            if avg_up_ratio > 60:
                score += 12
            elif avg_up_ratio > 50:
                score += 5
            elif avg_up_ratio < 30:
                score -= 12
            elif avg_up_ratio < 40:
                score -= 5

        # 3. VIX 信号 (权重 25%)
        vix = self.db.get_vix(days=5)
        if not vix.empty:
            recent_vix = float(vix['close'].iloc[-1])
            if recent_vix > 30:
                score -= 15
            elif recent_vix > 25:
                score -= 8
            elif recent_vix < 15:
                score += 10
            elif recent_vix < 20:
                score += 3

        # 4. 成交额信号 (权重 25%)
        if not breadth.empty:
            avg_volume = breadth['total_volume'].mean()
            recent_volume = float(breadth['total_volume'].iloc[-1]) if len(breadth) > 0 else 0
            if recent_volume > avg_volume * 1.5:
                score += 8
            elif recent_volume < avg_volume * 0.5:
                score -= 8

        score = max(0, min(100, score))

        # 解读
        if score >= 75:
            level = '贪婪'
        elif score >= 60:
            level = '偏乐观'
        elif score >= 40:
            level = '中性'
        elif score >= 25:
            level = '偏悲观'
        else:
            level = '恐慌'

        return {
            'score': round(score, 1),
            'level': level,
            'components': {
                'north_flow': '偏多' if score > 55 else ('偏空' if score < 45 else '中性'),
                'breadth': '偏多' if score > 55 else ('偏空' if score < 45 else '中性'),
                'vix': '偏低' if score > 55 else ('偏高' if score < 45 else '中性'),
            }
        }
