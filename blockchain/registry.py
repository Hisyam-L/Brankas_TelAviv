from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from blockchain.blockchain import Blockchain


class DocumentError(Exception):
    """Error yang aman ditampilkan langsung ke pengguna di UI."""


def hash_file(path, chunk_size: int = 1024 * 1024) -> str:
    """SHA-256 file, dibaca per potongan supaya file besar tidak memenuhi RAM."""
    sha = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                potongan = f.read(chunk_size)
                if not potongan:
                    break
                sha.update(potongan)
    except OSError as e:
        raise DocumentError(f"File tidak bisa dibaca: {path}") from e
    return sha.hexdigest()


class DocumentRegistry:
    """Mencatat sidik jari dokumen penting di blockchain dan memverifikasinya."""

    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain

    def _documents(self):
        """Blok yang berisi dokumen (genesis dilewati)."""
        return [b for b in self.blockchain.chain if "hash_file" in b.data]

    def register(self, path, jenis: str, pemilik: str):
        if not jenis.strip() or not pemilik.strip():
            raise DocumentError("Jenis dan pemilik dokumen tidak boleh kosong")

        h = hash_file(path)
        for blok in self._documents():
            if blok.data["hash_file"] == h:
                raise DocumentError(
                    f"Dokumen ini sudah terdaftar di blok #{blok.index} "
                    f"atas nama {blok.data['pemilik']}"
                )

        return self.blockchain.add_block({
            "jenis": jenis.strip(),
            "pemilik": pemilik.strip(),
            "nama_file": Path(path).name,
            "hash_file": h,
            "tanggal": date.today().isoformat(),
        })

    def verify(self, path, block_index: int | None = None) -> tuple[str, str]:
        """
        Mengembalikan (status, keterangan). Status:
          ASLI, DIUBAH, TIDAK_TERDAFTAR, RANTAI_RUSAK

        block_index diisi kalau pengguna memilih dokumen dari daftar,
        sehingga file yang diubah bisa dibedakan dari file yang memang belum terdaftar.
        """
        valid, pesan = self.blockchain.is_valid()
        if not valid:
            return "RANTAI_RUSAK", f"Blockchain dimanipulasi: {pesan}"

        h = hash_file(path)

        if block_index is not None:
            target = next((b for b in self._documents() if b.index == block_index), None)
            if target is None:
                raise DocumentError(f"Blok #{block_index} bukan blok dokumen")
            if target.data["hash_file"] == h:
                return "ASLI", f"Cocok dengan blok #{target.index} ({target.data['jenis']}, {target.data['pemilik']})"
            return "DIUBAH", f"Isi file berbeda dari yang tercatat di blok #{target.index}"

        for blok in self._documents():
            if blok.data["hash_file"] == h:
                return "ASLI", f"Cocok dengan blok #{blok.index} ({blok.data['jenis']}, {blok.data['pemilik']})"
        return "TIDAK_TERDAFTAR", "Tidak ada dokumen dengan sidik jari ini di blockchain"

    def list_documents(self) -> list[dict]:
        return [
            {"blok": b.index, **{k: b.data[k] for k in ("jenis", "pemilik", "nama_file", "tanggal")}}
            for b in self._documents()
        ]