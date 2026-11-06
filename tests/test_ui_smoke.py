from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from auth.dongle import DongleChecker
from auth.face_auth import FaceAuth
from auth.password_auth import PasswordAuth
from auth.session import Session
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


class FakeDongle(DongleChecker):
    def __init__(self, serial: str = "TEST-USB-999", present: bool = True, simulated: bool = True):
        self._serial = serial
        self._present = present
        self._simulated = simulated

    def is_present(self) -> bool:
        return self._present

    def get_serial(self) -> str | None:
        return self._serial if self._present else None

    @property
    def is_simulated(self) -> bool:
        return self._simulated


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


def test_login_window_first_run_setup(tmp_path: Path):
    db_path = tmp_path / "smoke_auth.db"
    auth = PasswordAuth(db_path=db_path)
    dongle = FakeDongle()
    face = FakeFaceAuth()

    win = LoginWindow(auth=auth, dongle_checker=dongle, face_auth=face)
    win.withdraw()

    # Pastikan mode setup terbuka jika belum ada user
    assert hasattr(win, "setup_user_entry")
    assert win.setup_user_entry is not None

    win._setup_detect_dongle()
    assert win.setup_dongle_serial == "TEST-USB-999"

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
    auth.register("alice", "PasswordKu123#", dongle_serial="TEST-USB-999")

    dongle = FakeDongle(serial="TEST-USB-999", present=True)
    face = FakeFaceAuth(should_match=True)

    success_sessions: list[Session] = []

    def on_success(sess: Session):
        success_sessions.append(sess)

    win = LoginWindow(auth=auth, dongle_checker=dongle, face_auth=face, on_success=on_success)
    win.withdraw()

    assert win.current_step == 1

    # Step 1: Dongle
    win._handle_verify_dongle()
    # Tunggu background thread selesai
    for _ in range(50):
        win.update()
        if win.verified_dongle_serial:
            break
        import time; time.sleep(0.05)

    assert win.verified_dongle_serial == "TEST-USB-999"
    # Tunggu transisi advance_to_step
    for _ in range(30):
        win.update()
        if win.current_step == 2:
            break
        import time; time.sleep(0.05)
    assert win.current_step == 2

    # Step 2: Face
    win.current_frame = np.zeros((200, 200, 3), dtype=np.uint8)
    win._handle_verify_face()
    for _ in range(50):
        win.update()
        if win.current_step == 3:
            break
        import time; time.sleep(0.05)
    assert win.current_step == 3

    # Step 3: Password
    win.password_input.set("PasswordKu123#")
    win._handle_verify_password()
    for _ in range(50):
        win.update()
        if success_sessions:
            break
        import time; time.sleep(0.05)

    assert len(success_sessions) == 1
    assert success_sessions[0].username == "alice"
    assert success_sessions[0].dongle_serial == "TEST-USB-999"


def test_login_window_lockout_after_failures(tmp_path: Path):
    db_path = tmp_path / "smoke_auth3.db"
    auth = PasswordAuth(db_path=db_path)
    auth.register("bob", "PasswordKu123#", dongle_serial="CORRECT_USB")

    # Dongle salah
    dongle = FakeDongle(serial="WRONG_USB", present=True)
    face = FakeFaceAuth(should_match=False)

    win = LoginWindow(auth=auth, dongle_checker=dongle, face_auth=face)
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
