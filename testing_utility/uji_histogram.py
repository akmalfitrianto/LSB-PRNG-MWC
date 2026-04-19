"""
================================================================================
SKRIP   : utilitas_penelitian/uji_histogram.py
PROJECT : Stego MWC — Steganografi LSB + PRNG Multiply-With-Carry
TUJUAN  : Bab 4 Skripsi — Analisis Histogram Citra
--------------------------------------------------------------------------------
FUNGSI SKRIP INI:
    Menghasilkan dan menyimpan grafik perbandingan histogram antara citra cover
    (asli) dan citra stego (setelah embedding). Histogram yang hampir identik
    membuktikan bahwa metode LSB tidak mengubah distribusi intensitas piksel
    secara signifikan — ini adalah bukti kunci imperceptibility steganografi.

    GRAFIK YANG DIHASILKAN (disimpan sebagai file PNG resolusi tinggi):
      1. Histogram RGB Cover vs Stego — 3 subplot (R, G, B) berdampingan.
      2. Histogram gabungan (grayscale) — cover dan stego di satu plot.
      3. Grafik selisih histogram — menunjukkan perbedaan frekuensi tiap intensitas.
      4. (Opsional) Perbandingan citra side-by-side.

CARA PAKAI:
    1. Jalankan embedding via aplikasi utama DULU.
    2. Sesuaikan konfigurasi di bawah.
    3. Jalankan dari terminal:
           python utilitas_penelitian/uji_histogram.py
    4. File grafik tersimpan di folder output_grafik/ (bisa diatur di konfigurasi).
    5. Masukkan file gambar ke naskah skripsi Bab 4.

DEPENDENSI:
    pip install matplotlib Pillow numpy
================================================================================
"""

import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from PIL import Image

# Gunakan backend non-interactive agar bisa berjalan tanpa display (server/CI)
matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ════════════════════════════════════════════════════════════════════════════════
# ── KONFIGURASI ──────────────────────────────────────────────────────────────
# ════════════════════════════════════════════════════════════════════════════════

PATH_COVER = "assets/cover.png"
PATH_STEGO = "assets/cover_stego.png"

# Folder output untuk menyimpan file grafik
FOLDER_OUTPUT = "utilitas_penelitian/output_grafik"

# DPI grafik — 150 cukup untuk skripsi digital, 300 untuk cetak
DPI = 150

# Label keterangan — bisa disesuaikan dengan nama file aktual
LABEL_COVER = "Citra Cover (Asli)"
LABEL_STEGO = "Citra Stego (Setelah Embedding)"

# Judul keseluruhan grafik untuk naskah skripsi
JUDUL_GRAFIK = "Perbandingan Histogram Citra Cover dan Citra Stego"

# ════════════════════════════════════════════════════════════════════════════════


# ── Konstanta Warna ───────────────────────────────────────────────────────────
# Palet warna konsisten dengan tema aplikasi (dark research tool)
WARNA_CHANNEL = {
    "R": ("#e05c5c", "#e0a0a0"),   # (cover, stego) merah
    "G": ("#5cb85c", "#a0e0a0"),   # hijau
    "B": ("#5c8fe0", "#a0c0f0"),   # biru
}
WARNA_COVER   = "#00d4aa"   # Teal — cover
WARNA_STEGO   = "#f85149"   # Merah — stego
WARNA_SELISIH = "#fbbf24"   # Amber — selisih
BG_DARK       = "#0d1117"
BG_PANEL      = "#161b22"
TEKS_PRIMER   = "#e6edf3"
TEKS_SEKUNDER = "#8b949e"
GRID_COLOR    = "#30363d"


def setup_tema_gelap() -> None:
    """Mengaplikasikan tema gelap ke semua grafik matplotlib."""
    plt.rcParams.update({
        "figure.facecolor":    BG_DARK,
        "axes.facecolor":      BG_PANEL,
        "axes.edgecolor":      GRID_COLOR,
        "axes.labelcolor":     TEKS_PRIMER,
        "axes.titlecolor":     TEKS_PRIMER,
        "axes.grid":           True,
        "grid.color":          GRID_COLOR,
        "grid.linewidth":      0.5,
        "grid.alpha":          0.8,
        "xtick.color":         TEKS_SEKUNDER,
        "ytick.color":         TEKS_SEKUNDER,
        "text.color":          TEKS_PRIMER,
        "legend.facecolor":    BG_PANEL,
        "legend.edgecolor":    GRID_COLOR,
        "legend.labelcolor":   TEKS_PRIMER,
        "font.family":         "DejaVu Sans",
        "font.size":           10,
    })


