import io
import logging
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import numpy as np
from PIL import Image

from ui import theme as T

# Import matplotlib dengan backend Agg (non-interactive) — HARUS sebelum pyplot
try:
    import matplotlib
    matplotlib.use("Agg")           # Non-interactive, render ke memory buffer
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    _MPL_OK = True
except ImportError:
    _MPL_OK = False

logger = logging.getLogger(__name__)

_CMAP_STEGO = LinearSegmentedColormap.from_list(
    "stego", [(0, "#161b22"), (0.5, "#003d2e"), (1.0, "#00d4aa")]
) if _MPL_OK else None

# Tema matplotlib — diterapkan sekali saat modul dimuat
_TEMA = {
    "figure.facecolor":  "#0d1117",
    "axes.facecolor":    "#161b22",
    "axes.edgecolor":    "#30363d",
    "axes.labelcolor":   "#e6edf3",
    "axes.titlecolor":   "#e6edf3",
    "axes.grid":         True,
    "grid.color":        "#30363d",
    "grid.linewidth":    0.5,
    "xtick.color":       "#8b949e",
    "ytick.color":       "#8b949e",
    "text.color":        "#e6edf3",
    "legend.facecolor":  "#161b22",
    "legend.edgecolor":  "#30363d",
    "font.family":       "DejaVu Sans",
    "font.size":         9,
}
if _MPL_OK:
    matplotlib.rcParams.update(_TEMA)


def _fig_ke_ctk_image(fig, lebar_px: int, tinggi_px: int) -> ctk.CTkImage:
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor(), dpi=110)
    buf.seek(0)
    pil_img = Image.open(buf).convert("RGB")
    pil_img = pil_img.resize((lebar_px, tinggi_px), Image.LANCZOS)
    plt.close(fig)
    return ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                        size=(lebar_px, tinggi_px))


