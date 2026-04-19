"""
================================================================================
MODULE  : ui/views/frame_konfigurasi.py
DESKRIPSI:
    Halaman Konfigurasi MWC — menampilkan parameter algoritma MWC secara
    interaktif. Pengguna bisa memasukkan password untuk melihat nilai seed
    (X₀, C₀) yang dihasilkan serta output iterasi pertama secara live.

    Halaman ini berguna untuk:
      • Memahami cara kerja MWC secara visual (untuk demo ke dosen penguji).
      • Memverifikasi bahwa dua password berbeda menghasilkan seed berbeda.
      • Menampilkan konstanta algoritma (a, b) sesuai naskah skripsi.
================================================================================
"""

import logging

import customtkinter as ctk

from ui import theme as T

logger = logging.getLogger(__name__)


class FrameKonfigurasi(ctk.CTkFrame):
    """Frame halaman Konfigurasi MWC."""

    def __init__(self, parent: ctk.CTkFrame, controller) -> None:
        super().__init__(parent, fg_color=T.BG_APP, corner_radius=0)
        self.controller = controller

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._bangun_ui()

    def _bangun_ui(self) -> None:
        # Header
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))
        ctk.CTkLabel(frame_header, text="Konfigurasi MWC", font=T.FONT_JUDUL, text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(frame_header, text="Parameter Algoritma Multiply-With-Carry (PRNG)",
                     font=T.FONT_LABEL, text_color=T.TEKS_SEKUNDER).pack(anchor="w", pady=(2, 0))
        ctk.CTkFrame(frame_header, height=2, fg_color=T.BORDER_NORMAL, corner_radius=1).pack(fill="x", pady=(12, 0))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                         scrollbar_button_color=T.BORDER_NORMAL)
        scroll.grid(row=1, column=0, sticky="nsew", padx=32, pady=16)
        scroll.grid_columnconfigure((0, 1), weight=1)

        # ── Panel Parameter Tetap ─────────────────────────────────────────────
        f_param = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_param.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        ctk.CTkLabel(f_param, text="⚙  Parameter Algoritma MWC (Konstanta Tetap)",
                     font=T.FONT_LABEL_BOLD, text_color=T.TEKS_PRIMER).pack(anchor="w", padx=20, pady=(16, 8))
        ctk.CTkFrame(f_param, height=1, fg_color=T.BORDER_SUBTLE).pack(fill="x", padx=20)

        params = [
            ("Multiplier (a)",  "36.969",  "Konstanta pengali pada Persamaan (2.1) & (2.2).\nNilai direkomendasikan Marsaglia (2003)."),
            ("Modulus (b)",     "65.536",  "b = 2¹⁶ = 65.536. Menentukan rentang output Xₙ\npada Persamaan (2.1)."),
            ("Warm-up iterasi", "10",      "Jumlah iterasi pemanasan sebelum koordinat\npertama dihasilkan."),
            ("Hash password",   "SHA-256", "Algoritma hash untuk konversi password → seed.\nMenghasilkan 256-bit deterministik."),
            ("Ukuran output Xₙ","16-bit",  "Rentang Xₙ: [0, 65.535]. Output 32-bit (t)\ndigunakan untuk Fisher-Yates Shuffle."),
            ("Periode",         "~2⁶⁰",   "Estimasi panjang periode sebelum deret\nbilangan acak berulang."),
        ]

        for label, nilai, keterangan in params:
            row = ctk.CTkFrame(f_param, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=6)

            ctk.CTkLabel(row, text=label, font=T.FONT_LABEL_BOLD,
                         text_color=T.TEKS_SEKUNDER, width=140, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=nilai, font=T.FONT_MONO,
                         text_color=T.AKSEN_PRIMER, width=90, anchor="w").pack(side="left", padx=(0, 16))
            ctk.CTkLabel(row, text=keterangan, font=T.FONT_KECIL,
                         text_color=T.TEKS_DISABLED, anchor="w", justify="left").pack(side="left", fill="x", expand=True)

        ctk.CTkFrame(f_param, height=12, fg_color="transparent").pack()

        # ── Panel Rumus ───────────────────────────────────────────────────────
        f_rumus = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_rumus.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(0, 14))

        ctk.CTkLabel(f_rumus, text="📐  Rumus (Bab 2 Naskah Skripsi)",
                     font=T.FONT_LABEL_BOLD, text_color=T.TEKS_PRIMER).pack(anchor="w", padx=16, pady=(16, 10))

        rumus_teks = (
            "Persamaan (2.1):\n"
            "  Xₙ = (a · Xₙ₋₁ + Cₙ₋₁) mod b\n\n"
            "Persamaan (2.2):\n"
            "  Cₙ = ⌊(a · Xₙ₋₁ + Cₙ₋₁) / b⌋\n\n"
            "Implementasi Python:\n"
            "  t    = a * X + C\n"
            "  X    = t & 0xFFFF   # Pers. (2.1)\n"
            "  C    = t >> 16      # Pers. (2.2)\n"
            "  out  = t            # 32-bit output"
        )
        ctk.CTkLabel(
            f_rumus, text=rumus_teks, font=T.FONT_MONO_KECIL,
            text_color=T.TEKS_SEKUNDER, justify="left", anchor="w",
        ).pack(anchor="w", padx=16, pady=(0, 16))

        # ── Panel Demo Live ───────────────────────────────────────────────────
        f_demo = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_demo.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(0, 14))

        ctk.CTkLabel(f_demo, text="🔬  Demo Seed Generator",
                     font=T.FONT_LABEL_BOLD, text_color=T.TEKS_PRIMER).pack(anchor="w", padx=16, pady=(16, 8))

        ctk.CTkLabel(f_demo, text="Masukkan password untuk melihat\nnilai seed (X₀, C₀) yang dihasilkan:",
                     font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER, justify="left").pack(anchor="w", padx=16)

        self._entry_demo = ctk.CTkEntry(
            f_demo, placeholder_text="Ketik password di sini...",
            font=T.FONT_LABEL, fg_color=T.BG_WIDGET, border_color=T.BORDER_NORMAL,
            text_color=T.TEKS_PRIMER, height=36, corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_demo.pack(fill="x", padx=16, pady=8)
        self._entry_demo.bind("<KeyRelease>", self._update_demo)

        # Output demo
        self._frame_demo_output = ctk.CTkFrame(f_demo, fg_color=T.BG_WIDGET, corner_radius=T.RADIUS_CARD)
        self._frame_demo_output.pack(fill="x", padx=16, pady=(0, 16))

        demo_rows = [
            ("SHA-256 (8 hex):", "_lbl_hash"),
            ("Seed 32-bit:", "_lbl_seed32"),
            ("X₀ (= seed & 0xFFFF):", "_lbl_x0"),
            ("C₀ (= seed >> 16):", "_lbl_c0"),
            ("Output iterasi 1 (t):", "_lbl_t1"),
            ("X₁ (= t & 0xFFFF):", "_lbl_x1"),
            ("C₁ (= t >> 16):", "_lbl_c1"),
        ]
        self._demo_labels: dict[str, ctk.CTkLabel] = {}
        for label_teks, attr in demo_rows:
            r = ctk.CTkFrame(self._frame_demo_output, fg_color="transparent")
            r.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(r, text=label_teks, font=T.FONT_KECIL,
                         text_color=T.TEKS_SEKUNDER, width=150, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(r, text="—", font=T.FONT_MONO_KECIL,
                               text_color=T.AKSEN_PRIMER, anchor="w")
            lbl.pack(side="left")
            self._demo_labels[attr] = lbl

        ctk.CTkFrame(self._frame_demo_output, height=8, fg_color="transparent").pack()

        # ── Panel Alur Fisher-Yates ───────────────────────────────────────────
        f_fy = ctk.CTkFrame(scroll, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f_fy.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        ctk.CTkLabel(f_fy, text="🔀  Alur Fisher-Yates Shuffle via MWC",
                     font=T.FONT_LABEL_BOLD, text_color=T.TEKS_PRIMER).pack(anchor="w", padx=20, pady=(16, 8))

        fy_teks = (
            "Langkah pengacakan koordinat piksel (sesuai Bab 3.3.2):\n\n"
            "  1. Buat pool semua koordinat: [(0,0), (1,0), ..., (W-1,H-1)]  → total W×H elemen\n"
            "  2. Untuk i dari (n-1) turun ke (n - jumlah_bit):\n"
            "       j  = MWC._next() mod (i+1)    ← indeks acak dari Persamaan (2.1) & (2.2)\n"
            "       tukar pool[i] ↔ pool[j]        ← swap in-place\n"
            "  3. Ambil pool[n - jumlah_bit :]     ← hasil: daftar koordinat unik & teracak\n\n"
            "  Kompleksitas: O(jumlah_bit) — jauh lebih efisien dari O(n) shuffle penuh.\n"
            "  Sifat output: UNIK (no duplikat) + DETERMINISTIK (password sama → urutan sama)."
        )
        ctk.CTkLabel(f_fy, text=fy_teks, font=T.FONT_MONO_KECIL, text_color=T.TEKS_SEKUNDER,
                     justify="left", anchor="w").pack(anchor="w", padx=20, pady=(0, 16))

    def _update_demo(self, event=None) -> None:
        """Update output demo secara live saat pengguna mengetik password."""
        import hashlib
        password = self._entry_demo.get()
        if not password:
            for lbl in self._demo_labels.values():
                lbl.configure(text="—")
            return

        try:
            hash_bytes = hashlib.sha256(password.encode("utf-8")).digest()
            seed_32    = int.from_bytes(hash_bytes[:4], byteorder="big")
            X0         = seed_32 & 0xFFFF
            C0         = (seed_32 >> 16) & 0xFFFF
            if X0 == 0: X0 = 1
            if C0 == 0: C0 = 1

            # Simulasi 1 iterasi MWC
            t1 = 36_969 * X0 + C0
            X1 = t1 & 0xFFFF
            C1 = t1 >> 16

            self._demo_labels["_lbl_hash"].configure(text=hash_bytes[:4].hex())
            self._demo_labels["_lbl_seed32"].configure(text=f"{seed_32:,}  (0x{seed_32:08X})")
            self._demo_labels["_lbl_x0"].configure(text=f"{X0:,}  (0x{X0:04X})")
            self._demo_labels["_lbl_c0"].configure(text=f"{C0:,}  (0x{C0:04X})")
            self._demo_labels["_lbl_t1"].configure(text=f"{t1:,}  (0x{t1:08X})")
            self._demo_labels["_lbl_x1"].configure(text=f"{X1:,}  (0x{X1:04X})")
            self._demo_labels["_lbl_c1"].configure(text=f"{C1:,}  (0x{C1:04X})")

        except Exception as e:
            logger.error(f"Demo error: {e}")

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass