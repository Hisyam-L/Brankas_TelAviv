from __future__ import annotations

import numpy as np
from PIL import Image


class StegoError(Exception):
    """Error yang aman ditampilkan langsung ke pengguna di UI."""


class LsbSteganography:
    """Menyembunyikan teks di bit terakhir (LSB) tiap nilai warna piksel PNG."""

    _HEADER_BITS = 32  # 4 byte pertama menyimpan panjang pesan

    def _load(self, path):
        try:
            gambar = Image.open(path).convert("RGB")
        except (FileNotFoundError, OSError) as e:
            raise StegoError(f"Gambar tidak bisa dibuka: {path}") from e
        arr = np.array(gambar)
        return arr.shape, arr.flatten()

    def capacity(self, path) -> int:
        """Perkiraan jumlah byte pesan yang muat di gambar."""
        _, datar = self._load(path)
        return (len(datar) - self._HEADER_BITS) // 8

    def hide(self, cover_path, output_path, message: str) -> None:
        bentuk, datar = self._load(cover_path)

        data = message.encode("utf-8")
        muatan = len(data).to_bytes(4, "big") + data
        bit = np.unpackbits(np.frombuffer(muatan, dtype=np.uint8))

        if len(bit) > len(datar):
            raise StegoError("Pesan terlalu panjang untuk gambar ini")

        datar[: len(bit)] = (datar[: len(bit)] & 0xFE) | bit
        Image.fromarray(datar.reshape(bentuk)).save(output_path, format="PNG")

    def reveal(self, stego_path) -> str:
        _, datar = self._load(stego_path)

        panjang = int.from_bytes(np.packbits(datar[: self._HEADER_BITS] & 1).tobytes(), "big")
        if panjang == 0 or self._HEADER_BITS + panjang * 8 > len(datar):
            raise StegoError("Tidak ada pesan tersembunyi di gambar ini")

        bit = datar[self._HEADER_BITS : self._HEADER_BITS + panjang * 8] & 1
        try:
            return np.packbits(bit).tobytes().decode("utf-8")
        except UnicodeDecodeError as e:
            raise StegoError("Data di gambar bukan pesan yang valid") from e


class SecureStego:
    """Enkripsi dulu (super encrypt), baru disembunyikan di gambar.

    Dua objek digabung lewat composition, jadi masing-masing tetap
    bisa dipakai dan dites sendiri.
    """

    def __init__(self, stego: LsbSteganography, cipher, order: list[str]):
        self.stego = stego
        self.cipher = cipher      # objek SuperEncryption
        self.order = order        # urutan lapisan, misal ["vigenere", "rail_fence", "aes"]

    def hide(self, cover_path, output_path, message: str) -> None:
        terenkripsi = self.cipher.encrypt(message, self.order)
        self.stego.hide(cover_path, output_path, terenkripsi)

    def reveal(self, stego_path) -> str:
        terenkripsi = self.stego.reveal(stego_path)
        return self.cipher.decrypt(terenkripsi, self.order)