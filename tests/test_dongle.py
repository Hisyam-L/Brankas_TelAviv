from __future__ import annotations

import json
import time
from pathlib import Path
import pytest

from auth.dongle import (
    DongleError,
    DongleManager,
    DongleWatcher,
    TOKEN_NAME,
)


def test_dongle_not_registered(tmp_path: Path):
    """1. Belum terdaftar -> DongleError saat verify."""
    reg_path = tmp_path / "dongle.json"
    mgr = DongleManager(registry_path=reg_path, mounts_fn=lambda: [], volume_id_fn=lambda m: None)
    assert mgr.is_registered() is False
    with pytest.raises(DongleError, match="Dongle belum didaftarkan"):
        mgr.verify()


def test_dongle_register_and_verify_valid(tmp_path: Path):
    """2. Pendaftaran dongle asli -> status valid."""
    reg_path = tmp_path / "app_data" / "dongle.json"
    drive_dir = tmp_path / "media" / "usb1"
    drive_dir.mkdir(parents=True)

    vol_map = {str(drive_dir): "VOL-UUID-1234"}
    current_mounts = [str(drive_dir)]

    mgr = DongleManager(
        registry_path=reg_path,
        mounts_fn=lambda: current_mounts,
        volume_id_fn=lambda m: vol_map.get(m),
    )

    # Daftarkan dongle
    mgr.register(str(drive_dir))
    assert mgr.is_registered() is True
    assert (drive_dir / TOKEN_NAME).exists()

    # Verifikasi dongle asli
    status = mgr.verify()
    assert status.ok is True
    assert status.message == "Dongle valid"
    assert status.mount == str(drive_dir)


def test_dongle_unplugged(tmp_path: Path):
    """3. Dongle dicabut -> ditolak ('Dongle tidak terpasang')."""
    reg_path = tmp_path / "dongle.json"
    drive_dir = tmp_path / "usb1"
    drive_dir.mkdir()

    vol_map = {str(drive_dir): "VOL-UUID-1234"}
    current_mounts = [str(drive_dir)]

    mgr = DongleManager(
        registry_path=reg_path,
        mounts_fn=lambda: current_mounts,
        volume_id_fn=lambda m: vol_map.get(m),
    )
    mgr.register(str(drive_dir))

    # Simulasi dongle dicabut
    current_mounts.clear()
    status = mgr.verify()
    assert status.ok is False
    assert "tidak terpasang" in status.message


def test_dongle_copied_to_different_drive(tmp_path: Path):
    """4. Token disalin ke drive lain (ID volume berbeda) -> ditolak."""
    reg_path = tmp_path / "dongle.json"
    drive1 = tmp_path / "usb1"
    drive2 = tmp_path / "usb2"
    drive1.mkdir()
    drive2.mkdir()

    vol_map = {str(drive1): "UUID-DRIVE-1", str(drive2): "UUID-DRIVE-2"}
    current_mounts = [str(drive1)]

    mgr = DongleManager(
        registry_path=reg_path,
        mounts_fn=lambda: current_mounts,
        volume_id_fn=lambda m: vol_map.get(m),
    )
    mgr.register(str(drive1))

    # Salin file token ke drive2
    token_src = drive1 / TOKEN_NAME
    token_dst = drive2 / TOKEN_NAME
    token_dst.write_text(token_src.read_text(encoding="utf-8"), encoding="utf-8")

    # Pasang drive2 (salinan) saja
    current_mounts[:] = [str(drive2)]
    status = mgr.verify()
    assert status.ok is False
    assert "tidak cocok" in status.message


def test_dongle_token_tampered(tmp_path: Path):
    """5. Isi token diubah -> ditolak."""
    reg_path = tmp_path / "dongle.json"
    drive = tmp_path / "usb"
    drive.mkdir()

    vol_map = {str(drive): "UUID-123"}
    mgr = DongleManager(
        registry_path=reg_path,
        mounts_fn=lambda: [str(drive)],
        volume_id_fn=lambda m: vol_map.get(m),
    )
    mgr.register(str(drive))

    token_file = drive / TOKEN_NAME
    data = json.loads(token_file.read_text(encoding="utf-8"))
    # Ubah secret
    data["secret"] = "0" * len(data["secret"])
    token_file.write_text(json.dumps(data), encoding="utf-8")

    status = mgr.verify()
    assert status.ok is False
    assert "tidak cocok" in status.message


