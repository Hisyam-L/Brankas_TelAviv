from __future__ import annotations

from pathlib import Path
import time
import numpy as np
import pytest

from auth.dongle import DongleManager, DongleStatus
from auth.face_auth import FaceAuth
from auth.password_auth import PasswordAuth
from auth.session import Session
from ui.dongle_gate import DongleGate
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


class FakeDongleManager:
    """Mock DongleManager untuk keperluan smoke test UI tanpa filesystem nyata."""

    def __init__(self, is_valid: bool = True, mount: str = "/media/usb_test", registered: bool = True):
        self._is_valid = is_valid
        self._mount = mount
        self._registered = registered

    def is_registered(self) -> bool:
        return self._registered

    def mounts_fn(self):
        return [self._mount] if self._is_valid else []

    def volume_id_fn(self, mount: str):
        return "FAKE-UUID-999"

    def register(self, mount: str, allow_overwrite: bool = False):
        self._registered = True
        self._mount = mount
        self._is_valid = True

    def verify(self) -> DongleStatus:
        if not self._registered:
            from auth.dongle import DongleError
            raise DongleError("Dongle belum didaftarkan atau data pendaftaran rusak")
        if self._is_valid:
            return DongleStatus(True, "Dongle valid", self._mount)
        return DongleStatus(False, "Dongle tidak terpasang")


class FakeFaceAuth:
    def __init__(self, should_match: bool = True):
        self.should_match = should_match
        self._enrolled_users: set[str] = {"alice"}

    def is_enrolled(self, username: str) -> bool:
        return username in self._enrolled_users

    def detect_faces(self, frame) -> list[tuple[int, int, int, int]]:
        return [(10, 10, 100, 100)]

    def verify(self, frame, expected_username: str | None = None) -> tuple[bool, float, str]:
        if self.should_match:
            return True, 45.0, f"Wajah cocok ({expected_username or 'test'})"
        return False, 90.0, "Wajah tidak cocok"

    def enroll(self, username: str, jumlah_sampel: int = 20) -> tuple[bool, str]:
        self._enrolled_users.add(username)
        return True, "Enrolled"


def test_main_window_pages_smoke():
    session = Session(username="Tester")
    win = MainWindow(session=session)
    win.withdraw()

    assert "catatan" in win.pages
    assert "berkas" in win.pages
    assert "sandi" in win.pages
    assert "foto" in win.pages
    assert "dokumen" in win.pages

    for page_key in ["catatan", "berkas", "sandi", "foto", "dokumen"]:
        win.select_page(page_key)

    win.destroy()


def test_main_window_change_dongle_dialog_smoke():
    session = Session(username="Tester")
    dongle = FakeDongleManager(is_valid=True)
    win = MainWindow(session=session, dongle_manager=dongle)
    win.withdraw()

    win._open_change_dongle_dialog()
    try:
        win.destroy()
    except Exception:
        pass


def test_dongle_gate_first_run_setup_smoke(tmp_path: Path):
    db_path = tmp_path / "auth_gate.db"
    auth = PasswordAuth(db_path=db_path)
    dongle = FakeDongleManager(registered=False)

    gate = DongleGate(manager=dongle, auth=auth)
    gate.withdraw()

    assert hasattr(gate, "mount_menu")
    assert hasattr(gate, "btn_register")
    assert gate.is_unlocked is False

    gate.mount_var.set("/media/usb_test")
    gate._handle_register()

    assert dongle.is_registered() is True
    assert gate.is_unlocked is True

    gate.destroy()


def test_dongle_gate_locked_when_users_exist_smoke(tmp_path: Path):
    db_path = tmp_path / "auth_gate_locked.db"
    auth = PasswordAuth(db_path=db_path)
    auth.register("bob", "PasswordKu123#")

    # Dongle belum terdaftar (misal data/dongle.json dihapus)
    dongle = FakeDongleManager(registered=False)

    gate = DongleGate(manager=dongle, auth=auth)
    gate.withdraw()

    # Harus menampilkan peringatan pelanggaran integritas dan mengunci
    assert not hasattr(gate, "btn_register")
    assert gate.is_unlocked is False

    gate.destroy()


