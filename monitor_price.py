import ccxt
import time
import subprocess
import os
import sys
from datetime import datetime

sys.path.insert(0, '/home/dcy/OkxTrading')
import monitor_onchain

API_KEY = os.environ.get('OKX_API_KEY', '')
SECRET = os.environ.get('OKX_SECRET', '')
PASSWORD = os.environ.get('OKX_PASSWORD', '')

LOG_FILE = '/home/dcy/OkxTrading/monitor.log'

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')

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
NOTIFY_INTERVAL_PRICE = 20 * 60
NOTIFY_INTERVAL_ONCHAIN = 5 * 60

def send_notification(title, message):
    subprocess.run(['notify-send', title, message], capture_output=True)
    subprocess.run(['paplay', '/usr/share/sounds/LinuxMint/stereo/dialog-information.ogg'], capture_output=True)

THRESHOLD = 2

log(f"=" * 60)
log(f"开始监控 {SYMBOL}")
log(f"价格提醒: 每 {NOTIFY_INTERVAL_PRICE//60} 分钟")
log(f"链上数据提醒: 每 {NOTIFY_INTERVAL_ONCHAIN//60} 分钟")
log("=" * 60)

try:
    ticker = okx.fetch_ticker(SYMBOL)
    current_price = ticker['last']
    base_price = current_price
    log(f"基准价格: ${base_price}")
    onchain_summary = monitor_onchain.get_onchain_summary()
    send_notification("盯盘已启动", 
        f"{SYMBOL}: ${current_price}\n买入: 下跌{THRESHOLD}% | 卖出: 上涨{THRESHOLD}%\n\n链上: {onchain_summary}")
except Exception as e:
    log(f"获取价格失败: {e}")
    send_notification("盯盘已启动", f"开始监控 {SYMBOL}\n买入: 下跌{THRESHOLD}% | 卖出: 上涨{THRESHOLD}%")
    base_price = None

notify_counter_price = 0
notify_counter_onchain = 0

while True:
    try:
        ticker = okx.fetch_ticker(SYMBOL)
        current_price = ticker['last']
        
        if base_price is None:
            base_price = current_price
            log(f"基准价格: ${base_price}")
        
        change_percent = (current_price - base_price) / base_price * 100
        
        notify_counter_price += 1
        notify_counter_onchain += 1
        
        if notify_counter_onchain >= NOTIFY_INTERVAL_ONCHAIN // CHECK_INTERVAL:
            notify_counter_onchain = 0
            onchain_summary = monitor_onchain.get_onchain_summary()
            log(f"链上数据: {onchain_summary}")
            send_notification("链上数据提醒", onchain_summary)
        
        if notify_counter_price >= NOTIFY_INTERVAL_PRICE // CHECK_INTERVAL:
            notify_counter_price = 0
            msg = f"当前价格: ${current_price}\n相对基准: {change_percent:+.2f}%\n基准价格: ${base_price}"
            send_notification("价格提醒", msg)
        
        if change_percent <= -THRESHOLD:
            msg = f"买入信号! 价格下跌 {abs(change_percent):.2f}%\n当前价格: ${current_price}\n基准价格: ${base_price}"
            log(f"🔔 {msg}")
            send_notification("买入信号", msg)
            base_price = current_price
            
        elif change_percent >= THRESHOLD:
            msg = f"卖出信号! 价格上涨 {change_percent:.2f}%\n当前价格: ${current_price}\n基准价格: ${base_price}"
            log(f"🔔 {msg}")
            send_notification("卖出信号", msg)
            base_price = current_price
        else:
            log(f"{SYMBOL}: ${current_price} ({change_percent:+.2f}%)")
        
    except Exception as e:
        log(f"错误: {e}")
    
    time.sleep(CHECK_INTERVAL)
