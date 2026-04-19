"""
================================================================================
MODULE  : ui/theme.py
DESKRIPSI:
    Satu sumber kebenaran (single source of truth) untuk semua konstanta
    warna, font, dan ukuran yang digunakan di seluruh antarmuka aplikasi.

    PRINSIP:
    Tidak ada angka warna hardcoded di file frame manapun. Semua mengacu
    ke konstanta di sini. Jika ingin ganti warna aksen, cukup ubah di sini.
================================================================================
"""

# ── Palet Warna Utama ──────────────────────────────────────────────────────────
# Terinspirasi dari dark terminal / research tool aesthetic.
# Dominan deep navy, aksen teal/cyan elektrik yang tajam.

BG_APP         = "#0d1117"   # Background utama aplikasi (paling gelap)
BG_SIDEBAR     = "#0d1117"   # Sidebar — sama dengan app, dibedakan border
BG_PANEL       = "#161b22"   # Card / panel konten (satu tingkat lebih terang)
BG_WIDGET      = "#1c2230"   # Input, entry, frame dalam card
BG_HOVER       = "#1f2d3d"   # Warna saat elemen di-hover

AKSEN_PRIMER   = "#00d4aa"   # Teal elektrik — warna utama brand
AKSEN_SEKUNDER = "#38bdf8"   # Sky blue — untuk elemen sekunder / info
AKSEN_WARNING  = "#fbbf24"   # Amber — untuk peringatan
AKSEN_DANGER   = "#f85149"   # Merah — untuk error
AKSEN_SUKSES   = "#3fb950"   # Hijau — untuk konfirmasi berhasil

TEKS_PRIMER    = "#e6edf3"   # Teks utama (hampir putih)
TEKS_SEKUNDER  = "#8b949e"   # Teks sekunder / label / hint
TEKS_DISABLED  = "#484f58"   # Teks nonaktif
TEKS_AKSEN     = "#00d4aa"   # Teks dengan warna aksen

BORDER_NORMAL  = "#30363d"   # Border default
BORDER_AKSEN   = "#00d4aa"   # Border dengan aksen (fokus, aktif)
BORDER_SUBTLE  = "#21262d"   # Border sangat halus

# ── Tombol ─────────────────────────────────────────────────────────────────────
BTN_FG          = "#0d1117"   # Teks di atas tombol primer (gelap di atas teal)
BTN_HOVER       = "#00b894"   # Hover tombol primer (sedikit lebih gelap)
BTN_SEKUNDER_BG = "#21262d"   # Background tombol sekunder
BTN_SEKUNDER_FG = "#e6edf3"   # Teks tombol sekunder

# ── Tipografi ──────────────────────────────────────────────────────────────────
# JetBrains Mono untuk elemen teknikal (koordinat, nilai hex, kode)
# Segoe UI / sistem untuk teks umum
FONT_JUDUL      = ("Segoe UI", 22, "bold")
FONT_SUBJUDUL   = ("Segoe UI", 13, "bold")
FONT_LABEL      = ("Segoe UI", 11)
FONT_LABEL_BOLD = ("Segoe UI", 11, "bold")
FONT_KECIL      = ("Segoe UI", 10)
FONT_MONO       = ("JetBrains Mono", 11)   # Fallback: Consolas
FONT_MONO_KECIL = ("JetBrains Mono", 10)
FONT_SIDEBAR    = ("Segoe UI", 12)
FONT_SIDEBAR_AKT= ("Segoe UI", 12, "bold")
FONT_BADGE      = ("Segoe UI", 9, "bold")

# ── Ukuran & Spacing ───────────────────────────────────────────────────────────
SIDEBAR_LEBAR   = 220
RADIUS_CARD     = 10
RADIUS_BTN      = 8
RADIUS_ENTRY    = 6
PADDING_CARD    = 20
PADDING_SECTION = 16