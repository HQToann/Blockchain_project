/**
 * Script tự động trích xuất ABI từ artifacts/ của Hardhat ra thư mục gốc.
 * Chạy sau khi: npx hardhat compile
 * Lệnh: node scripts/export_abi.js
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');

const ARTIFACTS = {
  Election:        resolve(ROOT, 'artifacts/blockchain/contracts/VotingSystem.sol/Election.json'),
  ElectionFactory: resolve(ROOT, 'artifacts/blockchain/contracts/VotingSystem.sol/ElectionFactory.json'),
};

const OUTPUT = {
  Election_ABI:  resolve(ROOT, 'Election_ABI.json'),
  Factory_ABI:   resolve(ROOT, 'Factory_ABI.json'),
};

let ok = true;

for (const [name, path] of Object.entries(ARTIFACTS)) {
  if (!existsSync(path)) {
    console.error(`❌ Không tìm thấy: ${path}`);
    console.error(`   → Hãy chạy: npx hardhat compile trước`);
    ok = false;
  }
}

if (!ok) process.exit(1);

const electionArtifact = JSON.parse(readFileSync(ARTIFACTS.Election, 'utf8'));
const factoryArtifact  = JSON.parse(readFileSync(ARTIFACTS.ElectionFactory, 'utf8'));

writeFileSync(OUTPUT.Election_ABI, JSON.stringify(electionArtifact.abi, null, 2));
writeFileSync(OUTPUT.Factory_ABI,  JSON.stringify(factoryArtifact.abi,  null, 2));

console.log('✅ Election_ABI.json — đã cập nhật');
console.log('✅ Factory_ABI.json  — đã cập nhật');
console.log('');
console.log('Events có trong Election_ABI:');
electionArtifact.abi
  .filter(x => x.type === 'event')
  .forEach(e => console.log(`   📡 ${e.name}(${e.inputs.map(i => `${i.type} ${i.name}`).join(', ')})`));
