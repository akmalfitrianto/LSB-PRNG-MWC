"""
================================================================================
MODULE  : ui/views/frame_embedding.py
DESKRIPSI:
    Halaman Embedding — tempat pengguna melakukan penyisipan pesan ke citra.

    ALUR UX:
      1. Pengguna memilih file citra cover (PNG/JPG) → tampil preview & info.
      2. Pengguna mengetik pesan dan password di form.
      3. Klik tombol "Proses Embedding" → jalankan embed_data() di background thread.
      4. Setelah selesai → tampilkan hasil: path stego, PSNR, MSE, kapasitas.
      5. Data otomatis tersimpan ke database riwayat.

    PENTING — Threading:
    Operasi embedding dijalankan di thread terpisah (threading.Thread) agar
    UI tidak freeze selama proses berlangsung. Hasil dikembalikan ke UI thread
    menggunakan self.after() (cara aman untuk update widget dari thread lain).
================================================================================
"""

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

# Ukuran thumbnail preview citra
_PREVIEW_SIZE = (220, 220)


class FrameEmbedding(ctk.CTkFrame):
    """
    Frame halaman Embedding.

    Attributes:
        _path_cover    (Path | None)     : Path file citra cover yang dipilih.
        _ctk_img_prev  (CTkImage | None) : Objek gambar untuk preview (harus disimpan
                                           sebagai atribut agar tidak di-garbage collect).
    """

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
        # ── Header ────────────────────────────────────────────────────────────
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))

        ctk.CTkLabel(
            frame_header,
            text="Embedding",
            font=T.FONT_JUDUL,
            text_color=T.TEKS_PRIMER,
        ).pack(anchor="w")
        ctk.CTkLabel(
            frame_header,
            text="Sisipkan pesan rahasia ke dalam citra digital",
            font=T.FONT_LABEL,
            text_color=T.TEKS_SEKUNDER,
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkFrame(frame_header, height=2, fg_color=T.AKSEN_PRIMER, corner_radius=1).pack(fill="x", pady=(12, 0))

        # ── Body (2 kolom: kiri=form, kanan=preview+hasil) ────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._bangun_kolom_form(body)
        self._bangun_kolom_preview(body)

    def _bangun_kolom_form(self, parent: ctk.CTkFrame) -> None:
        """Kolom kiri: form input (pilih file, pesan, kunci, tombol proses)."""
        scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent",
            scrollbar_button_color=T.BORDER_NORMAL,
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # ── Seksi 1: Pilih Citra Cover ────────────────────────────────────────
        self._buat_label_seksi(scroll, "1  PILIH CITRA COVER")

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

        frame_btn_file = ctk.CTkFrame(frame_file, fg_color="transparent")
        frame_btn_file.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkButton(
            frame_btn_file,
            text="  Pilih File Citra",
            font=T.FONT_LABEL,
            height=34,
            corner_radius=T.RADIUS_BTN,
            fg_color=T.BTN_SEKUNDER_BG,
            text_color=T.TEKS_PRIMER,
            hover_color=T.BG_HOVER,
            command=self._pilih_file,
        ).pack(side="left", padx=(0, 6))

        # Label info kapasitas
        self._lbl_kapasitas = ctk.CTkLabel(
            frame_btn_file,
            text="",
            font=T.FONT_KECIL,
            text_color=T.TEKS_SEKUNDER,
        )
        self._lbl_kapasitas.pack(side="left", padx=6)

        # ── Seksi 2: Pesan ────────────────────────────────────────────────────
        self._buat_label_seksi(scroll, "2  PESAN RAHASIA")

        frame_pesan = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        frame_pesan.pack(fill="x", pady=(4, 12))

        self._textbox_pesan = ctk.CTkTextbox(
            frame_pesan,
            height=100,
            font=T.FONT_LABEL,
            fg_color=T.BG_WIDGET,
            border_color=T.BORDER_NORMAL,
            border_width=1,
            text_color=T.TEKS_PRIMER,
            corner_radius=T.RADIUS_ENTRY,
            wrap="word",
        )
        self._textbox_pesan.pack(fill="x", padx=12, pady=12)
        self._textbox_pesan.bind("<KeyRelease>", self._update_hitung_karakter)

        # Counter karakter
        frame_counter = ctk.CTkFrame(frame_pesan, fg_color="transparent")
        frame_counter.pack(fill="x", padx=12, pady=(0, 12))
        self._lbl_counter = ctk.CTkLabel(
            frame_counter,
            text="0 karakter",
            font=T.FONT_KECIL,
            text_color=T.TEKS_SEKUNDER,
        )
        self._lbl_counter.pack(side="right")

        # ── Seksi 3: Kunci ────────────────────────────────────────────────────
        self._buat_label_seksi(scroll, "3  KUNCI / PASSWORD")

        frame_kunci = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        frame_kunci.pack(fill="x", pady=(4, 12))

        self._entry_kunci = ctk.CTkEntry(
            frame_kunci,
            placeholder_text="Masukkan password rahasia...",
            show="●",
            font=T.FONT_LABEL,
            fg_color=T.BG_WIDGET,
            border_color=T.BORDER_NORMAL,
            text_color=T.TEKS_PRIMER,
            height=38,
            corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_kunci.pack(fill="x", padx=12, pady=(12, 6))

        # Checkbox tampilkan password
        self._var_tampil_pass = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame_kunci,
            text="Tampilkan password",
            font=T.FONT_KECIL,
            text_color=T.TEKS_SEKUNDER,
            fg_color=T.AKSEN_PRIMER,
            border_color=T.BORDER_NORMAL,
            hover_color=T.BTN_HOVER,
            variable=self._var_tampil_pass,
            command=self._toggle_password,
        ).pack(anchor="w", padx=12, pady=(0, 12))

        # ── Tombol Proses ─────────────────────────────────────────────────────
        self._btn_proses = ctk.CTkButton(
            scroll,
            text="  ▶  Proses Embedding",
            font=("Segoe UI", 13, "bold"),
            height=46,
            corner_radius=T.RADIUS_BTN,
            fg_color=T.AKSEN_PRIMER,
            text_color=T.BG_APP,
            hover_color=T.BTN_HOVER,
            command=self._jalankan_embedding,
        )
        self._btn_proses.pack(fill="x", pady=(4, 8))

        # Progress bar (tersembunyi awalnya)
        self._progress = ctk.CTkProgressBar(
            scroll,
            fg_color=T.BG_WIDGET,
            progress_color=T.AKSEN_PRIMER,
            height=4,
            corner_radius=2,
        )
        self._progress.set(0)

        self._lbl_status = ctk.CTkLabel(
            scroll,
            text="",
            font=T.FONT_KECIL,
            text_color=T.TEKS_SEKUNDER,
        )
        self._lbl_status.pack(anchor="w")

    def _bangun_kolom_preview(self, parent: ctk.CTkFrame) -> None:
        """Kolom kanan: preview citra dan panel hasil embedding."""
        kolom = ctk.CTkFrame(parent, fg_color="transparent")
        kolom.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Panel preview citra
        frame_prev = ctk.CTkFrame(kolom, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        frame_prev.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            frame_prev,
            text="Preview Citra Cover",
            font=T.FONT_LABEL_BOLD,
            text_color=T.TEKS_SEKUNDER,
        ).pack(anchor="w", padx=14, pady=(14, 8))

        # Area preview: kotak dashed placeholder
        self._frame_preview_area = ctk.CTkFrame(
            frame_prev,
            fg_color=T.BG_WIDGET,
            corner_radius=T.RADIUS_CARD,
            height=_PREVIEW_SIZE[1],
        )
        self._frame_preview_area.pack(fill="x", padx=14, pady=(0, 8))
        self._frame_preview_area.pack_propagate(False)

        self._lbl_preview = ctk.CTkLabel(
            self._frame_preview_area,
            text="Belum ada\ncitra dipilih",
            font=T.FONT_KECIL,
            text_color=T.TEKS_DISABLED,
            image=None,
        )
        self._lbl_preview.pack(expand=True)

        # Info dimensi citra
        self._lbl_info_citra = ctk.CTkLabel(
            frame_prev,
            text="",
            font=T.FONT_MONO_KECIL,
            text_color=T.TEKS_SEKUNDER,
        )
        self._lbl_info_citra.pack(padx=14, pady=(0, 14))

        # Panel hasil embedding
        self._frame_hasil = ctk.CTkFrame(kolom, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        self._frame_hasil.pack(fill="x")

        ctk.CTkLabel(
            self._frame_hasil,
            text="Hasil Embedding",
            font=T.FONT_LABEL_BOLD,
            text_color=T.TEKS_SEKUNDER,
        ).pack(anchor="w", padx=14, pady=(14, 8))

        ctk.CTkFrame(self._frame_hasil, height=1, fg_color=T.BORDER_SUBTLE).pack(fill="x", padx=14)

        self._lbl_hasil_placeholder = ctk.CTkLabel(
            self._frame_hasil,
            text="Hasil akan muncul\nsetelah proses selesai",
            font=T.FONT_KECIL,
            text_color=T.TEKS_DISABLED,
        )
        self._lbl_hasil_placeholder.pack(pady=20)

        # Widget hasil (tersembunyi awalnya)
        self._frame_hasil_detail = ctk.CTkFrame(self._frame_hasil, fg_color="transparent")
        self._rows_hasil: dict[str, ctk.CTkLabel] = {}
        for key, label in [("path", "File Stego"), ("psnr", "PSNR"), ("mse", "MSE"), ("kapasitas", "Kapasitas Terpakai")]:
            self._rows_hasil[key] = self._buat_baris_hasil(self._frame_hasil_detail, label)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _buat_label_seksi(self, parent, teks: str) -> None:
        ctk.CTkLabel(
            parent,
            text=teks,
            font=("Segoe UI", 9, "bold"),
            text_color=T.TEKS_DISABLED,
        ).pack(anchor="w", pady=(8, 0))

    def _buat_baris_hasil(self, parent: ctk.CTkFrame, label: str) -> ctk.CTkLabel:
        """Membuat baris label:nilai di panel hasil. Mengembalikan label nilai."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3, padx=14)
        ctk.CTkLabel(row, text=f"{label}:", font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER, width=110, anchor="w").pack(side="left")
        lbl_val = ctk.CTkLabel(row, text="—", font=T.FONT_MONO_KECIL, text_color=T.TEKS_PRIMER, anchor="w")
        lbl_val.pack(side="left", fill="x", expand=True)
        return lbl_val

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _pilih_file(self) -> None:
        """Membuka dialog file picker dan memuat info + preview citra yang dipilih."""
        path_str = filedialog.askopenfilename(
            title="Pilih Citra Cover",
            filetypes=[("File Gambar", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("Semua File", "*.*")],
        )
        if not path_str:
            return

        self._path_cover = Path(path_str)

        # Update entry path (harus enable dulu, isi, lalu disable)
        self._entry_path.configure(state="normal")
        self._entry_path.delete(0, "end")
        self._entry_path.insert(0, str(self._path_cover))
        self._entry_path.configure(state="disabled")

        # Load preview
        self._muat_preview(self._path_cover)

        # Info kapasitas
        try:
            info = cek_kapasitas(self._path_cover)
            self._lbl_kapasitas.configure(
                text=f"{info['lebar']}×{info['tinggi']} px  |  Maks. {info['kapasitas_byte']:,} byte",
                text_color=T.TEKS_SEKUNDER,
            )
            self._lbl_info_citra.configure(
                text=f"{info['lebar']} × {info['tinggi']} piksel\n{info['total_piksel']:,} piksel total",
            )
        except Exception as e:
            self._lbl_kapasitas.configure(text=f"Error: {e}", text_color=T.AKSEN_DANGER)

    def _muat_preview(self, path: Path) -> None:
        """Memuat dan menampilkan thumbnail citra di area preview."""
        try:
            with Image.open(path) as img:
                img.thumbnail(_PREVIEW_SIZE, Image.LANCZOS)
                self._ctk_img_prev = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self._lbl_preview.configure(image=self._ctk_img_prev, text="")
        except Exception as e:
            self._lbl_preview.configure(image=None, text=f"Gagal load preview\n{e}", text_color=T.AKSEN_DANGER)

    def _update_hitung_karakter(self, event=None) -> None:
        """Update counter karakter saat pengguna mengetik di textbox pesan."""
        teks = self._textbox_pesan.get("1.0", "end-1c")
        n = len(teks)
        self._lbl_counter.configure(
            text=f"{n} karakter  ({len(teks.encode('utf-8'))} byte)",
            text_color=T.AKSEN_WARNING if n > 500 else T.TEKS_SEKUNDER,
        )

    def _toggle_password(self) -> None:
        """Menampilkan atau menyembunyikan karakter password."""
        self._entry_kunci.configure(show="" if self._var_tampil_pass.get() else "●")

    def _jalankan_embedding(self) -> None:
        """Validasi input lalu jalankan embedding di background thread."""
        if self._sedang_proses:
            return

        # Validasi
        if self._path_cover is None:
            messagebox.showwarning("Input Tidak Lengkap", "Pilih citra cover terlebih dahulu.")
            return

        pesan = self._textbox_pesan.get("1.0", "end-1c").strip()
        if not pesan:
            messagebox.showwarning("Input Tidak Lengkap", "Pesan tidak boleh kosong.")
            return

        kunci = self._entry_kunci.get().strip()
        if not kunci:
            messagebox.showwarning("Input Tidak Lengkap", "Kunci/password tidak boleh kosong.")
            return

        # UI: tampilkan loading state
        self._set_loading(True)

        # Jalankan di thread terpisah agar UI tidak freeze
        thread = threading.Thread(
            target=self._proses_embedding_thread,
            args=(self._path_cover, pesan, kunci),
            daemon=True,
        )
        thread.start()

    def _proses_embedding_thread(self, path_cover: Path, pesan: str, kunci: str) -> None:
        """
        Dijalankan di background thread. JANGAN akses widget Tkinter langsung di sini.
        Gunakan self.after() untuk update UI.
        """
        try:
            # Proses embedding
            hasil = embed_data(
                cover_path=path_cover,
                message=pesan,
                key=kunci,
            )

            # Hitung metrik kualitas
            metrik = hitung_semua_metrik(str(path_cover), str(hasil.path_stego))

            # Simpan ke database
            record = HistoryRecord(
                nama_file=path_cover.name,
                ukuran_pesan=len(pesan.encode("utf-8")),
                kunci_seed=kunci,
                nilai_psnr=metrik["psnr"],
                nilai_mse=metrik["mse"],
            )
            self.controller.db.simpan_riwayat(record)

            # Jadwalkan update UI di main thread
            self.after(0, lambda: self._on_embedding_sukses(hasil, metrik))

        except ValueError as e:
            self.after(0, lambda msg=str(e): self._on_embedding_gagal(msg))
        except Exception as e:
            logger.error(f"Error tidak terduga saat embedding: {e}", exc_info=True)
            self.after(0, lambda msg=str(e): self._on_embedding_gagal(f"Error: {msg}"))

    def _on_embedding_sukses(self, hasil, metrik: dict) -> None:
        """Dipanggil di main thread setelah embedding berhasil."""
        self._set_loading(False)

        # Tampilkan panel hasil
        self._lbl_hasil_placeholder.pack_forget()
        self._frame_hasil_detail.pack(fill="x", pady=(8, 14))

        self._rows_hasil["path"].configure(
            text=hasil.path_stego.name,
            text_color=T.AKSEN_SUKSES,
        )
        self._rows_hasil["psnr"].configure(
            text=f"{metrik['psnr']:.4f} dB",
            text_color=T.AKSEN_PRIMER,
        )
        self._rows_hasil["mse"].configure(
            text=f"{metrik['mse']:.6f}",
            text_color=T.TEKS_PRIMER,
        )
        self._rows_hasil["kapasitas"].configure(
            text=f"{hasil.persentase_pakai:.2f}% dari kapasitas",
            text_color=T.TEKS_SEKUNDER,
        )

        self._lbl_status.configure(
            text="✓  Embedding berhasil! Data tersimpan ke riwayat.",
            text_color=T.AKSEN_SUKSES,
        )

        messagebox.showinfo(
            "Berhasil!",
            f"Embedding selesai.\n\n"
            f"File stego: {hasil.path_stego.name}\n"
            f"PSNR: {metrik['psnr']:.4f} dB\n"
            f"MSE:  {metrik['mse']:.6f}\n\n"
            f"Data telah disimpan ke riwayat."
        )

    def _on_embedding_gagal(self, pesan_error: str) -> None:
        """Dipanggil di main thread saat embedding gagal."""
        self._set_loading(False)
        self._lbl_status.configure(
            text=f"✕  Gagal: {pesan_error}",
            text_color=T.AKSEN_DANGER,
        )
        messagebox.showerror("Embedding Gagal", pesan_error)

    def _set_loading(self, aktif: bool) -> None:
        """Mengaktifkan/menonaktifkan mode loading: disable tombol + tampilkan progress bar."""
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