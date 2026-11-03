import customtkinter as ctk

ctk.set_appearance_mode("dark")          # "light" / "dark" / "system"
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Brankas_TelAviv")
        self.geometry("1920x1080")

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        for nama in ["Catatan", "Berkas", "Kata Sandi", "Foto Rahasia", "Daftar Dokumen"]:
            tab = self.tabs.add(nama)
            ctk.CTkLabel(tab, text=f"Halaman {nama}").pack(pady=20)