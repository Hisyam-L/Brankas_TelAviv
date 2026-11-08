"""Script utilitas untuk mendaftarkan USB flashdisk sebagai dongle SafeVault."""
from __future__ import annotations

import sys
from auth.dongle import DongleError, DongleManager


def main() -> None:
    mgr = DongleManager()
    mounts = list(mgr.mounts_fn())

    if not mounts:
        print("Tidak ada drive USB yang terdeteksi.")
        print("Silakan tancapkan flashdisk terlebih dahulu.")
        return

    print("=== Pendaftaran USB Dongle SafeVault ===")
    print("Daftar titik mount yang terdeteksi:")
    for idx, m in enumerate(mounts, 1):
        print(f"  [{idx}] {m}")

    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        # Default pilih mount non-root jika ada
        non_root = [m for m in mounts if not m.startswith(("/boot", "/run/user")) and m != "/"]
        target = non_root[-1] if non_root else mounts[-1]

    print(f"\nMendaftarkan flashdisk: {target}")
    try:
        mgr.register(target, allow_overwrite=True)
        print("✓ SUKSES!")
        print("  1. Token '.safevault_dongle.json' (salt + secret) ditulis ke flashdisk.")
        print("  2. Hash SHA-256 (salt + secret + UUID) disimpan di 'data/dongle.json'.")
        status = mgr.verify()
        print(f"  3. Status verifikasi: {status.message} ({status.mount})")
        print("\nSekarang jalankan aplikasi dengan: python main.py")
    except DongleError as e:
        print(f"Gagal: {e}")


if __name__ == "__main__":
    main()
