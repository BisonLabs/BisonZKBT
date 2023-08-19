import json
import subprocess
from collections import defaultdict
import glob
import re
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
tick_value = config['contract_info']['tick_value']

def sort_by_number(files):
    return sorted(files, key=lambda x: int(re.search(r'\d+', x).group(0)))

def get_status_data(file):
    with open(file, 'r') as f:
        status_data = json.load(f)
    return status_data['Data']

def compute_diff(status1, status2):
    diff = defaultdict(int)
    for status in status1:
        diff[status['address']] -= status['amount']
    for status in status2:
        diff[status['address']] += status['amount']
    return diff

def get_transactions_data(file):
    with open(file, 'r') as f:
        transactions_data = json.load(f)
    return transactions_data['transactions']

def verify_signatures(file):
    transactions = get_transactions_data(file)
    valid = defaultdict(int)
    for tx in transactions:
        method = tx['method']
        if method == "transfer":
            senderAddress = tx['sAddr']
            receiptAddress = tx['rAddr']
            amount = tx['amt']
            tick = tx['tick']
            signature = tx['sig']
            message = json.dumps({
                "method": method,
                "sAddr": senderAddress,
                "rAddr": receiptAddress,
                "amt": amount,
                "tick": tick,
                "sig": ""
            }, separators=(',', ':'))
            process = subprocess.run(['node', './bisonappbackend_nodejs/bip322Verify.js', senderAddress, message, signature], text=True, capture_output=True)
            result = process.stdout.strip() 
            #print(result)
            if result == 'true':
                valid[tx['sAddr']] -= int(amount)
                valid[tx['rAddr']] += int(amount)

        elif method == "swap":
            maker_message = json.dumps({
                "method": "swap",
                "quoteID": tx['quoteID'],
                "expiry": tx['expiry'],
                "tick1": tx['tick1'],
                "contractAddress1": tx['contractAddress1'],
                "amount1": tx['amount1'],
                "tick2": tx['tick2'],
                "contractAddress2": tx['contractAddress2'],
                "amount2": tx['amount2'],
                "makerAddr": tx['makerAddr'],
                "takerAddr": "",
            }, separators=(',', ':'))
            taker_message = maker_message.replace('"takerAddr": ""', f'"takerAddr": "{tx["takerAddr"]}"')
            maker_result = subprocess.run(['node', './bisonappbackend_nodejs/bip322Verify.js', tx['makerAddr'], maker_message, tx['makerSig']], text=True, capture_output=True).stdout.strip()
            taker_result = subprocess.run(['node', './bisonappbackend_nodejs/bip322Verify.js', tx['takerAddr'], taker_message, tx['takerSig']], text=True, capture_output=True).stdout.strip()

            if maker_result == 'true' and taker_result == 'true':
                if tick_value == tx['tick1']:
                    valid[tx['makerAddr']] -= tx['amount1']
                    valid[tx['takerAddr']] += tx['amount1']
                elif tick_value == tx['tick2']:
                    valid[tx['makerAddr']] += tx['amount2']
                    valid[tx['takerAddr']] -= tx['amount2']  

    return valid

def print_balances(diff, description):
    balances = [v for k, v in sorted(diff.items())]
    print(description)
    print(balances)

def write_json(diff1, diff2, all_addresses):
    data = {
        "status_change_list": [diff1.get(addr, 0) for addr in all_addresses],
        "transaction_change_list": [diff2.get(addr, 0) for addr in all_addresses]
    }
    with open('zk_tmp.json', 'w') as f:
        json.dump(data, f)

def updateZKtmp():
    status_files = glob.glob('./status/*.json')
    proof_files = glob.glob('./statusProof/*.json')
    status_files = sort_by_number(status_files)
    proof_files = sort_by_number(proof_files)
    latest_status_file = status_files[-1]
    previous_status_file = status_files[-2]

    latest_proof_file = proof_files[-1]

    status1_data = get_status_data(previous_status_file)
    status2_data = get_status_data(latest_status_file)
    all_addresses = {tx['address'] for tx in status1_data + status2_data}

    status_diff = compute_diff(status1_data, status2_data)
    tx_diff = verify_signatures(latest_proof_file)

    #print_balances(status_diff, "Status balances changes:")
    #print_balances(tx_diff, "Transaction balance changes:")
    write_json(status_diff, tx_diff, all_addresses)

if __name__ == '__main__':
    updateZKtmp()
