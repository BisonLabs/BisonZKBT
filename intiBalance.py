from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

file_path = os.path.abspath(os.getcwd())+"/db/bison.db"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+file_path
db = SQLAlchemy(app)

class Balance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(80), unique=True, nullable=False)
    amount = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<Address %r>' % self.address

with app.app_context():
    # create an address
    address = "tb1ptw39pxy2stdlexwutfjwak7c8u6tnzut80dtwt8fmqfdzpd60nfqsejr7m"
    # create an initial balance
    balance = Balance(address=address, amount=21000000)
    # add the balance to the session
    db.session.add(balance)
    # commit the transaction
    db.session.commit()
