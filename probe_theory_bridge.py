"""Theory-bridge probe (ticket 04): replace in-place pivots by Keich excursions.

Simplified excursion at station i of the first half:
  slide out R along u_i, rotate the SAME small angle delta about the needle's
  own center, slide back R along u_{i+1}.  The excursion displaces the chain
  remainder by the rigid offset  Delta += R*(u_i - u_{i+1}); a rigid
  translation does not change swept area, so any area change is attributable
  to the excursion itself.  Numerical estimates only -- NOT a certificate.
"""
import json
import math
from pathlib import Path

import numpy as np

import motion_adapters
import integer_motion_area
from motion_adapters import _pose, _full_halfturn
from smooth_pivot import SmoothProfileModel

EPS = 0.002
STEP_FRACTION_SWEEP = 1e-3
STEP_FRACTION_CONFIRM = 1e-4
CARRIER = "results/coarse_refine_0002_K256.json"


def load_carrier():
    record = json.loads(Path(CARRIER).read_text())[0]
    model = SmoothProfileModel(record["K"], record["eps"],
                               record["Nf"], record["Nb"], record["n_arc"])
    full = model.to_full_params(np.asarray(record["best_params"], dtype=float))
    return record, model, full


def first_half(model, params):
    """First-half primitive list of the archived motion (identical construction
    to motion_adapters.pivot_primitives, pre-mirror)."""
    captured = []

    def capture(first):
        captured.append(first)
        return first

    original = motion_adapters._full_halfturn
    motion_adapters._full_halfturn = capture
    try:
        motion_adapters.pivot_primitives(model.base, params)
    finally:
        motion_adapters._full_halfturn = original
    if len(captured) != 1:
        raise ValueError("unexpected primitive construction")
    return captured[0]


def excursion_first_half(model, params, start_station: int, m: int, r: float):
    """Rebuild the first half replacing stations [s, s+m) pivots by excursions.

    Kind layout matches pivot_primitives: pivot_rotate at even indices,
    slides between.  Excursion legs are slide / pivot_rotate / slide so the
    mirror machinery applies unchanged.
    """
    pivots, centers, fractions, slides = model.base.centers_and_pivots(params)
    theta, u = model.theta, model.base.u
    K = model.K
    if not (0 <= start_station and start_station + m <= K):
        raise ValueError("excursion window outside first half")
    out = []
    current = _pose(centers[0], theta[0])
    offset = np.zeros(2)

    def shifted(p):
        return np.asarray(p, dtype=float) + offset

    for i in range(K):
        angle = float(theta[i + 1] - theta[i])
        if start_station <= i < start_station + m:
            out.append({"kind": "slide", "length": r,
                        "start": current,
                        "end": _pose(np.asarray(current["center"]) + r * u[i],
                                     theta[i])})
            current = out[-1]["end"]
            rot = {"kind": "pivot_rotate", "pivot": list(current["center"]),
                   "fraction": 0., "angle": angle,
                   "start": current,
                   "end": _pose(current["center"], theta[i + 1])}
            out.append(rot)
            current = rot["end"]
            back = _pose(np.asarray(current["center"]) - r * u[i + 1], theta[i + 1])
            out.append({"kind": "slide", "length": -r, "start": current,
                        "end": back})
            current = back
            offset = offset + r * (u[i] - u[i + 1])
            if i < K - 1:  # keep the inter-station slide of the archived chain
                beta = float(slides[i])
                sld = _pose(np.asarray(current["center"]) + beta * u[i + 1],
                            theta[i + 1])
                out.append({"kind": "slide", "length": beta,
                            "start": current, "end": sld})
                current = sld
        else:
            f = float(fractions[i])
            nominal_start = shifted(pivots[i] - .5 * f * u[i])
            end_center = shifted(pivots[i] - .5 * f * u[i + 1])
            rot = {"kind": "pivot_rotate",
                   "pivot": list(shifted(pivots[i])), "fraction": f,
                   "angle": angle, "start": current, "end": _pose(end_center, theta[i + 1])}
            out.append(rot)
            current = rot["end"]
            if i < K - 1:
                beta = float(slides[i])
                sld = _pose(np.asarray(current["center"]) + beta * u[i + 1],
                            theta[i + 1])
                out.append({"kind": "slide", "length": beta,
                            "start": current, "end": sld})
                current = sld
    return out, offset


