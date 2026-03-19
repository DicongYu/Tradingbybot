import requests
import time
import subprocess
import os
from datetime import datetime

LOG_FILE = '/home/dcy/OkxTrading/monitor.log'

CHECK_INTERVAL = 60
NOTIFY_INTERVAL = 5

ETHERSCAN_API_KEY = os.environ.get('ETHERSCAN_API_KEY', '')

PROXIES = {
    'http': 'http://127.0.0.1:20171',
    'https': 'http://127.0.0.1:20171'
}

ACTIVE_ADDRESS_THRESHOLD = 0.20
GAS_THRESHOLD = 0.30
LARGE_TX_THRESHOLD = 100

last_data = {
    'btc_active': None,
    'eth_active': None,
    'eth_gas': None,
    'btc_fees': None
}

cached_data = {
    'eth_gas': None,
    'btc_network': None,
    'large_txs': None,
    'timestamp': None
}
CACHE_TTL = 30

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')

def send_notification(title, message):
    subprocess.run(['notify-send', title, message], capture_output=True)
    subprocess.run(['paplay', '/usr/share/sounds/LinuxMint/stereo/dialog-information.ogg'], capture_output=True)

def get_btc_network_data():
    try:
        resp = requests.get('https://api.blockchain.info/stats', timeout=10)
        data = resp.json()
        return {
            'market_price': data.get('market_price_usd', 0),
            'tx_count': data.get('n_tx', 0),
            'difficulty': data.get('difficulty', 0)
        }
    except Exception as e:
        log(f"BTC network error: {e}")
    return None

def get_eth_gas_price():
    if not ETHERSCAN_API_KEY:
        return None
    try:
        url = f"https://api.etherscan.io/v2/api?chainid=1&module=gastracker&action=gasoracle&apikey={ETHERSCAN_API_KEY}"
        resp = requests.get(url, timeout=10, proxies=PROXIES)
        data = resp.json()
        if data.get('status') == '1' and data.get('result'):
            result = data['result']
            return {
                'safe': float(result.get('SafeGasPrice', 0)),
                'propose': float(result.get('ProposeGasPrice', 0)),
                'fast': float(result.get('FastGasPrice', 0)),
                'avg': float(result.get('ProposeGasPrice', result.get('SafeGasPrice', 0)))
            }
    except Exception as e:
        log(f"Gas error: {e}")
    return None

def get_large_transfers():
    result = {'btc': [], 'eth': []}
    
    try:
        resp = requests.get('https://blockchain.info/unconfirmed-transactions?format=json', timeout=10)
        data = resp.json()
        for tx in data.get('txs', [])[:30]:
            total_out = sum(out.get('value', 0) for out in tx.get('out', []))
            if total_out > LARGE_TX_THRESHOLD * 1e8:
                direction = analyze_btc_direction(tx)
                result['btc'].append({
                    'hash': tx['hash'],
                    'amount': total_out / 1e8,
                    'fee': tx.get('fee', 0) / 1e8,
                    'direction': direction,
                    'inputs': len(tx.get('inputs', [])),
                    'outputs': len(tx.get('out', []))
                })
    except Exception as e:
        log(f"BTC large tx error: {e}")
    
    return result

def analyze_btc_direction(tx):
    """分析BTC交易方向"""
    known_exchange_prefixes = {
        '1Kraken', '1Coinbase', '1Bittrex', '1Bitfinex', '1Bitstamp',
        '3A', '3B', '3C', '3D', '3E', '3F', '3L', '3M', 'bc1qb', 'bc1qc',
        '1ML', '1ND', '1AX', '1AY', '1AZ', '1Bx', '1By', '1Bz',
        '3AnX', '3AnY', '3AnZ', '3K', '3L', '3M'
    }
    
    inputs = tx.get('inputs', [])
    outputs = tx.get('out', [])
    
    input_addresses = []
    for inp in inputs:
        prev_out = inp.get('prev_out', {})
        addr = prev_out.get('addr', '')
        if addr:
            input_addresses.append(addr)
    
    output_addresses = []
    for out in outputs:
        addr = out.get('addr', '')
        if addr:
            output_addresses.append(addr)
    
    exchange_in_count = sum(1 for addr in output_addresses if any(addr.startswith(p) for p in known_exchange_prefixes))
    exchange_out_count = sum(1 for addr in input_addresses if any(addr.startswith(p) for p in known_exchange_prefixes))
    
    if exchange_in_count > 0:
        return "买入"
    elif exchange_out_count > 0:
        return "卖出"
    else:
        return "未知"