def test_dongle_token_corrupted_not_json(tmp_path: Path):
    """6. File token rusak (bukan JSON) -> ditolak, tidak crash."""
    reg_path = tmp_path / "dongle.json"
    drive = tmp_path / "usb"
    drive.mkdir()

    vol_map = {str(drive): "UUID-123"}
    mgr = DongleManager(
        registry_path=reg_path,
        mounts_fn=lambda: [str(drive)],
        volume_id_fn=lambda m: vol_map.get(m),
    )
    mgr.register(str(drive))

    token_file = drive / TOKEN_NAME
    token_file.write_text("INI BUKAN JSON SAMA SEKALI $$$$$", encoding="utf-8")

    status = mgr.verify()
    assert status.ok is False
    # Harus ditolak dengan aman tanpa crash
    assert status.message in [
        "Dongle tidak terpasang",
        "Dongle ditemukan tetapi tidak cocok (salinan, rusak, atau bukan dongle ini)",
    ]


def test_dongle_reregister_without_permission_raises(tmp_path: Path):
    """7. Daftar ulang tanpa allow_overwrite -> DongleError."""
    reg_path = tmp_path / "dongle.json"
    drive = tmp_path / "usb"
    drive.mkdir()

    vol_map = {str(drive): "UUID-123"}
    mgr = DongleManager(
        registry_path=reg_path,
        mounts_fn=lambda: [str(drive)],
        volume_id_fn=lambda m: vol_map.get(m),
    )
    mgr.register(str(drive))

    with pytest.raises(DongleError, match="Dongle sudah terdaftar"):
        mgr.register(str(drive), allow_overwrite=False)


def test_dongle_reregister_with_permission_allowed(tmp_path: Path):
    """8. Daftar ulang dengan allow_overwrite=True -> dongle baru valid."""
    reg_path = tmp_path / "dongle.json"
    drive1 = tmp_path / "usb1"
    drive2 = tmp_path / "usb2"
    drive1.mkdir()
    drive2.mkdir()

    vol_map = {str(drive1): "UUID-1", str(drive2): "UUID-2"}
    current_mounts = [str(drive1)]

    mgr = DongleManager(
        registry_path=reg_path,
        mounts_fn=lambda: current_mounts,
        volume_id_fn=lambda m: vol_map.get(m),
    )
    mgr.register(str(drive1))
    assert mgr.verify().ok is True

    # Daftarkan ulang ke drive2 setelah login penuh
    current_mounts[:] = [str(drive2)]
    mgr.register(str(drive2), allow_overwrite=True)

    status = mgr.verify()
    assert status.ok is True
    assert status.mount == str(drive2)


def test_dongle_watcher_calls_on_lost_when_unplugged(tmp_path: Path):
    """9. Pemantau (DongleWatcher) memanggil callback saat dongle dicabut."""
    reg_path = tmp_path / "dongle.json"
    drive = tmp_path / "usb"
    drive.mkdir()

    vol_map = {str(drive): "UUID-WATCH"}
    current_mounts = [str(drive)]

    mgr = DongleManager(
        registry_path=reg_path,
        mounts_fn=lambda: current_mounts,
        volume_id_fn=lambda m: vol_map.get(m),
    )
    mgr.register(str(drive))

    lost_messages: list[str] = []

    def on_lost(msg: str):
        lost_messages.append(msg)

    watcher = DongleWatcher(mgr, on_lost, interval=0.05)
    watcher.start()

    # Pastikan awalnya belum terpanggil karena dongle masih ada
    time.sleep(0.12)
    assert len(lost_messages) == 0

    # Cabut dongle
    current_mounts.clear()
    time.sleep(0.15)
    watcher.stop()

    assert len(lost_messages) >= 1
    assert "tidak terpasang" in lost_messages[0]
