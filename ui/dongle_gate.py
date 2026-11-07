"""Gerbang autentikasi dongle fisik (DongleGate).
Aplikasi hanya dapat diaktifkan jika flashdisk/hardisk eksternal yang cocok 1:1 terpasang."""
from __future__ import annotations

from typing import Callable
import customtkinter as ctk

from auth.dongle import DongleError, DongleManager, DongleStatus
from auth.password_auth import PasswordAuth
from ui.theme import (
    ACCENT_COLOR,
    BG_DARK,
    BORDER_COLOR,
    CARD_BG,
    ERROR_COLOR,
    FONT_BOLD,
    FONT_CODE,
    FONT_HEADER,
    FONT_REGULAR,
    FONT_SMALL,
    FONT_SUBHEADER,
    FONT_TITLE,
    SUCCESS_COLOR,
    TEXT_MUTED,
    TEXT_PRIMARY,
    WARNING_COLOR,
)
from ui.widgets import SectionCard, StatusLabel


class DongleGate(ctk.CTk):
    """
    Jendela Gerbang Dongle (Tahap 0 / Pintu Masuk SafeVault).
    Memeriksa kehadiran token kriptografi hardware pada USB flashdisk sebelum
    mengizinkan pengguna melangkah ke verifikasi biometrik dan kata sandi.
    """

    def __init__(
        self,
        manager: DongleManager | None = None,
        auth: PasswordAuth | None = None,
        on_unlocked: Callable[[str], None] | None = None,
        on_exit: Callable[[], None] | None = None,
    ):
        super().__init__()
        self.manager = manager or DongleManager()
        self.auth = auth or PasswordAuth()
        self.on_unlocked = on_unlocked
        self.on_exit = on_exit

        self.is_unlocked = False
        self._poll_job: str | None = None

        # Konfigurasi Tampilan
        self.title("SafeVault - Gerbang Keamanan Dongle")
        self.geometry("540x500")
        self.minsize(480, 420)
        self.configure(fg_color=BG_DARK)
        self.protocol("WM_DELETE_WINDOW", self._handle_exit)

        # Kontainer Utama
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=24, pady=24)

        self._build_header()
        self._render_view()

    def _build_header(self) -> None:
        """Header aplikasi dan logo brankas."""
        header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            header,
            text="🔐 SafeVault",
            font=FONT_TITLE,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="center")

        ctk.CTkLabel(
            header,
            text="Pemeriksaan Akses Kunci Perangkat Keras (Hardware Dongle)",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        ).pack(anchor="center", pady=(2, 0))

    def _render_view(self) -> None:
        """Memilih tampilan berdasarkan status registrasi dongle dan pengguna."""
        if not self.manager.is_registered():
            # Jika dongle belum terdaftar namun database users sudah ada isinya:
            # Berarti data/dongle.json terhapus atau rusak -> KUNCI TOTAL (cegah bypass)!
            if self.auth.has_users():
                self._render_locked_tamper_view()
            else:
                self._render_setup_view()
        else:
            self._render_verify_view()

    # =========================================================================
    # TAMPILAN SETUP (Hanya jika belum ada dongle DAN belum ada user)
    # =========================================================================

    def _render_setup_view(self) -> None:
        """Mode First-Run: Pendaftaran USB flashdisk pertama kali."""
        self.card = SectionCard(self.main_container, title="🛠️ Pendaftaran Dongle Pertama Kali")
        self.card.pack(fill="both", expand=True, pady=(0, 12))

        ctk.CTkLabel(
            self.card,
            text=(
                "Aplikasi SafeVault membutuhkan satu USB Flashdisk sebagai kunci fisik.\n"
                "Pasang flashdisk Anda sekarang, lalu pilih drive di bawah ini."
            ),
            font=FONT_REGULAR,
            text_color=TEXT_MUTED,
            justify="left",
        ).pack(fill="x", padx=16, pady=(8, 12))

        # Peringatan Keamanan Token
        warn_box = ctk.CTkFrame(self.card, fg_color="#3c1e22", corner_radius=6)
        warn_box.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(
            warn_box,
            text=(
                "⚠️ PERINGATAN PENTING:\n"
                "Berkas token '.safevault_dongle.json' di drive ini adalah kunci akses brankas.\n"
                "Jangan dibagikan. Salinan di drive lain akan otomatis ditolak karena ID volume berbeda."
            ),
            font=FONT_SMALL,
            text_color="#f85149",
            justify="left",
        ).pack(padx=12, pady=8, fill="x")

        # Pilihan Mount Drive
        ctk.CTkLabel(
            self.card, text="Pilih Drive USB / Flashdisk:", font=FONT_REGULAR, anchor="w"
        ).pack(fill="x", padx=16, pady=(4, 2))

        mounts = list(self.manager.mounts_fn())
        self.mount_var = ctk.StringVar(value=mounts[0] if mounts else "")
        self.mount_menu = ctk.CTkOptionMenu(
            self.card,
            values=mounts or ["(Tidak ada drive terdeteksi)"],
            variable=self.mount_var,
            font=FONT_REGULAR,
        )
        self.mount_menu.pack(fill="x", padx=16, pady=(0, 8))

        btn_row = ctk.CTkFrame(self.card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="🔄 Segarkan Drive",
            font=FONT_SMALL,
            fg_color="gray30",
            hover_color="gray40",
            width=130,
            command=self._refresh_mounts,
        ).pack(side="left")

        self.setup_status = StatusLabel(self.card)
        self.setup_status.pack(fill="x", padx=16, pady=(4, 10))

        # Tombol Daftarkan Dongle
        self.btn_register = ctk.CTkButton(
            self.card,
            text="🔑 Daftarkan Flashdisk sebagai Dongle",
            font=FONT_BOLD,
            height=38,
            command=self._handle_register,
        )
        self.btn_register.pack(fill="x", padx=16, pady=(0, 12))

    def _refresh_mounts(self) -> None:
        """Memperbarui daftar drive USB yang terdeteksi."""
        mounts = list(self.manager.mounts_fn())
        if mounts:
            self.mount_menu.configure(values=mounts)
            self.mount_var.set(mounts[0])
            self.setup_status.set_status(f"Ditemukan {len(mounts)} drive.", "info")
        else:
            self.mount_menu.configure(values=["(Tidak ada drive terdeteksi)"])
            self.mount_var.set("")
            self.setup_status.set_status("Tidak ada drive terdeteksi. Tancapkan flashdisk lalu coba lagi.", "warning")

    def _handle_register(self) -> None:
        """Mendaftarkan flashdisk terpilih sebagai dongle."""
        selected_mount = self.mount_var.get().strip()
        if not selected_mount or selected_mount.startswith("("):
            self.setup_status.set_status("Pilih drive flashdisk yang valid terlebih dahulu.", "error")
            return

        try:
            self.manager.register(selected_mount, allow_overwrite=False)
            self.setup_status.set_status("✓ Dongle berhasil didaftarkan! Mengalihkan...", "success")
            self.btn_register.configure(state="disabled")
            self.is_unlocked = True
            self.after(800, self._unlock_and_proceed, selected_mount)
        except DongleError as e:
            self.setup_status.set_status(f"Gagal mendaftarkan dongle: {e}", "error")
        except Exception as e:
            self.setup_status.set_status(f"Terjadi kesalahan: {e}", "error")

    # =========================================================================
    # TAMPILAN TERKUNCI PERMANEN (Tamper Alert)
    # =========================================================================

    def _render_locked_tamper_view(self) -> None:
        """Menolak akses jika data dongle hilang sementara database user sudah terisi."""
        self.card = SectionCard(self.main_container, title="🔒 Akses Sistem Terkunci Permanen")
        self.card.pack(fill="both", expand=True, pady=(0, 12))

        alert_box = ctk.CTkFrame(self.card, fg_color="#3c1e22", corner_radius=8)
        alert_box.pack(fill="x", padx=16, pady=20)

        ctk.CTkLabel(
            alert_box,
            text="⚠️ PELANGGARAN INTEGRITAS KEAMANAN",
            font=FONT_BOLD,
            text_color=ERROR_COLOR,
        ).pack(padx=16, pady=(14, 6))

        ctk.CTkLabel(
            alert_box,
            text=(
                "Data registrasi dongle (data/dongle.json) hilang atau dihapus,\n"
                "namun basis data pengguna telah terdaftar di sistem.\n\n"
                "Demi perlindungan dari pembobolan (bypass), pendaftaran baru diblokir.\n"
                "SafeVault tidak dapat dijalankan tanpa data pendaftaran asli."
            ),
            font=FONT_REGULAR,
            text_color=TEXT_PRIMARY,
            justify="center",
        ).pack(padx=16, pady=(0, 14))

        ctk.CTkButton(
            self.card,
            text="Tutup Aplikasi",
            font=FONT_BOLD,
            fg_color="gray30",
            hover_color="gray40",
            command=self._handle_exit,
        ).pack(padx=16, pady=(10, 16))

    # =========================================================================
    # TAMPILAN VERIFIKASI DONGLE NORMAL
    # =========================================================================

    def _render_verify_view(self) -> None:
        """Tampilan verifikasi dongle setiap aplikasi dibuka."""
        self.card = SectionCard(self.main_container, title="🔌 Verifikasi Kunci Dongle Fisik")
        self.card.pack(fill="both", expand=True, pady=(0, 12))

        ctk.CTkLabel(
            self.card,
            text=(
                "SafeVault hanya dapat diaktifkan jika Flashdisk Kunci terpasang pada komputer.\n"
                "Sistem memeriksa keberadaan token dan integritas ID volume secara otomatis."
            ),
            font=FONT_REGULAR,
            text_color=TEXT_MUTED,
            justify="left",
        ).pack(fill="x", padx=16, pady=(10, 12))

        # Status Hasil Pemeriksaan
        self.status_label = StatusLabel(self.card)
        self.status_label.pack(fill="x", padx=16, pady=(0, 14))

        # Tombol Aksi
        btn_box = ctk.CTkFrame(self.card, fg_color="transparent")
        btn_box.pack(fill="x", padx=16, pady=(0, 16))
        btn_box.grid_columnconfigure((0, 1), weight=1)

        self.btn_retry = ctk.CTkButton(
            btn_box,
            text="🔄 Coba Lagi",
            font=FONT_BOLD,
            height=38,
            command=self.check_dongle,
        )
        self.btn_retry.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            btn_box,
            text="Keluar",
            font=FONT_REGULAR,
            fg_color="gray30",
            hover_color="gray40",
            height=38,
            command=self._handle_exit,
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

        # Mulai pemeriksaan perdana dan polling berkala tiap 1 detik
        self.after(200, self.check_dongle)
        self._start_poll()

    def _start_poll(self) -> None:
        """Memulai polling otomatis tiap 1 detik jika belum valid."""
        if self.is_unlocked:
            return
        self._poll_job = self.after(1000, self._poll_step)

    def _poll_step(self) -> None:
        if self.is_unlocked:
            return
        self.check_dongle()
        if not self.is_unlocked:
            self._start_poll()

    def check_dongle(self) -> bool:
        """Mengecek apakah dongle valid saat ini."""
        if self.is_unlocked:
            return True

        try:
            status: DongleStatus = self.manager.verify()
        except DongleError as e:
            status = DongleStatus(False, str(e))

        if status.ok:
            self.is_unlocked = True
            if self._poll_job:
                self.after_cancel(self._poll_job)
                self._poll_job = None
            if hasattr(self, "status_label") and self.status_label.winfo_exists():
                self.status_label.set_status(f"✓ {status.message} ({status.mount})", "success")
            if hasattr(self, "btn_retry") and self.btn_retry.winfo_exists():
                self.btn_retry.configure(state="disabled", text="Membuka Akses...")
            self.after(500, self._unlock_and_proceed, status.mount or "")
            return True
        else:
            if hasattr(self, "status_label") and self.status_label.winfo_exists():
                self.status_label.set_status(f"Akses Ditolak: {status.message}", "error")
            return False

    def _unlock_and_proceed(self, mount: str) -> None:
        """Menutup jendela gerbang dan memanggil callback kelulusan."""
        self.destroy()
        if self.on_unlocked:
            self.on_unlocked(mount)

    def _handle_exit(self) -> None:
        """Menutup aplikasi saat pengguna membatalkan."""
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        self.destroy()
        if self.on_exit:
            self.on_exit()
