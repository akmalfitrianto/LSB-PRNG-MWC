import logging
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from database.db_manager import DatabaseManager
from ui import theme as T
from ui.views.frame_dashboard   import FrameDashboard
from ui.views.frame_embedding   import FrameEmbedding
from ui.views.frame_extraction  import FrameExtraction
from ui.views.frame_evaluasi    import FrameEvaluasi
from ui.views.frame_history     import FrameHistory
from ui.views.frame_laporan     import FrameLaporan
from ui.views.frame_konfigurasi import FrameKonfigurasi

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class AppMain(ctk.CTk):

    def __init__(self) -> None:
        super().__init__()
        self.db = DatabaseManager()

        self.title("Stego MWC — LSB Steganografi + PRNG Multiply-With-Carry")
        self.geometry("1200x720")
        self.minsize(1000, 620)
        self.configure(fg_color=T.BG_APP)
        self.protocol("WM_DELETE_WINDOW", self._on_tutup)

        self._frame_aktif: ctk.CTkFrame | None = None
        self._tombol_nav: dict[str, ctk.CTkButton] = {}

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
        self.sidebar = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # ── Logo ──────────────────────────────────────────────────────────────
        f_logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_logo.pack(fill="x", padx=16, pady=(24, 8))

        cv = tk.Canvas(f_logo, width=36, height=36, bg=T.BG_PANEL, highlightthickness=0)
        cv.pack(side="left", padx=(0, 10))
        cv.create_rectangle(2, 2, 34, 34, fill=T.AKSEN_PRIMER, outline="")
        cv.create_text(18, 19, text="S", fill=T.BG_APP, font=("Segoe UI", 16, "bold"))

        f_teks = ctk.CTkFrame(f_logo, fg_color="transparent")
        f_teks.pack(side="left")
        ctk.CTkLabel(f_teks, text="STEGO MWC", font=("Segoe UI", 13, "bold"),
                     text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(f_teks, text="LSB + PRNG MWC", font=("Segoe UI", 9),
                     text_color=T.TEKS_SEKUNDER).pack(anchor="w")

        self._divider(self.sidebar)

        # ── Navigasi ──────────────────────────────────────────────────────────
        self._label_seksi(self.sidebar, "NAVIGASI")

        menu_nav = [
            ("dashboard",  "⊞",  "Dashboard"),
            ("embedding",  "↓",  "Embedding"),
            ("extraction", "↑",  "Extraction"),
            ("evaluasi",   "▣",  "Evaluasi & Analisis"),
            ("history",    "≡",  "Riwayat"),
            ("laporan",    "📄", "Laporan"),
        ]
        for frame_id, ikon, label in menu_nav:
            btn = self._buat_tombol_nav(self.sidebar, f"  {ikon}   {label}", frame_id)
            self._tombol_nav[frame_id] = btn

        self._divider(self.sidebar)

        # ── Settings ──────────────────────────────────────────────────────────
        self._label_seksi(self.sidebar, "SETTINGS")
        btn_k = self._buat_tombol_nav(self.sidebar, "  ⚙   Konfigurasi MWC", "konfigurasi")
        self._tombol_nav["konfigurasi"] = btn_k

        # ── Footer ────────────────────────────────────────────────────────────
        f_footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_footer.pack(side="bottom", fill="x")

        self._divider(self.sidebar, before=f_footer)

        # Profil Peneliti
        f_profil = ctk.CTkFrame(f_footer, fg_color="transparent")
        f_profil.pack(fill="x", padx=14, pady=(8, 4))

        cv2 = tk.Canvas(f_profil, width=30, height=30, bg=T.BG_PANEL, highlightthickness=0)
        cv2.pack(side="left", padx=(0, 8))
        cv2.create_oval(2, 2, 28, 28, fill=T.BG_WIDGET, outline=T.BORDER_NORMAL)
        cv2.create_text(15, 16, text="M", fill=T.AKSEN_PRIMER, font=("Segoe UI", 11, "bold"))

        f_pinfo = ctk.CTkFrame(f_profil, fg_color="transparent")
        f_pinfo.pack(side="left")
        ctk.CTkLabel(f_pinfo, text="M. Akmal Fitrianto",
                     font=("Segoe UI", 9, "bold"), text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(f_pinfo, text="NPM: 2210010546",
                     font=("Segoe UI", 8), text_color=T.TEKS_DISABLED).pack(anchor="w")

        # Tombol Keluar
        ctk.CTkButton(
            f_footer, text="  →  Keluar",
            font=T.FONT_KECIL, height=32, corner_radius=T.RADIUS_BTN,
            fg_color="transparent", text_color=T.AKSEN_DANGER,
            hover_color="#2d1a1a", anchor="w",
            command=self._on_tutup,
        ).pack(fill="x", padx=10, pady=(4, 12))

    def _buat_tombol_nav(self, parent, teks: str, frame_id: str) -> ctk.CTkButton:
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
        self.frames: dict[str, ctk.CTkFrame] = {}
        kelas = {
            "dashboard":   FrameDashboard,
            "embedding":   FrameEmbedding,
            "extraction":  FrameExtraction,
            "evaluasi":    FrameEvaluasi,
            "history":     FrameHistory,
            "laporan":     FrameLaporan,
            "konfigurasi": FrameKonfigurasi,
        }
        for nama, Kelas in kelas.items():
            frame = Kelas(parent=self.content_area, controller=self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[nama] = frame

    # ── Navigasi ──────────────────────────────────────────────────────────────

    def navigasi_ke(self, frame_id: str) -> None:
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

        self._update_highlight(frame_id)
        logger.debug(f"Navigasi → '{frame_id}'")

    def _update_highlight(self, aktif: str) -> None:
        SETTINGS_IDS = {"konfigurasi"}
        for fid, btn in self._tombol_nav.items():
            if fid == aktif:
                if fid in SETTINGS_IDS:
                    btn.configure(fg_color=T.BG_HOVER, text_color=T.TEKS_PRIMER, font=T.FONT_SIDEBAR_AKT)
                else:
                    btn.configure(fg_color=T.AKSEN_PRIMER, text_color=T.BG_APP, font=T.FONT_SIDEBAR_AKT)
            else:
                btn.configure(fg_color="transparent", text_color=T.TEKS_SEKUNDER, font=T.FONT_SIDEBAR)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _divider(parent, before=None) -> None:
        d = ctk.CTkFrame(parent, height=1, fg_color=T.BORDER_SUBTLE, corner_radius=0)
        if before:
            d.pack(fill="x", pady=(0, 4), before=before)
        else:
            d.pack(fill="x", pady=8)

    @staticmethod
    def _label_seksi(parent, teks: str) -> None:
        ctk.CTkLabel(parent, text=f"  {teks}", font=("Segoe UI", 9, "bold"),
                     text_color=T.TEKS_DISABLED, anchor="w").pack(fill="x", padx=16, pady=(8, 4))

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_tutup(self) -> None:
        if not messagebox.askyesno("Keluar", "Yakin ingin menutup aplikasi?"):
            return
        logger.info("Menutup aplikasi...")
        try:
            self.db.tutup()
        except Exception as e:
            logger.warning(f"Error tutup DB: {e}")
        finally:
            self.destroy()