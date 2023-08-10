from models import db, Balance
from flask import Flask
import os
import json

app = Flask(__name__)
file_path = os.path.abspath(os.getcwd())+"/db/bison.db"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+file_path
db.init_app(app) 

def export_balances_to_json(statusNum):
    balances = Balance.query.all()
    balance_list = []
    for balance in balances:
        balance_dict = {
            'address': balance.address,
            'amount': balance.amount
        }
        balance_list.append(balance_dict)
    
    # Add extra fields
    output = {
        "p": "BisonStatus",
        "rawProof": "",
        "ContractName": "ZKBT",
        "ContractAddr": "tb1pam7razjc7647hthazkqzlycm78hr2ety0cxqaktc3suywm03x56s8y4hmg",
        "Version": "Bison0.1",
        "statusNum": statusNum,
        "Data": balance_list
    }
    
    # Write to the file

    file_path = os.path.abspath(os.getcwd())+"/status/status"+str(statusNum)+".json"

    with open(file_path, 'w') as f:
        json.dump(output, f, indent=4)



