import logging
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ui import theme as T

logger = logging.getLogger(__name__)


class FrameLaporan(ctk.CTkFrame):

    def __init__(self, parent: ctk.CTkFrame, controller) -> None:
        super().__init__(parent, fg_color=T.BG_APP, corner_radius=0)
        self.controller = controller

        # State file yang dipilih (dipakai oleh beberapa laporan)
        self._path_cover: Path | None = None
        self._path_stego: Path | None = None
        self._kunci: str = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._bangun_ui()

    # ── UI Builder ────────────────────────────────────────────────────────────

    def _bangun_ui(self) -> None:
        # Header
        f_header = ctk.CTkFrame(self, fg_color="transparent")
        f_header.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 0))
        ctk.CTkLabel(f_header, text="Laporan", font=T.FONT_JUDUL, text_color=T.TEKS_PRIMER).pack(anchor="w")
        ctk.CTkLabel(f_header, text="Ekspor 8 jenis laporan ke format PDF dan Excel",
                     font=T.FONT_LABEL, text_color=T.TEKS_SEKUNDER).pack(anchor="w", pady=(2, 0))
        ctk.CTkFrame(f_header, height=2, fg_color="#a78bfa", corner_radius=1).pack(fill="x", pady=(12, 0))

        # Body scrollable
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                         scrollbar_button_color=T.BORDER_NORMAL)
        scroll.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        scroll.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # ── Panel input file (dipakai laporan 2–8) ────────────────────────────
        self._bangun_panel_input(scroll)

        # ── 8 Kartu Laporan ───────────────────────────────────────────────────
        laporan_defs = [
            (1, "Rekapitulasi\nMetrik Kualitas",
             "Tabel semua riwayat embedding beserta PSNR, MSE, dan grafik batang.",
             ["PDF", "Excel"], self._ekspor_lap1_pdf, self._ekspor_lap1_excel),
            (2, "Analisis\nHistogram Citra",
             "Perbandingan histogram RGB cover vs stego + grafik selisih Δ.",
             ["PDF"], self._ekspor_lap2_pdf, None),
            (3, "Visualisasi\nSebaran Bit",
             "Noise map binary, overlay teal, dan scatter koordinat MWC.",
             ["PDF"], self._ekspor_lap3_pdf, None),
            (4, "Degradasi Kualitas\nvs Kapasitas",
             "Grafik tren PSNR dan MSE terhadap pertambahan ukuran payload.",
             ["PDF"], self._ekspor_lap4_pdf, None),
            (5, "Komparasi Visual\n(HVS Test)",
             "Side-by-side cover vs stego + citra diferensi yang diamplifikasi.",
             ["PDF"], self._ekspor_lap5_pdf, None),
            (6, "Analisis\nSensitivitas Kunci",
             "Buktikan hanya kunci benar yang bisa mengekstrak pesan valid.",
             ["PDF"], self._ekspor_lap6_pdf, None),
            (7, "Output Pesan &\nIntegritas Data",
             "Verifikasi 100% kesesuaian pesan input vs pesan hasil ekstraksi.",
             ["PDF"], self._ekspor_lap7_pdf, None),
            (8, "Ringkasan Pengujian\nTunggal",
             "Dashboard komprehensif satu halaman — semua metrik & visualisasi.",
             ["PDF"], self._ekspor_lap8_pdf, None),
        ]

        for i, (nomor, judul, deskripsi, format_list, fn_pdf, fn_excel) in enumerate(laporan_defs):
            row = i // 4 + 1   # mulai dari row 1 (row 0 = panel input)
            col = i % 4
            self._buat_kartu(scroll, row, col, nomor, judul, deskripsi, format_list, fn_pdf, fn_excel)

    def _bangun_panel_input(self, parent: ctk.CTkScrollableFrame) -> None:
        """Panel pilih file — dipakai oleh laporan 2–8."""
        f = ctk.CTkFrame(parent, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        f.grid(row=0, column=0, columnspan=4, sticky="ew", padx=4, pady=(0, 16))

        ctk.CTkLabel(f, text="File Input untuk Laporan (Laporan 2–8)",
                     font=T.FONT_LABEL_BOLD, text_color=T.TEKS_SEKUNDER).pack(anchor="w", padx=16, pady=(14, 8))
        ctk.CTkFrame(f, height=1, fg_color=T.BORDER_SUBTLE).pack(fill="x", padx=16)

        f_row = ctk.CTkFrame(f, fg_color="transparent")
        f_row.pack(fill="x", padx=16, pady=12)
        f_row.grid_columnconfigure((1, 3), weight=1)

        # Cover
        ctk.CTkLabel(f_row, text="Cover:", font=T.FONT_LABEL_BOLD,
                     text_color=T.TEKS_SEKUNDER, width=55).grid(row=0, column=0, padx=(0, 6))
        self._entry_cover = ctk.CTkEntry(f_row, placeholder_text="Pilih citra cover...",
                                          font=T.FONT_MONO_KECIL, fg_color=T.BG_WIDGET,
                                          border_color=T.BORDER_NORMAL, text_color=T.TEKS_PRIMER,
                                          state="disabled", height=32, corner_radius=T.RADIUS_ENTRY)
        self._entry_cover.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ctk.CTkButton(f_row, text="Pilih", font=T.FONT_KECIL, height=32, width=60,
                      corner_radius=T.RADIUS_BTN, fg_color=T.BTN_SEKUNDER_BG,
                      text_color=T.TEKS_PRIMER, hover_color=T.BG_HOVER,
                      command=lambda: self._pilih_file("cover")).grid(row=0, column=2, padx=(0, 16))

        # Stego
        ctk.CTkLabel(f_row, text="Stego:", font=T.FONT_LABEL_BOLD,
                     text_color=T.TEKS_SEKUNDER, width=55).grid(row=0, column=3, padx=(0, 6))
        self._entry_stego = ctk.CTkEntry(f_row, placeholder_text="Pilih citra stego...",
                                          font=T.FONT_MONO_KECIL, fg_color=T.BG_WIDGET,
                                          border_color=T.BORDER_NORMAL, text_color=T.TEKS_PRIMER,
                                          state="disabled", height=32, corner_radius=T.RADIUS_ENTRY)
        self._entry_stego.grid(row=0, column=4, sticky="ew", padx=(0, 6))
        ctk.CTkButton(f_row, text="Pilih", font=T.FONT_KECIL, height=32, width=60,
                      corner_radius=T.RADIUS_BTN, fg_color=T.BTN_SEKUNDER_BG,
                      text_color=T.TEKS_PRIMER, hover_color=T.BG_HOVER,
                      command=lambda: self._pilih_file("stego")).grid(row=0, column=5)

        # Kunci
        f_kunci = ctk.CTkFrame(f, fg_color="transparent")
        f_kunci.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(f_kunci, text="Kunci:", font=T.FONT_LABEL_BOLD,
                     text_color=T.TEKS_SEKUNDER, width=55).pack(side="left")
        self._entry_kunci = ctk.CTkEntry(f_kunci, placeholder_text="Kunci/password saat embedding...",
                                          show="●", font=T.FONT_LABEL, fg_color=T.BG_WIDGET,
                                          border_color=T.BORDER_NORMAL, text_color=T.TEKS_PRIMER,
                                          height=32, corner_radius=T.RADIUS_ENTRY)
        self._entry_kunci.pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _buat_kartu(
        self,
        parent, row: int, col: int,
        nomor: int, judul: str, deskripsi: str,
        format_list: list[str],
        fn_pdf, fn_excel,
    ) -> None:
        
        warna_strip = [T.AKSEN_PRIMER, T.AKSEN_SEKUNDER, "#a78bfa", T.AKSEN_WARNING,
                       T.AKSEN_SUKSES, T.AKSEN_DANGER, "#f472b6", "#fb923c"][nomor - 1]

        kartu = ctk.CTkFrame(parent, fg_color=T.BG_PANEL, corner_radius=T.RADIUS_CARD)
        kartu.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)

        # Strip warna atas
        ctk.CTkFrame(kartu, height=3, fg_color=warna_strip, corner_radius=2).pack(fill="x")

        # Badge nomor
        f_top = ctk.CTkFrame(kartu, fg_color="transparent")
        f_top.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(f_top, text=str(nomor), width=24, height=24,
                     corner_radius=12, fg_color=warna_strip, text_color=T.BG_APP,
                     font=T.FONT_BADGE).pack(side="left")

        # Format badges
        for fmt in format_list:
            warna_fmt = T.AKSEN_DANGER if fmt == "PDF" else T.AKSEN_SUKSES
            ctk.CTkLabel(f_top, text=fmt, font=T.FONT_BADGE, width=40, height=18,
                         corner_radius=4, fg_color=warna_fmt, text_color=T.BG_APP).pack(side="right", padx=2)

        # Judul & deskripsi
        ctk.CTkLabel(kartu, text=judul, font=T.FONT_LABEL_BOLD,
                     text_color=T.TEKS_PRIMER, justify="left", anchor="w").pack(anchor="w", padx=12, pady=(2, 4))
        ctk.CTkLabel(kartu, text=deskripsi, font=T.FONT_KECIL,
                     text_color=T.TEKS_SEKUNDER, justify="left", anchor="w",
                     wraplength=220).pack(anchor="w", padx=12, pady=(0, 8))

        # Tombol ekspor
        f_btn = ctk.CTkFrame(kartu, fg_color="transparent")
        f_btn.pack(fill="x", padx=10, pady=(0, 12))

        if fn_pdf:
            ctk.CTkButton(f_btn, text="↓ PDF", font=T.FONT_KECIL, height=28,
                          corner_radius=6, fg_color=T.BG_WIDGET,
                          text_color=T.AKSEN_DANGER, hover_color="#2d1a1a",
                          border_width=1, border_color=T.AKSEN_DANGER,
                          command=fn_pdf).pack(side="left", padx=(0, 4))
        if fn_excel:
            ctk.CTkButton(f_btn, text="↓ Excel", font=T.FONT_KECIL, height=28,
                          corner_radius=6, fg_color=T.BG_WIDGET,
                          text_color=T.AKSEN_SUKSES, hover_color="#0d2018",
                          border_width=1, border_color=T.AKSEN_SUKSES,
                          command=fn_excel).pack(side="left")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pilih_file(self, jenis: str) -> None:
        path_str = filedialog.askopenfilename(
            title=f"Pilih Citra {'Cover' if jenis == 'cover' else 'Stego'}",
            filetypes=[("PNG", "*.png"), ("Semua Gambar", "*.png *.jpg *.bmp"), ("Semua", "*.*")],
        )
        if not path_str:
            return
        path = Path(path_str)
        entry = self._entry_cover if jenis == "cover" else self._entry_stego
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, str(path))
        entry.configure(state="disabled")
        if jenis == "cover":
            self._path_cover = path
        else:
            self._path_stego = path

    def _get_kunci(self) -> str:
        return self._entry_kunci.get().strip()

    def _simpan_dialog(self, judul: str, ekstensi: str, nama_default: str) -> Path | None:
        path_str = filedialog.asksaveasfilename(
            title=judul, defaultextension=ekstensi,
            filetypes=[(f"File {ekstensi.upper()}", f"*{ekstensi}"), ("Semua", "*.*")],
            initialfile=nama_default,
        )
        return Path(path_str) if path_str else None

    def _cek_cover_stego(self) -> bool:
        if self._path_cover is None:
            messagebox.showwarning("Input Kurang", "Pilih citra cover di panel Input terlebih dahulu.")
            return False
        if self._path_stego is None:
            messagebox.showwarning("Input Kurang", "Pilih citra stego di panel Input terlebih dahulu.")
            return False
        return True

    def _jalankan_thread(self, fn, *args) -> None:
        """Jalankan fungsi generator laporan di background thread."""
        def _run():
            try:
                hasil = fn(*args)
                self.after(0, lambda p=str(hasil): messagebox.showinfo(
                    "Laporan Berhasil",
                    f"Laporan berhasil diekspor!\n\nFile: {Path(p).name}"
                ))
            except ImportError as e:
                self.after(0, lambda msg=str(e): messagebox.showerror(
                    "Dependensi Kurang",
                    f"Library yang dibutuhkan belum terinstall:\n{msg}\n\n"
                    "Jalankan: pip install matplotlib openpyxl"
                ))
            except Exception as e:
                logger.error(f"Error generate laporan: {e}", exc_info=True)
                self.after(0, lambda msg=str(e): messagebox.showerror("Gagal", f"Error:\n{msg}"))

        threading.Thread(target=_run, daemon=True).start()

    # ── Handler Ekspor per Laporan ────────────────────────────────────────────

    def _ekspor_lap1_pdf(self) -> None:
        path = self._simpan_dialog("Simpan Laporan 1 (PDF)", ".pdf", "laporan_1_metrik.pdf")
        if not path: return
        records = self.controller.db.ambil_semua()
        from engine.report_generator import laporan_1_pdf
        self._jalankan_thread(laporan_1_pdf, records, path)

    def _ekspor_lap1_excel(self) -> None:
        path = self._simpan_dialog("Simpan Laporan 1 (Excel)", ".xlsx", "laporan_1_metrik.xlsx")
        if not path: return
        records = self.controller.db.ambil_semua()
        from engine.report_generator import laporan_1_excel
        self._jalankan_thread(laporan_1_excel, records, path)

    def _ekspor_lap2_pdf(self) -> None:
        if not self._cek_cover_stego(): return
        path = self._simpan_dialog("Simpan Laporan 2 (PDF)", ".pdf", "laporan_2_histogram.pdf")
        if not path: return
        from engine.report_generator import laporan_2_pdf
        self._jalankan_thread(laporan_2_pdf, self._path_cover, self._path_stego, path)

    def _ekspor_lap3_pdf(self) -> None:
        if not self._cek_cover_stego(): return
        path = self._simpan_dialog("Simpan Laporan 3 (PDF)", ".pdf", "laporan_3_noisemap.pdf")
        if not path: return
        kunci = self._get_kunci() or None
        from engine.report_generator import laporan_3_pdf
        self._jalankan_thread(laporan_3_pdf, self._path_cover, self._path_stego, path, kunci)

    def _ekspor_lap4_pdf(self) -> None:
        if self._path_cover is None:
            messagebox.showwarning("Input Kurang", "Pilih citra cover di panel Input.")
            return
        path = self._simpan_dialog("Simpan Laporan 4 (PDF)", ".pdf", "laporan_4_degradasi.pdf")
        if not path: return
        records = self.controller.db.ambil_semua()
        from engine.report_generator import laporan_4_pdf
        self._jalankan_thread(laporan_4_pdf, records, self._path_cover, path)

    def _ekspor_lap5_pdf(self) -> None:
        if not self._cek_cover_stego(): return
        path = self._simpan_dialog("Simpan Laporan 5 (PDF)", ".pdf", "laporan_5_komparasi.pdf")
        if not path: return
        from engine.report_generator import laporan_5_pdf
        self._jalankan_thread(laporan_5_pdf, self._path_cover, self._path_stego, path)

    def _ekspor_lap6_pdf(self) -> None:
        if self._path_stego is None:
            messagebox.showwarning("Input Kurang", "Pilih citra stego di panel Input.")
            return
        kunci = self._get_kunci()
        if not kunci:
            messagebox.showwarning("Input Kurang", "Masukkan kunci di panel Input.")
            return
        path = self._simpan_dialog("Simpan Laporan 6 (PDF)", ".pdf", "laporan_6_sensitivitas_kunci.pdf")
        if not path: return

        # Minta pengguna memasukkan kunci salah untuk uji perbandingan
        kunci_salah = [kunci + "X", kunci[:-1] if len(kunci) > 1 else "wrongkey", "salah123"]
        from engine.report_generator import laporan_6_pdf
        self._jalankan_thread(laporan_6_pdf, self._path_stego, kunci, kunci_salah, path)

    def _ekspor_lap7_pdf(self) -> None:
        if not self._cek_cover_stego(): return
        kunci = self._get_kunci()
        if not kunci:
            messagebox.showwarning("Input Kurang", "Masukkan kunci di panel Input.")
            return
        path = self._simpan_dialog("Simpan Laporan 7 (PDF)", ".pdf", "laporan_7_integritas.pdf")
        if not path: return

        def _generate():
            try:
                from engine.stego_lsb import extract_data
                from engine.report_generator import laporan_7_pdf
                # Baca pesan dari DB terakhir atau ekstrak langsung
                records = self.controller.db.ambil_semua()
                pesan_input = f"[Tidak diketahui — pesan asli tidak tersimpan di DB]"
                if records:
                    pesan_input = f"[Ukuran pesan: {records[0].ukuran_pesan} byte]"
                pesan_output = extract_data(stego_path=self._path_stego, key=kunci)
                hasil = laporan_7_pdf(pesan_input, pesan_output,
                                      self._path_cover, self._path_stego, kunci, path)
                self.after(0, lambda p=str(hasil): messagebox.showinfo(
                    "Laporan Berhasil", f"File: {Path(p).name}"))
            except Exception as e:
                self.after(0, lambda msg=str(e): messagebox.showerror("Gagal", msg))

        threading.Thread(target=_generate, daemon=True).start()

    def _ekspor_lap8_pdf(self) -> None:
        if not self._cek_cover_stego(): return
        kunci = self._get_kunci()
        if not kunci:
            messagebox.showwarning("Input Kurang", "Masukkan kunci di panel Input.")
            return
        path = self._simpan_dialog("Simpan Laporan 8 (PDF)", ".pdf", "laporan_8_ringkasan.pdf")
        if not path: return

        def _generate():
            try:
                import numpy as np
                from engine.stego_lsb import extract_data
                from engine.evaluasi_metrik import hitung_semua_metrik
                from engine.report_generator import laporan_8_pdf

                metrik = hitung_semua_metrik(str(self._path_cover), str(self._path_stego))
                pesan_output = extract_data(stego_path=self._path_stego, key=kunci)
                records = self.controller.db.ambil_semua()
                pesan_input = f"[Pesan asli — ukuran: {records[0].ukuran_pesan} byte]" if records else "[—]"

                hasil = laporan_8_pdf(
                    path_cover=self._path_cover,
                    path_stego=self._path_stego,
                    kunci=kunci,
                    pesan_input=pesan_input,
                    pesan_output=pesan_output,
                    psnr=metrik["psnr"],
                    mse=metrik["mse"],
                    path_output=path,
                )
                self.after(0, lambda p=str(hasil): messagebox.showinfo(
                    "Laporan Berhasil", f"File: {Path(p).name}"))
            except Exception as e:
                logger.error(f"Laporan 8 error: {e}", exc_info=True)
                self.after(0, lambda msg=str(e): messagebox.showerror("Gagal", msg))

        threading.Thread(target=_generate, daemon=True).start()

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass