from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from blockchain.blockchain import Blockchain


class DocumentError(Exception):
    """Error domain registri dokumen yang aman ditampilkan langsung ke pengguna di UI."""


def hash_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """Menghitung SHA-256 berkas per potongan (chunk) agar hemat memori pada berkas besar."""
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
    """
    Mencatat sidik jari (SHA-256) aset dokumen penting ke dalam blockchain
    dan memverifikasi keaslian serta integritasnya.

    Catatan Keamanan & Keterbatasan:
    Blockchain ini bersifat single-node / lokal (tidak terdistribusi peer-to-peer).
    Pemeriksaan integritas mendeteksi pemalsuan konten atau berkas yang diubah,
    namun pemilik perangkat yang memiliki akses fisik dapat menulis ulang blockchain.
    """

    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain

    def _documents(self):
        """Mengambil blok yang menyimpan metadata dokumen (melewati genesis)."""
        return [b for b in self.blockchain.chain if "hash_file" in b.data]

    def register(self, path: str | Path, jenis: str, pemilik: str):
        """Mendaftarkan sidik jari dokumen ke blockchain."""
        if not jenis.strip() or not pemilik.strip():
            raise DocumentError("Jenis dan pemilik dokumen tidak boleh kosong")

        p = Path(path)
        if not p.exists() or not p.is_file():
            raise DocumentError(f"File dokumen tidak ditemukan: {path}")

        h = hash_file(p)
        for blok in self._documents():
            if blok.data.get("hash_file") == h:
                raise DocumentError(
                    f"Dokumen ini sudah terdaftar di blok #{blok.index} "
                    f"atas nama {blok.data.get('pemilik')}"
                )

        return self.blockchain.add_block({
            "jenis": jenis.strip(),
            "pemilik": pemilik.strip(),
            "nama_file": p.name,
            "hash_file": h,
            "tanggal": date.today().isoformat(),
        })

    def verify(self, path: str | Path, block_index: int | None = None) -> tuple[str, str]:
        """
        Memverifikasi integritas berkas terhadap catatan di blockchain.
        Mengembalikan tuple: (status, keterangan)
        Status: "ASLI", "DIUBAH", "TIDAK_TERDAFTAR", "RANTAI_RUSAK"
        """
        valid, pesan = self.blockchain.is_valid()
        if not valid:
            return "RANTAI_RUSAK", f"Blockchain dimanipulasi: {pesan}"

        p = Path(path)
        if not p.exists() or not p.is_file():
            raise DocumentError(f"File dokumen tidak ditemukan: {path}")

        h = hash_file(p)

        if block_index is not None:
            target = next((b for b in self._documents() if b.index == block_index), None)
            if target is None:
                raise DocumentError(f"Blok #{block_index} bukan blok dokumen")
            if target.data.get("hash_file") == h:
                return "ASLI", f"Cocok dengan blok #{target.index} ({target.data.get('jenis')}, {target.data.get('pemilik')})"
            return "DIUBAH", f"Isi file berbeda dari yang tercatat di blok #{target.index}"

        for blok in self._documents():
            if blok.data.get("hash_file") == h:
                return "ASLI", f"Cocok dengan blok #{blok.index} ({blok.data.get('jenis')}, {blok.data.get('pemilik')})"
        return "TIDAK_TERDAFTAR", "Tidak ada dokumen dengan sidik jari ini di blockchain"

    def list_documents(self) -> list[dict]:
        """Mengambil ringkasan semua dokumen yang tercatat di blockchain."""
        return [
            {
                "blok": b.index,
                "jenis": b.data.get("jenis", "-"),
                "pemilik": b.data.get("pemilik", "-"),
                "nama_file": b.data.get("nama_file", "-"),
                "tanggal": b.data.get("tanggal", "-"),
                "hash_file": b.data.get("hash_file", "-"),
            }
            for b in self._documents()
        ]
