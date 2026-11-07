# 🎙️ Bahan Presentasi & Skrip Demo SafeVault

Dokumen ini memuat rancangan **12 Slide Presentasi Tugas Akhir Kriptografi**, lengkap dengan naskah bicara (*speaker notes*) serta **skrip panduan demo langsung (*live demo script*)** langkah demi langkah di hadapan dosen penguji, termasuk peragaan skenario kegagalan (*failure scenarios*).

---

## 📑 OUTLINE 12 SLIDE PRESENTASI

### Slide 1: Judul & Identitas
- **Judul:** SafeVault — Brankas Digital Kriptografi Multi-Faktor
- **Subjudul:** Integrasi Super Enkripsi, Steganografi LSB, dan Blockchain untuk Perlindungan Aset Digital
- **Penyaji:** Hisyam Luthfi Baihaqi (Mata Kuliah Kriptografi)
- **Naskah Bicara (1 Menit):**
  > "Selamat pagi/siang Bapak/Ibu dosen penguji. Pada kesempatan ini saya mempresentasikan SafeVault, aplikasi desktop brankas digital yang dirancang untuk menjawab tantangan keamanan berlapis. SafeVault mengintegrasikan seluruh 8 kriteria tugas akhir: mulai dari 3-Factor Authentication fisik dan biometrik, super enkripsi klasik-modern, enkripsi berkas terpisah, steganografi citra, hingga buku besar blockchain untuk integritas dokumen."

---

### Slide 2: Latar Belakang & Masalah
- **Poin Kunci:**
  - Kerapuhan autentikasi tunggal (*single password vulnerability*).
  - Basis data teks polos yang rentan terhadap *data breach*.
  - Pemalsuan berkas dan manipulasi dokumen digital tanpa jejak.
- **Naskah Bicara (1 Menit):**
  > "Masalah terbesar sistem penyimpanan saat ini adalah titik kegagalan tunggal. Jika kata sandi bocor, seluruh data hilang. Jika berkas dipalsukan, sulit membuktikan keasliannya. SafeVault menerapkan filosofi pertahanan berlapis (defense-in-depth): tidak ada satu pun komponen yang berdiri sendiri tanpa pengamanan ganda."

---

### Slide 3: Pemetaan 8 Kriteria Wajib Dosen
- **Tabel Ringkas:**
  1. Login Biometrik + Dongle USB Fisik Wajib
  2. Kriptografi Login (bcrypt Hash Salted)
  3. Super Enkripsi Teks (Vigenère + Rail Fence + AES-256-GCM)
  4. Enkripsi Berkas Berbeda (ChaCha20-Poly1305 + scrypt)
  5. Enkripsi Basis Data (SQLite Ciphertext Terkategori)
  6. Steganografi Gambar (LSB + Magic Number SVLT)
  7. Pengamanan Aset Dokumen (Blockchain SHA-256 + PoW)
  8. Laporan Akademik & Presentasi Lengkap
- **Naskah Bicara (1.5 Menit):**
  > "Seluruh delapan kriteria penilaian yang ditetapkan telah diimplementasikan 100% tanpa kompromi. Masing-masing fitur memiliki peran spesifik dan menggunakan algoritma yang tepat guna."

---

### Slide 4: Arsitektur Perangkat Lunak & Aliran Data
- **Poin Kunci:**
  - Pemisahan lapisan UI, Autentikasi, Logika Kripto, dan Penyimpanan.
  - Zero-Knowledge Memory: Kunci tidak disimpan di disk/database.
- **Naskah Bicara (1 Menit):**
  > "Arsitektur SafeVault dirancang berorientasi objek murni. Lapisan UI tidak bercampur dengan logika kriptografi. Yang paling penting: kunci enkripsi tidak pernah disimpan di disk atau database, melainkan hanya berada di memori sesi aktif dan segera dimusnahkan saat brankas dikunci."

---

### Slide 5: Autentikasi 3-Faktor (Dongle → Wajah → Sandi)
- **Poin Kunci:**
  - Faktor 1: Hardware Dongle Token terikat ID Volume (`SHA-256(salt + secret + ID_VOLUME)`).
  - Faktor 2: Biometrik Pengenal Wajah (Haar Cascade + LBPH OpenCV).
  - Faktor 3: Kata Sandi Brankas (bcrypt constant-time verification).
  - Runtime Security: `DongleWatcher` memantau keberadaan dongle; jika dicabut, brankas terkunci seketika.
  - Mekanisme Anti-Bruteforce: Penguncian otomatis 30 detik jika gagal 3 kali.
