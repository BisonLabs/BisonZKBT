from flask import Flask
from flask_restful import Api
from flask_cors import CORS
import json
from models import db  # import database models
import os
import glob
from threading import Timer
from exportDB import export_balances_to_json
from zkProofGenerator import zkProofGenerator
from OrdinalsInput import OrdinalInput
from updateOrdinalSync import updateOrdinalSync
import configparser
from database_init import initialize_database
from config import get_status, set_status
from standard_modules import TransferResource, BalanceResource, NewestStatusResource, NewestProofResource, PrepareSwapResource, CommitSwapResource, RollbackSwapResource




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

# Initialize statusNum using the config module
status_files = sorted(glob.glob(os.path.abspath(os.getcwd()) + "/status/status*.json"), key=lambda name: int(os.path.basename(name)[6:-5]))
initial_status_num = int(os.path.basename(status_files[-1])[6:-5])  # Get the max status number
set_status(initial_status_num)

# Load the latest status file
with open(status_files[-1], 'r') as f:
    data = json.load(f)

# Update the database according to the latest status file
initialize_database(app, data)


        
def schedule_export_db(interval):
    # Use the config module to access statusNum
    current_status_num = get_status()
    new_status_num = current_status_num + 1
    set_status(new_status_num)

    with app.app_context():
        updateOrdinalSync()

    Timer(interval, schedule_export_db, [interval]).start()  # Schedule the next call

    proof_path = os.path.abspath(os.getcwd()) + f"/statusProof/proof_{new_status_num}.json"
    
    # Check if the proof file exists
    if not os.path.exists(proof_path):
        # Create a new file with empty transactions list
        data = {"p": "BisonRawProof", "statusNum": str(new_status_num), "transactions": []}
        with open(proof_path, 'w') as f:
            json.dump(data, f, indent=4)

    with app.app_context():
        export_balances_to_json(new_status_num)  # Run the function
        zkProofGenerator()  # Generate zero knowledge proof

api.add_resource(TransferResource, '/transfer')
api.add_resource(BalanceResource, '/balance')
api.add_resource(NewestStatusResource, '/newest_status')
api.add_resource(NewestProofResource, '/newest_proof')
api.add_resource(PrepareSwapResource, '/prepare_swap')
api.add_resource(CommitSwapResource, '/commit_swap/<string:hash_value>')
api.add_resource(RollbackSwapResource, '/rollback_swap/<string:hash_value>')


if __name__ == '__main__':

    schedule_export_db(int(config['other']['interval'])) # Every 600 seconds
    app.run(host=config['server']['host'], port=int(config['server']['port']))