def get_all_onchain_data(force_refresh=False):
    global cached_data
    
    now = time.time()
    cached_ts = cached_data.get('timestamp')
    if not force_refresh and cached_ts is not None:
        if now - cached_ts < CACHE_TTL:
            return cached_data
    
    gas_data = get_eth_gas_price()
    btc_data = get_btc_network_data()
    large_txs = get_large_transfers()
    
    cached_data = {
        'eth_gas': gas_data,
        'btc_network': btc_data,
        'large_txs': large_txs,
        'timestamp': now
    }
    
    return cached_data

def get_onchain_summary():
    data = get_all_onchain_data()
    gas = data.get('eth_gas') or {}
    btc = data.get('btc_network') or {}
    txs = data.get('large_txs') or {}
    
    summary = []
    if gas:
        summary.append(f"ETH Gas: {gas.get('propose', 'N/A')} Gwei")
    if btc:
        summary.append(f"BTC: ${btc.get('market_price', 0):,.0f}")
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
        summary.append(f"BTC大额: {len(txs['btc'])}笔 ({' '.join(direction_info)})")
    
    return " | ".join(summary) if summary else "数据获取中..."

def check_and_notify(key, current, threshold, title_prefix, format_fn):
    global last_data
    
    last = last_data.get(key)
    if last is None or current is None:
        last_data[key] = current
        return False
    
    if last > 0:
        change = (current - last) / last
        if abs(change) > threshold:
            direction = "激增" if change > 0 else "骤降"
            msg = format_fn(current, change)
            send_notification(f"{title_prefix} {direction}", msg)
            log(f"🔔 {title_prefix} {direction}: {change*100:+.1f}%")
            last_data[key] = current
            return True
    
    last_data[key] = current
    return False

def run_monitor():
    counter = 0
    
    while True:
        try:
            counter += 1
            log("=" * 50)
            log(f"第 {counter} 次链上数据检查")
            
            gas_data = get_eth_gas_price()
            if gas_data:
                log(f"ETH Gas | Safe: {gas_data['safe']} | Propose: {gas_data['propose']} | Fast: {gas_data['fast']}")
                check_and_notify('eth_gas', gas_data['propose'], GAS_THRESHOLD,
                    "ETH Gas", lambda c, ch: f"Propose: {c} Gwei\n变化: {ch*100:+.1f}%")
            
            btc_data = get_btc_network_data()
            if btc_data:
                log(f"BTC 网络 | 价格: ${btc_data['market_price']:,.0f} | 交易数: {btc_data['tx_count']:,.0f}")
                if btc_data.get('tx_count'):
                    check_and_notify('btc_active', btc_data['tx_count'], ACTIVE_ADDRESS_THRESHOLD,
                        "BTC活跃度", lambda c, ch: f"交易数: {c:,.0f}\n变化: {ch*100:+.1f}%")
            
            large_txs = get_large_transfers()
            if large_txs.get('btc'):
                log(f"BTC 大额转账: {len(large_txs['btc'])} 笔")
                for tx in large_txs['btc'][:3]:
                    direction = tx.get('direction', '未知')
                    direction_emoji = "📈" if direction == "买入" else "📉" if direction == "卖出" else "❓"
                    log(f"  {direction_emoji} {tx['amount']:.2f} BTC ({direction})")
            
            if counter % NOTIFY_INTERVAL == 0:
                summary = get_onchain_summary()
                send_notification("链上数据摘要", summary)
                log("已发送定期摘要通知")
                
        except Exception as e:
            log(f"监控错误: {e}")
        
        time.sleep(CHECK_INTERVAL)

def main():
    log("=" * 60)
    log("链上数据服务启动")
    log(f"检查间隔: {CHECK_INTERVAL}秒")
    log(f"通知频率: 每{NOTIFY_INTERVAL}次检查发送摘要")
    log("=" * 60)
    
    send_notification("链上监控服务", "链上数据获取服务已开启")
    
    run_monitor()

if __name__ == '__main__':
    main()
