import json
from config import CHAIN_PATH
from blockchain.blockchain import Blockchain

CHAIN_PATH.unlink(missing_ok=True)           # mulai bersih

bc = Blockchain()
bc.add_block({"aset": "Sertifikat Tanah", "pemilik": "Andi"})
bc.add_block({"aset": "BPKB Motor", "pemilik": "Budi"})
print("Awal            :", bc.is_valid())

# simulasi pemalsuan: ubah pemilik langsung di file
mentah = json.loads(CHAIN_PATH.read_text())
mentah[1]["data"]["pemilik"] = "Penjahat"
CHAIN_PATH.write_text(json.dumps(mentah))

print("Setelah diubah  :", Blockchain().is_valid())