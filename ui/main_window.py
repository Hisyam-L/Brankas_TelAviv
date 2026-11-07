from __future__ import annotations

from typing import Callable
import customtkinter as ctk

from auth.dongle import DongleManager
from auth.session import Session
from ui.asset_page import AssetPage
from ui.file_page import FilePage
from ui.image_page import ImagePage
from ui.password_page import PasswordPage
from ui.text_page import TextPage
from ui.widgets import StatusLabel
from ui.theme import (
    ACCENT_COLOR,
    BG_DARK,
    BG_SIDEBAR,
    BORDER_COLOR,
    FONT_BOLD,
    FONT_HEADER,
    FONT_REGULAR,
    FONT_SMALL,
    FONT_SUBHEADER,
    FONT_TITLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
)


class MainWindow(ctk.CTk):
    """
    Jendela Utama Aplikasi SafeVault (Brankas Digital Kriptografi).
    Menyediakan sidebar navigasi 5 modul kriptografi dan area konten dinamis.
    """

    def __init__(
        self,
        username: str = "Administrator",
        session: Session | None = None,
        on_logout: Callable[[], None] | None = None,
        dongle_manager: DongleManager | None = None,
    ):
        super().__init__()
        self.session: Session | None = session or Session(username=username)
        self.username = self.session.username if self.session else username
        self.on_logout = on_logout
        self.dongle_manager = dongle_manager or DongleManager()

        # Konfigurasi Jendela
        self.title("SafeVault - Brankas Digital Kriptografi")
        self.geometry("980x640")
        self.minsize(800, 520)

        # Layout Utama: 2 kolom (Sidebar kiri, Konten kanan)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()

        # Pilih halaman default: Catatan Rahasia
        self.select_page("catatan")

    def _build_sidebar(self) -> None:
        """Membangun sidebar navigasi di sebelah kiri."""
        self.sidebar = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0,
            fg_color=BG_SIDEBAR,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(7, weight=1)  # Spacer fleksibel sebelum logout

        # Brand / Logo Header
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=16, pady=(20, 16), sticky="w")

        ctk.CTkLabel(
            brand_frame, text="🔐 SafeVault", font=FONT_TITLE, text_color=TEXT_PRIMARY
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand_frame,
            text="Brankas Kriptografi",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        ).pack(anchor="w")

        # Badge Pengguna Aktif
        user_badge = ctk.CTkFrame(self.sidebar, fg_color="gray20", corner_radius=6)
        user_badge.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")

        ctk.CTkLabel(
            user_badge,
            text=f"👤 {self.username}",
            font=FONT_SMALL,
            text_color=TEXT_PRIMARY,
        ).pack(padx=10, pady=6, anchor="w")

        # Tombol Menu Navigasi
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        menus = [
            ("catatan", "📝 Catatan Rahasia"),
            ("berkas", "📁 Berkas Enkripsi"),
            ("sandi", "🔑 Kata Sandi"),
            ("foto", "🖼️ Foto Rahasia"),
            ("dokumen", "📜 Daftar Dokumen"),
        ]

        for idx, (page_key, label) in enumerate(menus, start=2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                font=FONT_REGULAR,
                fg_color="transparent",
                text_color=TEXT_PRIMARY,
                hover_color="gray25",
                height=38,
                corner_radius=6,
                command=lambda pk=page_key: self.select_page(pk),
            )
            btn.grid(row=idx, column=0, padx=12, pady=4, sticky="ew")
            self.nav_buttons[page_key] = btn

        # Bagian Bawah Sidebar (Mode Gelap & Kunci Brankas)
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.grid(row=8, column=0, padx=16, pady=16, sticky="ew")

        # Saklar Tema
        self.theme_switch = ctk.CTkSwitch(
            bottom_frame,
            text="Mode Gelap",
            font=FONT_SMALL,
            command=self._toggle_theme,
        )
        self.theme_switch.select()
        self.theme_switch.pack(fill="x", pady=(0, 8))

        # Tombol Ganti Dongle (Hanya setelah login penuh)
        self.change_dongle_btn = ctk.CTkButton(
            bottom_frame,
            text="🔑 Ganti Dongle",
            fg_color="gray25",
            hover_color="gray35",
            font=FONT_SMALL,
            command=self._open_change_dongle_dialog,
        )
        self.change_dongle_btn.pack(fill="x", pady=(0, 8))

        # Tombol Kunci Brankas (Logout)
        self.logout_btn = ctk.CTkButton(
            bottom_frame,
            text="🔒 Kunci Brankas",
            fg_color="#8b1c1c",
            hover_color="#ab2323",
            font=FONT_REGULAR,
            command=self._handle_logout,
        )
        self.logout_btn.pack(fill="x")

    def _build_content_area(self) -> None:
        """Area konten di sebelah kanan yang menampilkan halaman aktif."""
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # Inisialisasi kelima halaman
        self.pages: dict[str, ctk.CTkFrame] = {
            "catatan": TextPage(self.content_container),
            "berkas": FilePage(self.content_container),
            "sandi": PasswordPage(self.content_container),
            "foto": ImagePage(self.content_container),
            "dokumen": AssetPage(self.content_container),
        }

    def select_page(self, page_key: str) -> None:
        """Mengganti halaman aktif dan memperbarui sorotan navigasi sidebar."""
        for key, page in self.pages.items():
            if key == page_key:
                page.grid(row=0, column=0, sticky="nsew")
                if hasattr(page, "refresh_list"):
                    page.refresh_list()
                elif hasattr(page, "refresh_documents_list"):
                    page.refresh_documents_list()
            else:
                page.grid_forget()

        for key, btn in self.nav_buttons.items():
            if key == page_key:
                btn.configure(fg_color=ACCENT_COLOR, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_PRIMARY)

    def _toggle_theme(self) -> None:
        mode = "dark" if self.theme_switch.get() == 1 else "light"
        ctk.set_appearance_mode(mode)

    def _handle_logout(self) -> None:
        if self.session:
            self.session.clear()
            self.session = None
        if self.on_logout:
            self.destroy()
            self.on_logout()
        else:
            self.destroy()

    def _open_change_dongle_dialog(self) -> None:
        """Membuka dialog untuk mengganti/mendaftarkan ulang dongle (hanya saat login penuh)."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("Pengaturan Kunci Dongle")
        dlg.geometry("460x340")
        dlg.minsize(420, 300)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="🔑 Ganti Kunci Hardware Dongle", font=FONT_HEADER).pack(padx=16, pady=(16, 6))
        ctk.CTkLabel(
            dlg,
            text=(
                "Pilih drive flashdisk baru yang akan dijadikan kunci brankas.\n"
                "Kunci dongle lama tidak akan berlaku lagi setelah proses ini berhasil."
            ),
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            justify="center",
        ).pack(padx=16, pady=(0, 12))

        mounts = list(self.dongle_manager.mounts_fn())
        mount_var = ctk.StringVar(value=mounts[0] if mounts else "")
        menu = ctk.CTkOptionMenu(
            dlg, values=mounts or ["(Tidak ada drive terdeteksi)"], variable=mount_var, font=FONT_REGULAR
        )
        menu.pack(fill="x", padx=24, pady=(0, 10))

        status_lbl = StatusLabel(dlg)
        status_lbl.pack(fill="x", padx=24, pady=(0, 12))

        def save():
            m = mount_var.get().strip()
            if not m or m.startswith("("):
                status_lbl.set_status("Pilih drive flashdisk yang valid.", "error")
                return
            try:
                self.dongle_manager.register(m, allow_overwrite=True)
                status_lbl.set_status("✓ Dongle baru berhasil didaftarkan!", "success")
                dlg.after(1000, dlg.destroy)
            except Exception as e:
                status_lbl.set_status(f"Gagal mengganti dongle: {e}", "error")

        ctk.CTkButton(
            dlg, text="💾 Simpan & Tulis Token Baru", font=FONT_BOLD, height=36, command=save
        ).pack(fill="x", padx=24, pady=(0, 8))

        ctk.CTkButton(
            dlg, text="Batal", fg_color="gray30", hover_color="gray40", height=32, command=dlg.destroy
        ).pack(fill="x", padx=24, pady=(0, 12))
