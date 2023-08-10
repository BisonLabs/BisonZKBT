const { BIP322, Signer, Verifier } = require('bip322-js');

// 获取命令行参数
const address = process.argv[2];
const message = process.argv[3];
const signature = process.argv[4];

// Verifying a simple BIP-322 signature
const validity = Verifier.verifySignature(address, message, signature);
console.log(validity); // True 
