import subprocess
import json
import requests
from flask import Flask
from models import Status, Proof,db
import os


def updateOrdinalSync():
    # Fetch inscriptions using a command
    command = ["ord", "--testnet", "wallet", "inscriptions"]
    result = subprocess.run(command, stdout=subprocess.PIPE)
    output = result.stdout.decode()
    inscriptions = json.loads(output)

    # Process and save the inscriptions
    for ins in inscriptions:
        url = f"http://192.168.1.179:8075/content/{ins['inscription']}"
        response = requests.get(url)

        try:
            content = response.json()
        except json.JSONDecodeError:
            print(f"Non-JSON response from {url}. Skipping...")
            continue

        if "statusNum" in content:
            status_num = content['statusNum']
        else:
            continue

        if content.get('p') == "BisonStatus":
            status = Status(status_num=status_num, inscription_id=ins['inscription'])
            db.session.add(status)
        elif content.get('p') == "BisonRawProof":
            proof = Proof(status_num=status_num, inscription_id=ins['inscription'])
            db.session.add(proof)
        else:
            continue

    db.session.commit()


