import ccxt


class OkxBot:
    def __init__(self, api_key=None, secret=None, password=None, testnet=False):
        self.exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': secret,
            'password': password,
            'enableRateLimit': True,
            'proxies': {
                'http': 'http://127.0.0.1:20171',
                'https': 'http://127.0.0.1:20171',
            },
        })
        if testnet:
            self.exchange.set_sandbox_mode(True)

    def fetch_ticker(self, symbol):
        return self.exchange.fetch_ticker(symbol)

    def fetch_ohlcv(self, symbol, timeframe='1h', limit=100):
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit)

    def fetch_balance(self):
        return self.exchange.fetch_balance()

    def create_order(self, symbol, order_type, side, amount, price=None):
        return self.exchange.create_order(symbol, order_type, side, amount, price)

    def fetch_orders(self, symbol=None):
        return self.exchange.fetch_orders(symbol)


if __name__ == '__main__':
    bot = OkxBot()

    ticker = bot.fetch_ticker('BTC/USDT')
    print(f"BTC/USDT: {ticker['last']}")

    ohlcv = bot.fetch_ohlcv('BTC-USDT', '1h', 10)
    print(f"K线数据: {len(ohlcv)} 条")

    ticker = bot.fetch_ticker('ETH/USDT')
    print(f"ETH/USDT: {ticker['last']}")

    ohlcv = bot.fetch_ohlcv('ETH/USDT', '1h', 10)
    print(f"K线数据: {len(ohlcv)} 条")

   
