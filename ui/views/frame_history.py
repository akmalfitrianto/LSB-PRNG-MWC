"""
================================================================================
MODULE  : ui/views/frame_history.py
REVISI  : + Search bar, + Ekspor ke CSV (GAP 3)
DESKRIPSI:
    Halaman Riwayat — tabel semua operasi embedding beserta PSNR, MSE,
    dan waktu. Dilengkapi pencarian nama file dan ekspor CSV.
================================================================================
"""

import csv
import logging
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ui import theme as T

logger = logging.getLogger(__name__)

_KOLOM_TABEL = [
    ("id_history",   "ID",            52,  "center"),
    ("nama_file",    "Nama File",     185, "w"),
    ("ukuran_pesan", "Ukuran (byte)", 110, "center"),
    ("nilai_psnr",   "PSNR (dB)",     110, "center"),
    ("nilai_mse",    "MSE",           110, "center"),
    ("kunci_seed",   "Kunci MWC",     100, "center"),
    ("waktu_simpan", "Waktu Simpan",  155, "center"),
]


class FrameHistory(ctk.CTkFrame):
    """Frame halaman Riwayat dengan search + CSV export."""

    def __init__(self, parent: ctk.CTkFrame, controller) -> None:
        super().__init__(parent, fg_color=T.BG_APP, corner_radius=0)
        self.controller = controller

        self._baris_terpilih_idx: int | None = None
        self._baris_frames: list[ctk.CTkFrame] = []
        self._data_riwayat: list = []        # Semua record dari DB
        self._data_tampil:  list = []        # Record setelah difilter search

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._bangun_ui()

    # ── UI Builder ────────────────────────────────────────────────────────────

    def _bangun_ui(self) -> None:
        # ── Header ────────────────────────────────────────────────────────────
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))

        # Baris judul + tombol aksi
        judul_row = ctk.CTkFrame(frame_header, fg_color="transparent")
        judul_row.pack(fill="x")

        ctk.CTkLabel(judul_row, text="Riwayat", font=T.FONT_JUDUL,
                     text_color=T.TEKS_PRIMER).pack(side="left")

        # Tombol Ekspor CSV (kanan)
        ctk.CTkButton(
            judul_row, text="  ↓  Ekspor CSV",
            font=T.FONT_LABEL, height=34, corner_radius=T.RADIUS_BTN,
            fg_color=T.BTN_SEKUNDER_BG, text_color=T.AKSEN_SEKUNDER,
            hover_color=T.BG_HOVER,
            border_width=1, border_color=T.AKSEN_SEKUNDER,
            command=self._ekspor_csv,
        ).pack(side="right", padx=(8, 0))

        # Tombol Hapus
        self._btn_hapus = ctk.CTkButton(
            judul_row, text="  Hapus Terpilih",
            font=T.FONT_LABEL, height=34, corner_radius=T.RADIUS_BTN,
            fg_color=T.BG_WIDGET, text_color=T.AKSEN_DANGER,
            hover_color="#2d1a1a",
            border_width=1, border_color=T.AKSEN_DANGER,
            command=self._hapus_terpilih, state="disabled",
        ).pack(side="right", padx=(8, 0))

        # Tombol Refresh
        ctk.CTkButton(
            judul_row, text="  ↺  Refresh",
            font=T.FONT_LABEL, height=34, corner_radius=T.RADIUS_BTN,
            fg_color=T.BTN_SEKUNDER_BG, text_color=T.TEKS_PRIMER,
            hover_color=T.BG_HOVER, command=self._muat_data,
        ).pack(side="right")

        ctk.CTkLabel(frame_header, text="Semua operasi embedding yang pernah dilakukan",
                     font=T.FONT_LABEL, text_color=T.TEKS_SEKUNDER).pack(anchor="w", pady=(2, 0))

        # ── Search Bar ────────────────────────────────────────────────────────
        frame_search = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_search.pack(fill="x", pady=(10, 0))

        self._entry_search = ctk.CTkEntry(
            frame_search,
            placeholder_text="🔍  Cari nama file...",
            font=T.FONT_LABEL,
            fg_color=T.BG_PANEL,
            border_color=T.BORDER_NORMAL,
            text_color=T.TEKS_PRIMER,
            height=36,
            corner_radius=T.RADIUS_ENTRY,
        )
        self._entry_search.pack(side="left", fill="x", expand=True)
        self._entry_search.bind("<KeyRelease>", self._on_search)

        self._lbl_jumlah_hasil = ctk.CTkLabel(
            frame_search, text="", font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER,
        )
        self._lbl_jumlah_hasil.pack(side="left", padx=12)

        ctk.CTkFrame(frame_header, height=2, fg_color=T.AKSEN_WARNING,
                     corner_radius=1).pack(fill="x", pady=(10, 0))

        # ── Kontainer Tabel ───────────────────────────────────────────────────
        frame_tbl_outer = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        frame_tbl_outer.grid(row=1, column=0, sticky="nsew", padx=32, pady=20)
        frame_tbl_outer.grid_columnconfigure(0, weight=1)
        frame_tbl_outer.grid_rowconfigure(1, weight=1)

        self._bangun_header_kolom(frame_tbl_outer)

        self._scroll_baris = ctk.CTkScrollableFrame(
            frame_tbl_outer, fg_color="transparent",
            scrollbar_button_color=T.BORDER_NORMAL,
        )
        self._scroll_baris.grid(row=1, column=0, sticky="nsew")

        self._lbl_kosong = ctk.CTkLabel(
            self._scroll_baris,
            text="Belum ada riwayat.\nMulai dari menu Embedding untuk mencatat operasi pertama.",
            font=T.FONT_LABEL, text_color=T.TEKS_DISABLED,
        )

        # Footer
        frame_footer = ctk.CTkFrame(frame_tbl_outer, fg_color=T.BG_WIDGET,
                                     corner_radius=0)
        frame_footer.grid(row=2, column=0, sticky="ew")
        self._lbl_footer      = ctk.CTkLabel(frame_footer, text="", font=T.FONT_KECIL, text_color=T.TEKS_SEKUNDER)
        self._lbl_footer.pack(side="left", padx=14, pady=8)
        self._lbl_footer_psnr = ctk.CTkLabel(frame_footer, text="", font=T.FONT_KECIL, text_color=T.AKSEN_PRIMER)
        self._lbl_footer_psnr.pack(side="right", padx=14, pady=8)

    def _bangun_header_kolom(self, parent: ctk.CTkFrame) -> None:
        """Header kolom tabel yang fixed (tidak scroll)."""
        f_head = ctk.CTkFrame(parent, fg_color=T.BG_WIDGET, corner_radius=0)
        f_head.grid(row=0, column=0, sticky="ew")
        for i, (_, label, lebar, anchor) in enumerate(_KOLOM_TABEL):
            ctk.CTkLabel(
                f_head, text=label,
                font=("Segoe UI", 10, "bold"), text_color=T.TEKS_SEKUNDER,
                width=lebar, anchor=anchor,
            ).grid(row=0, column=i, padx=8, pady=10, sticky="ew")
        ctk.CTkFrame(parent, height=1, fg_color=T.BORDER_NORMAL,
                     corner_radius=0).grid(row=0, column=0, sticky="sew")

    # ── Data ──────────────────────────────────────────────────────────────────

    def _muat_data(self) -> None:
        """Ambil semua data dari DB dan render tabel."""
        try:
            self._data_riwayat = self.controller.db.ambil_semua(urutan="DESC")
        except Exception as e:
            logger.error(f"Gagal memuat riwayat: {e}")
            messagebox.showerror("Error Database", f"Gagal memuat riwayat:\n{e}")
            return

        # Reset search
        self._entry_search.delete(0, "end")
        self._data_tampil = list(self._data_riwayat)
        self._render_tabel()
        self._update_footer()
        self._baris_terpilih_idx = None
        self._btn_hapus.configure(state="disabled")

    def _on_search(self, event=None) -> None:
        """Filter tabel berdasarkan teks di search bar."""
        kata = self._entry_search.get().strip().lower()
        if not kata:
            self._data_tampil = list(self._data_riwayat)
        else:
            self._data_tampil = [
                r for r in self._data_riwayat
                if kata in r.nama_file.lower()
            ]
        self._baris_terpilih_idx = None
        self._btn_hapus.configure(state="disabled")
        self._render_tabel()
        self._update_footer()

    # ── Render Tabel ──────────────────────────────────────────────────────────

    def _render_tabel(self) -> None:
        for frame in self._baris_frames:
            frame.destroy()
        self._baris_frames.clear()

        if not self._data_tampil:
            teks = (
                "Tidak ada hasil yang cocok untuk pencarian ini."
                if self._entry_search.get().strip()
                else "Belum ada riwayat embedding."
            )
            self._lbl_kosong.configure(text=teks)
            self._lbl_kosong.pack(expand=True, pady=40)
            return

        self._lbl_kosong.pack_forget()
        for idx, record in enumerate(self._data_tampil):
            self._buat_baris(idx, record)

    def _buat_baris(self, idx: int, record) -> None:
        """Membuat satu baris tabel dengan zebra striping."""
        bg = T.BG_PANEL if idx % 2 == 0 else T.BG_WIDGET

        frame_baris = ctk.CTkFrame(self._scroll_baris, fg_color=bg,
                                   corner_radius=0, cursor="hand2")
        frame_baris.pack(fill="x")

        # Format nilai tiap kolom
        psnr_val = record.nilai_psnr
        nilai = {
            "id_history":   str(record.id_history),
            "nama_file":    record.nama_file,
            "ukuran_pesan": f"{record.ukuran_pesan:,} B",
            "nilai_psnr":   f"{psnr_val:.4f}" if psnr_val is not None else "—",
            "nilai_mse":    f"{record.nilai_mse:.6f}" if record.nilai_mse is not None else "—",
            "kunci_seed":   "●" * min(len(record.kunci_seed), 6),
            "waktu_simpan": str(record.waktu_simpan)[:19] if record.waktu_simpan else "—",
        }

        # Warna PSNR
        warna_psnr = T.TEKS_PRIMER
        if psnr_val is not None:
            if psnr_val >= 50:   warna_psnr = T.AKSEN_SUKSES
            elif psnr_val >= 40: warna_psnr = T.AKSEN_PRIMER
            elif psnr_val >= 30: warna_psnr = T.AKSEN_WARNING
            else:                warna_psnr = T.AKSEN_DANGER

        for col_i, (key, _, lebar, anchor) in enumerate(_KOLOM_TABEL):
            warna = warna_psnr if key == "nilai_psnr" else T.TEKS_PRIMER
            font  = T.FONT_MONO_KECIL if key in ("nilai_psnr", "nilai_mse", "id_history") else T.FONT_KECIL
            lbl   = ctk.CTkLabel(frame_baris, text=nilai.get(key, "—"),
                                  font=font, text_color=warna, width=lebar, anchor=anchor)
            lbl.grid(row=0, column=col_i, padx=8, pady=7, sticky="ew")

        # Binding klik baris
        for w in [frame_baris] + list(frame_baris.winfo_children()):
            w.bind("<Button-1>", lambda e, i=idx: self._pilih_baris(i))

        ctk.CTkFrame(self._scroll_baris, height=1, fg_color=T.BORDER_SUBTLE,
                     corner_radius=0).pack(fill="x")
        self._baris_frames.append(frame_baris)

    # ── Interaksi ─────────────────────────────────────────────────────────────

    def _pilih_baris(self, idx: int) -> None:
        """Highlight baris terpilih."""
        # Reset highlight lama
        if self._baris_terpilih_idx is not None:
            old = self._baris_terpilih_idx
            if old < len(self._baris_frames):
                bg = T.BG_PANEL if old % 2 == 0 else T.BG_WIDGET
                self._baris_frames[old].configure(fg_color=bg)
                for w in self._baris_frames[old].winfo_children():
                    if isinstance(w, ctk.CTkLabel):
                        w.configure(fg_color=bg)

        self._baris_terpilih_idx = idx
        if idx < len(self._baris_frames):
            self._baris_frames[idx].configure(fg_color="#1a2a3a")
            for w in self._baris_frames[idx].winfo_children():
                if isinstance(w, ctk.CTkLabel):
                    w.configure(fg_color="#1a2a3a")

        self._btn_hapus.configure(state="normal")

    def _hapus_terpilih(self) -> None:
        """Hapus record yang dipilih setelah konfirmasi."""
        if self._baris_terpilih_idx is None:
            return
        record = self._data_tampil[self._baris_terpilih_idx]
        if not messagebox.askyesno(
            "Konfirmasi Hapus",
            f"Hapus riwayat ini?\n\nID   : {record.id_history}\n"
            f"File : {record.nama_file}\n\nTindakan tidak dapat dibatalkan.",
        ):
            return
        try:
            if self.controller.db.hapus_riwayat(record.id_history):
                self._muat_data()
            else:
                messagebox.showerror("Gagal", f"Record ID={record.id_history} tidak ditemukan.")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menghapus:\n{e}")

    # ── Ekspor CSV ────────────────────────────────────────────────────────────

    def _ekspor_csv(self) -> None:
        """
        Mengekspor data riwayat yang sedang ditampilkan (hasil filter search)
        ke file CSV yang dipilih pengguna.
        """
        if not self._data_tampil:
            messagebox.showinfo("Tidak Ada Data", "Tidak ada data untuk diekspor.")
            return

        path_str = filedialog.asksaveasfilename(
            title="Simpan Riwayat sebagai CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("Semua File", "*.*")],
            initialfile="riwayat_steganografi.csv",
        )
        if not path_str:
            return

        try:
            with open(path_str, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)

                # Header CSV
                writer.writerow([
                    "ID", "Nama File", "Ukuran Pesan (byte)",
                    "Kunci MWC", "PSNR (dB)", "MSE", "Waktu Simpan",
                ])

                # Data rows
                for r in self._data_tampil:
                    writer.writerow([
                        r.id_history,
                        r.nama_file,
                        r.ukuran_pesan,
                        r.kunci_seed,
                        f"{r.nilai_psnr:.4f}" if r.nilai_psnr is not None else "",
                        f"{r.nilai_mse:.6f}"  if r.nilai_mse  is not None else "",
                        str(r.waktu_simpan)[:19] if r.waktu_simpan else "",
                    ])

            n = len(self._data_tampil)
            messagebox.showinfo(
                "Ekspor Berhasil",
                f"{n} record berhasil diekspor ke:\n{Path(path_str).name}",
            )
            logger.info(f"Riwayat diekspor ke CSV: {path_str} ({n} record)")

        except PermissionError:
            messagebox.showerror("Gagal", "Tidak ada izin menulis ke lokasi tersebut.")
        except Exception as e:
            messagebox.showerror("Gagal", f"Gagal mengekspor CSV:\n{e}")

    # ── Footer ────────────────────────────────────────────────────────────────

    def _update_footer(self) -> None:
        total_db    = len(self._data_riwayat)
        total_tampil = len(self._data_tampil)

        if total_tampil < total_db:
            self._lbl_footer.configure(
                text=f"Menampilkan {total_tampil} dari {total_db} record"
            )
        else:
            self._lbl_footer.configure(text=f"{total_db} record")

        self._lbl_jumlah_hasil.configure(
            text=f"{total_tampil} hasil" if self._entry_search.get().strip() else ""
        )

        psnr_vals = [r.nilai_psnr for r in self._data_tampil if r.nilai_psnr is not None]
        if psnr_vals:
            avg = sum(psnr_vals) / len(psnr_vals)
            self._lbl_footer_psnr.configure(text=f"Rata-rata PSNR: {avg:.4f} dB")
        else:
            self._lbl_footer_psnr.configure(text="")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        self._muat_data()

    def on_hide(self) -> None:
        pass