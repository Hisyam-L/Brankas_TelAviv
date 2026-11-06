from __future__ import annotations

import sys
from pathlib import Path

# Base directory: jika dibundel PyInstaller, gunakan folder tempat executable
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
KEYS_DIR = DATA_DIR / "keys"
FACES_DIR = DATA_DIR / "faces"

DB_PATH = DATA_DIR / "app.db"
CHAIN_PATH = DATA_DIR / "chain.json"

# Pastikan folder penting selalu ada
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
KEYS_DIR.mkdir(parents=True, exist_ok=True)
FACES_DIR.mkdir(parents=True, exist_ok=True)

# Parameter KDF dan Kriptografi
PBKDF2_ITERATIONS = 100_000
SCRYPT_N = 2**15  # 32768
SCRYPT_R = 8
SCRYPT_P = 1
SALT_LEN = 16
CHUNK_SIZE = 1024 * 1024  # 1 MB

# Parameter Steganografi
STEGO_MAGIC = b"SVLT"

# Parameter Blockchain
BLOCKCHAIN_DIFFICULTY = 3

# Parameter Autentikasi
FACE_CONFIDENCE_THRESHOLD = 70.0  # LBPH distance (semakin kecil semakin cocok)
DONGLE_KEY_FILENAME = ".safevault.key"
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_SECONDS = 30
