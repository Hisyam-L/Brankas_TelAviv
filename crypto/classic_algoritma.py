class VigenereCipher:
    def __init__(self, key: str, alphabet: str):
        if not key:
            raise ValueError("key must not be empty")
        if any(c not in alphabet for c in key):
            raise ValueError("key contains characters not in alphabet")
        self.key = key
        self.alphabet = alphabet
        self.index_of = {c: i for i, c in enumerate(alphabet)}

    def _shift(self, text: str, sign: int) -> str:
        result: list[str] = []
        key_pos = 0  # kunci hanya maju untuk karakter yang ada di alfabet
        n = len(self.alphabet)
        for char in text:
            if char not in self.index_of:
                result.append(char)
                continue
            key_index = self.index_of[self.key[key_pos % len(self.key)]]
            result.append(
                self.alphabet[(self.index_of[char] + sign * key_index) % n]
            )
            key_pos += 1
        return "".join(result)

    def encode(self, text: str) -> str:
        return self._shift(text, +1)

    def decode(self, text: str) -> str:
        return self._shift(text, -1)


class RailFenceCipher:
    def __init__(self, key: int):
        if key < 1:
            raise ValueError("key must be >= 1")
        self.key = key

    def _rail_pattern(self, length: int) -> list[int]:
        """Mengembalikan nomor rail untuk tiap posisi karakter."""
        if self.key == 1:
            return [0] * length
        pattern = []
        row, step = 0, 1
        for _ in range(length):
            pattern.append(row)
            if row == 0:
                step = 1
            elif row == self.key - 1:
                step = -1
            row += step
        return pattern

    def encryptRailFence(self, text: str) -> str:
        pattern = self._rail_pattern(len(text))
        order = sorted(range(len(text)), key=lambda i: (pattern[i], i))
        return "".join(text[i] for i in order)

    def decryptRailFence(self, cipher: str) -> str:
        pattern = self._rail_pattern(len(cipher))
        order = sorted(range(len(cipher)), key=lambda i: (pattern[i], i))
        result = [""] * len(cipher)
        for cipher_pos, original_pos in enumerate(order):
            result[original_pos] = cipher[cipher_pos]
        return "".join(result)