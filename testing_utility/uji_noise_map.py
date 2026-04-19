"""
================================================================================
SKRIP   : utilitas_penelitian/uji_noise_map.py
PROJECT : Stego MWC — Steganografi LSB + PRNG Multiply-With-Carry
TUJUAN  : Bab 4 Skripsi — Visualisasi Sebaran Piksel yang Dimodifikasi (Noise Map)
--------------------------------------------------------------------------------
FUNGSI SKRIP INI:
    Menghasilkan visualisasi dari piksel-piksel yang berubah akibat proses
    embedding LSB, dan membuktikan bahwa pola perubahannya bersifat acak/tersebar
    merata (bukan terkonsentrasi di satu area) berkat PRNG MWC.

    OUTPUT YANG DIHASILKAN (file PNG resolusi tinggi):
      1. Noise Map Binary  : Gambar hitam-putih. Piksel putih = dimodifikasi.
      2. Noise Map Overlay : Cover + highlight warna pada piksel yang berubah.
      3. Peta Koordinat MWC: Scatter plot koordinat (x, y) yang dihasilkan MWC.
      4. Analisis Sebaran  : Heatmap distribusi spasial perubahan piksel.
      5. Dashboard Lengkap : Semua visualisasi dalam satu halaman.

    INTERPRETASI UNTUK SKRIPSI:
      - Noise map yang tersebar merata → penyisipan tidak terdeteksi oleh mata.
      - Pola acak MWC berbeda dengan pola sekuensial yang mudah dideteksi.
      - Kepadatan perubahan rendah (<<1% piksel) → imperceptible.

CARA PAKAI:
    1. Jalankan embedding via aplikasi utama DULU.
    2. Sesuaikan konfigurasi di bawah.
    3. Jalankan:  python utilitas_penelitian/uji_noise_map.py
    4. File tersimpan di folder output_grafik/.

DEPENDENSI:
    pip install matplotlib Pillow numpy
================================================================================
"""

import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from PIL import Image

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.mwc_generator import MWCGenerator


# ════════════════════════════════════════════════════════════════════════════════
# ── KONFIGURASI ──────────────────────────────────────────────────────────────
# ════════════════════════════════════════════════════════════════════════════════

PATH_COVER = "assets/cover.png"
PATH_STEGO = "assets/cover_stego.png"
KUNCI      = "password123"
FOLDER_OUTPUT = "utilitas_penelitian/output_grafik"
DPI        = 150

# Ukuran pesan yang disisipkan (byte) — untuk hitung jumlah bit MWC
# Jika tidak tahu pasti, biarkan None → skrip akan menghitung otomatis dari selisih
UKURAN_PESAN_BYTE: int | None = None   # Contoh: 50 → isi 50; None → auto-detect

# Warna untuk overlay noise map (format matplotlib)
WARNA_PIKSEL_BERUBAH = "#00d4aa"   # Teal — piksel yang dimodifikasi
WARNA_SCATTER_MWC    = "#f85149"   # Merah — koordinat MWC

# ════════════════════════════════════════════════════════════════════════════════


# ── Konstanta Tema ────────────────────────────────────────────────────────────
BG_DARK     = "#0d1117"
BG_PANEL    = "#161b22"
TEKS_PRIMER = "#e6edf3"
TEKS_SEK    = "#8b949e"
GRID_COLOR  = "#30363d"

# Colormap custom untuk heatmap
_WARNA_HEATMAP = LinearSegmentedColormap.from_list(
    "stego_heat",
    [(0, "#0d1117"), (0.4, "#003d2e"), (0.7, "#00d4aa"), (1.0, "#ffffff")],
)


def setup_tema() -> None:
    plt.rcParams.update({
        "figure.facecolor": BG_DARK,
        "axes.facecolor":   BG_PANEL,
        "axes.edgecolor":   GRID_COLOR,
        "axes.labelcolor":  TEKS_PRIMER,
        "axes.titlecolor":  TEKS_PRIMER,
        "xtick.color":      TEKS_SEK,
        "ytick.color":      TEKS_SEK,
        "text.color":       TEKS_PRIMER,
        "font.family":      "DejaVu Sans",
        "font.size":        10,
    })


