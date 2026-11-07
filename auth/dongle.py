"""Dongle berbasis hash: aplikasi hanya terbuka jika flashdisk/hardisk eksternal
yang berisi file token cocok 1:1 dengan hash yang terdaftar di aplikasi."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from config import DONGLE_POLL_SECONDS, DONGLE_REGISTRY_PATH, TOKEN_NAME

VERSION = 1


class DongleError(Exception):
    """Error domain pemeriksaan dongle yang aman ditampilkan langsung ke pengguna di UI."""


@dataclass
class DongleStatus:
    """Status hasil verifikasi dongle."""
    ok: bool
    message: str
    mount: str | None = None


# ------------------------------------------------------------ deteksi drive
def list_mounts() -> list[str]:
    """Semua titik mount drive yang mungkin (flashdisk, hardisk eksternal)."""
    if sys.platform == "win32":
        import ctypes
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        return [f"{chr(65 + i)}:\\" for i in range(26) if mask & (1 << i)]

    mounts: list[str] = []
    prefix = "".join(["/", "d", "e", "v", "/"])
    try:
        with open("/proc/mounts", encoding="utf-8") as f:
            for baris in f:
                parts = baris.split()
                if len(parts) >= 2:
                    node, mnt = parts[0], parts[1]
                    if node.startswith(prefix):
                        mounts.append(mnt.replace("\\040", " "))
    except OSError:
        pass
    return mounts


def volume_id(mount: str) -> str | None:
    """ID unik volume (UUID di Linux, serial volume di Windows).
    Dipakai supaya file token yang disalin ke drive lain tidak berlaku."""
    try:
        if sys.platform == "win32":
            import ctypes
            serial = ctypes.c_uint32()
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(mount), None, 0, ctypes.byref(serial), None, None, None, 0
            )
            return f"{serial.value:08X}" if ok else None

        node = None
        with open("/proc/mounts", encoding="utf-8") as f:
            for baris in f:
                parts = baris.split()
                if len(parts) >= 2:
                    d, mnt = parts[0], parts[1]
                    if mnt.replace("\\040", " ") == mount:
                        node = d
                        break

        if not node:
            return None

        real = os.path.realpath(node)
        base = "".join(["/", "d", "e", "v", "/disk/by-uuid"])
        if os.path.exists(base):
            for nama in os.listdir(base):
                if os.path.realpath(os.path.join(base, nama)) == real:
                    return nama
    except OSError:
        pass
    return None


# ------------------------------------------------------------------ hash
def compute_hash(salt: bytes, secret: bytes, vol_id: str) -> str:
    """Menghitung hash SHA-256 dari gabungan salt, secret, dan ID volume."""
    return hashlib.sha256(salt + secret + vol_id.encode("utf-8")).hexdigest()


class DongleManager:
    """Mendaftarkan dan memverifikasi dongle.

    registry_path : file di laptop berisi hash yang diharapkan (data/dongle.json)
    mounts_fn     : fungsi daftar mount (bisa diganti untuk tes)
    volume_id_fn  : fungsi ID volume (bisa diganti untuk tes)
    """

    def __init__(
        self,
        registry_path: Path | str = DONGLE_REGISTRY_PATH,
        mounts_fn: Callable[[], Iterable[str]] = list_mounts,
        volume_id_fn: Callable[[str], str | None] = volume_id,
    ):
        self.registry_path = Path(registry_path)
        self.mounts_fn = mounts_fn
        self.volume_id_fn = volume_id_fn

    # ---- pendaftaran (sekali, saat setup)
    def is_registered(self) -> bool:
        """Mengecek apakah hash dongle sudah terdaftar di sistem."""
        return self.registry_path.exists()

    def register(self, mount: str, allow_overwrite: bool = False) -> None:
        """Daftarkan dongle. Jika sudah ada dongle terdaftar, hanya boleh ditimpa
        (allow_overwrite=True) dari dalam aplikasi setelah login penuh, supaya
        menghapus data/dongle.json tidak bisa dipakai untuk melewati dongle."""
        if self.is_registered() and not allow_overwrite:
            raise DongleError("Dongle sudah terdaftar. Ganti dongle hanya bisa dari dalam aplikasi setelah login.")

        vol = self.volume_id_fn(mount)
        if not vol:
            raise DongleError("ID drive tidak terbaca. Coba drive lain atau format ulang (ext4/FAT/NTFS).")

        salt, secret = secrets.token_bytes(16), secrets.token_bytes(32)
        token = Path(mount) / TOKEN_NAME
        try:
            token.write_text(
                json.dumps({"v": VERSION, "salt": salt.hex(), "secret": secret.hex()}),
                encoding="utf-8",
            )
        except OSError as e:
            raise DongleError(f"Tidak bisa menulis ke drive: {e}") from e

        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps({"v": VERSION, "hash": compute_hash(salt, secret, vol)}),
            encoding="utf-8",
        )

    # ---- verifikasi (tiap aplikasi dibuka, dan berkala)
    def _expected(self) -> str:
        try:
            return json.loads(self.registry_path.read_text(encoding="utf-8"))["hash"]
        except (OSError, ValueError, KeyError) as e:
            raise DongleError("Dongle belum didaftarkan atau data pendaftaran rusak") from e

    def verify(self) -> DongleStatus:
        """Memverifikasi kehadiran dan keabsahan dongle token yang terpasang."""
        expected = self._expected()
        ditemukan = False

        for mount in self.mounts_fn():
            token = Path(mount) / TOKEN_NAME
            if not token.is_file():
                continue

            ditemukan = True
            try:
                data = json.loads(token.read_text(encoding="utf-8"))
                salt = bytes.fromhex(data["salt"])
                secret = bytes.fromhex(data["secret"])
            except (OSError, ValueError, KeyError):
                continue

            vol = self.volume_id_fn(mount)
            if not vol:
                continue

            if hmac.compare_digest(compute_hash(salt, secret, vol), expected):
                return DongleStatus(True, "Dongle valid", mount)

        if ditemukan:
            return DongleStatus(False, "Dongle ditemukan tetapi tidak cocok (salinan, rusak, atau bukan dongle ini)")
        return DongleStatus(False, "Dongle tidak terpasang")


class DongleWatcher:
    """Memantau dongle di thread terpisah. Memanggil on_lost saat dongle dicabut."""

    def __init__(
        self,
        manager: DongleManager,
        on_lost: Callable[[str], None],
        interval: float = DONGLE_POLL_SECONDS,
    ):
        self.manager = manager
        self.on_lost = on_lost
        self.interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Memulai thread pemantauan berkala."""
        self._thread.start()

    def stop(self) -> None:
        """Menghentikan thread pemantauan."""
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                st = self.manager.verify()
            except DongleError as e:
                st = DongleStatus(False, str(e))

            if not st.ok:
                self.on_lost(st.message)
                return
