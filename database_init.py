from models import db, Balance

def initialize_database(app, data):
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
