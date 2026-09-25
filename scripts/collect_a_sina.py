"""
A股数据采集 - 新浪财经数据源（你的网络可用）
"""
import sys
sys.path.insert(0, 'C:/Users/Lzs/stock-dashboard/backend')
from data_engine.db import Database
import akshare as ak
import pandas as pd
from datetime import datetime

db = Database()
today = datetime.now().strftime('%Y-%m-%d')

print("=" * 50)
print("A股数据采集 - 新浪财经源")
print("=" * 50)

# 1. 股票列表
print("\n[1/4] 采集A股列表...")
# 新浪接口获取全市场
df_spot = ak.stock_zh_a_spot_em()  # 试一次东方财富
if df_spot is None or df_spot.empty:
    # 降级：用常见股票构建列表
    print("  东方财富不可用，使用预设股票池")
    # 沪深300核心成分股
    stocks_data = []
    try:
        # 用新浪接口逐个验证
        test_codes = [
            ('sh600000','浦发银行'),('sh600016','民生银行'),('sh600019','宝钢股份'),
            ('sh600028','中国石化'),('sh600030','中信证券'),('sh600036','招商银行'),
            ('sh600048','保利发展'),('sh600050','中国联通'),('sh600085','同仁堂'),
            ('sh600104','上汽集团'),('sh600111','北方稀土'),('sh600150','中国船舶'),
            ('sh600276','恒瑞医药'),('sh600309','万华化学'),('sh600406','国电南瑞'),
            ('sh600436','片仔癀'),('sh600438','通威股份'),('sh600519','贵州茅台'),
            ('sh600585','海螺水泥'),('sh600588','用友网络'),('sh600690','海尔智家'),
            ('sh600809','山西汾酒'),('sh600837','海通证券'),('sh600887','伊利股份'),
            ('sh600900','长江电力'),('sh601012','隆基绿能'),('sh601088','中国神华'),
            ('sh601111','中国国航'),('sh601166','兴业银行'),('sh601211','国泰君安'),
            ('sh601318','中国平安'),('sh601328','交通银行'),('sh601398','工商银行'),
            ('sh601601','中国太保'),('sh601628','中国人寿'),('sh601668','中国建筑'),
            ('sh601728','中国电信'),('sh601857','中国石油'),('sh601888','中国中免'),
            ('sh601899','紫金矿业'),('sh601919','中远海控'),('sh601939','建设银行'),
            ('sh601985','中国核电'),('sh603259','药明康德'),('sh603288','海天味业'),
            ('sz000001','平安银行'),('sz000002','万科A'),('sz000063','中兴通讯'),
            ('sz000333','美的集团'),('sz000338','潍柴动力'),('sz000568','泸州老窖'),
            ('sz000625','长安汽车'),('sz000651','格力电器'),('sz000725','京东方A'),
            ('sz000858','五粮液'),('sz001979','招商蛇口'),('sz002049','紫光国微'),
            ('sz002142','宁波银行'),('sz002230','科大讯飞'),('sz002271','东方雨虹'),
            ('sz002304','洋河股份'),('sz002352','顺丰控股'),('sz002415','海康威视'),
            ('sz002460','赣锋锂业'),('sz002475','立讯精密'),('sz002594','比亚迪'),
            ('sz002714','牧原股份'),('sz300015','爱尔眼科'),('sz300059','东方财富'),
            ('sz300124','汇川技术'),('sz300274','阳光电源'),('sz300498','温氏股份'),
            ('sz300750','宁德时代'),('sz300760','迈瑞医疗'),
        ]
        for code, name in test_codes:
            stocks_data.append({
                'symbol': code, 'name': name, 'market': 'A',
                'exchange': 'SSE' if code.startswith('sh') else 'SZSE',
                'industry': '', 'listed_date': None, 'is_active': 1
            })
    except Exception as e:
        print(f"  构建列表失败: {e}")

    df_stocks = pd.DataFrame(stocks_data)
    db.upsert_stocks(df_stocks)
    print(f"  写入 {len(stocks_data)} 只股票")
else:
    # 东方财富可用
    records = []
    for _, row in df_spot.iterrows():
        code = str(row.get('代码', ''))
        if code.startswith('6'):
            sym = f"sh{code}"
        elif code.startswith(('0','3','1')):
            sym = f"sz{code}"
        elif code.startswith(('8','4')):
            sym = f"bj{code}"
        else:
            sym = f"sh{code}"
        records.append({
            'symbol': sym, 'name': str(row.get('名称','')),
            'market': 'A', 'exchange': 'SSE' if sym.startswith('sh') else 'SZSE',
            'industry': str(row.get('所属行业','')), 'listed_date': None, 'is_active': 1,
        })
    db.upsert_stocks(pd.DataFrame(records))
    print(f"  写入 {len(records)} 只股票")

