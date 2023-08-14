import os
import shutil
import subprocess
import time
from verifier import updateZKtmp

def get_latest_n(dir):
    files = os.listdir(dir)
    numbers = [int(file.replace('status', '').replace('.json', '')) for file in files]
    return max(numbers)


def copy_file(n, source_dir, dest_dir, file_pattern):
    filename = file_pattern.format(n)
    source_file = os.path.join(source_dir, filename)
    dest_file = os.path.join(dest_dir, filename)
    shutil.copy2(source_file, dest_file)

def run_cairo_command(cairo_dir, n):
    cairo_run_path = "/home/jaylee/cairo_venv/bin/cairo-run"
    giza_prove_path = "/home/jaylee/.cargo/bin/giza"
    cairo_command = f"{cairo_run_path} --program=test_compiled.json --layout=small --program_input=zk_tmp.json --memory_file=memory.bin --trace_file=trace.bin"
    giza_command = f"{giza_prove_path} prove --trace=trace.bin --memory=memory.bin --program=test_compiled.json --output=zkproof{n}.bin --num-outputs=0"
    
    process = subprocess.Popen(cairo_command, cwd=cairo_dir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        print(f"Cairo command failed with error code {process.returncode}, stderr: {stderr.decode()}")
        return False

    if "Status Prove Succeeded!" not in stdout.decode():
        print(f"Verification failed, stdout: {stdout.decode()}")
        return False

    process = subprocess.Popen(giza_command, cwd=cairo_dir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        print(f"Giza command failed with error code {process.returncode}, stderr: {stderr.decode()}")
        return False

    copy_file(n, cairo_dir, './zkProof', 'zkproof{}.bin')

    return True

def zkProofGenerator():
    start_time = time.time()
    status_dir = './status/'
    proof_dir = './statusProof/'
    target_status_dir = '/home/jaylee/Documents/BisonCairoVerifier/status/'
    target_proof_dir = '/home/jaylee/Documents/BisonCairoVerifier/statusProof/'

    # Get the latest n from the status directory
    n = get_latest_n(status_dir)

    # Generate a new zk_tmp.json file
    updateZKtmp()

    # Copy the latest two status files to the target directory
    for i in range(n-1, n+1):
        shutil.copy2(os.path.join(status_dir, f'status{i}.json'), target_status_dir)

    # Copy the latest proof file to the target directory
    copy_file(n, proof_dir, target_proof_dir, 'proof_{}.json')

    # Copy zk_tmp.json to the target directory
    shutil.copy2('zk_tmp.json', '/home/jaylee/Documents/BisonCairoVerifier/')

    # Run the cairo command in the target directory and check result
    if run_cairo_command('/home/jaylee/Documents/BisonCairoVerifier/', n):
        print("Verification succeeded!")
    else:
        print("Verification failed!")

    elapsed_time = time.time() - start_time
    print(f"Elapsed time: {elapsed_time} seconds")

if __name__ == "__main__":
    zkProofGenerator()
