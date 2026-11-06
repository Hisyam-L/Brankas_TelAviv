from __future__ import annotations

import os
from pathlib import Path
import pytest

from crypto.file_enkripsi import ChaChaFileCipher, FileCipherError


def test_file_crypto_roundtrip(tmp_path: Path):
    asal = tmp_path / "data.bin"
    enc = tmp_path / "data.bin.enc"
    balik = tmp_path / "data_balik.bin"

    # Multi-chunk data: 2.2 MB (chunk_size = 1 MB)
    raw_data = os.urandom(2_200_000)
    asal.write_bytes(raw_data)

    cipher = ChaChaFileCipher("kunci_rahasia_file_123")
    cipher.encrypt_file(asal, enc)

    assert enc.exists()
    assert enc.stat().st_size > len(raw_data)

    cipher.decrypt_file(enc, balik)
    assert balik.read_bytes() == raw_data


def test_file_crypto_empty_file(tmp_path: Path):
    asal = tmp_path / "empty.txt"
    enc = tmp_path / "empty.txt.enc"
    balik = tmp_path / "empty_balik.txt"

    asal.write_bytes(b"")
    cipher = ChaChaFileCipher("passwordku")
    cipher.encrypt_file(asal, enc)
    cipher.decrypt_file(enc, balik)
    assert balik.read_bytes() == b""


def test_file_crypto_wrong_password(tmp_path: Path):
    asal = tmp_path / "test.txt"
    enc = tmp_path / "test.txt.enc"
    out = tmp_path / "out.txt"

    asal.write_text("Dokumen rahasia penting.")
    cipher = ChaChaFileCipher("pass_benar")
    cipher.encrypt_file(asal, enc)

    cipher_salah = ChaChaFileCipher("pass_salah")
    with pytest.raises(FileCipherError, match="password salah atau file telah diubah"):
        cipher_salah.decrypt_file(enc, out)


def test_file_crypto_tampered_byte(tmp_path: Path):
    asal = tmp_path / "test.txt"
    enc = tmp_path / "test.txt.enc"
    out = tmp_path / "out.txt"

    asal.write_text("Integritas data adalah kunci.")
    cipher = ChaChaFileCipher("password123")
    cipher.encrypt_file(asal, enc)

    # Ubah 1 byte di tengah berkas
    data = bytearray(enc.read_bytes())
    data[len(data) // 2] ^= 0xFF
    enc.write_bytes(bytes(data))

    with pytest.raises(FileCipherError):
        cipher.decrypt_file(enc, out)


def test_file_crypto_truncated_file(tmp_path: Path):
    asal = tmp_path / "test.txt"
    enc = tmp_path / "test.txt.enc"
    out = tmp_path / "out.txt"

    asal.write_text("Berkas akan dipotong.")
    cipher = ChaChaFileCipher("password123")
    cipher.encrypt_file(asal, enc)

    # Potong 20 byte terakhir
    data = enc.read_bytes()[:-20]
    enc.write_bytes(data)

    with pytest.raises(FileCipherError):
        cipher.decrypt_file(enc, out)


def test_file_crypto_progress_callback(tmp_path: Path):
    asal = tmp_path / "progress.bin"
    enc = tmp_path / "progress.bin.enc"
    asal.write_bytes(os.urandom(1_500_000))

    progress_vals = []
    cipher = ChaChaFileCipher("password123")
    cipher.encrypt_file(asal, enc, progress_callback=lambda p: progress_vals.append(p))

    assert len(progress_vals) > 0
    assert progress_vals[-1] == 1.0