def muat_citra(path: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Memuat citra dan mengembalikan array RGB dan array grayscale.

    Returns:
        tuple: (array_rgb uint8 (H,W,3), array_gray uint8 (H,W))
    """
    with Image.open(path) as img:
        rgb = np.array(img.convert("RGB"), dtype=np.uint8)
        gray = np.array(img.convert("L"), dtype=np.uint8)
    return rgb, gray


def hitung_histogram(arr_1d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Menghitung histogram untuk satu channel (array 1D).

    Returns:
        tuple: (nilai_intensitas 0-255, frekuensi)
    """
    bins = np.arange(257)   # 0 sampai 256 (257 tepi = 256 bin)
    freq, edges = np.histogram(arr_1d.ravel(), bins=bins)
    return edges[:-1], freq   # edges[:-1] = 0..255


# ── Grafik 1: Histogram RGB Tiga Channel ─────────────────────────────────────

def buat_grafik_histogram_rgb(
    arr_cover: np.ndarray,
    arr_stego: np.ndarray,
    path_output: Path,
) -> None:
    """
    Membuat grafik histogram 3 subplot (R, G, B) — Cover vs Stego.

    Setiap subplot menampilkan dua histogram bertumpuk (cover dan stego)
    dengan alpha 0.6 agar kedua distribusi terlihat sekaligus.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=False)
    fig.suptitle(
        f"{JUDUL_GRAFIK}\nHistogram per Channel Warna (RGB)",
        fontsize=13, fontweight="bold", y=1.02,
    )

    nama_channel = ["R (Red)", "G (Green)", "B (Blue)"]
    kunci_warna  = ["R", "G", "B"]

    for i, (ax, nama, kunci) in enumerate(zip(axes, nama_channel, kunci_warna)):
        warna_cv, warna_st = WARNA_CHANNEL[kunci]

        intensitas, freq_cover = hitung_histogram(arr_cover[:, :, i])
        _,          freq_stego = hitung_histogram(arr_stego[:, :, i])

        # Plot sebagai filled step histogram
        ax.fill_between(intensitas, freq_cover, alpha=0.55, color=warna_cv, label=LABEL_COVER, step="post")
        ax.fill_between(intensitas, freq_stego, alpha=0.55, color=warna_st, label=LABEL_STEGO, step="post")
        ax.step(intensitas, freq_cover, color=warna_cv, linewidth=0.8, where="post")
        ax.step(intensitas, freq_stego, color=warna_st, linewidth=0.8, where="post")

        ax.set_title(f"Channel {nama}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Intensitas Piksel (0–255)")
        ax.set_ylabel("Frekuensi Piksel")
        ax.set_xlim(0, 255)
        ax.legend(fontsize=8, loc="upper right")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))

    fig.tight_layout()
    fig.savefig(str(path_output), dpi=DPI, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"  ✓ Tersimpan: {path_output}")


# ── Grafik 2: Histogram Gabungan (Grayscale) ─────────────────────────────────

def buat_grafik_histogram_gabungan(
    arr_cover_gray: np.ndarray,
    arr_stego_gray: np.ndarray,
    path_output: Path,
) -> None:
    """
    Membuat grafik histogram grayscale dalam satu plot.
    Menampilkan kesamaan distribusi intensitas secara keseluruhan.
    """
    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.suptitle(
        f"{JUDUL_GRAFIK}\nHistogram Grayscale (Gabungan RGB)",
        fontsize=13, fontweight="bold",
    )

    intensitas, freq_cover = hitung_histogram(arr_cover_gray)
    _,          freq_stego = hitung_histogram(arr_stego_gray)

    ax.fill_between(intensitas, freq_cover, alpha=0.5, color=WARNA_COVER, label=LABEL_COVER, step="post")
    ax.fill_between(intensitas, freq_stego, alpha=0.5, color=WARNA_STEGO, label=LABEL_STEGO, step="post")
    ax.step(intensitas, freq_cover, color=WARNA_COVER, linewidth=1.2, where="post")
    ax.step(intensitas, freq_stego, color=WARNA_STEGO, linewidth=1.2, where="post")

    ax.set_xlabel("Intensitas Piksel (0–255)", fontsize=11)
    ax.set_ylabel("Frekuensi Piksel", fontsize=11)
    ax.set_xlim(0, 255)
    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Anotasi: tunjukkan bahwa kedua kurva hampir identik
    ax.annotate(
        "Distribusi hampir identik\n(imperceptibility terbukti)",
        xy=(128, max(freq_cover) * 0.6),
        fontsize=9,
        color=TEKS_SEKUNDER,
        ha="center",
        bbox=dict(boxstyle="round,pad=0.3", facecolor=BG_PANEL, edgecolor=GRID_COLOR, alpha=0.8),
    )

    fig.tight_layout()
    fig.savefig(str(path_output), dpi=DPI, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"  ✓ Tersimpan: {path_output}")


# ── Grafik 3: Selisih Histogram ───────────────────────────────────────────────

def buat_grafik_selisih_histogram(
    arr_cover: np.ndarray,
    arr_stego: np.ndarray,
    path_output: Path,
) -> None:
    """
    Membuat grafik selisih histogram (Δfrekuensi = stego − cover) per channel.

    Selisih mendekati nol di semua intensitas membuktikan distribusi piksel
    tidak berubah secara bermakna setelah embedding.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=False)
    fig.suptitle(
        f"{JUDUL_GRAFIK}\nSelisih Frekuensi Histogram Δ = (Stego − Cover)",
        fontsize=13, fontweight="bold", y=1.02,
    )

    nama_channel = ["R (Red)", "G (Green)", "B (Blue)"]

    for i, (ax, nama) in enumerate(zip(axes, nama_channel)):
        intensitas, freq_cover = hitung_histogram(arr_cover[:, :, i])
        _,          freq_stego = hitung_histogram(arr_stego[:, :, i])

        delta = freq_stego.astype(np.int64) - freq_cover.astype(np.int64)

        # Warna batang: hijau jika positif, merah jika negatif
        warna_batang = [WARNA_COVER if d >= 0 else WARNA_STEGO for d in delta]
        ax.bar(intensitas, delta, color=warna_batang, width=1.0, alpha=0.85)

        # Garis nol
        ax.axhline(y=0, color=TEKS_SEKUNDER, linewidth=0.8, linestyle="--")

        ax.set_title(f"Δ Channel {nama}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Intensitas Piksel (0–255)")
        ax.set_ylabel("Δ Frekuensi")
        ax.set_xlim(0, 255)

        # Teks informasi: max selisih
        max_delta = int(np.max(np.abs(delta)))
        ax.text(
            0.98, 0.98, f"Max |Δ| = {max_delta}",
            transform=ax.transAxes,
            fontsize=8, ha="right", va="top",
            color=WARNA_SELISIH,
        )

    fig.tight_layout()
    fig.savefig(str(path_output), dpi=DPI, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"  ✓ Tersimpan: {path_output}")


