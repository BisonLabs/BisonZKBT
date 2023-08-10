import os
import subprocess
import time

# 指定包含.zkproof文件的目录
proofs_directory = './zkProof'

# 获取所有的 .bin 文件
proof_files = [f for f in os.listdir(proofs_directory) if f.endswith('.bin')]

# 记录整体开始时间
start_time_total = time.time()

# 遍历所有的 .bin 文件并验证
for index, proof_file in enumerate(proof_files, start=1):
    start_time = time.time()
    command = f'giza verify --proof={os.path.join(proofs_directory, proof_file)}'
    subprocess.run(command, shell=True)
    elapsed_time = time.time() - start_time
    print(f'Status{index} verified in {elapsed_time:.2f} seconds')

# 记录整体花费时间
elapsed_time_total = time.time() - start_time_total
print(f'All status verified in {elapsed_time_total:.2f} seconds')
