"""Smoke tests for hierarchical_pivot.HierModel.

(a) all-zero params -> pi/4 (0.787 +/- 0.003) at eps=0.05, K=8.
(b) equivalence: hand-computed ruler beta matches to_full_params output
    and area equals pivot_slide evaluation of the same beta (1e-9).
(c) short DE trial: K=8 (m+1=4 dims), small budget, area <= 0.65 (family
    must beat the fixed-center disk 0.787 meaningfully).
"""
import sys
import time

import numpy as np

from hierarchical_pivot import HierModel, ruler_betas, v2


class SmokeObj:
    def __init__(self, m):
        self.m = m
    def __call__(self, x):
        x = np.asarray(x, dtype=float)
        if not np.all(np.isfinite(x)):
            return 1e6
        return self.m.swept_area(x)


def test_a() -> tuple[bool, str]:
    m = HierModel(8, 0.05)
    a = m.swept_area(np.zeros(m.ndim))
    ok = abs(a - 0.7854) < 0.004
    return ok, f"all-zero K=8 area={a:.5f} (pi/4=0.7854) {'PASS' if ok else 'FAIL'}"


def test_b() -> tuple[bool, str]:
    # K=4, m=2, s=[0.3,-0.2], alternating sign
    s = np.array([0.3, -0.2])
    m = HierModel(4, 0.05, sign_mode="alternating")
    x = np.concatenate([[0.1], s])
    full = m.to_full_params(x)
    # hand-computed betas: j=1..3
    expected = []
    for j in range(1, 4):
        r = 1 + v2(j)
        k = j >> r
        sign = 1.0 if k % 2 == 0 else -1.0
        expected.append(sign * s[r - 1])
    betas = full[1 + 4:]  # skip y0 + f(4)
    b_ok = np.allclose(betas, expected, atol=1e-9)
    # area equivalence: reconstruct full params from betas with f=0
    full2 = np.concatenate([[0.1], np.zeros(4), expected])
    a1 = m.base.swept_area(full)
    a2 = m.base.swept_area(full2)
    a_ok = abs(a1 - a2) < 1e-9
    ok = b_ok and a_ok
    return ok, (f"beta match={b_ok} area match={a_ok} ({a1:.6f} vs {a2:.6f}) "
                f"{'PASS' if ok else 'FAIL'}")


def test_c() -> tuple[bool, str]:
    from scipy.optimize import differential_evolution, minimize
    from hierarchical_pivot import HierModel

    m = HierModel(8, 0.05)
    obj = SmokeObj(m)
    bounds = [(-3.0, 3.0)] * m.ndim
    rng = np.random.default_rng(0)
    t0 = time.time()
    res = differential_evolution(obj, bounds, rng=rng, popsize=12,
                                 maxiter=40, tol=1e-8, polish=False,
                                 workers=3, updating="deferred")
    pol = minimize(obj, res.x, method="Nelder-Mead",
                   options={"maxiter": 2000, "xatol": 1e-4, "fatol": 1e-8})
    a = min(float(res.fun), float(pol.fun))
    ok = a <= 0.65 and a > 0.2
    return ok, (f"short DE K=8: area={a:.5f} in {time.time()-t0:.0f}s "
                f"{'PASS' if ok else 'FAIL'}")


def main():
    results = [test_a(), test_b(), test_c()]
    for ok, msg in results:
        print(msg)
    print(f"TOTAL: {sum(1 for ok, _ in results if ok)}/3 PASS")
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
