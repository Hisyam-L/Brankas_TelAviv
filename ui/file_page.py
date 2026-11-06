from __future__ import annotations

import threading
from pathlib import Path
import customtkinter as ctk

from config import OUTPUT_DIR
from crypto.file_enkripsi import ChaChaFileCipher, FileCipherError
from ui.theme import (
    FONT_CODE,
    FONT_HEADER,
    FONT_REGULAR,
    FONT_SMALL,
    FONT_SUBHEADER,
    TEXT_MUTED,
)
from ui.widgets import FilePicker, PasswordEntry, SectionCard, StatusLabel


class FilePage(ctk.CTkFrame):
    """
    Halaman Enkripsi & Dekripsi Berkas.
    Menggunakan ChaCha20-Poly1305 per chunk 1 MB dengan otentikasi AAD dan
    penurunan kunci scrypt. Operasi dieksekusi di background thread.
    """

    def __init__(self, master, cipher_factory=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.cipher_factory = cipher_factory or (lambda pw: ChaChaFileCipher(pw))

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.card = SectionCard(self, title="📁 Enkripsi & Dekripsi Berkas Aman")
        self.card.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Pilih berkas
        ctk.CTkLabel(self.card, text="Pilih Berkas Asal:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=20, pady=(10, 4)
        )
        self.file_picker = FilePicker(
            self.card,
            btn_text="Jelajahi Berkas...",
            on_file_selected=self._on_file_chosen,
        )
        self.file_picker.pack(fill="x", padx=20, pady=(0, 10))

        # 2. Input Password
        ctk.CTkLabel(
            self.card, text="Password Enkripsi Berkas:", font=FONT_REGULAR, anchor="w"
        ).pack(fill="x", padx=20, pady=(4, 4))
        self.password_entry = PasswordEntry(
            self.card, placeholder_text="Masukkan password berkas..."
        )
        self.password_entry.pack(fill="x", padx=20, pady=(0, 12))

        # 3. Baris info ukuran & lokasi berkas
        info_frame = ctk.CTkFrame(self.card, fg_color="gray20", corner_radius=6)
        info_frame.pack(fill="x", padx=20, pady=(0, 12))

        self.file_info_label = ctk.CTkLabel(
            info_frame,
            text="Ukuran Asal: -  |  Ukuran Hasil: -  |  Output: folder 'output/'",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        self.file_info_label.pack(padx=12, pady=8)

        # 4. Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.card)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(4, 8))

        # 5. Label status
        self.status_label = StatusLabel(self.card)
        self.status_label.pack(fill="x", padx=20, pady=(0, 12))

        # 6. Tombol Aksi
        btn_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 16))

        self.encrypt_btn = ctk.CTkButton(
            btn_frame,
            text="🔒 Enkripsi Berkas (.enc)",
            font=FONT_REGULAR,
            command=self._start_encrypt,
        )
        self.encrypt_btn.pack(side="left", padx=(0, 12))

        self.decrypt_btn = ctk.CTkButton(
            btn_frame,
            text="🔓 Dekripsi Berkas",
            font=FONT_REGULAR,
            command=self._start_decrypt,
            fg_color="#238636",
            hover_color="#2ea043",
        )
        self.decrypt_btn.pack(side="left")

    def _on_file_chosen(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            size_mb = p.stat().st_size / (1024 * 1024)
            self.file_info_label.configure(
                text=f"Berkas: {p.name} ({size_mb:.2f} MB)  |  Output: folder 'output/'"
            )

    def _set_ui_state(self, is_processing: bool) -> None:
        state = "disabled" if is_processing else "normal"
        self.encrypt_btn.configure(state=state)
        self.decrypt_btn.configure(state=state)
        self.file_picker.btn.configure(state=state)

    def _start_encrypt(self) -> None:
        path_str = self.file_picker.get_path()
        password = self.password_entry.get()

        if not path_str or not Path(path_str).exists():
            self.status_label.set_status("Pilih berkas yang valid terlebih dahulu!", "error")
            return
        if not password:
            self.status_label.set_status("Password enkripsi tidak boleh kosong!", "error")
            return

        self._set_ui_state(True)
        self.progress_bar.set(0)
        self.status_label.set_status("Memulai proses enkripsi ChaCha20-Poly1305...", "info")

        def worker():
            src_path = Path(path_str)
            dest_path = OUTPUT_DIR / f"{src_path.name}.enc"
            try:
                cipher = self.cipher_factory(password)
                cipher.encrypt_file(
                    src_path,
                    dest_path,
                    progress_callback=lambda p: self.after(0, lambda: self.progress_bar.set(p)),
                )
                orig_size = src_path.stat().st_size
                enc_size = dest_path.stat().st_size
                self.after(
                    0,
                    lambda: self._on_finish_success(
                        f"Enkripsi berhasil! Disimpan di: {dest_path.name}",
                        orig_size,
                        enc_size,
                    ),
                )
            except FileCipherError as e:
                self.after(0, lambda: self._on_finish_error(str(e)))
            except Exception as e:
                self.after(0, lambda: self._on_finish_error(f"Error tidak terduga: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _start_decrypt(self) -> None:
        path_str = self.file_picker.get_path()
        password = self.password_entry.get()

        if not path_str or not Path(path_str).exists():
            self.status_label.set_status("Pilih berkas terenkripsi terlebih dahulu!", "error")
            return
        if not password:
            self.status_label.set_status("Password dekripsi tidak boleh kosong!", "error")
            return

        self._set_ui_state(True)
        self.progress_bar.set(0)
        self.status_label.set_status("Memulai proses dekripsi...", "info")

        def worker():
            src_path = Path(path_str)
            # Hilangkan ekstensi .enc bila ada, atau beri awalan decrypted_
            clean_name = src_path.name[:-4] if src_path.name.endswith(".enc") else f"dec_{src_path.name}"
            dest_path = OUTPUT_DIR / clean_name
            try:
                cipher = self.cipher_factory(password)
                cipher.decrypt_file(
                    src_path,
                    dest_path,
                    progress_callback=lambda p: self.after(0, lambda: self.progress_bar.set(p)),
                )
                enc_size = src_path.stat().st_size
                dec_size = dest_path.stat().st_size
                self.after(
                    0,
                    lambda: self._on_finish_success(
                        f"Dekripsi berhasil! Disimpan di: {dest_path.name}",
                        enc_size,
                        dec_size,
                    ),
                )
            except FileCipherError as e:
                self.after(0, lambda: self._on_finish_error(str(e)))
            except Exception as e:
                self.after(0, lambda: self._on_finish_error(f"Gagal dekripsi: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_finish_success(self, msg: str, orig_size: int, out_size: int) -> None:
        self.progress_bar.set(1.0)
        self._set_ui_state(False)
        self.status_label.set_status(msg, "success")
        self.file_info_label.configure(
            text=f"Asal: {orig_size / 1024:.1f} KB  |  Hasil: {out_size / 1024:.1f} KB  |  Status: Selesai"
        )

    def _on_finish_error(self, err_msg: str) -> None:
        self.progress_bar.set(0)
        self._set_ui_state(False)
        self.status_label.set_status(err_msg, "error")
