"""Load and preprocess knee medical images."""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np


def load_knee_image(path):
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not load image: {path.name}")
    # Downscale very large images for stable processing
    max_dim = 1200
    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def normalize_image(img: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(img)


def estimate_pixel_to_mm(img: np.ndarray, pixel_to_mm=None) -> float:
    if pixel_to_mm and pixel_to_mm > 0:
        return float(pixel_to_mm)
    return max(img.shape[1], img.shape[0]) / 512.0 * 0.15


def detect_knee_roi(img: np.ndarray) -> Tuple[int, int, int, int]:
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = img.shape
    if not contours:
        margin_x, margin_y = int(w * 0.1), int(h * 0.1)
        return margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y

    largest = max(contours, key=cv2.contourArea)
    x, y, bw, bh = cv2.boundingRect(largest)
    pad_x, pad_y = int(bw * 0.05), int(bh * 0.05)
    x = max(0, x - pad_x)
    y = max(0, y - pad_y)
    bw = min(w - x, bw + 2 * pad_x)
    bh = min(h - y, bh + 2 * pad_y)
    return x, y, bw, bh
