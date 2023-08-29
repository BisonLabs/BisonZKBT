# config.py
_statusNum = 0

def get_status():
    return _statusNum

def set_status(new_status):
    global _statusNum
    _statusNum = new_status
