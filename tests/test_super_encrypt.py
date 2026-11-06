from __future__ import annotations

import pytest

from crypto.super_enkripsi import (
    AesLayer,
    CipherError,
    RailFenceLayer,
    SuperEncryption,
    VigenereLayer,
)


@pytest.fixture
def pipeline():
    return SuperEncryption([
        VigenereLayer("kunciku"),
        RailFenceLayer(3),
        AesLayer("password123"),
    ])


def test_super_encryption_roundtrip(pipeline):
    order = ["vigenere", "rail_fence", "aes"]
    teks = "Pesan Sangat Rahasia: PIN ATM 987654. Baris baru:\nLine 2!"
    enc = pipeline.encrypt(teks, order)
    assert enc != teks
    dec = pipeline.decrypt(enc, order)
    assert dec == teks


def test_super_encryption_wrong_aes_password():
    order = ["vigenere", "rail_fence", "aes"]
    p1 = SuperEncryption([
        VigenereLayer("kunciku"),
        RailFenceLayer(3),
        AesLayer("password_asli"),
    ])
    p2 = SuperEncryption([
        VigenereLayer("kunciku"),
        RailFenceLayer(3),
        AesLayer("password_salah"),
    ])
    enc = p1.encrypt("Rahasia", order)
    with pytest.raises(CipherError, match="password salah atau data rusak"):
        p2.decrypt(enc, order)


def test_super_encryption_wrong_classical_keys_scrambles(pipeline):
    order = ["vigenere", "rail_fence", "aes"]
    enc = pipeline.encrypt("Rahasia Besar Negara", order)

    p_salah_vig = SuperEncryption([
        VigenereLayer("kuncilain"),
        RailFenceLayer(3),
        AesLayer("password123"),
    ])
    # Classical cipher wrong key produces scrambled text, does not raise CipherError
    dec = p_salah_vig.decrypt(enc, order)
    assert dec != "Rahasia Besar Negara"


def test_super_encryption_empty_order(pipeline):
    with pytest.raises(CipherError, match="Urutan lapisan tidak boleh kosong"):
        pipeline.encrypt("Halo", [])


def test_super_encryption_unknown_layer(pipeline):
    with pytest.raises(CipherError, match="Lapisan tidak dikenal"):
        pipeline.encrypt("Halo", ["unknown_layer"])


def test_super_encryption_duplicate_layers():
    with pytest.raises(CipherError, match="duplikat"):
        SuperEncryption([
            AesLayer("pw1"),
            AesLayer("pw2"),
        ])
