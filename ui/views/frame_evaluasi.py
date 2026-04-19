"""
================================================================================
MODULE  : ui/views/frame_evaluasi.py
PROJECT : Stego MWC — Steganografi LSB + PRNG Multiply-With-Carry
DESKRIPSI:
    Halaman Evaluasi & Analisis — sesuai Gambar 3.14 pada proposal skripsi.

    FITUR:
      • Pilih citra cover dan citra stego secara terpisah.
      • Hitung PSNR dan MSE secara langsung di UI (tanpa terminal).
      • Visualisasi histogram RGB perbandingan (matplotlib embedded).
      • Visualisasi noise map — peta piksel yang berubah (matplotlib embedded).
      • Visualisasi komparasi visual cover vs stego side-by-side.
      • Semua grafik di-render langsung di dalam tab CTkTabview.

    TEKNIK EMBEDDING MATPLOTLIB KE CUSTOMTKINTER:
      Menggunakan FigureCanvasTkAgg dari matplotlib.backends.backend_tkagg.
      Canvas ini adalah widget Tkinter biasa yang bisa di-pack/grid seperti
      widget lainnya. Setiap kali evaluasi dijalankan, figure lama di-clear
      dan digambar ulang (clf + draw).
================================================================================
"""

import logging
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import numpy as np
from PIL import Image

from ui import theme as T

# Matplotlib harus diimport setelah customtkinter agar backend tidak konflik
try:
    import matplotlib
    matplotlib.use("TkAgg")   # Backend Tkinter
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.colors import LinearSegmentedColormap
    _MATPLOTLIB_TERSEDIA = True
except ImportError:
    _MATPLOTLIB_TERSEDIA = False

logger = logging.getLogger(__name__)

# Colormap custom teal untuk noise map
_CMAP_STEGO = LinearSegmentedColormap.from_list(
    "stego", [(0, "#161b22"), (0.5, "#003d2e"), (1.0, "#00d4aa")]
) if _MATPLOTLIB_TERSEDIA else None


