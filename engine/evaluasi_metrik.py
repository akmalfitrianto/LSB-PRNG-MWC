import math
import logging
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Nilai piksel maksimum untuk citra 8-bit (0–255).
# Konstanta ini digunakan dalam rumus PSNR sebagai nilai puncak sinyal.
_NILAI_MAKS_PIKSEL: float = 255.0


# ── Fungsi Pembantu (Private) ─────────────────────────────────────────────────

def _buka_sebagai_array(path_citra: str | Path) -> np.ndarray:
    
    path = Path(path_citra)
    if not path.exists():
        raise FileNotFoundError(f"File citra tidak ditemukan: '{path}'")

    try:
        with Image.open(path) as img:
            img_rgb = img.convert("RGB")
            return np.array(img_rgb, dtype=np.float64)
    except OSError as e:
        raise OSError(f"Gagal membuka file citra '{path}': {e}") from e


def _validasi_dimensi(arr_cover: np.ndarray, arr_stego: np.ndarray) -> None:
    
    if arr_cover.shape != arr_stego.shape:
        raise ValueError(
            f"Dimensi kedua citra tidak sama. "
            f"Cover: {arr_cover.shape}, Stego: {arr_stego.shape}. "
            "Pastikan kedua file adalah citra yang sama (sebelum & sesudah embedding)."
        )


# ── Fungsi Publik Utama ───────────────────────────────────────────────────────

def hitung_mse(
    path_cover: str | Path,
    path_stego: str | Path,
) -> float:
    
    arr_cover = _buka_sebagai_array(path_cover)
    arr_stego = _buka_sebagai_array(path_stego)
    _validasi_dimensi(arr_cover, arr_stego)

    # Hitung selisih piksel, kuadratkan, lalu rata-ratakan seluruh elemen array.
    # np.mean() otomatis merata-ratakan atas semua dimensi (tinggi × lebar × channel).
    selisih = arr_cover - arr_stego
    mse = float(np.mean(selisih ** 2))

    logger.debug(f"MSE dihitung: {mse:.6f}")
    return mse


def hitung_psnr(
    path_cover: str | Path,
    path_stego: str | Path,
    mse: float | None = None,
) -> float:
    
    # Gunakan MSE yang sudah ada jika tersedia, hitung sendiri jika tidak.
    nilai_mse = mse if mse is not None else hitung_mse(path_cover, path_stego)

    if nilai_mse == 0.0:
        logger.debug("MSE = 0: kedua citra identik, PSNR = ∞")
        return float("inf")

    # Terapkan rumus PSNR standar.
    psnr = 10.0 * math.log10((_NILAI_MAKS_PIKSEL ** 2) / nilai_mse)

    logger.debug(f"PSNR dihitung: {psnr:.4f} dB (dari MSE={nilai_mse:.6f})")
    return psnr


def hitung_semua_metrik(
    path_cover: str | Path,
    path_stego: str | Path,
) -> dict[str, float]:
    
    arr_cover = _buka_sebagai_array(path_cover)
    arr_stego = _buka_sebagai_array(path_stego)
    _validasi_dimensi(arr_cover, arr_stego)

    # Hitung MSE langsung dari array yang sudah ada di memori (tanpa buka file lagi)
    selisih = arr_cover - arr_stego
    nilai_mse = float(np.mean(selisih ** 2))

    # Gunakan MSE yang baru dihitung untuk PSNR (tanpa buka file lagi)
    if nilai_mse == 0.0:
        nilai_psnr = float("inf")
    else:
        nilai_psnr = 10.0 * math.log10((_NILAI_MAKS_PIKSEL ** 2) / nilai_mse)

    logger.info(
        f"Metrik kualitas — MSE: {nilai_mse:.6f} | PSNR: {nilai_psnr:.4f} dB"
    )

    return {"mse": nilai_mse, "psnr": nilai_psnr}