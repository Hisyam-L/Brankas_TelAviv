from __future__ import annotations

from pathlib import Path
import pytest

from auth.password_auth import PasswordAuth, PasswordAuthError


@pytest.fixture
def auth(tmp_path: Path):
    db_file = tmp_path / "test_auth.db"
    return PasswordAuth(db_path=db_file)


def test_auth_first_run_detection(auth):
    assert auth.has_users() is False


def test_auth_register_short_password(auth):
    with pytest.raises(PasswordAuthError, match="minimal 8 karakter"):
        auth.register("admin", "12345")


def test_auth_register_and_verify(auth):
    user_id = auth.register("alice", "password123#Secure", dongle_serial="USB12345")
    assert user_id is not None
    assert auth.has_users() is True

    # Password benar
    assert auth.verify("alice", "password123#Secure") is True

    # Password salah
    assert auth.verify("alice", "wrongpassword") is False

    # Username salah
    assert auth.verify("bob", "password123#Secure") is False


def test_auth_register_duplicate(auth):
    auth.register("charlie", "password123#Secure")
    with pytest.raises(PasswordAuthError, match="sudah digunakan"):
        auth.register("charlie", "passwordLain123")


def test_auth_get_user_and_update_dongle(auth):
    auth.register("dave", "password123#Secure", dongle_serial="OLD_SERIAL")
    user = auth.get_user("dave")
    assert user is not None
    assert user["dongle_serial"] == "OLD_SERIAL"

    auth.set_dongle_serial("dave", "NEW_SERIAL")
    user2 = auth.get_user("dave")
    assert user2["dongle_serial"] == "NEW_SERIAL"