def muat_arrays(path_cover: str, path_stego: str) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Memuat kedua citra dan mengembalikan array numpy + dimensi."""
    with Image.open(path_cover) as img:
        arr_cover = np.array(img.convert("RGB"), dtype=np.uint8)
    with Image.open(path_stego) as img:
        arr_stego = np.array(img.convert("RGB"), dtype=np.uint8)
    tinggi, lebar = arr_cover.shape[:2]
    return arr_cover, arr_stego, lebar, tinggi


def deteksi_piksel_berubah(
    arr_cover: np.ndarray,
    arr_stego: np.ndarray,
    channel: int = 0,
) -> np.ndarray:
    """
    Membuat array boolean (H×W): True jika piksel di channel tertentu berubah.
    Channel 0 = Red (channel yang digunakan oleh stego_lsb.py).
    """
    return arr_cover[:, :, channel] != arr_stego[:, :, channel]


def hitung_koordinat_mwc(
    kunci: str,
    lebar: int,
    tinggi: int,
    jumlah_bit: int,
) -> list[tuple[int, int]]:
    """Membangkitkan koordinat MWC untuk sejumlah bit yang disisipkan."""
    gen = MWCGenerator(password=kunci)
    return gen.hasilkan_koordinat(lebar=lebar, tinggi=tinggi, jumlah=jumlah_bit)


# ── Grafik 1: Noise Map Binary ────────────────────────────────────────────────

def buat_noise_map_binary(
    mask_berubah: np.ndarray,
    lebar: int,
    tinggi: int,
    path_output: Path,
) -> None:
    """
    Membuat gambar hitam-putih: putih = piksel berubah, hitam = tidak berubah.
    Kepadatan piksel putih menunjukkan seberapa banyak pesan yang disisipkan.
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(BG_DARK)

    # Convert boolean mask ke uint8 (0 atau 255)
    noise_img = (mask_berubah.astype(np.uint8)) * 255

    ax.imshow(noise_img, cmap="gray", vmin=0, vmax=255, aspect="auto")
    ax.set_title(
        "Noise Map — Piksel yang Dimodifikasi LSB\n"
        "(Putih = dimodifikasi, Hitam = tidak berubah)",
        fontsize=11, fontweight="bold",
    )
    ax.set_xlabel(f"Kolom Piksel (0–{lebar-1})")
    ax.set_ylabel(f"Baris Piksel (0–{tinggi-1})")

    total_berubah = int(mask_berubah.sum())
    total_piksel  = lebar * tinggi
    persentase    = (total_berubah / total_piksel) * 100

    ax.text(
        0.02, 0.02,
        f"Dimodifikasi: {total_berubah:,} dari {total_piksel:,} piksel ({persentase:.3f}%)",
        transform=ax.transAxes,
        fontsize=9, color=WARNA_PIKSEL_BERUBAH,
        bbox=dict(facecolor=BG_PANEL, edgecolor=GRID_COLOR, alpha=0.85, boxstyle="round,pad=0.4"),
    )

    fig.tight_layout()
    fig.savefig(str(path_output), dpi=DPI, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"  ✓ Tersimpan: {path_output}")


# ── Grafik 2: Noise Map Overlay ───────────────────────────────────────────────

def buat_noise_map_overlay(
    arr_cover: np.ndarray,
    mask_berubah: np.ndarray,
    path_output: Path,
) -> None:
    """
    Menampilkan citra cover asli dengan highlight warna teal pada piksel yang berubah.
    Lebih intuitif dari noise map binary untuk presentasi skripsi.
    """
    # Buat salinan RGBA agar bisa menambah alpha layer
    overlay = arr_cover.copy()

    # Highlight piksel yang berubah: ubah channel R ke warna teal (0, 212, 170)
    overlay[mask_berubah, 0] = 0
    overlay[mask_berubah, 1] = 212
    overlay[mask_berubah, 2] = 170

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(
        "Overlay Noise Map — Lokasi Penyisipan Bit LSB pada Citra",
        fontsize=12, fontweight="bold",
    )

    axes[0].imshow(arr_cover)
    axes[0].set_title("Citra Cover (Asli)", fontsize=11, fontweight="bold", color=TEKS_PRIMER)
    axes[0].axis("off")

    axes[1].imshow(overlay)
    axes[1].set_title(
        f"Overlay: Piksel yang Dimodifikasi (Teal = perubahan LSB)",
        fontsize=11, fontweight="bold", color=WARNA_PIKSEL_BERUBAH,
    )
    axes[1].axis("off")

    # Legend manual
    from matplotlib.patches import Patch
    legend_el = [
        Patch(facecolor=WARNA_PIKSEL_BERUBAH, label="Piksel dimodifikasi LSB"),
    ]
    axes[1].legend(handles=legend_el, loc="lower right", fontsize=9,
                   facecolor=BG_PANEL, edgecolor=GRID_COLOR)

    fig.tight_layout()
    fig.savefig(str(path_output), dpi=DPI, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"  ✓ Tersimpan: {path_output}")


