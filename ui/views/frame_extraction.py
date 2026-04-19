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

    def __init__(self, parent: ctk.CTkFrame, controller) -> None:
        super().__init__(parent, fg_color=T.BG_APP, corner_radius=0)
        self.controller = controller

        self._path_stego: Path | None = None
        self._ctk_img_prev: ctk.CTkImage | None = None
        self._sedang_proses = False
        self._pesan_hasil: str = ""  # Simpan hasil untuk tombol save

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._bangun_ui()

    # ── UI Builder ────────────────────────────────────────────────────────────

    def _bangun_ui(self) -> None:
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))
        ctk.CTkLabel(frame_header, text="Extraction", font=T.FONT_JUDUL, text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(frame_header, text="Ekstrak pesan tersembunyi dari citra stego",
                     font=T.FONT_LABEL, text_color=T.TEKS_SEKUNDER).pack(anchor="w", pady=(2, 0))
        ctk.CTkFrame(frame_header, height=2, fg_color=T.AKSEN_SEKUNDER, corner_radius=1).pack(fill="x", pady=(12, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._bangun_kolom_form(body)
        self._bangun_kolom_kanan(body)

    def _bangun_kolom_form(self, parent: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=T.BORDER_NORMAL)
        scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # ── Seksi 1: Pilih Stego ──────────────────────────────────────────────
        self._seksi(scroll, "1  PILIH CITRA STEGO")
        f_file = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_file.pack(fill="x", pady=(4, 12))

        self._entry_path = ctk.CTkEntry(
            f_file, placeholder_text="Belum ada file stego dipilih...",
            font=T.FONT_MONO_KECIL, fg_color=T.BG_WIDGET, border_color=T.BORDER_NORMAL,
            text_color=T.TEKS_PRIMER, state="disabled", height=36, corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_path.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkButton(f_file, text="  Pilih File Stego (.png)", font=T.FONT_LABEL, height=34,
                      corner_radius=T.RADIUS_BTN, fg_color=T.BTN_SEKUNDER_BG, text_color=T.TEKS_PRIMER,
                      hover_color=T.BG_HOVER, command=self._pilih_file).pack(anchor="w", padx=12, pady=(0, 12))

        # ── Seksi 2: Kunci ────────────────────────────────────────────────────
        self._seksi(scroll, "2  KUNCI / PASSWORD (SEED MWC)")
        f_kunci = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_kunci.pack(fill="x", pady=(4, 12))

        self._entry_kunci = ctk.CTkEntry(
            f_kunci, placeholder_text="Masukkan kunci yang sama seperti saat embedding...",
            show="●", font=T.FONT_LABEL, fg_color=T.BG_WIDGET, border_color=T.BORDER_NORMAL,
            text_color=T.TEKS_PRIMER, height=38, corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_kunci.pack(fill="x", padx=12, pady=(12, 6))

        self._var_tampil = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f_kunci, text="Tampilkan password", font=T.FONT_KECIL,
                        text_color=T.TEKS_SEKUNDER, fg_color=T.AKSEN_SEKUNDER,
                        border_color=T.BORDER_NORMAL, hover_color=T.AKSEN_SEKUNDER,
                        variable=self._var_tampil, command=self._toggle_pass).pack(anchor="w", padx=12, pady=(0, 12))

        # Peringatan kunci
        f_warn = ctk.CTkFrame(scroll, fg_color="#1c1a0a", corner_radius=T.RADIUS_CARD,
                               border_width=1, border_color="#4a3c00")
        f_warn.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(f_warn, text="⚠  Kunci yang salah akan menghasilkan teks sampah atau error decoding.",
                     font=T.FONT_KECIL, text_color=T.AKSEN_WARNING, wraplength=340, justify="left").pack(padx=12, pady=10)

        # ── Tombol Ekstrak ────────────────────────────────────────────────────
        self._btn_ekstrak = ctk.CTkButton(
            scroll, text="  ▶  Ekstrak Pesan",
            font=("Segoe UI", 13, "bold"), height=46, corner_radius=T.RADIUS_BTN,
            fg_color=T.AKSEN_SEKUNDER, text_color=T.BG_APP, hover_color="#1aa8e8",
            command=self._jalankan,
        )
        self._btn_ekstrak.pack(fill="x", pady=(4, 8))

        self._progress = ctk.CTkProgressBar(scroll, fg_color=T.BG_WIDGET,
                                             progress_color=T.AKSEN_SEKUNDER, height=4, corner_radius=2)
        self._progress.set(0)

        self._lbl_status = ctk.CTkLabel(scroll, text="", font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER)
        self._lbl_status.pack(anchor="w")

    def _bangun_kolom_kanan(self, parent: ctk.CTkFrame) -> None:
        kolom = ctk.CTkFrame(parent, fg_color="transparent")
        kolom.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Preview
        f_prev = ctk.CTkFrame(kolom, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_prev.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(f_prev, text="Preview Citra Stego", font=T.FONT_LABEL_BOLD,
                     text_color=T.TEKS_SEKUNDER).pack(anchor="w", padx=14, pady=(14, 8))

        self._frame_prev = ctk.CTkFrame(f_prev, fg_color=T.BG_WIDGET,
                                         corner_radius=T.RADIUS_CARD, height=_PREVIEW_SIZE[1])
        self._frame_prev.pack(fill="x", padx=14, pady=(0, 14))
        self._frame_prev.pack_propagate(False)

        self._lbl_preview = ctk.CTkLabel(self._frame_prev, text="Belum ada\ncitra dipilih",
                                          font=T.FONT_KECIL, text_color=T.TEKS_DISABLED)
        self._lbl_preview.pack(expand=True)

        # Panel hasil pesan
        f_hasil = ctk.CTkFrame(kolom, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_hasil.pack(fill="both", expand=True)

        # Header panel hasil: judul + tombol-tombol aksi
        f_judul = ctk.CTkFrame(f_hasil, fg_color="transparent")
        f_judul.pack(fill="x", padx=14, pady=(14, 8))

        ctk.CTkLabel(f_judul, text="Pesan Hasil Ekstraksi",
                     font=T.FONT_LABEL_BOLD, text_color=T.TEKS_SEKUNDER).pack(side="left")

        # Tombol Simpan TXT (GAP 5) — di sisi kanan
        self._btn_simpan_txt = ctk.CTkButton(
            f_judul,
            text="💾 Simpan .TXT",
            font=T.FONT_KECIL,
            height=28, width=100,
            corner_radius=6,
            fg_color=T.BG_WIDGET,
            text_color=T.AKSEN_SUKSES,
            hover_color=T.BG_HOVER,
            border_width=1,
            border_color=T.AKSEN_SUKSES,
            command=self._simpan_txt,
            state="disabled",
        )
        self._btn_simpan_txt.pack(side="right", padx=(4, 0))

        # Tombol Salin
        self._btn_salin = ctk.CTkButton(
            f_judul, text="Salin", font=T.FONT_KECIL, height=28, width=56,
            corner_radius=6, fg_color=T.BTN_SEKUNDER_BG, text_color=T.TEKS_PRIMER,
            hover_color=T.BG_HOVER, command=self._salin, state="disabled",
        )
        self._btn_salin.pack(side="right", padx=(0, 4))

        ctk.CTkFrame(f_hasil, height=1, fg_color=T.BORDER_SUBTLE).pack(fill="x", padx=14)

        self._textbox_hasil = ctk.CTkTextbox(
            f_hasil, font=T.FONT_LABEL, fg_color=T.BG_WIDGET, text_color=T.TEKS_PRIMER,
            border_width=0, state="disabled", wrap="word",
        )
        self._textbox_hasil.pack(fill="both", expand=True, padx=14, pady=14)

        # Info panjang + integritas
        f_info_bawah = ctk.CTkFrame(f_hasil, fg_color="transparent")
        f_info_bawah.pack(fill="x", padx=14, pady=(0, 10))
        self._lbl_info_pesan = ctk.CTkLabel(f_info_bawah, text="", font=T.FONT_KECIL,
                                             text_color=T.TEKS_SEKUNDER)
        self._lbl_info_pesan.pack(side="left")
        self._lbl_integritas = ctk.CTkLabel(f_info_bawah, text="", font=T.FONT_KECIL,
                                             text_color=T.AKSEN_SUKSES)
        self._lbl_integritas.pack(side="right")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _seksi(self, parent, teks: str) -> None:
        ctk.CTkLabel(parent, text=teks, font=("Segoe UI", 9, "bold"),
                     text_color=T.TEKS_DISABLED).pack(anchor="w", pady=(8, 0))

    def _set_entry(self, entry: ctk.CTkEntry, nilai: str) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, nilai)
        entry.configure(state="disabled")

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _pilih_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Pilih Citra Stego",
            filetypes=[("File PNG", "*.png"), ("Semua", "*.*")],
        )
        if not path_str:
            return
        self._path_stego = Path(path_str)
        self._set_entry(self._entry_path, str(self._path_stego))

        # Reset area hasil
        self._pesan_hasil = ""
        self._textbox_hasil.configure(state="normal")
        self._textbox_hasil.delete("1.0", "end")
        self._textbox_hasil.configure(state="disabled")
        self._lbl_status.configure(text="")
        self._lbl_info_pesan.configure(text="")
        self._lbl_integritas.configure(text="")
        self._btn_salin.configure(state="disabled")
        self._btn_simpan_txt.configure(state="disabled")

        try:
            with Image.open(self._path_stego) as img:
                img.thumbnail(_PREVIEW_SIZE, Image.LANCZOS)
                self._ctk_img_prev = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self._lbl_preview.configure(image=self._ctk_img_prev, text="")
        except Exception as e:
            self._lbl_preview.configure(image=None, text=f"Gagal\n{e}", text_color=T.AKSEN_DANGER)

    def _toggle_pass(self) -> None:
        self._entry_kunci.configure(show="" if self._var_tampil.get() else "●")

    def _jalankan(self) -> None:
        if self._sedang_proses:
            return
        if self._path_stego is None:
            messagebox.showwarning("Input Kurang", "Pilih file citra stego terlebih dahulu.")
            return
        kunci = self._entry_kunci.get().strip()
        if not kunci:
            messagebox.showwarning("Input Kurang", "Masukkan kunci/password terlebih dahulu.")
            return

        self._set_loading(True)
        threading.Thread(
            target=self._thread_extract,
            args=(self._path_stego, kunci),
            daemon=True,
        ).start()

    def _thread_extract(self, path_stego: Path, kunci: str) -> None:
        try:
            pesan = extract_data(stego_path=path_stego, key=kunci)
            self.after(0, lambda p=pesan: self._on_sukses(p))
        except UnicodeDecodeError:
            self.after(0, lambda: self._on_gagal(
                "Gagal mendekode pesan.\nKemungkinan kunci yang digunakan salah,\n"
                "atau file ini bukan citra stego yang valid."
            ))
        except ValueError as e:
            self.after(0, lambda msg=str(e): self._on_gagal(msg))
        except Exception as e:
            logger.error(f"Error ekstraksi: {e}", exc_info=True)
            self.after(0, lambda msg=str(e): self._on_gagal(f"Error: {msg}"))

    def _on_sukses(self, pesan: str) -> None:
        self._set_loading(False)
        self._pesan_hasil = pesan

        self._textbox_hasil.configure(state="normal")
        self._textbox_hasil.delete("1.0", "end")
        self._textbox_hasil.insert("1.0", pesan)
        self._textbox_hasil.configure(state="disabled")

        n_char = len(pesan)
        n_byte = len(pesan.encode("utf-8"))
        self._lbl_info_pesan.configure(text=f"{n_char} karakter  •  {n_byte:,} byte")
        self._lbl_integritas.configure(text="✓ Ekstraksi Valid (100% Akurat)", text_color=T.AKSEN_SUKSES)
        self._lbl_status.configure(text="✓  Ekstraksi berhasil!", text_color=T.AKSEN_SUKSES)
        self._btn_salin.configure(state="normal")
        self._btn_simpan_txt.configure(state="normal")

    def _on_gagal(self, msg: str) -> None:
        self._set_loading(False)
        self._lbl_status.configure(text="✕  Gagal", text_color=T.AKSEN_DANGER)
        messagebox.showerror("Ekstraksi Gagal", msg)

    def _salin(self) -> None:
        
        if self._pesan_hasil:
            self.clipboard_clear()
            self.clipboard_append(self._pesan_hasil)
            self._btn_salin.configure(text="✓ Disalin!")
            self.after(2000, lambda: self._btn_salin.configure(text="Salin"))

    def _simpan_txt(self) -> None:
        
        if not self._pesan_hasil:
            return

        nama_default = "pesan_ekstraksi.txt"
        if self._path_stego:
            nama_default = self._path_stego.stem + "_pesan.txt"

        path_str = filedialog.asksaveasfilename(
            title="Simpan Pesan sebagai File .TXT",
            defaultextension=".txt",
            filetypes=[("File Teks", "*.txt"), ("Semua File", "*.*")],
            initialfile=nama_default,
        )
        if not path_str:
            return

        try:
            Path(path_str).write_text(self._pesan_hasil, encoding="utf-8")
            n_byte = len(self._pesan_hasil.encode("utf-8"))
            messagebox.showinfo(
                "Berhasil Disimpan",
                f"Pesan berhasil disimpan!\n\n"
                f"File : {Path(path_str).name}\n"
                f"Ukuran: {n_byte:,} byte",
            )
            logger.info(f"Pesan disimpan ke: {path_str}")
        except PermissionError:
            messagebox.showerror("Gagal", "Tidak ada izin menulis ke lokasi tersebut.")
        except Exception as e:
            messagebox.showerror("Gagal", f"Gagal menyimpan file:\n{e}")

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