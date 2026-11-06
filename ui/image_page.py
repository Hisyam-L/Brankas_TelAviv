from __future__ import annotations

import os
from pathlib import Path
from PIL import Image
import customtkinter as ctk

from config import BASE_DIR, OUTPUT_DIR
from database.db import URUTAN, buat_pipeline
from stego.steganografi import LsbSteganography, SecureStego, StegoError
from crypto.super_enkripsi import CipherError
from ui.theme import (
    FONT_CODE,
    FONT_HEADER,
    FONT_REGULAR,
    FONT_SMALL,
    FONT_SUBHEADER,
    TEXT_MUTED,
    WARNING_COLOR,
)
from ui.widgets import FilePicker, PasswordEntry, SectionCard, StatusLabel


class ImagePage(ctk.CTkFrame):
    """
    Halaman Steganografi Citra (Foto Rahasia).
    Menyembunyikan pesan ber-Super Enkripsi ke dalam LSB kanal warna gambar PNG.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.stego = LsbSteganography()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_hide_section()
        self._build_reveal_section()

    def _build_hide_section(self) -> None:
        """Panel Kiri: Sembunyikan Pesan."""
        self.hide_card = SectionCard(self, title="🖼️ Sembunyikan Pesan ke Gambar")
        self.hide_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)

        # 1. Pilih Gambar Sampul
        ctk.CTkLabel(self.hide_card, text="Pilih Gambar Sampul (Cover):", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(4, 2)
        )
        self.cover_picker = FilePicker(
            self.hide_card,
            btn_text="Pilih Gambar...",
            filetypes=[("Berkas Gambar", "*.png *.jpg *.jpeg *.bmp"), ("Semua", "*.*")],
            on_file_selected=self._on_cover_selected,
        )
        self.cover_picker.pack(fill="x", padx=16, pady=(0, 4))

        # Preview Citra & Kapasitas
        self.preview_frame = ctk.CTkFrame(self.hide_card, fg_color="gray15", height=120)
        self.preview_frame.pack(fill="x", padx=16, pady=(0, 6))

        self.preview_label = ctk.CTkLabel(
            self.preview_frame, text="Pratinjau Gambar", font=FONT_SMALL, text_color=TEXT_MUTED
        )
        self.preview_label.pack(pady=10)

        self.capacity_label = ctk.CTkLabel(
            self.hide_card, text="Kapasitas Muatan: - byte", font=FONT_SMALL, text_color=TEXT_MUTED
        )
        self.capacity_label.pack(padx=16, pady=(0, 4), anchor="w")

        # 2. Pesan Rahasia
        ctk.CTkLabel(self.hide_card, text="Pesan Rahasia:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(2, 2)
        )
        self.secret_entry = ctk.CTkTextbox(self.hide_card, height=60, font=FONT_REGULAR)
        self.secret_entry.pack(fill="x", padx=16, pady=(0, 6))

        # 3. Kunci Super Enkripsi
        key_frame = ctk.CTkFrame(self.hide_card, fg_color="transparent")
        key_frame.pack(fill="x", padx=16, pady=(0, 4))
        key_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(key_frame, text="Vigenère:", font=FONT_SMALL).grid(row=0, column=0, sticky="w", pady=2)
        self.vig_entry = ctk.CTkEntry(key_frame, placeholder_text="Kunci teks", font=FONT_CODE)
        self.vig_entry.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=2)

        ctk.CTkLabel(key_frame, text="Rail Fence:", font=FONT_SMALL).grid(row=1, column=0, sticky="w", pady=2)
        self.rail_entry = ctk.CTkEntry(key_frame, placeholder_text="Angka >= 1", font=FONT_CODE)
        self.rail_entry.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=2)

        ctk.CTkLabel(key_frame, text="Password AES:", font=FONT_SMALL).grid(row=2, column=0, sticky="w", pady=2)
        self.aes_entry = PasswordEntry(key_frame, placeholder_text="Password...")
        self.aes_entry.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=2)

        # Peringatan Kompresi
        ctk.CTkLabel(
            self.hide_card,
            text="⚠️ Peringatan: Jangan kirim gambar hasil lewat WhatsApp/Telegram "
            "(kompresi gambar otomatis merusak bit LSB pesan rahasia).",
            font=FONT_SMALL,
            text_color=WARNING_COLOR,
            wraplength=380,
            justify="left",
        ).pack(fill="x", padx=16, pady=(4, 6))

        self.hide_status = StatusLabel(self.hide_card)
        self.hide_status.pack(fill="x", padx=16, pady=(0, 4))

        self.hide_btn = ctk.CTkButton(
            self.hide_card,
            text="🔒 Sembunyikan Pesan (Simpan PNG)",
            command=self._on_hide_message,
            font=FONT_REGULAR,
        )
        self.hide_btn.pack(fill="x", padx=16, pady=(4, 12))

    def _build_reveal_section(self) -> None:
        """Panel Kanan: Ungkap Pesan."""
        self.reveal_card = SectionCard(self, title="🔍 Ungkap Pesan dari Gambar Stego")
        self.reveal_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)

        ctk.CTkLabel(self.reveal_card, text="Pilih Gambar Stego (.png):", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(4, 2)
        )
        self.stego_picker = FilePicker(
            self.reveal_card,
            btn_text="Pilih Gambar Stego...",
            filetypes=[("Gambar PNG", "*.png"), ("Semua", "*.*")],
        )
        self.stego_picker.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            self.reveal_card,
            text="* Masukkan 3 kunci enkripsi pada panel kiri untuk mendekripsi isi pesan.",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 6))

        self.reveal_status = StatusLabel(self.reveal_card)
        self.reveal_status.pack(fill="x", padx=16, pady=(0, 4))

        self.reveal_btn = ctk.CTkButton(
            self.reveal_card,
            text="🔓 Ekstrak & Ungkap Pesan",
            command=self._on_reveal_message,
            font=FONT_REGULAR,
            fg_color="#238636",
            hover_color="#2ea043",
        )
        self.reveal_btn.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkLabel(self.reveal_card, text="Pesan Rahasia Terbaca:", font=FONT_SUBHEADER, anchor="w").pack(
            fill="x", padx=16, pady=(6, 2)
        )
        self.result_box = ctk.CTkTextbox(self.reveal_card, height=160, font=FONT_REGULAR)
        self.result_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    def _on_cover_selected(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            return
        try:
            cap = self.stego.capacity(p)
            self.capacity_label.configure(
                text=f"Kapasitas Muatan: {cap:,} byte ({cap / 1024:.1f} KB)",
                text_color=TEXT_MUTED,
            )
            # Muat thumbnail pratinjau
            img = Image.open(p)
            img.thumbnail((180, 80))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            self.preview_label.configure(image=ctk_img, text="")
        except Exception as e:
            self.capacity_label.configure(text=f"Error membaca gambar: {e}", text_color="red")

    def _on_hide_message(self) -> None:
        cover_path = self.cover_picker.get_path()
        message = self.secret_entry.get("1.0", "end-1c").strip()
        vig_key = self.vig_entry.get().strip()
        rail_key = self.rail_entry.get().strip()
        aes_key = self.aes_entry.get().strip()

        if not cover_path or not Path(cover_path).exists():
            self.hide_status.set_status("Pilih gambar sampul terlebih dahulu!", "error")
            return
        if not message:
            self.hide_status.set_status("Pesan rahasia tidak boleh kosong!", "error")
            return
        if not vig_key or not rail_key or not aes_key:
            self.hide_status.set_status("Semua 3 kunci enkripsi harus diisi!", "error")
            return
        if not rail_key.isdigit() or int(rail_key) < 1:
            self.hide_status.set_status("Kunci Rail Fence harus berupa angka >= 1!", "error")
            return

        try:
            pipeline = buat_pipeline(vig_key, int(rail_key), aes_key)
            sec_stego = SecureStego(self.stego, pipeline, URUTAN)
            out_name = f"stego_{Path(cover_path).stem}.png"
            dest_path = OUTPUT_DIR / out_name

            sec_stego.hide(cover_path, dest_path, message)
            self.hide_status.set_status(f"Berhasil disimpan di: output/{out_name}", "success")
            self.stego_picker.set_path(str(dest_path))
        except (StegoError, CipherError) as e:
            self.hide_status.set_status(str(e), "error")
        except Exception as e:
            self.hide_status.set_status(f"Gagal menyembunyikan: {e}", "error")

    def _on_reveal_message(self) -> None:
        stego_path = self.stego_picker.get_path()
        vig_key = self.vig_entry.get().strip()
        rail_key = self.rail_entry.get().strip()
        aes_key = self.aes_entry.get().strip()

        if not stego_path or not Path(stego_path).exists():
            self.reveal_status.set_status("Pilih berkas gambar stego terlebih dahulu!", "error")
            return
        if not vig_key or not rail_key or not aes_key:
            self.reveal_status.set_status("Masukkan 3 kunci pada panel kiri!", "error")
            return

        try:
            pipeline = buat_pipeline(vig_key, int(rail_key), aes_key)
            sec_stego = SecureStego(self.stego, pipeline, URUTAN)
            teks = sec_stego.reveal(stego_path)
            self.result_box.delete("1.0", "end")
            self.result_box.insert("1.0", teks)
            self.reveal_status.set_status("Pesan rahasia berhasil diungkap!", "success")
        except (StegoError, CipherError) as e:
            self.result_box.delete("1.0", "end")
            self.reveal_status.set_status(str(e), "error")
        except Exception as e:
            self.result_box.delete("1.0", "end")
            self.reveal_status.set_status(f"Gagal membaca gambar: {e}", "error")
