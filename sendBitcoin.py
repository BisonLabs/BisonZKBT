import subprocess

def send_bitcoin(address, amount, fee_rate, wallet_name="paywallet"):
    try:
        command = [
            'bitcoin-cli', '--testnet', '-rpcwallet=' + wallet_name, '-named',
            'sendtoaddress', 'address=' + address, 'amount=' + str(amount), 'fee_rate=' + str(fee_rate)
        ]

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            return "Error:", result.stderr.decode()

        return "Success:", result.stdout.decode()

    except Exception as e:
        return "An exception occurred:", str(e)