# 2. 日线数据（新浪财经 + yfinance）
print("\n[2/4] 采集日线行情（新浪/yfinance）...")
stocks = db.get_stocks(market='A')
if len(stocks) == 0:
    print("  没有股票数据，跳过")
else:
    all_prices = []
    import time
    for i, (_, s) in enumerate(stocks.iterrows()):
        sym = s['symbol']
        name = s['name']
        try:
            # 新浪接口
            df = ak.stock_zh_a_daily(symbol=sym, adjust="qfq")
            if df is not None and not df.empty:
                for _, row in df.tail(250).iterrows():
                    all_prices.append({
                        'date': str(row.get('date','')),
                        'symbol': sym,
                        'open': float(row['open']) if row.get('open') else None,
                        'high': float(row['high']) if row.get('high') else None,
                        'low': float(row['low']) if row.get('low') else None,
                        'close': float(row['close']) if row.get('close') else None,
                        'volume': float(row['volume']) if row.get('volume') else None,
                        'amount': None,
                        'turnover': None,
                        'change_pct': None,
                    })
        except Exception as e:
            # 静默跳过
            pass
        if (i+1) % 10 == 0:
            print(f"  进度: {i+1}/{len(stocks)}")
        time.sleep(0.1)  # 避免请求太快

    if all_prices:
        db.insert_daily_prices(pd.DataFrame(all_prices))
        print(f"  写入 {len(all_prices)} 条日线数据 ({len(set(p['symbol'] for p in all_prices))} 只)")

# 3. 估值数据
print("\n[3/4] 写入估值数据...")
try:
    df_spot = ak.stock_zh_a_spot_em()
    if df_spot is not None and not df_spot.empty:
        val_records = []
        for _, row in df_spot.iterrows():
            code = str(row.get('代码',''))
            sym = ('sh'+code) if code.startswith('6') else ('sz'+code) if code.startswith(('0','3')) else None
            if sym:
                val_records.append({
                    'date': today, 'symbol': sym,
                    'pe': float(row.get('市盈率-动态',0)) if row.get('市盈率-动态') not in [None,'-',''] else None,
                    'pe_ttm': float(row.get('市盈率-静态',0)) if row.get('市盈率-静态') not in [None,'-',''] else None,
                    'pb': float(row.get('市净率',0)) if row.get('市净率') not in [None,'-',''] else None,
                    'ps': None, 'dividend_yield': None,
                    'total_mv': float(row.get('总市值',0)) if row.get('总市值') not in [None,'-',''] else None,
                    'circ_mv': float(row.get('流通市值',0)) if row.get('流通市值') not in [None,'-',''] else None,
                })
        db.insert_daily_valuation(pd.DataFrame(val_records))
        print(f"  写入 {len(val_records)} 条估值数据")
    else:
        print("  跳过（东方财富不可用）")
except Exception as e:
    print(f"  跳过（东方财富不可用）: {e}")

# 4. 市场情绪
print("\n[4/4] 采集市场情绪...")
try:
    df = ak.stock_zh_a_spot_em()
    if df is not None and not df.empty:
        up = int((df['涨跌幅'] > 0).sum())
        down = int((df['涨跌幅'] < 0).sum())
        flat = int((df['涨跌幅'] == 0).sum())
        vol = df['成交额'].astype(float).sum() / 1e8
        limit_up = int((df['涨跌幅'] >= 9.9).sum())
        limit_down = int((df['涨跌幅'] <= -9.9).sum())
        db.insert_market_breadth(today, 'A', {
            'up_count': up, 'down_count': down, 'flat_count': flat,
            'limit_up': limit_up, 'limit_down': limit_down,
            'total_volume': round(vol, 2),
        })
        print(f"  涨{up} 跌{down} 平{flat} 涨停{limit_up} 跌停{limit_down}")
    else:
        print("  跳过（东方财富不可用）")
except Exception as e:
    print(f"  跳过: {e}")

print("\n" + "=" * 50)
# 验证
a = db.get_stocks('A')
prices = __import__('sqlite3').connect(str(db.db_path)).execute('SELECT COUNT(DISTINCT symbol) FROM daily_prices').fetchone()[0]
print(f"完成! A股:{len(a)}只  日线覆盖:{prices}只")
print("=" * 50)
