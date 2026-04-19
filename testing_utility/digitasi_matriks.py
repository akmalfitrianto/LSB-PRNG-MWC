import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Tambahkan root project ke sys.path agar import engine bisa berjalan
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.mwc_generator import MWCGenerator


# ════════════════════════════════════════════════════════════════════════════════
# ── KONFIGURASI — Sesuaikan nilai di bawah ini sebelum menjalankan ──────────
# ════════════════════════════════════════════════════════════════════════════════

# Path ke citra cover (asli) dan citra stego (hasil embedding)
PATH_COVER = "assets/cover.png"     # ← Ganti dengan path citra cover Anda
PATH_STEGO = "assets/cover_stego.png"  # ← Ganti dengan path citra stego Anda

# Kunci/password yang digunakan saat embedding
KUNCI = "password123"               # ← Ganti dengan kunci yang Anda gunakan

# Region piksel yang ingin ditampilkan (koordinat x,y = pojok kiri atas)
# Region kecil (8×8 atau 10×10) sudah cukup untuk dokumentasi skripsi
REGION_X_MULAI = 0    # Kolom mulai (inklusif)
REGION_Y_MULAI = 0    # Baris mulai (inklusif)
REGION_LEBAR   = 8    # Jumlah kolom yang ditampilkan
REGION_TINGGI  = 8    # Jumlah baris yang ditampilkan

# Channel yang ditampilkan: 0=Red, 1=Green, 2=Blue
CHANNEL = 0
NAMA_CHANNEL = {0: "Red (R)", 1: "Green (G)", 2: "Blue (B)"}

# ════════════════════════════════════════════════════════════════════════════════


# ── Konstanta Tampilan ────────────────────────────────────────────────────────
# Karakter ANSI escape untuk pewarnaan terminal
RESET  = "\033[0m"
MERAH  = "\033[91m"    # Piksel yang berubah (dimodifikasi LSB)
HIJAU  = "\033[92m"    # Nilai yang sama / tidak berubah
KUNING = "\033[93m"    # Selisih piksel
BIRU   = "\033[94m"    # Header / label
TEBAL  = "\033[1m"
TEAL   = "\033[96m"    # Aksen header


def cetak_pemisah(karakter: str = "─", lebar: int = 72) -> None:
    
    print(karakter * lebar)


def cetak_judul(teks: str) -> None:
    
    print()
    cetak_pemisah("═")
    print(f"{TEAL}{TEBAL}  {teks}{RESET}")
    cetak_pemisah("═")


def cetak_subjudul(teks: str) -> None:
    
    print(f"\n{BIRU}{TEBAL}  {teks}{RESET}")
    cetak_pemisah("─", 50)


def format_sel(nilai: int, dimodifikasi: bool = False) -> str:
    
    s = f"{nilai:3d}"
    if dimodifikasi:
        return f"{MERAH}{TEBAL}{s}{RESET}"
    return s


def cetak_matriks(
    arr: np.ndarray,
    label: str,
    x_mulai: int,
    y_mulai: int,
    lebar: int,
    tinggi: int,
    channel: int,
    koordinat_dimodifikasi: set[tuple[int, int]] | None = None,
) -> None:
    
    if koordinat_dimodifikasi is None:
        koordinat_dimodifikasi = set()

    cetak_subjudul(f"{label} — Channel {NAMA_CHANNEL[channel]}")

    # Baris nomor kolom (header)
    header = "     "   # Padding untuk label baris
    for x in range(x_mulai, x_mulai + lebar):
        header += f"[{x:2d}] "
    print(f"{BIRU}{header}{RESET}")
    cetak_pemisah("·", 6 + lebar * 5)

    # Baris data
    for y in range(y_mulai, y_mulai + tinggi):
        baris = f"{BIRU}[{y:2d}]{RESET} "
        for x in range(x_mulai, x_mulai + lebar):
            nilai = int(arr[y, x, channel])
            dimod = (x, y) in koordinat_dimodifikasi
            baris += format_sel(nilai, dimod) + "  "
        print(baris)


def cetak_matriks_selisih(
    arr_cover: np.ndarray,
    arr_stego: np.ndarray,
    x_mulai: int,
    y_mulai: int,
    lebar: int,
    tinggi: int,
    channel: int,
) -> None:
    
    cetak_subjudul(f"MATRIKS SELISIH Δ = (Stego − Cover) — Channel {NAMA_CHANNEL[channel]}")

    header = "     "
    for x in range(x_mulai, x_mulai + lebar):
        header += f"[{x:2d}] "
    print(f"{BIRU}{header}{RESET}")
    cetak_pemisah("·", 6 + lebar * 5)

    total_berubah = 0
    for y in range(y_mulai, y_mulai + tinggi):
        baris = f"{BIRU}[{y:2d}]{RESET} "
        for x in range(x_mulai, x_mulai + lebar):
            cover_val = int(arr_cover[y, x, channel])
            stego_val = int(arr_stego[y, x, channel])
            delta = stego_val - cover_val

            if delta != 0:
                total_berubah += 1
                baris += f"{KUNING}{TEBAL}{delta:+3d}{RESET}  "
            else:
                baris += f"{HIJAU}  0{RESET}  "
        print(baris)

    print(f"\n  Total piksel berubah dalam region: {KUNING}{TEBAL}{total_berubah}{RESET} dari {lebar * tinggi}")


