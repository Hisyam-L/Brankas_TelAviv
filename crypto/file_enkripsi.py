from __future__ import annotations

import os
import struct
from pathlib import Path

from Crypto.Cipher import ChaCha20_Poly1305
from Crypto.Protocol.KDF import scrypt
from Crypto.Random import get_random_bytes

from config import CHUNK_SIZE, SALT_LEN, SCRYPT_N, SCRYPT_P, SCRYPT_R


class FileCipherError(Exception):
    """Error yang aman ditampilkan langsung ke pengguna di UI."""


class ChaChaFileCipher:
    """
    Enkripsi/dekripsi file per chunk dengan ChaCha20-Poly1305 dan penurunan kunci scrypt.

    Format file hasil enkripsi:
        salt (16 byte)
        lalu berulang per chunk:
            flag_terakhir (1) | panjang (4) | nonce (12) | tag (16) | isi (panjang)

    Nomor urut chunk dan flag_terakhir diotentikasi sebagai AAD (Additional Authenticated Data),
    sehingga chunk yang tertukar, dihapus, disisipkan, atau file terpotong akan terdeteksi
    saat dekripsi.
    """

    NONCE_LEN = 12
    TAG_LEN = 16
    HEADER_LEN = 5  # flag (1) + panjang (4)

    def __init__(self, password: str, chunk_size: int = CHUNK_SIZE):
        if not password:
            raise FileCipherError("Password tidak boleh kosong")
        if chunk_size < 1:
            raise FileCipherError("Ukuran chunk harus >= 1")
        self.password = password
        self.chunk_size = chunk_size

    # ------------------------------------------------------------ helper
    @classmethod
    def _derive_key(cls, password: str, salt: bytes) -> bytes:
        return scrypt(
            password.encode("utf-8"),
            salt,
            key_len=32,
            N=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
        )

    @staticmethod
    def _aad(counter: int, is_last: bool) -> bytes:
        return struct.pack(">QB", counter, 1 if is_last else 0)

    def _write_chunk(self, dst, key: bytes, counter: int, is_last: bool, data: bytes) -> None:
        cipher = ChaCha20_Poly1305.new(key=key)  # Nonce acak unik tiap chunk
        cipher.update(self._aad(counter, is_last))
        isi, tag = cipher.encrypt_and_digest(data)
        dst.write(
            bytes([1 if is_last else 0])
            + struct.pack(">I", len(isi))
            + cipher.nonce
            + tag
            + isi
        )

    @staticmethod
    def _read_exact(src, n: int) -> bytes:
        data = src.read(n)
        if len(data) != n:
            raise FileCipherError("File terenkripsi rusak atau terpotong")
        return data

    @staticmethod
    def _cleanup(path: str | Path) -> None:
        try:
            os.remove(path)
        except OSError:
            pass

    # ------------------------------------------------------------ public
    def encrypt_file(
        self,
        path_asal: str | Path,
        path_hasil: str | Path,
        progress_callback: callable | None = None,
    ) -> None:
        path_asal = Path(path_asal)
        path_hasil = Path(path_hasil)
        salt = get_random_bytes(SALT_LEN)
        key = self._derive_key(self.password, salt)

        total_bytes = path_asal.stat().st_size if path_asal.exists() else 0
        processed_bytes = 0

        try:
            with open(path_asal, "rb") as src, open(path_hasil, "wb") as dst:
                dst.write(salt)
                counter = 0
                current = src.read(self.chunk_size)
                while True:
                    processed_bytes += len(current)
                    nxt = src.read(self.chunk_size)  # Baca ke depan untuk memastikan apakah ini chunk terakhir
                    is_last = not nxt
                    self._write_chunk(dst, key, counter, is_last, current)

                    if progress_callback and total_bytes > 0:
                        progress = min(1.0, processed_bytes / total_bytes)
                        progress_callback(progress)

                    if is_last:
                        break
                    current = nxt
                    counter += 1
        except OSError as e:
            self._cleanup(path_hasil)
            raise FileCipherError(f"Gagal membaca/menulis file: {e}") from e

    def decrypt_file(
        self,
        path_asal: str | Path,
        path_hasil: str | Path,
        progress_callback: callable | None = None,
    ) -> None:
        path_asal = Path(path_asal)
        path_hasil = Path(path_hasil)
        total_bytes = path_asal.stat().st_size if path_asal.exists() else 0
        processed_bytes = 0

        try:
            with open(path_asal, "rb") as src, open(path_hasil, "wb") as dst:
                salt = self._read_exact(src, SALT_LEN)
                key = self._derive_key(self.password, salt)
                counter = 0
                processed_bytes += SALT_LEN

                while True:
                    header = src.read(self.HEADER_LEN)
                    if len(header) != self.HEADER_LEN:
                        raise FileCipherError("File terenkripsi rusak atau terpotong")
                    flag, panjang = struct.unpack(">BI", header)
                    if flag not in (0, 1):
                        raise FileCipherError("Format file terenkripsi tidak valid")
                    if panjang > self.chunk_size:
                        raise FileCipherError("Ukuran chunk tidak valid (file tidak sesuai)")

                    nonce = self._read_exact(src, self.NONCE_LEN)
                    tag = self._read_exact(src, self.TAG_LEN)
                    isi = self._read_exact(src, panjang)

                    processed_bytes += self.HEADER_LEN + self.NONCE_LEN + self.TAG_LEN + panjang
                    if progress_callback and total_bytes > 0:
                        progress = min(1.0, processed_bytes / total_bytes)
                        progress_callback(progress)

                    is_last = flag == 1
                    cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
                    cipher.update(self._aad(counter, is_last))
                    try:
                        dst.write(cipher.decrypt_and_verify(isi, tag))
                    except ValueError as e:
                        raise FileCipherError(
                            "Dekripsi gagal: password salah atau file telah diubah"
                        ) from e

                    if is_last:
                        if src.read(1):
                            raise FileCipherError("Ada data tambahan setelah chunk terakhir")
                        break
                    counter += 1
        except FileCipherError:
            self._cleanup(path_hasil)
            raise
        except OSError as e:
            self._cleanup(path_hasil)
            raise FileCipherError(f"Gagal membaca/menulis file: {e}") from e
