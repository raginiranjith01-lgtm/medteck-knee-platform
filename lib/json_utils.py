"""Convert numpy types to native Python for JSON serialization."""

from __future__ import annotations

from typing import Any

import numpy as np


def json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    # NumPy 2.x scalars (e.g. np.bool_) subclass Python bool/int/float
    # but are NOT json-serializable — catch by module name.
    if type(obj).__module__ == "numpy":
        return obj.item() if hasattr(obj, "item") else obj
    return obj
