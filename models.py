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
    hash = db.Column(db.String, unique=True, nullable=False)
    sender_address = db.Column(db.String, nullable=False)
    receiver_address = db.Column(db.String, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    method = db.Column(db.String, nullable=False) # 添加额外的字段，如交易方法，如果需要的话


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