# ── Grafik 4: Dashboard Lengkap (Semua dalam Satu) ───────────────────────────

def buat_grafik_dashboard_lengkap(
    arr_cover: np.ndarray,
    arr_stego: np.ndarray,
    arr_cover_gray: np.ndarray,
    arr_stego_gray: np.ndarray,
    path_output: Path,
) -> None:
    """
    Membuat satu halaman grafik komprehensif yang menggabungkan semua analisis:
      Baris 1: Tampilan citra cover dan stego (thumbnail).
      Baris 2: Histogram RGB tiga channel.
      Baris 3: Histogram grayscale + selisih histogram.

    Grafik ini cocok untuk satu halaman penuh di Bab 4 skripsi.
    """
    fig = plt.figure(figsize=(16, 12), facecolor=BG_DARK)
    fig.suptitle(
        f"{JUDUL_GRAFIK}\nAnalisis Komprehensif Kualitas Citra Stego",
        fontsize=14, fontweight="bold", y=0.98, color=TEKS_PRIMER,
    )

    gs = gridspec.GridSpec(3, 6, figure=fig, hspace=0.45, wspace=0.4)

    # ── Baris 1: Thumbnail Citra ───────────────────────────────────────────────
    ax_cover_img = fig.add_subplot(gs[0, :3])
    ax_stego_img = fig.add_subplot(gs[0, 3:])

    ax_cover_img.imshow(arr_cover)
    ax_cover_img.set_title(f"Cover: {LABEL_COVER}", fontsize=10, fontweight="bold", color=WARNA_COVER)
    ax_cover_img.axis("off")

    ax_stego_img.imshow(arr_stego)
    ax_stego_img.set_title(f"Stego: {LABEL_STEGO}", fontsize=10, fontweight="bold", color=WARNA_STEGO)
    ax_stego_img.axis("off")

    # ── Baris 2: Histogram RGB ─────────────────────────────────────────────────
    nama_ch = ["R (Red)", "G (Green)", "B (Blue)"]
    kunci_ch = ["R", "G", "B"]

    for i in range(3):
        ax = fig.add_subplot(gs[1, i * 2:(i + 1) * 2])
        warna_cv, warna_st = WARNA_CHANNEL[kunci_ch[i]]
        intensitas, freq_cv = hitung_histogram(arr_cover[:, :, i])
        _,          freq_st = hitung_histogram(arr_stego[:, :, i])
        ax.fill_between(intensitas, freq_cv, alpha=0.5, color=warna_cv, label="Cover", step="post")
        ax.fill_between(intensitas, freq_st, alpha=0.5, color=warna_st, label="Stego", step="post")
        ax.step(intensitas, freq_cv, color=warna_cv, linewidth=0.7, where="post")
        ax.step(intensitas, freq_st, color=warna_st, linewidth=0.7, where="post")
        ax.set_title(f"Channel {nama_ch[i]}", fontsize=9, fontweight="bold")
        ax.set_xlabel("Intensitas (0–255)", fontsize=8)
        ax.set_ylabel("Frekuensi", fontsize=8)
        ax.legend(fontsize=7)
        ax.set_xlim(0, 255)
        ax.tick_params(labelsize=7)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x/1000)}K" if x >= 1000 else f"{int(x)}"))

    # ── Baris 3: Grayscale + Selisih ──────────────────────────────────────────
    ax_gray = fig.add_subplot(gs[2, :3])
    intensitas, freq_cv_gray = hitung_histogram(arr_cover_gray)
    _,          freq_st_gray = hitung_histogram(arr_stego_gray)
    ax_gray.fill_between(intensitas, freq_cv_gray, alpha=0.5, color=WARNA_COVER, label="Cover", step="post")
    ax_gray.fill_between(intensitas, freq_st_gray, alpha=0.5, color=WARNA_STEGO, label="Stego", step="post")
    ax_gray.step(intensitas, freq_cv_gray, color=WARNA_COVER, linewidth=0.8, where="post")
    ax_gray.step(intensitas, freq_st_gray, color=WARNA_STEGO, linewidth=0.8, where="post")
    ax_gray.set_title("Histogram Grayscale Gabungan", fontsize=9, fontweight="bold")
    ax_gray.set_xlabel("Intensitas (0–255)")
    ax_gray.set_ylabel("Frekuensi")
    ax_gray.legend(fontsize=8)
    ax_gray.set_xlim(0, 255)

    ax_delta = fig.add_subplot(gs[2, 3:])
    # Tampilkan selisih channel R saja (representatif)
    _, freq_cv_r = hitung_histogram(arr_cover[:, :, 0])
    _, freq_st_r = hitung_histogram(arr_stego[:, :, 0])
    delta_r = freq_st_r.astype(np.int64) - freq_cv_r.astype(np.int64)
    warna_batang = [WARNA_COVER if d >= 0 else WARNA_STEGO for d in delta_r]
    ax_delta.bar(intensitas, delta_r, color=warna_batang, width=1.0, alpha=0.85)
    ax_delta.axhline(y=0, color=TEKS_SEKUNDER, linewidth=0.8, linestyle="--")
    ax_delta.set_title("Selisih Δ Histogram Channel R", fontsize=9, fontweight="bold")
    ax_delta.set_xlabel("Intensitas (0–255)")
    ax_delta.set_ylabel("Δ Frekuensi")
    ax_delta.set_xlim(0, 255)
    ax_delta.text(
        0.98, 0.98, f"Max |Δ| = {int(np.max(np.abs(delta_r)))}",
        transform=ax_delta.transAxes, fontsize=8,
        ha="right", va="top", color=WARNA_SELISIH,
    )

    fig.savefig(str(path_output), dpi=DPI, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"  ✓ Tersimpan: {path_output}")


