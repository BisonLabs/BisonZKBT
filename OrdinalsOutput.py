import subprocess
import json

def inscribe_to_bitcoin(file_path, fee_rate=2):
    try:
        result = subprocess.run(['ord', '--testnet', 'wallet', 'inscribe', '--fee-rate', str(fee_rate), file_path],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        output = json.loads(result.stdout.decode().strip())
        inscription_value = output['inscription']
        return inscription_value
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr.decode().strip()}")
        return None
    except json.JSONDecodeError:
        print("Failed to parse the output as JSON.")
        return None
