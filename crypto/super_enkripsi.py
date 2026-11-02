from __future__ import annotations
from Crypto.Protocol.KDF import PBKDF2

import base64
from abc import ABC, abstractmethod

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

from crypto.classic_algoritma import RailFenceCipher, VigenereCipher

# "+/=" ikut dimasukkan supaya Vigenere juga bisa mengenkripsi output base64 dari AES
ALPHABET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789 +/="
)


class CipherError(Exception):
    """Error yang aman ditampilkan langsung ke pengguna di UI."""


def generate_rsa_keypair(bits: int = 2048) -> tuple[RSA.RsaKey, RSA.RsaKey]:
    private_key = RSA.generate(bits)
    return private_key, private_key.publickey()


# ---------------------------------------------------------------- Layers
class Layer(ABC):
    name: str   # id unik, dipakai di daftar urutan
    label: str  # nama yang ditampilkan di UI

    @abstractmethod
    def encrypt(self, text: str) -> str: ...

    @abstractmethod
    def decrypt(self, text: str) -> str: ...


class VigenereLayer(Layer):
    name = "vigenere"
    label = "Vigenère Cipher"

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
    name = "rail_fence"
    label = "Rail Fence Cipher"

    def __init__(self, key: int):
        try:
            self._cipher = RailFenceCipher(int(key))
        except (ValueError, TypeError) as e:
            raise CipherError("Kunci Rail Fence harus bilangan bulat >= 1") from e

    def encrypt(self, text: str) -> str:
        return self._cipher.encryptRailFence(text)

    def decrypt(self, text: str) -> str:
        return self._cipher.decryptRailFence(text)



class AesLayer(Layer):
    name = "aes"
    label = "AES-256-GCM (password)"

    def __init__(self, password: str):
        if not password:
            raise CipherError("Password AES tidak boleh kosong")
        self.password = password

    def encrypt(self, text: str) -> str:
        salt = get_random_bytes(16)
        key = PBKDF2(self.password, salt, dkLen=32, count=100_000)
        aes = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = aes.encrypt_and_digest(text.encode("utf-8"))
        return base64.b64encode(salt + aes.nonce + tag + ciphertext).decode("ascii")

    def decrypt(self, text: str) -> str:
        try:
            blob = base64.b64decode(text, validate=True)
            salt, nonce, tag, ciphertext = blob[:16], blob[16:32], blob[32:48], blob[48:]
            key = PBKDF2(self.password, salt, dkLen=32, count=100_000)
            aes = AES.new(key, AES.MODE_GCM, nonce=nonce)
            return aes.decrypt_and_verify(ciphertext, tag).decode("utf-8")
        except ValueError as e:
            raise CipherError("Dekripsi AES gagal: password salah atau data rusak") from e

# -------------------------------------------------------------- Pipeline
class SuperEncryption:
    def __init__(self, layers: list[Layer]):
        self.layers = {layer.name: layer for layer in layers}
        if len(self.layers) != len(layers):
            raise CipherError("Nama lapisan tidak boleh duplikat")

    def available_layers(self) -> list[dict[str, str]]:
        """Untuk mengisi pilihan di UI (dropdown / checkbox)."""
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
        Default: `order` = urutan yang dipakai saat ENKRIPSI, otomatis dibalik.
        Jika order_is_decrypt_order=True: `order` dipakai apa adanya,
        yaitu urutan lapisan yang dibuka satu per satu.
        """
        layers = self._resolve(order)
        if not order_is_decrypt_order:
            layers = layers[::-1]
        for layer in layers:
            text = layer.decrypt(text)
        return text
