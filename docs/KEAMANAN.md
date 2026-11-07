# 🛡️ Analisis Keamanan & Model Ancaman SafeVault

Dokumen ini menjabarkan analisis model ancaman (*threat modeling*), alasan pemilihan tiap algoritma kriptografi, jaminan keamanan yang diberikan, serta evaluasi keterbatasan teknis secara jujur dan transparan pada aplikasi **SafeVault**.

---

## 1. Model Ancaman (Threat Modeling)

Dalam perancangan SafeVault, diasumsikan beberapa profil penyerang (*adversary models*):

1. **Penyerang Fisik Sepintas (*Casual Physical Attacker*):** Seseorang yang mencoba menyalakan komputer saat pemilik tidak ada di tempat.
2. **Pencuri Media Penyimpanan (*Data-at-Rest Thief*):** Penyerang yang menyalin berkas basis data SQLite (`app.db`), berkas terenkripsi (`.enc`), atau citra stego dari disk.
3. **Penyadap Jalur Jaringan (*Network Observer*):** Pihak yang memantau berkas yang dikirimkan melalui saluran tidak aman.
4. **Pemalsu Integritas Berkas (*Tamperer*):** Penyerang yang berupaya memanipulasi 1 byte ciphertext, memotong berkas, atau mengubah isi dokumen resmi di disk.

---

## 2. Rincian Algoritma & Alasan Pemilihan

### 2.1 Autentikasi Pengguna: bcrypt
- **Algoritma:** bcrypt (berbasis Eksplorasi Blowfish).
- **Alasan Pemilihan:** Berbeda dari fungsi hash kriptografi umum seperti MD5 atau SHA-256 yang sangat cepat (sehingga rentan serangan *brute-force* berbantuan GPU/ASIC), bcrypt dirancang sengaja lambat (*computationally expensive*) dengan parameter kerja (*cost factor*) dan salt acak unik 128-bit untuk mencegah serangan *rainbow table*.
- **Perbandingan:** Menggunakan verifikasi *constant-time* (`bcrypt.checkpw`) guna menangkal serangan *timing side-channel*.

