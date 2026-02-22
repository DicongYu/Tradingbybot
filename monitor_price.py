import ccxt
import time
import subprocess
import os

API_KEY = os.environ.get('OKX_API_KEY', '')
SECRET = os.environ.get('OKX_SECRET', '')
PASSWORD = os.environ.get('OKX_PASSWORD', '')

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

SYMBOL = 'ETH/USDT'
CHECK_INTERVAL = 60

def send_notification(title, message):
    subprocess.run(['notify-send', title, message])
    subprocess.run(['paplay', '/usr/share/sounds/LinuxMint/stereo/dialog-information.ogg'])

def play_sound():
    subprocess.run(['paplay', '/usr/share/sounds/LinuxMint/stereo/dialog-information.ogg'])

import sys

SYMBOL = 'ETH/USDT'
CHECK_INTERVAL = 60
THRESHOLD = 2  # 涨跌幅阈值 (%)

print(f"开始监控 {SYMBOL}，每 {CHECK_INTERVAL} 秒检查一次", flush=True)
print(f"买入信号: 下跌 {THRESHOLD}% | 卖出信号: 上涨 {THRESHOLD}%", flush=True)
print("按 Ctrl+C 停止\n", flush=True)

base_price = None

while True:
    try:
        ticker = okx.fetch_ticker(SYMBOL)
        current_price = ticker['last']
        
        if base_price is None:
            base_price = current_price
            print(f"基准价格: ${base_price}", flush=True)
        
        change_percent = (current_price - base_price) / base_price * 100
        
        if change_percent <= -THRESHOLD:
            msg = f"买入信号! 价格下跌 {abs(change_percent):.2f}%\n当前价格: ${current_price}\n基准价格: ${base_price}"
            print(f"🔔 {msg}", flush=True)
            send_notification("买入信号", msg)
            base_price = current_price  # 重置基准
            
        elif change_percent >= THRESHOLD:
            msg = f"卖出信号! 价格上涨 {change_percent:.2f}%\n当前价格: ${current_price}\n基准价格: ${base_price}"
            print(f"🔔 {msg}", flush=True)
            send_notification("卖出信号", msg)
            base_price = current_price  # 重置基准
        else:
            print(f"{SYMBOL}: ${current_price} (相对基准: {change_percent:+.2f}%)", flush=True)
        
    except Exception as e:
        print(f"错误: {e}")
    
    time.sleep(CHECK_INTERVAL)
