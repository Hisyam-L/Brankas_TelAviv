from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

from config import STEGO_MAGIC


class StegoError(Exception):
    """Error domain steganografi yang aman ditampilkan langsung ke pengguna di UI."""


class LsbSteganography:
    """
    Menyembunyikan teks di bit terakhir (LSB) tiap kanal warna piksel gambar PNG.
    Format header di LSB:
        - 4 byte Magic Number ("SVLT") untuk mendeteksi apakah gambar memuat pesan rahasia
        - 4 byte Panjang Pesan (big-endian unsigned integer)
        - N byte Isi Pesan (UTF-8)
    """

    _MAGIC = STEGO_MAGIC
    _MAGIC_BITS = len(STEGO_MAGIC) * 8  # 32 bit
    _LENGTH_BITS = 32                   # 32 bit
    _HEADER_BITS = _MAGIC_BITS + _LENGTH_BITS  # 64 bit (8 byte)

    def _load(self, path: str | Path):
        try:
            gambar = Image.open(path).convert("RGB")
        except (FileNotFoundError, OSError) as e:
            raise StegoError(f"Gambar tidak bisa dibuka: {path}") from e
        arr = np.array(gambar)
        return arr.shape, arr.flatten()

    def capacity(self, path: str | Path) -> int:
        """Kapasitas muatan pesan (dalam satuan byte) yang muat di gambar."""
        _, datar = self._load(path)
        kapasitas = (len(datar) - self._HEADER_BITS) // 8
        return max(0, kapasitas)

    def hide(self, cover_path: str | Path, output_path: str | Path, message: str) -> None:
        """Menyematkan pesan teks ke dalam cover image dan menyimpannya sebagai PNG lossless."""
        if not message:
            raise StegoError("Pesan yang akan disembunyikan tidak boleh kosong")

        bentuk, datar = self._load(cover_path)
        data = message.encode("utf-8")
        muatan = self._MAGIC + len(data).to_bytes(4, "big") + data
        bit = np.unpackbits(np.frombuffer(muatan, dtype=np.uint8))

        if len(bit) > len(datar):
            raise StegoError("Pesan terlalu panjang untuk kapasitas gambar ini")

        datar[: len(bit)] = (datar[: len(bit)] & 0xFE) | bit
        Image.fromarray(datar.reshape(bentuk)).save(output_path, format="PNG")

    def reveal(self, stego_path: str | Path) -> str:
        """Mengekstrak pesan teks dari gambar steganografi PNG."""
        _, datar = self._load(stego_path)

        if len(datar) < self._HEADER_BITS:
            raise StegoError("Ukuran gambar terlalu kecil untuk memuat pesan")

        # 1. Verifikasi magic number
        magic_bytes = np.packbits(datar[: self._MAGIC_BITS] & 1).tobytes()
        if magic_bytes != self._MAGIC:
            raise StegoError("Tidak ada pesan tersembunyi di gambar ini")

        # 2. Baca panjang payload
        len_bits = datar[self._MAGIC_BITS : self._HEADER_BITS] & 1
        panjang = int.from_bytes(np.packbits(len_bits).tobytes(), "big")

        if panjang <= 0 or self._HEADER_BITS + panjang * 8 > len(datar):
            raise StegoError("Tidak ada pesan tersembunyi di gambar ini")

        # 3. Ekstrak isi pesan
        bit = datar[self._HEADER_BITS : self._HEADER_BITS + panjang * 8] & 1
        try:
            return np.packbits(bit).tobytes().decode("utf-8")
        except UnicodeDecodeError as e:
            raise StegoError("Data di gambar bukan pesan yang valid") from e


class SecureStego:
    """
    Enkripsi bertingkat (super enkripsi) sebelum disembunyikan ke gambar.
    Menggunakan pola komposisi sehingga cipher dan steganografi tetap modular.
    """

    def __init__(self, stego: LsbSteganography, cipher, order: list[str]):
        self.stego = stego
        self.cipher = cipher      # Objek SuperEncryption
        self.order = order        # Urutan lapisan, misal ["vigenere", "rail_fence", "aes"]

    def hide(self, cover_path: str | Path, output_path: str | Path, message: str) -> None:
        if not message:
            raise StegoError("Pesan rahasia tidak boleh kosong")
        terenkripsi = self.cipher.encrypt(message, self.order)
        self.stego.hide(cover_path, output_path, terenkripsi)

    def reveal(self, stego_path: str | Path) -> str:
        terenkripsi = self.stego.reveal(stego_path)
        return self.cipher.decrypt(terenkripsi, self.order)
