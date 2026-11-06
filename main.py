from __future__ import annotations

import sys
from auth.session import Session
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def run_app() -> None:
    """
    Siklus hidup utama aplikasi SafeVault:
    1. Membuka alur autentikasi 3-faktor di LoginWindow (Dongle -> Wajah -> Password).
    2. Jika lolos, membuka MainWindow dengan sesi pengguna aktif.
    3. Jika pengguna menekan 'Kunci Brankas', sesi dihapus dan kembali ke LoginWindow.
    """
    while True:
        session_box: list[Session] = []

        def on_login_success(session: Session) -> None:
            session_box.append(session)

        login_win = LoginWindow(on_success=on_login_success)
        login_win.mainloop()

        # Jika login ditutup tanpa keberhasilan autentikasi, keluar aplikasi
        if not session_box:
            break

        active_session = session_box[0]
        relogin_flag = [False]

        def on_logout() -> None:
            relogin_flag[0] = True

        main_win = MainWindow(
            session=active_session,
            on_logout=on_logout,
        )
        main_win.mainloop()

        # Jika jendela utama ditutup bukan karena logout, akhiri program
        if not relogin_flag[0]:
            break


if __name__ == "__main__":
    run_app()
