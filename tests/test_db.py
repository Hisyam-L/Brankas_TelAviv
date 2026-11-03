from database.db import buat_pipeline, SecureMessageStore

benar = SecureMessageStore(buat_pipeline("kunci", 3, "passwordku"))
benar.simpan("Rahasia 1", "Password wifi: abc123")

print("Daftar            :", benar.daftar())
print("Kunci benar       :", benar.buka(1))

salah_aes = SecureMessageStore(buat_pipeline("kunci", 3, "salah"))
print("Password AES salah:", salah_aes.buka(1))

salah_vig = SecureMessageStore(buat_pipeline("kunciX", 3, "passwordku"))
print("Vigenere salah    :", salah_vig.buka(1))