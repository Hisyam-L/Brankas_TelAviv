from __future__ import annotations

import sqlite3
from pathlib import Path
import pytest

from database.db import SecureMessageStore, buat_pipeline


@pytest.fixture
def store(tmp_path: Path):
    db_file = tmp_path / "test_app.db"
    pipeline = buat_pipeline("kunci", 3, "passwordku")
    return SecureMessageStore(pipeline, db_path=db_file)


def test_db_save_and_read(store):
    msg_id = store.simpan("Catatan 1", "Pesan rahasia di database.")
    assert msg_id is not None

    daftar = store.daftar()
    assert (msg_id, "Catatan 1") in daftar

    konten = store.buka(msg_id)
    assert konten == "Pesan rahasia di database."


def test_db_wrong_aes_password(tmp_path: Path):
    db_file = tmp_path / "test_app.db"
    pipeline_asli = buat_pipeline("kunci", 3, "passwordku")
    store1 = SecureMessageStore(pipeline_asli, db_path=db_file)
    msg_id = store1.simpan("Judul", "Isi rahasia")

    pipeline_salah = buat_pipeline("kunci", 3, "salah_pass")
    store2 = SecureMessageStore(pipeline_salah, db_path=db_file)

    # Salah AES password mengembalikan None
    assert store2.buka(msg_id) is None


def test_db_wrong_vigenere_scrambled(tmp_path: Path):
    db_file = tmp_path / "test_app.db"
    pipeline_asli = buat_pipeline("kunci", 3, "passwordku")
    store1 = SecureMessageStore(pipeline_asli, db_path=db_file)
    msg_id = store1.simpan("Judul", "Password wifi: abc123")

    pipeline_salah = buat_pipeline("kunciX", 3, "passwordku")
    store2 = SecureMessageStore(pipeline_salah, db_path=db_file)

    buka_hasil = store2.buka(msg_id)
    assert buka_hasil is not None
    assert buka_hasil != "Password wifi: abc123"


def test_db_categories(tmp_path: Path):
    db_file = tmp_path / "test_app.db"
    pipeline = buat_pipeline("kunci", 3, "passwordku")
    store = SecureMessageStore(pipeline, db_path=db_file)

    id_catatan = store.simpan("Catatan Harian", "Hari ini cerah", kategori="catatan")
    id_sandi = store.simpan("Akun Github", "admin:rahasia", kategori="sandi")

    daftar_catatan = store.daftar(kategori="catatan")
    assert any(item[0] == id_catatan for item in daftar_catatan)
    assert not any(item[0] == id_sandi for item in daftar_catatan)

    daftar_sandi = store.daftar(kategori="sandi")
    assert any(item[0] == id_sandi for item in daftar_sandi)
    assert not any(item[0] == id_catatan for item in daftar_sandi)


def test_db_migration(tmp_path: Path):
    # Simulasikan skema lama tanpa kategori & created_at
    db_file = tmp_path / "old.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE pesan (id INTEGER PRIMARY KEY AUTOINCREMENT, judul TEXT, isi_terenkripsi TEXT)")
    conn.commit()
    conn.close()

    # Buka dengan SecureMessageStore, harus bermigrasi otomatis tanpa error
    pipeline = buat_pipeline("kunci", 3, "passwordku")
    store = SecureMessageStore(pipeline, db_path=db_file)
    new_id = store.simpan("Baru", "Pesan baru", kategori="catatan")
    assert store.buka(new_id) == "Pesan baru"
