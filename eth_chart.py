import ccxt
import mplfinance as mpf
import pandas as pd

# OKX K线 API 有问题，使用 Coinbase 获取数据
exchange = ccxt.coinbase()

print("正在获取 ETH/USDT K线数据...")
ohlcv = exchange.fetch_ohlcv('ETH/USDT', '1h', 200)

df = pd.DataFrame(ohlcv, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
df['Date'] = pd.to_datetime(df['Date'], unit='ms')
df.set_index('Date', inplace=True)

df['Signal'] = 0
df.loc[
    (df['Close'] < df['Close'].shift(1) * 0.98) & (df['Volume'] > 0),
    'Signal'
] = 1  # 买入信号: 下跌2%

df.loc[
    (df['Close'] > df['Close'].shift(1) * 1.02) & (df['Volume'] > 0),
    'Signal'
] = -1  # 卖出信号: 上涨2%

buy_signals = df[df['Signal'] == 1].index
sell_signals = df[df['Signal'] == -1].index

print(f"买入信号数量: {len(buy_signals)}")
print(f"卖出信号数量: {len(sell_signals)}")

if len(buy_signals) > 0:
    print(f"买入信号日期: {buy_signals.tolist()}")
if len(sell_signals) > 0:
    print(f"卖出信号日期: {sell_signals.tolist()}")

buy_points = [(date, df.loc[date, 'Close']) for date in buy_signals]
sell_points = [(date, df.loc[date, 'Close']) for date in sell_signals]

apds = []
if buy_points:
    apds.append(mpf.make_addplot([df.loc[d, 'Close'] if d in df.index else None for d in df.index], 
                                  type='scatter', marker='^', markersize=100, color='green', label='Buy'))
if sell_points:
    apds.append(mpf.make_addplot([df.loc[d, 'Close'] if d in df.index else None for d in df.index], 
                                   type='scatter', marker='v', markersize=100, color='red', label='Sell'))

mc = mpf.make_marketcolors(up='green', down='red', edge='inherit', wick='inherit', volume='in')
s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='charles')

print("正在生成图表...")
if apds:
    mpf.plot(df, type='candle', style=s, title='ETH/USDT 1H', ylabel='Price (USD)', 
             addplot=apds)
else:
    mpf.plot(df, type='candle', style=s, title='ETH/USDT 1H', ylabel='Price (USD)')
print("图表已显示")
