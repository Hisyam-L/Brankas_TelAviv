from __future__ import annotations

import json
from pathlib import Path
import pytest

from blockchain.blockchain import Blockchain
from blockchain.registry import DocumentError, DocumentRegistry


@pytest.fixture
def registry(tmp_path: Path):
    chain_file = tmp_path / "chain.json"
    bc = Blockchain(path=chain_file, difficulty=2)
    return DocumentRegistry(bc)


def test_registry_register_and_verify(registry, tmp_path: Path):
    doc = tmp_path / "ijazah.pdf"
    doc.write_text("Sertifikat Ijazah Sarjana Informatika 2026")

    blok = registry.register(doc, "Ijazah", "Budi Santoso")
    assert blok.index == 1

    status, msg = registry.verify(doc)
    assert status == "ASLI"
    assert "Budi Santoso" in msg

    status_row, _ = registry.verify(doc, block_index=1)
    assert status_row == "ASLI"


def test_registry_duplicate_registration(registry, tmp_path: Path):
    doc = tmp_path / "ijazah.pdf"
    doc.write_text("Sertifikat Ijazah Sarjana Informatika 2026")

    registry.register(doc, "Ijazah", "Budi Santoso")
    with pytest.raises(DocumentError, match="sudah terdaftar"):
        registry.register(doc, "Ijazah", "Orang Lain")


def test_registry_tampered_document(registry, tmp_path: Path):
    doc = tmp_path / "dokumen.txt"
    doc.write_text("Nilai Asli A")
    registry.register(doc, "Transkrip", "Siti")

    # Ubah isi berkas fisik
    doc.write_text("Nilai Palsu A+")
    status_selected, msg = registry.verify(doc, block_index=1)
    assert status_selected == "DIUBAH"

    status_unselected, _ = registry.verify(doc)
    assert status_unselected == "TIDAK_TERDAFTAR"


def test_registry_unregistered_file(registry, tmp_path: Path):
    doc = tmp_path / "asing.txt"
    doc.write_text("Berkas belum terdaftar sama sekali")

    status, msg = registry.verify(doc)
    assert status == "TIDAK_TERDAFTAR"


def test_registry_broken_chain(registry, tmp_path: Path):
    doc = tmp_path / "surat.txt"
    doc.write_text("Surat Perjanjian")
    registry.register(doc, "Kontrak", "Ali")

    # Rusak file chain
    chain_file = registry.blockchain.path
    data = json.loads(chain_file.read_text())
    data[1]["data"]["pemilik"] = "Manipulator"
    chain_file.write_text(json.dumps(data))

    # Re-instantiate blockchain & registry
    reg2 = DocumentRegistry(Blockchain(path=chain_file, difficulty=2))
    status, msg = reg2.verify(doc)
    assert status == "RANTAI_RUSAK"


def test_registry_missing_file(registry):
    with pytest.raises(DocumentError, match="tidak ditemukan"):
        registry.register("/path/palsu/tidak/ada.pdf", "Jenis", "Pemilik")
