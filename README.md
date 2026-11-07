# 🔐 SafeVault — Brankas Digital Kriptografi

**SafeVault** adalah aplikasi desktop brankas digital berbasis Python dan CustomTkinter yang mengintegrasikan berbagai mekanisme kriptografi klasik, modern, steganografi citra, buku besar blockchain sederhana, dan autentikasi multi-faktor (perangkat keras USB dongle, biometrik wajah, dan kata sandi). Proyek ini disusun sebagai tugas akhir mata kuliah **Kriptografi**.

---

## 📋 Pemetaan Fitur terhadap Kriteria Penilaian Dosen

| No | Kriteria Wajib Dosen | Implementasi pada SafeVault | Modul Terkait |
|:--:|:----------------------|:----------------------------|:--------------|
| 1 | **Login biometrik & wajib bantuan dongle** | Autentikasi ketat: Dongle fisik USB wajib terhubung (`DongleGate` & `DongleManager` dengan token SHA-256 terikat ID volume drive 1:1), verifikasi biometrik wajah (`FaceAuth` via Haar Cascade + LBPH OpenCV), dan verifikasi kata sandi bcrypt. Pemantau aktif `DongleWatcher` mengunci aplikasi seketika jika dongle dicabut. | `auth/dongle.py`, `ui/dongle_gate.py`, `auth/face_auth.py`, `ui/login_window.py` |
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

> **Keamanan Penuh (Zero-Bypass):**  
> Sesuai spesifikasi keamanan, SafeVault **tidak memiliki mode dev, flag bypass, atau simulasi** di kode produksi. Aplikasi hanya dapat dibuka jika USB flashdisk dongle yang terdaftar dan cocok 1:1 terpasang.

---

## 🔑 Alur Registrasi Pertama (First-Run Setup) & Login

1. **First-Run Setup (Pendaftaran Perdana):**
   - Saat pertama kali dijalankan (belum ada dongle terdaftar dan basis data pengguna kosong):
   - **Langkah 1 (DongleGate):** Tancapkan USB Flashdisk Anda. Pilih drive dari menu, klik **"🔑 Daftarkan Flashdisk sebagai Dongle"**. Berkas token kriptografis `.safevault_dongle.json` akan ditulis ke flashdisk dan hash SHA-256 terikat ID volume akan disimpan di `data/dongle.json`.
   - **Langkah 2 (Pendaftaran Akun & Wajah):** Setelah dongle terdaftar, jendela pendaftaran terbuka. Masukkan Username dan Kata Sandi (minimal 8 karakter), hadapkan wajah ke kamera webcam, lalu klik **"📷 Rekam 20 Sampel Wajah"**. Model LBPH akan dilatih otomatis. Klik **"💾 Simpan & Daftarkan Akun"**.

2. **Alur Autentikasi Normal (Dongle → Wajah → Password):**
   - **Tahap 1 (DongleGate):** Pastikan USB Flashdisk dongle Anda terpasang. `DongleGate` secara otomatis memindai dan memverifikasi token 1:1 tiap 1 detik. Jika cocok, gerbang terbuka menuju login.
   - **Tahap 2 (Verifikasi Wajah):** Kamera webcam aktif otomatis. Posisikan wajah Anda lalu klik **"👤 Cocokkan Wajah"**.
   - **Tahap 3 (Kata Sandi):** Masukkan kata sandi akun brankas dan tekan Enter / klik **"🔓 Buka Brankas SafeVault"**.
   - **Anti-Bruteforce Lockout:** Jika gagal 3 kali berturut-turut pada tahap mana pun, sistem akan mengunci antarmuka selama **30 detik**.
   - **Perlindungan Runtime (DongleWatcher):** Saat brankas terbuka (`MainWindow`), thread `DongleWatcher` memeriksa dongle tiap 2 detik. Jika flashdisk dicabut, memori sesi seketika dihapus dan aplikasi kembali terkunci ke `DongleGate`!

---

## 🧪 Menjalankan Pengujian Otomatis

Seluruh modul dan pengujian UI (smoke test) dapat dijalankan menggunakan `pytest`:

```bash
cd kripto-app
python -m pytest -v
```

Hasil pengujian mencakup **74 skenario pengujian** (100% Lolos):
- Verifikasi token dongle 1:1, pencegahan duplikasi token di drive lain (volume-bound), deteksi token rusak, tampered token, reregistrasi terkontrol, dan DongleWatcher (`tests/test_dongle.py`).
- Enkripsi dan dekripsi super enkripsi (Vigenère, Rail Fence, AES-256-GCM).
- Pengujian ChaCha20-Poly1305 pada berkas kosong, berkas normal, berkas terpotong, dan manipulasi 1 byte.
- Pengujian kapasitas dan integritas steganografi LSB dengan *magic number*.
- Pengujian validasi rantai blockchain, manipulasi blok, dan deteksi rantai putus.
- Pengujian registrasi dokumen SHA-256 dan deteksi berkas diubah.
- Pengujian bcrypt hash, first-run detection, dan password length.
- Pengujian UI smoke test (DongleGate setup, gate locked tampered, MainWindow 5 menu, dialog ganti dongle, 3-factor login, dan lockout).
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
│   ├── dongle_gate.py        # Gerbang keamanan hardware dongle USB 1:1
│   ├── login_window.py       # Jendela login bertahap (Wajah & Password & First-Run Setup)
│   ├── main_window.py        # Jendela utama dengan navigasi sidebar 5 menu & dialog ganti dongle
│   ├── text_page.py          # Menu 1: Catatan Rahasia (Super Enkripsi)
│   ├── file_page.py          # Menu 2: Berkas Enkripsi (ChaCha20-Poly1305)
│   ├── password_page.py      # Menu 3: Brankas Kata Sandi Akun
│   ├── image_page.py         # Menu 4: Foto Rahasia (Steganografi LSB)
│   └── asset_page.py         # Menu 5: Daftar Dokumen & Validasi Rantai (Blockchain)
├── tests/                    # Berkas Pengujian pytest
│   ├── test_dongle.py        # Pengujian token dongle 1:1, UUID bound, tampered token, DongleWatcher
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
├── data/                     # Basis data SQLite, file blockchain JSON, sampel wajah, hash dongle
├── output/                   # Direktori keluaran berkas terenkripsi (.enc) dan citra stego
└── docs/                     # Dokumentasi Akademik & Teknis Lengkap
    ├── ARSITEKTUR.md         # Diagram arsitektur lapisan, alur enkripsi, ERD, spesifikasi payload
    ├── DONGLE.md             # Spesifikasi teknis token dongle, Mermaid flowchart, dan model ancaman
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
