from __future__ import annotations

import pytest

from crypto.classic_algoritma import RailFenceCipher, VigenereCipher
from crypto.super_enkripsi import ALPHABET


def test_vigenere_roundtrip():
    cipher = VigenereCipher("RAHASIA", ALPHABET)
    pesan = "Halo Dunia 123! Selamat Datang di SafeVault."
    terenkripsi = cipher.encode(pesan)
    assert terenkripsi != pesan
    dekripsi = cipher.decode(terenkripsi)
    assert dekripsi == pesan


def test_vigenere_empty_key():
    with pytest.raises(ValueError, match="key must not be empty"):
        VigenereCipher("", ALPHABET)


def test_vigenere_invalid_key_char():
    with pytest.raises(ValueError, match="contains characters not in alphabet"):
        VigenereCipher("KUNCI#@!", ALPHABET)


def test_rail_fence_roundtrip():
    cipher = RailFenceCipher(3)
    pesan = "KRIPTOGRAFI ITB 2026"
    terenkripsi = cipher.encryptRailFence(pesan)
    assert terenkripsi != pesan
    dekripsi = cipher.decryptRailFence(terenkripsi)
    assert dekripsi == pesan


def test_rail_fence_key_one():
    cipher = RailFenceCipher(1)
    pesan = "TETAP SAMA"
    assert cipher.encryptRailFence(pesan) == pesan
    assert cipher.decryptRailFence(pesan) == pesan


def test_rail_fence_invalid_key():
    with pytest.raises(ValueError, match="key must be >= 1"):
        RailFenceCipher(0)
