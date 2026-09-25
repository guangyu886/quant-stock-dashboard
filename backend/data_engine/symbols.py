"""
股票代码管理模块
管理 A股/港股/美股 代码清单，支持全市场 + 自选
"""

# ===== A股主要指数成分股（沪深300 + 中证500 + 创业板 + 科创板代表）=====
# 实际使用时通过 akshare 动态获取全市场列表
A_INDEX_SYMBOLS = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000688": "科创50",
    "sh000300": "沪深300",
    "sh000905": "中证500",
    "sh000852": "中证1000",
    "bj899050": "北证50",
}

# ===== 港股主要指数 =====
HK_INDEX_SYMBOLS = {
    "^HSI": "恒生指数",
    "^HSCE": "国企指数",
    "^HSTECH": "恒生科技指数",
}

# ===== 美股主要指数 =====
US_INDEX_SYMBOLS = {
    "^GSPC": "标普500",
    "^DJI": "道琼斯工业",
    "^IXIC": "纳斯达克综合",
    "^NDX": "纳斯达克100",
    "^RUT": "罗素2000",
    "^VIX": "恐慌指数",
}

# ===== 美股自选池（示例）=====
US_STARTER_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "V", "JNJ", "WMT", "PG", "XOM", "BAC", "DIS",
    "NFLX", "ADBE", "CRM", "AMD", "INTC", "QCOM", "TXN", "AVGO",
    "SPY", "QQQ", "IWM", "DIA", "EEM", "FXI", "KWEB",
]

# ===== 港股自选池（示例）=====
HK_STARTER_SYMBOLS = [
    "00700", "09988", "09999", "00941", "01299", "02318", "00388",
    "03690", "09618", "09888", "01810", "02269", "01024", "02015",
    "02800", "02828", "03033",
]

# ===== 市场代码前缀映射 =====
def to_akshare_symbol(symbol: str, market: str) -> str:
    """转成 akshare 格式"""
    if market == 'A':
        if symbol.startswith('sh') or symbol.startswith('sz') or symbol.startswith('bj'):
            return symbol
        if symbol.startswith('6') or symbol.startswith('9'):
            return f"sh{symbol}"
        if symbol.startswith('0') or symbol.startswith('3') or symbol.startswith('1'):
            return f"sz{symbol}"
        if symbol.startswith('8') or symbol.startswith('4'):
            return f"bj{symbol}"
    return symbol


def to_yfinance_symbol(symbol: str, market: str) -> str:
    """转成 yfinance 格式"""
    if market == 'A':
        code = symbol.replace('sh', '').replace('sz', '').replace('bj', '')
        if symbol.startswith('sh'):
            return f"{code}.SS"
        elif symbol.startswith('sz'):
            return f"{code}.SZ"
        elif symbol.startswith('bj'):
            return f"{code}.BJ"
    elif market == 'HK':
        code = symbol.lstrip('0') or '0'
        return f"{code}.HK"
    return symbol
