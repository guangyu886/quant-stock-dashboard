"""
技术指标分析模块
纯 Pandas 实现，无需 pandas-ta（兼容 Python 3.14）
对标 TradingView 常用指标（30+）：

移动平均: SMA, EMA, WMA, HMA
趋势: MACD, ADX/DMI, CCI, SAR, SuperTrend, Ichimoku 一目均衡表
动量: RSI, Stochastic, Williams %R, ROC, Momentum, KDJ
波动: Bollinger Bands, Keltner Channels, Donchian Channels, ATR
成交量: OBV, VWAP, MFI, CMF
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, List


class TechnicalAnalyzer:
    """技术指标计算器"""

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """简单移动平均"""
        return series.rolling(window=period).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """指数移动平均"""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        MACD 指标
        返回: DataFrame with DIF, DEA, MACD (柱状图)
        """
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd_bar = 2 * (dif - dea)  # 柱状图
        return pd.DataFrame({'DIF': dif, 'DEA': dea, 'MACD': macd_bar}, index=close.index)

    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """相对强弱指标 RSI"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def bollinger_bands(close: pd.Series, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
        """
        布林带
        返回: DataFrame with upper, middle, lower, width, pct_b
        """
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        width = upper - lower
        pct_b = (close - lower) / (upper - lower)
        return pd.DataFrame({
            'BB_UPPER': upper, 'BB_MIDDLE': middle, 'BB_LOWER': lower,
            'BB_WIDTH': width, 'BB_PCTB': pct_b
        }, index=close.index)

    @staticmethod
    def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
            n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        """
        KDJ 随机指标
        返回: DataFrame with K, D, J
        """
        lowest_low = low.rolling(window=n).min()
        highest_high = high.rolling(window=n).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100

        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        j = 3 * k - 2 * d
        return pd.DataFrame({'K': k, 'D': d, 'J': j}, index=close.index)

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """平均真实波幅 ATR"""
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(alpha=1/period, adjust=False).mean()

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """能量潮 OBV"""
        direction = np.where(close.diff() > 0, 1, np.where(close.diff() < 0, -1, 0))
        return (volume * direction).cumsum()

    # ============================================================
    # 移动平均扩展
    # ============================================================

    @staticmethod
    def wma(series: pd.Series, period: int) -> pd.Series:
        """加权移动平均 WMA"""
        weights = np.arange(1, period + 1)
        return series.rolling(window=period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

    @staticmethod
    def hma(series: pd.Series, period: int) -> pd.Series:
        """Hull 移动平均 HMA - 超平滑"""
        half_period = int(period / 2)
        sqrt_period = int(np.sqrt(period))
        wma_half = series.rolling(window=half_period).apply(
            lambda x: np.dot(x, np.arange(1, half_period + 1)) / np.arange(1, half_period + 1).sum(), raw=True)
        wma_full = series.rolling(window=period).apply(
            lambda x: np.dot(x, np.arange(1, period + 1)) / np.arange(1, period + 1).sum(), raw=True)
        raw_hma = 2 * wma_half - wma_full
        return raw_hma.rolling(window=sqrt_period).apply(
            lambda x: np.dot(x, np.arange(1, sqrt_period + 1)) / np.arange(1, sqrt_period + 1).sum(), raw=True)

    # ============================================================
    # 趋势指标
    # ============================================================

    @staticmethod
    def sar(high: pd.Series, low: pd.Series, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
        """抛物线转向指标 Parabolic SAR"""
        n = len(high)
        sar = np.zeros(n)
        ep = np.zeros(n)
        af = np.zeros(n)
        trend = np.ones(n)  # 1=上升, -1=下降

        # 初始值
        trend[0] = 1
        sar[0] = low.iloc[0]
        ep[0] = high.iloc[0]
        af[0] = af_start

        for i in range(1, n):
            prev_sar = sar[i-1]
            prev_af = af[i-1]
            prev_ep = ep[i-1]
            prev_trend = trend[i-1]

            # 更新 SAR
            sar[i] = prev_sar + prev_af * (prev_ep - prev_sar)

            # 限制 SAR 不能超过前两根 K 线的价格
            high_i = high.iloc[i]; low_i = low.iloc[i]
            high_prev = high.iloc[i-1]; low_prev = low.iloc[i-1]

            if prev_trend == 1:
                sar[i] = min(sar[i], min(low_prev, low_i))
            else:
                sar[i] = max(sar[i], max(high_prev, high_i))

            # 判断趋势反转
            if (prev_trend == 1 and low_i <= sar[i]) or (prev_trend == -1 and high_i >= sar[i]):
                trend[i] = -prev_trend
                sar[i] = ep[i-1]  # 反转时 SAR 跳到极值点
                ep[i] = low_i if prev_trend == 1 else high_i
                af[i] = af_start
            else:
                trend[i] = prev_trend
                if prev_trend == 1 and high_i > prev_ep:
                    ep[i] = high_i
                    af[i] = min(prev_af + af_step, af_max)
                elif prev_trend == -1 and low_i < prev_ep:
                    ep[i] = low_i
                    af[i] = min(prev_af + af_step, af_max)
                else:
                    ep[i] = prev_ep
                    af[i] = prev_af

        return pd.Series(sar, index=high.index)

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.DataFrame:
        """平均趋向指数 ADX/DMI"""
        prev_close = close.shift(1)
        prev_high = high.shift(1)
        prev_low = low.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()

        up_move = high - prev_high
        down_move = prev_low - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        plus_di = 100 * pd.Series(plus_dm, index=high.index).ewm(alpha=1/period, adjust=False).mean() / atr
        minus_di = 100 * pd.Series(minus_dm, index=high.index).ewm(alpha=1/period, adjust=False).mean() / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(alpha=1/period, adjust=False).mean()

        return pd.DataFrame({'ADX': adx, '+DI': plus_di, '-DI': minus_di}, index=close.index)

    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """商品通道指数 CCI"""
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        return (tp - sma_tp) / (0.015 * mad)

    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
        """SuperTrend 超级趋势"""
        atr = TechnicalAnalyzer.atr(high, low, close, period)
        mid = (high + low) / 2

        upper = mid + multiplier * atr
        lower = mid - multiplier * atr

        n = len(close)
        trend = np.zeros(n)
        supertrend = np.zeros(n)
        trend[0] = 1
        supertrend[0] = lower.iloc[0]

        for i in range(1, n):
            prev_upper = upper.iloc[i-1]
            prev_lower = lower.iloc[i-1]
            prev_close = close.iloc[i-1]

            # 更新上下轨
            if upper.iloc[i] < prev_upper or prev_close > prev_upper:
                upper.iloc[i] = upper.iloc[i]
            else:
                upper.iloc[i] = min(upper.iloc[i], prev_upper)

            if lower.iloc[i] > prev_lower or prev_close < prev_lower:
                lower.iloc[i] = lower.iloc[i]
            else:
                lower.iloc[i] = max(lower.iloc[i], prev_lower)

            # 判断趋势
            curr_close = close.iloc[i]
            if trend[i-1] == 1:
                supertrend[i] = lower.iloc[i]
                trend[i] = -1 if curr_close < lower.iloc[i] else 1
            else:
                supertrend[i] = upper.iloc[i]
                trend[i] = 1 if curr_close > upper.iloc[i] else -1

        return pd.DataFrame({'SUPERT': supertrend, 'SUPERT_DIR': trend}, index=close.index)

    # ============================================================
    # 动量指标
    # ============================================================

    @staticmethod
    def stoch(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, k_smooth: int = 3, d_smooth: int = 3) -> pd.DataFrame:
        """随机指标 Stochastic %K, %D"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        fast_k = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-10)
        slow_k = fast_k.rolling(window=k_smooth).mean()
        slow_d = slow_k.rolling(window=d_smooth).mean()
        return pd.DataFrame({'STOCH_K': slow_k, 'STOCH_D': slow_d}, index=close.index)

    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """威廉指标 Williams %R"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        return -100 * (highest_high - close) / (highest_high - lowest_low + 1e-10)

    @staticmethod
    def roc(close: pd.Series, period: int = 12) -> pd.Series:
        """变动率 Rate of Change"""
        return ((close - close.shift(period)) / close.shift(period)) * 100

    @staticmethod
    def momentum(close: pd.Series, period: int = 10) -> pd.Series:
        """动量指标 Momentum"""
        return close - close.shift(period)

    # ============================================================
    # 波动性指标
    # ============================================================

    @staticmethod
    def keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series, ema_period: int = 20, atr_mult: float = 2.0, atr_period: int = 10) -> pd.DataFrame:
        """肯特纳通道 Keltner Channels"""
        middle = close.ewm(span=ema_period, adjust=False).mean()
        atr = TechnicalAnalyzer.atr(high, low, close, atr_period)
        upper = middle + atr_mult * atr
        lower = middle - atr_mult * atr
        return pd.DataFrame({'KC_UPPER': upper, 'KC_MIDDLE': middle, 'KC_LOWER': lower}, index=close.index)

    @staticmethod
    def donchian_channels(high: pd.Series, low: pd.Series, period: int = 20) -> pd.DataFrame:
        """唐奇安通道 Donchian Channels"""
        upper = high.rolling(window=period).max()
        lower = low.rolling(window=period).min()
        middle = (upper + lower) / 2
        return pd.DataFrame({'DC_UPPER': upper, 'DC_MIDDLE': middle, 'DC_LOWER': lower}, index=high.index)

    # ============================================================
    # 一目均衡表 (Ichimoku Cloud)
    # ============================================================
    @staticmethod
    def ichimoku(high: pd.Series, low: pd.Series, tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52) -> pd.DataFrame:
        """一目均衡表 Ichimoku Cloud"""
        # 转换线 Tenkan-sen
        tenkan_high = high.rolling(window=tenkan_period).max()
        tenkan_low = low.rolling(window=tenkan_period).min()
        tenkan = (tenkan_high + tenkan_low) / 2

        # 基准线 Kijun-sen
        kijun_high = high.rolling(window=kijun_period).max()
        kijun_low = low.rolling(window=kijun_period).min()
        kijun = (kijun_high + kijun_low) / 2

        # 先行带 A Senkou Span A
        senkou_a = ((tenkan + kijun) / 2).shift(kijun_period)

        # 先行带 B Senkou Span B
        senkou_high = high.rolling(window=senkou_b_period).max()
        senkou_low = low.rolling(window=senkou_b_period).min()
        senkou_b = ((senkou_high + senkou_low) / 2).shift(kijun_period)

        # 迟行线 Chikou Span
        chikou = close.shift(-kijun_period)

        return pd.DataFrame({
            'ICH_TENKAN': tenkan, 'ICH_KIJUN': kijun,
            'ICH_SENKOU_A': senkou_a, 'ICH_SENKOU_B': senkou_b,
            'ICH_CHIKOU': chikou
        }, index=high.index)

    # ============================================================
    # 成交量指标
    # ============================================================

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """成交量加权平均价 VWAP"""
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()

    @staticmethod
    def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
        """资金流量指标 Money Flow Index"""
        typical_price = (high + low + close) / 3
        raw_mf = typical_price * volume

        positive_flow = raw_mf.where(typical_price > typical_price.shift(1), 0)
        negative_flow = raw_mf.where(typical_price < typical_price.shift(1), 0)

        pos_mf = positive_flow.rolling(window=period).sum()
        neg_mf = negative_flow.rolling(window=period).sum()

        mfr = pos_mf / (neg_mf + 1e-10)
        return 100 - (100 / (1 + mfr))

    @staticmethod
    def cmf(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 21) -> pd.Series:
        """蔡金资金流量 Chaikin Money Flow"""
        # A/D Multiplier
        ad_mult = ((close - low) - (high - close)) / (high - low + 1e-10)
        mf_volume = ad_mult * volume
        return mf_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()

    # ============================================================
    # 🔥 TradingView 社区 Top 指标（LazyBear 经典）
    # ============================================================

    @staticmethod
    def squeeze_momentum(high: pd.Series, low: pd.Series, close: pd.Series,
                         bb_period: int = 20, bb_mult: float = 2.0,
                         kc_period: int = 20, kc_mult: float = 1.5) -> pd.DataFrame:
        """
        Squeeze Momentum (TTM Squeeze) - TradingView 全站 #1 热门指标
        作者: LazyBear / 源自 John Carter《Mastering the Trade》

        原理: 布林带收进肯特纳通道内 = 波动压缩 → 即将突破
        信号: 黑点=压缩中 / 浅点=释放中 / 绿色柱=多头动量 / 红色柱=空头动量
        """
        # 布林带
        bb_mid = close.rolling(window=bb_period).mean()
        bb_std = close.rolling(window=bb_period).std()
        bb_upper = bb_mid + bb_mult * bb_std
        bb_lower = bb_mid - bb_mult * bb_std

        # 肯特纳通道
        kc_mid = close.ewm(span=kc_period, adjust=False).mean()
        atr = TechnicalAnalyzer.atr(high, low, close, kc_period)
        kc_upper = kc_mid + kc_mult * atr
        kc_lower = kc_mid - kc_mult * atr

        # Squeeze 判断: BB 是否被 KC 包住
        squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
        squeeze_off = ~squeeze_on

        # 动量计算: 线性回归斜率
        def linear_reg(x):
            n = len(x)
            if n < 2:
                return np.nan
            t = np.arange(n)
            slope = (n * np.dot(t, x) - t.sum() * x.sum()) / (n * (t ** 2).sum() - t.sum() ** 2 + 1e-10)
            return slope

        momentum = close.rolling(window=20).apply(linear_reg, raw=True)

        return pd.DataFrame({
            'SQZ_ON': squeeze_on.astype(int),      # 1=压缩中, 0=释放
            'SQZ_MOM': momentum,                    # 动量值（正=多头，负=空头）
            'BB_UPPER': bb_upper, 'BB_LOWER': bb_lower,
            'KC_UPPER': kc_upper, 'KC_LOWER': kc_lower,
        }, index=close.index)

    @staticmethod
    def wavetrend(high: pd.Series, low: pd.Series, close: pd.Series,
                  n1: int = 10, n2: int = 21, n_smooth: int = 4) -> pd.DataFrame:
        """
        WaveTrend Oscillator - TradingView 全站 #2 热门指标
        作者: LazyBear

        比 RSI 更平滑的动量震荡器，低噪音+信号线交叉系统
        WT1 上穿/下穿 WT2 + 超买超卖区间
        """
        hlc3 = (high + low + close) / 3
        esa = hlc3.ewm(span=n1, adjust=False).mean()
        d = abs(hlc3 - esa).ewm(span=n1, adjust=False).mean()
        ci = (hlc3 - esa) / (0.015 * d)
        wt1 = ci.ewm(span=n2, adjust=False).mean()
        wt2 = wt1.rolling(window=n_smooth).mean()

        return pd.DataFrame({
            'WT1': wt1, 'WT2': wt2, 'WT_DIFF': wt1 - wt2
        }, index=close.index)

    @staticmethod
    def vfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
            period: int = 130, coef: float = 0.2, vcoef: float = 2.5,
            signal_period: int = 5) -> pd.DataFrame:
        """
        Volume Flow Indicator (VFI) - LazyBear
        检测资金是买入还是卖出主导

        VFI > 0 = 资金净流入（看涨）
        VFI < 0 = 资金净流出（看跌）
        """
        typical = (high + low + close) / 3
        prev_typical = typical.shift(1)

        # 价格变化率
        vinter = typical / prev_typical.apply(lambda x: x if x > 0 else np.nan) - 1
        vstop = (close - typical).abs().ewm(span=period).mean()
        vmax = vstop * vcoef * volume / volume.ewm(span=period).mean()
        vf = volume * np.where(vinter > coef * vstop, 1, np.where(vinter < -coef * vstop, -1, 0)) * vmax
        vfi_val = vf.ewm(span=period).mean()
        vfi_signal = vfi_val.ewm(span=signal_period).mean()

        return pd.DataFrame({
            'VFI': vfi_val, 'VFI_SIGNAL': vfi_signal
        }, index=close.index)

    @staticmethod
    def impulse_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        Impulse MACD - LazyBear
        标准 MACD + 彩色动量柱：
        绿色 = 多头动量增强, 红色 = 空头动量增强
        浅绿 = 多头减弱, 浅红 = 空头减弱
        """
        macd_df = TechnicalAnalyzer.macd(close, fast, slow, signal)
        macd_line = macd_df['DIF']
        macd_hist = macd_df['MACD']

        # 判断动量方向
        prev_hist = macd_hist.shift(1)

        impulse = np.zeros(len(close))
        for i in range(len(close)):
            h = macd_hist.iloc[i]
            ph = prev_hist.iloc[i] if i > 0 else 0
            if h > 0 and h > ph:
                impulse[i] = 2   # 深绿：多头增强
            elif h > 0:
                impulse[i] = 1   # 浅绿：多头减弱
            elif h < 0 and h < ph:
                impulse[i] = -2  # 深红：空头增强
            elif h < 0:
                impulse[i] = -1  # 浅红：空头减弱

        macd_df['IMPULSE'] = impulse
        macd_df['MACDH'] = macd_hist  # alias
        return macd_df

    @staticmethod
    def elder_impulse(close: pd.Series, ema_period: int = 13, macd_fast: int = 12,
                      macd_slow: int = 26, macd_signal: int = 9) -> pd.Series:
        """
        Elder Impulse System - Dr. Alexander Elder
        经典三色 K 线系统：
        绿色柱 = 多头（EM A↑ + MACD↑）
        红色柱 = 空头（EMA↓ + MACD↓）
        灰色柱 = 不确定
        """
        ema = close.ewm(span=ema_period, adjust=False).mean()
        macd_df = TechnicalAnalyzer.macd(close, macd_fast, macd_slow, macd_signal)

        impulse = np.zeros(len(close))
        for i in range(1, len(close)):
            ema_up = ema.iloc[i] > ema.iloc[i-1]
            macd_up = macd_df['MACD'].iloc[i] > macd_df['MACD'].iloc[i-1]

            if ema_up and macd_up:
                impulse[i] = 1    # 绿色 多头
            elif not ema_up and not macd_up:
                impulse[i] = -1   # 红色 空头
            else:
                impulse[i] = 0    # 灰色 不确定

        return pd.Series(impulse, index=close.index, name='ELDER')

    @staticmethod
    def vma(close: pd.Series, period: int = 20, sensitivity: float = 0.5) -> pd.Series:
        """
        Variable Moving Average (VMA) - 自适应均线
        波动越大，均线越灵敏；波动越小，均线越平滑
        """
        std = close.rolling(window=period).std()
        sma = close.rolling(window=period).mean()

        volatility_ratio = std / sma * 100
        avg_volatility = volatility_ratio.rolling(window=period).mean()

        # 自适应权重
        weight = 1 - np.exp(-sensitivity * volatility_ratio / avg_volatility)
        weight = weight.fillna(0.5).clip(0.1, 0.9)

        vma_val = np.zeros(len(close))
        vma_val[0] = close.iloc[0]
        for i in range(1, len(close)):
            w = weight.iloc[i] if not pd.isna(weight.iloc[i]) else 0.5
            vma_val[i] = w * close.iloc[i] + (1 - w) * vma_val[i-1]

        return pd.Series(vma_val, index=close.index, name='VMA')

    @staticmethod
    def heikin_ashi(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.DataFrame:
        """
        Heikin Ashi 平滑 K 线
        降低噪声，更清晰地显示趋势
        """
        ha_close = (open_ + high + low + close) / 4
        ha_open = np.zeros(len(open_))
        ha_high = np.zeros(len(high))
        ha_low = np.zeros(len(low))

        ha_open[0] = (open_.iloc[0] + close.iloc[0]) / 2
        ha_high[0] = high.iloc[0]
        ha_low[0] = low.iloc[0]

        for i in range(1, len(open_)):
            ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2
            ha_high[i] = max(high.iloc[i], ha_open[i], ha_close[i])
            ha_low[i] = min(low.iloc[i], ha_open[i], ha_close[i])

        return pd.DataFrame({
            'HA_OPEN': ha_open, 'HA_HIGH': ha_high,
            'HA_LOW': ha_low, 'HA_CLOSE': ha_close.values
        }, index=close.index)

    # ============================================================
    # 综合计算
    # ============================================================

    @classmethod
    def calc_all(cls, df: pd.DataFrame, indicators: list = None) -> pd.DataFrame:
        """
        对 OHLCV DataFrame 计算技术指标
        参数:
            df: OHLCV DataFrame
            indicators: 指标列表, 默认全部计算
                       ['ma','ema','wma','hma','macd','rsi','boll','kdj','atr','obv',
                        'sar','adx','cci','supertrend','stoch','wr','roc','momentum',
                        'keltner','donchian','ichimoku','vwap','mfi','cmf']
        """
        if indicators is None:
            indicators = ['ma','ema','macd','rsi','boll','kdj','atr','obv',
                         'sar','adx','cci','stoch','wr','vwap','mfi',
                         'squeeze','wavetrend','impulse_macd','vfi','elder','vma','heikin']

        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        result = df.copy()

        # 移动平均
        if 'ma' in indicators:
            for p in [5, 10, 20, 60, 120, 250]:
                result[f'MA{p}'] = cls.sma(close, p)
        if 'ema' in indicators:
            for p in [5, 10, 20, 60, 120, 250]:
                result[f'EMA{p}'] = cls.ema(close, p)
        if 'wma' in indicators:
            result['WMA20'] = cls.wma(close, 20)
        if 'hma' in indicators:
            result['HMA20'] = cls.hma(close, 20)

        # 趋势
        if 'macd' in indicators:
            macd_df = cls.macd(close)
            result = pd.concat([result, macd_df.add_prefix('MACD_')], axis=1)
        if 'sar' in indicators:
            result['SAR'] = cls.sar(high, low)
        if 'adx' in indicators:
            adx_df = cls.adx(high, low, close)
            result = pd.concat([result, adx_df], axis=1)
        if 'cci' in indicators:
            result['CCI20'] = cls.cci(high, low, close, 20)
        if 'supertrend' in indicators:
            st_df = cls.supertrend(high, low, close)
            result = pd.concat([result, st_df], axis=1)

        # 动量
        if 'rsi' in indicators:
            result['RSI14'] = cls.rsi(close, 14)
            result['RSI28'] = cls.rsi(close, 28)
        if 'stoch' in indicators:
            stoch_df = cls.stoch(high, low, close)
            result = pd.concat([result, stoch_df], axis=1)
        if 'wr' in indicators:
            result['WILLR14'] = cls.williams_r(high, low, close, 14)
        if 'kdj' in indicators:
            kdj_df = cls.kdj(high, low, close)
            result = pd.concat([result, kdj_df.add_prefix('KDJ_')], axis=1)
        if 'roc' in indicators:
            result['ROC12'] = cls.roc(close, 12)
        if 'momentum' in indicators:
            result['MOM10'] = cls.momentum(close, 10)

        # 波动性
        if 'boll' in indicators:
            bb_df = cls.bollinger_bands(close)
            result = pd.concat([result, bb_df], axis=1)
        if 'atr' in indicators:
            result['ATR14'] = cls.atr(high, low, close, 14)
        if 'keltner' in indicators:
            kc_df = cls.keltner_channels(high, low, close)
            result = pd.concat([result, kc_df], axis=1)
        if 'donchian' in indicators:
            dc_df = cls.donchian_channels(high, low)
            result = pd.concat([result, dc_df], axis=1)

        # 一目均衡表
        if 'ichimoku' in indicators:
            ichi_df = cls.ichimoku(high, low)
            result = pd.concat([result, ichi_df], axis=1)

        # 成交量
        if 'obv' in indicators:
            result['OBV'] = cls.obv(close, volume)
        if 'vwap' in indicators:
            result['VWAP'] = cls.vwap(high, low, close, volume)
        if 'mfi' in indicators:
            result['MFI14'] = cls.mfi(high, low, close, volume, 14)
        if 'cmf' in indicators:
            result['CMF21'] = cls.cmf(high, low, close, volume, 21)

        # 🔥 TradingView 社区 Top 指标
        if 'squeeze' in indicators:
            sqz = cls.squeeze_momentum(high, low, close)
            result = pd.concat([result, sqz], axis=1)
        if 'wavetrend' in indicators:
            wt = cls.wavetrend(high, low, close)
            result = pd.concat([result, wt], axis=1)
        if 'impulse_macd' in indicators:
            imacd = cls.impulse_macd(close)
            result = pd.concat([result, imacd.add_prefix('IMACD_')], axis=1)
        if 'vfi' in indicators:
            vfi_df = cls.vfi(high, low, close, volume)
            result = pd.concat([result, vfi_df], axis=1)
        if 'elder' in indicators:
            result['ELDER'] = cls.elder_impulse(close)
        if 'vma' in indicators:
            result['VMA20'] = cls.vma(close, 20)
        if 'heikin' in indicators:
            ha = cls.heikin_ashi(df['open'], high, low, close)
            result = pd.concat([result, ha], axis=1)

        return result

    @classmethod
    def detect_signals(cls, df: pd.DataFrame) -> List[Dict]:
        """
        检测最近的技术信号（对标 TradingView 常用信号）
        返回: [{date, type, strength, desc}, ...]
        """
        signals = []
        if len(df) < 60:
            return signals

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        idx = df.index[-1]

        # 金叉/死叉 (MA)
        for fast, slow, desc in [(5, 20, 'MA'), (10, 60, 'MA'), (20, 60, 'MA')]:
            fk, sk = f'MA{fast}', f'MA{slow}'
            if fk in df.columns and sk in df.columns:
                if prev[fk] <= prev[sk] and latest[fk] > latest[sk]:
                    signals.append({'date': str(idx), 'type': 'golden_cross', 'strength': 'high', 'desc': f'{desc}{fast}/{slow}金叉'})
                elif prev[fk] >= prev[sk] and latest[fk] < latest[sk]:
                    signals.append({'date': str(idx), 'type': 'dead_cross', 'strength': 'high', 'desc': f'{desc}{fast}/{slow}死叉'})

        # MACD
        if 'MACD_DIF' in df.columns and 'MACD_DEA' in df.columns:
            if prev['MACD_DIF'] <= prev['MACD_DEA'] and latest['MACD_DIF'] > latest['MACD_DEA']:
                signals.append({'date': str(idx), 'type': 'macd_golden', 'strength': 'high', 'desc': 'MACD金叉'})
            elif prev['MACD_DIF'] >= prev['MACD_DEA'] and latest['MACD_DIF'] < latest['MACD_DEA']:
                signals.append({'date': str(idx), 'type': 'macd_dead', 'strength': 'high', 'desc': 'MACD死叉'})
            if latest['MACD_DIF'] > 0 and prev['MACD_DIF'] <= 0:
                signals.append({'date': str(idx), 'type': 'macd_zero', 'strength': 'medium', 'desc': 'MACD上穿零轴'})
            elif latest['MACD_DIF'] < 0 and prev['MACD_DIF'] >= 0:
                signals.append({'date': str(idx), 'type': 'macd_zero', 'strength': 'medium', 'desc': 'MACD下穿零轴'})

        # RSI
        if 'RSI14' in df.columns:
            rsi = latest['RSI14']
            if rsi and rsi > 70:
                signals.append({'date': str(idx), 'type': 'overbought', 'strength': 'medium', 'desc': f'RSI14={rsi:.1f}超买区'})
            elif rsi and rsi < 30:
                signals.append({'date': str(idx), 'type': 'oversold', 'strength': 'medium', 'desc': f'RSI14={rsi:.1f}超卖区'})
            # RSI 背离检测（简化：价格新高 RSI 没有新高）
            if len(df) >= 20:
                recent_highs = df['close'].iloc[-20:].values
                recent_rsi = df['RSI14'].iloc[-20:].values
                if len(recent_highs) > 10:
                    half_h = int(len(recent_highs) / 2)
                    first_max_idx = recent_highs[:half_h].argmax()
                    second_max_idx = recent_highs[half_h:].argmax() + half_h
                    if (recent_highs[second_max_idx] > recent_highs[first_max_idx]
                            and recent_rsi[second_max_idx] < recent_rsi[first_max_idx]):
                        signals.append({'date': str(idx), 'type': 'bearish_div', 'strength': 'high', 'desc': 'RSI顶背离(看跌)'})

        # 布林带
        if 'BB_UPPER' in df.columns and 'BB_LOWER' in df.columns:
            try:
                bb_up = float(latest['BB_UPPER']); bb_low = float(latest['BB_LOWER'])
                cls_val = float(latest['close'])
                if cls_val and bb_up and cls_val > bb_up:
                    signals.append({'date': str(idx), 'type': 'bb_breakout', 'strength': 'medium', 'desc': '价格突破布林上轨'})
                elif cls_val and bb_low and cls_val < bb_low:
                    signals.append({'date': str(idx), 'type': 'bb_breakdown', 'strength': 'medium', 'desc': '价格跌破布林下轨'})
            except (ValueError, TypeError):
                pass
            # 带宽收缩（预示即将变盘）
            if 'BB_WIDTH' in df.columns and len(df) >= 20:
                recent = df['BB_WIDTH'].iloc[-20:].values
                if recent[-1] < recent.mean() * 0.5:
                    signals.append({'date': str(idx), 'type': 'bb_squeeze', 'strength': 'low', 'desc': '布林带收窄(即将变盘)'})

        # KDJ
        if 'KDJ_K' in df.columns and 'KDJ_D' in df.columns:
            if prev['KDJ_K'] <= prev['KDJ_D'] and latest['KDJ_K'] > latest['KDJ_D']:
                signals.append({'date': str(idx), 'type': 'kdj_golden', 'strength': 'medium', 'desc': 'KDJ金叉'})
            if latest['KDJ_J'] and latest['KDJ_J'] > 100:
                signals.append({'date': str(idx), 'type': 'kdj_overbought', 'strength': 'low', 'desc': 'KDJ超买'})
            elif latest['KDJ_J'] and latest['KDJ_J'] < 0:
                signals.append({'date': str(idx), 'type': 'kdj_oversold', 'strength': 'low', 'desc': 'KDJ超卖'})

        # ADX 趋势强度
        if 'ADX' in df.columns:
            adx = latest['ADX']
            if adx:
                if adx > 40:
                    signals.append({'date': str(idx), 'type': 'strong_trend', 'strength': 'high', 'desc': f'ADX={adx:.1f}强趋势'})
                elif adx < 20:
                    signals.append({'date': str(idx), 'type': 'weak_trend', 'strength': 'low', 'desc': f'ADX={adx:.1f}震荡市'})

        # CCI
        if 'CCI20' in df.columns:
            cci = latest['CCI20']
            if cci and cci > 100:
                signals.append({'date': str(idx), 'type': 'cci_overbought', 'strength': 'low', 'desc': f'CCI={cci:.0f}超买'})
            elif cci and cci < -100:
                signals.append({'date': str(idx), 'type': 'cci_oversold', 'strength': 'low', 'desc': f'CCI={cci:.0f}超卖'})

        # SuperTrend 转向
        if 'SUPERT_DIR' in df.columns:
            if prev['SUPERT_DIR'] == -1 and latest['SUPERT_DIR'] == 1:
                signals.append({'date': str(idx), 'type': 'supertrend_up', 'strength': 'high', 'desc': 'SuperTrend转多'})
            elif prev['SUPERT_DIR'] == 1 and latest['SUPERT_DIR'] == -1:
                signals.append({'date': str(idx), 'type': 'supertrend_down', 'strength': 'high', 'desc': 'SuperTrend转空'})

        # Stochastic
        if 'STOCH_K' in df.columns and 'STOCH_D' in df.columns:
            stoch_k = latest['STOCH_K']
            if stoch_k:
                if stoch_k > 80:
                    signals.append({'date': str(idx), 'type': 'stoch_overbought', 'strength': 'low', 'desc': f'StochK={stoch_k:.1f}超买'})
                elif stoch_k < 20:
                    signals.append({'date': str(idx), 'type': 'stoch_oversold', 'strength': 'low', 'desc': f'StochK={stoch_k:.1f}超卖'})

        # 均线排列
        if all(f'MA{p}' in df.columns for p in [5, 20, 60]):
            if latest['MA5'] > latest['MA20'] > latest['MA60'] and not (prev['MA5'] > prev['MA20'] > prev['MA60']):
                signals.append({'date': str(idx), 'type': 'bullish_alignment', 'strength': 'high', 'desc': '均线多头排列'})
            elif latest['MA5'] < latest['MA20'] < latest['MA60'] and not (prev['MA5'] < prev['MA20'] < prev['MA60']):
                signals.append({'date': str(idx), 'type': 'bearish_alignment', 'strength': 'high', 'desc': '均线空头排列'})

        # 🔥 Squeeze Momentum 信号
        if 'SQZ_ON' in df.columns and 'SQZ_MOM' in df.columns:
            if prev['SQZ_ON'] == 1 and latest['SQZ_ON'] == 0 and latest['SQZ_MOM'] > 0:
                signals.append({'date': str(idx), 'type': 'squeeze_fire_long', 'strength': 'very_high',
                                'desc': 'Squeeze释放+多头动量(强力做多)'})
            elif prev['SQZ_ON'] == 1 and latest['SQZ_ON'] == 0 and latest['SQZ_MOM'] < 0:
                signals.append({'date': str(idx), 'type': 'squeeze_fire_short', 'strength': 'very_high',
                                'desc': 'Squeeze释放+空头动量(强力做空)'})

        # 🔥 WaveTrend 信号
        if 'WT1' in df.columns and 'WT2' in df.columns:
            wt1, wt2 = latest['WT1'], latest['WT2']
            pwt1, pwt2 = prev['WT1'], prev['WT2']
            if pwt1 <= pwt2 and wt1 > wt2:
                signals.append({'date': str(idx), 'type': 'wt_golden', 'strength': 'high', 'desc': 'WaveTrend金叉'})
            elif pwt1 >= pwt2 and wt1 < wt2:
                signals.append({'date': str(idx), 'type': 'wt_dead', 'strength': 'high', 'desc': 'WaveTrend死叉'})
            if wt1 is not None:
                if wt1 > 60:
                    signals.append({'date': str(idx), 'type': 'wt_overbought', 'strength': 'medium',
                                    'desc': f'WaveTrend={wt1:.1f}超买区'})
                elif wt1 < -60:
                    signals.append({'date': str(idx), 'type': 'wt_oversold', 'strength': 'medium',
                                    'desc': f'WaveTrend={wt1:.1f}超卖区'})

        # Elder Impulse 信号
        if 'ELDER' in df.columns:
            if prev['ELDER'] != 1 and latest['ELDER'] == 1:
                signals.append({'date': str(idx), 'type': 'elder_green', 'strength': 'medium', 'desc': 'Elder转为多头'})
            elif prev['ELDER'] != -1 and latest['ELDER'] == -1:
                signals.append({'date': str(idx), 'type': 'elder_red', 'strength': 'medium', 'desc': 'Elder转为空头'})

        # VFI 信号
        if 'VFI' in df.columns:
            vfi = latest['VFI']
            if vfi is not None:
                if prev.get('VFI') and prev['VFI'] <= 0 and vfi > 0:
                    signals.append({'date': str(idx), 'type': 'vfi_turnover', 'strength': 'high', 'desc': 'VFI转正(资金流入)'})
                elif prev.get('VFI') and prev['VFI'] >= 0 and vfi < 0:
                    signals.append({'date': str(idx), 'type': 'vfi_turnover', 'strength': 'high', 'desc': 'VFI转负(资金流出)'})

        return signals
