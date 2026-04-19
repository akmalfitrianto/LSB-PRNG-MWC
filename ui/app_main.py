"""
================================================================================
MODULE  : ui/app_main.py
REVISI  : + Menu Evaluasi & Analisis, + Section SETTINGS, + Konfigurasi MWC,
            + Profil Peneliti, + Tombol Keluar (GAP 2 & 4)
DESKRIPSI:
    Window utama aplikasi — layout sidebar + content area.
    Sidebar sesuai rancangan Gambar 3.11 pada proposal skripsi.
================================================================================
"""

import logging
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from database.db_manager import DatabaseManager
from ui import theme as T
from ui.views.frame_dashboard  import FrameDashboard
from ui.views.frame_embedding  import FrameEmbedding
from ui.views.frame_extraction import FrameExtraction
from ui.views.frame_evaluasi   import FrameEvaluasi
from ui.views.frame_history    import FrameHistory
from ui.views.frame_konfigurasi import FrameKonfigurasi

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class AppMain(ctk.CTk):
    """
    Window utama aplikasi Stego MWC.

    Sidebar 5 menu utama + 1 sub-menu settings:
      ┌─────────────────────┐
      │  [S]  STEGO MWC     │
      │       LSB + PRNG    │
      ├─────────────────────┤
      │  NAVIGASI           │
      │  ⊞  Dashboard       │
      │  ↓  Embedding       │
      │  ↑  Extraction      │
      │  ▣  Evaluasi        │
      │  ≡  Riwayat         │
      ├─────────────────────┤
      │  SETTINGS           │
      │  ⚙  Konfigurasi MWC │
      ├─────────────────────┤  ← spacer
      │  Profil Peneliti    │
      │  → Keluar           │
      └─────────────────────┘
    """

    def __init__(self) -> None:
        super().__init__()

        self.db = DatabaseManager()

        self.title("Stego MWC — LSB Steganografi + PRNG Multiply-With-Carry")
        self.geometry("1150x700")
        self.minsize(960, 600)
        self.configure(fg_color=T.BG_APP)

        self.protocol("WM_DELETE_WINDOW", self._on_tutup)

        self._frame_aktif: ctk.CTkFrame | None = None
        self._btn_aktif:   ctk.CTkButton | None = None

        self._bangun_layout()
        self._bangun_sidebar()
        self._bangun_content_area()
        self._inisialisasi_frames()

        self.navigasi_ke("dashboard")
        logger.info("AppMain berhasil diinisialisasi.")

    # ── Layout ────────────────────────────────────────────────────────────────

    def _bangun_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0, minsize=T.SIDEBAR_LEBAR)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _bangun_sidebar(self) -> None:
        """Sidebar lengkap sesuai Gambar 3.11 proposal."""
        self.sidebar = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        # Row 5 mendapat weight agar footer terdorong ke bawah
        self.sidebar.grid_rowconfigure(5, weight=1)

        # ── Logo ──────────────────────────────────────────────────────────────
        frame_logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_logo.pack(fill="x", padx=16, pady=(28, 8))

        canvas_logo = tk.Canvas(frame_logo, width=36, height=36,
                                bg=T.BG_PANEL, highlightthickness=0)
        canvas_logo.pack(side="left", padx=(0, 10))
        canvas_logo.create_rectangle(2, 2, 34, 34, fill=T.AKSEN_PRIMER, outline="")
        canvas_logo.create_text(18, 19, text="S", fill=T.BG_APP,
                                font=("Segoe UI", 16, "bold"))

        f_teks = ctk.CTkFrame(frame_logo, fg_color="transparent")
        f_teks.pack(side="left")
        ctk.CTkLabel(f_teks, text="STEGO MWC", font=("Segoe UI", 13, "bold"),
                     text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(f_teks, text="LSB + PRNG MWC", font=("Segoe UI", 9),
                     text_color=T.TEKS_SEKUNDER).pack(anchor="w")

        self._divider(self.sidebar)

        # ── Label Navigasi ────────────────────────────────────────────────────
        self._label_seksi(self.sidebar, "NAVIGASI")

        menu_navigasi = [
            ("dashboard",  "⊞",  "Dashboard"),
            ("embedding",  "↓",  "Embedding"),
            ("extraction", "↑",  "Extraction"),
            ("evaluasi",   "▣",  "Evaluasi & Analisis"),
            ("history",    "≡",  "Riwayat"),
        ]

        self._tombol_nav: dict[str, ctk.CTkButton] = {}
        for frame_id, ikon, label in menu_navigasi:
            btn = self._buat_tombol_nav(self.sidebar, f"  {ikon}   {label}", frame_id)
            self._tombol_nav[frame_id] = btn

        self._divider(self.sidebar)

        # ── Label Settings ────────────────────────────────────────────────────
        self._label_seksi(self.sidebar, "SETTINGS")

        btn_konfig = self._buat_tombol_nav(self.sidebar, "  ⚙   Konfigurasi MWC", "konfigurasi")
        self._tombol_nav["konfigurasi"] = btn_konfig

        # ── Footer (Profil + Keluar) ──────────────────────────────────────────
        frame_footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_footer.pack(side="bottom", fill="x", padx=0, pady=0)

        self._divider(self.sidebar, before=frame_footer)

        # Profil Peneliti
        frame_profil = ctk.CTkFrame(frame_footer, fg_color="transparent")
        frame_profil.pack(fill="x", padx=14, pady=(8, 4))

        # Avatar bulat kecil
        canvas_av = tk.Canvas(frame_profil, width=30, height=30,
                              bg=T.BG_PANEL, highlightthickness=0)
        canvas_av.pack(side="left", padx=(0, 8))
        canvas_av.create_oval(2, 2, 28, 28, fill=T.BG_WIDGET, outline=T.BORDER_NORMAL)
        canvas_av.create_text(15, 16, text="M", fill=T.AKSEN_PRIMER,
                              font=("Segoe UI", 11, "bold"))

        f_profil_teks = ctk.CTkFrame(frame_profil, fg_color="transparent")
        f_profil_teks.pack(side="left")
        ctk.CTkLabel(f_profil_teks, text="M. Akmal Fitrianto",
                     font=("Segoe UI", 9, "bold"), text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(f_profil_teks, text="NPM: 2210010546",
                     font=("Segoe UI", 8), text_color=T.TEKS_DISABLED).pack(anchor="w")

        # Tombol Keluar
        ctk.CTkButton(
            frame_footer,
            text="  →  Keluar",
            font=T.FONT_KECIL,
            height=32,
            corner_radius=T.RADIUS_BTN,
            fg_color="transparent",
            text_color=T.AKSEN_DANGER,
            hover_color="#2d1a1a",
            anchor="w",
            command=self._on_tutup,
        ).pack(fill="x", padx=10, pady=(4, 12))

    def _buat_tombol_nav(
        self, parent: ctk.CTkFrame, teks: str, frame_id: str,
    ) -> ctk.CTkButton:
        btn = ctk.CTkButton(
            parent, text=teks, font=T.FONT_SIDEBAR, anchor="w",
            height=40, corner_radius=T.RADIUS_BTN,
            fg_color="transparent", text_color=T.TEKS_SEKUNDER,
            hover_color=T.BG_HOVER,
            command=lambda fid=frame_id: self.navigasi_ke(fid),
        )
        btn.pack(fill="x", padx=10, pady=2)
        return btn

    def _bangun_content_area(self) -> None:
        self.content_area = ctk.CTkFrame(self, fg_color=T.BG_APP, corner_radius=0)
        self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

    def _inisialisasi_frames(self) -> None:
        """Buat semua frame dan tumpuk di content_area (Frame Stack pattern)."""
        self.frames: dict[str, ctk.CTkFrame] = {}

        kelas_frame = {
            "dashboard":   FrameDashboard,
            "embedding":   FrameEmbedding,
            "extraction":  FrameExtraction,
            "evaluasi":    FrameEvaluasi,
            "history":     FrameHistory,
            "konfigurasi": FrameKonfigurasi,
        }

        for nama, KelasFrame in kelas_frame.items():
            frame = KelasFrame(parent=self.content_area, controller=self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[nama] = frame

    # ── Navigasi ──────────────────────────────────────────────────────────────

    def navigasi_ke(self, frame_id: str) -> None:
        """Tampilkan frame yang dipilih dan update highlight sidebar."""
        if frame_id not in self.frames:
            logger.warning(f"Frame tidak dikenal: '{frame_id}'")
            return

        if self._frame_aktif is not None and hasattr(self._frame_aktif, "on_hide"):
            self._frame_aktif.on_hide()

        frame_baru = self.frames[frame_id]
        frame_baru.tkraise()
        self._frame_aktif = frame_baru

        if hasattr(frame_baru, "on_show"):
            frame_baru.on_show()

        self._update_highlight_sidebar(frame_id)
        logger.debug(f"Navigasi → '{frame_id}'")

    def _update_highlight_sidebar(self, frame_id_aktif: str) -> None:
        for fid, btn in self._tombol_nav.items():
            if fid == frame_id_aktif:
                # Konfigurasi MWC di SETTINGS — warna aksen berbeda (abu-abu terang)
                if fid == "konfigurasi":
                    btn.configure(fg_color=T.BG_HOVER, text_color=T.TEKS_PRIMER,
                                  font=T.FONT_SIDEBAR_AKT)
                else:
                    btn.configure(fg_color=T.AKSEN_PRIMER, text_color=T.BG_APP,
                                  font=T.FONT_SIDEBAR_AKT)
            else:
                btn.configure(fg_color="transparent", text_color=T.TEKS_SEKUNDER,
                              font=T.FONT_SIDEBAR)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _divider(parent: ctk.CTkFrame, before=None) -> ctk.CTkFrame:
        d = ctk.CTkFrame(parent, height=1, fg_color=T.BORDER_SUBTLE, corner_radius=0)
        if before:
            d.pack(fill="x", padx=0, pady=(0, 4), before=before)
        else:
            d.pack(fill="x", padx=0, pady=8)
        return d

    @staticmethod
    def _label_seksi(parent: ctk.CTkFrame, teks: str) -> None:
        ctk.CTkLabel(parent, text=f"  {teks}", font=("Segoe UI", 9, "bold"),
                     text_color=T.TEKS_DISABLED, anchor="w").pack(fill="x", padx=16, pady=(8, 4))

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_tutup(self) -> None:
        """Tutup aplikasi dengan aman: konfirmasi → tutup DB → destroy."""
        if not messagebox.askyesno("Keluar", "Yakin ingin menutup aplikasi?"):
            return
        logger.info("Aplikasi menutup — menutup koneksi database...")
        try:
            self.db.tutup()
        except Exception as e:
            logger.warning(f"Error saat menutup DB: {e}")
        finally:
            self.destroy()