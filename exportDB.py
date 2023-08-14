from models import db, Balance
from flask import Flask
import os
import json
from configparser import ConfigParser

app = Flask(__name__)
config = ConfigParser()
config.read('config.ini')

# 从配置文件中获取数据库文件路径
file_path_bison = os.path.abspath(os.getcwd()) + config['database']['file_path_bison']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + file_path_bison
db.init_app(app)

def export_balances_to_json(statusNum):
    # 获取配置参数
    contract_name = config['contract_info']['contract_name']
    contract_addr = config['contract_info']['contract_addr']
    version = config['contract_info']['version']

    balances = Balance.query.all()
    balance_list = []
    for balance in balances:
        balance_dict = {
            'address': balance.address,
            'amount': balance.amount
        }
        balance_list.append(balance_dict)

    # 使用配置文件中的值
    output = {
        "p": "BisonStatus",
        "rawProof": "",
        "ContractName": contract_name,
        "ContractAddr": contract_addr,
        "Version": version,
        "statusNum": statusNum,
        "Data": balance_list
    }

    # 写入文件
    file_path = os.path.abspath(os.getcwd()) + "/status/status" + str(statusNum) + ".json"

    with open(file_path, 'w') as f:
        json.dump(output, f, indent=4)