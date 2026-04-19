"""
================================================================================
FILE    : main.py
PROJECT : Stego MWC — Steganografi LSB + PRNG Multiply-With-Carry
DESKRIPSI:
    Entry point (titik masuk) utama aplikasi.
    Jalankan file ini untuk memulai aplikasi:

        python main.py

    YANG DILAKUKAN FILE INI:
      1. Mengonfigurasi sistem logging ke konsol + file log.
      2. Memastikan direktori kerja Python sudah benar (untuk import relatif).
      3. Membuat dan menjalankan instance AppMain (CustomTkinter event loop).
================================================================================
"""

import logging
import sys
from pathlib import Path

# ── Pastikan root project ada di sys.path ────────────────────────────────────
# Diperlukan agar semua import relatif (from engine.xxx import ...) berfungsi
# dengan benar saat file ini dijalankan dari direktori manapun.
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ── Konfigurasi Logging ───────────────────────────────────────────────────────
def _setup_logging() -> None:
    """
    Mengatur sistem logging untuk seluruh aplikasi.

    Output ke DUA tujuan sekaligus:
      1. Konsol (stdout) — untuk monitoring saat development di terminal.
      2. File 'stego_app.log' — untuk menyimpan log permanen di direktori proyek.

    Format log mencakup: timestamp, nama modul, level, dan pesan.
    """
    log_format = "[%(asctime)s] %(name)-28s %(levelname)-8s %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(ROOT_DIR / "stego_app.log", encoding="utf-8"),
        ],
    )

    # Kurangi verbositas library pihak ketiga agar log tidak terlalu bising
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("customtkinter").setLevel(logging.WARNING)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Stego MWC — Aplikasi Steganografi LSB + PRNG")
    logger.info("=" * 60)

    try:
        from ui.app_main import AppMain

        app = AppMain()
        logger.info("Event loop CustomTkinter dimulai.")
        app.mainloop()

    except ImportError as e:
        logger.critical(
            f"Gagal mengimpor modul: {e}\n"
            "Pastikan semua dependensi sudah terinstall:\n"
            "  pip install customtkinter Pillow numpy opencv-python"
        )
        sys.exit(1)

    except Exception as e:
        logger.critical(f"Error fatal saat startup: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logger.info("Aplikasi ditutup.")