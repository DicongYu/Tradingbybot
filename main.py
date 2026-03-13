import time
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, '/home/dcy/OkxTrading')
import monitor_okx
import monitor_onchain

LOG_FILE = '/home/dcy/OkxTrading/monitor.log'

CHECK_INTERVAL = 60
SYMBOL = 'ETH/USDT'
THRESHOLD = 2

NOTIFY_INTERVALS = {
    'price': 20 * 60,
    'onchain': 5 * 60,
}

class AlertManager:
    def __init__(self):
        self.counters = {key: 0 for key in NOTIFY_INTERVALS}
        self.last_price = None
        self.base_price = None
    
    def check(self, current_price, onchain_data):
        alerts = []
        
        self.counters['price'] += 1
        self.counters['onchain'] += 1
        
        change_percent = 0
        if self.base_price:
            change_percent = (current_price - self.base_price) / self.base_price * 100
        
        if self.counters['onchain'] >= NOTIFY_INTERVALS['onchain'] // CHECK_INTERVAL:
            self.counters['onchain'] = 0
            alerts.append({
                'type': 'onchain',
                'title': '链上数据提醒',
                'message': self._format_onchain(onchain_data)
            })
        
        if self.counters['price'] >= NOTIFY_INTERVALS['price'] // CHECK_INTERVAL:
            self.counters['price'] = 0
            base_str = f"${self.base_price:.2f}" if self.base_price else "未设置"
            alerts.append({
                'type': 'price',
                'title': '价格提醒',
                'message': f"当前: ${current_price}\n相对基准: {change_percent:+.2f}%\n基准: {base_str}"
            })
        
        if self.base_price and change_percent <= -THRESHOLD:
            alerts.append({
                'type': 'buy',
                'title': '买入信号',
                'message': f"下跌 {abs(change_percent):.2f}%\n当前: ${current_price}\n基准: ${self.base_price:.2f}"
            })
            self.base_price = current_price
            
        elif self.base_price and change_percent >= THRESHOLD:
            alerts.append({
                'type': 'sell',
                'title': '卖出信号',
                'message': f"上涨 {change_percent:.2f}%\n当前: ${current_price}\n基准: ${self.base_price:.2f}"
            })
            self.base_price = current_price
        
        if self.base_price is None:
            self.base_price = current_price
        
        return alerts, change_percent
    
    def _format_onchain(self, data):
        gas = data.get('eth_gas') or {}
        btc = data.get('btc_network') or {}
        txs = data.get('large_txs') or {}
        
        parts = []
        if gas:
            parts.append(f"Gas: {gas.get('propose', 'N/A')} Gwei")
        if btc:
            parts.append(f"BTC: ${btc.get('market_price', 0):,.0f}")
        if txs.get('btc'):
            parts.append(f"大额: {len(txs['btc'])}笔")
        
        return " | ".join(parts) if parts else "数据获取中..."

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')

def send_notification(title, message):
    subprocess.run(['notify-send', title, message], capture_output=True)
    subprocess.run(['paplay', '/usr/share/sounds/LinuxMint/stereo/dialog-information.ogg'], capture_output=True)

def main():
    log("=" * 60)
    log("交易所+链上监控启动")
    log(f"监控品种: {SYMBOL}")
    log(f"提醒间隔: 价格{NOTIFY_INTERVALS['price']//60}分钟 | 链上{NOTIFY_INTERVALS['onchain']//60}分钟")
    log(f"交易阈值: ±{THRESHOLD}%")
    log("=" * 60)
    
    try:
        ticker = monitor_okx.get_ticker(SYMBOL)
        base_price = ticker['last']
        log(f"基准价格: ${base_price}")
    except Exception as e:
        log(f"获取价格失败: {e}")
        base_price = None
    
    send_notification("监控已启动", f"{SYMBOL} 基准: ${base_price}")
    
    alert_mgr = AlertManager()
    if base_price:
        alert_mgr.base_price = base_price
    
    while True:
        try:
            ticker = monitor_okx.get_ticker(SYMBOL)
            current_price = ticker['last']
            
            onchain_data = monitor_onchain.get_all_onchain_data()
            
            alerts, change_percent = alert_mgr.check(current_price, onchain_data)
            
            for alert in alerts:
                log(f"🔔 {alert['title']}: {alert['message'].replace(chr(10), ' | ')}")
                send_notification(alert['title'], alert['message'])
            
            if not alerts:
                log(f"{SYMBOL}: ${current_price} ({change_percent:+.2f}%)")
            
        except Exception as e:
            log(f"错误: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
