"""Module 2: Femoral/tibial measurement and implant sizing."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from lib.image_processor import detect_knee_roi, estimate_pixel_to_mm, normalize_image
from lib.json_utils import json_safe


@dataclass
class BoneMeasurement:
    bone: str
    width_mm: float
    ap_mm: float
    region_x: int
    region_y: int
    region_w: int
    region_h: int


@dataclass
class ImplantMatch:
    component: str
    size: str
    score: float
    width_mm: float
    ap_mm: float
    fit_notes: str


@dataclass
class ImplantSizingResult:
    femoral: BoneMeasurement
    tibial: BoneMeasurement
    femoral_matches: list[ImplantMatch]
    tibial_matches: list[ImplantMatch]
    recommended_femoral: ImplantMatch
    recommended_tibial: ImplantMatch
    pixel_to_mm: float


def _load_database(base_dir: Path) -> dict:
    with open(base_dir / "data" / "implant_database.json") as f:
        return json.load(f)


def _measure_bone(img: np.ndarray, x: int, y: int, w: int, h: int, pixel_to_mm: float, bone: str) -> BoneMeasurement:
    region = img[y : y + h, x : x + w]
    if region.size == 0:
        width_px, ap_px = w, h
    else:
        width_px = w
        ap_px = int(h * 0.85)

    return BoneMeasurement(
        bone=bone,
        width_mm=round(width_px * pixel_to_mm, 1),
        ap_mm=round(ap_px * pixel_to_mm, 1),
        region_x=x,
        region_y=y,
        region_w=w,
        region_h=h,
    )


def _rank_implants(measured_width: float, measured_ap: float, components: list[dict], component_name: str) -> list[ImplantMatch]:
    matches = []
    for comp in components:
        w_diff = abs(measured_width - comp["width"])
        ap_diff = abs(measured_ap - comp["ap"])
        score = round(100 - (w_diff * 1.2 + ap_diff * 0.8), 1)
        score = max(0, min(100, score))

        notes = "Good fit"
        if measured_width > comp["width"] + 2:
            notes = "Risk of under-coverage — consider larger size"
        elif measured_width < comp["width"] - 3:
            notes = "Risk of overhang — consider smaller size"

        matches.append(
            ImplantMatch(
                component=component_name,
                size=comp["size"],
                score=score,
                width_mm=comp["width"],
                ap_mm=comp["ap"],
                fit_notes=notes,
            )
        )

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches


def analyze_implant_sizing(img: np.ndarray, base_dir: Path, pixel_to_mm=None) -> ImplantSizingResult:
    normalized = normalize_image(img)
    px_to_mm = estimate_pixel_to_mm(normalized, pixel_to_mm)
    x, y, w, h = detect_knee_roi(normalized)

    femur_h = int(h * 0.38)
    tibia_h = int(h * 0.38)
    meniscus_h = h - femur_h - tibia_h

    femoral = _measure_bone(normalized, x, y, w, femur_h, px_to_mm, "Femur")
    tibial = _measure_bone(normalized, x, y + femur_h + meniscus_h, w, tibia_h, px_to_mm, "Tibia")

    db = _load_database(base_dir)
    femoral_matches = _rank_implants(femoral.width_mm, femoral.ap_mm, db["femoral_components"], "Femoral")
    tibial_matches = _rank_implants(tibial.width_mm, tibial.ap_mm, db["tibial_components"], "Tibial")

    return ImplantSizingResult(
        femoral=femoral,
        tibial=tibial,
        femoral_matches=femoral_matches[:5],
        tibial_matches=tibial_matches[:5],
        recommended_femoral=femoral_matches[0],
        recommended_tibial=tibial_matches[0],
        pixel_to_mm=px_to_mm,
    )


def result_to_dict(result: ImplantSizingResult) -> dict[str, Any]:
    return json_safe({
        "femoral": asdict(result.femoral),
        "tibial": asdict(result.tibial),
        "femoral_matches": [asdict(m) for m in result.femoral_matches],
        "tibial_matches": [asdict(m) for m in result.tibial_matches],
        "recommended_femoral": asdict(result.recommended_femoral),
        "recommended_tibial": asdict(result.recommended_tibial),
        "pixel_to_mm": result.pixel_to_mm,
    })
