from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import math


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def _percentile(sorted_vals: List[float], p: float) -> float:
    """
    Simple linear-interpolation percentile.
    sorted_vals must be sorted ascending and non-empty.
    p is in [0, 1].
    """
    if not sorted_vals:
        raise ValueError("percentile requires non-empty list")
    if p <= 0:
        return sorted_vals[0]
    if p >= 1:
        return sorted_vals[-1]

    n = len(sorted_vals)
    idx = (n - 1) * p
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return sorted_vals[lo]
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def compute_score_range_from_calibration_hits(
    calibration_hits: List[Dict[str, Any]],
    points_possible: float = 40.0,
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Returns:
      (score_low, score_high, explanation_text)

    Uses ONLY grade_numeric values from calibration hits (deterministic).
    - Base range uses IQR: [p25, p75]
    - Widens range when sample is small or distances suggest low similarity
    - Clamps to [0, points_possible]
    """

    pts = _safe_float(points_possible) or 0.0
    if pts <= 0:
        return None, None, "Points possible is not set to a valid positive number."

    # Pull grades + distances
    grades: List[float] = []
    dists: List[float] = []
    for h in calibration_hits or []:
        g = _safe_float(h.get("grade_numeric"))
        if g is not None:
            grades.append(g)
        d = _safe_float(h.get("distance"))
        if d is not None:
            dists.append(d)

    if len(grades) < 3:
        return (
            None,
            None,
            f"Not enough graded calibration examples yet ({len(grades)} found). Add at least 3 with grade_numeric to compute a range.",
        )

    # Clamp grades to [0, pts] just in case older data is messy
    grades = [max(0.0, min(pts, g)) for g in grades]
    grades.sort()

    p25 = _percentile(grades, 0.25)
    p50 = _percentile(grades, 0.50)
    p75 = _percentile(grades, 0.75)

    base_low, base_high = p25, p75

    # Confidence heuristics
    n = len(grades)
    avg_dist = (sum(dists) / len(dists)) if dists else None

    # Widening rules (MVP-friendly):
    # - small sample -> widen
    # - higher average distance -> widen more
    widen = 0.0

    # Sample-size widen
    if n == 3:
        widen += 0.18 * pts
    elif n <= 5:
        widen += 0.12 * pts
    elif n <= 8:
        widen += 0.08 * pts
    else:
        widen += 0.04 * pts

    # Distance widen (tuned to your observed distances, ~0.37 for good match)
    # Lower distance = more similar = tighter
    confidence_note = "medium confidence"
    if avg_dist is None:
        widen += 0.06 * pts
        confidence_note = "medium confidence (no distance signal)"
    else:
        if avg_dist <= 0.45:
            widen += 0.03 * pts
            confidence_note = "higher confidence"
        elif avg_dist <= 0.65:
            widen += 0.08 * pts
            confidence_note = "medium confidence"
        else:
            widen += 0.16 * pts
            confidence_note = "low confidence"

    low = base_low - widen
    high = base_high + widen

    # Clamp and ensure ordering
    low = max(0.0, min(pts, low))
    high = max(0.0, min(pts, high))
    if high < low:
        low, high = high, low

    # Round to something sensible (avoid goofy decimals)
    low_r = round(low, 1)
    high_r = round(high, 1)

    expl = (
        f"Range based on {n} graded calibration examples (median {round(p50,1)}), {confidence_note}. "
        f"Computed from the middle 50% of similar past work, then widened for uncertainty."
    )
    return low_r, high_r, expl
