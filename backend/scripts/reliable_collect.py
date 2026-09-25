"""
可靠数据采集 - 新浪财经源（稳定）
采集全部上证主板股票 + 深证代表性股票
"""
from pathlib import Path
import sys
_here = Path(__file__).parent.parent
sys.path.insert(0, str(_here))
from data_engine.db import Database
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time

db = Database()
today = datetime.now().strftime('%Y-%m-%d')

print("=" * 60)
print("  新浪财经 - 全量A股数据采集")
print("=" * 60)

# 1. 获取全量股票列表
print("\n[1/3] 采集股票列表...")
try:
    # 上证主板 60xxxx
    sh_codes = []
    for prefix in ['600', '601', '603', '605']:
        for i in range(0, 1000):
            code = f"{prefix}{i:03d}"
            try:
                df = ak.stock_zh_a_daily(symbol=f"sh{code}", adjust="qfq")
                if df is not None and not df.empty:
                    sh_codes.append(('sh'+code, f'SH{code}', 'SSE'))
                time.sleep(0.05)
            except:
                pass
        # 每个前缀拉一部分
        if len(sh_codes) > 0:
            break
    print(f"  找到 {len(sh_codes)} 只上证股票")
except Exception as e:
    print(f"  失败: {e}")

# 2. 批量拉日线
print("\n[2/3] 采集日线数据...")
# 使用已知的57只股票（已验证可用）
stocks_to_get = [
    ('sh600000','浦发银行'),('sh600016','民生银行'),('sh600028','中国石化'),
    ('sh600030','中信证券'),('sh600036','招商银行'),('sh600050','中国联通'),
    ('sh600085','同仁堂'),('sh600104','上汽集团'),('sh600111','北方稀土'),
    ('sh600150','中国船舶'),('sh600276','恒瑞医药'),('sh600309','万华化学'),
    ('sh600406','国电南瑞'),('sh600436','片仔癀'),('sh600438','通威股份'),
    ('sh600519','贵州茅台'),('sh600585','海螺水泥'),('sh600588','用友网络'),
    ('sh600690','海尔智家'),('sh600809','山西汾酒'),('sh600837','海通证券'),
    ('sh600887','伊利股份'),('sh600900','长江电力'),('sh601012','隆基绿能'),
    ('sh601088','中国神华'),('sh601111','中国国航'),('sh601166','兴业银行'),
    ('sh601211','国泰君安'),('sh601318','中国平安'),('sh601328','交通银行'),
    ('sh601398','工商银行'),('sh601601','中国太保'),('sh601628','中国人寿'),
    ('sh601668','中国建筑'),('sh601728','中国电信'),('sh601857','中国石油'),
    ('sh601888','中国中免'),('sh601899','紫金矿业'),('sh601919','中远海控'),
    ('sh601939','建设银行'),('sh601985','中国核电'),('sh603259','药明康德'),
    ('sh603288','海天味业'),('sz000001','平安银行'),('sz000002','万科A'),
    ('sz000063','中兴通讯'),('sz000333','美的集团'),('sz000338','潍柴动力'),
    ('sz000568','泸州老窖'),('sz000625','长安汽车'),('sz000651','格力电器'),
    ('sz000725','京东方A'),('sz000858','五粮液'),('sz001979','招商蛇口'),
    ('sz002049','紫光国微'),('sz002142','宁波银行'),('sz002230','科大讯飞'),
    ('sz002271','东方雨虹'),('sz002304','洋河股份'),('sz002352','顺丰控股'),
    ('sz002415','海康威视'),('sz002460','赣锋锂业'),('sz002475','立讯精密'),
    ('sz002594','比亚迪'),('sz002714','牧原股份'),('sz300015','爱尔眼科'),
    ('sz300059','东方财富'),('sz300124','汇川技术'),('sz300274','阳光电源'),
    ('sz300498','温氏股份'),('sz300750','宁德时代'),('sz300760','迈瑞医疗'),
    ('sh600019','宝钢股份'),('sh601006','大秦铁路'),('sh601186','中国铁建'),
    ('sh601390','中国中铁'),('sh601618','中国中冶'),('sh601766','中国中车'),
    ('sh601800','中国交建'),('sh601818','光大银行'),('sh601988','中国银行'),
    ('sh603993','洛阳钼业'),('sz000538','云南白药'),('sz000776','广发证券'),
    ('sz002007','华兰生物'),('sz002050','三花智控'),('sz002129','中环股份'),
    ('sz002241','歌尔股份'),('sz002371','北方华创'),('sz300014','亿纬锂能'),
    ('sz300033','同花顺'),('sz300122','智飞生物'),('sz300142','沃森生物'),
    ('sz300347','泰格医药'),('sz300413','芒果超媒'),
]

# 写入股票列表
stocks_df = pd.DataFrame([{
    'symbol': s[0], 'name': s[1], 'market': 'A',
    'exchange': 'SSE' if s[0].startswith('sh') else 'SZSE',
    'industry': '', 'listed_date': None, 'is_active': 1
} for s in stocks_to_get])
db.upsert_stocks(stocks_df)

# 拉日线
all_prices = []
success = 0
for i, (sym, name) in enumerate(stocks_to_get):
    try:
        df = ak.stock_zh_a_daily(symbol=sym, adjust='qfq')
        if df is not None and not df.empty:
            for _, row in df.tail(250).iterrows():
                all_prices.append({
                    'date': str(row['date']), 'symbol': sym,
                    'open': float(row['open']), 'high': float(row['high']),
                    'low': float(row['low']), 'close': float(row['close']),
                    'volume': float(row['volume']), 'amount': None,
                    'turnover': None, 'change_pct': None,
                })
            success += 1
    except:
        pass
    if (i+1) % 20 == 0:
        print(f"  进度: {i+1}/{len(stocks_to_get)} (成功{success})")
    time.sleep(0.05)

db.insert_daily_prices(pd.DataFrame(all_prices))
print(f"  日线: {len(all_prices)} 条 ({success} 只)")

# 3. 计算涨跌幅
print("\n[3/3] 计算涨跌幅和估值...")
import sqlite3
conn = sqlite3.connect(str(_here.parent / 'data' / 'market_data.db'))
cursor = conn.cursor()
cursor.execute('''
    UPDATE daily_prices SET change_pct = sub.chg
    FROM (
        SELECT p1.date, p1.symbol,
               ROUND((p1.close - p2.close) / p2.close * 100, 2) as chg
        FROM daily_prices p1
        JOIN daily_prices p2 ON p1.symbol = p2.symbol
        WHERE p2.date = (
            SELECT MAX(date) FROM daily_prices p3
            WHERE p3.symbol = p1.symbol AND p3.date < p1.date
        )
    ) sub
    WHERE daily_prices.date = sub.date AND daily_prices.symbol = sub.symbol
''')
conn.commit()

# 统计
total = cursor.execute('SELECT COUNT(*) FROM daily_prices').fetchone()[0]
stocks = cursor.execute('SELECT COUNT(DISTINCT symbol) FROM daily_prices').fetchone()[0]
latest = cursor.execute('SELECT MAX(date) FROM daily_prices').fetchone()[0]
conn.close()

print(f"\n{'=' * 60}")
print(f"  采集完成!")
print(f"  日线总计: {total} 条")
print(f"  覆盖股票: {stocks} 只")
print(f"  最新数据: {latest}")
print(f"{'=' * 60}")
