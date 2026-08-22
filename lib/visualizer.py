"""Draw anatomical overlays on knee images."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


COLORS = {
    "Femur": (66, 135, 245),
    "Medial Meniscus": (46, 204, 113),
    "Tibia": (241, 196, 15),
}


def create_visualization(img: np.ndarray, meniscus_result: dict, implant_result: dict) -> str:
    """Return base64 PNG with structure overlays and measurement markers."""
    if len(img.shape) == 2:
        canvas = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        canvas = img.copy()

    for structure in meniscus_result.get("structures", []):
        name = structure["name"]
        color = COLORS.get(name, (200, 200, 200))
        x, y, w, h = structure["x"], structure["y"], structure["width"], structure["height"]
        cv2.rectangle(canvas, (x, y), (x + w, y + h), color, 2)
        cv2.putText(canvas, name, (x + 4, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    for m in meniscus_result.get("measurements", []):
        cx, cy = m["x"], m["y"]
        half = 15
        cv2.line(canvas, (cx, cy - half), (cx, cy + half), (0, 255, 255), 2)
        label = f"{m['location']}: {m['thickness_mm']}mm"
        cv2.putText(canvas, label, (cx + 8, cy - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    femoral = implant_result.get("femoral", {})
    tibial = implant_result.get("tibial", {})
    for bone in (femoral, tibial):
        if not bone:
            continue
        x, y, w, h = bone["region_x"], bone["region_y"], bone["region_w"], bone["region_h"]
        cv2.putText(
            canvas,
            f"{bone['bone']} W:{bone['width_mm']} AP:{bone['ap_mm']}mm",
            (x + 4, y + h - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1,
        )

    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    buf = BytesIO()
    pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")
