import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from engine.mwc_generator import MWCGenerator

logger = logging.getLogger(__name__)


# ── Konstanta ──────────────────────────────────────────────────────────────────
# Indeks channel warna pada array numpy format RGB.
_CHANNEL_RED: int = 0    # Indeks 0 = channel Merah (R)

# Ukuran header dalam bit: 32 bit = 4 byte = cukup untuk menyimpan panjang
# pesan hingga 2^32 - 1 byte (~4 GB). Jauh melebihi kebutuhan praktis.
_UKURAN_HEADER_BIT: int = 32

# Mask 1-bit paling kanan: digunakan untuk mengambil atau menghapus LSB.
_MASK_LSB: np.uint8 = np.uint8(1)        # 0000 0001 — untuk membaca LSB
_MASK_HAPUS_LSB: np.uint8 = np.uint8(0xFE)  # 1111 1110 — untuk menghapus LSB


# ── Data Class untuk Hasil Embedding ─────────────────────────────────────────
@dataclass
class HasilEmbedding:
    
    path_stego:       Path
    jumlah_bit:       int
    kapasitas_maks:   int
    persentase_pakai: float = field(init=False)

    def __post_init__(self) -> None:
        """Dihitung otomatis setelah field lain terisi."""
        kapasitas_bit = self.kapasitas_maks * 8
        self.persentase_pakai = (self.jumlah_bit / kapasitas_bit) * 100 if kapasitas_bit > 0 else 0.0


# ── Fungsi Pembantu (Private) ─────────────────────────────────────────────────

def _pesan_ke_bitstream(pesan: str) -> list[int]:
    
    # Konversi string ke bytes menggunakan encoding UTF-8
    pesan_bytes = pesan.encode("utf-8")
    panjang_bytes = len(pesan_bytes)

    # Buat 32-bit header: representasi big-endian dari panjang pesan (dalam byte)
    # Contoh: panjang 5 → 0x00000005 → [0,0,0,0,...,0,1,0,1] (32 bit)
    header_bits = [
        (panjang_bytes >> (31 - i)) & 1
        for i in range(_UKURAN_HEADER_BIT)
    ]

    # Konversi setiap byte pesan menjadi 8 bit (MSB first)
    payload_bits = []
    for byte in pesan_bytes:
        for i in range(7, -1, -1):    # Dari bit ke-7 (paling kiri) ke bit ke-0
            payload_bits.append((byte >> i) & 1)

    return header_bits + payload_bits


def _bitstream_ke_pesan(bits: list[int]) -> str:
    
    # Kelompokkan bit menjadi byte (8 bit per byte)
    nilai_bytes = []
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i + 8]
        if len(byte_bits) < 8:
            break   # Abaikan sisa bit yang tidak genap 8
        nilai = sum(bit << (7 - j) for j, bit in enumerate(byte_bits))
        nilai_bytes.append(nilai)

    # Konversi list integer ke bytes, lalu decode UTF-8
    return bytes(nilai_bytes).decode("utf-8")