def cetak_bit_lsb(
    arr: np.ndarray,
    label: str,
    x_mulai: int,
    y_mulai: int,
    lebar: int,
    tinggi: int,
    channel: int,
    koordinat_dimodifikasi: set[tuple[int, int]] | None = None,
) -> None:
    
    if koordinat_dimodifikasi is None:
        koordinat_dimodifikasi = set()

    cetak_subjudul(f"{label} — Bit LSB Channel {NAMA_CHANNEL[channel]}")

    header = "     "
    for x in range(x_mulai, x_mulai + lebar):
        header += f"[{x:2d}] "
    print(f"{BIRU}{header}{RESET}")
    cetak_pemisah("·", 6 + lebar * 5)

    for y in range(y_mulai, y_mulai + tinggi):
        baris = f"{BIRU}[{y:2d}]{RESET} "
        for x in range(x_mulai, x_mulai + lebar):
            nilai = int(arr[y, x, channel])
            lsb = nilai & 1
            dimod = (x, y) in koordinat_dimodifikasi
            if dimod:
                baris += f"{MERAH}{TEBAL}  {lsb}{RESET}  "
            else:
                baris += f"  {lsb}  "
        print(baris)


def tampilkan_koordinat_mwc_dalam_region(
    koordinat_semua: list[tuple[int, int]],
    x_mulai: int,
    y_mulai: int,
    lebar: int,
    tinggi: int,
    maks_tampil: int = 20,
) -> set[tuple[int, int]]:
    
    cetak_subjudul("KOORDINAT MWC YANG JATUH DI DALAM REGION INI")

    x_akhir = x_mulai + lebar
    y_akhir = y_mulai + tinggi

    dalam_region = [
        (urutan, x, y)
        for urutan, (x, y) in enumerate(koordinat_semua, start=1)
        if x_mulai <= x < x_akhir and y_mulai <= y < y_akhir
    ]

    if not dalam_region:
        print(f"  {KUNING}Tidak ada koordinat MWC yang jatuh di region ini.{RESET}")
        print(f"  Coba perbesar REGION_LEBAR/TINGGI atau perbanyak panjang pesan.")
        return set()

    tampil = dalam_region[:maks_tampil]
    print(f"  Ditemukan {TEBAL}{len(dalam_region)}{RESET} koordinat dalam region "
          f"(menampilkan {min(len(tampil), maks_tampil)} pertama):\n")

    print(f"  {'No.Urut':>8}  {'(x, y)':>10}  {'Bit Ke-':>8}")
    cetak_pemisah("·", 40)
    for urutan, x, y in tampil:
        # Bit ke- = urutan - 1 (0-indexed): 0-31 adalah header, 32+ adalah payload
        bit_ke = urutan - 1
        keterangan = "header (panjang pesan)" if bit_ke < 32 else f"payload bit-{bit_ke - 32}"
        print(f"  {urutan:>8}  ({x:3d}, {y:3d})  {bit_ke:>8}  ← {keterangan}")

    if len(dalam_region) > maks_tampil:
        print(f"  ... dan {len(dalam_region) - maks_tampil} koordinat lainnya.")

    return {(x, y) for _, x, y in dalam_region}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    cetak_judul("DIGITASI MATRIKS PIKSEL — ANALISIS LSB STEGANOGRAFI")

    print(f"\n  {TEBAL}Konfigurasi:{RESET}")
    print(f"  Cover : {PATH_COVER}")
    print(f"  Stego : {PATH_STEGO}")
    print(f"  Kunci : {'●' * len(KUNCI)}")
    print(f"  Region: x=[{REGION_X_MULAI}..{REGION_X_MULAI+REGION_LEBAR-1}], "
          f"y=[{REGION_Y_MULAI}..{REGION_Y_MULAI+REGION_TINGGI-1}] "
          f"({REGION_LEBAR}×{REGION_TINGGI} piksel)")

    # ── Muat Citra ────────────────────────────────────────────────────────────
    print(f"\n  Memuat citra...")
    try:
        with Image.open(PATH_COVER) as img:
            arr_cover = np.array(img.convert("RGB"), dtype=np.uint8)
        with Image.open(PATH_STEGO) as img:
            arr_stego = np.array(img.convert("RGB"), dtype=np.uint8)
    except FileNotFoundError as e:
        print(f"\n  {MERAH}ERROR: {e}{RESET}")
        print("  Pastikan PATH_COVER dan PATH_STEGO sudah benar,")
        print("  dan proses embedding sudah dilakukan terlebih dahulu.\n")
        sys.exit(1)

    lebar_img, tinggi_img = arr_cover.shape[1], arr_cover.shape[0]
    print(f"  Dimensi citra: {lebar_img} × {tinggi_img} piksel")

    # ── Hasilkan Koordinat MWC ────────────────────────────────────────────────
    # Hitung estimasi jumlah bit dari selisih array (piksel yang berubah = 1 bit)
    jumlah_berubah = int(np.sum(arr_cover[:, :, CHANNEL] != arr_stego[:, :, CHANNEL]))
    # Total bit = jumlah piksel berubah (karena 1 piksel = 1 bit pada LSB 1-bit)
    # Tapi kita perlu total bit yang disisipkan (termasuk header dan piksel yang kebetulan tidak berubah)
    # Untuk keperluan tampilan, kita gunakan minimum 32 (header) + yang terdeteksi
    estimasi_total_bit = max(32, jumlah_berubah + 100)  # tambah buffer untuk piksel yg nilainya sama

    print(f"  Piksel yang berubah (terdeteksi): {jumlah_berubah}")
    print(f"  Membangkitkan koordinat MWC ({estimasi_total_bit} bit)...")

    generator = MWCGenerator(password=KUNCI)
    try:
        koordinat_semua = generator.hasilkan_koordinat(
            lebar=lebar_img,
            tinggi=tinggi_img,
            jumlah=estimasi_total_bit,
        )
    except ValueError as e:
        print(f"\n  {KUNING}Peringatan: {e}{RESET}")
        print("  Menggunakan semua piksel yang tersedia...")
        koordinat_semua = generator.hasilkan_koordinat(
            lebar=lebar_img, tinggi=tinggi_img,
            jumlah=lebar_img * tinggi_img,
        )

    # ── Tampilkan Koordinat MWC dalam Region ──────────────────────────────────
    koordinat_dalam_region = tampilkan_koordinat_mwc_dalam_region(
        koordinat_semua,
        REGION_X_MULAI, REGION_Y_MULAI,
        REGION_LEBAR, REGION_TINGGI,
    )

    # ── Cetak Matriks Nilai Piksel ────────────────────────────────────────────
    cetak_matriks(
        arr_cover, "CITRA COVER (ASLI)",
        REGION_X_MULAI, REGION_Y_MULAI, REGION_LEBAR, REGION_TINGGI,
        CHANNEL, koordinat_dalam_region,
    )

    cetak_matriks(
        arr_stego, "CITRA STEGO (SETELAH EMBEDDING)",
        REGION_X_MULAI, REGION_Y_MULAI, REGION_LEBAR, REGION_TINGGI,
        CHANNEL, koordinat_dalam_region,
    )

    # ── Cetak Matriks Selisih ─────────────────────────────────────────────────
    cetak_matriks_selisih(
        arr_cover, arr_stego,
        REGION_X_MULAI, REGION_Y_MULAI, REGION_LEBAR, REGION_TINGGI,
        CHANNEL,
    )

    # ── Cetak Bit LSB ─────────────────────────────────────────────────────────
    cetak_bit_lsb(
        arr_cover, "COVER — Bit LSB Sebelum",
        REGION_X_MULAI, REGION_Y_MULAI, REGION_LEBAR, REGION_TINGGI,
        CHANNEL, koordinat_dalam_region,
    )
    cetak_bit_lsb(
        arr_stego, "STEGO — Bit LSB Sesudah (berisi bit pesan)",
        REGION_X_MULAI, REGION_Y_MULAI, REGION_LEBAR, REGION_TINGGI,
        CHANNEL, koordinat_dalam_region,
    )

    # ── Ringkasan ─────────────────────────────────────────────────────────────
    cetak_judul("RINGKASAN")
    total_piksel_region = REGION_LEBAR * REGION_TINGGI
    print(f"  Ukuran region        : {REGION_LEBAR} × {REGION_TINGGI} = {total_piksel_region} piksel")
    print(f"  Piksel dimodifikasi  : {len(koordinat_dalam_region)} dari {total_piksel_region}")
    print(f"  Channel dianalisis   : {NAMA_CHANNEL[CHANNEL]}")
    print(f"  {MERAH}{TEBAL}Merah = piksel yang dimodifikasi LSB{RESET}")
    print(f"  {KUNING}{TEBAL}Kuning = selisih nilai (Δ ≠ 0){RESET}")
    print()


if __name__ == "__main__":
    main()