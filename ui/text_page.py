from __future__ import annotations

import tkinter.messagebox as mb
import customtkinter as ctk

from database.db import SecureMessageStore, buat_pipeline
from ui.theme import (
    FONT_CODE,
    FONT_HEADER,
    FONT_REGULAR,
    FONT_SMALL,
    FONT_SUBHEADER,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from ui.widgets import PasswordEntry, SectionCard, StatusLabel


class TextPage(ctk.CTkFrame):
    """
    Halaman Catatan Rahasia.
    Menerapkan Super Enkripsi (Vigenère + Rail Fence + AES-256-GCM) sebelum
    disimpan ke dalam basis data SQLite.
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
        """Panel kiri: Form input dan kunci enkripsi."""
        self.form_card = SectionCard(self, title="📝 Tulis Catatan Rahasia")
        self.form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)

        # Field Judul
        ctk.CTkLabel(self.form_card, text="Judul Catatan:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(4, 2)
        )
        self.title_entry = ctk.CTkEntry(
            self.form_card, placeholder_text="Masukkan judul catatan...", font=FONT_REGULAR
        )
        self.title_entry.pack(fill="x", padx=16, pady=(0, 8))

        # Field Isi Pesan
        ctk.CTkLabel(self.form_card, text="Isi Catatan Rahasia:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(4, 2)
        )
        self.content_text = ctk.CTkTextbox(self.form_card, height=120, font=FONT_REGULAR)
        self.content_text.pack(fill="x", padx=16, pady=(0, 8))

        # Field Tiga Kunci Super Enkripsi
        ctk.CTkLabel(
            self.form_card,
            text="Kunci Super Enkripsi (Klasik + Modern):",
            font=FONT_SUBHEADER,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(6, 2))

        key_grid = ctk.CTkFrame(self.form_card, fg_color="transparent")
        key_grid.pack(fill="x", padx=16, pady=(0, 4))
        key_grid.grid_columnconfigure(1, weight=1)

        # 1. Kunci Vigenère
        ctk.CTkLabel(key_grid, text="1. Vigenère (Teks):", font=FONT_SMALL).grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.vig_entry = ctk.CTkEntry(
            key_grid, placeholder_text="Contoh: KUNCIVIG", font=FONT_CODE
        )
        self.vig_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)

        # 2. Kunci Rail Fence
        ctk.CTkLabel(key_grid, text="2. Rail Fence (Angka):", font=FONT_SMALL).grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.rail_entry = ctk.CTkEntry(
            key_grid, placeholder_text="Contoh: 3", font=FONT_CODE
        )
        self.rail_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)

        # 3. Password AES
        ctk.CTkLabel(key_grid, text="3. AES-256 (Password):", font=FONT_SMALL).grid(
            row=2, column=0, sticky="w", pady=4
        )
        self.aes_entry = PasswordEntry(key_grid, placeholder_text="Password kuat...")
        self.aes_entry.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=4)

        # Info Karakteristik Cipher Klasik
        ctk.CTkLabel(
            self.form_card,
            text="ℹ️ Catatan: Kunci AES yang salah akan memicu error otentikasi GCM. "
            "Namun kunci Vigenère / Rail Fence yang salah akan menghasilkan teks teracak tanpa error.",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            wraplength=380,
            justify="left",
        ).pack(fill="x", padx=16, pady=(4, 8))

        # Tombol Simpan
        self.status_label = StatusLabel(self.form_card)
        self.status_label.pack(fill="x", padx=16, pady=(0, 4))

        btn_row = ctk.CTkFrame(self.form_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(4, 12))

        self.save_btn = ctk.CTkButton(
            btn_row,
            text="💾 Simpan Terenkripsi",
            command=self._on_simpan,
            font=FONT_REGULAR,
        )
        self.save_btn.pack(side="left", padx=(0, 8))

        self.clear_btn = ctk.CTkButton(
            btn_row,
            text="Bersihkan",
            fg_color="gray30",
            hover_color="gray40",
            command=self._clear_form,
            font=FONT_REGULAR,
            width=80,
        )
        self.clear_btn.pack(side="left")

    def _build_list_section(self) -> None:
        """Panel kanan: Daftar catatan tersimpan di database dan penampil isi."""
        self.list_card = SectionCard(self, title="🗄️ Daftar Catatan Tersimpan")
        self.list_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)

        # Area Scrollable Frame untuk daftar catatan
        self.scroll_list = ctk.CTkScrollableFrame(self.list_card, height=180)
        self.scroll_list.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        # Preview hasil dekripsi
        ctk.CTkLabel(
            self.list_card, text="Isi Catatan Terdekripsi:", font=FONT_SUBHEADER, anchor="w"
        ).pack(fill="x", padx=16, pady=(6, 2))

        self.view_box = ctk.CTkTextbox(self.list_card, height=140, font=FONT_REGULAR)
        self.view_box.pack(fill="x", padx=16, pady=(0, 8))

        # Tombol aksi daftar
        act_row = ctk.CTkFrame(self.list_card, fg_color="transparent")
        act_row.pack(fill="x", padx=16, pady=(0, 12))

        self.refresh_btn = ctk.CTkButton(
            act_row,
            text="🔄 Segarkan",
            width=90,
            command=self.refresh_list,
            font=FONT_REGULAR,
        )
        self.refresh_btn.pack(side="left", padx=(0, 8))

        self.delete_btn = ctk.CTkButton(
            act_row,
            text="🗑️ Hapus",
            fg_color="#a83232",
            hover_color="#c43b3b",
            width=80,
            command=self._on_hapus,
            font=FONT_REGULAR,
        )
        self.delete_btn.pack(side="left")

        self.selected_id: int | None = None

    def refresh_list(self) -> None:
        """Memuat ulang daftar catatan kategori 'catatan' dari basis data."""
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        try:
            # Gunakan pipeline dummy untuk memuat daftar
            store = self.store_factory("KUNCI", 2, "DUMMY")
            catatan_list = store.daftar(kategori="catatan")
        except Exception as e:
            self.status_label.set_status(f"Gagal memuat database: {e}", "error")
            return

        if not catatan_list:
            lbl = ctk.CTkLabel(
                self.scroll_list,
                text="Belum ada catatan rahasia tersimpan.",
                font=FONT_SMALL,
                text_color=TEXT_MUTED,
            )
            lbl.pack(pady=20)
            return

        for msg_id, judul in catatan_list:
            item_frame = ctk.CTkFrame(self.scroll_list, fg_color="gray20", corner_radius=6)
            item_frame.pack(fill="x", pady=2, padx=2)

            lbl = ctk.CTkLabel(
                item_frame,
                text=f"#{msg_id} - {judul}",
                font=FONT_REGULAR,
                text_color=TEXT_PRIMARY,
                anchor="w",
            )
            lbl.pack(side="left", fill="x", expand=True, padx=8, pady=4)

            open_btn = ctk.CTkButton(
                item_frame,
                text="🔓 Buka",
                width=60,
                height=26,
                command=lambda mid=msg_id: self._on_buka(mid),
                font=FONT_SMALL,
            )
            open_btn.pack(side="right", padx=4, pady=4)

    def _on_simpan(self) -> None:
        """Menyimpan catatan dengan Super Enkripsi."""
        judul = self.title_entry.get().strip()
        pesan = self.content_text.get("1.0", "end-1c").strip()
        vig_key = self.vig_entry.get().strip()
        rail_key = self.rail_entry.get().strip()
        aes_key = self.aes_entry.get().strip()

        if not judul:
            self.status_label.set_status("Judul catatan tidak boleh kosong!", "error")
            return
        if not pesan:
            self.status_label.set_status("Isi catatan tidak boleh kosong!", "error")
            return
        if not vig_key:
            self.status_label.set_status("Kunci Vigenère harus diisi!", "error")
            return
        if not rail_key.isdigit() or int(rail_key) < 1:
            self.status_label.set_status("Kunci Rail Fence harus bilangan bulat >= 1!", "error")
            return
        if not aes_key:
            self.status_label.set_status("Password AES harus diisi!", "error")
            return

        try:
            store = self.store_factory(vig_key, int(rail_key), aes_key)
            new_id = store.simpan(judul, pesan, kategori="catatan")
            self.status_label.set_status(f"Catatan #{new_id} berhasil disimpan!", "success")
            self.title_entry.delete(0, "end")
            self.content_text.delete("1.0", "end")
            self.refresh_list()
        except Exception as e:
            self.status_label.set_status(f"Gagal menyimpan: {e}", "error")

    def _on_buka(self, msg_id: int) -> None:
        """Membuka dan mendekripsi catatan menggunakan tiga kunci yang tertera di form."""
        vig_key = self.vig_entry.get().strip()
        rail_key = self.rail_entry.get().strip()
        aes_key = self.aes_entry.get().strip()

        if not vig_key or not rail_key or not aes_key:
            self.status_label.set_status(
                "Harap masukkan 3 kunci enkripsi di panel kiri untuk membuka catatan ini!",
                "warning",
            )
            return

        try:
            store = self.store_factory(vig_key, int(rail_key), aes_key)
            hasil = store.buka(msg_id)
            if hasil is None:
                self.view_box.delete("1.0", "end")
                self.view_box.insert("1.0", "[GAGAL: Password AES salah atau data rusak]")
                self.status_label.set_status("Password AES salah atau data rusak!", "error")
            else:
                self.selected_id = msg_id
                self.view_box.delete("1.0", "end")
                self.view_box.insert("1.0", hasil)
                self.status_label.set_status(
                    f"Catatan #{msg_id} berhasil dibuka.", "success"
                )
        except Exception as e:
            self.status_label.set_status(f"Error membuka catatan: {e}", "error")

    def _on_hapus(self) -> None:
        """Menghapus catatan yang sedang dipilih."""
        if not self.selected_id:
            self.status_label.set_status("Pilih catatan terlebih dahulu!", "warning")
            return
        if mb.askyesno("Konfirmasi Hapus", f"Hapus catatan #{self.selected_id}?"):
            try:
                store = self.store_factory("DUMMY", 2, "DUMMY")
                store.hapus(self.selected_id)
                self.selected_id = None
                self.view_box.delete("1.0", "end")
                self.status_label.set_status("Catatan berhasil dihapus.", "info")
                self.refresh_list()
            except Exception as e:
                self.status_label.set_status(f"Gagal menghapus: {e}", "error")

    def _clear_form(self) -> None:
        self.title_entry.delete(0, "end")
        self.content_text.delete("1.0", "end")
        self.vig_entry.delete(0, "end")
        self.rail_entry.delete(0, "end")
        self.aes_entry.delete(0, "end")
        self.status_label.clear()