- **Naskah Bicara (1.5 Menit):**
  > "Alur masuk sistem mengombinasikan something you have (USB flashdisk dengan token kriptografis terikat ID volume), something you are (wajah pemilik), dan something you know (kata sandi). Jika salah satu gagal, brankas tidak dapat dibuka. Bahkan saat brankas terbuka, jika dongle dicabut, aplikasi otomatis mengosongkan memori dan terkunci kembali."

---

### Slide 6: Super Enkripsi Teks & Catatan Rahasia
- **Poin Kunci:**
  - Lapisan 1: Vigenère Cipher (Substitusi Polialfabetik).
  - Lapisan 2: Rail Fence Cipher (Transposisi Zig-Zag).
  - Lapisan 3: AES-256-GCM (Cipher Blok Modern Terotentikasi).
  - Diturunkan via PBKDF2 100.000 iterasi.
- **Naskah Bicara (1 Menit):**
  > "Untuk pesan teks dan catatan, kami menerapkan super enkripsi sejati: substitusi klasik, transposisi klasik, dan diakhiri cipher modern terotentikasi AES-256-GCM. Tag otentikasi GCM memastikan bahwa manipulasi satu bit saja akan langsung menggagalkan dekripsi."

---

### Slide 7: Brankas Kata Sandi & Keamanan Basis Data
- **Poin Kunci:**
  - Pemisahan kategori tabel di SQLite (`catatan` vs `sandi`).
  - Fitur Password Generator acak dengan entropi tinggi.
  - Pengosongan clipboard otomatis dalam 20 detik setelah disalin.
- **Naskah Bicara (1 Menit):**
  > "Modul Brankas Kata Sandi menyimpan kredensial akun terenkripsi di database SQLite yang sama namun dengan kategori terpisah. Terdapat fitur generator password dan clipboard cleaner otomatis setelah 20 detik agar password tidak tertinggal di memori sistem operasi."

---

### Slide 8: Enkripsi Berkas Digital (ChaCha20-Poly1305)
- **Poin Kunci:**
  - Algoritma berbeda dari teks: ChaCha20-Poly1305 stream cipher.
  - KDF scrypt memory-hard ($N=32768, r=8, p=1$).
  - Pemrosesan hemat memori per chunk 1 MB dengan otentikasi AAD.
- **Naskah Bicara (1.5 Menit):**
  > "Kriteria keempat mengharuskan enkripsi berkas berbeda dari teks. Kami memilih ChaCha20-Poly1305 dengan KDF scrypt. Berkas diproses per potongan 1 MB dengan AAD counter, sehingga berkas video atau dokumen berukuran ratusan megabyte dapat dienkripsi secara cepat tanpa membuat aplikasi freeze."

---

### Slide 9: Foto Rahasia (Steganografi LSB)
- **Poin Kunci:**
  - Metode Least Significant Bit (LSB) pada citra PNG 24-bit.
  - Double Protection: Pesan di-super enkripsi terlebih dahulu sebelum disematkan.
  - Header Magic Bytes `SVLT` untuk validasi keberadaan pesan.
- **Naskah Bicara (1 Menit):**
  > "Pada modul Foto Rahasia, pesan tidak hanya disembunyikan secara polos, melainkan di-super enkripsi terlebih dahulu. Kami menambahkan magic bytes SVLT pada LSB agar gambar biasa tanpa pesan tidak memicu pembacaan noise acak."

---

### Slide 10: Integritas Dokumen & Blockchain
- **Poin Kunci:**
  - Single-Node Blockchain dengan Proof-of-Work (Target Hash 3 Nol).
  - Registrasi sidik jari digital (SHA-256) dokumen penting (Ijazah, BPKB, Sertifikat).
  - Status Verifikasi: ASLI, DIUBAH, TIDAK TERDAFTAR, RANTAI RUSAK.
- **Naskah Bicara (1.5 Menit):**
  > "Untuk menjamin keaslian aset dokumen, kami membuat blockchain mandiri dengan konsensus Proof-of-Work. Setiap berkas didaftarkan nilai SHA-256-nya ke dalam blok. Jika isi dokumen diubah 1 byte di kemudian hari, sistem verifikasi akan langsung mendeteksi status DIUBAH."

---

