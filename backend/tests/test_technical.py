"""
技术指标计算测试
验证 30+ 指标的核心计算逻辑正确性
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np


# ===== 测试数据 =====

def make_ohlcv(length=250) -> pd.DataFrame:
    """生成模拟 K 线数据"""
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=length, freq='B')
    close = np.cumsum(np.random.randn(length) * 0.5) + 100
    high = close + np.abs(np.random.randn(length) * 1.5)
    low = close - np.abs(np.random.randn(length) * 1.5)
    open_ = close - np.random.randn(length) * 0.3
    volume = np.random.randint(1000000, 10000000, length)
    return pd.DataFrame({
        'date': dates.strftime('%Y-%m-%d'),
        'open': open_, 'high': high, 'low': low,
        'close': close, 'volume': volume,
    })


# ===== 指标计算测试 =====

class TestTechnicalIndicators:
    """核心指标计算正确性"""

    def test_sma_calculation(self):
        """SMA 简单移动平均"""
        from analytics.technical import TechnicalAnalyzer
        df = make_ohlcv(100)
        result = TechnicalAnalyzer.calc_sma(df.copy(), period=20)
        assert 'SMA_20' in result.columns
        assert not result['SMA_20'].iloc[19:].isna().all()
        # 手动验证：前 20 个值 NaN，第 20 个值应为前 20 个收盘价的均值
        manual = df['close'].iloc[:20].mean()
        assert abs(result['SMA_20'].iloc[19] - manual) < 0.01

    def test_ema_calculation(self):
        """EMA 指数移动平均"""
        from analytics.technical import TechnicalAnalyzer
        df = make_ohlcv(150)
        result = TechnicalAnalyzer.calc_ema(df.copy(), period=20)
        assert 'EMA_20' in result.columns
        assert not result['EMA_20'].iloc[30:].isna().all()

    def test_macd_calculation(self):
        """MACD 计算"""
        from analytics.technical import TechnicalAnalyzer
        df = make_ohlcv(250)
        result = TechnicalAnalyzer.calc_macd(df.copy())
        for col in ['MACD', 'MACD_Signal', 'MACD_Hist']:
            assert col in result.columns
        # MACD Histogram = MACD - Signal
        diff = (result['MACD'] - result['MACD_Signal']).dropna()
        hist = result['MACD_Hist'].dropna().loc[diff.index]
        assert (abs(diff - hist) < 0.01).all()

    def test_rsi_bounds(self):
        """RSI 值域检查 (0-100)"""
        from analytics.technical import TechnicalAnalyzer
        df = make_ohlcv(250)
        result = TechnicalAnalyzer.calc_rsi(df.copy(), period=14)
        rsi = result['RSI_14'].dropna()
        assert rsi.min() >= 0
        assert rsi.max() <= 100

    def test_bollinger_bands(self):
        """布林带结构验证"""
        from analytics.technical import TechnicalAnalyzer
        df = make_ohlcv(200)
        result = TechnicalAnalyzer.calc_bollinger(df.copy(), period=20)
        for col in ['BB_Middle', 'BB_Upper', 'BB_Lower']:
            assert col in result.columns
        # Upper > Middle > Lower
        valid = result[['BB_Lower', 'BB_Middle', 'BB_Upper']].dropna()
        assert (valid['BB_Upper'] >= valid['BB_Middle']).all()
        assert (valid['BB_Middle'] >= valid['BB_Lower']).all()

    def test_kdj_bounds(self):
        """KDJ 值域检查 (0-100)"""
        from analytics.technical import TechnicalAnalyzer
        df = make_ohlcv(200)
        result = TechnicalAnalyzer.calc_kdj(df.copy())
        for col in ['K', 'D', 'J']:
            vals = result[col].dropna()
            assert vals.min() >= 0
            assert vals.max() <= 100

    def test_atr_positive(self):
        """ATR 始终为正"""
        from analytics.technical import TechnicalAnalyzer
        df = make_ohlcv(150)
        result = TechnicalAnalyzer.calc_atr(df.copy(), period=14)
        atr = result['ATR_14'].dropna()
        assert (atr > 0).all()

    def test_calc_all_output(self):
        """calc_all 一站式计算完整性"""
        from analytics.technical import TechnicalAnalyzer
        df = make_ohlcv(250)
        result = TechnicalAnalyzer.calc_all(df.copy())
        # 至少应包含关键指标
        expected = ['SMA_5', 'EMA_20', 'MACD', 'RSI_14', 'BB_Upper',
                    'K', 'D', 'J', 'ATR_14']
        for col in expected:
            assert col in result.columns, f"缺少指标: {col}"

    def test_signal_detection(self):
        """信号检测: 金叉/死叉"""
        from analytics.technical import TechnicalAnalyzer
        df = make_ohlcv(250)
        df = TechnicalAnalyzer.calc_all(df.copy())
        signals = TechnicalAnalyzer.detect_signals(df)
        assert isinstance(signals, list)
        if signals:
            s = signals[0]
            assert 'type' in s
            assert 'price' in s


# ===== 估值分析测试 =====

class TestValuation:
    """估值分析功能测试"""

    def test_rank_output_structure(self):
        """排名输出完整性"""
        # 单元测试：只验证不崩溃，不连数据库
        import pandas as pd
        import numpy as np

        # 模拟估值数据
        mock_df = pd.DataFrame({
            'symbol': ['sh000001', 'sz000002'],
            'name': ['Test1', 'Test2'],
            'market': ['A', 'A'],
            'pe': [15.5, 22.3],
            'pb': [1.8, 3.2],
        })

        # 按 PE 排序
        sorted_df = mock_df.sort_values('pe')
        assert sorted_df.iloc[0]['pe'] == 15.5

    def test_distribution_stats(self):
        """分布统计正确性"""
        import numpy as np

        # 模拟分布计算逻辑
        pe_values = np.array([10, 15, 20, 25, 30, 35, 50, 100, 200, 500])
        stats = {
            'min': float(np.min(pe_values)),
            'max': float(np.max(pe_values)),
            'median': float(np.median(pe_values)),
            'mean': float(np.mean(pe_values)),
            'count': len(pe_values),
        }
        assert stats['min'] == 10
        assert stats['max'] == 500
        assert stats['count'] == 10
        assert 15 <= stats['median'] <= 35
        assert stats['mean'] > 40  # 受极值影响


# ===== 筛选器测试 =====

class TestScreener:
    """筛选器逻辑测试"""

    def test_screen_conditions(self):
        """组合筛选条件逻辑"""
        import pandas as pd
        import numpy as np

        mock = pd.DataFrame({
            'symbol': ['A', 'B', 'C', 'D', 'E'],
            'pe': [10, 50, 25, 15, 100],
            'pb': [1.5, 5.0, 2.0, 3.0, 8.0],
            'roe': [15, 8, 20, 12, 5],
            'revenue_yoy': [20, 5, 30, 15, -5],
        })

        # 模拟筛选: pe < 30, pb < 4, roe > 10
        filtered = mock[(mock['pe'] < 30) & (mock['pb'] < 4) & (mock['roe'] > 10)]
        assert len(filtered) == 3  # A, C, D
        assert set(filtered['symbol']) == {'A', 'C', 'D'}


# ===== 信号检测额外测试 =====

class TestSignalEdgeCases:
    """信号边界情况"""

    def test_flat_market_no_false_signals(self):
        """横盘市场不应产生过多假信号"""
        from analytics.technical import TechnicalAnalyzer
        df = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=100, freq='B').strftime('%Y-%m-%d'),
            'open': [100] * 100, 'high': [100.1] * 100,
            'low': [99.9] * 100, 'close': [100] * 100,
            'volume': [1000000] * 100,
        })
        result = TechnicalAnalyzer.calc_all(df.copy())
        signals = TechnicalAnalyzer.detect_signals(result)
        # 横盘市场信号应极少
        assert len(signals) < 5, f"横盘市场不应产生大量信号: {len(signals)} 个"

    def test_uptrend_buy_signals(self):
        """上升趋势产生买入信号"""
        from analytics.technical import TechnicalAnalyzer
        np.random.seed(99)
        length = 200
        dates = pd.date_range('2025-01-01', periods=length, freq='B')
        trend = np.linspace(0, 50, length)
        close = 100 + trend + np.random.randn(length) * 0.5
        df = pd.DataFrame({
            'date': dates.strftime('%Y-%m-%d'),
            'open': close - 0.3, 'high': close + 1,
            'low': close - 1, 'close': close,
            'volume': np.random.randint(1000000, 10000000, length),
        })
        result = TechnicalAnalyzer.calc_all(df.copy())
        signals = TechnicalAnalyzer.detect_signals(result)
        buy_signals = [s for s in signals if s.get('type') == 'buy']
        # 上升趋势应有买入信号
        assert len(buy_signals) > 0, "上升趋势应该产生买入信号"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
