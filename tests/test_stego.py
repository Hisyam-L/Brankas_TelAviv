from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image
import pytest

from database.db import URUTAN, buat_pipeline
from stego.steganografi import LsbSteganography, SecureStego, StegoError


@pytest.fixture
def cover_image(tmp_path: Path):
    """Membuat cover image uji berukuran 100x100 RGB."""
    img_path = tmp_path / "sample.png"
    arr = (np.random.rand(100, 100, 3) * 255).astype(np.uint8)
    Image.fromarray(arr).save(img_path, format="PNG")
    return img_path


def test_stego_capacity(cover_image):
    stego = LsbSteganography()
    cap = stego.capacity(cover_image)
    # 100x100x3 = 30000 pixel values. (30000 - 64) // 8 = 3742 bytes
    assert cap == (30000 - 64) // 8


def test_stego_plain_roundtrip(cover_image, tmp_path: Path):
    stego = LsbSteganography()
    out = tmp_path / "stego.png"
    pesan = "Pesan rahasia 123! Karakter khusus: @#% & baris baru.\nBaris 2."

    stego.hide(cover_image, out, pesan)
    assert out.exists()

    hasil = stego.reveal(out)
    assert hasil == pesan


def test_secure_stego_roundtrip(cover_image, tmp_path: Path):
    pipeline = buat_pipeline("kuncivig", 4, "passaes123")
    sec_stego = SecureStego(LsbSteganography(), pipeline, URUTAN)
    out = tmp_path / "secure_stego.png"
    pesan = "Super Enkripsi + LSB Stego Berhasil!"

    sec_stego.hide(cover_image, out, pesan)
    hasil = sec_stego.reveal(out)
    assert hasil == pesan


def test_stego_plain_image_detection(cover_image):
    stego = LsbSteganography()
    with pytest.raises(StegoError, match="Tidak ada pesan tersembunyi"):
        stego.reveal(cover_image)


def test_stego_empty_message(cover_image, tmp_path: Path):
    stego = LsbSteganography()
    with pytest.raises(StegoError, match="tidak boleh kosong"):
        stego.hide(cover_image, tmp_path / "out.png", "")


def test_stego_capacity_exceeded(cover_image, tmp_path: Path):
    stego = LsbSteganography()
    cap = stego.capacity(cover_image)
    pesan_terlalu_panjang = "A" * (cap + 100)
    with pytest.raises(StegoError, match="terlalu panjang"):
        stego.hide(cover_image, tmp_path / "out.png", pesan_terlalu_panjang)
