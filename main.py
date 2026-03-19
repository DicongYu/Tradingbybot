import time
import subprocess
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

sys.path.insert(0, '/home/dcy/OkxTrading')
import monitor_okx
import monitor_onchain

LOG_DIR = '/home/dcy/OkxTrading'
LOG_FILE = f'{LOG_DIR}/monitor.log'

CHECK_INTERVAL = 60
SYMBOL = 'ETH/USDT'
THRESHOLD = 2

NOTIFY_INTERVALS = {
    'price': 20 * 60,
    'onchain': 5 * 60,
    'balance': 30 * 60,
}

class AlertManager:
    def __init__(self):
        self.counters = {key: 0 for key in NOTIFY_INTERVALS}
        self.last_price = None
        self.base_price = None
        self.last_balance = None
    
    def check(self, current_price, onchain_data, balance_data=None):
        alerts = []
        
        self.counters['price'] += 1
        self.counters['onchain'] += 1
        if balance_data:
            self.counters['balance'] += 1
        
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
        
        if balance_data and self.counters['balance'] >= NOTIFY_INTERVALS['balance'] // CHECK_INTERVAL:
            self.counters['balance'] = 0
            alerts.append({
                'type': 'balance',
                'title': '账户资产',
                'message': self._format_balance(balance_data)
            })
        
        if self.base_price is None:
            self.base_price = current_price
        
        return alerts, change_percent
    
    def _format_onchain(self, data):
        gas = data.get('eth_gas') or {}
        btc = data.get('btc_network') or {}
        txs = data.get('large_txs') or {}
        
        parts = []
        if gas and gas.get('propose'):
            gas_val = gas['propose']
            if gas_val < 20:
                gas_status = "便宜"
            elif gas_val <= 50:
                gas_status = "正常"
            else:
                gas_status = "拥堵"
            parts.append(f"Gas: {gas_val:.1f} Gwei ({gas_status})")
        if btc:
            parts.append(f"BTC: ${btc.get('market_price', 0):,.0f}")
            parts.append(f"交易: {btc.get('tx_count', 0):,.0f}")
        if txs.get('btc'):
            buy_count = sum(1 for tx in txs['btc'] if tx.get('direction') == '买入')
            sell_count = sum(1 for tx in txs['btc'] if tx.get('direction') == '卖出')
            unknown_count = len(txs['btc']) - buy_count - sell_count
            direction_info = []
            if buy_count > 0:
                direction_info.append(f"↑买入{buy_count}")
            if sell_count > 0:
                direction_info.append(f"↓卖出{sell_count}")
            if unknown_count > 0:
                direction_info.append(f"?未知{unknown_count}")
            parts.append(f"大额: {len(txs['btc'])}笔 ({' '.join(direction_info)})")
        
        return " | ".join(parts) if parts else "数据获取中..."
    
    def _format_balance(self, data):
        parts = []
        if data.get('total_usd'):
            parts.append(f"总: ${data['total_usd']:,.2f}")
        if data.get('ETH'):
            parts.append(f"ETH: {data['ETH']:.4f}")
        if data.get('BTC'):
            parts.append(f"BTC: {data['BTC']:.6f}")
        if data.get('USDT'):
            parts.append(f"USDT: {data['USDT']:.2f}")
        return " | ".join(parts) if parts else "获取失败"

def setup_logging():
    logger = logging.getLogger('monitor')
    logger.setLevel(logging.INFO)
    
    handler = TimedRotatingFileHandler(
        LOG_FILE,
        when='midnight',
        interval=1,
        backupCount=9999,
        encoding='utf-8'
    )
    handler.suffix = '%Y-%m-%d'
    
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger

logger = setup_logging()

def log(msg):
    print(msg, flush=True)
    logger.info(msg)

def send_notification(title, message):
    subprocess.run(['notify-send', title, message], capture_output=True)
    subprocess.run(['paplay', '/usr/share/sounds/LinuxMint/stereo/dialog-information.ogg'], capture_output=True)

def main():
    log("=" * 60)
    log("交易所+链上监控启动")
    log(f"监控品种: {SYMBOL}")
    log(f"提醒间隔: 价格{NOTIFY_INTERVALS['price']//60}分钟 | 链上{NOTIFY_INTERVALS['onchain']//60}分钟 | 资产{NOTIFY_INTERVALS['balance']//60}分钟")
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
    
    balance_data = None
    try:
        balance_data = monitor_okx.get_balance()
        if balance_data:
            log(f"账户资产: {alert_mgr._format_balance(balance_data)}")
    except Exception as e:
        log(f"获取余额失败: {e}")
    
    onchain_data = None
    try:
        onchain_data = monitor_onchain.get_all_onchain_data(force_refresh=True)
        if onchain_data:
            log(f"链上数据: {alert_mgr._format_onchain(onchain_data)}")
    except Exception as e:
        log(f"获取链上数据失败: {e}")
    
    log("=" * 60)
    log("启动测试: 模拟各提醒")
    
    if base_price and onchain_data:
        test_price = base_price * 1.03
        alert_mgr.counters['price'] = NOTIFY_INTERVALS['price'] // CHECK_INTERVAL
        alerts, _ = alert_mgr.check(test_price, onchain_data, balance_data)
        for a in alerts:
            if a['type'] == 'price':
                log(f"🔔 测试-价格提醒: {a['message'].replace(chr(10), ' | ')}")
                send_notification(a['title'], a['message'])
        
        alert_mgr.counters['onchain'] = NOTIFY_INTERVALS['onchain'] // CHECK_INTERVAL
        alerts, _ = alert_mgr.check(base_price, onchain_data, balance_data)
        for a in alerts:
            if a['type'] == 'onchain':
                log(f"🔔 测试-链上提醒: {a['message'].replace(chr(10), ' | ')}")
                send_notification(a['title'], a['message'])
        
        if balance_data:
            alert_mgr.counters['balance'] = NOTIFY_INTERVALS['balance'] // CHECK_INTERVAL
            alerts, _ = alert_mgr.check(base_price, onchain_data, balance_data)
            for a in alerts:
                if a['type'] == 'balance':
                    log(f"🔔 测试-资产提醒: {a['message'].replace(chr(10), ' | ')}")
                    send_notification(a['title'], a['message'])
    
    log("=" * 60)
    log("启动完成，进入监控")
    
    while True:
        try:
            ticker = monitor_okx.get_ticker(SYMBOL)
            current_price = ticker['last']
            
            onchain_data = monitor_onchain.get_all_onchain_data()
            
            alerts, change_percent = alert_mgr.check(current_price, onchain_data, balance_data)
            
            for alert in alerts:
                log(f"🔔 {alert['title']}: {alert['message'].replace(chr(10), ' | ')}")
                send_notification(alert['title'], alert['message'])
            
            if not alerts:
                log(f"{SYMBOL}: ${current_price} ({change_percent:+.2f}%)")
            
            if balance_data is None:
                try:
                    balance_data = monitor_okx.get_balance()
                except:
                    pass
            
        except Exception as e:
            log(f"错误: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
