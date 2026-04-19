"""
================================================================================
MODULE  : ui/views/frame_dashboard.py
DESKRIPSI:
    Halaman Dashboard — halaman pertama yang muncul saat aplikasi dibuka.

    KONTEN:
      • Header selamat datang dengan deskripsi singkat aplikasi.
      • 3 kartu statistik: Total Riwayat, Rata-rata PSNR, Rata-rata MSE.
      • Panel "Tentang Algoritma" — penjelasan singkat MWC & LSB.
      • Panel "Panduan Cepat" — langkah-langkah penggunaan.

    Data statistik di-refresh setiap kali halaman ini ditampilkan (on_show).
================================================================================
"""

import logging

import customtkinter as ctk

from ui import theme as T

logger = logging.getLogger(__name__)


class FrameDashboard(ctk.CTkFrame):
    """
    Frame halaman Dashboard.

    Args:
        parent     : Widget induk (content_area dari AppMain).
        controller : Referensi ke AppMain, untuk akses db dan navigasi.
    """

    def __init__(self, parent: ctk.CTkFrame, controller) -> None:
        super().__init__(parent, fg_color=T.BG_APP, corner_radius=0)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._bangun_ui()

    # ── UI Builder ────────────────────────────────────────────────────────────

    def _bangun_ui(self) -> None:
        """Merakit seluruh konten halaman dashboard."""

        # ── Header ────────────────────────────────────────────────────────────
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))

        ctk.CTkLabel(
            frame_header,
            text="Dashboard",
            font=T.FONT_JUDUL,
            text_color=T.TEKS_PRIMER,
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame_header,
            text="Sistem Steganografi LSB dengan PRNG Multiply-With-Carry",
            font=T.FONT_LABEL,
            text_color=T.TEKS_SEKUNDER,
        ).pack(anchor="w", pady=(2, 0))

        # Garis aksen di bawah header
        ctk.CTkFrame(
            frame_header, height=2, fg_color=T.AKSEN_PRIMER, corner_radius=1,
        ).pack(fill="x", pady=(12, 0))

        # ── Scrollable Content ────────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", scrollbar_button_color=T.BORDER_NORMAL,
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        scroll.grid_columnconfigure((0, 1, 2), weight=1)

        # ── Kartu Statistik ───────────────────────────────────────────────────
        self._label_total    = self._buat_kartu_statistik(scroll, col=0, judul="Total Riwayat",   satuan="operasi", warna=T.AKSEN_PRIMER)
        self._label_psnr_avg = self._buat_kartu_statistik(scroll, col=1, judul="Rata-rata PSNR",  satuan="dB",      warna=T.AKSEN_SEKUNDER)
        self._label_mse_avg  = self._buat_kartu_statistik(scroll, col=2, judul="Rata-rata MSE",   satuan="",        warna=T.AKSEN_WARNING)

        # ── Panel Tentang Algoritma ───────────────────────────────────────────
        frame_algo = self._buat_panel(scroll, judul="⚙  Tentang Algoritma", row=1, colspan=3)
        frame_algo.grid_columnconfigure((0, 1), weight=1)

        # Kolom MWC
        frame_mwc = ctk.CTkFrame(frame_algo, fg_color=T.BG_WIDGET, corner_radius=T.RADIUS_CARD)
        frame_mwc.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

        ctk.CTkLabel(
            frame_mwc,
            text="PRNG Multiply-With-Carry",
            font=T.FONT_LABEL_BOLD,
            text_color=T.AKSEN_PRIMER,
        ).pack(anchor="w", padx=14, pady=(14, 4))

        teks_mwc = (
            "Algoritma MWC menggunakan formula:\n"
            "z(n) = a × (z(n-1) & 0xFFFF) + (z(n-1) >> 16)\n\n"
            "• Multiplier a = 36.969 (Marsaglia, 2003)\n"
            "• Periode sangat panjang (~2⁶⁰)\n"
            "• Password di-hash SHA-256 → seed integer\n"
            "• Menghasilkan koordinat piksel unik & teracak"
        )
        ctk.CTkLabel(
            frame_mwc,
            text=teks_mwc,
            font=T.FONT_MONO_KECIL,
            text_color=T.TEKS_SEKUNDER,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 14))

        # Kolom LSB
        frame_lsb = ctk.CTkFrame(frame_algo, fg_color=T.BG_WIDGET, corner_radius=T.RADIUS_CARD)
        frame_lsb.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)

        ctk.CTkLabel(
            frame_lsb,
            text="Least Significant Bit (LSB)",
            font=T.FONT_LABEL_BOLD,
            text_color=T.AKSEN_SEKUNDER,
        ).pack(anchor="w", padx=14, pady=(14, 4))

        teks_lsb = (
            "Operasi bitwise pada channel Red:\n"
            "Embed  : P_baru = (P_lama & 0xFE) | bit\n"
            "Extract: bit    =  P_stego & 0x01\n\n"
            "• Perubahan nilai piksel ±1 (tidak terdeteksi)\n"
            "• Format output: PNG (lossless)\n"
            "• Header 32-bit menyimpan panjang pesan\n"
            "• PSNR yang dihasilkan biasanya > 50 dB"
        )
        ctk.CTkLabel(
            frame_lsb,
            text=teks_lsb,
            font=T.FONT_MONO_KECIL,
            text_color=T.TEKS_SEKUNDER,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 14))

        # ── Panel Panduan Cepat ───────────────────────────────────────────────
        frame_panduan = self._buat_panel(scroll, judul="▶  Panduan Cepat", row=2, colspan=3)

        langkah = [
            ("1", "Embedding",  "Buka menu Embedding → pilih citra cover → masukkan pesan & kunci → klik Proses."),
            ("2", "Unduh Hasil","Citra stego (.png) otomatis tersimpan di folder yang sama dengan citra asli."),
            ("3", "Extraction", "Buka menu Extraction → pilih citra stego → masukkan kunci yang sama → klik Ekstrak."),
            ("4", "Riwayat",    "Semua operasi embedding tercatat otomatis di tabel Riwayat beserta nilai PSNR & MSE."),
        ]

        for nomor, judul_lang, deskripsi in langkah:
            self._buat_item_langkah(frame_panduan, nomor, judul_lang, deskripsi)

        # Tombol navigasi cepat
        frame_nav_cepat = ctk.CTkFrame(frame_panduan, fg_color="transparent")
        frame_nav_cepat.pack(fill="x", pady=(8, 4))

        ctk.CTkButton(
            frame_nav_cepat,
            text="→  Mulai Embedding",
            font=T.FONT_LABEL_BOLD,
            height=38,
            corner_radius=T.RADIUS_BTN,
            fg_color=T.AKSEN_PRIMER,
            text_color=T.BG_APP,
            hover_color=T.BTN_HOVER,
            command=lambda: self.controller.navigasi_ke("embedding"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            frame_nav_cepat,
            text="→  Mulai Extraction",
            font=T.FONT_LABEL_BOLD,
            height=38,
            corner_radius=T.RADIUS_BTN,
            fg_color=T.BTN_SEKUNDER_BG,
            text_color=T.TEKS_PRIMER,
            hover_color=T.BG_HOVER,
            command=lambda: self.controller.navigasi_ke("extraction"),
        ).pack(side="left")

    def _buat_kartu_statistik(
        self,
        parent: ctk.CTkFrame,
        col: int,
        judul: str,
        satuan: str,
        warna: str,
    ) -> ctk.CTkLabel:
        """
        Membuat kartu statistik dengan angka besar di tengah.
        Mengembalikan label angkanya agar bisa di-update saat refresh.
        """
        kartu = ctk.CTkFrame(parent, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        kartu.grid(row=0, column=col, sticky="ew", padx=6, pady=(0, 12))

        # Strip warna aksen di atas kartu
        ctk.CTkFrame(kartu, height=3, fg_color=warna, corner_radius=2).pack(fill="x")

        ctk.CTkLabel(
            kartu,
            text=judul,
            font=T.FONT_KECIL,
            text_color=T.TEKS_SEKUNDER,
        ).pack(anchor="w", padx=T.PADDING_CARD, pady=(12, 0))

        lbl_angka = ctk.CTkLabel(
            kartu,
            text="—",
            font=("Segoe UI", 28, "bold"),
            text_color=warna,
        )
        lbl_angka.pack(anchor="w", padx=T.PADDING_CARD)

        if satuan:
            ctk.CTkLabel(
                kartu,
                text=satuan,
                font=T.FONT_KECIL,
                text_color=T.TEKS_DISABLED,
            ).pack(anchor="w", padx=T.PADDING_CARD, pady=(0, 14))
        else:
            ctk.CTkFrame(kartu, height=14, fg_color="transparent").pack()

        return lbl_angka

    def _buat_panel(
        self,
        parent: ctk.CTkScrollableFrame,
        judul: str,
        row: int,
        colspan: int = 1,
    ) -> ctk.CTkFrame:
        """
        Membuat panel kartu besar dengan judul section di atas.
        Mengembalikan frame konten dalam panel.
        """
        frame_luar = ctk.CTkFrame(parent, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        frame_luar.grid(
            row=row, column=0, columnspan=colspan,
            sticky="ew", padx=6, pady=(0, 12),
        )

        ctk.CTkLabel(
            frame_luar,
            text=judul,
            font=T.FONT_LABEL_BOLD,
            text_color=T.TEKS_PRIMER,
        ).pack(anchor="w", padx=T.PADDING_CARD, pady=(T.PADDING_CARD, 10))

        ctk.CTkFrame(frame_luar, height=1, fg_color=T.BORDER_SUBTLE, corner_radius=0).pack(fill="x", padx=T.PADDING_CARD)

        frame_konten = ctk.CTkFrame(frame_luar, fg_color="transparent")
        frame_konten.pack(fill="both", expand=True, padx=T.PADDING_CARD, pady=T.PADDING_CARD)

        return frame_konten

    def _buat_item_langkah(
        self,
        parent: ctk.CTkFrame,
        nomor: str,
        judul: str,
        deskripsi: str,
    ) -> None:
        """Membuat satu baris item langkah dengan nomor badge, judul, dan deskripsi."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)

        # Badge nomor bulat
        badge = ctk.CTkLabel(
            row,
            text=nomor,
            width=26, height=26,
            corner_radius=13,
            fg_color=T.AKSEN_PRIMER,
            text_color=T.BG_APP,
            font=T.FONT_BADGE,
        )
        badge.pack(side="left", padx=(0, 12), anchor="n", pady=2)

        frame_teks = ctk.CTkFrame(row, fg_color="transparent")
        frame_teks.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            frame_teks,
            text=judul,
            font=T.FONT_LABEL_BOLD,
            text_color=T.TEKS_PRIMER,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame_teks,
            text=deskripsi,
            font=T.FONT_KECIL,
            text_color=T.TEKS_SEKUNDER,
            anchor="w",
            wraplength=600,
            justify="left",
        ).pack(anchor="w")

    # ── Lifecycle Hooks ───────────────────────────────────────────────────────

    def on_show(self) -> None:
        """Dipanggil oleh AppMain setiap kali halaman ini ditampilkan. Refresh statistik."""
        self._refresh_statistik()

    def _refresh_statistik(self) -> None:
        """Mengambil data terbaru dari database dan memperbarui kartu statistik."""
        try:
            semua = self.controller.db.ambil_semua()
            total = len(semua)

            self._label_total.configure(text=str(total))

            if total > 0:
                psnr_vals = [r.nilai_psnr for r in semua if r.nilai_psnr is not None]
                mse_vals  = [r.nilai_mse  for r in semua if r.nilai_mse  is not None]

                avg_psnr = sum(psnr_vals) / len(psnr_vals) if psnr_vals else 0
                avg_mse  = sum(mse_vals)  / len(mse_vals)  if mse_vals  else 0

                self._label_psnr_avg.configure(text=f"{avg_psnr:.2f}")
                self._label_mse_avg.configure( text=f"{avg_mse:.4f}")
            else:
                self._label_psnr_avg.configure(text="—")
                self._label_mse_avg.configure( text="—")

        except Exception as e:
            logger.error(f"Gagal refresh statistik dashboard: {e}")