"""Collect sweep results, plot area(eps), and test scaling hypotheses.

Checks:
  * f(eps) = eps^2 f(1/eps)  (your similarity claim; verified by running
    the optimizer's best motion for eps=1/e' scaled up, for one pair)
  * f(eps) ~ A / log(c/eps)  (the known asymptotic rate)
"""
import glob
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(results_dir="results"):
    pts = []
    for f in sorted(glob.glob(f"{results_dir}/eps_*.json")):
        try:
            with open(f) as fh:
                runs = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            print(f"skipping unreadable result file {f}: {e}", file=sys.stderr)
            continue
        best = min(runs, key=lambda r: r["area_hi"])
        pts.append((best["eps"], best["area_hi"], best["K"],
                    best["area"], len(runs)))
    pts.sort()
    return pts


def fit_log_model(eps, area):
    """area ~ A / (log(1/eps) + B)   (2-param least squares on that form)."""
    L = np.log(1.0 / np.asarray(eps, dtype=float))
    # grid search B, linear solve A: area * (L + B) = A
    best = None
    for B in np.linspace(-2, 20, 2001):
        A = np.sum(area * (L + B)) / np.sum((L + B) ** 2)
        resid = np.sum((area - A / (L + B)) ** 2)
        if best is None or resid < best[0]:
            best = (resid, A, B)
    return best  # (resid, A, B)


def main():
    pts = load()
    if not pts:
        print("no results yet")
        return 1
    eps = np.array([p[0] for p in pts])
    area = np.array([p[1] for p in pts])

    print("eps      area_best   (K, seeds, area_coarse)")
    for e, a, K, ac, ns in pts:
        print(f"{e:<8g} {a:<11.5f} (K={K}, {ns} seeds, coarse {ac:.5f})")

    fit = fit_log_model(eps, area)
    if fit is None:
        print("log-model fit failed (no data?)")
        return 1
    resid, A, B = fit
    print(f"\nfit area = A/(log(1/eps)+B):  A={A:.4f}  B={B:.3f}  "
          f"resid={resid:.2e}")

    # compare with a pure power law area = C * eps^p
    p, logC = np.polyfit(np.log(eps), np.log(area), 1)
    pred_pow = np.exp(logC) * eps ** p
    resid_pow = np.sum((area - pred_pow) ** 2)
    print(f"power-law fit: C={np.exp(logC):.4f} p={p:.3f} resid={resid_pow:.2e}")
    print("=> log model", "WINS" if resid < resid_pow else "loses",
          "(expected: log wins as eps -> 0)")

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    ax[0].plot(eps, area, "o-", label="optimized (K=6, best of seeds)")
    ee = np.linspace(eps.min(), eps.max(), 300)
    ax[0].plot(ee, A / (np.log(1 / ee) + B), "--",
               label=f"A/(log(1/e)+B), A={A:.3f} B={B:.2f}")
    ax[0].plot(ee, np.exp(logC) * ee ** p, ":",
               label=f"power law e^{p:.2f}")
    ax[0].plot(ee, np.pi / 4 * np.ones_like(ee), "gray", lw=0.8,
               label="pi/4 (fixed center)")
    ax[0].set_xscale("log")
    ax[0].set_xlabel("eps")
    ax[0].set_ylabel("swept area")
    ax[0].legend()
    ax[0].set_title("fat Kakeya: area vs eps")

    ax[1].plot(1 / np.log(1 / eps), area, "o-")
    ax[1].set_xlabel("1/log(1/eps)")
    ax[1].set_ylabel("area")
    ax[1].set_title("area vs 1/log(1/eps)  (straight => log law)")
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("area_vs_eps.png", dpi=140)
    print("wrote area_vs_eps.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
