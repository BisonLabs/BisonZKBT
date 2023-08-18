from flask import Flask, request
from flask_restful import Resource, Api
from flask_cors import CORS
import json
import subprocess  
from models import db, Balance,Status,Proof,TempTransaction  # import database models
import os
import glob
from threading import Timer
from exportDB import export_balances_to_json
from zkProofGenerator import zkProofGenerator
from OrdinalsOutput import inscribe_to_bitcoin
from OrdinalsInput import OrdinalInput
from sendBitcoin import send_bitcoin
from updateOrdinalSync import updateOrdinalSync
import configparser
from datetime import datetime


config = configparser.ConfigParser()
config.read('config.ini')

OrdinalInput()

file_path_bison = os.path.abspath(os.getcwd()) + config['database']['file_path_bison']
file_path_ordinal_sync = os.path.abspath(os.getcwd()) + config['database']['file_path_ordinal_sync']
tick_value = config['contract_info']['tick_value']

app = Flask(__name__)
CORS(app)
api = Api(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + file_path_bison
app.config['SQLALCHEMY_BINDS'] = {
    'bison': 'sqlite:///' + file_path_bison,
    'ordinal_sync': 'sqlite:///' + file_path_ordinal_sync
}


db.init_app(app)  # initiative the database

# Get a list of all status files, sorted by number
status_files = sorted(glob.glob(os.path.abspath(os.getcwd()) + "/status/status*.json"), key=lambda name: int(os.path.basename(name)[6:-5]))

# Initialize statusNum as a global variable
global statusNum
statusNum = int(os.path.basename(status_files[-1])[6:-5])  # Get the max status number

# Load the latest status file
with open(status_files[-1], 'r') as f:
    data = json.load(f)

# Update the database according to the latest status file
with app.app_context():
    db.create_all()  # Create all tables
    for record in data['Data']:
        balance = Balance.query.filter_by(address=record['address']).first()
        if balance is None:
            balance = Balance(address=record['address'], amount=record['amount'])
            db.session.add(balance)
        else:
            balance.amount = record['amount']
    db.session.commit()

def record_proof(method, **kwargs):
    # Use the global statusNum
    global statusNum
    proof_path = os.path.abspath(os.getcwd()) + f"/statusProof/proof_{statusNum+1}.json"

    # Load the existing data
    if os.path.exists(proof_path):
        with open(proof_path, 'r') as f:
            data = json.load(f)
            # Ensure data["transactions"] is a list
            data["transactions"] = data.get("transactions", [])
    else:
        data = {"p": "BisonRawProof", "statusNum": str(statusNum), "transactions": []}

    # Add the new record
    if method == "transfer":
        data["transactions"].append({
            "method": method,
            "tick": kwargs['tick'],
            "sAddr": kwargs['senderAddress'],
            "rAddr": kwargs['receiptAddress'],
            "amt": kwargs['amount'],
            "sig": kwargs['signature']
        })
    elif method == "swap":
        data["transactions"].append({
            "method": method,
            "quoteID": kwargs['quoteID'],
            "expiry": kwargs['expiry'],
            "tick1": kwargs['tick1'],
            "contractAddress1": kwargs['contractAddress1'],
            "amount1": kwargs['amount1'],
            "tick2": kwargs['tick2'],
            "contractAddress2": kwargs['contractAddress2'],
            "amount2": kwargs['amount2'],
            "makerAddr": kwargs['makerAddr'],
            "takerAddr": kwargs['takerAddr'],
            "makerSig": kwargs['makerSig'],
            "takerSig": kwargs['takerSig']
        })

    # Write back to the file
    with open(proof_path, 'w') as f:
        json.dump(data, f, indent=4)


def transfer_funds(sender_address, receiver_address, amount):
    # 查询发送方余额
    sender_balance = Balance.query.filter_by(address=sender_address).first()
    if not sender_balance or sender_balance.amount < int(amount):
        return False, "insufficient balance"

    # 查询接收方余额，如果不存在，则创建
    receiver_balance = Balance.query.filter_by(address=receiver_address).first()
    if receiver_balance is None:
        receiver_balance = Balance(address=receiver_address, amount=0)
        db.session.add(receiver_balance)

    # 实际转账
    sender_balance.amount -= int(amount)
    receiver_balance.amount += int(amount)
    db.session.commit()

    return True, "transfer successful"

def prepare_transfer(sender_address, receiver_address, amount, transaction_hash):
    # 检查余额等
    sender_balance = Balance.query.filter_by(address=sender_address).first()
    if not sender_balance or sender_balance.amount < int(amount):
        return False, "insufficient balance"
    
    # 记录预备交易信息到临时表
    temp_transaction = TempTransaction(hash=transaction_hash, sender=sender_address, receiver=receiver_address, amount=amount)
    db.session.add(temp_transaction)
    db.session.commit()

    return True, "prepared"


class SwapResource(Resource):
    def post(self):
        json_data = request.get_json(force=True)
        
        # 提取交换操作所需的所有信息
        method = json_data.get('method')
        quoteID = json_data.get('quoteID')
        expiry = json_data.get('expiry')
        tick1 = json_data.get('tick1')
        contractAddress1 = json_data.get('contractAddress1')
        amount1 = json_data.get('amount1')
        tick2 = json_data.get('tick2')
        contractAddress2 = json_data.get('contractAddress2')
        amount2 = json_data.get('amount2')
        makerAddr = json_data.get('makerAddr')
        takerAddr = json_data.get('takerAddr')
        makerSig = json_data.get('makerSig')
        takerSig = json_data.get('takerSig')
        
        expiry_time = datetime.fromisoformat(expiry.rstrip("Z"))

        # 确认method是swap
        if method != 'swap':
            return {"error": "invalid method, expected 'swap'"}, 400
        
        # 检查expiry_time是否在当前时间之后
        if expiry_time < datetime.utcnow():
            return {"error": "expired swap request"}, 400
        
        message = json.dumps({
            "method": "swap",
            "quoteID": json_data.get('quoteID'),
            "expiry": json_data.get('expiry'),
            "tick1": json_data.get('tick1'),
            "contractAddress1": json_data.get('contractAddress1'),
            "amount1": json_data.get('amount1'),
            "tick2": json_data.get('tick2'),
            "contractAddress2": json_data.get('contractAddress2'),
            "amount2": json_data.get('amount2'),
            "makerAddr": json_data.get('makerAddr'),
            "takerAddr": "",  # taker地址为空
            # makerSig  和 takerSig 将稍后添加
        }, separators=(',', ':'))
        process = subprocess.run(['node', './bisonappbackend_nodejs/bip322Verify.js', makerAddr, message, makerSig], text=True, capture_output=True)
        result1 = process.stdout.strip()  # 返回结果

        print(result1)
        if result1 != 'true':  
            return {"error": "Invalid signature"}, 400
    
        message = json.dumps({
            "method": "swap",
            "quoteID": json_data.get('quoteID'),
            "expiry": json_data.get('expiry'),
            "tick1": json_data.get('tick1'),
            "contractAddress1": json_data.get('contractAddress1'),
            "amount1": json_data.get('amount1'),
            "tick2": json_data.get('tick2'),
            "contractAddress2": json_data.get('contractAddress2'),
            "amount2": json_data.get('amount2'),
            "makerAddr": json_data.get('makerAddr'),
            "takerAddr": json_data.get('takerAddr'),  
        }, separators=(',', ':'))
        process = subprocess.run(['node', './bisonappbackend_nodejs/bip322Verify.js', takerAddr, message, takerSig], text=True, capture_output=True)
        result2 = process.stdout.strip()  # 返回结果

        print(result2)
        if result2 != 'true':  
            return {"error": "Invalid signature"}, 400
        # 在交换操作成功后，可以返回一个成功的响应，或者在失败时返回一个错误响应



        # 确定处理的 tick
        if tick_value == tick1:
            sender_address = makerAddr
            receiver_address = takerAddr
            amount_to_transfer = amount1
        elif tick_value == tick2:
            sender_address = takerAddr
            receiver_address = makerAddr
            amount_to_transfer = amount2
        else:
            return {"error": "invalid tick value"}, 400
        
        success, message = transfer_funds(sender_address, receiver_address, amount_to_transfer)
        if not success:
            return {"error": message}, 400

        record_proof("swap", quoteID=quoteID, expiry=expiry, tick1=tick1, contractAddress1=contractAddress1, amount1=amount1, tick2=tick2, contractAddress2=contractAddress2, amount2=amount2, makerAddr=makerAddr, takerAddr=takerAddr, makerSig=makerSig, takerSig=takerSig)


        return {"status": "swap successful"}, 200


class TransferResource(Resource):
    def post(self):
        json_data = request.get_json(force=True)
        method = json_data.get('method')
        tick = json_data.get('tick')
        senderAddress = json_data.get('sAddr')
        receiptAddress = json_data.get('rAddr')
        amount = json_data.get('amt')
        signature = json_data.get('sig')

        # Get Message
        message = json.dumps({
            "method": method,
            "sAddr": senderAddress,
            "rAddr": receiptAddress,
            "amt": amount,
            "tick": tick,
            "sig": ""
        }, separators=(',', ':'))

        if tick != tick_value:
            return {"error": "invalid tick value"}, 400
        
        print("Verifing sig")

        process = subprocess.run(['node', './bisonappbackend_nodejs/bip322Verify.js', senderAddress, message, signature], text=True, capture_output=True)
        result = process.stdout.strip()  # Return result

        print(result)

        if result == 'true':  
            if method == 'transfer':
                success, message = transfer_funds(senderAddress, receiptAddress, amount)
                if success:
                    record_proof(method, tick, senderAddress=senderAddress, receiptAddress=receiptAddress, amount=amount, signature=signature)

                    return {"status": message,
                            "from": senderAddress,
                            "to": receiptAddress,
                            "amount": amount,
                            "signature": signature}, 200
                else:
                    return {"error": message}, 400
            else:
                return {"error": "invalid method"}, 400
        else:  # Logic of invalid signature
            return {"error": "invalid signature"}, 400

class BalanceResource(Resource):
    def post(self):
        json_data = request.get_json(force=True)
        address = json_data.get('address')
        balance_record = Balance.query.filter_by(address=address).first()
        if balance_record is not None:
            return {'balance': balance_record.amount}
        else:
            return {'balance': 0}  # return 0 if not exist
        
class NewestStatusResource(Resource):
    def get(self):
        newest_statuses = Status.query.order_by(Status.status_num.desc()).limit(6).all()
        response_data = [{"num": status.status_num, "inscription": status.inscription_id} for status in newest_statuses]
        return response_data

class NewestProofResource(Resource):
    def get(self):
        newest_proofs = Proof.query.order_by(Proof.status_num.desc()).limit(6).all()
        response_data = [{"num": proof.status_num, "inscription": proof.inscription_id} for proof in newest_proofs]
        return response_data

        
def schedule_export_db(interval):
    # Use the global statusNum
    global statusNum

    statusNum += 1
    with app.app_context():
        updateOrdinalSync()

    Timer(interval, schedule_export_db, [interval]).start()  # Schedule the next call
    
    proof_path = os.path.abspath(os.getcwd()) + f"/statusProof/proof_{statusNum}.json"
    # Check if the proof file exists
    if not os.path.exists(proof_path):
        # Create a new file with empty transactions list
        data = {"p": "BisonRawProof", "statusNum": str(statusNum), "transactions": []}
        with open(proof_path, 'w') as f:
            json.dump(data, f, indent=4)

    with app.app_context():
        export_balances_to_json(statusNum)  # Run the function
        zkProofGenerator() # Generate zero knowledge proof

    # Increase statusNum after exporting and generating proof

api.add_resource(TransferResource, '/transfer')
api.add_resource(BalanceResource, '/balance')
api.add_resource(NewestStatusResource, '/newest_status')
api.add_resource(NewestProofResource, '/newest_proof')
api.add_resource(SwapResource, '/swap')



if __name__ == '__main__':

    schedule_export_db(int(config['other']['interval'])) # Every 600 seconds
    app.run(host=config['server']['host'], port=int(config['server']['port']))