### Slide 11: Analisis Keamanan & Keterbatasan Jujur
- **Poin Kunci:**
  - Yang Terlindungi: Data at rest, tamper-evident file, anti-bruteforce, broken chain detection.
  - Keterbatasan: Cipher klasik tidak punya tag integritas, LBPH belum ada liveness detection, steganografi rusak jika dikompresi WhatsApp, kehilangan password = data hilang selamanya.
- **Naskah Bicara (1 Menit):**
  > "Secara jujur kami mengevaluasi keterbatasan teknis sistem: pengenal wajah LBPH belum memiliki sensor 3D liveness, steganografi LSB rentan kompresi lossy media sosial, dan karena menggunakan arsitektur zero-knowledge, kehilangan password berarti data hilang permanen."

---

### Slide 12: Kesimpulan & Sesi Tanya Jawab
- **Poin Kunci:**
  - 100% dari 8 Kriteria Dosen Terpenuhi.
  - 74 Test Case Otomatis Berhasil (pytest).
  - Siap untuk Live Demo pengujian normal & pengujian skenario gagal.
- **Naskah Bicara (0.5 Menit):**
  > "SafeVault membuktikan bahwa kombinasi teknik kriptografi klasik, modern, biometrik, steganografi, dan blockchain dapat diintegrasikan secara harmonis dan kokoh. Terima kasih atas perhatian Bapak/Ibu dosen, kami siap mendemokan aplikasi."

---

## 🎬 SKRIP LIVE DEMO PENGUJIAN LANGKAH DEMI LANGKAH

Panduan ini digunakan saat mendemokan aplikasi di hadapan dosen penguji, meliputi skenario sukses dan skenario gagal yang wajib diperlihatkan:

### BAGIAN 1: Demo Autentikasi Masuk (3-Factor Auth)
1. **Skenario Gagal 1 (Dongle Belum Terpasang):**
   - Pastikan flashdisk USB belum dicolokkan.
   - Jalankan `python main.py`.
   - Gerbang **DongleGate** muncul dan secara otomatis memindai.
   - **Hasil Terlihat:** Muncul status merah *"Akses Ditolak: Dongle tidak terpasang"*. Polling otomatis memeriksa tiap 1 detik.
2. **Skenario Gagal 2 (Dongle Salinan di Flashdisk Lain):**
   - Tancapkan flashdisk lain yang berisi salinan file `.safevault_dongle.json`.
   - **Hasil Terlihat:** Muncul status merah *"Akses Ditolak: Dongle ditemukan tetapi tidak cocok (salinan, rusak, atau bukan dongle ini)"*. Ini membuktikan bahwa pembawaan ID volume (UUID) ke dalam hash berhasil menolak dongle bajakan!
3. **Skenario Berhasil 1 (Dongle Asli Ditancapkan):**
   - Tancapkan flashdisk USB asli yang didaftarkan.
   - Dalam 1 detik, sistem mendeteksi hash cocok 1:1, status berubah hijau *"✓ Dongle valid (/run/media/...)"*, DongleGate tertutup dan LoginWindow terbuka.
4. **Skenario Gagal 3 (Wajah Bukan Pemilik / Dihalangi):**
   - Tutup kamera webcam dengan tangan atau arahkan ke orang lain.
   - Klik **"👤 Cocokkan Wajah"**.
   - **Hasil Terlihat:** Muncul pesan merah *"Wajah tidak cocok / tidak terdeteksi"*. Percobaan gagal bertambah 1/3.
5. **Skenario Simulasi Lockout 30 Detik:**
   - Sengaja klik gagal sekali lagi hingga mencapai 3 kali percobaan berturut-turut.
   - **Hasil Terlihat:** Muncul banner merah menyala *"⚠️ SISTEM TERKUNCI KARENA KEGAGALAN BERULANG"*, dengan timer hitung mundur 30 detik. Seluruh tombol dinonaktifkan.
6. **Skenario Berhasil 2 & 3 (Wajah Cocok + Password Benar):**
   - Setelah 30 detik selesai, hadapkan wajah asli ke kamera dan klik "Cocokkan Wajah" (Lolos hijau).
   - Ketikkan kata sandi akun pada field tahap 3, tekan Enter atau klik "🔓 Buka Brankas SafeVault".
   - **Hasil Terlihat:** Jendela login tertutup dan Jendela Utama SafeVault terbuka!
