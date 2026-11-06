from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Session:
    """
    Representasi sesi login pengguna aktif di aplikasi SafeVault.
    Menyimpan username, serial dongle yang digunakan saat login,
    dan kunci sesi sementara di memori (dibersihkan saat logout).
    """

    username: str
    dongle_serial: str | None = None
    login_time: datetime = field(default_factory=datetime.now)
    active_keys: dict[str, str] = field(default_factory=dict)

    def set_key(self, key_name: str, key_val: str) -> None:
        """Menyimpan kunci sementara di memori selama sesi berlangsung."""
        self.active_keys[key_name] = key_val

    def get_key(self, key_name: str) -> str | None:
        """Mengambil kunci tersimpan dalam sesi."""
        return self.active_keys.get(key_name)

    def clear(self) -> None:
        """Menghapus seluruh kunci dan data sensitif dari memori saat logout."""
        self.active_keys.clear()
        self.dongle_serial = None
