from flask import Flask, request
from flask_restful import Resource, Api
from flask_cors import CORS
import json
import subprocess  
from models import db, Balance,Status,Proof  # import database models
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

def record_proof(method, tick, senderAddress, receiptAddress, amount, signature):
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
    data["transactions"].append({
        "method": method,
        "tick": tick,
        "sAddr": senderAddress,
        "rAddr": receiptAddress,
        "amt": amount,
        "sig": signature
    })

    # Write back to the file
    with open(proof_path, 'w') as f:
        json.dump(data, f, indent=4)

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
        
        process = subprocess.run(['node', './bisonappbackend_nodejs/bip322Verify.js', senderAddress, message, signature], text=True, capture_output=True)
        result = process.stdout.strip()  # Return result

        print(result)
        if result == 'true':  
            if method == 'transfer':
                # Balance check here
                sender_balance = Balance.query.filter_by(address=senderAddress).first()
                if sender_balance and sender_balance.amount >= int(amount):
                    # Creat a new address if not exist yet
                    receipt_balance = Balance.query.filter_by(address=receiptAddress).first()
                    if receipt_balance is None:
                        receipt_balance = Balance(address=receiptAddress, amount=0)
                        db.session.add(receipt_balance)

                    # Actual transfer
                    sender_balance.amount -= int(amount)
                    receipt_balance.amount += int(amount)
                    db.session.commit()

                    record_proof(method, tick, senderAddress, receiptAddress, amount, signature)
                    
                    if receiptAddress == 'tb1ptw39pxy2stdlexwutfjwak7c8u6tnzut80dtwt8fmqfdzpd60nfqsejr7m':
                        tmpres = send_bitcoin(senderAddress,int(amount)/10000,2)
                        print(tmpres)

                    return {"status": "transfer successful", 
                            "from": senderAddress, 
                            "to": receiptAddress, 
                            "amount": amount, 
                            "signature": signature}, 200
                else:
                    return {"error": "insufficient balance"}, 400
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


if __name__ == '__main__':

    schedule_export_db(int(config['other']['interval'])) # Every 600 seconds
    app.run(host=config['server']['host'], port=int(config['server']['port']))