class FrameEvaluasi(ctk.CTkFrame):
    """
    Frame halaman Evaluasi & Analisis.

    Attributes:
        _path_cover (Path | None): Path citra asli yang dipilih.
        _path_stego (Path | None): Path citra stego yang dipilih.
        _canvas_dict (dict)      : Menyimpan FigureCanvasTkAgg per tab agar
                                   tidak di-garbage collect.
    """

    def __init__(self, parent: ctk.CTkFrame, controller) -> None:
        super().__init__(parent, fg_color=T.BG_APP, corner_radius=0)
        self.controller = controller

        self._path_cover: Path | None = None
        self._path_stego: Path | None = None
        self._canvas_dict: dict[str, FigureCanvasTkAgg] = {}
        self._sedang_proses = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._bangun_ui()

    # ── UI Builder ────────────────────────────────────────────────────────────

    def _bangun_ui(self) -> None:
        # Header
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))
        ctk.CTkLabel(frame_header, text="Evaluasi & Analisis", font=T.FONT_JUDUL, text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(frame_header, text="Uji kualitas citra stego: PSNR, MSE, Histogram, dan Noise Map",
                     font=T.FONT_LABEL, text_color=T.TEKS_SEKUNDER).pack(anchor="w", pady=(2, 0))
        ctk.CTkFrame(frame_header, height=2, fg_color="#fbbf24", corner_radius=1).pack(fill="x", pady=(12, 0))

        if not _MATPLOTLIB_TERSEDIA:
            ctk.CTkLabel(
                self,
                text="⚠  Matplotlib tidak terinstall.\nJalankan: pip install matplotlib",
                font=T.FONT_SUBJUDUL, text_color=T.AKSEN_WARNING,
            ).grid(row=1, column=0, pady=40)
            return

        # Body: 2 kolom
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        self._bangun_kolom_kiri(body)
        self._bangun_kolom_kanan(body)

    def _bangun_kolom_kiri(self, parent: ctk.CTkFrame) -> None:
        """Form input + tombol evaluasi + panel hasil metrik."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=T.BORDER_NORMAL)
        scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # ── Pilih Cover ───────────────────────────────────────────────────────
        self._buat_label_seksi(scroll, "1  PILIH CITRA COVER (ASLI)")
        f_cover = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_cover.pack(fill="x", pady=(4, 10))
        self._entry_cover = self._buat_entry_path(f_cover, "Pilih citra cover (.png)...")
        ctk.CTkButton(f_cover, text="  Pilih Cover", font=T.FONT_LABEL, height=32,
                      corner_radius=T.RADIUS_BTN, fg_color=T.BTN_SEKUNDER_BG,
                      text_color=T.TEKS_PRIMER, hover_color=T.BG_HOVER,
                      command=lambda: self._pilih_file("cover")).pack(anchor="w", padx=12, pady=(0, 10))

        # ── Pilih Stego ───────────────────────────────────────────────────────
        self._buat_label_seksi(scroll, "2  PILIH CITRA STEGO (HASIL EMBEDDING)")
        f_stego = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_stego.pack(fill="x", pady=(4, 10))
        self._entry_stego = self._buat_entry_path(f_stego, "Pilih citra stego (.png)...")
        ctk.CTkButton(f_stego, text="  Pilih Stego", font=T.FONT_LABEL, height=32,
                      corner_radius=T.RADIUS_BTN, fg_color=T.BTN_SEKUNDER_BG,
                      text_color=T.TEKS_PRIMER, hover_color=T.BG_HOVER,
                      command=lambda: self._pilih_file("stego")).pack(anchor="w", padx=12, pady=(0, 10))

        # ── Kunci (untuk noise map MWC) ───────────────────────────────────────
        self._buat_label_seksi(scroll, "3  KUNCI (OPSIONAL — untuk noise map MWC)")
        f_kunci = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_kunci.pack(fill="x", pady=(4, 10))
        self._entry_kunci = ctk.CTkEntry(
            f_kunci, placeholder_text="Kunci saat embedding (jika ingin overlay MWC)...",
            show="●", font=T.FONT_LABEL, fg_color=T.BG_WIDGET,
            border_color=T.BORDER_NORMAL, text_color=T.TEKS_PRIMER,
            height=36, corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_kunci.pack(fill="x", padx=12, pady=10)

        # ── Tombol Evaluasi ───────────────────────────────────────────────────
        self._btn_evaluasi = ctk.CTkButton(
            scroll, text="  ▶  Mulai Evaluasi",
            font=("Segoe UI", 13, "bold"), height=46, corner_radius=T.RADIUS_BTN,
            fg_color="#fbbf24", text_color=T.BG_APP, hover_color="#d97706",
            command=self._jalankan_evaluasi,
        )
        self._btn_evaluasi.pack(fill="x", pady=(4, 8))

        self._progress = ctk.CTkProgressBar(scroll, fg_color=T.BG_WIDGET,
                                             progress_color="#fbbf24", height=4, corner_radius=2)
        self._progress.set(0)
        self._lbl_status = ctk.CTkLabel(scroll, text="", font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER)
        self._lbl_status.pack(anchor="w")

        # ── Panel Hasil Metrik ────────────────────────────────────────────────
        self._buat_label_seksi(scroll, "HASIL EVALUASI")
        f_hasil = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_hasil.pack(fill="x", pady=(4, 0))

        self._rows_metrik: dict[str, ctk.CTkLabel] = {}
        metrik_items = [
            ("psnr",      "PSNR",            T.AKSEN_PRIMER),
            ("mse",       "MSE",             T.TEKS_PRIMER),
            ("dimensi",   "Dimensi",         T.TEKS_SEKUNDER),
            ("berubah",   "Piksel berubah",  T.AKSEN_WARNING),
            ("persentase","Persentase ubah", T.TEKS_SEKUNDER),
            ("status",    "Kualitas",        T.AKSEN_SUKSES),
        ]
        for key, label, warna in metrik_items:
            self._rows_metrik[key] = self._buat_baris_metrik(f_hasil, label, warna)

        # Nilai awal
        for key in self._rows_metrik:
            self._rows_metrik[key].configure(text="—")

    def _bangun_kolom_kanan(self, parent: ctk.CTkFrame) -> None:
        """Panel kanan: CTkTabview dengan 3 tab visualisasi matplotlib."""
        self._tabview = ctk.CTkTabview(
            parent,
            fg_color=T.BG_PANEL,
            segmented_button_fg_color=T.BG_WIDGET,
            segmented_button_selected_color=T.AKSEN_PRIMER,
            segmented_button_selected_hover_color="#00b894",
            segmented_button_unselected_color=T.BG_WIDGET,
            segmented_button_unselected_hover_color=T.BG_HOVER,
            text_color=T.TEKS_PRIMER,
            text_color_disabled=T.TEKS_DISABLED,
            corner_radius=T.RADIUS_CARD,
        )
        self._tabview.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Buat 3 tab
        for nama_tab in ["Histogram RGB", "Noise Map", "Komparasi Visual"]:
            self._tabview.add(nama_tab)
            tab = self._tabview.tab(nama_tab)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

            # Placeholder label di setiap tab
            lbl = ctk.CTkLabel(
                tab,
                text=f"Jalankan evaluasi\nuntuk melihat {nama_tab}",
                font=T.FONT_LABEL, text_color=T.TEKS_DISABLED,
            )
            lbl.grid(row=0, column=0)

            # Simpan referensi placeholder untuk di-hide nanti
            tab._placeholder = lbl  # type: ignore[attr-defined]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _buat_label_seksi(self, parent, teks: str) -> None:
        ctk.CTkLabel(parent, text=teks, font=("Segoe UI", 9, "bold"),
                     text_color=T.TEKS_DISABLED).pack(anchor="w", pady=(8, 0))

    def _buat_entry_path(self, parent: ctk.CTkFrame, placeholder: str) -> ctk.CTkEntry:
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder,
                             font=T.FONT_MONO_KECIL, fg_color=T.BG_WIDGET,
                             border_color=T.BORDER_NORMAL, text_color=T.TEKS_PRIMER,
                             state="disabled", height=34, corner_radius=T.RADIUS_ENTRY)
        entry.pack(fill="x", padx=12, pady=(10, 6))
        return entry

    def _buat_baris_metrik(self, parent: ctk.CTkFrame, label: str, warna: str) -> ctk.CTkLabel:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row, text=f"{label}:", font=T.FONT_KECIL,
                     text_color=T.TEKS_SEKUNDER, width=120, anchor="w").pack(side="left")
        lbl_val = ctk.CTkLabel(row, text="—", font=T.FONT_MONO_KECIL,
                               text_color=warna, anchor="w")
        lbl_val.pack(side="left", fill="x", expand=True)
        return lbl_val

    def _set_entry(self, entry: ctk.CTkEntry, nilai: str) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, nilai)
        entry.configure(state="disabled")

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _pilih_file(self, jenis: str) -> None:
        """Membuka dialog pilih file untuk cover atau stego."""
        path_str = filedialog.askopenfilename(
            title=f"Pilih Citra {'Cover' if jenis == 'cover' else 'Stego'}",
            filetypes=[("File PNG", "*.png"), ("Semua Gambar", "*.png *.jpg *.bmp"), ("Semua", "*.*")],
        )
        if not path_str:
            return
        path = Path(path_str)
        if jenis == "cover":
            self._path_cover = path
            self._set_entry(self._entry_cover, str(path))
        else:
            self._path_stego = path
            self._set_entry(self._entry_stego, str(path))

    def _jalankan_evaluasi(self) -> None:
        """Validasi input lalu jalankan evaluasi di background thread."""
        if self._sedang_proses:
            return
        if self._path_cover is None:
            messagebox.showwarning("Input Kurang", "Pilih citra cover terlebih dahulu.")
            return
        if self._path_stego is None:
            messagebox.showwarning("Input Kurang", "Pilih citra stego terlebih dahulu.")
            return

        kunci = self._entry_kunci.get().strip()
        self._set_loading(True)

        thread = threading.Thread(
            target=self._thread_evaluasi,
            args=(self._path_cover, self._path_stego, kunci),
            daemon=True,
        )
        thread.start()

    def _thread_evaluasi(self, path_cover: Path, path_stego: Path, kunci: str) -> None:
        """Dijalankan di background thread — semua komputasi berat di sini."""
        try:
            # Muat citra
            with Image.open(path_cover) as img:
                arr_cover = np.array(img.convert("RGB"), dtype=np.uint8)
            with Image.open(path_stego) as img:
                arr_stego = np.array(img.convert("RGB"), dtype=np.uint8)

            if arr_cover.shape != arr_stego.shape:
                raise ValueError(
                    f"Dimensi tidak sama!\nCover: {arr_cover.shape} | Stego: {arr_stego.shape}"
                )

            # Hitung metrik
            selisih   = arr_cover.astype(np.float64) - arr_stego.astype(np.float64)
            mse       = float(np.mean(selisih ** 2))
            psnr      = (10.0 * np.log10(255.0 ** 2 / mse)) if mse > 0 else float("inf")
            mask_ubah = arr_cover[:, :, 0] != arr_stego[:, :, 0]
            n_berubah = int(mask_ubah.sum())
            h, w      = arr_cover.shape[:2]

            # Koordinat MWC (jika kunci diberikan)
            koordinat_mwc = None
            if kunci:
                try:
                    from engine.mwc_generator import MWCGenerator
                    n_bit = max(32, n_berubah + 32)
                    gen   = MWCGenerator(password=kunci)
                    koordinat_mwc = gen.hasilkan_koordinat(
                        lebar=w, tinggi=h,
                        jumlah=min(n_bit, w * h),
                    )
                except Exception:
                    koordinat_mwc = None

            # Jadwalkan update UI di main thread
            self.after(0, lambda: self._on_sukses(
                arr_cover, arr_stego, mask_ubah,
                mse, psnr, n_berubah, w, h, koordinat_mwc,
            ))

        except Exception as e:
            logger.error(f"Error evaluasi: {e}", exc_info=True)
            self.after(0, lambda msg=str(e): self._on_gagal(msg))

    def _on_sukses(
        self,
        arr_cover: np.ndarray,
        arr_stego: np.ndarray,
        mask_ubah: np.ndarray,
        mse: float,
        psnr: float,
        n_berubah: int,
        w: int,
        h: int,
        koordinat_mwc,
    ) -> None:
        """Dipanggil di main thread setelah evaluasi berhasil."""
        self._set_loading(False)

        # Update panel metrik
        psnr_str  = f"{psnr:.4f} dB" if psnr != float("inf") else "∞ dB (identik)"
        persentase = (n_berubah / (w * h)) * 100

        if psnr == float("inf") or psnr >= 50:
            status, warna_s = "Sangat Baik (> 50 dB)", T.AKSEN_SUKSES
        elif psnr >= 40:
            status, warna_s = "Baik (40–50 dB)", T.AKSEN_PRIMER
        elif psnr >= 30:
            status, warna_s = "Cukup (30–40 dB)", T.AKSEN_WARNING
        else:
            status, warna_s = "Buruk (< 30 dB)", T.AKSEN_DANGER

        self._rows_metrik["psnr"].configure(text=psnr_str,       text_color=T.AKSEN_PRIMER)
        self._rows_metrik["mse"].configure( text=f"{mse:.6f}",   text_color=T.TEKS_PRIMER)
        self._rows_metrik["dimensi"].configure(text=f"{w} × {h} piksel")
        self._rows_metrik["berubah"].configure(text=f"{n_berubah:,} piksel", text_color=T.AKSEN_WARNING)
        self._rows_metrik["persentase"].configure(text=f"{persentase:.4f}%")
        self._rows_metrik["status"].configure(text=status, text_color=warna_s)

        self._lbl_status.configure(text="✓  Evaluasi selesai!", text_color=T.AKSEN_SUKSES)

        # Render ketiga visualisasi
        self._render_histogram(arr_cover, arr_stego)
        self._render_noise_map(arr_cover, arr_stego, mask_ubah, koordinat_mwc)
        self._render_komparasi(arr_cover, arr_stego, psnr, mse)

    def _on_gagal(self, pesan: str) -> None:
        self._set_loading(False)
        self._lbl_status.configure(text=f"✕  {pesan[:80]}", text_color=T.AKSEN_DANGER)
        messagebox.showerror("Evaluasi Gagal", pesan)

    # ── Render Matplotlib ─────────────────────────────────────────────────────

    def _get_atau_buat_canvas(
        self,
        nama_tab: str,
        figsize: tuple[float, float],
    ) -> tuple["plt.Figure", "FigureCanvasTkAgg"]:
        """
        Mendapatkan atau membuat FigureCanvasTkAgg di dalam tab yang ditentukan.
        Jika canvas sudah ada, figure-nya di-clear untuk digambar ulang.
        """
        tab = self._tabview.tab(nama_tab)

        if nama_tab in self._canvas_dict:
            canvas = self._canvas_dict[nama_tab]
            canvas.figure.clf()
            return canvas.figure, canvas

        # Hapus placeholder label
        if hasattr(tab, "_placeholder"):
            tab._placeholder.grid_forget()

        fig = plt.Figure(figsize=figsize, facecolor=T.BG_DARK)
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self._canvas_dict[nama_tab] = canvas
        return fig, canvas

    def _setup_ax(self, ax: "plt.Axes", judul: str) -> None:
        """Mengaplikasikan tema gelap ke satu axes."""
        ax.set_facecolor(T.BG_PANEL)
        ax.set_title(judul, color=T.TEKS_PRIMER, fontsize=9, fontweight="bold")
        ax.tick_params(colors=T.TEKS_SEKUNDER, labelsize=7)
        ax.xaxis.label.set_color(T.TEKS_SEKUNDER)
        ax.yaxis.label.set_color(T.TEKS_SEKUNDER)
        for spine in ax.spines.values():
            spine.set_edgecolor(T.BORDER_NORMAL)
        ax.grid(True, color=T.BORDER_NORMAL, linewidth=0.4, alpha=0.6)

    def _render_histogram(self, arr_cover: np.ndarray, arr_stego: np.ndarray) -> None:
        """Render histogram RGB 3 subplot ke tab 'Histogram RGB'."""
        fig, canvas = self._get_atau_buat_canvas("Histogram RGB", figsize=(7, 4.5))
        bins = np.arange(257)
        warna = [("#e05c5c", "#e0a0a0"), ("#5cb85c", "#a0e0a0"), ("#5c8fe0", "#a0c0f0")]
        nama  = ["Channel R (Red)", "Channel G (Green)", "Channel B (Blue)"]

        axes = fig.subplots(1, 3)
        for i, (ax, nm, (wc, ws)) in enumerate(zip(axes, nama, warna)):
            fc, _ = np.histogram(arr_cover[:, :, i].ravel(), bins=bins)
            fs, _ = np.histogram(arr_stego[:, :, i].ravel(), bins=bins)
            ax.fill_between(bins[:-1], fc, alpha=0.55, color=wc, step="post", label="Cover")
            ax.fill_between(bins[:-1], fs, alpha=0.55, color=ws, step="post", label="Stego")
            ax.step(bins[:-1], fc, color=wc, linewidth=0.7, where="post")
            ax.step(bins[:-1], fs, color=ws, linewidth=0.7, where="post")
            self._setup_ax(ax, nm)
            ax.set_xlim(0, 255)
            ax.set_xlabel("Intensitas (0–255)", fontsize=7)
            ax.set_ylabel("Frekuensi", fontsize=7)
            ax.legend(fontsize=6, facecolor=T.BG_PANEL, labelcolor=T.TEKS_PRIMER)

        fig.tight_layout(pad=1.5)
        canvas.draw()

    def _render_noise_map(
        self,
        arr_cover: np.ndarray,
        arr_stego: np.ndarray,
        mask_ubah: np.ndarray,
        koordinat_mwc,
    ) -> None:
        """Render noise map binary + scatter MWC ke tab 'Noise Map'."""
        fig, canvas = self._get_atau_buat_canvas("Noise Map", figsize=(7, 4))
        n_subplot = 3 if koordinat_mwc else 2
        axes = fig.subplots(1, n_subplot)
        if n_subplot == 2:
            axes = list(axes)

        # Noise map binary
        ax0 = axes[0]
        ax0.imshow((mask_ubah.astype(np.uint8)) * 255, cmap="gray", aspect="auto")
        self._setup_ax(ax0, "Noise Map Binary\n(Putih = Piksel Berubah)")
        ax0.set_xlabel(f"Kolom", fontsize=7)
        ax0.set_ylabel("Baris", fontsize=7)

        # Overlay warna teal pada piksel berubah
        overlay = arr_cover.copy()
        overlay[mask_ubah, 0] = 0
        overlay[mask_ubah, 1] = 212
        overlay[mask_ubah, 2] = 170
        ax1 = axes[1]
        ax1.imshow(overlay, aspect="auto")
        self._setup_ax(ax1, "Overlay Noise Map\n(Teal = Dimodifikasi LSB)")
        ax1.grid(False)

        # Scatter koordinat MWC (jika kunci diisi)
        if koordinat_mwc and n_subplot == 3:
            ax2 = axes[2]
            xs = [x for x, y in koordinat_mwc]
            ys = [y for x, y in koordinat_mwc]
            ax2.scatter(xs, ys, s=0.3, alpha=0.3, color=T.AKSEN_DANGER, linewidths=0)
            self._setup_ax(ax2, f"Scatter Koordinat MWC\n({len(koordinat_mwc):,} titik)")
            ax2.set_xlim(0, arr_cover.shape[1])
            ax2.set_ylim(arr_cover.shape[0], 0)
            ax2.set_xlabel("X (kolom)", fontsize=7)
            ax2.set_ylabel("Y (baris)", fontsize=7)

        fig.tight_layout(pad=1.5)
        canvas.draw()

    def _render_komparasi(
        self,
        arr_cover: np.ndarray,
        arr_stego: np.ndarray,
        psnr: float,
        mse: float,
    ) -> None:
        """Render komparasi visual cover vs stego ke tab 'Komparasi Visual'."""
        fig, canvas = self._get_atau_buat_canvas("Komparasi Visual", figsize=(7, 4))
        axes = fig.subplots(1, 2)

        axes[0].imshow(arr_cover)
        axes[0].set_title("Citra Cover (Asli)", color=T.AKSEN_PRIMER,
                          fontsize=9, fontweight="bold")
        axes[0].axis("off")

        axes[1].imshow(arr_stego)
        psnr_lbl = f"{psnr:.4f} dB" if psnr != float("inf") else "∞ dB"
        axes[1].set_title(f"Citra Stego | PSNR={psnr_lbl} | MSE={mse:.4f}",
                          color=T.AKSEN_WARNING, fontsize=9, fontweight="bold")
        axes[1].axis("off")

        fig.tight_layout(pad=1.0)
        canvas.draw()

    # ── Loading State ─────────────────────────────────────────────────────────

    def _set_loading(self, aktif: bool) -> None:
        self._sedang_proses = aktif
        if aktif:
            self._btn_evaluasi.configure(text="  ⏳  Mengevaluasi...",
                                          state="disabled", fg_color=T.TEKS_DISABLED)
            self._progress.pack(fill="x", pady=(4, 2))
            self._progress.start()
            self._lbl_status.configure(text="Sedang menghitung metrik...",
                                        text_color=T.TEKS_SEKUNDER)
        else:
            self._btn_evaluasi.configure(text="  ▶  Mulai Evaluasi",
                                          state="normal", fg_color="#fbbf24")
            self._progress.stop()
            self._progress.pack_forget()

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass