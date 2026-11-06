from __future__ import annotations

import json
from pathlib import Path
import pytest

from blockchain.blockchain import Block, Blockchain, BlockchainError


def test_block_creation_and_pow():
    b = Block(1, 1000.0, {"doc": "Sertifikat"}, "0" * 64)
    assert b.hash == b.compute_hash()
    b.mine(difficulty=2)
    assert b.hash.startswith("00")
    assert b.hash == b.compute_hash()


def test_blockchain_genesis_and_add(tmp_path: Path):
    chain_file = tmp_path / "chain.json"
    bc = Blockchain(path=chain_file, difficulty=2)

    assert len(bc.chain) == 1
    assert bc.chain[0].index == 0
    assert bc.chain[0].data["info"] == "Genesis Block SafeVault"

    valid, msg = bc.is_valid()
    assert valid is True

    # Tambah blok 1
    b1 = bc.add_block({"aset": "Ijazah S1", "pemilik": "Andi"})
    assert b1.index == 1
    assert len(bc.chain) == 2

    valid, msg = bc.is_valid()
    assert valid is True


def test_blockchain_invalid_data_type(tmp_path: Path):
    chain_file = tmp_path / "chain.json"
    bc = Blockchain(path=chain_file, difficulty=2)
    with pytest.raises(BlockchainError, match="dictionary"):
        bc.add_block("Bukan dict")


def test_blockchain_tampered_block(tmp_path: Path):
    chain_file = tmp_path / "chain.json"
    bc = Blockchain(path=chain_file, difficulty=2)
    bc.add_block({"aset": "Tanah", "pemilik": "Budi"})

    # Manipulasi langsung di file
    data = json.loads(chain_file.read_text())
    data[1]["data"]["pemilik"] = "Penipu"
    chain_file.write_text(json.dumps(data))

    bc_reloaded = Blockchain(path=chain_file, difficulty=2)
    valid, msg = bc_reloaded.is_valid()
    assert valid is False
    assert "isi diubah" in msg


def test_blockchain_broken_link(tmp_path: Path):
    chain_file = tmp_path / "chain.json"
    bc = Blockchain(path=chain_file, difficulty=2)
    bc.add_block({"aset": "A"})
    bc.add_block({"aset": "B"})

    # Rusak previous_hash pada blok 2
    data = json.loads(chain_file.read_text())
    data[2]["previous_hash"] = "abc123def"
    data[2]["hash"] = Block.from_dict(data[2]).compute_hash()  # re-hash agar hash cocok
    chain_file.write_text(json.dumps(data))

    bc_reloaded = Blockchain(path=chain_file, difficulty=2)
    valid, msg = bc_reloaded.is_valid()
    assert valid is False
    assert "rantai putus" in msg or "proof of work" in msg


def test_blockchain_corrupt_file(tmp_path: Path):
    chain_file = tmp_path / "chain.json"
    chain_file.write_text("BUKAN JSON VALID!!!")
    with pytest.raises(BlockchainError, match="rusak atau formatnya salah"):
        Blockchain(path=chain_file, difficulty=2)
