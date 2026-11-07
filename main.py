"""Titik masuk utama aplikasi SafeVault (Brankas Digital Kriptografi).
Alur autentikasi bertingkat: Dongle -> Wajah -> Password -> MainWindow.
DongleWatcher memantau keberadaan dongle secara berkala saat brankas terbuka."""
from __future__ import annotations

import sys
from auth.dongle import DongleManager, DongleWatcher
from auth.face_auth import FaceAuth
from auth.password_auth import PasswordAuth
from auth.session import Session
from config import DONGLE_POLL_SECONDS
from ui.dongle_gate import DongleGate
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def run_app() -> None:
    """
    Siklus hidup utama aplikasi SafeVault:
    1. Gerbang Dongle (DongleGate): Hanya bisa terbuka jika flashdisk kunci yang cocok 1:1 terpasang.
    2. Login Bertingkat (LoginWindow): Verifikasi biometrik wajah lalu verifikasi password bcrypt.
    3. Jendela Utama (MainWindow): Akses 5 modul brankas kriptografi.
    4. Pemantau Dongle (DongleWatcher): Jika dongle dicabut selama brankas terbuka,
       aplikasi otomatis mengosongkan memori sesi dan terkunci kembali ke DongleGate.
    """
    auth = PasswordAuth()
    dongle_mgr = DongleManager()
    face_auth = FaceAuth()

    while True:
        # -------------------------------------------------------------
        # TAHAP 1: GERBANG DONGLE (DongleGate)
        # -------------------------------------------------------------
        dongle_unlocked = [False]
        verified_mount = [""]

        def on_dongle_ok(mount: str) -> None:
            dongle_unlocked[0] = True
            verified_mount[0] = mount

        gate = DongleGate(
            manager=dongle_mgr,
            auth=auth,
            on_unlocked=on_dongle_ok,
        )
        gate.mainloop()

        # Jika pengguna menutup gerbang tanpa dongle valid, akhiri aplikasi
        if not dongle_unlocked[0]:
            break

        # -------------------------------------------------------------
        # TAHAP 2 & 3: BIOMETRIK WAJAH & KATA SANDI (LoginWindow)
        # -------------------------------------------------------------
        session_box: list[Session] = []

        def on_login_success(session: Session) -> None:
            session_box.append(session)

        login_win = LoginWindow(
            auth=auth,
            dongle_manager=dongle_mgr,
            face_auth=face_auth,
            on_success=on_login_success,
        )
        login_win.mainloop()

        # Jika jendela login ditutup tanpa berhasil autentikasi, kembali ke loop gerbang
        if not session_box:
            break

        active_session = session_box[0]
        relogin_flag = [False]

        def on_logout() -> None:
            relogin_flag[0] = True

        main_win = MainWindow(
            session=active_session,
            on_logout=on_logout,
            dongle_manager=dongle_mgr,
        )

        # -------------------------------------------------------------
        # TAHAP 4: PEMANTAU DONGLE AKTIF SELAMA BRANKAS TERBUKA
        # -------------------------------------------------------------
        def on_dongle_lost(reason: str) -> None:
            """Callback saat dongle dicabut: kunci brankas seketika."""
            def lock_vault():
                if active_session:
                    active_session.clear()
                relogin_flag[0] = True
                try:
                    if main_win.winfo_exists():
                        main_win.destroy()
                except Exception:
                    pass

            # Pastikan perubahan widget dipanggil di thread utama UI Tkinter
            main_win.after(0, lock_vault)

        watcher = DongleWatcher(
            manager=dongle_mgr,
            on_lost=on_dongle_lost,
            interval=DONGLE_POLL_SECONDS,
        )
        watcher.start()

        main_win.mainloop()
        watcher.stop()

        # Jika relogin aktif (logout manual atau dongle dicabut), loop berulang ke DongleGate
        if not relogin_flag[0]:
            break


if __name__ == "__main__":
    run_app()
