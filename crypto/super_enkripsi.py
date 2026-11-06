from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from pathlib import Path

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA1, SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

from config import PBKDF2_ITERATIONS, SALT_LEN
from crypto.classic_algoritma import RailFenceCipher, VigenereCipher

# Alfabet Vigenère yang mendukung output Base64 dari AES beserta spasi dan simbol umum
ALPHABET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789 +/="
)


class CipherError(Exception):
    """Error domain enkripsi yang aman ditampilkan langsung ke pengguna di UI."""


def generate_rsa_keypair(bits: int = 2048) -> tuple[RSA.RsaKey, RSA.RsaKey]:
    """Menghasilkan pasangan kunci RSA publik dan privat."""
    private_key = RSA.generate(bits)
    return private_key, private_key.publickey()


# ---------------------------------------------------------------- Layers
class Layer(ABC):
    name: str   # ID unik lapisan
    label: str  # Nama deskriptif untuk tampilan antarmuka

    @abstractmethod
    def encrypt(self, text: str) -> str: ...

    @abstractmethod
    def decrypt(self, text: str) -> str: ...


class VigenereLayer(Layer):
    """
    Lapisan cipher subtitusi polialfabetik klasik (Vigenère).
    Catatan keamanan: Jika kunci salah pada proses dekripsi, algoritma tidak memicu
    error, melainkan menghasilkan teks teracak (karakteristik alami cipher klasik).
    """
    name = "vigenere"
    label = "Vigenère Cipher (Klasik)"

    def __init__(self, key: str, alphabet: str = ALPHABET):
        try:
            self._cipher = VigenereCipher(key, alphabet)
        except ValueError as e:
            raise CipherError(f"Kunci Vigenère tidak valid: {e}") from e

    def encrypt(self, text: str) -> str:
        return self._cipher.encode(text)

    def decrypt(self, text: str) -> str:
        return self._cipher.decode(text)


class RailFenceLayer(Layer):
    """
    Lapisan cipher transposisi klasik (Rail Fence / Zig-Zag).
    Catatan keamanan: Kunci harus berupa bilangan bulat >= 1. Kunci salah menghasilkan
    urutan karakter teracak tanpa error integritas.
    """
    name = "rail_fence"
    label = "Rail Fence Cipher (Transposisi)"

    def __init__(self, key: int | str):
        try:
            int_key = int(key)
            if int_key < 1:
                raise ValueError("Nilai harus >= 1")
            self._cipher = RailFenceCipher(int_key)
        except (ValueError, TypeError) as e:
            raise CipherError("Kunci Rail Fence harus bilangan bulat >= 1") from e

    def encrypt(self, text: str) -> str:
        return self._cipher.encryptRailFence(text)

    def decrypt(self, text: str) -> str:
        return self._cipher.decryptRailFence(text)


class AesLayer(Layer):
    """
    Lapisan cipher simetris modern AES-256-GCM terotentikasi.
    Kunci diturunkan dari password menggunakan PBKDF2-HMAC-SHA256.
    Tag autentikasi (GCM) memverifikasi integritas: password salah atau ciphertext
    dimanipulasi akan langsung memicu CipherError.
    """
    name = "aes"
    label = "AES-256-GCM (Modern Terotentikasi)"

    def __init__(self, password: str):
        if not password:
            raise CipherError("Password AES tidak boleh kosong")
        self.password = password

    def encrypt(self, text: str) -> str:
        salt = get_random_bytes(SALT_LEN)
        key = PBKDF2(
            self.password,
            salt,
            dkLen=32,
            count=PBKDF2_ITERATIONS,
            hmac_hash_module=SHA256,
        )
        aes = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = aes.encrypt_and_digest(text.encode("utf-8"))
        # Format payload: salt (16 byte) + nonce (16 byte) + tag (16 byte) + ciphertext
        blob = salt + aes.nonce + tag + ciphertext
        return base64.b64encode(blob).decode("ascii")

    def decrypt(self, text: str) -> str:
        try:
            blob = base64.b64decode(text, validate=True)
            if len(blob) < SALT_LEN + 16 + 16:
                raise CipherError("Ukuran payload AES tidak mencukupi")
            salt = blob[:SALT_LEN]
            nonce = blob[SALT_LEN : SALT_LEN + 16]
            tag = blob[SALT_LEN + 16 : SALT_LEN + 32]
            ciphertext = blob[SALT_LEN + 32 :]

            # Coba terlebih dahulu dengan PBKDF2 HMAC-SHA256
            try:
                key = PBKDF2(
                    self.password,
                    salt,
                    dkLen=32,
                    count=PBKDF2_ITERATIONS,
                    hmac_hash_module=SHA256,
                )
                aes = AES.new(key, AES.MODE_GCM, nonce=nonce)
                return aes.decrypt_and_verify(ciphertext, tag).decode("utf-8")
            except (ValueError, Exception):
                # Fallback ke HMAC-SHA1 untuk kompatibilitas data lama jika ada
                key_legacy = PBKDF2(
                    self.password,
                    salt,
                    dkLen=32,
                    count=PBKDF2_ITERATIONS,
                    hmac_hash_module=SHA1,
                )
                aes_legacy = AES.new(key_legacy, AES.MODE_GCM, nonce=nonce)
                return aes_legacy.decrypt_and_verify(ciphertext, tag).decode("utf-8")
        except (ValueError, Exception) as e:
            raise CipherError("Dekripsi AES gagal: password salah atau data rusak") from e


# -------------------------------------------------------------- Pipeline
class SuperEncryption:
    """
    Pipeline super enkripsi menggabungkan beberapa lapisan cipher secara berurutan.
    Urutan default: Vigenère (substitusi) -> Rail Fence (transposisi) -> AES-256-GCM (modern).
    Dekripsi dilakukan dengan urutan kebalikan (AES -> Rail Fence -> Vigenère).
    """

    def __init__(self, layers: list[Layer]):
        self.layers = {layer.name: layer for layer in layers}
        if len(self.layers) != len(layers):
            raise CipherError("Nama lapisan tidak boleh duplikat")

    def available_layers(self) -> list[dict[str, str]]:
        """Mengambil daftar lapisan yang tersedia untuk UI."""
        return [{"name": l.name, "label": l.label} for l in self.layers.values()]

    def _resolve(self, order: list[str]) -> list[Layer]:
        if not order:
            raise CipherError("Urutan lapisan tidak boleh kosong")
        unknown = [n for n in order if n not in self.layers]
        if unknown:
            raise CipherError(f"Lapisan tidak dikenal: {', '.join(unknown)}")
        return [self.layers[n] for n in order]

    def encrypt(self, text: str, order: list[str]) -> str:
        for layer in self._resolve(order):
            text = layer.encrypt(text)
        return text

    def decrypt(
        self, text: str, order: list[str], order_is_decrypt_order: bool = False
    ) -> str:
        """
        Default: `order` adalah urutan saat enkripsi, otomatis dibalik untuk proses dekripsi.
        Jika order_is_decrypt_order=True, lapisan dieksekusi sesuai urutan yang diberikan.
        """
        layers = self._resolve(order)
        if not order_is_decrypt_order:
            layers = layers[::-1]
        for layer in layers:
            text = layer.decrypt(text)
        return text
