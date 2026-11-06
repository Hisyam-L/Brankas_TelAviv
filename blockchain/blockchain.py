from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from config import BLOCKCHAIN_DIFFICULTY, CHAIN_PATH


class BlockchainError(Exception):
    """Error domain blockchain yang aman ditampilkan langsung ke pengguna di UI."""


class Block:
    def __init__(self, index: int, timestamp: float, data: dict, previous_hash: str, nonce: int = 0):
        self.index = index
        self.timestamp = timestamp
        self.data = data                  # dict dokumen / aset
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        isi = json.dumps(
            [self.index, self.timestamp, self.data, self.previous_hash, self.nonce],
            sort_keys=True,
        )
        return hashlib.sha256(isi.encode("utf-8")).hexdigest()

    def mine(self, difficulty: int) -> None:
        """Proof of Work: mencari nonce hingga hash diawali nol sebanyak difficulty."""
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Block:
        try:
            blok = cls(d["index"], d["timestamp"], d["data"], d["previous_hash"], d["nonce"])
            blok.hash = d["hash"]             # Menggunakan hash tersimpan untuk mendeteksi manipulasi
            return blok
        except KeyError as e:
            raise BlockchainError(f"Format blok dalam chain tidak valid: atribut {e} hilang") from e


class Blockchain:
    def __init__(self, path: Path | str = CHAIN_PATH, difficulty: int = BLOCKCHAIN_DIFFICULTY):
        self.path = Path(path)
        self.difficulty = difficulty
        self.chain: list[Block] = []
        if self.path.exists():
            self._load()
        else:
            self._create_genesis()

    def _create_genesis(self) -> None:
        """Membuat blok pertama (genesis block) jika berkas chain belum ada."""
        genesis = Block(0, time.time(), {"info": "Genesis Block SafeVault"}, "0")
        genesis.mine(self.difficulty)
        self.chain = [genesis]
        self._save()

    def add_block(self, data: dict) -> Block:
        """Menambahkan blok baru dengan Proof-of-Work ke blockchain."""
        if not isinstance(data, dict):
            raise BlockchainError("Data blok harus berupa dictionary")

        if not self.chain:
            self._create_genesis()

        terakhir = self.chain[-1]
        blok = Block(terakhir.index + 1, time.time(), data, terakhir.hash)
        blok.mine(self.difficulty)
        self.chain.append(blok)
        self._save()
        return blok

    def is_valid(self) -> tuple[bool, str]:
        """Memvalidasi integritas rantai: keterkaitan hash, PoW, dan konsistensi data."""
        if not self.chain:
            return False, "Blockchain kosong"

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
        """Menyimpan blockchain secara atomik untuk mencegah berkas korup jika terjadi interupsi."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps([b.to_dict() for b in self.chain], indent=2)
        dir_name = str(self.path.parent)

        # Buat temporary file di folder yang sama untuk atomic rename
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            tf.write(payload)
            tf.flush()
            os.fsync(tf.fileno())
            temp_path = tf.name

        os.replace(temp_path, str(self.path))

    def _load(self) -> None:
        """Membaca rantai dari berkas chain JSON."""
        try:
            content = self.path.read_text(encoding="utf-8")
            if not content.strip():
                self._create_genesis()
                return
            mentah = json.loads(content)
            if not isinstance(mentah, list):
                raise BlockchainError("Format file blockchain salah (bukan array JSON)")
            self.chain = [Block.from_dict(d) for d in mentah]
        except (json.JSONDecodeError, BlockchainError, OSError) as e:
            raise BlockchainError("File blockchain rusak atau formatnya salah") from e
