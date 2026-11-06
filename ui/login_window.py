from __future__ import annotations

import queue
import threading
import time
from typing import Callable
import cv2
import numpy as np
from PIL import Image
import customtkinter as ctk

from auth.dongle import DongleChecker, get_dongle_checker
from auth.face_auth import FaceAuth, FaceAuthError
from auth.password_auth import PasswordAuth, PasswordAuthError
from auth.session import Session
from config import LOCKOUT_SECONDS, MAX_LOGIN_ATTEMPTS
from ui.theme import (
    ACCENT_COLOR,
    ACCENT_HOVER,
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
from ui.widgets import PasswordEntry, SectionCard, StatusLabel


class LoginWindow(ctk.CTk):
    """
    Jendela Autentikasi SafeVault Tiga Tahap:
    1. Pemeriksaan Dongle Fisik (USB Hardware Key)
    2. Verifikasi Biometrik Wajah (OpenCV Haar + LBPH)
    3. Verifikasi Kata Sandi Brankas (bcrypt Hash)

    Menyediakan mode First-Run Setup jika belum ada pengguna terdaftar,
    serta penguncian otomatis (lockout) 30 detik jika gagal 3 kali berturut-turut.
    """

    def __init__(
        self,
        auth: PasswordAuth | None = None,
        dongle_checker: DongleChecker | None = None,
        face_auth: FaceAuth | None = None,
        on_success: Callable[[Session], None] | None = None,
    ):
        super().__init__()
        self.auth = auth or PasswordAuth()
        self.dongle_checker = dongle_checker or get_dongle_checker()
        self.face_auth = face_auth or FaceAuth()
        self.on_success = on_success

        # Variabel Status Autentikasi
        self.current_step = 1  # 1: Dongle, 2: Wajah, 3: Sandi
        self.verified_dongle_serial: str | None = None
        self.active_username: str = ""
        self.failed_attempts = 0
        self.is_locked = False
        self.lockout_seconds_left = 0

        # State Kamera
        self.cap: cv2.VideoCapture | None = None
        self.is_camera_running = False
        self.current_frame: np.ndarray | None = None
        self.camera_thread: threading.Thread | None = None

        # Antrean eksekusi thread-safe untuk pembaruan UI
        self.task_queue: queue.Queue = queue.Queue()
        self._poll_ui_queue()

        # Konfigurasi Jendela
        self.title("SafeVault - Autentikasi Keamanan Berlapis")
        self.geometry("560x720")
        self.minsize(500, 650)
        self.configure(fg_color=BG_DARK)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Kontainer Utama
        self.main_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_header()

        # Tampilkan setup jika belum ada user, sebaliknya tampilkan login
        if not self.auth.has_users():
            self._show_setup_view()
        else:
            self._show_login_view()

    def post_ui(self, fn: Callable, *args, **kwargs) -> None:
        """Menjadwalkan eksekusi fungsi di thread utama Tkinter secara aman."""
        self.task_queue.put((fn, args, kwargs))

    def _poll_ui_queue(self) -> None:
        """Mengosongkan dan mengeksekusi antrean tugas UI di thread utama."""
        while not self.task_queue.empty():
            try:
                fn, args, kwargs = self.task_queue.get_nowait()
                fn(*args, **kwargs)
            except Exception:
                pass
        try:
            if self.winfo_exists():
                self.after(20, self._poll_ui_queue)
        except Exception:
            pass

    def _build_header(self) -> None:
        """Membangun header aplikasi dan peringatan dev mode bila ada."""
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            self.header_frame,
            text="🔐 SafeVault",
            font=FONT_TITLE,
            text_color=TEXT_PRIMARY,
        ).pack(anchor="center")

        ctk.CTkLabel(
            self.header_frame,
            text="Autentikasi Brankas Berlapis Tiga (3-Factor Authentication)",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        ).pack(anchor="center", pady=(2, 6))

        # Peringatan Mode Simulasi jika aktif
        if self.dongle_checker.is_simulated:
            dev_banner = ctk.CTkFrame(
                self.header_frame, fg_color="#422500", border_width=1, border_color="#d29922"
            )
            dev_banner.pack(fill="x", pady=(4, 6))
            ctk.CTkLabel(
                dev_banner,
                text="⚠️ PERINGATAN: Mode Pengembang Aktif (Simulated Dongle)",
                font=FONT_SMALL,
                text_color="#f0b72f",
            ).pack(padx=10, pady=4)

        # Status Label Umum
        self.global_status = StatusLabel(self.header_frame)
        self.global_status.pack(fill="x", pady=(4, 0))

    # =========================================================================
    # TAMPILAN LOGIN BERTINGKAT (Dongle -> Wajah -> Sandi)
    # =========================================================================

    def _show_login_view(self) -> None:
        """Menampilkan alur login 3 tahap."""
        if hasattr(self, "content_frame") and self.content_frame:
            self.content_frame.destroy()

        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)

        # Indikator Langkah 1 - 2 - 3
        self.steps_bar = ctk.CTkFrame(self.content_frame, fg_color=CARD_BG, corner_radius=8)
        self.steps_bar.pack(fill="x", pady=(0, 16))
        self.steps_bar.grid_columnconfigure((0, 1, 2), weight=1)

        self.step_indicators = []
        step_labels = ["1. Dongle Fisik", "2. Verifikasi Wajah", "3. Kata Sandi"]
        for idx, lbl in enumerate(step_labels):
            box = ctk.CTkLabel(
                self.steps_bar,
                text=lbl,
                font=FONT_SMALL,
                fg_color="transparent",
                text_color=TEXT_MUTED,
                corner_radius=6,
                height=32,
            )
            box.grid(row=0, column=idx, padx=4, pady=4, sticky="ew")
            self.step_indicators.append(box)

        # Dropdown / Pilihan Pengguna
        user_select_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        user_select_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            user_select_frame, text="Pilih Pengguna:", font=FONT_REGULAR, text_color=TEXT_PRIMARY
        ).pack(side="left", padx=(0, 8))

        usernames = self.auth.list_usernames()
        self.user_var = ctk.StringVar(value=usernames[0] if usernames else "")
        self.user_menu = ctk.CTkOptionMenu(
            user_select_frame,
            values=usernames or ["(Belum ada)"],
            variable=self.user_var,
            font=FONT_REGULAR,
            command=self._on_user_changed,
        )
        self.user_menu.pack(side="left", fill="x", expand=True)

        self.active_username = self.user_var.get()

        # Kartu Interaktif Langkah
        self.step_card = SectionCard(self.content_frame, title="Tahap Autentikasi")
        self.step_card.pack(fill="both", expand=True, pady=(0, 12))

        # Bottom Bar: Tombol Setup & Tombol Keluar
        bottom_bar = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        bottom_bar.pack(fill="x", pady=(4, 0))

        ctk.CTkButton(
            bottom_bar,
            text="+ Tambah Akun Baru",
            font=FONT_SMALL,
            fg_color="transparent",
            hover_color="gray25",
            text_color=TEXT_MUTED,
            command=self._show_setup_view,
        ).pack(side="left")

        ctk.CTkButton(
            bottom_bar,
            text="Keluar",
            font=FONT_SMALL,
            fg_color="gray30",
            hover_color="gray40",
            width=80,
            command=self._on_close,
        ).pack(side="right")

        self._render_current_step()

    def _update_step_indicators(self) -> None:
        """Memperbarui visual status bar indikator tahapan."""
        for idx, lbl in enumerate(self.step_indicators, start=1):
            if idx < self.current_step:
                lbl.configure(text_color=SUCCESS_COLOR, text=f"✓ {lbl.cget('text').lstrip('✓ ')}")
            elif idx == self.current_step:
                lbl.configure(text_color=TEXT_PRIMARY, fg_color=ACCENT_COLOR)
            else:
                lbl.configure(text_color=TEXT_MUTED, fg_color="transparent")

    def _render_current_step(self) -> None:
        """Membuat widget UI yang sesuai dengan tahap aktif saat ini."""
        self._update_step_indicators()

        # Bersihkan isi kartu tahapan
        for child in self.step_card.winfo_children():
            if child != getattr(self.step_card, "header_label", None):
                child.destroy()

        if self.is_locked:
            self._render_lockout_view()
            return

        if self.current_step == 1:
            self._render_step1_dongle()
        elif self.current_step == 2:
            self._render_step2_face()
        elif self.current_step == 3:
            self._render_step3_password()

    # --------------------------------------------------- Tahap 1: Dongle Fisik
    def _render_step1_dongle(self) -> None:
        self.step_card.header_label.configure(text="🔌 Tahap 1: Pemeriksaan Dongle Fisik")

        info_lbl = ctk.CTkLabel(
            self.step_card,
            text=(
                "SafeVault hanya dapat diaktifkan jika dongle perangkat keras (USB Flashdisk)\n"
                "kunci brankas terpasang pada komputer."
            ),
            font=FONT_REGULAR,
            text_color=TEXT_MUTED,
            justify="left",
        )
        info_lbl.pack(fill="x", padx=16, pady=(6, 12))

        self.dongle_status = StatusLabel(self.step_card)
        self.dongle_status.pack(fill="x", padx=16, pady=(0, 12))

        self.btn_check_dongle = ctk.CTkButton(
            self.step_card,
            text="🔌 Periksa Sambungan Dongle",
            font=FONT_BOLD,
            height=38,
            command=self._handle_verify_dongle,
        )
        self.btn_check_dongle.pack(fill="x", padx=16, pady=(0, 16))

        # Lakukan auto-check seketika saat masuk tahap 1
        self.after(200, self._handle_verify_dongle)

    def _handle_verify_dongle(self) -> None:
        if self.is_locked:
            return

        self.btn_check_dongle.configure(state="disabled", text="Memeriksa perangkat USB...")
        self.dongle_status.set_status("Memindai port USB...", "info")

        def task():
            present = self.dongle_checker.is_present()
            serial = self.dongle_checker.get_serial()

            def finish():
                self.btn_check_dongle.configure(state="normal", text="🔌 Periksa Sambungan Dongle")
                user_info = self.auth.get_user(self.active_username)
                registered_serial = user_info["dongle_serial"] if user_info else None

                if not present or not serial:
                    self.dongle_status.set_status(
                        "Gagal: Dongle fisik tidak ditemukan. Pastikan USB kunci terpasang.", "error"
                    )
                    self._record_failure("Dongle fisik tidak terdeteksi")
                    return

                # Jika pengguna telah mendaftarkan serial tertentu, verifikasi kesesuaiannya
                if registered_serial and serial != registered_serial:
                    self.dongle_status.set_status(
                        f"Gagal: Dongle yang terpasang ({serial}) tidak cocok dengan akun ini.", "error"
                    )
                    self._record_failure("Serial dongle tidak cocok")
                    return

                self.verified_dongle_serial = serial
                self.dongle_status.set_status(
                    f"✓ Dongle Terverifikasi! (Serial: {serial})", "success"
                )

                # Berhasil lolos Tahap 1 -> Lanjut ke Tahap 2
                self.after(600, self._advance_to_step, 2)

            self.post_ui(finish)

        threading.Thread(target=task, daemon=True).start()

    # --------------------------------------------------- Tahap 2: Verifikasi Wajah
    def _render_step2_face(self) -> None:
        self.step_card.header_label.configure(text="👤 Tahap 2: Verifikasi Biometrik Wajah")

        info_lbl = ctk.CTkLabel(
            self.step_card,
            text=f"Arahkan wajah Anda ({self.active_username}) ke kamera webcam untuk pengenalan biometrik.",
            font=FONT_REGULAR,
            text_color=TEXT_MUTED,
            justify="left",
        )
        info_lbl.pack(fill="x", padx=16, pady=(4, 8))

        # Wadah Tampilan Webcam
        self.cam_frame = ctk.CTkFrame(self.step_card, fg_color="gray15", height=240, corner_radius=8)
        self.cam_frame.pack(fill="x", padx=16, pady=(0, 10))
        self.cam_frame.pack_propagate(False)

        self.cam_label = ctk.CTkLabel(
            self.cam_frame,
            text="Kamera belum aktif...\nKlik 'Mulai Kamera' untuk pratinjau",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        self.cam_label.pack(expand=True)

        self.face_status = StatusLabel(self.step_card)
        self.face_status.pack(fill="x", padx=16, pady=(0, 10))

        # Tombol Kontrol Kamera & Verifikasi
        btn_box = ctk.CTkFrame(self.step_card, fg_color="transparent")
        btn_box.pack(fill="x", padx=16, pady=(0, 16))
        btn_box.grid_columnconfigure((0, 1), weight=1)

        self.btn_toggle_cam = ctk.CTkButton(
            btn_box,
            text="📷 Mulai Kamera",
            font=FONT_REGULAR,
            fg_color="gray30",
            hover_color="gray40",
            command=self._toggle_camera,
        )
        self.btn_toggle_cam.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.btn_verify_face = ctk.CTkButton(
            btn_box,
            text="👤 Cocokkan Wajah",
            font=FONT_BOLD,
            command=self._handle_verify_face,
        )
        self.btn_verify_face.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        # Otomatis mulai kamera
        self.after(100, self._start_camera)

    def _start_camera(self) -> None:
        if self.is_camera_running:
            return
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.face_status.set_status("Webcam tidak terdeteksi pada indeks 0.", "warning")
                return
            self.is_camera_running = True
            self.btn_toggle_cam.configure(text="⏹️ Hentikan Kamera")
            self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
            self.camera_thread.start()
        except Exception as e:
            self.face_status.set_status(f"Gagal membuka kamera: {e}", "error")

    def _stop_camera(self) -> None:
        self.is_camera_running = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        if hasattr(self, "btn_toggle_cam") and self.btn_toggle_cam.winfo_exists():
            self.btn_toggle_cam.configure(text="📷 Mulai Kamera")

    def _toggle_camera(self) -> None:
        if self.is_camera_running:
            self._stop_camera()
            self.cam_label.configure(image="", text="Kamera dihentikan.")
        else:
            self._start_camera()

    def _camera_loop(self) -> None:
        """Loop pemindaian frame kamera di background thread."""
        while self.is_camera_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            self.current_frame = frame.copy()

            # Beri kotak deteksi wajah pada pratinjau
            preview = frame.copy()
            faces = self.face_auth.detect_faces(frame)
            for (x, y, w, h) in faces:
                cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)

            rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
            rgb = cv2.resize(rgb, (320, 220))
            img = Image.fromarray(rgb)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(320, 220))

            def update_ui(image_obj=ctk_img):
                if self.is_camera_running and hasattr(self, "cam_label") and self.cam_label.winfo_exists():
                    self.cam_label.configure(image=image_obj, text="")

            self.post_ui(update_ui)
            time.sleep(0.03)

    def _handle_verify_face(self) -> None:
        if self.is_locked:
            return

        # Cek apakah model wajah pengguna terdaftar
        if not self.face_auth.is_enrolled(self.active_username):
            self.face_status.set_status(
                f"Pengguna '{self.active_username}' belum memiliki model wajah terdaftar.", "error"
            )
            self._record_failure("Model biometrik belum terdaftar")
            return

        frame = self.current_frame
        if frame is None:
            self.face_status.set_status("Frame kamera belum tersedia. Pastikan kamera menyala.", "warning")
            return

        self.btn_verify_face.configure(state="disabled", text="Mencocokkan...")
        self.face_status.set_status("Menganalisis biometrik wajah...", "info")

        def task():
            match, distance, msg = self.face_auth.verify(frame, expected_username=self.active_username)

            def finish():
                self.btn_verify_face.configure(state="normal", text="👤 Cocokkan Wajah")
                if match:
                    self._stop_camera()
                    self.face_status.set_status(f"✓ {msg}", "success")
                    self.after(600, self._advance_to_step, 3)
                else:
                    self.face_status.set_status(f"Gagal: {msg}", "error")
                    self._record_failure(f"Wajah tidak cocok ({distance:.1f})")

            self.post_ui(finish)

        threading.Thread(target=task, daemon=True).start()

    # --------------------------------------------------- Tahap 3: Kata Sandi
    def _render_step3_password(self) -> None:
        self.step_card.header_label.configure(text="🔑 Tahap 3: Kata Sandi Brankas")

        info_lbl = ctk.CTkLabel(
            self.step_card,
            text=f"Masukkan kata sandi akun '{self.active_username}' untuk membuka brankas.",
            font=FONT_REGULAR,
            text_color=TEXT_MUTED,
            justify="left",
        )
        info_lbl.pack(fill="x", padx=16, pady=(4, 10))

        self.password_input = PasswordEntry(
            self.step_card, placeholder_text="Masukkan kata sandi..."
        )
        self.password_input.pack(fill="x", padx=16, pady=(0, 10))
        self.password_input.entry.bind("<Return>", lambda e: self._handle_verify_password())

        self.pw_status = StatusLabel(self.step_card)
        self.pw_status.pack(fill="x", padx=16, pady=(0, 12))

        self.btn_login = ctk.CTkButton(
            self.step_card,
            text="🔓 Buka Brankas SafeVault",
            font=FONT_BOLD,
            height=40,
            command=self._handle_verify_password,
        )
        self.btn_login.pack(fill="x", padx=16, pady=(0, 16))

        self.password_input.entry.focus()

    def _handle_verify_password(self) -> None:
        if self.is_locked:
            return

        password = self.password_input.get()
        if not password:
            self.pw_status.set_status("Kata sandi tidak boleh kosong", "error")
            return

        self.btn_login.configure(state="disabled", text="Memverifikasi hash...")
        self.pw_status.set_status("Memeriksa password...", "info")

        def task():
            is_valid = self.auth.verify(self.active_username, password)

            def finish():
                self.btn_login.configure(state="normal", text="🔓 Buka Brankas SafeVault")
                if is_valid:
                    self.pw_status.set_status("✓ Autentikasi Berhasil! Membuka brankas...", "success")
                    session = Session(
                        username=self.active_username,
                        dongle_serial=self.verified_dongle_serial,
                    )
                    self._stop_camera()
                    self.after(500, self._complete_login, session)
                else:
                    self.pw_status.set_status("Kata sandi salah. Akses ditolak.", "error")
                    self._record_failure("Kata sandi salah")

            self.post_ui(finish)

        threading.Thread(target=task, daemon=True).start()

    def _advance_to_step(self, step: int) -> None:
        self.current_step = step
        self._render_current_step()

    def _complete_login(self, session: Session) -> None:
        """Menutup jendela login dan menjalankan callback on_success dengan sesi aktif."""
        self.destroy()
        if self.on_success:
            self.on_success(session)

    # =========================================================================
    # MEKANISME PENGUNCIAN (LOCKOUT 30 DETIK)
    # =========================================================================

    def _record_failure(self, reason: str) -> None:
        """Mencatat kegagalan autentikasi dan memicu lockout jika mencapai batas maksimal."""
        self.failed_attempts += 1
        sisa = MAX_LOGIN_ATTEMPTS - self.failed_attempts
        if self.failed_attempts >= MAX_LOGIN_ATTEMPTS:
            self._start_lockout()
        else:
            self.global_status.set_status(
                f"Percobaan gagal ({self.failed_attempts}/{MAX_LOGIN_ATTEMPTS}). Sisa percobaan: {sisa}.",
                "warning",
            )

    def _start_lockout(self) -> None:
        self.is_locked = True
        self.lockout_seconds_left = LOCKOUT_SECONDS
        self._stop_camera()
        self._render_current_step()
        self._tick_lockout()

    def _render_lockout_view(self) -> None:
        self.step_card.header_label.configure(text="🔒 Akses Terkunci Sementara")

        lockout_box = ctk.CTkFrame(self.step_card, fg_color="#3c1e22", corner_radius=8)
        lockout_box.pack(fill="x", padx=16, pady=16)

        ctk.CTkLabel(
            lockout_box,
            text="⚠️ SISTEM TERKUNCI KARENA KEGAGALAN BERULANG",
            font=FONT_BOLD,
            text_color=ERROR_COLOR,
        ).pack(padx=16, pady=(12, 6))

        self.lockout_timer_label = ctk.CTkLabel(
            lockout_box,
            text=f"Silakan tunggu {self.lockout_seconds_left} detik...",
            font=FONT_HEADER,
            text_color=TEXT_PRIMARY,
        )
        self.lockout_timer_label.pack(padx=16, pady=(0, 12))

    def _tick_lockout(self) -> None:
        if not self.is_locked:
            return

        if self.lockout_seconds_left > 0:
            if hasattr(self, "lockout_timer_label") and self.lockout_timer_label.winfo_exists():
                self.lockout_timer_label.configure(
                    text=f"Silakan tunggu {self.lockout_seconds_left} detik..."
                )
            self.lockout_seconds_left -= 1
            self.after(1000, self._tick_lockout)
        else:
            # Selesai penguncian: reset percobaan dan kembalikan ke tahap 1
            self.is_locked = False
            self.failed_attempts = 0
            self.current_step = 1
            self.global_status.set_status("Masa penguncian selesai. Silakan coba kembali.", "info")
            self._render_current_step()

    def _on_user_changed(self, choice: str) -> None:
        self.active_username = choice
        self.current_step = 1
        self._stop_camera()
        self._render_current_step()

    # =========================================================================
    # TAMPILAN FIRST-RUN SETUP & PENDAFTARAN PENGGUNA BARU
    # =========================================================================

    def _show_setup_view(self) -> None:
        """Menampilkan form pendaftaran pengguna awal / baru."""
        self._stop_camera()
        if hasattr(self, "content_frame") and self.content_frame:
            self.content_frame.destroy()

        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)

        setup_card = SectionCard(self.content_frame, title="🛠️ Pendaftaran Akun & Kunci Keamanan")
        setup_card.pack(fill="both", expand=True, pady=(0, 12))

        # 1. Username
        ctk.CTkLabel(setup_card, text="Nama Pengguna (Username):", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(8, 2)
        )
        self.setup_user_entry = ctk.CTkEntry(
            setup_card, placeholder_text="Masukkan nama pengguna...", font=FONT_REGULAR
        )
        self.setup_user_entry.pack(fill="x", padx=16, pady=(0, 8))

        # 2. Password & Konfirmasi
        ctk.CTkLabel(
            setup_card, text="Kata Sandi (Minimal 8 Karakter):", font=FONT_REGULAR, anchor="w"
        ).pack(fill="x", padx=16, pady=(2, 2))
        self.setup_pw_entry = PasswordEntry(setup_card, placeholder_text="Minimal 8 karakter...")
        self.setup_pw_entry.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(setup_card, text="Konfirmasi Kata Sandi:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(2, 2)
        )
        self.setup_pw_confirm = PasswordEntry(setup_card, placeholder_text="Ulangi kata sandi...")
        self.setup_pw_confirm.pack(fill="x", padx=16, pady=(0, 10))

        # 3. Asosiasi Dongle USB
        dongle_sec = ctk.CTkFrame(setup_card, fg_color="gray20", corner_radius=6)
        dongle_sec.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkLabel(
            dongle_sec, text="🔌 Pasangkan Dongle USB:", font=FONT_SUBHEADER, text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.setup_dongle_lbl = ctk.CTkLabel(
            dongle_sec,
            text="Klik 'Deteksi Dongle' saat flashdisk terpasang",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        self.setup_dongle_lbl.pack(anchor="w", padx=10, pady=(0, 6))

        self.setup_dongle_serial: str | None = None
        ctk.CTkButton(
            dongle_sec,
            text="Deteksi Dongle Saat Ini",
            font=FONT_SMALL,
            fg_color="gray30",
            hover_color="gray40",
            command=self._setup_detect_dongle,
        ).pack(anchor="w", padx=10, pady=(0, 8))

        # 4. Sampel Wajah Biometrik
        face_sec = ctk.CTkFrame(setup_card, fg_color="gray20", corner_radius=6)
        face_sec.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            face_sec, text="👤 Rekam Biometrik Wajah:", font=FONT_SUBHEADER, text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.setup_face_lbl = ctk.CTkLabel(
            face_sec,
            text="Belum ada sampel wajah. Rekam 20 foto sampel wajah lewat webcam.",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            wraplength=440,
            justify="left",
        )
        self.setup_face_lbl.pack(anchor="w", padx=10, pady=(0, 6))

        self.has_face_enrolled = False
        self.btn_enroll_face = ctk.CTkButton(
            face_sec,
            text="📷 Rekam 20 Sampel Wajah",
            font=FONT_SMALL,
            command=self._setup_enroll_face,
        )
        self.btn_enroll_face.pack(anchor="w", padx=10, pady=(0, 8))

        self.setup_status = StatusLabel(setup_card)
        self.setup_status.pack(fill="x", padx=16, pady=(0, 10))

        # Tombol Simpan & Batal
        btn_row = ctk.CTkFrame(setup_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 16))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        if self.auth.has_users():
            ctk.CTkButton(
                btn_row,
                text="← Kembali ke Login",
                font=FONT_REGULAR,
                fg_color="gray30",
                hover_color="gray40",
                command=self._show_login_view,
            ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            btn_row,
            text="💾 Simpan & Daftarkan Akun",
            font=FONT_BOLD,
            command=self._handle_save_setup,
        ).grid(row=0, column=1 if self.auth.has_users() else 0, columnspan=1 if self.auth.has_users() else 2, padx=(6, 0) if self.auth.has_users() else (0, 0), sticky="ew")

    def _setup_detect_dongle(self) -> None:
        serial = self.dongle_checker.get_serial()
        if serial:
            self.setup_dongle_serial = serial
            self.setup_dongle_lbl.configure(
                text=f"✓ Dongle terdeteksi: {serial}", text_color=SUCCESS_COLOR
            )
        else:
            self.setup_dongle_lbl.configure(
                text="Perangkat USB tidak ditemukan. Tancapkan flashdisk lalu klik lagi.",
                text_color=ERROR_COLOR,
            )

    def _setup_enroll_face(self) -> None:
        username = self.setup_user_entry.get().strip()
        if not username:
            self.setup_status.set_status("Isi nama pengguna terlebih dahulu sebelum merekam wajah.", "error")
            return

        self.btn_enroll_face.configure(state="disabled", text="Merekam 20 sampel wajah...")
        self.setup_status.set_status("Membuka kamera, tatap layar langsung...", "info")

        def task():
            try:
                success, msg = self.face_auth.enroll(username, jumlah_sampel=20)
                def finish():
                    self.btn_enroll_face.configure(state="normal", text="📷 Rekam Ulang Sampel Wajah")
                    if success:
                        self.has_face_enrolled = True
                        self.setup_face_lbl.configure(
                            text=f"✓ Model biometrik wajah '{username}' berhasil dilatih (20 sampel).",
                            text_color=SUCCESS_COLOR,
                        )
                        self.setup_status.set_status("Perekaman biometrik berhasil!", "success")
                    else:
                        self.setup_status.set_status(f"Gagal merekam wajah: {msg}", "error")
                self.post_ui(finish)
            except (FaceAuthError, Exception) as e:
                def finish_err():
                    self.btn_enroll_face.configure(state="normal", text="📷 Rekam 20 Sampel Wajah")
                    self.setup_status.set_status(f"Gagal merekam wajah: {e}", "error")
                self.post_ui(finish_err)

        threading.Thread(target=task, daemon=True).start()

    def _handle_save_setup(self) -> None:
        username = self.setup_user_entry.get().strip()
        pw = self.setup_pw_entry.get()
        confirm = self.setup_pw_confirm.get()

        if not username:
            self.setup_status.set_status("Nama pengguna tidak boleh kosong", "error")
            return
        if pw != confirm:
            self.setup_status.set_status("Konfirmasi kata sandi tidak cocok", "error")
            return

        try:
            self.auth.register(username, pw, dongle_serial=self.setup_dongle_serial)
            self.setup_status.set_status("Akun berhasil didaftarkan! Mengalihkan ke login...", "success")
            self.after(800, self._show_login_view)
        except PasswordAuthError as e:
            self.setup_status.set_status(str(e), "error")
        except Exception as e:
            self.setup_status.set_status(f"Gagal mendaftar: {e}", "error")

    def _on_close(self) -> None:
        """Penanganan saat jendela ditutup."""
        self._stop_camera()
        self.destroy()
