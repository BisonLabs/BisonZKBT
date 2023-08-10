from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Balance(db.Model):
    __bind_key__ = 'bison'
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(80), unique=True, nullable=False)
    amount = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<Address %r>' % self.address

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
