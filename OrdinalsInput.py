import subprocess
import json
import requests
import os
import shutil
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

def delete_files():
    folders_to_clear = ['./status', './statusProof', './db','./zkProof']
    for folder in folders_to_clear:
        try:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        except FileNotFoundError:
            print(f"{folder} not found. Skipping...")

def fetch_inscriptions():
    wallet_name = config['contract_info']['wallet_name']
    command = ["ord", "--testnet", "--wallet", wallet_name, "wallet", "inscriptions"]
    result = subprocess.run(command, stdout=subprocess.PIPE)
    output = result.stdout.decode()
    inscriptions = json.loads(output)
    return inscriptions

def save_content(inscriptions, ordinal_url, contract_name):
    for ins in inscriptions:
        url = f"{ordinal_url}/content/{ins['inscription']}"
        response = requests.get(url)
        
        try:
            content = response.json()
        except json.JSONDecodeError:
            print(f"Non-JSON response from {url}. Skipping...")
            continue

        if content.get('ContractName') != contract_name:
            print(f"Contract name mismatch: expected {contract_name}, got {content.get('ContractName')}. Skipping...")
            continue

        if "statusNum" in content:
            status_num = content['statusNum']
        else:
            continue

        if content.get('p') == "BisonStatus":
            path = f"status/status{status_num}.json"
        elif content.get('p') == "BisonRawProof":
            path = f"statusProof/proof_{status_num}.json"
        else:
            continue

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as file:
            json.dump(content, file, indent=4)

def OrdinalInput():

    ordinal_url = config['ordinal_explorer']['url']
    contract_name = config['contract_info']['contract_name']

    delete_files()
    inscriptions = fetch_inscriptions()
    save_content(inscriptions, ordinal_url, contract_name)
    print('Status synced from Bitcoin.')

#OrdinalInput()
