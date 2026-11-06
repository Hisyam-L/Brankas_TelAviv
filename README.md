# 🔐 SafeVault — Brankas Digital Kriptografi

**SafeVault** adalah aplikasi desktop brankas digital berbasis Python dan CustomTkinter yang mengintegrasikan berbagai mekanisme kriptografi klasik, modern, steganografi citra, buku besar blockchain sederhana, dan autentikasi multi-faktor (perangkat keras USB dongle, biometrik wajah, dan kata sandi). Proyek ini disusun sebagai tugas akhir mata kuliah **Kriptografi**.

---

## 📋 Pemetaan Fitur terhadap Kriteria Penilaian Dosen

| No | Kriteria Wajib Dosen | Implementasi pada SafeVault | Modul Terkait |
|:--:|:----------------------|:----------------------------|:--------------|
| 1 | **Login biometrik & wajib bantuan dongle** | Autentikasi 3 tahap: Dongle fisik USB wajib terhubung (`UsbSerialDongle` / `pyudev`), verifikasi biometrik wajah (`FaceAuth` via Haar Cascade + LBPH OpenCV), dan verifikasi password. | `auth/dongle.py`, `auth/face_auth.py`, `ui/login_window.py` |
| 2 | **Login memakai algoritma kriptografi** | Kata sandi di-hash menggunakan algoritma **bcrypt** dengan salt acak 128-bit, diverifikasi secara *constant-time*. | `auth/password_auth.py` |
| 3 | **Super enkripsi pada pesan teks** | Penggabungan cipher klasik dan modern bertingkat: **Vigenère Cipher (Substitusi)** → **Rail Fence Cipher (Transposisi)** → **AES-256-GCM (Modern Terotentikasi)** dengan KDF PBKDF2. | `crypto/classic_algoritma.py`, `crypto/super_enkripsi.py`, `ui/text_page.py` |
| 4 | **Enkripsi berkas berbeda dari teks** | Berkas dienkripsi menggunakan stream cipher modern **ChaCha20-Poly1305** dengan KDF **scrypt**, diproses per chunk 1 MB dengan otentikasi data tambahan (AAD) counter urutan. | `crypto/file_enkripsi.py`, `crypto/file_crypto.py`, `ui/file_page.py` |
| 5 | **Pesan penting dienkripsi pada database** | Database SQLite menyimpan pesan teks rahasia dan kredensial akun dalam keadaan ciphertext ter-super enkripsi. Tabel `pesan` mendukung pemisahan kategori (`catatan` vs `sandi`). | `database/db.py`, `ui/password_page.py` |
| 6 | **Pesan gambar diamankan dengan steganografi** | Pesan di-super enkripsi terlebih dahulu lalu disematkan pada bit terakhir (*Least Significant Bit* / LSB) kanal warna citra PNG, dilengkapi *magic number* (`SVLT`) dan header panjang. | `stego/steganografi.py`, `ui/image_page.py` |
| 7 | **Aset penting diamankan dengan blockchain** | Sidik jari SHA-256 berkas dokumen penting dicatat ke dalam buku besar *blockchain* mandiri berantai dengan mekanisme konsensus *Proof-of-Work* (PoW, target kesulitan hash). | `blockchain/blockchain.py`, `blockchain/registry.py`, `ui/asset_page.py` |
| 8 | **Laporan akademik dan presentasi** | Laporan ilmiah lengkap (Bab 1–5, perancangan, hasil uji) dan bahan presentasi 10 slide beserta skrip demo dan simulasi uji gagal. | `docs/LAPORAN.md`, `docs/PRESENTASI.md`, `docs/ARSITEKTUR.md`, `docs/KEAMANAN.md` |

---

## 💻 Prasyarat Sistem (Fedora Linux)

Aplikasi dibangun dan diuji pada lingkungan **Fedora Linux** dengan **Python 3.14**:

1. **Paket Sistem Tkinter:**
   ```bash
   sudo dnf install python3-tkinter
   ```
2. **Kamera Webcam:** Perangkat webcam terhubung (indeks 0, misal `/dev/video0`) untuk verifikasi biometrik wajah.
3. **USB Flashdisk:** Sebagai dongle fisik (dideteksi nomor seri perangkat kerasnya via `pyudev`).

---

## 🚀 Panduan Instalasi & Menjalankan

