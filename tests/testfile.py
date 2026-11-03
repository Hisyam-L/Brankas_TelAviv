import hashlib
import os

from config import OUTPUT_DIR
from crypto.file_enkripsi import ChaChaFileCipher, FileCipherError


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


asal = OUTPUT_DIR / "contoh.bin"
enc = OUTPUT_DIR / "contoh.bin.enc"
balik = OUTPUT_DIR / "contoh_balik.bin"

asal.write_bytes(os.urandom(2_500_000))        # 2,5 MB = 3 potongan

cipher = ChaChaFileCipher("passwordku")
cipher.encrypt_file(asal, enc)
cipher.decrypt_file(enc, balik)
print("Isi identik     :", sha(asal) == sha(balik))

# password salah
try:
    ChaChaFileCipher("salah").decrypt_file(enc, OUTPUT_DIR / "gagal.bin")
except FileCipherError as e:
    print("Password salah  :", e)

# file diubah satu byte
data = bytearray(enc.read_bytes())
data[100] ^= 1
rusak = OUTPUT_DIR / "rusak.enc"
rusak.write_bytes(bytes(data))
try:
    cipher.decrypt_file(rusak, OUTPUT_DIR / "gagal2.bin")
except FileCipherError as e:
    print("File diubah     :", e)