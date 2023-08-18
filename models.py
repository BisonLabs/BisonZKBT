from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Balance(db.Model):
    __bind_key__ = 'bison'
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(80), unique=True, nullable=False)
    amount = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<Address %r>' % self.address
    
class TempTransaction(db.Model):
    __bind_key__ = 'bison'
    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(256), unique=True, nullable=False)
    method = db.Column(db.String(80), nullable=False)
    quoteID = db.Column(db.String(80))
    expiry = db.Column(db.String(80))
    tick1 = db.Column(db.String(80))
    contractAddress1 = db.Column(db.String(80))
    amount1 = db.Column(db.Float)
    tick2 = db.Column(db.String(80))
    contractAddress2 = db.Column(db.String(80))
    amount2 = db.Column(db.Float)
    makerAddr = db.Column(db.String(80))
    takerAddr = db.Column(db.String(80))
    makerSig = db.Column(db.String(80))
    takerSig = db.Column(db.String(80))


class Status(db.Model):
    __bind_key__ = 'ordinal_sync'
    id = db.Column(db.Integer, primary_key=True)
    status_num = db.Column(db.Integer)
    inscription_id = db.Column(db.String)

class Proof(db.Model):
    __bind_key__ = 'ordinal_sync'
    id = db.Column(db.Integer, primary_key=True)
    status_num = db.Column(db.Integer)
    inscription_id = db.Column(db.String)