def _hitung_kapasitas_maks(lebar: int, tinggi: int) -> int:
    
    total_piksel = lebar * tinggi
    kapasitas_bit = total_piksel - _UKURAN_HEADER_BIT
    return max(0, kapasitas_bit // 8)


# ── Fungsi Publik Utama ───────────────────────────────────────────────────────

def embed_data(
    cover_path: str | Path,
    message: str,
    key: str,
    output_path: str | Path | None = None,
) -> HasilEmbedding:
    
    # ── Validasi Input ────────────────────────────────────────────────────────
    if not message or not message.strip():
        raise ValueError("Pesan yang akan disisipkan tidak boleh kosong.")
    if not key or not key.strip():
        raise ValueError("Kunci/password tidak boleh kosong.")

    cover_path = Path(cover_path)
    if not cover_path.exists():
        raise FileNotFoundError(f"File cover tidak ditemukan: '{cover_path}'")

    # ── Buka Citra Cover ──────────────────────────────────────────────────────
    try:
        with Image.open(cover_path) as img:
            # Konversi ke RGB untuk memastikan 3 channel (menangani RGBA, Grayscale, dll.)
            img_rgb = img.convert("RGB")
            lebar, tinggi = img_rgb.size
    except OSError as e:
        raise OSError(f"Gagal membuka file citra cover: {e}") from e

    # ── Periksa Kapasitas ─────────────────────────────────────────────────────
    kapasitas_byte = _hitung_kapasitas_maks(lebar, tinggi)
    pesan_bytes = message.encode("utf-8")
    panjang_pesan_byte = len(pesan_bytes)

    if panjang_pesan_byte > kapasitas_byte:
        raise ValueError(
            f"Pesan terlalu panjang! Panjang pesan: {panjang_pesan_byte} byte, "
            f"kapasitas citra ({lebar}×{tinggi} px): {kapasitas_byte} byte. "
            f"Gunakan citra yang lebih besar atau pesan yang lebih pendek."
        )

    # ── Buat Bit Stream ───────────────────────────────────────────────────────
    # Mengkonversi pesan + header menjadi aliran bit yang siap disisipkan.
    bit_stream = _pesan_ke_bitstream(message)
    total_bit = len(bit_stream)

    logger.info(
        f"Memulai embedding — Citra: '{cover_path.name}' ({lebar}×{tinggi}) | "
        f"Pesan: {panjang_pesan_byte} byte | Total bit: {total_bit}"
    )

    # ── Hasilkan Koordinat Acak via MWC ──────────────────────────────────────
    # Generator baru dengan kunci yang diberikan → hasilkan sejumlah 'total_bit'
    # koordinat unik dan diacak untuk menentukan piksel mana yang dimodifikasi.
    generator = MWCGenerator(password=key)
    koordinat = generator.hasilkan_koordinat(
        lebar=lebar,
        tinggi=tinggi,
        jumlah=total_bit,
    )

    # ── Sisipkan Bit ke Array NumPy ───────────────────────────────────────────
    # Konversi citra ke array NumPy uint8 untuk manipulasi piksel.
    # Shape array: (tinggi, lebar, 3) — perhatikan urutan: tinggi dulu, baru lebar.
    # Ini adalah konvensi numpy (baris/row = Y, kolom/col = X).
    arr = np.array(img_rgb, dtype=np.uint8)

    for i, (x, y) in enumerate(koordinat):
        bit = bit_stream[i]
        # Operasi bitwise LSB:
        # Langkah 1: Hapus LSB lama → arr[y, x, 0] & 0xFE
        # Langkah 2: Setel LSB baru → ... | bit
        # Catatan: arr[y, x, 0] → channel Red, koordinat numpy [baris=y, kolom=x]
        arr[y, x, _CHANNEL_RED] = (arr[y, x, _CHANNEL_RED] & _MASK_HAPUS_LSB) | np.uint8(bit)

    # ── Tentukan Path Output & Simpan ─────────────────────────────────────────
    if output_path is None:
        # Default: simpan di folder yang sama dengan cover, nama + '_stego'
        nama_stego = cover_path.stem + "_stego.png"
        output_path = cover_path.parent / nama_stego
    else:
        output_path = Path(output_path)
        # Pastikan ekstensi .png (paksa PNG untuk lossless)
        output_path = output_path.with_suffix(".png")

    # Konversi array NumPy kembali ke objek PIL Image, lalu simpan sebagai PNG.
    # PNG dipilih karena lossless — format JPG/JPEG TIDAK BOLEH digunakan karena
    # kompresi lossy-nya akan merusak bit LSB yang sudah disisipkan.
    try:
        stego_img = Image.fromarray(arr, mode="RGB")
        stego_img.save(str(output_path), format="PNG")
    except PermissionError as e:
        raise PermissionError(f"Tidak ada izin untuk menyimpan file di '{output_path}': {e}") from e

    logger.info(f"Embedding berhasil. Citra stego disimpan di: '{output_path}'")

    return HasilEmbedding(
        path_stego=output_path,
        jumlah_bit=total_bit,
        kapasitas_maks=kapasitas_byte,
    )


def extract_data(
    stego_path: str | Path,
    key: str,
) -> str:
    
    # ── Validasi Input ────────────────────────────────────────────────────────
    if not key or not key.strip():
        raise ValueError("Kunci/password tidak boleh kosong.")

    stego_path = Path(stego_path)
    if not stego_path.exists():
        raise FileNotFoundError(f"File stego tidak ditemukan: '{stego_path}'")

    # ── Buka Citra Stego ──────────────────────────────────────────────────────
    try:
        with Image.open(stego_path) as img:
            img_rgb = img.convert("RGB")
            lebar, tinggi = img_rgb.size
            arr = np.array(img_rgb, dtype=np.uint8)
    except OSError as e:
        raise OSError(f"Gagal membuka file citra stego: {e}") from e

    logger.info(
        f"Memulai ekstraksi — Citra: '{stego_path.name}' ({lebar}×{tinggi})"
    )

    # ── Tahap 1: Ekstrak Header (32 bit) ─────────────────────────────────────
    # Inisialisasi generator MWC dengan kunci yang sama → koordinat identik.
    generator = MWCGenerator(password=key)

    # Dapatkan 32 koordinat pertama untuk membaca header.
    koordinat_header = generator.hasilkan_koordinat(
        lebar=lebar,
        tinggi=tinggi,
        jumlah=_UKURAN_HEADER_BIT,
    )

    # Baca 32 bit dari LSB channel Red pada koordinat header.
    header_bits = [
        int(arr[y, x, _CHANNEL_RED] & _MASK_LSB)
        for x, y in koordinat_header
    ]

    # Susun 32 bit menjadi integer: panjang pesan dalam byte.
    panjang_pesan_byte = 0
    for bit in header_bits:
        panjang_pesan_byte = (panjang_pesan_byte << 1) | bit

    # Validasi panjang pesan: harus positif dan tidak melebihi kapasitas citra.
    kapasitas_byte = _hitung_kapasitas_maks(lebar, tinggi)
    if panjang_pesan_byte <= 0 or panjang_pesan_byte > kapasitas_byte:
        raise ValueError(
            f"Header tidak valid: panjang pesan terbaca = {panjang_pesan_byte} byte. "
            f"Kapasitas citra: {kapasitas_byte} byte. "
            "Kemungkinan penyebab: kunci yang digunakan salah, atau file tidak "
            "mengandung pesan tersembunyi dari aplikasi ini."
        )

    logger.debug(f"Header terbaca: panjang pesan = {panjang_pesan_byte} byte")

    # ── Tahap 2: Ekstrak Payload ──────────────────────────────────────────────
    # Hitung jumlah bit payload yang harus dibaca.
    jumlah_bit_payload = panjang_pesan_byte * 8
    total_bit_dibutuhkan = _UKURAN_HEADER_BIT + jumlah_bit_payload

    # Buat ulang generator BARU dengan kunci yang sama untuk mendapatkan
    # seluruh urutan koordinat dari awal (header + payload).
    # Ini diperlukan karena kita tidak bisa "meneruskan" state MWC dari
    # koordinat_header — kita harus mereproduksi seluruh urutan.
    generator_ulang = MWCGenerator(password=key)
    semua_koordinat = generator_ulang.hasilkan_koordinat(
        lebar=lebar,
        tinggi=tinggi,
        jumlah=total_bit_dibutuhkan,
    )

    # Ambil hanya koordinat payload (setelah 32 koordinat header)
    koordinat_payload = semua_koordinat[_UKURAN_HEADER_BIT:]

    # Baca bit payload dari LSB channel Red
    payload_bits = [
        int(arr[y, x, _CHANNEL_RED] & _MASK_LSB)
        for x, y in koordinat_payload
    ]

    # ── Dekode Bit Payload menjadi String ────────────────────────────────────
    try:
        pesan = _bitstream_ke_pesan(payload_bits)
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(
            e.encoding, e.object, e.start, e.end,
            f"Gagal mendekode pesan: kunci yang digunakan mungkin salah, "
            f"atau file bukan citra stego yang valid. Detail: {e.reason}"
        ) from e

    logger.info(
        f"Ekstraksi berhasil — Pesan diekstrak: {panjang_pesan_byte} byte, "
        f"{len(pesan)} karakter."
    )
    return pesan


def cek_kapasitas(cover_path: str | Path) -> dict[str, int | float]:
    
    cover_path = Path(cover_path)
    if not cover_path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: '{cover_path}'")

    try:
        with Image.open(cover_path) as img:
            lebar, tinggi = img.size
    except OSError as e:
        raise OSError(f"Gagal membuka file: {e}") from e

    kapasitas_byte = _hitung_kapasitas_maks(lebar, tinggi)

    return {
        "lebar":              lebar,
        "tinggi":             tinggi,
        "total_piksel":       lebar * tinggi,
        "kapasitas_byte":     kapasitas_byte,
        "kapasitas_karakter": kapasitas_byte,   # 1 char ASCII = 1 byte
    }