def evaluate_primitives(first, eps, step_fraction):
    full = _full_halfturn(first)
    return integer_motion_area.evaluate(full, eps=eps,
                                        step_fraction=step_fraction,
                                        max_wall_s=600)


def run(out_path="results/theory_bridge_probe_0002_K256.json",
        confirm=True):
    record, model, full = load_carrier()
    base_first = first_half(model, full)
    base_row = evaluate_primitives(base_first, record["eps"],
                                   STEP_FRACTION_SWEEP)
    if base_row["status"] != "ok":
        raise RuntimeError(f"baseline evaluation failed: {base_row}")
    baseline = float(base_row["numeric_outer_area"])

    positions = {"early": 32, "mid": 128, "late": 208}
    r_multipliers = [2, 4, 8, 16]  # units of half needle length 0.5
    variants = []
    for name, s in positions.items():
        for m in (1, 4, 16):
            for mult in r_multipliers:
                variants.append((f"{name}_m{m}_R{mult}", s, m, mult * .5))
    for mult in r_multipliers:
        variants.append((f"full_m256_R{mult}", 0, model.K, mult * .5))

    rows = [{"variant": "baseline", "start_station": None, "m": 0, "R": 0.,
             "area": baseline, "delta": 0., "delta_pct": 0.,
             "status": base_row["status"], "cpu_s": base_row.get("cpu_s"),
             "tier": "numerical_estimate"}]
    for name, s, m, r in variants:
        first, offset = excursion_first_half(model, full, s, m, r)
        row = evaluate_primitives(first, record["eps"], STEP_FRACTION_SWEEP)
        area = row.get("numeric_outer_area")
        delta = None if area is None else area - baseline
        rows.append({"variant": name, "start_station": s, "m": m, "R": r,
                     "offset_norm": float(np.hypot(*offset)),
                     "area": area, "delta": delta,
                     "delta_pct": None if delta is None else 100. * delta / baseline,
                     "status": row["status"], "cpu_s": row.get("cpu_s"),
                     "tier": "numerical_estimate"})

    confirmed = None
    best = min((x for x in rows[1:] if x["delta"] is not None),
               key=lambda x: x["delta"], default=None)
    if confirm and best is not None:
        s, m, r = best["start_station"], best["m"], best["R"]
        first, _ = excursion_first_half(model, full, s, m, r)
        hi = evaluate_primitives(first, record["eps"], STEP_FRACTION_CONFIRM)
        base_hi = evaluate_primitives(base_first, record["eps"],
                                      STEP_FRACTION_CONFIRM)
        confirmed = {
            "variant": best["variant"], "step_fraction": STEP_FRACTION_CONFIRM,
            "baseline_area": base_hi.get("numeric_outer_area"),
            "variant_area": hi.get("numeric_outer_area"),
            "delta": (None if hi.get("numeric_outer_area") is None else
                      hi["numeric_outer_area"] - base_hi["numeric_outer_area"]),
            "baseline_status": base_hi["status"], "variant_status": hi["status"],
            "tier": "numerical_estimate"}

    out = {"carrier": CARRIER, "eps": record["eps"],
           "K": record["K"], "baseline_step_fraction": STEP_FRACTION_SWEEP,
           "baseline_area": baseline,
           "baseline_limitation": integer_motion_area.LIMITATION,
           "note": ("numerical estimates at fixed resolution; the variant is "
                    "never certified; a smaller union is only meaningful "
                    "relative to the same-resolution baseline"),
           "variants": rows, "high_resolution_confirm": confirmed}
    Path(out_path).write_text(json.dumps(out, indent=1))
    return out


def main():
    result = run()
    best = min((x for x in result["variants"][1:]
                if x["delta"] is not None), key=lambda x: x["delta"])
    print("baseline", result["baseline_area"])
    print("best variant", best["variant"], best["area"],
          f"{best['delta_pct']:.3f}%")
    print("confirm", json.dumps(result["high_resolution_confirm"]))


if __name__ == "__main__":
    main()
