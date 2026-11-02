from __future__ import annotations

import hashlib
import json
import time

from config import CHAIN_PATH


class BlockchainError(Exception):
    """Error yang aman ditampilkan langsung ke pengguna di UI."""


class Block:
    def __init__(self, index, timestamp, data, previous_hash, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.data = data                  # dict, misal {"jenis": "Ijazah", "pemilik": "Andi", ...}
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        isi = json.dumps(
            [self.index, self.timestamp, self.data, self.previous_hash, self.nonce],
            sort_keys=True,
        )
        return hashlib.sha256(isi.encode()).hexdigest()

    def mine(self, difficulty: int) -> None:
        """Proof of work sederhana: cari nonce sampai hash diawali nol sebanyak difficulty."""
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()

    def to_dict(self) -> dict:
        return {
            "index": self.index, "timestamp": self.timestamp, "data": self.data,
            "previous_hash": self.previous_hash, "nonce": self.nonce, "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Block":
        blok = cls(d["index"], d["timestamp"], d["data"], d["previous_hash"], d["nonce"])
        blok.hash = d["hash"]             # pakai hash tersimpan, supaya manipulasi terdeteksi
        return blok


class Blockchain:
    def __init__(self, path=CHAIN_PATH, difficulty: int = 3):
        self.path = path
        self.difficulty = difficulty
        self.chain: list[Block] = []
        if self.path.exists():
            self._load()
        else:
            self._create_genesis()

    def _create_genesis(self) -> None:
        genesis = Block(0, time.time(), {"info": "Genesis"}, "0")
        genesis.mine(self.difficulty)
        self.chain = [genesis]
        self._save()

    def add_block(self, data: dict) -> Block:
        terakhir = self.chain[-1]
        blok = Block(terakhir.index + 1, time.time(), data, terakhir.hash)
        blok.mine(self.difficulty)
        self.chain.append(blok)
        self._save()
        return blok

    def is_valid(self) -> tuple[bool, str]:
        target = "0" * self.difficulty
        for i, blok in enumerate(self.chain):
            if blok.hash != blok.compute_hash():
                return False, f"Blok {blok.index}: isi diubah (hash tidak cocok)"
            if not blok.hash.startswith(target):
                return False, f"Blok {blok.index}: proof of work tidak valid"
            if i > 0 and blok.previous_hash != self.chain[i - 1].hash:
                return False, f"Blok {blok.index}: rantai putus (previous_hash tidak cocok)"
        return True, "Rantai valid"

    def _save(self) -> None:
        self.path.write_text(
            json.dumps([b.to_dict() for b in self.chain], indent=2), encoding="utf-8"
        )

    def _load(self) -> None:
        try:
            mentah = json.loads(self.path.read_text(encoding="utf-8"))
            self.chain = [Block.from_dict(d) for d in mentah]
        except (json.JSONDecodeError, KeyError) as e:
            raise BlockchainError("File blockchain rusak atau formatnya salah") from e