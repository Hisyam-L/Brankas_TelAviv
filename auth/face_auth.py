from __future__ import annotations

import json
from pathlib import Path
import cv2
import numpy as np

from config import DATA_DIR, FACE_CONFIDENCE_THRESHOLD, FACES_DIR


class FaceAuthError(Exception):
    """Error domain autentikasi biometrik wajah."""


class FaceAuth:
    """
    Autentikasi biometrik wajah menggunakan Haar Cascade Detector dan
    Local Binary Patterns Histograms (LBPH Face Recognizer) dari OpenCV.

    Catatan Keamanan & Keterbatasan:
    Modul ini mengimplementasikan pencocokan geometri dan tekstur wajah secara lokal.
    Belum mendukung liveness detection (anti-spoofing), sehingga secara teoritis
    dapat dikelabui dengan foto cetak atau layar perangkat beresolusi tinggi.
    """

    def __init__(
        self,
        faces_dir: Path | str = FACES_DIR,
        threshold: float = FACE_CONFIDENCE_THRESHOLD,
    ):
        self.faces_dir = Path(faces_dir)
        self.faces_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = threshold
        self.model_path = self.faces_dir / "model.yml"
        self.labels_map_path = self.faces_dir / "labels_map.json"

        # Inisialisasi Cascade Classifier untuk deteksi wajah
        self.cascade = self._load_cascade()
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self._load_trained_model_if_exists()

    def _load_cascade(self) -> cv2.CascadeClassifier:
        """Mencari dan memuat haarcascade file."""
        candidates = [
            DATA_DIR / "haarcascade_frontalface_default.xml",
            Path(getattr(cv2.data, "haarcascades", "/nonexistent")) / "haarcascade_frontalface_default.xml",
            Path("/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"),
        ]
        for p in candidates:
            if p.exists():
                cascade = cv2.CascadeClassifier(str(p))
                if not cascade.empty():
                    return cascade

        raise FaceAuthError(
            "Berkas model deteksi wajah (haarcascade_frontalface_default.xml) tidak ditemukan."
        )

    def _load_trained_model_if_exists(self) -> None:
        """Memuat model LBPH yang sudah dilatih jika berkas tersedia."""
        if self.model_path.exists() and self.labels_map_path.exists():
            try:
                self.recognizer.read(str(self.model_path))
            except Exception:
                pass

    def detect_faces(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Mendeteksi bounding box wajah [(x, y, w, h)] pada frame."""
        if frame is None or frame.size == 0:
            return []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        faces = self.cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
        )
        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]

    def is_enrolled(self, username: str) -> bool:
        """Mengecek apakah wajah pengguna sudah terdaftar dan model sudah dilatih."""
        user_folder = self.faces_dir / username
        if not user_folder.exists():
            return False
        if not self.model_path.exists():
            return False
        labels_map = self._get_labels_map()
        return username in labels_map.values()

    def _get_labels_map(self) -> dict[str, str]:
        if not self.labels_map_path.exists():
            return {}
        try:
            return json.loads(self.labels_map_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def enroll_face_sample(
        self, username: str, frame: np.ndarray, sample_idx: int
    ) -> tuple[bool, str]:
        """
        Mendeteksi dan menyimpan 1 potongan wajah ke folder sampel pengguna.
        """
        faces = self.detect_faces(frame)
        if len(faces) == 0:
            return False, "Wajah tidak terdeteksi di kamera"
        if len(faces) > 1:
            return False, "Lebih dari satu wajah terdeteksi"

        x, y, w, h = faces[0]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        face_crop = cv2.resize(gray[y : y + h, x : x + w], (200, 200))

        user_dir = self.faces_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        sample_path = user_dir / f"{sample_idx:03d}.png"
        cv2.imwrite(str(sample_path), face_crop)
        return True, "Sampel wajah berhasil disimpan"

    def enroll(
        self, username: str, jumlah_sampel: int = 20, camera_index: int = 0
    ) -> tuple[bool, str]:
        """
        Merekam sampel wajah dari webcam dan melatih model LBPH.
        Mengambil `jumlah_sampel` (default 20) potongan wajah, menyimpannya di
        data/faces/<username>/, lalu melatih model dan menyimpannya di data/faces/model.yml.
        """
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise FaceAuthError("Kamera webcam tidak ditemukan atau tidak dapat diakses")

        saved_count = 0
        attempts = 0
        max_attempts = jumlah_sampel * 20

        try:
            while saved_count < jumlah_sampel and attempts < max_attempts:
                attempts += 1
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                success, _ = self.enroll_face_sample(username, frame, saved_count)
                if success:
                    saved_count += 1
        finally:
            cap.release()

        if saved_count < jumlah_sampel:
            raise FaceAuthError(
                f"Hanya berhasil mengambil {saved_count}/{jumlah_sampel} sampel wajah. "
                "Pastikan wajah menghadap ke kamera dengan pencahayaan cukup."
            )

        train_success, train_msg = self.train_model()
        if not train_success:
            raise FaceAuthError(f"Gagal melatih model wajah: {train_msg}")

        return True, f"Berhasil mendaftarkan {jumlah_sampel} sampel wajah untuk '{username}'"

    def train_model(self) -> tuple[bool, str]:
        """
        Melatih model LBPH dari seluruh sampel wajah yang terkumpul di direktori faces.
        """
        labels_map: dict[str, str] = {}
        images: list[np.ndarray] = []
        labels: list[int] = []

        current_label = 0
        for user_dir in self.faces_dir.iterdir():
            if user_dir.is_dir() and not user_dir.name.startswith("."):
                username = user_dir.name
                user_images = list(user_dir.glob("*.png"))
                if not user_images:
                    continue

                labels_map[str(current_label)] = username
                for img_path in user_images:
                    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        images.append(cv2.resize(img, (200, 200)))
                        labels.append(current_label)
                current_label += 1

        if not images:
            return False, "Belum ada sampel foto wajah untuk dilatih"

        # Latih model LBPH
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.train(images, np.array(labels))
        self.recognizer.save(str(self.model_path))
        self.labels_map_path.write_text(json.dumps(labels_map, indent=2), encoding="utf-8")
        return True, "Model pengenal wajah berhasil dilatih"

    def verify(self, frame: np.ndarray, expected_username: str | None = None) -> tuple[bool, float, str]:
        """
        Memverifikasi wajah dari satu frame webcam.
        Mengembalikan: (is_match, confidence_distance, keterangan)
        """
        if not self.model_path.exists() or not self.labels_map_path.exists():
            return False, 999.0, "Model wajah belum didaftarkan"

        faces = self.detect_faces(frame)
        if len(faces) == 0:
            return False, 999.0, "Wajah tidak terdeteksi"
        if len(faces) > 1:
            return False, 999.0, "Lebih dari satu wajah terdeteksi"

        x, y, w, h = faces[0]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        face_crop = cv2.resize(gray[y : y + h, x : x + w], (200, 200))

        # LBPH predict mengembalikan (label_id, distance). Jarak lebih kecil = lebih mirip
        try:
            self._load_trained_model_if_exists()
            label_id, distance = self.recognizer.predict(face_crop)
        except Exception as e:
            return False, 999.0, f"Gagal memprediksi wajah: {e}"

        labels_map = self._get_labels_map()
        recognized_user = labels_map.get(str(label_id), "Unknown")

        if expected_username and recognized_user.lower() != expected_username.lower():
            return False, distance, f"Wajah terdeteksi bukan milik '{expected_username}'"

        if distance <= self.threshold:
            return True, distance, f"Wajah cocok ({recognized_user}, skor: {distance:.1f})"
        else:
            return False, distance, f"Wajah tidak cocok (skor jarak {distance:.1f} > ambang {self.threshold})"
