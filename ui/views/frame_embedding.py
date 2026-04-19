import logging
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from database.db_manager import DatabaseManager, HistoryRecord
from engine.evaluasi_metrik import hitung_semua_metrik
from engine.stego_lsb import embed_data, cek_kapasitas
from ui import theme as T

logger = logging.getLogger(__name__)
_PREVIEW_SIZE = (220, 220)


class FrameEmbedding(ctk.CTkFrame):

    def __init__(self, parent: ctk.CTkFrame, controller) -> None:
        super().__init__(parent, fg_color=T.BG_APP, corner_radius=0)
        self.controller = controller

        self._path_cover: Path | None = None
        self._ctk_img_prev: ctk.CTkImage | None = None
        self._sedang_proses = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._bangun_ui()

    # ── UI Builder ────────────────────────────────────────────────────────────

    def _bangun_ui(self) -> None:
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))
        ctk.CTkLabel(frame_header, text="Embedding", font=T.FONT_JUDUL, text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(frame_header, text="Sisipkan pesan rahasia ke dalam citra digital",
                     font=T.FONT_LABEL, text_color=T.TEKS_SEKUNDER).pack(anchor="w", pady=(2, 0))
        ctk.CTkFrame(frame_header, height=2, fg_color=T.AKSEN_PRIMER, corner_radius=1).pack(fill="x", pady=(12, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._bangun_kolom_form(body)
        self._bangun_kolom_preview(body)

    def _bangun_kolom_form(self, parent: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=T.BORDER_NORMAL)
        scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # ── Seksi 1: Pilih Citra Cover ────────────────────────────────────────
        self._seksi(scroll, "1  PILIH CITRA COVER")
        f_file = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_file.pack(fill="x", pady=(4, 12))

        self._entry_path = ctk.CTkEntry(
            f_file, placeholder_text="Belum ada file dipilih...",
            font=T.FONT_MONO_KECIL, fg_color=T.BG_WIDGET, border_color=T.BORDER_NORMAL,
            text_color=T.TEKS_PRIMER, state="disabled", height=36, corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_path.pack(fill="x", padx=12, pady=(12, 6))

        f_btn_file = ctk.CTkFrame(f_file, fg_color="transparent")
        f_btn_file.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(f_btn_file, text="  Pilih File Citra", font=T.FONT_LABEL, height=34,
                      corner_radius=T.RADIUS_BTN, fg_color=T.BTN_SEKUNDER_BG, text_color=T.TEKS_PRIMER,
                      hover_color=T.BG_HOVER, command=self._pilih_file_citra).pack(side="left", padx=(0, 6))
        self._lbl_kapasitas = ctk.CTkLabel(f_btn_file, text="", font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER)
        self._lbl_kapasitas.pack(side="left", padx=6)

        # ── Seksi 2: Pesan ────────────────────────────────────────────────────
        self._seksi(scroll, "2  PESAN RAHASIA")
        f_pesan = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_pesan.pack(fill="x", pady=(4, 12))

        # Toolbar: judul + tombol muat .TXT
        f_toolbar = ctk.CTkFrame(f_pesan, fg_color="transparent")
        f_toolbar.pack(fill="x", padx=12, pady=(10, 0))

        ctk.CTkLabel(f_toolbar, text="Teks Pesan:", font=T.FONT_LABEL_BOLD,
                     text_color=T.TEKS_SEKUNDER).pack(side="left")

        ctk.CTkButton(
            f_toolbar,
            text="  📄  Muat dari File .TXT",
            font=T.FONT_KECIL,
            height=28, width=160,
            corner_radius=6,
            fg_color=T.BG_WIDGET,
            text_color=T.AKSEN_SEKUNDER,
            hover_color=T.BG_HOVER,
            border_width=1,
            border_color=T.AKSEN_SEKUNDER,
            command=self._muat_dari_txt,
        ).pack(side="right")

        self._textbox_pesan = ctk.CTkTextbox(
            f_pesan, height=110, font=T.FONT_LABEL,
            fg_color=T.BG_WIDGET, border_color=T.BORDER_NORMAL, border_width=1,
            text_color=T.TEKS_PRIMER, corner_radius=T.RADIUS_ENTRY, wrap="word",
        )
        self._textbox_pesan.pack(fill="x", padx=12, pady=6)
        self._textbox_pesan.bind("<KeyRelease>", self._update_counter)

        f_bottom_pesan = ctk.CTkFrame(f_pesan, fg_color="transparent")
        f_bottom_pesan.pack(fill="x", padx=12, pady=(0, 10))

        # Label sumber (dari file atau diketik)
        self._lbl_sumber = ctk.CTkLabel(
            f_bottom_pesan, text="",
            font=T.FONT_KECIL, text_color=T.TEKS_DISABLED,
        )
        self._lbl_sumber.pack(side="left")

        self._lbl_counter = ctk.CTkLabel(f_bottom_pesan, text="0 karakter",
                                          font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER)
        self._lbl_counter.pack(side="right")

        # ── Seksi 3: Kunci ────────────────────────────────────────────────────
        self._seksi(scroll, "3  KUNCI / PASSWORD (SEED MWC)")
        f_kunci = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_kunci.pack(fill="x", pady=(4, 12))

        self._entry_kunci = ctk.CTkEntry(
            f_kunci, placeholder_text="Masukkan password rahasia (seed MWC)...",
            show="●", font=T.FONT_LABEL, fg_color=T.BG_WIDGET, border_color=T.BORDER_NORMAL,
            text_color=T.TEKS_PRIMER, height=38, corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_kunci.pack(fill="x", padx=12, pady=(12, 6))

        self._var_tampil = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f_kunci, text="Tampilkan password", font=T.FONT_KECIL,
                        text_color=T.TEKS_SEKUNDER, fg_color=T.AKSEN_PRIMER,
                        border_color=T.BORDER_NORMAL, hover_color=T.BTN_HOVER,
                        variable=self._var_tampil, command=self._toggle_pass).pack(anchor="w", padx=12, pady=(0, 12))

        # ── Tombol Proses ─────────────────────────────────────────────────────
        self._btn_proses = ctk.CTkButton(
            scroll, text="  ▶  Proses Embedding",
            font=("Segoe UI", 13, "bold"), height=46, corner_radius=T.RADIUS_BTN,
            fg_color=T.AKSEN_PRIMER, text_color=T.BG_APP, hover_color=T.BTN_HOVER,
            command=self._jalankan,
        )
        self._btn_proses.pack(fill="x", pady=(4, 8))

        self._progress = ctk.CTkProgressBar(scroll, fg_color=T.BG_WIDGET,
                                             progress_color=T.AKSEN_PRIMER, height=4, corner_radius=2)
        self._progress.set(0)

        self._lbl_status = ctk.CTkLabel(scroll, text="", font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER)
        self._lbl_status.pack(anchor="w")

    def _bangun_kolom_preview(self, parent: ctk.CTkFrame) -> None:
        kolom = ctk.CTkFrame(parent, fg_color="transparent")
        kolom.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        f_prev = ctk.CTkFrame(kolom, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_prev.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(f_prev, text="Preview Citra Cover", font=T.FONT_LABEL_BOLD,
                     text_color=T.TEKS_SEKUNDER).pack(anchor="w", padx=14, pady=(14, 8))

        self._frame_prev_area = ctk.CTkFrame(f_prev, fg_color=T.BG_WIDGET,
                                              corner_radius=T.RADIUS_CARD, height=_PREVIEW_SIZE[1])
        self._frame_prev_area.pack(fill="x", padx=14, pady=(0, 8))
        self._frame_prev_area.pack_propagate(False)

        self._lbl_preview = ctk.CTkLabel(self._frame_prev_area, text="Belum ada\ncitra dipilih",
                                          font=T.FONT_KECIL, text_color=T.TEKS_DISABLED)
        self._lbl_preview.pack(expand=True)

        self._lbl_info_citra = ctk.CTkLabel(f_prev, text="", font=T.FONT_MONO_KECIL,
                                             text_color=T.TEKS_SEKUNDER)
        self._lbl_info_citra.pack(padx=14, pady=(0, 14))

        # Panel hasil
        self._f_hasil = ctk.CTkFrame(kolom, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        self._f_hasil.pack(fill="x")
        ctk.CTkLabel(self._f_hasil, text="Hasil Embedding", font=T.FONT_LABEL_BOLD,
                     text_color=T.TEKS_SEKUNDER).pack(anchor="w", padx=14, pady=(14, 8))
        ctk.CTkFrame(self._f_hasil, height=1, fg_color=T.BORDER_SUBTLE).pack(fill="x", padx=14)

        self._lbl_hasil_ph = ctk.CTkLabel(self._f_hasil, text="Hasil akan muncul\nsetelah proses selesai",
                                           font=T.FONT_KECIL, text_color=T.TEKS_DISABLED)
        self._lbl_hasil_ph.pack(pady=20)

        self._f_hasil_detail = ctk.CTkFrame(self._f_hasil, fg_color="transparent")
        self._rows_hasil: dict[str, ctk.CTkLabel] = {}
        for key, label in [("path", "File Stego"), ("psnr", "PSNR"), ("mse", "MSE"), ("kapasitas", "Kapasitas Terpakai")]:
            self._rows_hasil[key] = self._buat_baris_hasil(self._f_hasil_detail, label)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _seksi(self, parent, teks: str) -> None:
        ctk.CTkLabel(parent, text=teks, font=("Segoe UI", 9, "bold"),
                     text_color=T.TEKS_DISABLED).pack(anchor="w", pady=(8, 0))

    def _buat_baris_hasil(self, parent: ctk.CTkFrame, label: str) -> ctk.CTkLabel:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3, padx=14)
        ctk.CTkLabel(row, text=f"{label}:", font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER,
                     width=120, anchor="w").pack(side="left")
        lbl = ctk.CTkLabel(row, text="—", font=T.FONT_MONO_KECIL, text_color=T.TEKS_PRIMER, anchor="w")
        lbl.pack(side="left", fill="x", expand=True)
        return lbl

    def _set_entry(self, entry: ctk.CTkEntry, nilai: str) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, nilai)
        entry.configure(state="disabled")

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _pilih_file_citra(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Pilih Citra Cover",
            filetypes=[("File Gambar", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("Semua", "*.*")],
        )
        if not path_str:
            return
        self._path_cover = Path(path_str)
        self._set_entry(self._entry_path, str(self._path_cover))

        # Preview
        try:
            with Image.open(self._path_cover) as img:
                img.thumbnail(_PREVIEW_SIZE, Image.LANCZOS)
                self._ctk_img_prev = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self._lbl_preview.configure(image=self._ctk_img_prev, text="")
        except Exception as e:
            self._lbl_preview.configure(image=None, text=f"Gagal\n{e}", text_color=T.AKSEN_DANGER)

        # Info kapasitas
        try:
            info = cek_kapasitas(self._path_cover)
            self._lbl_kapasitas.configure(
                text=f"{info['lebar']}×{info['tinggi']} px  |  Maks. {info['kapasitas_byte']:,} byte",
                text_color=T.TEKS_SEKUNDER,
            )
            self._lbl_info_citra.configure(
                text=f"{info['lebar']} × {info['tinggi']} piksel\n{info['total_piksel']:,} piksel total"
            )
        except Exception as e:
            self._lbl_kapasitas.configure(text=f"Error: {e}", text_color=T.AKSEN_DANGER)

    def _muat_dari_txt(self) -> None:
        
        path_str = filedialog.askopenfilename(
            title="Pilih File Teks (.txt)",
            filetypes=[("File Teks", "*.txt"), ("Semua File", "*.*")],
        )
        if not path_str:
            return

        path_txt = Path(path_str)
        try:
            # Coba UTF-8 dulu, fallback ke Latin-1
            try:
                konten = path_txt.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                konten = path_txt.read_text(encoding="latin-1")

            if not konten.strip():
                messagebox.showwarning("File Kosong", f"File '{path_txt.name}' tidak berisi teks.")
                return

            # Masukkan ke textbox
            self._textbox_pesan.delete("1.0", "end")
            self._textbox_pesan.insert("1.0", konten)
            self._update_counter()

            # Tampilkan label sumber
            n_byte = len(konten.encode("utf-8"))
            self._lbl_sumber.configure(
                text=f"📄 Dimuat dari: {path_txt.name} ({n_byte:,} byte)",
                text_color=T.AKSEN_SEKUNDER,
            )
            logger.info(f"Pesan dimuat dari file: '{path_txt}' ({n_byte} byte)")

        except PermissionError:
            messagebox.showerror("Tidak Ada Izin", f"Tidak bisa membaca file:\n{path_txt}")
        except Exception as e:
            messagebox.showerror("Gagal Memuat File", f"Error:\n{e}")

    def _update_counter(self, event=None) -> None:
        teks = self._textbox_pesan.get("1.0", "end-1c")
        n = len(teks)
        n_byte = len(teks.encode("utf-8"))
        self._lbl_counter.configure(
            text=f"{n} karakter  ({n_byte:,} byte)",
            text_color=T.AKSEN_WARNING if n > 500 else T.TEKS_SEKUNDER,
        )

    def _toggle_pass(self) -> None:
        self._entry_kunci.configure(show="" if self._var_tampil.get() else "●")

    def _jalankan(self) -> None:
        if self._sedang_proses:
            return
        if self._path_cover is None:
            messagebox.showwarning("Input Kurang", "Pilih citra cover terlebih dahulu.")
            return
        pesan = self._textbox_pesan.get("1.0", "end-1c").strip()
        if not pesan:
            messagebox.showwarning("Input Kurang", "Pesan tidak boleh kosong.")
            return
        kunci = self._entry_kunci.get().strip()
        if not kunci:
            messagebox.showwarning("Input Kurang", "Kunci/password tidak boleh kosong.")
            return

        self._set_loading(True)
        threading.Thread(
            target=self._thread_embed,
            args=(self._path_cover, pesan, kunci),
            daemon=True,
        ).start()

    def _thread_embed(self, path_cover: Path, pesan: str, kunci: str) -> None:
        try:
            hasil  = embed_data(cover_path=path_cover, message=pesan, key=kunci)
            metrik = hitung_semua_metrik(str(path_cover), str(hasil.path_stego))
            record = HistoryRecord(
                nama_file=path_cover.name,
                ukuran_pesan=len(pesan.encode("utf-8")),
                kunci_seed=kunci,
                nilai_psnr=metrik["psnr"],
                nilai_mse=metrik["mse"],
            )
            self.controller.db.simpan_riwayat(record)
            self.after(0, lambda: self._on_sukses(hasil, metrik))
        except ValueError as e:
            self.after(0, lambda msg=str(e): self._on_gagal(msg))
        except Exception as e:
            logger.error(f"Error embedding: {e}", exc_info=True)
            self.after(0, lambda msg=str(e): self._on_gagal(f"Error tidak terduga: {msg}"))

    def _on_sukses(self, hasil, metrik: dict) -> None:
        self._set_loading(False)
        self._lbl_hasil_ph.pack_forget()
        self._f_hasil_detail.pack(fill="x", pady=(8, 14))
        self._rows_hasil["path"].configure(text=hasil.path_stego.name, text_color=T.AKSEN_SUKSES)
        self._rows_hasil["psnr"].configure(text=f"{metrik['psnr']:.4f} dB", text_color=T.AKSEN_PRIMER)
        self._rows_hasil["mse"].configure(text=f"{metrik['mse']:.6f}", text_color=T.TEKS_PRIMER)
        self._rows_hasil["kapasitas"].configure(text=f"{hasil.persentase_pakai:.2f}% kapasitas")
        self._lbl_status.configure(text="✓  Embedding berhasil! Data tersimpan ke riwayat.", text_color=T.AKSEN_SUKSES)
        messagebox.showinfo("Berhasil!", f"Embedding selesai.\n\nFile: {hasil.path_stego.name}\nPSNR: {metrik['psnr']:.4f} dB\nMSE:  {metrik['mse']:.6f}")

    def _on_gagal(self, msg: str) -> None:
        self._set_loading(False)
        self._lbl_status.configure(text=f"✕  {msg[:80]}", text_color=T.AKSEN_DANGER)
        messagebox.showerror("Embedding Gagal", msg)

    def _set_loading(self, aktif: bool) -> None:
        self._sedang_proses = aktif
        if aktif:
            self._btn_proses.configure(text="  ⏳  Memproses...", state="disabled", fg_color=T.TEKS_DISABLED)
            self._progress.pack(fill="x", pady=(4, 2))
            self._progress.start()
            self._lbl_status.configure(text="Sedang menyisipkan pesan...", text_color=T.TEKS_SEKUNDER)
        else:
            self._btn_proses.configure(text="  ▶  Proses Embedding", state="normal", fg_color=T.AKSEN_PRIMER)
            self._progress.stop()
            self._progress.pack_forget()

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass