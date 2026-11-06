from __future__ import annotations

import os
from pathlib import Path

from auth.dongle import KeyFileDongle, SimulatedDongle, get_dongle_checker


def test_simulated_dongle_plug_and_unplug(tmp_path: Path):
    key_file = tmp_path / "dev.key"
    dongle = SimulatedDongle(key_path=key_file, serial="TEST-USB-123")

    # Pastikan awalnya file tidak ada
    os.environ.pop("SAFEVAULT_DEV", None)
    assert dongle.is_present() is False
    assert dongle.get_serial() is None

    # Tancapkan dongle
    dongle.plug_in()
    assert dongle.is_present() is True
    assert dongle.get_serial() == "TEST-USB-123"

    # Cabut dongle
    dongle.unplug()
    assert dongle.is_present() is False
    assert dongle.get_serial() is None


def test_key_file_dongle_verification():
    content = KeyFileDongle.generate_key_content("SERIAL_DONGLE_FLASH_DISK_99")
    assert KeyFileDongle.verify_key_content(content) is True

    # Manipulasi tanda tangan
    tampered = content[:-2] + "00"
    assert KeyFileDongle.verify_key_content(tampered) is False

    # Format salah
    assert KeyFileDongle.verify_key_content("hanyaserialtanpasignature") is False


def test_get_dongle_checker_env(monkeypatch):
    monkeypatch.setenv("SAFEVAULT_DEV", "1")
    checker = get_dongle_checker()
    assert checker.is_simulated is True