def _setup_ax(ax, judul: str = "") -> None:
    
    ax.set_facecolor("#161b22")
    if judul:
        ax.set_title(judul, color="#e6edf3", fontsize=8, fontweight="bold")
    ax.tick_params(colors="#8b949e", labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")
    ax.grid(True, color="#30363d", linewidth=0.4, alpha=0.5)


class FrameEvaluasi(ctk.CTkFrame):
    
    def __init__(self, parent: ctk.CTkFrame, controller) -> None:
        super().__init__(parent, fg_color=T.BG_APP, corner_radius=0)
        self.controller = controller

        self._path_cover: Path | None = None
        self._path_stego: Path | None = None
        self._sedang_proses = False

        # Simpan referensi CTkImage agar tidak di-garbage collect
        self._img_histogram:  ctk.CTkImage | None = None
        self._img_noise_map:  ctk.CTkImage | None = None
        self._img_komparasi:  ctk.CTkImage | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._bangun_ui()

    # ── UI Builder ────────────────────────────────────────────────────────────

    def _bangun_ui(self) -> None:
        # Header
        f_header = ctk.CTkFrame(self, fg_color="transparent")
        f_header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))
        ctk.CTkLabel(f_header, text="Evaluasi & Analisis", font=T.FONT_JUDUL,
                     text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(f_header,
                     text="Uji kualitas citra stego: PSNR, MSE, Histogram, dan Noise Map",
                     font=T.FONT_LABEL, text_color=T.TEKS_SEKUNDER).pack(anchor="w", pady=(2, 0))
        ctk.CTkFrame(f_header, height=2, fg_color="#fbbf24", corner_radius=1).pack(fill="x", pady=(12, 0))

        if not _MPL_OK:
            ctk.CTkLabel(self,
                         text="⚠  Matplotlib tidak terinstall.\nJalankan: pip install matplotlib",
                         font=T.FONT_SUBJUDUL, text_color=T.AKSEN_WARNING).grid(row=1, column=0, pady=40)
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
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=T.BORDER_NORMAL)
        scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Pilih Cover
        self._seksi(scroll, "1  PILIH CITRA COVER (ASLI)")
        f_cv = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_cv.pack(fill="x", pady=(4, 10))
        self._entry_cover = self._entry_path(f_cv, "Pilih citra cover (.png)...")
        ctk.CTkButton(f_cv, text="  Pilih Cover", font=T.FONT_LABEL, height=32,
                      corner_radius=T.RADIUS_BTN, fg_color=T.BTN_SEKUNDER_BG,
                      text_color=T.TEKS_PRIMER, hover_color=T.BG_HOVER,
                      command=lambda: self._pilih("cover")).pack(anchor="w", padx=12, pady=(0, 10))

        # Pilih Stego
        self._seksi(scroll, "2  PILIH CITRA STEGO (HASIL EMBEDDING)")
        f_st = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_st.pack(fill="x", pady=(4, 10))
        self._entry_stego = self._entry_path(f_st, "Pilih citra stego (.png)...")
        ctk.CTkButton(f_st, text="  Pilih Stego", font=T.FONT_LABEL, height=32,
                      corner_radius=T.RADIUS_BTN, fg_color=T.BTN_SEKUNDER_BG,
                      text_color=T.TEKS_PRIMER, hover_color=T.BG_HOVER,
                      command=lambda: self._pilih("stego")).pack(anchor="w", padx=12, pady=(0, 10))

        # Kunci (opsional)
        self._seksi(scroll, "3  KUNCI (OPSIONAL — untuk scatter MWC di noise map)")
        f_kunci = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_kunci.pack(fill="x", pady=(4, 10))
        self._entry_kunci = ctk.CTkEntry(
            f_kunci, placeholder_text="Kunci saat embedding (opsional)...",
            show="●", font=T.FONT_LABEL, fg_color=T.BG_WIDGET,
            border_color=T.BORDER_NORMAL, text_color=T.TEKS_PRIMER,
            height=36, corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_kunci.pack(fill="x", padx=12, pady=10)

        # Tombol evaluasi
        self._btn_eval = ctk.CTkButton(
            scroll, text="  ▶  Mulai Evaluasi",
            font=("Segoe UI", 13, "bold"), height=46, corner_radius=T.RADIUS_BTN,
            fg_color="#fbbf24", text_color=T.BG_APP, hover_color="#d97706",
            command=self._jalankan,
        )
        self._btn_eval.pack(fill="x", pady=(4, 8))

        self._progress = ctk.CTkProgressBar(scroll, fg_color=T.BG_WIDGET,
                                             progress_color="#fbbf24", height=4, corner_radius=2)
        self._progress.set(0)
        self._lbl_status = ctk.CTkLabel(scroll, text="", font=T.FONT_KECIL,
                                         text_color=T.TEKS_SEKUNDER)
        self._lbl_status.pack(anchor="w")

        # Panel metrik hasil
        self._seksi(scroll, "HASIL METRIK EVALUASI")
        f_hasil = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_hasil.pack(fill="x", pady=(4, 0))

        self._metrik: dict[str, ctk.CTkLabel] = {}
        for key, label, warna in [
            ("psnr",      "PSNR",              T.AKSEN_PRIMER),
            ("mse",       "MSE",               T.TEKS_PRIMER),
            ("dimensi",   "Dimensi",           T.TEKS_SEKUNDER),
            ("berubah",   "Piksel berubah",    T.AKSEN_WARNING),
            ("persentase","Persentase ubah",   T.TEKS_SEKUNDER),
            ("kualitas",  "Kualitas",          T.AKSEN_SUKSES),
        ]:
            row = ctk.CTkFrame(f_hasil, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(row, text=f"{label}:", font=T.FONT_KECIL,
                         text_color=T.TEKS_SEKUNDER, width=120, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", font=T.FONT_MONO_KECIL,
                               text_color=warna, anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            self._metrik[key] = lbl

    def _bangun_kolom_kanan(self, parent: ctk.CTkFrame) -> None:
        
        self._tabs = ctk.CTkTabview(
            parent,
            fg_color=T.BG_PANEL,
            segmented_button_fg_color=T.BG_WIDGET,
            segmented_button_selected_color="#fbbf24",
            segmented_button_selected_hover_color="#d97706",
            segmented_button_unselected_color=T.BG_WIDGET,
            segmented_button_unselected_hover_color=T.BG_HOVER,
            text_color=T.TEKS_PRIMER,
            corner_radius=T.RADIUS_CARD,
        )
        self._tabs.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._lbl_tab: dict[str, ctk.CTkLabel] = {}

        for nama in ["Histogram RGB", "Noise Map", "Komparasi Visual"]:
            self._tabs.add(nama)
            tab = self._tabs.tab(nama)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

            # Label placeholder — akan diganti dengan CTkImage setelah render
            lbl = ctk.CTkLabel(
                tab,
                text=f"Jalankan evaluasi\nuntuk melihat {nama}",
                font=T.FONT_LABEL,
                text_color=T.TEKS_DISABLED,
                image=None,
            )
            lbl.grid(row=0, column=0, sticky="nsew")
            self._lbl_tab[nama] = lbl

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _seksi(self, parent, teks: str) -> None:
        ctk.CTkLabel(parent, text=teks, font=("Segoe UI", 9, "bold"),
                     text_color=T.TEKS_DISABLED).pack(anchor="w", pady=(8, 0))

    def _entry_path(self, parent: ctk.CTkFrame, ph: str) -> ctk.CTkEntry:
        e = ctk.CTkEntry(parent, placeholder_text=ph, font=T.FONT_MONO_KECIL,
                         fg_color=T.BG_WIDGET, border_color=T.BORDER_NORMAL,
                         text_color=T.TEKS_PRIMER, state="disabled",
                         height=34, corner_radius=T.RADIUS_ENTRY)
        e.pack(fill="x", padx=12, pady=(10, 6))
        return e

    def _set_entry(self, entry: ctk.CTkEntry, val: str) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, val)
        entry.configure(state="disabled")

    def _ukuran_tab(self) -> tuple[int, int]:
        
        self._tabs.update_idletasks()
        lebar  = max(self._tabs.winfo_width()  - 20, 500)
        tinggi = max(self._tabs.winfo_height() - 60, 340)
        return lebar, tinggi

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _pilih(self, jenis: str) -> None:
        path_str = filedialog.askopenfilename(
            title=f"Pilih Citra {'Cover' if jenis == 'cover' else 'Stego'}",
            filetypes=[("PNG", "*.png"), ("Semua Gambar", "*.png *.jpg *.bmp"), ("Semua", "*.*")],
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

    def _jalankan(self) -> None:
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
        threading.Thread(
            target=self._thread_evaluasi,
            args=(self._path_cover, self._path_stego, kunci),
            daemon=True,
        ).start()

    def _thread_evaluasi(self, cv: Path, st: Path, kunci: str) -> None:
        
        try:
            with Image.open(cv) as img:
                arr_cv = np.array(img.convert("RGB"), dtype=np.uint8)
            with Image.open(st) as img:
                arr_st = np.array(img.convert("RGB"), dtype=np.uint8)

            if arr_cv.shape != arr_st.shape:
                raise ValueError(
                    f"Dimensi tidak sama!\nCover: {arr_cv.shape} | Stego: {arr_st.shape}"
                )

            selisih   = arr_cv.astype(np.float64) - arr_st.astype(np.float64)
            mse       = float(np.mean(selisih ** 2))
            psnr      = (10.0 * np.log10(255.0 ** 2 / mse)) if mse > 0 else float("inf")
            mask_ubah = arr_cv[:, :, 0] != arr_st[:, :, 0]
            n_ubah    = int(mask_ubah.sum())
            h, w      = arr_cv.shape[:2]

            # Koordinat MWC opsional
            koordinat_mwc = None
            if kunci:
                try:
                    from engine.mwc_generator import MWCGenerator
                    n_bit = max(32, n_ubah + 32)
                    gen   = MWCGenerator(password=kunci)
                    koordinat_mwc = gen.hasilkan_koordinat(
                        lebar=w, tinggi=h, jumlah=min(n_bit, w * h)
                    )
                except Exception:
                    koordinat_mwc = None

            # Render semua figure di thread ini (matplotlib Agg tidak butuh main thread)
            lebar_px, tinggi_px = 640, 380  # Ukuran gambar yang di-render

            img_hist  = self._render_histogram(arr_cv, arr_st, lebar_px, tinggi_px)
            img_noise = self._render_noise_map(arr_cv, arr_st, mask_ubah, koordinat_mwc,
                                               lebar_px, tinggi_px)
            img_komp  = self._render_komparasi(arr_cv, arr_st, psnr, mse, lebar_px, tinggi_px)

            # Jadwalkan update UI di main thread
            self.after(0, lambda: self._on_sukses(
                psnr, mse, n_ubah, w, h, img_hist, img_noise, img_komp
            ))

        except Exception as e:
            logger.error(f"Error evaluasi: {e}", exc_info=True)
            self.after(0, lambda msg=str(e): self._on_gagal(msg))

    # ── Render matplotlib → CTkImage ─────────────────────────────────────────

    def _render_histogram(
        self,
        arr_cv: np.ndarray,
        arr_st: np.ndarray,
        w: int, h: int,
    ) -> ctk.CTkImage:
        
        fig, axes = plt.subplots(1, 3, figsize=(w / 96, h / 96), facecolor="#0d1117")
        bins = np.arange(257)
        warna = [("#e05c5c", "#e0a0a0"), ("#5cb85c", "#a0e0a0"), ("#5c8fe0", "#a0c0f0")]
        nama  = ["R (Red)", "G (Green)", "B (Blue)"]

        for i, (ax, nm, (wc, ws)) in enumerate(zip(axes, nama, warna)):
            fc, _ = np.histogram(arr_cv[:, :, i].ravel(), bins=bins)
            fs, _ = np.histogram(arr_st[:, :, i].ravel(), bins=bins)
            ax.fill_between(bins[:-1], fc, alpha=0.55, color=wc, step="post", label="Cover")
            ax.fill_between(bins[:-1], fs, alpha=0.55, color=ws, step="post", label="Stego")
            ax.step(bins[:-1], fc, color=wc, lw=0.7, where="post")
            ax.step(bins[:-1], fs, color=ws, lw=0.7, where="post")
            _setup_ax(ax, f"Channel {nm}")
            ax.set_xlim(0, 255)
            ax.set_xlabel("Intensitas (0–255)", fontsize=7)
            ax.set_ylabel("Frekuensi", fontsize=7)
            ax.legend(fontsize=6, facecolor="#161b22", labelcolor="#e6edf3")

        fig.tight_layout(pad=1.5)
        return _fig_ke_ctk_image(fig, w, h)

    def _render_noise_map(
        self,
        arr_cv: np.ndarray,
        arr_st: np.ndarray,
        mask: np.ndarray,
        koordinat_mwc,
        w: int, h: int,
    ) -> ctk.CTkImage:
        
        n_col = 3 if koordinat_mwc else 2
        fig, axes = plt.subplots(1, n_col, figsize=(w / 96, h / 96), facecolor="#0d1117")
        if n_col == 2:
            axes = list(axes)

        # Noise map binary
        axes[0].imshow(mask.astype(np.uint8) * 255, cmap="gray", aspect="auto")
        axes[0].set_title("Noise Map Binary\n(Putih = Berubah)",
                          color="#e6edf3", fontsize=8, fontweight="bold")
        axes[0].axis("off")

        # Overlay teal
        overlay = arr_cv.copy()
        overlay[mask, 0] = 0; overlay[mask, 1] = 212; overlay[mask, 2] = 170
        axes[1].imshow(overlay, aspect="auto")
        axes[1].set_title("Overlay (Teal = Dimodifikasi LSB)",
                          color="#00d4aa", fontsize=8, fontweight="bold")
        axes[1].axis("off")

        # Scatter MWC
        if koordinat_mwc and n_col == 3:
            xs = [x for x, y in koordinat_mwc]
            ys = [y for x, y in koordinat_mwc]
            axes[2].scatter(xs, ys, s=0.3, alpha=0.35, color="#f85149", linewidths=0)
            _setup_ax(axes[2], f"Scatter Koordinat MWC\n({len(koordinat_mwc):,} titik)")
            h_img, w_img = arr_cv.shape[:2]
            axes[2].set_xlim(0, w_img); axes[2].set_ylim(h_img, 0)
            axes[2].set_xlabel("X (kolom)", fontsize=7)
            axes[2].set_ylabel("Y (baris)", fontsize=7)

        fig.tight_layout(pad=1.0)
        return _fig_ke_ctk_image(fig, w, h)

    def _render_komparasi(
        self,
        arr_cv: np.ndarray,
        arr_st: np.ndarray,
        psnr: float,
        mse: float,
        w: int, h: int,
    ) -> ctk.CTkImage:
        
        fig, axes = plt.subplots(1, 2, figsize=(w / 96, h / 96), facecolor="#0d1117")

        axes[0].imshow(arr_cv); axes[0].axis("off")
        axes[0].set_title("Citra Cover (Asli)", color="#00d4aa", fontsize=9, fontweight="bold")

        axes[1].imshow(arr_st); axes[1].axis("off")
        psnr_lbl = f"{psnr:.4f} dB" if psnr != float("inf") else "∞ dB"
        axes[1].set_title(f"Citra Stego | PSNR={psnr_lbl} | MSE={mse:.4f}",
                          color="#fbbf24", fontsize=9, fontweight="bold")

        fig.tight_layout(pad=0.8)
        return _fig_ke_ctk_image(fig, w, h)

    # ── Update UI setelah render ──────────────────────────────────────────────

    def _on_sukses(
        self,
        psnr: float, mse: float,
        n_ubah: int, w: int, h: int,
        img_hist: ctk.CTkImage,
        img_noise: ctk.CTkImage,
        img_komp: ctk.CTkImage,
    ) -> None:
        self._set_loading(False)

        # Update metrik
        psnr_str = f"{psnr:.4f} dB" if psnr != float("inf") else "∞ dB (identik)"
        persen   = (n_ubah / (w * h)) * 100

        if psnr == float("inf") or psnr >= 50:
            kualitas, wk = "Sangat Baik (> 50 dB)", T.AKSEN_SUKSES
        elif psnr >= 40:
            kualitas, wk = "Baik (40–50 dB)", T.AKSEN_PRIMER
        elif psnr >= 30:
            kualitas, wk = "Cukup (30–40 dB)", T.AKSEN_WARNING
        else:
            kualitas, wk = "Buruk (< 30 dB)", T.AKSEN_DANGER

        self._metrik["psnr"].configure(text=psnr_str, text_color=T.AKSEN_PRIMER)
        self._metrik["mse"].configure(text=f"{mse:.6f}", text_color=T.TEKS_PRIMER)
        self._metrik["dimensi"].configure(text=f"{w} × {h} piksel")
        self._metrik["berubah"].configure(text=f"{n_ubah:,} piksel", text_color=T.AKSEN_WARNING)
        self._metrik["persentase"].configure(text=f"{persen:.4f}%")
        self._metrik["kualitas"].configure(text=kualitas, text_color=wk)
        self._lbl_status.configure(text="✓  Evaluasi selesai!", text_color=T.AKSEN_SUKSES)

        # ── Tampilkan gambar di tab masing-masing ─────────────────────────────
        # Simpan referensi agar tidak di-garbage collect
        self._img_histogram = img_hist
        self._img_noise_map = img_noise
        self._img_komparasi = img_komp

        # Update label di setiap tab dengan CTkImage
        self._lbl_tab["Histogram RGB"].configure(
            image=img_hist, text="", fg_color="transparent"
        )
        self._lbl_tab["Noise Map"].configure(
            image=img_noise, text="", fg_color="transparent"
        )
        self._lbl_tab["Komparasi Visual"].configure(
            image=img_komp, text="", fg_color="transparent"
        )

    def _on_gagal(self, msg: str) -> None:
        self._set_loading(False)
        self._lbl_status.configure(text=f"✕  {msg[:80]}", text_color=T.AKSEN_DANGER)
        messagebox.showerror("Evaluasi Gagal", msg)

    def _set_loading(self, aktif: bool) -> None:
        self._sedang_proses = aktif
        if aktif:
            self._btn_eval.configure(text="  ⏳  Mengevaluasi...",
                                      state="disabled", fg_color=T.TEKS_DISABLED)
            self._progress.pack(fill="x", pady=(4, 2))
            self._progress.start()
            self._lbl_status.configure(text="Menghitung metrik & merender grafik...",
                                        text_color=T.TEKS_SEKUNDER)
        else:
            self._btn_eval.configure(text="  ▶  Mulai Evaluasi",
                                      state="normal", fg_color="#fbbf24")
            self._progress.stop()
            self._progress.pack_forget()

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass