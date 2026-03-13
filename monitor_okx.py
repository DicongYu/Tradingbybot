import ccxt
import os

API_KEY = os.environ.get('OKX_API_KEY', '')
SECRET = os.environ.get('OKX_SECRET', '')
PASSWORD = os.environ.get('OKX_PASSWORD', '')

okx = None

def init_okx():
    global okx
    if API_KEY and SECRET:
        okx = ccxt.okx({
            'apiKey': API_KEY,
            'secret': SECRET,
            'password': PASSWORD,
            'enableRateLimit': True,
            'timeout': 30000,
            'proxies': {
                'http': 'http://127.0.0.1:20171',
                'https': 'http://127.0.0.1:20171',
            },
        })
    else:
        okx = ccxt.okx({
            'enableRateLimit': True,
            'timeout': 30000,
            'proxies': {
                'http': 'http://127.0.0.1:20171',
                'https': 'http://127.0.0.1:20171',
            },
        })

def get_price(symbol='ETH/USDT'):
    if okx is None:
        init_okx()
    ticker = okx.fetch_ticker(symbol)
    return {
        'symbol': symbol,
        'price': ticker['last'],
        'high': ticker.get('high'),
        'low': ticker.get('low'),
        'volume': ticker.get('baseVolume'),
        'change': ticker.get('percentage'),
        'bid': ticker.get('bid'),
        'ask': ticker.get('ask')
    }

def get_ticker(symbol='ETH/USDT'):
    if okx is None:
        init_okx()
    return okx.fetch_ticker(symbol)

def get_balance():
    if okx is None:
        init_okx()
    try:
        balance = okx.fetch_balance()
        return {
            'total_usd': balance.get('total', {}).get('USDT', 0),
            'ETH': balance.get('total', {}).get('ETH', 0),
            'BTC': balance.get('total', {}).get('BTC', 0),
            'USDT': balance.get('total', {}).get('USDT', 0),
            'free': balance.get('free', {}),
        }
    except Exception as e:
        return None

init_okx()
