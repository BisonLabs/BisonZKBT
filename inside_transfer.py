from models import db, Balance

def transfer_funds(sender_address, receiver_address, amount):
    # 查询发送方余额
    sender_balance = Balance.query.filter_by(address=sender_address).first()
    if not sender_balance or sender_balance.amount < int(amount):
        return False, "insufficient balance"

    # 查询接收方余额，如果不存在，则创建
    receiver_balance = Balance.query.filter_by(address=receiver_address).first()
    if receiver_balance is None:
        receiver_balance = Balance(address=receiver_address, amount=0)
        db.session.add(receiver_balance)

    # 实际转账
    sender_balance.amount -= int(amount)
    receiver_balance.amount += int(amount)
    db.session.commit()

    return True, "transfer successful"