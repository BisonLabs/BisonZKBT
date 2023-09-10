import hashlib
import json
from datetime import datetime
import subprocess
from flask_restful import Resource
from flask import request
from models import TempTransaction, Balance,Status,Proof,db  # 请根据你的应用程序结构调整导入路径
from inside_transfer import transfer_funds
from proof_manager import record_proof
import configparser
from config import get_status
import requests


config = configparser.ConfigParser()
config.read('config.ini')
tick_value = config['contract_info']['tick_value']
bison_sequencer_url = config['Bison_sequencer']['url']


def generate_hash(method, quoteID, expiry, tick1, contractAddress1, amount1, tick2, contractAddress2, amount2, makerAddr, takerAddr, makerSig, takerSig):
    content = f"{method}{quoteID}{expiry}{tick1}{contractAddress1}{amount1}{tick2}{contractAddress2}{amount2}{makerAddr}{takerAddr}{makerSig}{takerSig}".encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def prepare_swap(method, quoteID, expiry, tick1, contractAddress1, amount1, tick2, contractAddress2, amount2, makerAddr, takerAddr, makerSig, takerSig):
    temp_transaction = TempTransaction(
        hash=generate_hash(method, quoteID, expiry, tick1, contractAddress1, amount1, tick2, contractAddress2, amount2, makerAddr, takerAddr, makerSig, takerSig),
        method=method,
        quoteID=quoteID,
        expiry=expiry,
        tick1=tick1,
        contractAddress1=contractAddress1,
        amount1=amount1,
        tick2=tick2,
        contractAddress2=contractAddress2,
        amount2=amount2,
        makerAddr=makerAddr,
        takerAddr=takerAddr,
        makerSig=makerSig,
        takerSig=takerSig
    )
    db.session.add(temp_transaction)
    db.session.commit()
    return True, temp_transaction.hash


def commit_swap(hash_value):
    # 找到对应的临时交易记录
    temp_transaction = TempTransaction.query.filter_by(hash=hash_value).first()

    # 检查是否找到了记录
    if temp_transaction is None:
        return False, "TempTransaction not found"

    # 在这里可以执行实际的交换操作，例如，调用transfer_funds函数
    # 根据tick值选择正确的交换参数
    sender_address, receiver_address, amount_to_transfer = (
        (temp_transaction.makerAddr, temp_transaction.takerAddr, temp_transaction.amount1)
        if temp_transaction.tick1 == tick_value
        else (temp_transaction.takerAddr, temp_transaction.makerAddr, temp_transaction.amount2)
    )

    success, message = transfer_funds(sender_address, receiver_address, amount_to_transfer)
    if not success:
        return False, message

    # 删除或更新临时交易记录，根据你的业务逻辑进行选择
    # 例如，以下代码将删除记录
    db.session.delete(temp_transaction)
    db.session.commit()

    current_status_num = get_status()

    # 可以在此处调用record_proof来存储证明
    record_proof(current_status_num,"swap", quoteID=temp_transaction.quoteID, expiry=temp_transaction.expiry,
                 tick1=temp_transaction.tick1, contractAddress1=temp_transaction.contractAddress1,
                 amount1=temp_transaction.amount1, tick2=temp_transaction.tick2,
                 contractAddress2=temp_transaction.contractAddress2, amount2=temp_transaction.amount2,
                 makerAddr=temp_transaction.makerAddr, takerAddr=temp_transaction.takerAddr,
                 makerSig=temp_transaction.makerSig, takerSig=temp_transaction.takerSig)

    return True, "Swap committed successfully"



def rollback_swap(hash):
    temp_transaction = TempTransaction.query.filter_by(hash=hash).first()
    if temp_transaction:
        # 删除临时交易，撤销交换
        db.session.delete(temp_transaction)
        db.session.commit()
        return True, "Swap rolled back"
    return False, "Swap rollback failed"



class PrepareSwapResource(Resource):
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
        if (tick_value != tick1) and (tick_value != tick2):
            return {"error": "invalid tick value"}, 400
        
        # 使用prepare_swap替代直接转账
        success, transaction_hash = prepare_swap(method, quoteID, expiry, tick1, contractAddress1, amount1, tick2, contractAddress2, amount2, makerAddr, takerAddr, makerSig, takerSig)
        if not success:
            return {"error": "Failed to prepare the swap"}, 400

        return {"status": "swap prepared", "transaction_hash": transaction_hash}, 200

class CommitSwapResource(Resource):
    def post(self, hash_value):
        success, message = commit_swap(hash_value)
        if success:
            return {"status": "Swap committed successfully", "hash": hash_value}, 200
        else:
            return {"error": message}, 400
        

class RollbackSwapResource(Resource):
    def post(self, hash_value):
        success, message = rollback_swap(hash_value)  # 你需要定义这个函数
        if success:
            return {"status": "Swap rolled back successfully", "hash": hash_value}, 200
        else:
            return {"error": message}, 400


class TransferResource(Resource):
    def post(self):
        json_data = request.get_json(force=True)
        method = json_data.get('method')
        tick = json_data.get('tick')
        senderAddress = json_data.get('sAddr')
        receiptAddress = json_data.get('rAddr')
        amount = json_data.get('amt')
        signature = json_data.get('sig')
        nonce = json_data.get("nonce")
        tokenContractAddress = json_data.get("tokenContractAddress")
        gas_estimated = json_data.get("gas_estimated")
        gas_estimated_hash = json_data.get("gas_estimated_hash")



# 使用HTTP请求来获取指定地址的nonce
        response = requests.get(f"{bison_sequencer_url}/nonce/{senderAddress}")
        if response.status_code != 200:
            return {"error": "Failed to fetch nonce from bison sequencer"}, 500

# 获取API返回的nonce
        api_nonce = response.json().get('nonce')


# 比较从API获取的nonce和json中的nonce是否一致
        if (api_nonce+1) != int(nonce):
            return {"error": "Mismatched nonce value"}, 400
        # Get Message
        message = json.dumps({
            "method": method,
            "sAddr": senderAddress,
            "rAddr": receiptAddress,
            "amt": amount,
            "tick": tick,
            "nonce": int(nonce),
            "tokenContractAddress": tokenContractAddress,
            "sig": "",
            "gas_estimated": int(gas_estimated),
            "gas_estimated_hash": gas_estimated_hash
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
                    current_status_num = get_status()

                    record_proof(current_status_num,method,tick = tick, senderAddress=senderAddress, receiptAddress=receiptAddress, amount=amount, signature=signature)

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