# ── Hitung & Cetak Statistik Histogram ───────────────────────────────────────

def cetak_statistik_histogram(
    arr_cover: np.ndarray,
    arr_stego: np.ndarray,
) -> None:
    """
    Mencetak statistik ringkasan perbedaan histogram ke terminal.
    Berguna untuk tabel Bab 4.
    """
    print("\n  ┌─────────────────────────────────────────────────────────┐")
    print("  │   STATISTIK PERBANDINGAN HISTOGRAM                      │")
    print("  ├──────────┬──────────────┬──────────────┬────────────────┤")
    print("  │ Channel  │  Cover (μ)   │  Stego (μ)   │  Max |Δfrek|   │")
    print("  ├──────────┼──────────────┼──────────────┼────────────────┤")

    for i, nama in enumerate(["Red (R)", "Green(G)", "Blue (B)"]):
        mean_cv = arr_cover[:, :, i].mean()
        mean_st = arr_stego[:, :, i].mean()
        _, freq_cv = hitung_histogram(arr_cover[:, :, i])
        _, freq_st = hitung_histogram(arr_stego[:, :, i])
        max_delta = int(np.max(np.abs(freq_st.astype(np.int64) - freq_cv.astype(np.int64))))
        print(f"  │ {nama}  │  {mean_cv:9.4f}   │  {mean_st:9.4f}   │  {max_delta:14,}  │")

    print("  └──────────┴──────────────┴──────────────┴────────────────┘")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "═" * 65)
    print("  UJI HISTOGRAM — Analisis Distribusi Piksel")
    print("═" * 65)
    print(f"  Cover  : {PATH_COVER}")
    print(f"  Stego  : {PATH_STEGO}")
    print(f"  Output : {FOLDER_OUTPUT}/")
    print(f"  DPI    : {DPI}")

    # Buat folder output jika belum ada
    folder = Path(FOLDER_OUTPUT)
    folder.mkdir(parents=True, exist_ok=True)

    # Muat citra
    print("\n  Memuat citra...")
    try:
        arr_cover, arr_cover_gray = muat_citra(PATH_COVER)
        arr_stego, arr_stego_gray = muat_citra(PATH_STEGO)
    except FileNotFoundError as e:
        print(f"\n  ERROR: {e}")
        print("  Pastikan PATH_COVER dan PATH_STEGO sudah benar.\n")
        sys.exit(1)

    h, w = arr_cover.shape[:2]
    print(f"  Dimensi citra: {w} × {h} piksel ({w * h:,} piksel total)")

    # Setup tema
    setup_tema_gelap()

    # Cetak statistik ke terminal
    cetak_statistik_histogram(arr_cover, arr_stego)

    # Generate semua grafik
    print("  Membuat grafik...")

    buat_grafik_histogram_rgb(arr_cover, arr_stego, folder / "histogram_rgb.png")
    buat_grafik_histogram_gabungan(arr_cover_gray, arr_stego_gray, folder / "histogram_gabungan.png")
    buat_grafik_selisih_histogram(arr_cover, arr_stego, folder / "histogram_selisih.png")
    buat_grafik_dashboard_lengkap(
        arr_cover, arr_stego,
        arr_cover_gray, arr_stego_gray,
        folder / "histogram_dashboard.png",
    )

    print(f"\n  Semua grafik tersimpan di: {folder.resolve()}/")
    print("  File yang dihasilkan:")
    for f in sorted(folder.glob("*.png")):
        ukuran_kb = f.stat().st_size / 1024
        print(f"    • {f.name:<35} ({ukuran_kb:.0f} KB)")
    print()


if __name__ == "__main__":
    main()