7. **Skenario Ekstrem (Dongle Dicabut Saat Brankas Terbuka):**
   - Saat berada di dalam jendela utama SafeVault, cabut flashdisk USB.
   - Dalam tempo ≤ 2 detik, thread `DongleWatcher` mendeteksi pencabutan, seluruh isi sesi dan memori dihapus, MainWindow seketika tertutup, dan aplikasi kembali terkunci di layar `DongleGate`!

---

### BAGIAN 2: Demo Catatan Rahasia (Super Enkripsi)
1. Masukkan Judul: *"Rencana Rahasia 2026"*.
2. Masukkan Isi Pesan: *"Proyek kriptografi ini sukses 100%!"*.
3. Masukkan 3 Kunci:
   - Kunci Vigenère: `RAHASIA`
   - Kunci Rail Fence: `3`
   - Password AES: `KunciKuat123#`
4. Klik **"💾 Simpan Catatan Terenkripsi"**. Muncul status hijau *"Catatan berhasil dienkripsi dan disimpan"*.
5. Buka Catatan:
   - Pilih catatan pada daftar sebelah kanan.
   - **Uji Kunci AES Salah:** Masukkan password salah `Salah123#`, klik "Buka".
     - **Hasil:** Muncul status merah *"Password AES salah atau data rusak!"* (Integritas GCM menolak).
   - **Uji Kunci Benar:** Masukkan ketiga kunci yang benar.
     - **Hasil:** Pesan asli terbaca sempurna di kotak pembaca.

---

### BAGIAN 3: Demo Enkripsi Berkas (ChaCha20-Poly1305)
1. Pilih berkas sampel apa pun (misal gambar atau PDF).
2. Masukkan password berkas: `BerkasAman2026!`.
3. Klik **"🔒 Enkripsi Berkas"**.
   - **Hasil:** Progress bar berjalan cepat di thread background, berkas `<nama>.enc` tersimpan di folder `output/`.
4. **Skenario Gagal (Manipulasi 1 Byte Berkas .enc):**
   - Buka terminal, ubah 1 byte pada berkas `.enc` hasil enkripsi:
     ```bash
     printf "\x00" | dd of=output/<nama_file>.enc bs=1 seek=100 count=1 conv=notrunc
     ```
   - Di aplikasi SafeVault, pilih berkas `.enc` yang baru saja diubah tersebut, masukkan password yang benar, klik **"🔓 Dekripsi Berkas"**.
   - **Hasil:** Sistem menampilkan status merah *"Data berkas telah dimanipulasi atau korup!"* (Tag Poly1305 berhasil melindungi integritas).

---

### BAGIAN 4: Demo Foto Rahasia (Steganografi LSB)
1. Klik menu **"Foto Rahasia"**.
2. Pilih cover image `foto.png`. Aplikasi menampilkan resolusi gambar dan kapasitas muat byte (misal `~139.7 KB`).
3. Ketikkan pesan rahasia dan ketiga kunci super enkripsi.
4. Klik **"Sembunyikan ke Citra"**. Berkas citra stego PNG tersimpan di folder `output/`.
5. Buka panel kanan ("Ungkap Pesan"), pilih citra stego yang baru dihasilkan, masukkan ketiga kunci.
   - **Hasil:** Pesan rahasia terekstrak dan terdekripsi secara utuh tanpa ada cacat visual pada gambar sampul.

---

### BAGIAN 5: Demo Daftar Dokumen & Validasi Blockchain
1. Klik menu **"Daftar Dokumen"**.
2. Masukkan Jenis: *"Ijazah S1"*, Pemilik: *"Hisyam Luthfi"*, pilih berkas dokumen.
3. Klik **"📜 Daftarkan ke Blockchain"**.
   - **Hasil:** Penambang melakukan Proof-of-Work (mencari nonce hingga hash diawali `000`), blok baru tercatat di tabel.
4. Klik tombol **"🔍 Verifikasi Berkas Dokumen"**:
   - Pilih berkas yang sama -> Status **ASLI (Hijau)**.
5. **Skenario Gagal (Dokumen Diubah):**
   - Buka berkas dokumen di text editor, tambahkan spasi atau 1 karakter, simpan.
   - Verifikasi ulang berkas tersebut di SafeVault.
   - **Hasil:** Status seketika berubah menjadi **DIUBAH (Merah)**!
6. Klik **"⛓️ Cek Integritas Rantai"**: Status menampilkan *"Rantai valid"* (seluruh hash dan previous_hash sinkron).
