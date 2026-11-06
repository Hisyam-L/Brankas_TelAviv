from __future__ import annotations

import contextlib
from datetime import datetime
import sqlite3
from pathlib import Path

from config import DB_PATH
from crypto.super_enkripsi import (
    AesLayer,
    CipherError,
    RailFenceLayer,
    SuperEncryption,
    VigenereLayer,
)

URUTAN = ["vigenere", "rail_fence", "aes"]


def buat_pipeline(kunci_vigenere: str, kunci_rail: int | str, password_aes: str) -> SuperEncryption:
    """Merakit pipeline super enkripsi dari tiga kunci yang dimasukkan pengguna."""
    return SuperEncryption([
        VigenereLayer(kunci_vigenere),
        RailFenceLayer(int(kunci_rail)),
        AesLayer(password_aes),
    ])


class SecureMessageStore:
    """Penyimpanan pesan penting terenkripsi di SQLite dengan dukungan kategori."""

    def __init__(
        self,
        cipher: SuperEncryption,
        order: list[str] | None = None,
        db_path: Path | str = DB_PATH,
        default_kategori: str = "catatan",
    ):
        self.cipher = cipher
        self.order = order or URUTAN
        self.db_path = str(db_path)
        self.default_kategori = default_kategori
        self._init_table()

    def _connect(self):
        """Membuka koneksi SQLite."""
        return sqlite3.connect(self.db_path)

    def _init_table(self) -> None:
        """Membuat tabel pesan dan melakukan migrasi kolom jika belum ada."""
        with contextlib.closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS pesan (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        judul TEXT,
                        isi_terenkripsi TEXT,
                        kategori TEXT DEFAULT 'catatan',
                        created_at TEXT
                    )"""
                )
                cursor = conn.execute("PRAGMA table_info(pesan)")
                existing_cols = {row[1] for row in cursor.fetchall()}
                if "kategori" not in existing_cols:
                    conn.execute("ALTER TABLE pesan ADD COLUMN kategori TEXT DEFAULT 'catatan'")
                if "created_at" not in existing_cols:
                    conn.execute("ALTER TABLE pesan ADD COLUMN created_at TEXT")

    def simpan(self, judul: str, pesan: str, kategori: str | None = None) -> int:
        """Enkripsi pesan lalu simpan ke database dengan kategori."""
        terenkripsi = self.cipher.encrypt(pesan, self.order)
        kat = (kategori or self.default_kategori).strip()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with contextlib.closing(self._connect()) as conn:
            with conn:
                cur = conn.execute(
                    "INSERT INTO pesan (judul, isi_terenkripsi, kategori, created_at) VALUES (?, ?, ?, ?)",
                    (judul, terenkripsi, kat, now_str),
                )
                return cur.lastrowid

    def daftar(self, kategori: str | None = None) -> list[tuple[int, str]]:
        """Mengambil daftar (id, judul) pesan. Jika kategori diisi, difilter berdasarkan kategori."""
        with contextlib.closing(self._connect()) as conn:
            if kategori:
                rows = conn.execute(
                    "SELECT id, judul FROM pesan WHERE kategori = ? ORDER BY id ASC",
                    (kategori,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, judul FROM pesan ORDER BY id ASC"
                ).fetchall()
            return rows

    def buka(self, id_pesan: int) -> str | None:
        """Membuka dan mendekripsi pesan berdasarkan ID. Mengembalikan None jika password salah/rusak."""
        with contextlib.closing(self._connect()) as conn:
            baris = conn.execute(
                "SELECT isi_terenkripsi FROM pesan WHERE id = ?", (id_pesan,)
            ).fetchone()

        if baris is None:
            return None

        try:
            return self.cipher.decrypt(baris[0], self.order)
        except CipherError:
            return None

    def hapus(self, id_pesan: int) -> bool:
        """Menghapus pesan berdasarkan ID."""
        with contextlib.closing(self._connect()) as conn:
            with conn:
                cur = conn.execute("DELETE FROM pesan WHERE id = ?", (id_pesan,))
                return cur.rowcount > 0

    def ambil_metadata(self, id_pesan: int) -> dict | None:
        """Mengambil metadata pesan tanpa membuka isi terenkripsi."""
        with contextlib.closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT id, judul, kategori, created_at FROM pesan WHERE id = ?",
                (id_pesan,),
            ).fetchone()
        if row:
            return {
                "id": row[0],
                "judul": row[1],
                "kategori": row[2],
                "created_at": row[3],
            }
        return None
