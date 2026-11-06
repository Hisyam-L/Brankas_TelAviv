from __future__ import annotations

import tkinter.filedialog as fd
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from ui.theme import (
    BORDER_COLOR,
    CARD_BG,
    ERROR_COLOR,
    FONT_CODE,
    FONT_REGULAR,
    FONT_SMALL,
    FONT_SUBHEADER,
    SUCCESS_COLOR,
    TEXT_MUTED,
    TEXT_PRIMARY,
    WARNING_COLOR,
)


class StatusLabel(ctk.CTkLabel):
    """Label status dengan warna dinamis (sukses, error, info, peringatan)."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            text="",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            wraplength=600,
            justify="left",
            **kwargs,
        )

    def set_status(self, text: str, status_type: str = "info") -> None:
        """Menyetel pesan status dan warna sesuai jenisnya."""
        colors = {
            "success": SUCCESS_COLOR,
            "error": ERROR_COLOR,
            "warning": WARNING_COLOR,
            "info": TEXT_MUTED,
        }
        self.configure(text=text, text_color=colors.get(status_type, TEXT_MUTED))

    def clear(self) -> None:
        self.configure(text="")


class PasswordEntry(ctk.CTkFrame):
    """Field input kata sandi dilengkapi tombol toggle intip kata sandi."""

    def __init__(
        self,
        master,
        placeholder_text: str = "Masukkan kata sandi...",
        width: int = 250,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder_text,
            show="•",
            font=FONT_REGULAR,
            width=width,
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self._is_visible = False
        self.toggle_btn = ctk.CTkButton(
            self,
            text="👁",
            width=36,
            height=32,
            fg_color="gray30",
            hover_color="gray40",
            command=self._toggle_visibility,
        )
        self.toggle_btn.grid(row=0, column=1)

    def _toggle_visibility(self) -> None:
        self._is_visible = not self._is_visible
        if self._is_visible:
            self.entry.configure(show="")
            self.toggle_btn.configure(fg_color="#1f6feb")
        else:
            self.entry.configure(show="•")
            self.toggle_btn.configure(fg_color="gray30")

    def get(self) -> str:
        return self.entry.get()

    def set(self, val: str) -> None:
        self.delete(0, "end")
        self.entry.insert(0, val)

    def delete(self, first, last=None) -> None:
        self.entry.delete(first, last)


class FilePicker(ctk.CTkFrame):
    """Komponen pemilih berkas dengan dialog berkas OS dan label path."""

    def __init__(
        self,
        master,
        btn_text: str = "Pilih Berkas...",
        filetypes: list[tuple[str, str]] | None = None,
        save_mode: bool = False,
        default_extension: str = "",
        on_file_selected: Callable[[str], None] | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(1, weight=1)

        self.filetypes = filetypes or [("Semua Berkas", "*.*")]
        self.save_mode = save_mode
        self.default_extension = default_extension
        self.on_file_selected = on_file_selected
        self.chosen_path: str = ""

        self.btn = ctk.CTkButton(
            self,
            text=btn_text,
            width=130,
            command=self._browse,
            font=FONT_REGULAR,
        )
        self.btn.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.path_label = ctk.CTkLabel(
            self,
            text="Belum ada berkas dipilih",
            font=FONT_CODE,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.path_label.grid(row=0, column=1, sticky="ew")

    def _browse(self) -> None:
        if self.save_mode:
            path = fd.asksaveasfilename(
                filetypes=self.filetypes,
                defaultextension=self.default_extension,
            )
        else:
            path = fd.askopenfilename(filetypes=self.filetypes)

        if path:
            self.set_path(path)
            if self.on_file_selected:
                self.on_file_selected(path)

    def set_path(self, path: str) -> None:
        self.chosen_path = path
        p = Path(path)
        self.path_label.configure(text=f"{p.name} ({p.parent})", text_color=TEXT_PRIMARY)

    def get_path(self) -> str:
        return self.chosen_path

    def clear(self) -> None:
        self.chosen_path = ""
        self.path_label.configure(text="Belum ada berkas dipilih", text_color=TEXT_MUTED)


class SectionCard(ctk.CTkFrame):
    """Kartu kontainer terstruktur untuk form dan pengelompokan elemen antarmuka."""

    def __init__(self, master, title: str | None = None, **kwargs):
        super().__init__(
            master,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=CARD_BG,
            **kwargs,
        )
        if title:
            self.header_label = ctk.CTkLabel(
                self,
                text=title,
                font=FONT_SUBHEADER,
                text_color=TEXT_PRIMARY,
                anchor="w",
            )
            self.header_label.pack(fill="x", padx=16, pady=(12, 6))