def test_dongle_gate_verify_valid_smoke(tmp_path: Path):
    db_path = tmp_path / "auth_gate_ok.db"
    auth = PasswordAuth(db_path=db_path)
    dongle = FakeDongleManager(registered=True, is_valid=True)

    unlocked_mount = []
    def on_unlocked(mount: str):
        unlocked_mount.append(mount)

    gate = DongleGate(manager=dongle, auth=auth, on_unlocked=on_unlocked)
    gate.withdraw()

    assert gate.check_dongle() is True
    assert gate.is_unlocked is True

    gate.destroy()


def test_login_window_first_run_setup(tmp_path: Path):
    db_path = tmp_path / "smoke_auth.db"
    auth = PasswordAuth(db_path=db_path)
    dongle = FakeDongleManager(registered=True, is_valid=True)
    face = FakeFaceAuth()

    win = LoginWindow(auth=auth, dongle_manager=dongle, face_auth=face)
    win.withdraw()

    # Pastikan mode setup terbuka jika belum ada user
    assert hasattr(win, "setup_user_entry")
    assert win.setup_user_entry is not None

    win._setup_detect_dongle()
    assert win.setup_dongle_serial == "/media/usb_test"

    # Isi setup form
    win.setup_user_entry.insert(0, "alice")
    win.setup_pw_entry.set("SecretPass123#")
    win.setup_pw_confirm.set("SecretPass123#")

    win._handle_save_setup()
    assert auth.has_users() is True
    assert auth.verify("alice", "SecretPass123#") is True

    win.destroy()


def test_login_window_3_factor_flow(tmp_path: Path):
    db_path = tmp_path / "smoke_auth2.db"
    auth = PasswordAuth(db_path=db_path)
    auth.register("alice", "PasswordKu123#", dongle_serial="/media/usb_test")

    dongle = FakeDongleManager(registered=True, is_valid=True, mount="/media/usb_test")
    face = FakeFaceAuth(should_match=True)

    success_sessions: list[Session] = []

    def on_success(sess: Session):
        success_sessions.append(sess)

    win = LoginWindow(auth=auth, dongle_manager=dongle, face_auth=face, on_success=on_success)
    win.withdraw()

    assert win.current_step == 1

    # Step 1: Dongle
    win._handle_verify_dongle()
    # Tunggu background thread selesai
    for _ in range(50):
        win.update()
        if win.verified_dongle_serial:
            break
        time.sleep(0.05)

    assert win.verified_dongle_serial == "/media/usb_test"
    # Tunggu transisi advance_to_step
    for _ in range(30):
        win.update()
        if win.current_step == 2:
            break
        time.sleep(0.05)
    assert win.current_step == 2

    # Step 2: Face
    win.current_frame = np.zeros((200, 200, 3), dtype=np.uint8)
    win._handle_verify_face()
    for _ in range(50):
        win.update()
        if win.current_step == 3:
            break
        time.sleep(0.05)
    assert win.current_step == 3

    # Step 3: Password
    win.password_input.set("PasswordKu123#")
    win._handle_verify_password()
    for _ in range(50):
        win.update()
        if success_sessions:
            break
        time.sleep(0.05)

    assert len(success_sessions) == 1
    assert success_sessions[0].username == "alice"
    assert success_sessions[0].dongle_serial == "/media/usb_test"

    try:
        win.destroy()
    except Exception:
        pass


def test_login_window_lockout_after_failures(tmp_path: Path):
    db_path = tmp_path / "smoke_auth3.db"
    auth = PasswordAuth(db_path=db_path)
    auth.register("bob", "PasswordKu123#")

    dongle = FakeDongleManager(registered=True, is_valid=False)
    face = FakeFaceAuth(should_match=False)

    win = LoginWindow(auth=auth, dongle_manager=dongle, face_auth=face)
    win.withdraw()

    # Lakukan 3 kali kegagalan
    win._record_failure("test fail 1")
    assert win.failed_attempts == 1
    assert win.is_locked is False

    win._record_failure("test fail 2")
    assert win.failed_attempts == 2
    assert win.is_locked is False

    win._record_failure("test fail 3")
    assert win.failed_attempts == 3
    assert win.is_locked is True

    win.destroy()
