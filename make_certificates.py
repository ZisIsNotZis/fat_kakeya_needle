"""Compute certified strict upper bounds for headline constructions.

Usage: python3 make_certificates.py
Writes results/certificates.json and prints a table.
"""
from __future__ import annotations

import json
import math

import numpy as np

from strict_bound import strict_upper


def pose_fn_v2(keyframes, eps):
    """optimize_v2.py stores keyframes as [theta, z_x, z_y] rows where
    (z_x, z_y) are signed-log coordinates of the sweeper_v2.LogSweeper
    (center = sigma*(exp(z)-1)).  Decode to world centers first."""
    kf = np.asarray(keyframes, dtype=float)
    import math as _math
    sigma = max(1.0, 8.0 * eps)
    centers = sigma * np.expm1(kf[:, 1:3])
    th = kf[:, 0]
    xy = centers

    def pose(s):
        t = s * (len(kf) - 1)
        i = min(int(t), len(kf) - 2)
        frac = t - i
        theta = th[i] + (th[i + 1] - th[i]) * frac
        cx = xy[i, 0] + (xy[i + 1, 0] - xy[i, 0]) * frac
        cy = xy[i, 1] + (xy[i + 1, 1] - xy[i, 1]) * frac
        return (theta, cx, cy)
    return pose


def pose_fn_pivot(pivot_slide_mod, params):
    """pivot+slide model: decode params, pose rotates about P_i within
    segment i, slides at keyframes."""
    P, centers, f, beta = pivot_slide_mod.centers_and_pivots(params)
    K = pivot_slide_mod.K
    th = pivot_slide_mod.theta
    u = pivot_slide_mod.u

    def pose(s):
        t = s * K
        i = min(int(t), K - 1)
        frac = t - i
        theta = th[i] + (th[i + 1] - th[i]) * frac
        # needle pivots about P[i] at fraction f[i]:
        c = P[i] - 0.5 * f[i] * u[i] + \
            (P[i] - 0.5 * f[i] * u[i + 1] - (P[i] - 0.5 * f[i] * u[i])) * frac
        return (theta, c[0], c[1])
    return pose


def main() -> int:
    out = []

    # --- v2 keyframe certificates -------------------------------------
    for fn, eps, label in [("results/v2_0005.json", 0.005, "v2@0.005"),
                           ("results/v2_001.json", 0.01, "v2@0.01")]:
        try:
            runs = json.load(open(fn))
        except (OSError, json.JSONDecodeError) as e:
            print(f"skip {fn}: {e}")
            continue
        best = min(runs, key=lambda r: r["area"])
        pose = pose_fn_v2(np.asarray(best["keyframes"]), eps)
        for n_sub in (150, 300):
            r = strict_upper(eps, pose, n_sub=n_sub, m_sample=12)
            print(f"{label} n_sub={n_sub}: lower={r['lower']:.5f} "
                  f"upper={r['upper']:.5f} gap={r['gap']:.5f}", flush=True)
        out.append({"label": label, "eps": eps, "claimed": best["area"],
                    "certified_upper": r["upper"], "lower": r["lower"],
                    "gap": r["gap"], "n_sub": n_sub, "model": "v2-keyframe"})

    # --- pivot+slide certificate ---------------------------------------
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pivot_slide", "pivot_slide.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    try:
        runs = json.load(open("results/pivot_005_K16_night.json"))
        best = min(runs, key=lambda r: r["area"])
        model = mod.PivotSlideModel(best["eps"], K=best["K"])
        pose = pose_fn_pivot(model, np.asarray(best["params"]))
        r = strict_upper(best["eps"], pose, n_sub=300, m_sample=10)
        print(f"pivot@0.05 K=16 n_sub=300: lower={r['lower']:.5f} "
              f"upper={r['upper']:.5f} gap={r['gap']:.5f}", flush=True)
        out.append({"label": "pivot@0.05", "eps": best["eps"],
                    "claimed": best["area"], "certified_upper": r["upper"],
                    "lower": r["lower"], "gap": r["gap"], "n_sub": 300,
                    "model": "pivot-slide"})
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"pivot certificate failed: {e}")

    try:
        with open("results/certificates.json", "w") as fh:
            json.dump(out, fh, indent=1)
        print("wrote results/certificates.json")
    except OSError as e:
        print(f"write failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