### 2.2 Dongle Perangkat Keras: Token Kriptografi Terikat Volume (Volume-Bound SHA-256)
- **Algoritma:** Hashing token `SHA-256(salt + secret + ID_VOLUME)` dan perbandingan *constant-time* `hmac.compare_digest`.
- **Alasan Pemilihan:** Mengikat hak akses aplikasi ke kepemilikan fisik perangkat (*something you have*). Aplikasi tidak dapat dibuka hanya dengan mengetahui kata sandi, melainkan mewajibkan kehadiran fisik flashdisk/dongle yang memuat berkas token `.safevault_dongle.json`.
- **Pengikatan ID Volume:** Menambahkan ID volume (UUID partisi Linux atau Serial Volume Windows) ke dalam hash mencegah penyalinan berkas token ke flashdisk lain (flashdisk salinan akan ditolak karena ID volume berbeda).
- **Rincian lengkap:** Lihat dokumentasi khusus di [DONGLE.md](file:///home/hisyamlbaihaqi/kuliah/semester56/projek_akhir_kripto/kripto-app/docs/DONGLE.md).

### 2.3 Biometrik Wajah: Haar Cascade Detector + LBPH Face Recognizer
- **Algoritma:** Detektor Haar Cascade (`cv2.CascadeClassifier`) + *Local Binary Patterns Histograms* (`cv2.face.LBPHFaceRecognizer`).
- **Alasan Pemilihan:** LBPH sangat ringan, tidak membutuhkan dependensi model deep learning berukuran gigabyte (seperti PyTorch/TensorFlow), tahan terhadap variasi pencahayaan monokromatik karena membandingkan pola tekstur piksel lokal, dan dapat dilatih secara *on-device* dalam hitungan detik.

### 2.4 Super Enkripsi Pesan Teks: Vigenère + Rail Fence + AES-256-GCM
- **Algoritma:**
  - **Vigenère Cipher (Klasik):** Substitusi polialfabetik berdasarkan kata kunci.
  - **Rail Fence Cipher (Klasik):** Transposisi pola zig-zag berdasarkan jumlah rel.
  - **AES-256-GCM (Modern):** Advanced Encryption Standard dengan panjang kunci 256-bit beroperasi dalam mode *Galois/Counter Mode* (Authenticated Encryption with Associated Data / AEAD).
- **Alasan Pemilihan:**
  - Kombinasi klasik + modern memenuhi tuntutan akademik perpaduan cipher substitusi, transposisi, dan cipher blok modern.
  - Lapisan terluar AES-256-GCM menjamin kerahasiaan (*confidentiality*) sekaligus integritas otentikasi data (*authenticity/integrity*). Tag GCM (16 byte) memastikan bahwa jika ciphertext dimanipulasi sekecil apa pun, dekripsi akan langsung gagal.
- **KDF:** PBKDF2-HMAC-SHA256 dengan 100.000 iterasi dan salt acak 16 byte.

### 2.5 Enkripsi Berkas: ChaCha20-Poly1305 + scrypt
- **Algoritma:** Stream cipher ChaCha20 dipadukan dengan authenticator Poly1305 (RFC 8439).
- **Alasan Pemilihan:**
  - Berkas diproses menggunakan algoritma yang berbeda dari teks (kriteria wajib dosen nomor 4).
  - ChaCha20 memiliki performa komputasi perangkat lunak (software implementation) yang jauh lebih cepat dibandingkan AES pada prosesor tanpa akselerasi instruksi perangkat keras AES-NI.
  - Menggunakan KDF **scrypt** ($N=32768, r=8, p=1$) yang bersifat *memory-hard*, memberikan ketahanan tinggi terhadap serangan cracking berbasis FPGA/ASIC.
  - Pemrosesan berkas per chunk 1 MB dengan otentikasi AAD (counter urutan chunk dan flag akhir) mencegah serangan *chunk reordering* atau *truncation attack*.

### 2.6 Steganografi Citra: LSB dengan Magic Number `SVLT`
- **Algoritma:** *Least Significant Bit* (LSB) pada bidang warna citra RGB format PNG lossless.
- **Alasan Pemilihan:** Perubahan 1 bit terendah pada nilai warna piksel (rentang 0–255) tidak dapat dipersepsi oleh mata manusia (*imperceptible*). Dilengkapi prefiks *magic number* 4 byte `SVLT` dan panjang muatan 32-bit untuk mencegah pembacaan data acak pada gambar polos.

### 2.7 Integritas Dokumen & Aset: Single-Node Blockchain + Proof-of-Work
- **Algoritma:** Buku besar berantai SHA-256 dengan konsensus *Proof-of-Work* (kesulitan mencari hash dengan prefiks nol).
- **Alasan Pemilihan:** Menjamin immutability (ketidakbisaubahan) sidik jari berkas dokumen penting. Setiap blok terikat secara kriptografis ke hash blok sebelumnya. Jika 1 byte berkas diubah, atau jika isi blok di masa lalu disunting, rantai blok akan putus (*broken chain*) dan terdeteksi seketika.

---

## 3. Matriks Jaminan Keamanan (Apa yang Dilindungi vs Tidak Dilindungi)

| Potensi Serangan / Skenario | Status Proteksi | Penjelasan Teknis |
|:---|:---:|:---|
| Pencurian basis data `app.db` | **Terlindungi** | Seluruh catatan penting tersimpan dalam bentuk ciphertext AES-256-GCM terotentikasi. Tanpa kunci pengguna, data tidak dapat didekripsi. |
| Manipulasi 1 byte berkas `.enc` | **Terlindungi** | Tag otentikasi Poly1305 pada chunk terkait akan menolak data dan memicu error domain `FileCipherError`. |
| Penghapusan chunk akhir berkas `.enc` | **Terlindungi** | Flag AAD chunk terakhir memastikan bahwa jika berkas terpotong, dekripsi akan menolak berkas karena flag akhir belum tercapai. |
| Pengubahan isi dokumen penting | **Terlindungi** | Fungsi `DocumentRegistry.verify` membandingkan hash SHA-256 terkini dengan catatan blok blockchain, status akan bertanda **DIUBAH** berwarna merah. |
| Serangan *Brute-Force* Login | **Terlindungi** | Dibatasi maksimal 3 kali percobaan gagal, kemudian sistem terkunci (*lockout*) selama 30 detik. |
| Kebocoran Kunci Enkripsi | **Terlindungi** | Kunci enkripsi teks (Vigenère, Rail Fence, AES) dan berkas (ChaCha20) **tidak pernah ditulis ke disk atau database**. Kunci hanya berada di memori sesi aktif dan segera dihapus saat logout. |

---

## 4. Evaluasi Keterbatasan Teknis Secara Jujur (*Honest Limitations*)

1. **Cipher Klasik Tidak Memiliki Pemeriksaan Integritas:**
   Cipher Vigenère dan Rail Fence adalah algoritma klasik tanpa kode autentikasi pesan (MAC). Jika pengguna memasukkan kunci klasik yang salah saat dekripsi, cipher tidak memunculkan pesan error, melainkan mengembalikan karakter yang tetap teracak. Hanya lapisan AES-GCM yang mendeteksi kesalahan password secara kriptografis.
2. **Keterbatasan Biometrik Wajah Tanpa *Liveness Detection*:**
   Model LBPH mendeteksi struktur geometri dan histogram piksel wajah. Model ini belum dilengkapi algoritma anti-spoofing berbasis kedalaman (3D depth) atau deteksi kedipan mata (*blink detection*), sehingga penyerang yang memegang foto cetak beresolusi tinggi secara teoritis berpotensi mengelabui kamera.
3. **Karakteristik Steganografi LSB Rentan Kompresi:**
   Steganografi LSB sangat bergantung pada integritas bit murni citra PNG lossless. Apabila citra dikirimkan melalui kanal transmisi yang melakukan re-kompresi lossy (JPEG, kompresi otomatis WhatsApp/Instagram), seluruh bit muatan rahasia akan rusak dan tidak dapat dipulihkan.
4. **Sifat Blockchain Lokal (Node Tunggal):**
   Mekanisme Proof-of-Work dan chaining SHA-256 menjamin integritas data terhadap modifikasi parsial. Namun, karena tidak beroperasi pada jaringan *peer-to-peer* terdistribusi (bukan multi-node publik seperti Bitcoin/Ethereum), pengguna dengan hak akses administratif lokal (root) tetap dapat menghapus berkas `chain.json` secara keseluruhan.
5. **Konsekuensi *Zero-Knowledge Architecture*:**
   Karena kunci enkripsi tidak disimpan di mana pun, apabila pengguna melupakan password AES atau kunci super enkripsinya, data yang tersimpan di dalam brankas **secara matematis mustahil untuk dipulihkan kembali** (*unrecoverable by design*).
