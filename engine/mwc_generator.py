import hashlib
from typing import Generator


# ── Konstanta Algoritma MWC ───────────────────────────────────────────────────
# Nilai 'a' direkomendasikan Marsaglia (2003) — menghasilkan periode ~2⁶⁰
_MULTIPLIER_A: int = 36_969     # Konstanta pengali (a) pada Persamaan 2.1 & 2.2
_MODULUS_B:    int = 65_536     # Modulus b = 2¹⁶ = 65.536


# ── Fungsi Utilitas ───────────────────────────────────────────────────────────

def password_ke_seed(password: str) -> tuple[int, int]:
    
    if not password or not password.strip():
        raise ValueError("Password/kunci tidak boleh kosong.")

    hash_bytes = hashlib.sha256(password.encode("utf-8")).digest()
    seed_32    = int.from_bytes(hash_bytes[:4], byteorder="big")

    X0 = seed_32 & 0xFFFF           # 16 bit bawah → nilai awal X (Pers. 2.1)
    C0 = (seed_32 >> 16) & 0xFFFF   # 16 bit atas  → nilai awal C (Pers. 2.2)

    # Guard: state nol menyebabkan MWC menghasilkan 0 selamanya (degenerate)
    if X0 == 0:
        X0 = 1
    if C0 == 0:
        C0 = 1

    return X0, C0


# ── Kelas Utama MWCGenerator ──────────────────────────────────────────────────

class MWCGenerator:

    def __init__(self, password: str) -> None:
        
        self._X, self._C = password_ke_seed(password)
        self._seed_info  = f"X₀={self._X}, C₀={self._C}"

        # Warm-up: jalankan 10 iterasi agar output pertama tidak terlalu
        # dekat dengan nilai seed awal (menghindari output yang terprediksi)
        for _ in range(10):
            self._next()

    # ── Core Algorithm ────────────────────────────────────────────────────────

    def _next(self) -> int:
        
        # Hitung intermediate t = a · Xₙ₋₁ + Cₙ₋₁
        t: int = _MULTIPLIER_A * self._X + self._C

        # Persamaan (2.1): Xₙ = t mod b
        self._X = t & 0xFFFF      # setara: t % _MODULUS_B, tapi lebih cepat

        # Persamaan (2.2): Cₙ = ⌊t / b⌋
        self._C = t >> 16         # setara: t // _MODULUS_B, tapi lebih cepat

        return t                  # 32-bit output untuk Fisher-Yates

    # ── Public Interface ──────────────────────────────────────────────────────

    def stream_angka(self) -> Generator[int, None, None]:
        
        while True:
            yield self._next()

    def hasilkan_koordinat(
        self,
        lebar: int,
        tinggi: int,
        jumlah: int,
    ) -> list[tuple[int, int]]:
        
        # ── Validasi ──────────────────────────────────────────────────────────
        if lebar <= 0 or tinggi <= 0:
            raise ValueError(
                f"Dimensi citra tidak valid: {lebar}×{tinggi}. Harus > 0."
            )
        kapasitas = lebar * tinggi
        if jumlah > kapasitas:
            raise ValueError(
                f"Jumlah koordinat ({jumlah:,}) melebihi total piksel citra "
                f"({kapasitas:,} = {lebar}×{tinggi}). "
                "Gunakan citra lebih besar atau pesan lebih pendek."
            )
        if jumlah <= 0:
            raise ValueError(f"Jumlah koordinat harus positif, diterima: {jumlah}.")

        # ── Pool Koordinat Sekuensial ─────────────────────────────────────────
        pool: list[tuple[int, int]] = [
            (x, y)
            for y in range(tinggi)
            for x in range(lebar)
        ]

        # ── Partial Fisher-Yates Shuffle via MWC ─────────────────────────────
        n = kapasitas
        for i in range(n - 1, n - 1 - jumlah, -1):
            # j = output MWC (Pers. 2.1 & 2.2) mod (i+1) → indeks acak [0, i]
            j = self._next() % (i + 1)
            pool[i], pool[j] = pool[j], pool[i]

        # Kembalikan 'jumlah' elemen terakhir (hasil shuffle)
        return pool[n - jumlah:]

    def get_state(self) -> dict:
        
        return {
            "X_saat_ini":  self._X,
            "C_saat_ini":  self._C,
            "multiplier_a": _MULTIPLIER_A,
            "modulus_b":    _MODULUS_B,
            "seed_info":   self._seed_info,
        }

    def __repr__(self) -> str:
        return (
            f"MWCGenerator("
            f"a={_MULTIPLIER_A}, b={_MODULUS_B}, "
            f"seed=[{self._seed_info}], "
            f"state=[X={self._X}, C={self._C}])"
        )