### 1. Kloning dan Menyiapkan Virtual Environment

```bash
# Pindah ke direktori proyek
cd /home/hisyamlbaihaqi/kuliah/semester56/projek_akhir_kripto

# Buat virtual environment jika belum ada
python3 -m venv myenv

# Aktifkan virtual environment
source myenv/bin/activate

# Pindah ke direktori aplikasi
cd kripto-app

# Pasang dependensi
pip install -r requirements.txt
```

### 2. Menjalankan Aplikasi

```bash
python main.py
```

> **Catatan Mode Pengujian / Pengembang (Tanpa Dongle USB Fisik):**  
> Jika sedang menguji tanpa perangkat USB fisik, jalankan dengan variabel lingkungan:
> ```bash
> SAFEVAULT_DEV=1 python main.py
> ```
> *Aplikasi akan menampilkan spanduk peringatan oranye bahwa Simulated Dongle sedang aktif.*

---

## 🔑 Alur Registrasi Pertama (First-Run Setup) & Login

1. **First-Run Setup:**
   - Saat pertama kali dijalankan (database `data/app.db` masih kosong), aplikasi langsung membuka form pendaftaran.
   - Masukkan **Username** dan **Kata Sandi** (minimal 8 karakter).
   - Tancapkan flashdisk USB, klik **"Deteksi Dongle Saat Ini"** untuk mengikat nomor seri flashdisk ke akun Anda.
   - Posisikan wajah di depan kamera webcam, klik **"📷 Rekam 20 Sampel Wajah"**. Model LBPH akan dilatih otomatis dan disimpan di `data/faces/model.yml`.
   - Klik **"💾 Simpan & Daftarkan Akun"**.

2. **Alur Login 3-Faktor:**
   - **Tahap 1 (Dongle):** Pastikan flashdisk USB Anda tertancap. Klik "Periksa Sambungan Dongle".
   - **Tahap 2 (Wajah):** Kamera webcam akan aktif. Posisikan wajah Anda lalu klik "👤 Cocokkan Wajah".
   - **Tahap 3 (Kata Sandi):** Ketikkan kata sandi Anda dan tekan Enter / klik "🔓 Buka Brankas SafeVault".
   - Jika salah 3 kali pada tahap mana pun, sistem akan mengunci antarmuka selama **30 detik**.

---

## 🧪 Menjalankan Pengujian Otomatis

Seluruh modul dan pengujian UI (smoke test) dapat dijalankan menggunakan `pytest`:

```bash
cd kripto-app
python -m pytest -v
```

Hasil pengujian mencakup 55 skenario pengujian:
- Enkripsi dan dekripsi super enkripsi (Vigenère, Rail Fence, AES-256-GCM).
- Pengujian ChaCha20-Poly1305 pada berkas kosong, berkas normal, berkas terpotong, dan manipulasi 1 byte.
- Pengujian kapasitas dan integritas steganografi LSB dengan *magic number*.
- Pengujian validasi rantai blockchain, manipulasi blok, dan deteksi rantai putus.
- Pengujian registrasi dokumen SHA-256 dan deteksi berkas diubah.
- Pengujian bcrypt hash, first-run setup, dan asosiasi dongle serial.
- Pengujian UI smoke test (MainWindow, LoginWindow 3-tahap, dan lockout).

---

## 📁 Struktur Direktori Proyek

