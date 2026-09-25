"""
技术指标计算测试
验证指标计算逻辑正确性。

注意：TechnicalAnalyzer 的指标方法是静态方法，直接吃 Series
（如 TechnicalAnalyzer.sma(close, 20)），返回 Series / DataFrame；
只有 calc_all() 吃 OHLCV DataFrame。早期版本曾用 calc_sma(df, period) 这类
接口，本文件已按现接口重写。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np

from analytics.technical import TechnicalAnalyzer


# ===== 测试数据 =====

def make_ohlcv(length=250, seed=42) -> pd.DataFrame:
    """生成模拟 K 线数据"""
    np.random.seed(seed)
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


def make_uptrend(length=200, seed=99) -> pd.DataFrame:
    """单边上升趋势数据"""
    np.random.seed(seed)
    dates = pd.date_range('2025-01-01', periods=length, freq='B')
    close = 100 + np.linspace(0, 50, length) + np.random.randn(length) * 0.5
    return pd.DataFrame({
        'date': dates.strftime('%Y-%m-%d'),
        'open': close - 0.3, 'high': close + 1,
        'low': close - 1, 'close': close,
        'volume': np.random.randint(1000000, 10000000, length),
    })


def make_flat(length=100) -> pd.DataFrame:
    """完全横盘数据"""
    return pd.DataFrame({
        'date': pd.date_range('2025-01-01', periods=length, freq='B').strftime('%Y-%m-%d'),
        'open': [100] * length, 'high': [100.1] * length,
        'low': [99.9] * length, 'close': [100] * length,
        'volume': [1000000] * length,
    })


# ===== 指标计算测试 =====

class TestTechnicalIndicators:
    """核心指标计算正确性"""

    def test_sma_matches_manual_mean(self):
        """SMA：第 N 个值应等于前 N 个收盘价的算术平均"""
        df = make_ohlcv(100)
        sma20 = TechnicalAnalyzer.sma(df['close'], 20)
        assert sma20.iloc[:19].isna().all(), "前 19 个应为 NaN"
        manual = df['close'].iloc[:20].mean()
        assert abs(sma20.iloc[19] - manual) < 1e-9

    def test_ema_reacts_faster_than_sma(self):
        """EMA 对近期价格更敏感：上升趋势中 EMA 应高于同期 SMA"""
        df = make_uptrend(150)
        ema20 = TechnicalAnalyzer.ema(df['close'], 20)
        sma20 = TechnicalAnalyzer.sma(df['close'], 20)
        # 趋势向上时，指数加权会更快跟上价格，末值应高于简单平均
        assert ema20.iloc[-1] > sma20.iloc[-1]

    def test_macd_histogram_is_double_dif_minus_dea(self):
        """MACD 柱 = 2 × (DIF - DEA)

        这是 A 股软件的通行画法（通达信/同花顺的 MACD 柱是 DIF-DEA 的两倍），
        与 TradingView 等欧美软件的 MACD 柱 = DIF - DEA 不同。
        本项目面向 A 股，采用国内口径。
        """
        df = make_ohlcv(250)
        macd = TechnicalAnalyzer.macd(df['close'])
        assert list(macd.columns) == ['DIF', 'DEA', 'MACD']
        expected = 2 * (macd['DIF'] - macd['DEA'])
        assert (abs(expected - macd['MACD']) < 1e-9).all()
        # DIF 与 DEA 都应与收盘价等长、无缺失
        assert len(macd) == len(df)
        assert macd['DIF'].notna().all() and macd['DEA'].notna().all()

    def test_rsi_bounds(self):
        """RSI 值域必须在 0-100"""
        df = make_ohlcv(250)
        rsi = TechnicalAnalyzer.rsi(df['close'], 14).dropna()
        assert len(rsi) > 0
        assert rsi.min() >= 0
        assert rsi.max() <= 100

    def test_bollinger_bands_ordering(self):
        """布林带结构：上轨 >= 中轨 >= 下轨，中轨等于 SMA"""
        df = make_ohlcv(200)
        bb = TechnicalAnalyzer.bollinger_bands(df['close'], 20)
        for col in ['BB_UPPER', 'BB_MIDDLE', 'BB_LOWER']:
            assert col in bb.columns
        valid = bb[['BB_UPPER', 'BB_MIDDLE', 'BB_LOWER']].dropna()
        assert len(valid) > 0
        assert (valid['BB_UPPER'] >= valid['BB_MIDDLE']).all()
        assert (valid['BB_MIDDLE'] >= valid['BB_LOWER']).all()
        # 中轨即 20 日均线
        sma20 = TechnicalAnalyzer.sma(df['close'], 20).dropna()
        assert (abs(valid['BB_MIDDLE'] - sma20.loc[valid.index]) < 1e-9).all()

    def test_kdj_bounds(self):
        """KDJ 的 K/D 在 0-100；J 可越界（这是 KDJ 的定义）"""
        df = make_ohlcv(200)
        kdj = TechnicalAnalyzer.kdj(df['high'], df['low'], df['close']).dropna()
        assert list(kdj.columns) == ['K', 'D', 'J']
        assert kdj['K'].min() >= 0 and kdj['K'].max() <= 100
        assert kdj['D'].min() >= 0 and kdj['D'].max() <= 100

    def test_atr_positive(self):
        """ATR 衡量波动幅度，恒为正数"""
        df = make_ohlcv(150)
        atr = TechnicalAnalyzer.atr(df['high'], df['low'], df['close'], 14).dropna()
        assert len(atr) > 0
        assert (atr > 0).all()


class TestCalcAll:
    """calc_all 一站式计算"""

    def test_expected_columns_present(self):
        """输出应包含全部核心指标列"""
        result = TechnicalAnalyzer.calc_all(make_ohlcv(250))
        expected = ['MA5', 'MA20', 'MA250', 'EMA20', 'MACD_DIF', 'MACD_DEA',
                    'MACD_MACD', 'RSI14', 'RSI28', 'KDJ_K', 'KDJ_D', 'KDJ_J',
                    'ATR14', 'BB_UPPER', 'BB_MIDDLE', 'BB_LOWER',
                    'OBV', 'ADX', 'CCI20', 'SQZ_ON', 'SQZ_MOM', 'WT1', 'WT2']
        missing = [c for c in expected if c not in result.columns]
        assert not missing, f"缺少指标列: {missing}"

    def test_no_duplicate_columns(self):
        """回归测试：squeeze_momentum 曾与 bollinger_bands 同时输出
        BB_UPPER/BB_LOWER，导致 calc_all 出现重复列名。重复列会让
        df['BB_UPPER'] 返回 DataFrame 而非 Series，使 detect_signals 里
        的 float(latest['BB_UPPER']) 抛 TypeError。"""
        result = TechnicalAnalyzer.calc_all(make_ohlcv(250))
        dupes = sorted({c for c in result.columns if list(result.columns).count(c) > 1})
        assert dupes == [], f"出现重复列名: {dupes}"
        # 关键列必须是 Series，能直接 float()
        assert isinstance(result['BB_UPPER'], pd.Series)
        float(result.iloc[-1]['BB_UPPER'])

    def test_preserves_input_rows_and_ohlcv(self):
        """不应改动原始 OHLCV 数据"""
        df = make_ohlcv(250)
        result = TechnicalAnalyzer.calc_all(df.copy())
        assert len(result) == len(df)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            assert (result[col] == df[col]).all()


class TestSignalDetection:
    """信号检测"""

    def test_signal_schema(self):
        """信号结构：date / type / strength / desc"""
        df = TechnicalAnalyzer.calc_all(make_uptrend(250))
        signals = TechnicalAnalyzer.detect_signals(df)
        assert isinstance(signals, list)
        for s in signals:
            assert set(s.keys()) == {'date', 'type', 'strength', 'desc'}
            assert isinstance(s['type'], str) and s['type']
            assert isinstance(s['desc'], str) and s['desc']

    def test_flat_market_few_signals(self):
        """横盘市场不应产生大量信号"""
        result = TechnicalAnalyzer.calc_all(make_flat(100))
        signals = TechnicalAnalyzer.detect_signals(result)
        assert len(signals) < 5, f"横盘市场不应产生大量信号: {len(signals)} 个"

    def test_uptrend_produces_bullish_signals(self):
        """单边上升趋势应产生看多类信号"""
        BULLISH = {'golden_cross', 'macd_golden', 'macd_zero', 'bullish_alignment',
                   'squeeze_fire_long', 'wt_golden', 'elder_green', 'bb_breakout'}
        df = TechnicalAnalyzer.calc_all(make_uptrend(250))
        signals = TechnicalAnalyzer.detect_signals(df)
        bullish = [s for s in signals if s['type'] in BULLISH]
        assert len(bullish) > 0, (
            f"上升趋势应产生看多信号，实际得到: {[s['type'] for s in signals]}")

    def test_short_series_returns_empty(self):
        """数据不足 60 根时不产生信号（避免指标未收敛就报信号）"""
        df = TechnicalAnalyzer.calc_all(make_ohlcv(40))
        assert TechnicalAnalyzer.detect_signals(df) == []


# ===== 筛选器测试 =====

class TestScreenerLogic:
    """筛选条件组合逻辑"""

    def test_condition_combination(self):
        """多条件取交集"""
        mock = pd.DataFrame({
            'symbol': ['A', 'B', 'C', 'D', 'E'],
            'pe': [10, 50, 25, 15, 100],
            'pb': [1.5, 5.0, 2.0, 3.0, 8.0],
            'roe': [15, 8, 20, 12, 5],
            'revenue_yoy': [20, 5, 30, 15, -5],
        })
        filtered = mock[(mock['pe'] < 30) & (mock['pb'] < 4) & (mock['roe'] > 10)]
        assert set(filtered['symbol']) == {'A', 'C', 'D'}


@pytest.fixture(scope="module")
def screener():
    from data_engine.db import Database
    from analytics.screener import StockScreener
    return StockScreener(Database())


@pytest.fixture(scope="module")
def has_financials():
    """演示库里有没有财务数据；没有就跳过，避免在空库上误报失败"""
    try:
        import sqlite3
        from data_engine.db import DB_PATH
        conn = sqlite3.connect(str(DB_PATH))
        n = conn.execute('SELECT COUNT(*) FROM financials').fetchone()[0]
        conn.close()
    except Exception:
        n = 0
    if n == 0:
        pytest.skip("演示库 financials 为空，跳过（先跑一次采集即可）")
    return True


class TestScreenerDatabase:
    """对自带演示库的集成测试：验证财务条件真的在过滤。

    仓库自带 data/market_data.db，克隆后即可运行。
    """

    def test_financial_filter_narrows_result(self, screener, has_financials):
        """加了 ROE 条件后结果应变少，且是原结果的子集"""
        base = screener.screen(market='A', limit=100000)
        filtered = screener.screen(market='A', roe_min=15, limit=100000)
        if base.empty:
            pytest.skip("演示库估值数据为空")
        assert len(filtered) < len(base), "ROE 条件没有收窄结果，财务筛选可能失效"
        assert set(filtered['symbol']) <= set(base['symbol']), "筛选结果不是原结果的子集"

    def test_three_conditions_equal_intersection(self, screener, has_financials):
        """三条件叠加的结果 == 三个单独筛选结果的交集"""
        roe = screener.screen(market='A', roe_min=15, limit=100000)
        rev = screener.screen(market='A', revenue_growth_min=30, limit=100000)
        npf = screener.screen(market='A', net_profit_growth_min=50, limit=100000)
        tri = screener.screen(market='A', roe_min=15, revenue_growth_min=30,
                              net_profit_growth_min=50, limit=100000)
        inter = set(roe['symbol']) & set(rev['symbol']) & set(npf['symbol'])
        assert set(tri['symbol']) == inter


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
