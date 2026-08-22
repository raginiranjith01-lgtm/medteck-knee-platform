"""Module 1: Medial meniscus thickness and OA assessment."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from lib.image_processor import detect_knee_roi, estimate_pixel_to_mm, normalize_image
from lib.json_utils import json_safe


@dataclass
class StructureRegion:
    name: str
    x: int
    y: int
    width: int
    height: int


@dataclass
class MeniscusMeasurement:
    location: str
    thickness_mm: float
    x: int
    y: int


@dataclass
class MeniscusAnalysisResult:
    structures: list[StructureRegion]
    measurements: list[MeniscusMeasurement]
    mean_thickness_mm: float
    oa_assessment: dict[str, Any]
    pixel_to_mm: float


def _load_reference(base_dir: Path) -> dict:
    db_path = base_dir / "data" / "implant_database.json"
    with open(db_path) as f:
        return json.load(f)["reference_meniscus_thickness_mm"]


def _estimate_structures(roi: np.ndarray, x0: int, y0: int, w: int, h: int) -> list[StructureRegion]:
    """Estimate femur, tibia, and medial meniscus regions within ROI."""
    femur_h = int(h * 0.38)
    tibia_h = int(h * 0.38)
    meniscus_h = h - femur_h - tibia_h

    femur = StructureRegion("Femur", x0, y0, w, femur_h)
    meniscus = StructureRegion("Medial Meniscus", x0, y0 + femur_h, w, max(meniscus_h, 8))
    tibia = StructureRegion("Tibia", x0, y0 + femur_h + meniscus_h, w, tibia_h)
    return [femur, meniscus, tibia]


def _measure_meniscus_thickness(
    img: np.ndarray,
    meniscus: StructureRegion,
    pixel_to_mm: float,
) -> list[MeniscusMeasurement]:
    """Measure thickness at anterior, mid-body, and posterior horn."""
    region = img[meniscus.y : meniscus.y + meniscus.height, meniscus.x : meniscus.x + meniscus.width]
    if region.size == 0:
        region = img

    col_strength = np.mean(region, axis=0)
    grad = np.abs(np.gradient(col_strength.astype(float)))
    peak_cols = np.argsort(grad)[-3:]
    peak_cols = sorted(peak_cols)

    locations = ["Anterior", "Mid-body", "Posterior horn"]
    measurements: list[MeniscusMeasurement] = []

    for loc, col in zip(locations, peak_cols):
        col = int(np.clip(col, 0, region.shape[1] - 1))
        column = region[:, col]
        edges = np.where(column < np.percentile(column, 35))[0]
        if len(edges) >= 2:
            thickness_px = edges[-1] - edges[0]
        else:
            thickness_px = max(region.shape[0] * 0.12, 5)

        thickness_px = max(thickness_px, 3)
        cx = meniscus.x + col
        cy = meniscus.y + meniscus.height // 2
        measurements.append(
            MeniscusMeasurement(
                location=loc,
                thickness_mm=round(thickness_px * pixel_to_mm, 2),
                x=cx,
                y=cy,
            )
        )

    return measurements


def _assess_oa(
    measurements: list[MeniscusMeasurement],
    sex: str,
    oa_status: str,
    reference: dict,
) -> dict[str, Any]:
    sex_key = "male" if sex.lower() in ("male", "m") else "female"
    ref = reference[sex_key]
    loc_map = {
        "Anterior": "anterior",
        "Mid-body": "mid_body",
        "Posterior horn": "posterior",
    }

    comparisons = []
    for m in measurements:
        ref_val = ref[loc_map[m.location]]
        diff_pct = round(float(m.thickness_mm - ref_val) / ref_val * 100, 1)
        comparisons.append(
            {
                "location": m.location,
                "measured_mm": float(m.thickness_mm),
                "reference_mm": float(ref_val),
                "difference_percent": diff_pct,
                "below_reference": bool(float(m.thickness_mm) < float(ref_val)),
            }
        )

    mean_measured = float(sum(float(m.thickness_mm) for m in measurements) / len(measurements))
    mean_ref = float(sum(ref.values()) / len(ref))
    reduction = round((mean_ref - mean_measured) / mean_ref * 100, 1)

    oa_likelihood = "Low"
    if reduction >= reference["oa_reduced_percent"]:
        oa_likelihood = "High"
    elif reduction >= reference["oa_reduced_percent"] * 0.5:
        oa_likelihood = "Moderate"

    return {
        "sex_reference": sex_key,
        "clinical_oa_label": oa_status,
        "ai_oa_likelihood": oa_likelihood,
        "mean_thickness_mm": round(mean_measured, 2),
        "reference_mean_mm": round(mean_ref, 2),
        "reduction_vs_reference_percent": reduction,
        "location_comparisons": comparisons,
        "note": "Decision-support only — not a clinical diagnosis.",
    }


def analyze_meniscus(
    img: np.ndarray,
    base_dir: Path,
    sex: str = "male",
    oa_status: str = "unknown",
    pixel_to_mm: float | None = None,
) -> MeniscusAnalysisResult:
    normalized = normalize_image(img)
    px_to_mm = estimate_pixel_to_mm(normalized, pixel_to_mm)
    x, y, w, h = detect_knee_roi(normalized)
    structures = _estimate_structures(normalized[y : y + h, x : x + w], x, y, w, h)
    meniscus = next(s for s in structures if s.name == "Medial Meniscus")
    measurements = _measure_meniscus_thickness(normalized, meniscus, px_to_mm)
    reference = _load_reference(base_dir)
    oa_assessment = _assess_oa(measurements, sex, oa_status, reference)
    mean_thickness = sum(m.thickness_mm for m in measurements) / len(measurements)

    return MeniscusAnalysisResult(
        structures=structures,
        measurements=measurements,
        mean_thickness_mm=round(mean_thickness, 2),
        oa_assessment=oa_assessment,
        pixel_to_mm=px_to_mm,
    )


def result_to_dict(result: MeniscusAnalysisResult) -> dict:
    return json_safe({
        "structures": [asdict(s) for s in result.structures],
        "measurements": [asdict(m) for m in result.measurements],
        "mean_thickness_mm": result.mean_thickness_mm,
        "oa_assessment": result.oa_assessment,
        "pixel_to_mm": result.pixel_to_mm,
    })
