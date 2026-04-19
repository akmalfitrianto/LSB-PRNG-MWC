"""
================================================================================
MODULE  : ui/views/frame_extraction.py
DESKRIPSI:
    Halaman Extraction — tempat pengguna mengekstrak pesan tersembunyi.

    ALUR UX:
      1. Pengguna memilih file citra stego (.png).
      2. Pengguna memasukkan password/kunci yang sama dengan saat embedding.
      3. Klik "Ekstrak Pesan" → jalankan extract_data() di background thread.
      4. Pesan yang berhasil diekstrak tampil di textbox hasil.
      5. Pengguna bisa menyalin pesan ke clipboard.
================================================================================
"""

import logging
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from engine.stego_lsb import extract_data
from ui import theme as T

logger = logging.getLogger(__name__)

_PREVIEW_SIZE = (220, 220)


class FrameExtraction(ctk.CTkFrame):
    """Frame halaman Extraction."""

    def __init__(self, parent: ctk.CTkFrame, controller) -> None:
        super().__init__(parent, fg_color=T.BG_APP, corner_radius=0)
        self.controller = controller

        self._path_stego: Path | None = None
        self._ctk_img_prev: ctk.CTkImage | None = None
        self._sedang_proses = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._bangun_ui()

    # ── UI Builder ────────────────────────────────────────────────────────────

    def _bangun_ui(self) -> None:
        # ── Header ────────────────────────────────────────────────────────────
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))

        ctk.CTkLabel(frame_header, text="Extraction", font=T.FONT_JUDUL, text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(
            frame_header,
            text="Ekstrak pesan tersembunyi dari citra stego",
            font=T.FONT_LABEL, text_color=T.TEKS_SEKUNDER,
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkFrame(frame_header, height=2, fg_color=T.AKSEN_SEKUNDER, corner_radius=1).pack(fill="x", pady=(12, 0))

        # ── Body ──────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._bangun_kolom_form(body)
        self._bangun_kolom_kanan(body)

    def _bangun_kolom_form(self, parent: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent", scrollbar_button_color=T.BORDER_NORMAL)
        scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # ── Seksi 1: Pilih Citra Stego ────────────────────────────────────────
        self._buat_label_seksi(scroll, "1  PILIH CITRA STEGO")

        frame_file = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        frame_file.pack(fill="x", pady=(4, 12))

        self._entry_path = ctk.CTkEntry(
            frame_file,
            placeholder_text="Belum ada file dipilih...",
            font=T.FONT_MONO_KECIL,
            fg_color=T.BG_WIDGET,
            border_color=T.BORDER_NORMAL,
            text_color=T.TEKS_PRIMER,
            state="disabled",
            height=36,
            corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_path.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkButton(
            frame_file,
            text="  Pilih File Stego (.png)",
            font=T.FONT_LABEL,
            height=34,
            corner_radius=T.RADIUS_BTN,
            fg_color=T.BTN_SEKUNDER_BG,
            text_color=T.TEKS_PRIMER,
            hover_color=T.BG_HOVER,
            command=self._pilih_file,
        ).pack(anchor="w", padx=12, pady=(0, 12))

        # ── Seksi 2: Kunci ────────────────────────────────────────────────────
        self._buat_label_seksi(scroll, "2  KUNCI / PASSWORD")

        frame_kunci = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        frame_kunci.pack(fill="x", pady=(4, 12))

        self._entry_kunci = ctk.CTkEntry(
            frame_kunci,
            placeholder_text="Masukkan kunci yang sama seperti saat embedding...",
            show="●",
            font=T.FONT_LABEL,
            fg_color=T.BG_WIDGET,
            border_color=T.BORDER_NORMAL,
            text_color=T.TEKS_PRIMER,
            height=38,
            corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_kunci.pack(fill="x", padx=12, pady=(12, 6))

        self._var_tampil_pass = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame_kunci,
            text="Tampilkan password",
            font=T.FONT_KECIL,
            text_color=T.TEKS_SEKUNDER,
            fg_color=T.AKSEN_SEKUNDER,
            border_color=T.BORDER_NORMAL,
            hover_color=T.AKSEN_SEKUNDER,
            variable=self._var_tampil_pass,
            command=self._toggle_password,
        ).pack(anchor="w", padx=12, pady=(0, 12))

        # ── Peringatan ────────────────────────────────────────────────────────
        frame_warn = ctk.CTkFrame(scroll, fg_color="#1c1a0a", corner_radius=T.RADIUS_CARD, border_width=1, border_color="#4a3c00")
        frame_warn.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            frame_warn,
            text="⚠  Kunci yang salah akan menghasilkan teks sampah atau error decoding.",
            font=T.FONT_KECIL,
            text_color=T.AKSEN_WARNING,
            wraplength=340,
            justify="left",
        ).pack(padx=12, pady=10)

        # ── Tombol Ekstrak ────────────────────────────────────────────────────
        self._btn_ekstrak = ctk.CTkButton(
            scroll,
            text="  ▶  Ekstrak Pesan",
            font=("Segoe UI", 13, "bold"),
            height=46,
            corner_radius=T.RADIUS_BTN,
            fg_color=T.AKSEN_SEKUNDER,
            text_color=T.BG_APP,
            hover_color="#1aa8e8",
            command=self._jalankan_ekstraksi,
        )
        self._btn_ekstrak.pack(fill="x", pady=(4, 8))

        self._progress = ctk.CTkProgressBar(
            scroll, fg_color=T.BG_WIDGET, progress_color=T.AKSEN_SEKUNDER, height=4, corner_radius=2,
        )
        self._progress.set(0)

        self._lbl_status = ctk.CTkLabel(scroll, text="", font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER)
        self._lbl_status.pack(anchor="w")

    def _bangun_kolom_kanan(self, parent: ctk.CTkFrame) -> None:
        """Kolom kanan: preview stego + area tampil hasil pesan."""
        kolom = ctk.CTkFrame(parent, fg_color="transparent")
        kolom.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Preview
        frame_prev = ctk.CTkFrame(kolom, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        frame_prev.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(frame_prev, text="Preview Citra Stego", font=T.FONT_LABEL_BOLD, text_color=T.TEKS_SEKUNDER).pack(anchor="w", padx=14, pady=(14, 8))

        self._frame_preview_area = ctk.CTkFrame(frame_prev, fg_color=T.BG_WIDGET, corner_radius=T.RADIUS_CARD, height=_PREVIEW_SIZE[1])
        self._frame_preview_area.pack(fill="x", padx=14, pady=(0, 14))
        self._frame_preview_area.pack_propagate(False)

        self._lbl_preview = ctk.CTkLabel(self._frame_preview_area, text="Belum ada\ncitra dipilih", font=T.FONT_KECIL, text_color=T.TEKS_DISABLED)
        self._lbl_preview.pack(expand=True)

        # Panel hasil pesan
        frame_hasil = ctk.CTkFrame(kolom, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        frame_hasil.pack(fill="both", expand=True)

        frame_judul_hasil = ctk.CTkFrame(frame_hasil, fg_color="transparent")
        frame_judul_hasil.pack(fill="x", padx=14, pady=(14, 8))

        ctk.CTkLabel(frame_judul_hasil, text="Pesan Hasil Ekstraksi", font=T.FONT_LABEL_BOLD, text_color=T.TEKS_SEKUNDER).pack(side="left")

        self._btn_salin = ctk.CTkButton(
            frame_judul_hasil,
            text="Salin",
            font=T.FONT_KECIL,
            height=26,
            width=60,
            corner_radius=6,
            fg_color=T.BTN_SEKUNDER_BG,
            text_color=T.TEKS_PRIMER,
            hover_color=T.BG_HOVER,
            command=self._salin_pesan,
            state="disabled",
        )
        self._btn_salin.pack(side="right")

        ctk.CTkFrame(frame_hasil, height=1, fg_color=T.BORDER_SUBTLE).pack(fill="x", padx=14)

        self._textbox_hasil = ctk.CTkTextbox(
            frame_hasil,
            font=T.FONT_LABEL,
            fg_color=T.BG_WIDGET,
            text_color=T.TEKS_PRIMER,
            border_width=0,
            state="disabled",
            wrap="word",
        )
        self._textbox_hasil.pack(fill="both", expand=True, padx=14, pady=14)

        # Label info panjang pesan
        self._lbl_info_pesan = ctk.CTkLabel(frame_hasil, text="", font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER)
        self._lbl_info_pesan.pack(anchor="e", padx=14, pady=(0, 10))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _buat_label_seksi(self, parent, teks: str) -> None:
        ctk.CTkLabel(parent, text=teks, font=("Segoe UI", 9, "bold"), text_color=T.TEKS_DISABLED).pack(anchor="w", pady=(8, 0))

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _pilih_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Pilih Citra Stego",
            filetypes=[("File PNG", "*.png"), ("Semua File", "*.*")],
        )
        if not path_str:
            return

        self._path_stego = Path(path_str)

        self._entry_path.configure(state="normal")
        self._entry_path.delete(0, "end")
        self._entry_path.insert(0, str(self._path_stego))
        self._entry_path.configure(state="disabled")

        # Reset area hasil
        self._textbox_hasil.configure(state="normal")
        self._textbox_hasil.delete("1.0", "end")
        self._textbox_hasil.configure(state="disabled")
        self._lbl_status.configure(text="")
        self._lbl_info_pesan.configure(text="")
        self._btn_salin.configure(state="disabled")

        # Load preview
        try:
            with Image.open(self._path_stego) as img:
                img.thumbnail(_PREVIEW_SIZE, Image.LANCZOS)
                self._ctk_img_prev = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self._lbl_preview.configure(image=self._ctk_img_prev, text="")
        except Exception as e:
            self._lbl_preview.configure(image=None, text=f"Gagal load\n{e}", text_color=T.AKSEN_DANGER)

    def _toggle_password(self) -> None:
        self._entry_kunci.configure(show="" if self._var_tampil_pass.get() else "●")

    def _jalankan_ekstraksi(self) -> None:
        if self._sedang_proses:
            return

        if self._path_stego is None:
            messagebox.showwarning("Input Tidak Lengkap", "Pilih file citra stego terlebih dahulu.")
            return

        kunci = self._entry_kunci.get().strip()
        if not kunci:
            messagebox.showwarning("Input Tidak Lengkap", "Masukkan kunci/password terlebih dahulu.")
            return

        self._set_loading(True)

        thread = threading.Thread(
            target=self._proses_ekstraksi_thread,
            args=(self._path_stego, kunci),
            daemon=True,
        )
        thread.start()

    def _proses_ekstraksi_thread(self, path_stego: Path, kunci: str) -> None:
        """Dijalankan di background thread."""
        try:
            pesan = extract_data(stego_path=path_stego, key=kunci)
            self.after(0, lambda p=pesan: self._on_ekstraksi_sukses(p))
        except UnicodeDecodeError:
            self.after(0, lambda: self._on_ekstraksi_gagal(
                "Gagal mendekode pesan.\nKemungkinan kunci yang digunakan salah,\natau file tidak mengandung pesan tersembunyi."
            ))
        except ValueError as e:
            self.after(0, lambda msg=str(e): self._on_ekstraksi_gagal(msg))
        except Exception as e:
            logger.error(f"Error tidak terduga saat ekstraksi: {e}", exc_info=True)
            self.after(0, lambda msg=str(e): self._on_ekstraksi_gagal(f"Error: {msg}"))

    def _on_ekstraksi_sukses(self, pesan: str) -> None:
        self._set_loading(False)

        self._textbox_hasil.configure(state="normal")
        self._textbox_hasil.delete("1.0", "end")
        self._textbox_hasil.insert("1.0", pesan)
        self._textbox_hasil.configure(state="disabled")

        n_char = len(pesan)
        n_byte = len(pesan.encode("utf-8"))
        self._lbl_info_pesan.configure(text=f"{n_char} karakter  •  {n_byte} byte")
        self._lbl_status.configure(text="✓  Ekstraksi berhasil!", text_color=T.AKSEN_SUKSES)
        self._btn_salin.configure(state="normal")

    def _on_ekstraksi_gagal(self, pesan_error: str) -> None:
        self._set_loading(False)
        self._lbl_status.configure(text=f"✕  Gagal", text_color=T.AKSEN_DANGER)
        messagebox.showerror("Ekstraksi Gagal", pesan_error)

    def _salin_pesan(self) -> None:
        """Menyalin isi textbox hasil ke clipboard sistem."""
        pesan = self._textbox_hasil.get("1.0", "end-1c")
        if pesan:
            self.clipboard_clear()
            self.clipboard_append(pesan)
            self._btn_salin.configure(text="✓ Disalin!")
            self.after(2000, lambda: self._btn_salin.configure(text="Salin"))

    def _set_loading(self, aktif: bool) -> None:
        self._sedang_proses = aktif
        if aktif:
            self._btn_ekstrak.configure(text="  ⏳  Mengekstrak...", state="disabled", fg_color=T.TEKS_DISABLED)
            self._progress.pack(fill="x", pady=(4, 2))
            self._progress.start()
            self._lbl_status.configure(text="Sedang membaca bit dari citra...", text_color=T.TEKS_SEKUNDER)
        else:
            self._btn_ekstrak.configure(text="  ▶  Ekstrak Pesan", state="normal", fg_color=T.AKSEN_SEKUNDER)
            self._progress.stop()
            self._progress.pack_forget()

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass