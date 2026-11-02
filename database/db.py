from __future__ import annotations

import sqlite3

from config import DB_PATH
from crypto.super_enkripsi import (
    AesLayer, CipherError, RailFenceLayer, SuperEncryption, VigenereLayer,
)

URUTAN = ["vigenere", "rail_fence", "aes"]


def buat_pipeline(kunci_vigenere, kunci_rail, password_aes) -> SuperEncryption:
    """Merakit super encrypt dari tiga kunci yang diketik pengguna."""
    return SuperEncryption([
        VigenereLayer(kunci_vigenere),
        RailFenceLayer(kunci_rail),
        AesLayer(password_aes),
    ])


class SecureMessageStore:

    def __init__(self, cipher: SuperEncryption, order: list[str] = URUTAN, db_path=DB_PATH):
        self.cipher = cipher
        self.order = order
        self.db_path = db_path
        self._init_table()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_table(self) -> None:
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS pesan (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            judul TEXT,
                            isi_terenkripsi TEXT)""")

    def simpan(self, judul: str, pesan: str) -> int:
        terenkripsi = self.cipher.encrypt(pesan, self.order)   # dienkripsi dulu
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO pesan (judul, isi_terenkripsi) VALUES (?, ?)",
                (judul, terenkripsi),                          # baru masuk database
            )
            return cur.lastrowid

    def daftar(self) -> list[tuple[int, str]]:
        with self._connect() as db:
            return db.execute("SELECT id, judul FROM pesan").fetchall()

    def buka(self, id_pesan: int) -> str | None:
        with self._connect() as db:
            baris = db.execute(
                "SELECT isi_terenkripsi FROM pesan WHERE id = ?", (id_pesan,)
            ).fetchone()
        if baris is None:
            return None
        try:
            return self.cipher.decrypt(baris[0], self.order)
        except CipherError:                                    # password salah / data rusak
            return None