```
kripto-app/
├── main.py                   # Titik masuk utama aplikasi (SafeVaultApp lifecycle)
├── config.py                 # Konfigurasi path, KDF parameter, threshold, dsb.
├── requirements.txt          # Daftar dependensi terkunci
├── README.md                 # Dokumentasi pengantar dan panduan proyek
├── foto.png                  # Sampel citra untuk uji steganografi
├── auth/                     # Lapisan Autentikasi Keamanan
│   ├── dongle.py             # DongleChecker (UsbSerialDongle, KeyFileDongle, SimulatedDongle)
│   ├── face_auth.py          # FaceAuth (Haar Cascade + OpenCV LBPH Face Recognizer)
│   ├── password_auth.py      # PasswordAuth (bcrypt hash + constant-time verify)
│   └── session.py            # Session object (username, active keys, clear on logout)
├── crypto/                   # Lapisan Kriptografi Inti
│   ├── classic_algoritma.py  # VigenereCipher & RailFenceCipher
│   ├── super_enkripsi.py     # SuperEncryption (VigenereLayer + RailFenceLayer + AesLayer)
│   ├── file_enkripsi.py      # ChaChaFileCipher (ChaCha20-Poly1305 + scrypt per chunk)
│   └── file_crypto.py        # Re-export ChaChaFileCipher
├── database/                 # Basis Data Terenkripsi
│   └── db.py                 # SecureMessageStore (SQLite terenkripsi dengan kategori pesan)
├── stego/                    # Steganografi Citra
│   └── steganografi.py       # LsbSteganography (magic SVLT) & SecureStego
├── blockchain/               # Integritas Dokumen & Aset
│   ├── blockchain.py         # Block, Blockchain (Proof-of-Work, atomic save)
│   └── registry.py           # DocumentRegistry (SHA-256 hash & verifikasi status dokumen)
├── ui/                       # Antarmuka Pengguna (CustomTkinter)
│   ├── theme.py              # Skema palet warna gelap dan tipografi
│   ├── widgets.py            # Komponen pakai ulang (PasswordEntry, FilePicker, SectionCard, StatusLabel)
│   ├── login_window.py       # Jendela login bertahap (Dongle -> Wajah -> Password & First-Run Setup)
│   ├── main_window.py        # Jendela utama dengan navigasi sidebar 5 menu
│   ├── text_page.py          # Menu 1: Catatan Rahasia (Super Enkripsi)
│   ├── file_page.py          # Menu 2: Berkas Enkripsi (ChaCha20-Poly1305)
│   ├── password_page.py      # Menu 3: Brankas Kata Sandi Akun
│   ├── image_page.py         # Menu 4: Foto Rahasia (Steganografi LSB)
│   └── asset_page.py         # Menu 5: Daftar Dokumen & Validasi Rantai (Blockchain)
├── tests/                    # Berkas Pengujian pytest
│   ├── test_crypto.py
│   ├── test_super_encrypt.py
│   ├── test_file_crypto.py
│   ├── test_stego.py
│   ├── test_blockchain.py
│   ├── test_registry.py
│   ├── test_db.py
│   ├── test_auth_dongle.py
│   ├── test_auth_face.py
│   ├── test_auth_password.py
│   └── test_ui_smoke.py
├── data/                     # Basis data SQLite, file blockchain JSON, sampel wajah
├── output/                   # Direktori keluaran berkas terenkripsi (.enc) dan citra stego
└── docs/                     # Dokumentasi Akademik & Teknis Lengkap
    ├── ARSITEKTUR.md         # Diagram arsitektur lapisan, alur enkripsi, ERD, spesifikasi payload
    ├── KEAMANAN.md           # Model ancaman, analisis kriptografi, dan batasan teknis jujur
    ├── LAPORAN.md            # Naskah laporan ilmiah Bab 1 s.d. Bab 5
    └── PRESENTASI.md         # Slide outline presentasi (12 slide) dan skrip demo pengujian gagal
```

---

## ⚠️ Batasan & Keterbatasan Teknis

1. **Biometrik Wajah Tanpa Liveness Detection:** Pengenalan wajah berbasis LBPH memetakan tekstur lokal wajah namun belum dilengkapi deteksi kedipan atau kedalaman (*depth camera*), sehingga secara teoritis rentan terhadap manipulasi menggunakan foto cetak beresolusi tinggi.
2. **Karakteristik Cipher Klasik:** Algoritma Vigenère dan Rail Fence tidak memiliki tag integritas. Jika kunci klasik salah dimasukkan saat dekripsi, teks hasil dekripsi akan tampil teracak (tidak melempar error). Integritas dijamin oleh lapisan AES-GCM terotentikasi.
3. **Blockchain Node Tunggal (Lokal):** Rantai blok disimpan dalam format file JSON lokal dengan *Proof-of-Work*. Rantai ini mendeteksi segala bentuk manipulasi dokumen atau pengubahan data blok, namun pemilik komputer dengan akses root tetap dapat menghapus berkas `chain.json`.
4. **Kompresi Citra Steganografi:** Gambar hasil steganografi disimpan dalam format PNG lossless. Jika gambar dikirim melalui media sosial yang menerapkan kompresi lossy (seperti WhatsApp atau Telegram standar), bit muatan LSB akan rusak dan pesan rahasia tidak dapat dibaca kembali.
