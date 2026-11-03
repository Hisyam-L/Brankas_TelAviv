from config import BASE_DIR, OUTPUT_DIR
from stego.steganografi import LsbSteganography, SecureStego, StegoError
from database.db import buat_pipeline, URUTAN

stego = LsbSteganography()
asal = BASE_DIR / "foto.png"
print("Kapasitas (byte):", stego.capacity(asal))

# 1. Steganografi saja
hasil1 = OUTPUT_DIR / "stego_biasa.png"
stego.hide(asal, hasil1, "Ini pesan rahasia 123")
print("Terbaca         :", stego.reveal(hasil1))

# 2. Enkripsi dulu, lalu disembunyikan
aman = SecureStego(stego, buat_pipeline("kunci", 3, "passwordku"), URUTAN)
hasil2 = OUTPUT_DIR / "stego_aman.png"
aman.hide(asal, hasil2, "Pesan penting")
print("Terbaca (aman)  :", aman.reveal(hasil2))

# 3. Yang tertanam di gambar sebenarnya teks acak
print("Mentah di gambar:", stego.reveal(hasil2)[:40], "...")

# 4. Gambar tanpa pesan
try:
    stego.reveal(asal)
except StegoError as e:
    print("Gambar polos    :", e)