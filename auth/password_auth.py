from __future__ import annotations

import contextlib
import sqlite3
from datetime import datetime
from pathlib import Path

import bcrypt

from config import DB_PATH


class PasswordAuthError(Exception):
    """Error domain autentikasi password."""


class PasswordAuth:
    """
    Manajemen autentikasi pengguna dengan hash password bcrypt dan SQLite.
    Menyimpan profil pengguna: username, hash password, serial dongle USB, dan tanggal dibuat.
    """

    MIN_PASSWORD_LENGTH = 8

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)
        self._init_table()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_table(self) -> None:
        """Membuat tabel users jika belum ada."""
        with contextlib.closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        dongle_serial TEXT,
                        created_at TEXT
                    )"""
                )

    def has_users(self) -> bool:
        """Mengecek apakah sudah ada pengguna terdaftar (untuk mode First-Run Setup)."""
        with contextlib.closing(self._connect()) as conn:
            row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
            return bool(row and row[0] > 0)

    def register(
        self, username: str, password: str, dongle_serial: str | None = None
    ) -> int:
        """
        Mendaftarkan pengguna baru dengan validasi kekuatan password dan hash bcrypt.
        """
        username_clean = username.strip()
        if not username_clean:
            raise PasswordAuthError("Username tidak boleh kosong")

        if len(password) < self.MIN_PASSWORD_LENGTH:
            raise PasswordAuthError(
                f"Password terlalu pendek (minimal {self.MIN_PASSWORD_LENGTH} karakter)"
            )

        # Hash password menggunakan bcrypt dengan salt acak
        salt = bcrypt.gensalt()
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with contextlib.closing(self._connect()) as conn:
            with conn:
                try:
                    cur = conn.execute(
                        """INSERT INTO users (username, password_hash, dongle_serial, created_at)
                           VALUES (?, ?, ?, ?)""",
                        (username_clean, pw_hash, dongle_serial, now_str),
                    )
                    return cur.lastrowid
                except sqlite3.IntegrityError as e:
                    raise PasswordAuthError(f"Username '{username_clean}' sudah digunakan") from e

    def verify(self, username: str, password: str) -> bool:
        """
        Memverifikasi password pengguna secara constant-time melalui bcrypt.checkpw.
        """
        username_clean = username.strip()
        if not username_clean or not password:
            return False

        with contextlib.closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT password_hash FROM users WHERE username = ?", (username_clean,)
            ).fetchone()

        if not row:
            return False

        stored_hash = row[0].encode("utf-8")
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash)
        except Exception:
            return False

    def get_user(self, username: str) -> dict | None:
        """Mengambil data pengguna berdasarkan username (tanpa mengekspos hash password)."""
        with contextlib.closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT id, username, dongle_serial, created_at FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "dongle_serial": row[2],
                "created_at": row[3],
            }
        return None

    def set_dongle_serial(self, username: str, dongle_serial: str) -> bool:
        """Memperbarui asosiasi serial dongle USB untuk pengguna."""
        with contextlib.closing(self._connect()) as conn:
            with conn:
                cur = conn.execute(
                    "UPDATE users SET dongle_serial = ? WHERE username = ?",
                    (dongle_serial.strip(), username.strip()),
                )
                return cur.rowcount > 0

    def list_usernames(self) -> list[str]:
        """Mengambil daftar semua username terdaftar."""
        with contextlib.closing(self._connect()) as conn:
            rows = conn.execute("SELECT username FROM users ORDER BY id ASC").fetchall()
            return [r[0] for r in rows]
