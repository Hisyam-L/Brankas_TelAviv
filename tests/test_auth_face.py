from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np

from auth.face_auth import FaceAuth


def test_face_auth_init_and_no_faces(tmp_path: Path):
    auth = FaceAuth(faces_dir=tmp_path / "faces")
    assert auth.cascade is not None
    assert not auth.cascade.empty()

    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = auth.detect_faces(blank_frame)
    assert len(faces) == 0

    valid, dist, msg = auth.verify(blank_frame)
    assert valid is False
    assert "belum didaftarkan" in msg or "tidak terdeteksi" in msg


def test_face_auth_train_and_verify(tmp_path: Path):
    faces_dir = tmp_path / "faces"
    auth = FaceAuth(faces_dir=faces_dir, threshold=80.0)

    # Buat sampel wajah sintetis untuk 'budi'
    budi_dir = faces_dir / "budi"
    budi_dir.mkdir(parents=True, exist_ok=True)

    # 10 sampel gambar 200x200 dengan pola seragam
    base_face = (np.ones((200, 200), dtype=np.uint8) * 128)
    cv2.circle(base_face, (70, 70), 20, 50, -1)   # Mata kiri
    cv2.circle(base_face, (130, 70), 20, 50, -1)  # Mata kanan
    cv2.line(base_face, (80, 140), (120, 140), 50, 4)  # Mulut

    for i in range(10):
        noisy_face = np.clip(base_face + np.random.randint(-5, 6, (200, 200)), 0, 255).astype(np.uint8)
        cv2.imwrite(str(budi_dir / f"{i:03d}.png"), noisy_face)

    # Latih model
    success, msg = auth.train_model()
    assert success is True
    assert auth.model_path.exists()
    assert auth.is_enrolled("budi") is True
    assert auth.is_enrolled("alice") is False
