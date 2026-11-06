from __future__ import annotations

import hmac
import hashlib
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from config import DATA_DIR, DONGLE_KEY_FILENAME


class DongleError(Exception):
    """Error domain pemeriksaan dongle fisik."""


class DongleChecker(ABC):
    """Antarmuka dasar untuk pemeriksaan dongle fisik."""

    @abstractmethod
    def is_present(self) -> bool:
        """Mengecek apakah dongle terpasang."""
        ...

    @abstractmethod
    def get_serial(self) -> str | None:
        """Mengambil nomor seri unik dongle yang terpasang."""
        ...

    @property
    def is_simulated(self) -> bool:
        """Menandakan apakah dongle ini adalah dongle simulasi (dev mode)."""
        return False


class UsbSerialDongle(DongleChecker):
    """
    Pemeriksaan dongle USB berdasarkan serial number perangkat fisik.
    Mendukung Linux via pyudev dan Windows fallback.
    """

    def __init__(self, expected_serial: str | None = None):
        self.expected_serial = expected_serial

    def list_connected_serials(self) -> list[dict[str, str]]:
        """Mendeteksi daftar perangkat USB yang sedang terhubung ke komputer."""
        devices: list[dict[str, str]] = []
        if sys.platform.startswith("linux"):
            try:
                import pyudev
                context = pyudev.Context()
                # 1. Periksa USB block devices (Flashdisk / Removable USB Storage fisik)
                for dev in context.list_devices(subsystem="block"):
                    if dev.get("ID_BUS") == "usb" and dev.get("DEVTYPE") in ("disk", "partition"):
                        serial = dev.get("ID_SERIAL_SHORT") or dev.get("ID_SERIAL")
                        if serial and not any(d["serial"] == serial for d in devices):
                            devices.append({
                                "serial": serial,
                                "vendor": dev.get("ID_VENDOR", "USB"),
                                "model": dev.get("ID_MODEL", "Flashdisk"),
                                "node": dev.device_node or "",
                            })

                # 2. Jika bukan block storage, izinkan hanya USB security token / dongle eksternal
                # (Abaikan root hub internal Linux, webcam laptop, bluetooth, dan keyboard/touchpad)
                if not devices:
                    for dev in context.list_devices(subsystem="usb"):
                        if dev.get("DEVTYPE") == "usb_device":
                            vendor_id = (dev.get("ID_VENDOR_ID") or "").lower()
                            driver = dev.get("DRIVER") or ""
                            dev_class = dev.get("bDeviceClass") or ""

                            # Filter keluar perangkat internal motherboard
                            # 1d6b = Linux Foundation USB root hub
                            if vendor_id in ("1d6b", ""):
                                continue
                            # 0e = video/webcam, e0 = bluetooth, 09 = hub
                            if dev_class in ("0e", "e0", "09"):
                                continue
                            if driver in ("uvcvideo", "btusb", "hub"):
                                continue

                            # Khusus perangkat penyimpanan USB eksternal atau hardware security key
                            if driver == "usb-storage" or dev.get("ID_DRIVE_FLASH") == "1":
                                serial = dev.get("ID_SERIAL_SHORT") or dev.get("ID_SERIAL")
                                if serial and not any(d["serial"] == serial for d in devices):
                                    devices.append({
                                        "serial": serial,
                                        "vendor": dev.get("ID_VENDOR_FROM_DATABASE") or dev.get("ID_VENDOR", "USB"),
                                        "model": dev.get("ID_MODEL_FROM_DATABASE") or dev.get("ID_MODEL", "Dongle"),
                                        "node": dev.device_node or "",
                                    })
            except Exception:
                pass
        return devices

    def get_serial(self) -> str | None:
        serials = self.list_connected_serials()
        if not serials:
            return None
        if self.expected_serial:
            for d in serials:
                if d["serial"] == self.expected_serial:
                    return d["serial"]
            return None
        return serials[0]["serial"]

    def is_present(self) -> bool:
        return self.get_serial() is not None


class KeyFileDongle(DongleChecker):
    """
    Pemeriksaan dongle berbasis berkas kunci otentikasi (.safevault.key) pada drive eksternal.
    Berkas kunci diverifikasi menggunakan HMAC-SHA256.
    """

    HMAC_SECRET = b"SafeVault_Dongle_Authentication_Secret_2026"

    def __init__(self, key_filename: str = DONGLE_KEY_FILENAME):
        self.key_filename = key_filename

    def _find_key_files(self) -> list[Path]:
        found: list[Path] = []
        search_dirs: list[Path] = []

        # Lokasi mount umum di Linux
        if sys.platform.startswith("linux"):
            for base in ["/media", "/run/media", "/mnt"]:
                p = Path(base)
                if p.exists():
                    search_dirs.extend([d for d in p.rglob(self.key_filename) if d.is_file()])

        return search_dirs

    @classmethod
    def generate_key_content(cls, serial_seed: str) -> str:
        """Membuat tanda tangan kriptografis berkas kunci dongle."""
        sig = hmac.new(cls.HMAC_SECRET, serial_seed.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{serial_seed}:{sig}"

    @classmethod
    def verify_key_content(cls, content: str) -> bool:
        """Memvalidasi isi berkas kunci."""
        parts = content.strip().split(":")
        if len(parts) != 2:
            return False
        seed, sig = parts
        expected = hmac.new(cls.HMAC_SECRET, seed.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)

    def get_serial(self) -> str | None:
        key_files = self._find_key_files()
        for kf in key_files:
            try:
                content = kf.read_text(encoding="utf-8").strip()
                if self.verify_key_content(content):
                    return content.split(":")[0]
            except OSError:
                continue
        return None

    def is_present(self) -> bool:
        return self.get_serial() is not None


class SimulatedDongle(DongleChecker):
    """
    Dongle simulasi untuk pengujian lokal (development mode).
    HANYA aktif jika variabel lingkungan SAFEVAULT_DEV=1 disetel.
    Diberikan peringatan keras di UI bila mode ini aktif.
    """

    SIMULATED_KEY_FILE = DATA_DIR / "dev_dongle.key"
    DEFAULT_SERIAL = "SIMULATED-DEV-DONGLE-9999"

    def __init__(self, key_path: Path | None = None, serial: str = DEFAULT_SERIAL):
        self.key_path = key_path or self.SIMULATED_KEY_FILE
        self.serial = serial

    @property
    def is_simulated(self) -> bool:
        return True

    def is_present(self) -> bool:
        # Dongle simulasi dianggap hadir jika file dev_dongle.key ada atau mode dev aktif
        return self.key_path.exists() or os.environ.get("SAFEVAULT_DEV") == "1"

    def get_serial(self) -> str | None:
        if self.is_present():
            if self.key_path.exists():
                try:
                    return self.key_path.read_text(encoding="utf-8").strip() or self.serial
                except OSError:
                    pass
            return self.serial
        return None

    def plug_in(self) -> None:
        """Membuat file simulasi dongle terpasang."""
        self.key_path.write_text(self.serial, encoding="utf-8")

    def unplug(self) -> None:
        """Menghapus file simulasi dongle tercabut."""
        try:
            self.key_path.unlink(missing_ok=True)
        except OSError:
            pass


def get_dongle_checker(expected_serial: str | None = None) -> DongleChecker:
    """
    Factory untuk mendapatkan implementasi DongleChecker yang sesuai dengan lingkungan.
    """
    if os.environ.get("SAFEVAULT_DEV") == "1":
        return SimulatedDongle(serial=expected_serial or SimulatedDongle.DEFAULT_SERIAL)
    return UsbSerialDongle(expected_serial=expected_serial)
