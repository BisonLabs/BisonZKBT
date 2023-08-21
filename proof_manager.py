import json
import os
def record_proof(statusNum,method, **kwargs):
    # Use the global statusNum
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
