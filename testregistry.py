from config import CHAIN_PATH, OUTPUT_DIR
from blockchain.blockchain import Blockchain
from blockchain.registry import DocumentRegistry, DocumentError

CHAIN_PATH.unlink(missing_ok=True)                # mulai bersih

ijazah = OUTPUT_DIR / "ijazah.txt"
ijazah.write_text("Ijazah S1 atas nama Andi, IPK 3.75")

reg = DocumentRegistry(Blockchain())
blok = reg.register(ijazah, "Ijazah", "Andi")
print("Terdaftar          : blok #", blok.index)

print("Verifikasi asli    :", reg.verify(ijazah))

try:
    reg.register(ijazah, "Ijazah", "Andi")
except DocumentError as e:
    print("Daftar dua kali    :", e)

# file dipalsukan: IPK diubah
ijazah.write_text("Ijazah S1 atas nama Andi, IPK 4.00")
print("Dipalsukan (dipilih):", reg.verify(ijazah, block_index=1))
print("Dipalsukan (umum)  :", reg.verify(ijazah))

# blockchain dimanipulasi langsung di file
import json
mentah = json.loads(CHAIN_PATH.read_text())
mentah[1]["data"]["pemilik"] = "Penjahat"
CHAIN_PATH.write_text(json.dumps(mentah))
ijazah.write_text("Ijazah S1 atas nama Andi, IPK 3.75")    # file dikembalikan seperti asli
print("Chain dimanipulasi :", DocumentRegistry(Blockchain()).verify(ijazah))

print("Daftar             :", reg.list_documents())