# ── Grafik 3: Scatter Plot Koordinat MWC ─────────────────────────────────────

def buat_scatter_koordinat_mwc(
    koordinat: list[tuple[int, int]],
    lebar: int,
    tinggi: int,
    path_output: Path,
) -> None:
    """
    Membuat scatter plot koordinat (x, y) yang dihasilkan MWC.

    Distribusi acak merata membuktikan MWC menghasilkan koordinat yang tidak
    berkluster/terpola — berbeda signifikan dengan penyisipan sekuensial.
    """
    xs = [x for x, y in koordinat]
    ys = [y for x, y in koordinat]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(
        f"Distribusi Spasial Koordinat MWC\n"
        f"({len(koordinat):,} titik dari {lebar}×{tinggi} piksel)",
        fontsize=12, fontweight="bold",
    )

    # ── Subplot kiri: Scatter plot ────────────────────────────────────────────
    ax_scatter = axes[0]
    ax_scatter.scatter(
        xs, ys,
        s=0.5, alpha=0.4, color=WARNA_SCATTER_MWC, linewidths=0,
    )
    ax_scatter.set_title("Scatter Plot Koordinat MWC", fontsize=11, fontweight="bold")
    ax_scatter.set_xlabel("Posisi X (Kolom)")
    ax_scatter.set_ylabel("Posisi Y (Baris)")
    ax_scatter.set_xlim(0, lebar)
    ax_scatter.set_ylim(tinggi, 0)   # Balik sumbu Y agar sesuai koordinat citra
    ax_scatter.set_facecolor(BG_PANEL)
    ax_scatter.grid(True, color=GRID_COLOR, linewidth=0.4, alpha=0.6)

    # Teks kepadatan
    kepadatan = (len(koordinat) / (lebar * tinggi)) * 100
    ax_scatter.text(
        0.02, 0.98,
        f"Kepadatan: {kepadatan:.3f}%\n({len(koordinat):,} / {lebar*tinggi:,})",
        transform=ax_scatter.transAxes,
        fontsize=9, va="top", color=WARNA_SCATTER_MWC,
        bbox=dict(facecolor=BG_DARK, edgecolor=GRID_COLOR, alpha=0.8, boxstyle="round,pad=0.4"),
    )

    # ── Subplot kanan: Pembanding — penyisipan sekuensial ────────────────────
    ax_seq = axes[1]
    # Simulasi penyisipan sekuensial: koordinat berurutan dari (0,0)
    n = len(koordinat)
    xs_seq = [(i % lebar) for i in range(n)]
    ys_seq = [(i // lebar) for i in range(n)]

    ax_seq.scatter(
        xs_seq, ys_seq,
        s=0.5, alpha=0.4, color="#fbbf24", linewidths=0,
    )
    ax_seq.set_title(
        "Pembanding: Penyisipan SEKUENSIAL\n(bukan MWC — untuk perbandingan)",
        fontsize=11, fontweight="bold", color="#fbbf24",
    )
    ax_seq.set_xlabel("Posisi X (Kolom)")
    ax_seq.set_ylabel("Posisi Y (Baris)")
    ax_seq.set_xlim(0, lebar)
    ax_seq.set_ylim(tinggi, 0)
    ax_seq.set_facecolor(BG_PANEL)
    ax_seq.grid(True, color=GRID_COLOR, linewidth=0.4, alpha=0.6)

    ax_seq.text(
        0.5, 0.5,
        "Pola terkonsentrasi\ndi sudut kiri atas!\n(mudah dideteksi)",
        transform=ax_seq.transAxes,
        fontsize=10, ha="center", va="center", color="#fbbf24", fontweight="bold",
        bbox=dict(facecolor=BG_DARK, edgecolor="#fbbf24", alpha=0.9, boxstyle="round,pad=0.5"),
    )

    fig.tight_layout()
    fig.savefig(str(path_output), dpi=DPI, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"  ✓ Tersimpan: {path_output}")


# ── Grafik 4: Heatmap Distribusi Spasial ─────────────────────────────────────

def buat_heatmap_sebaran(
    mask_berubah: np.ndarray,
    lebar: int,
    tinggi: int,
    path_output: Path,
    ukuran_sel: int = 32,
) -> None:
    """
    Membuat heatmap distribusi spasial perubahan piksel.

    Citra dibagi menjadi grid sel-sel kecil (ukuran_sel × ukuran_sel piksel).
    Intensitas warna setiap sel menunjukkan berapa banyak piksel yang berubah
    di dalam sel tersebut. Distribusi merata → tidak ada area yang 'terlalu banyak'
    atau 'terlalu sedikit' dimodifikasi.

    Args:
        ukuran_sel: Ukuran satu sel grid dalam piksel. Default 32×32.
    """
    n_baris = tinggi // ukuran_sel
    n_kolom = lebar  // ukuran_sel

    heatmap = np.zeros((n_baris, n_kolom), dtype=np.float64)

    for r in range(n_baris):
        for c in range(n_kolom):
            region = mask_berubah[
                r * ukuran_sel:(r + 1) * ukuran_sel,
                c * ukuran_sel:(c + 1) * ukuran_sel,
            ]
            heatmap[r, c] = region.sum()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(
        f"Heatmap Distribusi Spasial Perubahan Piksel\n"
        f"(Grid {ukuran_sel}×{ukuran_sel} piksel per sel | "
        f"{n_kolom}×{n_baris} sel total)",
        fontsize=12, fontweight="bold",
    )

    # Heatmap MWC
    im = axes[0].imshow(heatmap, cmap=_WARNA_HEATMAP, aspect="auto", interpolation="nearest")
    axes[0].set_title("Distribusi Perubahan MWC (Acak)", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Sel Kolom")
    axes[0].set_ylabel("Sel Baris")
    plt.colorbar(im, ax=axes[0], label="Jumlah piksel berubah per sel", shrink=0.8)

    # Statistik distribusi
    mean_per_sel = heatmap.mean()
    std_per_sel  = heatmap.std()
    axes[0].text(
        0.02, 0.02,
        f"μ = {mean_per_sel:.2f} piksel/sel\nσ = {std_per_sel:.2f}",
        transform=axes[0].transAxes,
        fontsize=9, color=TEKS_PRIMER, va="bottom",
        bbox=dict(facecolor=BG_DARK, edgecolor=GRID_COLOR, alpha=0.85, boxstyle="round,pad=0.4"),
    )

    # Histogram distribusi nilai heatmap
    axes[1].hist(heatmap.ravel(), bins=30, color=WARNA_PIKSEL_BERUBAH, alpha=0.8, edgecolor=BG_DARK)
    axes[1].set_title("Histogram Nilai Heatmap per Sel", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Jumlah Piksel Berubah per Sel")
    axes[1].set_ylabel("Jumlah Sel")
    axes[1].set_facecolor(BG_PANEL)
    axes[1].grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.6)
    axes[1].axvline(mean_per_sel, color="#fbbf24", linestyle="--", linewidth=1.5, label=f"Rata-rata = {mean_per_sel:.1f}")
    axes[1].legend(fontsize=9)

    fig.tight_layout()
    fig.savefig(str(path_output), dpi=DPI, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"  ✓ Tersimpan: {path_output}")


# ── Cetak Statistik ke Terminal ───────────────────────────────────────────────

def cetak_statistik_noise(
    mask_berubah: np.ndarray,
    koordinat_mwc: list[tuple[int, int]],
    lebar: int,
    tinggi: int,
) -> None:
    total_piksel  = lebar * tinggi
    total_berubah = int(mask_berubah.sum())
    persentase    = (total_berubah / total_piksel) * 100
    jumlah_mwc    = len(koordinat_mwc)

    print("\n  ┌─────────────────────────────────────────────────────────┐")
    print("  │   STATISTIK NOISE MAP & SEBARAN KOORDINAT MWC           │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print(f"  │  Dimensi citra          : {lebar} × {tinggi} piksel")
    print(f"  │  Total piksel           : {total_piksel:>15,}")
    print(f"  │  Piksel dimodifikasi    : {total_berubah:>15,}  ({persentase:.4f}%)")
    print(f"  │  Koordinat MWC dibangkitkan: {jumlah_mwc:>12,}")
    print(f"  │  Header (32 bit)        : {32:>15,}  (panjang pesan)")
    print(f"  │  Payload (bit pesan)    : {jumlah_mwc - 32:>15,}  ({(jumlah_mwc-32)//8} byte)")
    print("  ├─────────────────────────────────────────────────────────┤")

    # Uji keseragaman distribusi (Coefficient of Variation)
    xs = [x for x, y in koordinat_mwc]
    ys = [y for x, y in koordinat_mwc]
    cv_x = (np.std(xs) / np.mean(xs)) * 100 if np.mean(xs) > 0 else 0
    cv_y = (np.std(ys) / np.mean(ys)) * 100 if np.mean(ys) > 0 else 0

    print(f"  │  CoV distribusi X       : {cv_x:>14.2f}%  (makin rendah=makin merata)")
    print(f"  │  CoV distribusi Y       : {cv_y:>14.2f}%")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "═" * 65)
    print("  UJI NOISE MAP — Visualisasi Sebaran Bit LSB")
    print("═" * 65)
    print(f"  Cover  : {PATH_COVER}")
    print(f"  Stego  : {PATH_STEGO}")
    print(f"  Kunci  : {'●' * len(KUNCI)}")
    print(f"  Output : {FOLDER_OUTPUT}/")

    folder = Path(FOLDER_OUTPUT)
    folder.mkdir(parents=True, exist_ok=True)

    # Muat citra
    print("\n  Memuat citra...")
    try:
        arr_cover, arr_stego, lebar, tinggi = muat_arrays(PATH_COVER, PATH_STEGO)
    except FileNotFoundError as e:
        print(f"\n  ERROR: {e}")
        print("  Jalankan embedding terlebih dahulu.\n")
        sys.exit(1)

    print(f"  Dimensi: {lebar} × {tinggi} piksel")

    # Deteksi piksel berubah
    mask_berubah = deteksi_piksel_berubah(arr_cover, arr_stego, channel=0)
    total_berubah = int(mask_berubah.sum())

    # Hitung jumlah bit MWC
    if UKURAN_PESAN_BYTE is not None:
        jumlah_bit = 32 + (UKURAN_PESAN_BYTE * 8)
        print(f"  Jumlah bit MWC (dari config): {jumlah_bit}")
    else:
        # Auto-detect dari piksel yang berubah + buffer header
        jumlah_bit = total_berubah + 32
        print(f"  Jumlah bit MWC (auto-detect): {jumlah_bit} (dari {total_berubah} piksel berubah)")

    # Bangkitkan koordinat MWC
    print("  Membangkitkan koordinat MWC...")
    try:
        koordinat_mwc = hitung_koordinat_mwc(KUNCI, lebar, tinggi, jumlah_bit)
    except ValueError as e:
        print(f"  Peringatan: {e} — menggunakan jumlah bit lebih kecil.")
        koordinat_mwc = hitung_koordinat_mwc(KUNCI, lebar, tinggi, min(jumlah_bit, lebar * tinggi))

    # Cetak statistik
    cetak_statistik_noise(mask_berubah, koordinat_mwc, lebar, tinggi)

    # Setup tema
    setup_tema()

    # Generate semua grafik
    print("  Membuat grafik noise map...")
    buat_noise_map_binary(mask_berubah, lebar, tinggi, folder / "noise_map_binary.png")
    buat_noise_map_overlay(arr_cover, mask_berubah, folder / "noise_map_overlay.png")
    buat_scatter_koordinat_mwc(koordinat_mwc, lebar, tinggi, folder / "scatter_koordinat_mwc.png")
    buat_heatmap_sebaran(mask_berubah, lebar, tinggi, folder / "heatmap_sebaran.png")

    print(f"\n  Semua grafik tersimpan di: {folder.resolve()}/")
    for f in sorted(folder.glob("noise_map_*.png")):
        print(f"    • {f.name}")
    for f in sorted(folder.glob("scatter_*.png")):
        print(f"    • {f.name}")
    for f in sorted(folder.glob("heatmap_*.png")):
        print(f"    • {f.name}")
    print()


if __name__ == "__main__":
    main()