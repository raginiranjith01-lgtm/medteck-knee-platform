"""Persist and analyze patient cases for research comparisons."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _cases_path(base_dir: Path) -> Path:
    return base_dir / "data" / "cases.json"


def _load_cases(base_dir: Path) -> list[dict]:
    path = _cases_path(base_dir)
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def _save_cases(base_dir: Path, cases: list[dict]) -> None:
    path = _cases_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(cases, f, indent=2)


def save_case(base_dir: Path, case_data: dict) -> str:
    cases = _load_cases(base_dir)
    case_id = str(uuid4())
    case_data["id"] = case_id
    case_data["created_at"] = datetime.now(timezone.utc).isoformat()
    cases.append(case_data)
    _save_cases(base_dir, cases)
    return case_id


def get_analytics(base_dir: Path) -> dict[str, Any]:
    cases = _load_cases(base_dir)
    if not cases:
        return {
            "total_cases": 0,
            "by_sex": {},
            "by_oa_status": {},
            "meniscus_comparison": {},
        }

    def avg_thickness(subset):
        vals = [c.get("mean_thickness_mm", 0) for c in subset if c.get("mean_thickness_mm")]
        return round(sum(vals) / len(vals), 2) if vals else 0

    male = [c for c in cases if c.get("sex", "").lower() in ("male", "m")]
    female = [c for c in cases if c.get("sex", "").lower() in ("female", "f")]
    oa = [c for c in cases if c.get("oa_status", "").lower() in ("oa", "yes", "positive")]
    non_oa = [c for c in cases if c.get("oa_status", "").lower() in ("non-oa", "no", "negative", "normal")]

    return {
        "total_cases": len(cases),
        "by_sex": {
            "male": {"count": len(male), "avg_meniscus_mm": avg_thickness(male)},
            "female": {"count": len(female), "avg_meniscus_mm": avg_thickness(female)},
        },
        "by_oa_status": {
            "oa": {"count": len(oa), "avg_meniscus_mm": avg_thickness(oa)},
            "non_oa": {"count": len(non_oa), "avg_meniscus_mm": avg_thickness(non_oa)},
        },
        "meniscus_comparison": {
            "oa_vs_non_oa_diff_mm": round(avg_thickness(non_oa) - avg_thickness(oa), 2),
            "male_vs_female_diff_mm": round(avg_thickness(male) - avg_thickness(female), 2),
        },
        "recent_cases": cases[-5:],
    }
