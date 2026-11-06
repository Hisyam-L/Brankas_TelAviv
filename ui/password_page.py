from __future__ import annotations

import json
import secrets
import string
import tkinter.messagebox as mb
import customtkinter as ctk

from database.db import SecureMessageStore, buat_pipeline
from ui.theme import (
    FONT_CODE,
    FONT_REGULAR,
    FONT_SMALL,
    FONT_SUBHEADER,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from ui.widgets import PasswordEntry, SectionCard, StatusLabel


class PasswordPage(ctk.CTkFrame):
    """
    Halaman Brankas Kata Sandi.
    Menyimpan kredensial akun terenkripsi di SQLite dengan kategori 'sandi'.
    Menyediakan generator password acak dan pembersih clipboard otomatis 20 detik.
    """

    def __init__(self, master, store_factory=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.store_factory = store_factory or (
            lambda vig, rail, aes: SecureMessageStore(buat_pipeline(vig, rail, aes))
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_form_section()
        self._build_list_section()
        self.refresh_list()

    def _build_form_section(self) -> None:
        self.form_card = SectionCard(self, title="🔑 Tambah Akun & Kata Sandi")
        self.form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)

        # 1. Akun / Situs
        ctk.CTkLabel(self.form_card, text="Layanan / Situs:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(4, 2)
        )
        self.site_entry = ctk.CTkEntry(
            self.form_card, placeholder_text="Contoh: GitHub, Google, Bank...", font=FONT_REGULAR
        )
        self.site_entry.pack(fill="x", padx=16, pady=(0, 6))

        # 2. Username / Email
        ctk.CTkLabel(self.form_card, text="Username / Email:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(2, 2)
        )
        self.user_entry = ctk.CTkEntry(
            self.form_card, placeholder_text="Contoh: user@gmail.com", font=FONT_REGULAR
        )
        self.user_entry.pack(fill="x", padx=16, pady=(0, 6))

        # 3. Kata Sandi + Tombol Acak
        ctk.CTkLabel(self.form_card, text="Kata Sandi Akun:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(2, 2)
        )
        pw_row = ctk.CTkFrame(self.form_card, fg_color="transparent")
        pw_row.pack(fill="x", padx=16, pady=(0, 6))
        pw_row.grid_columnconfigure(0, weight=1)

        self.account_pw_entry = PasswordEntry(pw_row, placeholder_text="Kata sandi akun...")
        self.account_pw_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.gen_btn = ctk.CTkButton(
            pw_row,
            text="🎲 Acak",
            width=65,
            command=self._generate_random_password,
            font=FONT_SMALL,
        )
        self.gen_btn.grid(row=0, column=1)

        # 4. Kunci Enkripsi Brankas
        ctk.CTkLabel(
            self.form_card, text="Kunci Brankas (Super Enkripsi):", font=FONT_SUBHEADER, anchor="w"
        ).pack(fill="x", padx=16, pady=(6, 2))

        key_grid = ctk.CTkFrame(self.form_card, fg_color="transparent")
        key_grid.pack(fill="x", padx=16, pady=(0, 6))
        key_grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(key_grid, text="Vigenère:", font=FONT_SMALL).grid(row=0, column=0, sticky="w", pady=2)
        self.vig_entry = ctk.CTkEntry(key_grid, placeholder_text="Kunci teks", font=FONT_CODE)
        self.vig_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=2)

        ctk.CTkLabel(key_grid, text="Rail Fence:", font=FONT_SMALL).grid(row=1, column=0, sticky="w", pady=2)
        self.rail_entry = ctk.CTkEntry(key_grid, placeholder_text="Angka >= 1", font=FONT_CODE)
        self.rail_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=2)

        ctk.CTkLabel(key_grid, text="Password AES:", font=FONT_SMALL).grid(row=2, column=0, sticky="w", pady=2)
        self.aes_entry = PasswordEntry(key_grid, placeholder_text="Master password...")
        self.aes_entry.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=2)

        self.status_label = StatusLabel(self.form_card)
        self.status_label.pack(fill="x", padx=16, pady=(4, 4))

        # Tombol Simpan
        self.save_btn = ctk.CTkButton(
            self.form_card,
            text="💾 Simpan Kata Sandi",
            command=self._on_simpan,
            font=FONT_REGULAR,
        )
        self.save_btn.pack(fill="x", padx=16, pady=(4, 12))

    def _build_list_section(self) -> None:
        self.list_card = SectionCard(self, title="📋 Brankas Akun Tersimpan")
        self.list_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)

        self.scroll_list = ctk.CTkScrollableFrame(self.list_card, height=180)
        self.scroll_list.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        # Detail akun yang dibuka
        ctk.CTkLabel(self.list_card, text="Detail Kredensial:", font=FONT_SUBHEADER, anchor="w").pack(
            fill="x", padx=16, pady=(6, 2)
        )

        self.detail_box = ctk.CTkTextbox(self.list_card, height=100, font=FONT_CODE)
        self.detail_box.pack(fill="x", padx=16, pady=(0, 6))

        # Tombol aksi
        act_row = ctk.CTkFrame(self.list_card, fg_color="transparent")
        act_row.pack(fill="x", padx=16, pady=(0, 12))

        self.copy_btn = ctk.CTkButton(
            act_row,
            text="📋 Salin Password",
            command=self._copy_password_with_timeout,
            font=FONT_REGULAR,
            state="disabled",
        )
        self.copy_btn.pack(side="left", padx=(0, 8))

        self.clipboard_status = StatusLabel(act_row)
        self.clipboard_status.pack(side="left", padx=4)

        self.active_decrypted_password: str | None = None
        self.selected_id: int | None = None

    def _generate_random_password(self) -> None:
        """Membuat kata sandi acak berkekuatan tinggi (16 karakter)."""
        alphabet = string.ascii_letters + string.digits + "!@#$%&*-_=+"
        pw = "".join(secrets.choice(alphabet) for _ in range(16))
        self.account_pw_entry.set(pw)

    def refresh_list(self) -> None:
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        try:
            store = self.store_factory("DUMMY", 2, "DUMMY")
            akun_list = store.daftar(kategori="sandi")
        except Exception as e:
            self.status_label.set_status(f"Gagal memuat database: {e}", "error")
            return

        if not akun_list:
            lbl = ctk.CTkLabel(
                self.scroll_list,
                text="Belum ada akun tersimpan.",
                font=FONT_SMALL,
                text_color=TEXT_MUTED,
            )
            lbl.pack(pady=20)
            return

        for msg_id, judul in akun_list:
            item_frame = ctk.CTkFrame(self.scroll_list, fg_color="gray20", corner_radius=6)
            item_frame.pack(fill="x", pady=2, padx=2)

            lbl = ctk.CTkLabel(
                item_frame,
                text=f"🔑 {judul}",
                font=FONT_REGULAR,
                text_color=TEXT_PRIMARY,
                anchor="w",
            )
            lbl.pack(side="left", fill="x", expand=True, padx=8, pady=4)

            btn = ctk.CTkButton(
                item_frame,
                text="Buka",
                width=55,
                height=26,
                command=lambda mid=msg_id: self._on_buka(mid),
                font=FONT_SMALL,
            )
            btn.pack(side="right", padx=4, pady=4)

    def _on_simpan(self) -> None:
        site = self.site_entry.get().strip()
        user = self.user_entry.get().strip()
        pwd = self.account_pw_entry.get()
        vig_key = self.vig_entry.get().strip()
        rail_key = self.rail_entry.get().strip()
        aes_key = self.aes_entry.get().strip()

        if not site or not user or not pwd:
            self.status_label.set_status("Layanan, username, dan password akun harus diisi!", "error")
            return
        if not vig_key or not rail_key or not aes_key:
            self.status_label.set_status("Masukkan 3 kunci enkripsi brankas!", "error")
            return
        if not rail_key.isdigit() or int(rail_key) < 1:
            self.status_label.set_status("Kunci Rail Fence harus berupa angka >= 1!", "error")
            return

        payload = json.dumps({"site": site, "user": user, "password": pwd}, indent=2)
        try:
            store = self.store_factory(vig_key, int(rail_key), aes_key)
            new_id = store.simpan(site, payload, kategori="sandi")
            self.status_label.set_status(f"Akun '{site}' berhasil diamankan!", "success")
            self.site_entry.delete(0, "end")
            self.user_entry.delete(0, "end")
            self.account_pw_entry.delete(0, "end")
            self.refresh_list()
        except Exception as e:
            self.status_label.set_status(f"Gagal menyimpan: {e}", "error")

    def _on_buka(self, msg_id: int) -> None:
        vig_key = self.vig_entry.get().strip()
        rail_key = self.rail_entry.get().strip()
        aes_key = self.aes_entry.get().strip()

        if not vig_key or not rail_key or not aes_key:
            self.status_label.set_status("Masukkan 3 kunci brankas di kiri untuk membuka akun!", "warning")
            return

        try:
            store = self.store_factory(vig_key, int(rail_key), aes_key)
            hasil = store.buka(msg_id)
            if hasil is None:
                self.detail_box.delete("1.0", "end")
                self.detail_box.insert("1.0", "[GAGAL: Password AES salah atau data rusak]")
                self.copy_btn.configure(state="disabled")
                self.active_decrypted_password = None
                return

            try:
                data = json.loads(hasil)
                formatted = f"Layanan: {data.get('site')}\nUsername: {data.get('user')}\nPassword: {data.get('password')}"
                self.active_decrypted_password = data.get("password")
                self.copy_btn.configure(state="normal")
            except Exception:
                formatted = hasil
                self.active_decrypted_password = hasil
                self.copy_btn.configure(state="normal")

            self.detail_box.delete("1.0", "end")
            self.detail_box.insert("1.0", formatted)
            self.selected_id = msg_id
            self.status_label.set_status("Kredensial berhasil dibuka.", "success")
        except Exception as e:
            self.status_label.set_status(f"Gagal membuka kredensial: {e}", "error")

    def _copy_password_with_timeout(self) -> None:
        """Menyalin password ke clipboard dan otomatis menghapusnya setelah 20 detik."""
        if not self.active_decrypted_password:
            return

        self.clipboard_clear()
        self.clipboard_append(self.active_decrypted_password)
        self.update()

        self.clipboard_status.set_status("Tersalin! (Akan dihapus dlm 20 dtk)", "success")
        self.after(20000, self._auto_clear_clipboard)

    def _auto_clear_clipboard(self) -> None:
        """Mengosongkan clipboard sistem demi keamanan."""
        try:
            self.clipboard_clear()
            self.clipboard_status.set_status("Clipboard telah dibersihkan.", "info")
        except Exception:
            pass
