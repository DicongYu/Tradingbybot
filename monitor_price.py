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

print(f"开始监控 {SYMBOL}，每 {CHECK_INTERVAL} 秒检查一次", flush=True)
print("买入信号: 下跌 2% | 卖出信号: 上涨 2%", flush=True)
print("按 Ctrl+C 停止\n", flush=True)

prev_price = None

while True:
    try:
        ticker = okx.fetch_ticker(SYMBOL)
        current_price = ticker['last']
        
        if prev_price is not None:
            change_percent = (current_price - prev_price) / prev_price * 100
            
            if change_percent <= -2:
                msg = f"买入信号! 价格下跌 {change_percent:.2f}%\n当前价格: ${current_price}\n上次价格: ${prev_price}"
                print(f"🔔 {msg}", flush=True)
                send_notification("买入信号", msg)
                
            elif change_percent >= 2:
                msg = f"卖出信号! 价格上涨 {change_percent:.2f}%\n当前价格: ${current_price}\n上次价格: ${prev_price}"
                print(f"🔔 {msg}", flush=True)
                send_notification("卖出信号", msg)
            else:
                print(f"{SYMBOL}: ${current_price} (变化: {change_percent:+.2f}%)", flush=True)
        else:
            print(f"{SYMBOL}: ${current_price} (首次价格)", flush=True)
        
        prev_price = current_price
        
    except Exception as e:
        print(f"错误: {e}")
    
    time.sleep(CHECK_INTERVAL)
