import sqlite3
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Konfigurasi Logging ────────────────────────────────────────────────────────
# Menggunakan logger khusus per-modul agar output tidak bercampur dengan
# logger dari modul lain di aplikasi.
logger = logging.getLogger(__name__)


# ── Konstanta ──────────────────────────────────────────────────────────────────
# Mendefinisikan path database secara dinamis relatif terhadap lokasi file ini,
# sehingga aplikasi tetap berjalan dari direktori manapun.
_DB_DIR = Path(__file__).resolve().parent
DB_PATH = _DB_DIR / "stego_history.db"

# Query DDL (Data Definition Language) untuk membuat tabel jika belum ada.
# Menggunakan 'IF NOT EXISTS' agar aman dipanggil berkali-kali saat startup.
_DDL_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tb_history (
    id_history  INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_file   VARCHAR(255)    NOT NULL,
    ukuran_pesan INTEGER        NOT NULL,
    kunci_seed  VARCHAR(255)    NOT NULL,
    nilai_psnr  REAL,
    nilai_mse   REAL,
    waktu_simpan TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);
"""


# ── Data Class untuk Representasi Baris Tabel ─────────────────────────────────
@dataclass
class HistoryRecord:
    
    nama_file:    str
    ukuran_pesan: int
    kunci_seed:   str
    nilai_psnr:   Optional[float] = None
    nilai_mse:    Optional[float] = None
    # Field berikut hanya terisi ketika record di-fetch dari database
    id_history:   Optional[int]      = field(default=None, repr=False)
    waktu_simpan: Optional[datetime] = field(default=None, repr=False)


# ── Kelas Utama DatabaseManager ───────────────────────────────────────────────
class DatabaseManager:

    _instance: Optional["DatabaseManager"] = None  # Penyimpan instance Singleton

    def __new__(cls) -> "DatabaseManager":
        
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connection = None  # Inisialisasi atribut koneksi
        return cls._instance

    def __init__(self) -> None:
        
        if self._connection is None:
            self._buka_koneksi()
            self._inisialisasi_skema()

    # ── Private Methods ───────────────────────────────────────────────────────

    def _buka_koneksi(self) -> None:
        
        try:
            self._connection = sqlite3.connect(
                database=str(DB_PATH),
                check_same_thread=False,
                isolation_level=None,       # Autocommit mode
            )
            # Mengaktifkan Row Factory agar hasil query bisa diakses
            # seperti dictionary: row["nama_file"] bukan row[1]
            self._connection.row_factory = sqlite3.Row
            logger.info(f"Koneksi database berhasil dibuka: {DB_PATH}")
        except sqlite3.Error as e:
            logger.critical(f"Gagal membuka koneksi database: {e}")
            raise  # Re-raise agar aplikasi utama bisa menangani

    def _inisialisasi_skema(self) -> None:
        
        try:
            self._connection.execute(_DDL_CREATE_TABLE)
            logger.info("Skema tabel tb_history siap digunakan.")
        except sqlite3.Error as e:
            logger.error(f"Gagal menginisialisasi skema database: {e}")
            raise

    def _pastikan_koneksi(self) -> None:
        
        if self._connection is None:
            raise ConnectionError(
                "Koneksi database belum aktif. Panggil DatabaseManager() terlebih dahulu."
            )

    # ── Public Methods (CRUD) ─────────────────────────────────────────────────

    def simpan_riwayat(self, record: HistoryRecord) -> int:
        
        self._pastikan_koneksi()

        query = """
            INSERT INTO tb_history
                (nama_file, ukuran_pesan, kunci_seed, nilai_psnr, nilai_mse)
            VALUES
                (:nama_file, :ukuran_pesan, :kunci_seed, :nilai_psnr, :nilai_mse)
        """
        # Menggunakan named parameters (:nama) untuk keterbacaan dan keamanan
        # dari SQL Injection (meskipun input internal, ini adalah praktik terbaik).
        params = {
            "nama_file":    record.nama_file,
            "ukuran_pesan": record.ukuran_pesan,
            "kunci_seed":   record.kunci_seed,
            "nilai_psnr":   record.nilai_psnr,
            "nilai_mse":    record.nilai_mse,
        }

        try:
            cursor = self._connection.execute(query, params)
            new_id = cursor.lastrowid
            logger.info(
                f"Riwayat disimpan — ID: {new_id} | File: '{record.nama_file}' "
                f"| PSNR: {record.nilai_psnr:.4f} dB"
            )
            return new_id
        except sqlite3.Error as e:
            logger.error(f"Gagal menyimpan riwayat: {e}")
            raise

    def ambil_semua(self, urutan: str = "DESC") -> list[HistoryRecord]:
        
        self._pastikan_koneksi()

        # Validasi input untuk mencegah SQL Injection pada klausa ORDER BY
        # (parameter binding tidak bisa digunakan untuk nama kolom/arah sort)
        if urutan.upper() not in ("ASC", "DESC"):
            raise ValueError(f"Nilai 'urutan' tidak valid: '{urutan}'. Gunakan 'ASC' atau 'DESC'.")

        query = f"SELECT * FROM tb_history ORDER BY waktu_simpan {urutan.upper()}"

        try:
            cursor = self._connection.execute(query)
            rows = cursor.fetchall()
            # Konversi setiap sqlite3.Row menjadi HistoryRecord untuk keamanan tipe data
            return [self._row_ke_record(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Gagal mengambil semua riwayat: {e}")
            raise

    def ambil_berdasarkan_id(self, id_history: int) -> Optional[HistoryRecord]:
        
        self._pastikan_koneksi()
        query = "SELECT * FROM tb_history WHERE id_history = ?"
        try:
            cursor = self._connection.execute(query, (id_history,))
            row = cursor.fetchone()
            return self._row_ke_record(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Gagal mengambil riwayat ID={id_history}: {e}")
            raise

    def hapus_riwayat(self, id_history: int) -> bool:
        
        self._pastikan_koneksi()
        query = "DELETE FROM tb_history WHERE id_history = ?"
        try:
            cursor = self._connection.execute(query, (id_history,))
            terhapus = cursor.rowcount > 0
            if terhapus:
                logger.info(f"Riwayat ID={id_history} berhasil dihapus.")
            else:
                logger.warning(f"Tidak ada riwayat dengan ID={id_history}.")
            return terhapus
        except sqlite3.Error as e:
            logger.error(f"Gagal menghapus riwayat ID={id_history}: {e}")
            raise

    def hitung_total_riwayat(self) -> int:
        
        self._pastikan_koneksi()
        try:
            cursor = self._connection.execute("SELECT COUNT(*) FROM tb_history")
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Gagal menghitung total riwayat: {e}")
            raise

    def tutup(self) -> None:
        
        if self._connection:
            self._connection.close()
            self._connection = None
            DatabaseManager._instance = None   
            logger.info("Koneksi database ditutup dengan aman.")

    # ── Helper / Utility ──────────────────────────────────────────────────────

    @staticmethod
    def _row_ke_record(row: sqlite3.Row) -> HistoryRecord:
        
        return HistoryRecord(
            id_history=row["id_history"],
            nama_file=row["nama_file"],
            ukuran_pesan=row["ukuran_pesan"],
            kunci_seed=row["kunci_seed"],
            nilai_psnr=row["nilai_psnr"],
            nilai_mse=row["nilai_mse"],
            waktu_simpan=row["waktu_simpan"],
        )