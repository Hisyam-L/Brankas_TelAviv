from __future__ import annotations

from pathlib import Path
import customtkinter as ctk

from blockchain.blockchain import Blockchain, BlockchainError
from blockchain.registry import DocumentError, DocumentRegistry
from config import CHAIN_PATH
from ui.theme import (
    ERROR_COLOR,
    FONT_CODE,
    FONT_HEADER,
    FONT_REGULAR,
    FONT_SMALL,
    FONT_SUBHEADER,
    SUCCESS_COLOR,
    TEXT_MUTED,
    TEXT_PRIMARY,
    WARNING_COLOR,
)
from ui.widgets import FilePicker, SectionCard, StatusLabel


class AssetPage(ctk.CTkFrame):
    """
    Halaman Aset Penting & Integritas Dokumen (Blockchain).
    Mencatat sidik jari SHA-256 berkas penting ke buku besar terdistribusi sederhana
    (Proof-of-Work Mining) dan memverifikasi keasliannya dari pemalsuan.
    """

    def __init__(self, master, registry=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.blockchain = Blockchain(path=CHAIN_PATH)
        self.registry = registry or DocumentRegistry(self.blockchain)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.selected_block_idx: int | None = None

        self._build_register_section()
        self._build_verify_and_chain_section()
        self.refresh_documents_list()

    def _build_register_section(self) -> None:
        """Panel Kiri: Registrasi dokumen & daftar dokumen."""
        self.reg_card = SectionCard(self, title="📜 Pendaftaran Dokumen ke Blockchain")
        self.reg_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)

        # Form Registrasi
        ctk.CTkLabel(self.reg_card, text="Jenis Dokumen:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(4, 2)
        )
        self.type_entry = ctk.CTkEntry(
            self.reg_card, placeholder_text="Contoh: Ijazah S1, Sertifikat Tanah, BPKB...", font=FONT_REGULAR
        )
        self.type_entry.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(self.reg_card, text="Nama Pemilik Sah:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(2, 2)
        )
        self.owner_entry = ctk.CTkEntry(
            self.reg_card, placeholder_text="Contoh: Budi Santoso", font=FONT_REGULAR
        )
        self.owner_entry.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(self.reg_card, text="Pilih Berkas Dokumen:", font=FONT_REGULAR, anchor="w").pack(
            fill="x", padx=16, pady=(2, 2)
        )
        self.file_picker = FilePicker(self.reg_card, btn_text="Pilih Dokumen...")
        self.file_picker.pack(fill="x", padx=16, pady=(0, 6))

        self.reg_status = StatusLabel(self.reg_card)
        self.reg_status.pack(fill="x", padx=16, pady=(0, 4))

        self.reg_btn = ctk.CTkButton(
            self.reg_card,
            text="⛏️ Daftarkan & Tambah Blok (PoW)",
            command=self._on_register_document,
            font=FONT_REGULAR,
        )
        self.reg_btn.pack(fill="x", padx=16, pady=(2, 10))

        # Tabel Dokumen Terdaftar
        ctk.CTkLabel(
            self.reg_card, text="Daftar Dokumen Terdaftar di Rantai:", font=FONT_SUBHEADER, anchor="w"
        ).pack(fill="x", padx=16, pady=(6, 2))

        self.doc_scroll = ctk.CTkScrollableFrame(self.reg_card, height=160)
        self.doc_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    def _build_verify_and_chain_section(self) -> None:
        """Panel Kanan: Verifikasi keaslian berkas & status kesehatan blockchain."""
        self.right_card = SectionCard(self, title="🔍 Verifikasi Keaslian & Integritas Rantai")
        self.right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)

        # 1. Verifikasi Berkas
        ctk.CTkLabel(
            self.right_card,
            text="Pilih Berkas Dokumen yang Ingin Diuji Keasliannya:",
            font=FONT_REGULAR,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 2))

        self.verify_picker = FilePicker(self.right_card, btn_text="Pilih Berkas Uji...")
        self.verify_picker.pack(fill="x", padx=16, pady=(0, 8))

        self.selected_target_label = ctk.CTkLabel(
            self.right_card,
            text="Target Blok Spesifik: Semua Blok (Otomatis)",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.selected_target_label.pack(fill="x", padx=16, pady=(0, 6))

        v_btn_row = ctk.CTkFrame(self.right_card, fg_color="transparent")
        v_btn_row.pack(fill="x", padx=16, pady=(0, 8))

        self.verify_btn = ctk.CTkButton(
            v_btn_row,
            text="🔎 Uji Keaslian Dokumen",
            command=self._on_verify_file,
            font=FONT_REGULAR,
        )
        self.verify_btn.pack(side="left", padx=(0, 8))

        self.reset_target_btn = ctk.CTkButton(
            v_btn_row,
            text="Reset Target",
            width=85,
            fg_color="gray30",
            hover_color="gray40",
            command=self._reset_target_block,
            font=FONT_SMALL,
        )
        self.reset_target_btn.pack(side="left")

        # Banner Hasil Verifikasi
        self.result_badge = ctk.CTkLabel(
            self.right_card,
            text="Status: Siap Verifikasi",
            font=FONT_SUBHEADER,
            corner_radius=6,
            fg_color="gray20",
            height=34,
        )
        self.result_badge.pack(fill="x", padx=16, pady=(0, 4))

        self.result_detail = ctk.CTkLabel(
            self.right_card,
            text="",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            wraplength=380,
            justify="left",
        )
        self.result_detail.pack(fill="x", padx=16, pady=(0, 10))

        # 2. Cek Integritas Blockchain
        ctk.CTkLabel(
            self.right_card, text="Struktur Rantai Blok (Ledger):", font=FONT_SUBHEADER, anchor="w"
        ).pack(fill="x", padx=16, pady=(6, 2))

        self.chain_scroll = ctk.CTkScrollableFrame(self.right_card, height=130)
        self.chain_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        c_btn_row = ctk.CTkFrame(self.right_card, fg_color="transparent")
        c_btn_row.pack(fill="x", padx=16, pady=(0, 12))

        self.check_chain_btn = ctk.CTkButton(
            c_btn_row,
            text="🛡️ Cek Integritas Seluruh Rantai",
            command=self._on_check_chain_integrity,
            font=FONT_REGULAR,
            fg_color="#1f6feb",
            hover_color="#388bfd",
        )
        self.check_chain_btn.pack(side="left", padx=(0, 8))

        self.chain_status_label = StatusLabel(c_btn_row)
        self.chain_status_label.pack(side="left", padx=4)

    def refresh_documents_list(self) -> None:
        """Memuat daftar dokumen dari blockchain."""
        for w in self.doc_scroll.winfo_children():
            w.destroy()

        try:
            # Muat ulang blockchain dari disk
            self.blockchain = Blockchain(path=CHAIN_PATH)
            self.registry = DocumentRegistry(self.blockchain)
            docs = self.registry.list_documents()
        except Exception as e:
            self.reg_status.set_status(f"Gagal memuat rantai: {e}", "error")
            return

        if not docs:
            ctk.CTkLabel(
                self.doc_scroll, text="Belum ada dokumen terdaftar.", font=FONT_SMALL, text_color=TEXT_MUTED
            ).pack(pady=20)
        else:
            for d in docs:
                b_idx = d["blok"]
                row_f = ctk.CTkFrame(self.doc_scroll, fg_color="gray20", corner_radius=6)
                row_f.pack(fill="x", pady=2, padx=2)

                txt = f"Blok #{b_idx}: {d['jenis']} - {d['pemilik']} ({d['nama_file']})"
                ctk.CTkLabel(row_f, text=txt, font=FONT_SMALL, anchor="w").pack(
                    side="left", fill="x", expand=True, padx=8, pady=4
                )

                sel_btn = ctk.CTkButton(
                    row_f,
                    text="Pilih",
                    width=50,
                    height=24,
                    command=lambda b=b_idx: self._select_target_block(b),
                    font=FONT_SMALL,
                )
                sel_btn.pack(side="right", padx=4, pady=4)

        # Perbarui ringkasan blok
        self._refresh_chain_view()

    def _refresh_chain_view(self) -> None:
        for w in self.chain_scroll.winfo_children():
            w.destroy()

        for b in self.blockchain.chain:
            bf = ctk.CTkFrame(self.chain_scroll, fg_color="gray15", corner_radius=4)
            bf.pack(fill="x", pady=2, padx=2)

            h_short = f"{b.hash[:8]}...{b.hash[-6:]}"
            prev_short = f"{b.previous_hash[:8]}..." if len(b.previous_hash) > 10 else b.previous_hash
            txt = f"Blok #{b.index} | Hash: {h_short} | Prev: {prev_short} | Nonce: {b.nonce}"
            ctk.CTkLabel(bf, text=txt, font=FONT_CODE, text_color=TEXT_MUTED, anchor="w").pack(
                padx=6, pady=3
            )

    def _select_target_block(self, block_idx: int) -> None:
        self.selected_block_idx = block_idx
        self.selected_target_label.configure(
            text=f"Target Blok Spesifik: Blok #{block_idx}", text_color=TEXT_PRIMARY
        )

    def _reset_target_block(self) -> None:
        self.selected_block_idx = None
        self.selected_target_label.configure(
            text="Target Blok Spesifik: Semua Blok (Otomatis)", text_color=TEXT_MUTED
        )

    def _on_register_document(self) -> None:
        jenis = self.type_entry.get().strip()
        pemilik = self.owner_entry.get().strip()
        file_path = self.file_picker.get_path()

        if not jenis or not pemilik:
            self.reg_status.set_status("Jenis dokumen dan pemilik tidak boleh kosong!", "error")
            return
        if not file_path or not Path(file_path).exists():
            self.reg_status.set_status("Pilih berkas dokumen yang valid!", "error")
            return

        self.reg_btn.configure(state="disabled")
        self.reg_status.set_status("Menghitung hash SHA-256 dan melakukan PoW mining...", "info")

        try:
            blok = self.registry.register(file_path, jenis, pemilik)
            self.reg_status.set_status(
                f"Sukses! Dokumen tercatat di Blok #{blok.index} (Hash: {blok.hash[:12]}...)",
                "success",
            )
            self.type_entry.delete(0, "end")
            self.owner_entry.delete(0, "end")
            self.file_picker.clear()
            self.refresh_documents_list()
        except DocumentError as e:
            self.reg_status.set_status(str(e), "error")
        except Exception as e:
            self.reg_status.set_status(f"Gagal mendaftarkan: {e}", "error")
        finally:
            self.reg_btn.configure(state="normal")

    def _on_verify_file(self) -> None:
        file_path = self.verify_picker.get_path()
        if not file_path or not Path(file_path).exists():
            self.result_badge.configure(
                text="STATUS: PILIH BERKAS TERLEBIH DAHULU", fg_color=ERROR_COLOR
            )
            self.result_detail.configure(text="Pilih berkas dokumen fisik untuk diverifikasi.")
            return

        try:
            status, ket = self.registry.verify(file_path, block_index=self.selected_block_idx)
            if status == "ASLI":
                self.result_badge.configure(text="✅ ASLI (TERVERIFIKASI INTEGRITASNYA)", fg_color=SUCCESS_COLOR)
            elif status == "DIUBAH":
                self.result_badge.configure(text="❌ DIUBAH / DIPALSUKAN", fg_color=ERROR_COLOR)
            elif status == "TIDAK_TERDAFTAR":
                self.result_badge.configure(text="⚠️ TIDAK TERDAFTAR", fg_color=WARNING_COLOR)
            elif status == "RANTAI_RUSAK":
                self.result_badge.configure(text="🚨 RANTAI RUSAK / DIMANIPULASI", fg_color=ERROR_COLOR)

            self.result_detail.configure(text=ket)
        except Exception as e:
            self.result_badge.configure(text="ERROR VERIFIKASI", fg_color=ERROR_COLOR)
            self.result_detail.configure(text=str(e))

    def _on_check_chain_integrity(self) -> None:
        try:
            self.blockchain = Blockchain(path=CHAIN_PATH)
            valid, msg = self.blockchain.is_valid()
            if valid:
                self.chain_status_label.set_status(f"Rantai Valid ({len(self.blockchain.chain)} Blok)", "success")
            else:
                self.chain_status_label.set_status(f"Peringatan: {msg}", "error")
            self._refresh_chain_view()
        except Exception as e:
            self.chain_status_label.set_status(f"Gagal mengecek: {e}", "error")
