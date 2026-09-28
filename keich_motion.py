"""Finite Keich THEORY recurrence; floating-point poses are demonstrations, not certificates."""

import argparse
from fractions import Fraction
import json
import math


MAX_N = 8  # At most 1025 stations and roughly 6000 elementary primitives.
SOURCE_URL = "https://authors.library.caltech.edu/records/js5yc-8gw95/files/KEIblms99.pdf"
SOURCE_SHA256 = "9b94f16437157cd5dca35b9bc98cca3190741573a5255cd0173a9d33976f5a0e"


def fraction_text(value):
    """Use one unambiguous representation for every exact rational output."""
    return str(value)


def level(eps):
    """Return floor(log2(1/eps)/4) by rational comparison, or reject the scale."""
    if eps <= 0:
        raise ValueError("eps must be positive")
    n = 0
    for candidate in range(1, MAX_N + 2):
        if eps > Fraction(1, 1 << (4 * candidate)):
            break
        n = candidate
    if n == 0:
        raise ValueError("eps must be at most 1/16 (the recurrence needs n >= 1)")
    if n > MAX_N:
        raise ValueError(f"n exceeds the safe maximum {MAX_N}")
    return n


def triangle(n, q):
    """Exact, unrotated Keich triangle, with e_1 the most significant bit."""
    M = 1 << n
    if n < 1 or not 0 <= q < M:
        raise ValueError("n must be positive and q an n-bit nonnegative integer")
    h = Fraction(1, M)
    a = Fraction(q, M)
    b = -sum((Fraction(i - 1, n * (1 << i)) * ((q >> (n - i)) & 1)
              for i in range(1, n + 1)), Fraction(0))
    c = a + 6 * b - 2 * h
    return {"q": q, "bits": format(q, f"0{n}b"), "a": a, "b": b, "c": c,
            "vertices": ((Fraction(0), c), (Fraction(0), c - h),
                         (Fraction(1), c + a))}


def rotate(point, angle):
    x, y = map(float, point)
    return [x * math.cos(angle) - y * math.sin(angle),
            x * math.sin(angle) + y * math.cos(angle)]


def station(tri, block, lower=False):
    """Midpoint of a rational triangle edge and a centered floating unit segment."""
    if block not in range(4) or (lower and
                                  (block != 3 or tri["q"] != (1 << len(tri["bits"])) - 1)):
        raise ValueError("the terminal lower edge is only used at the last block's last q")
    a, c = tri["a"], tri["c"]
    h = Fraction(1, 1 << len(tri["bits"]))
    slope = a + h if lower else a
    midpoint = (Fraction(1, 2), c + a / 2 - (h / 2 if lower else 0))
    theta = math.pi if lower else block * math.pi / 4 + math.atan(float(a))
    center = rotate(midpoint, block * math.pi / 4)
    norm = math.sqrt(1 + float(slope) ** 2)
    local_direction = (1 / norm, float(slope) / norm)
    direction = rotate(local_direction, block * math.pi / 4)
    return {"block": block, "q": tri["q"], "edge": "lower" if lower else "upper",
            "slope": fraction_text(slope),
            "edge_midpoint_local": [fraction_text(v) for v in midpoint],
            "center": center, "theta": theta,
            "unit_segment": [[center[i] - direction[i] / 2 for i in range(2)],
                             [center[i] + direction[i] / 2 for i in range(2)]]}


def pose(center, theta):
    return {"center": list(center), "theta": theta}


def slide(start, length, station_transition):
    center, theta = start["center"], start["theta"]
    end = pose([center[0] + length * math.cos(theta),
                center[1] + length * math.sin(theta)], theta)
    return {"kind": "slide", "station_transition": station_transition,
            "length": length, "start": start, "end": end}


def turn(start, angle, station_transition):
    end = pose(start["center"], start["theta"] + angle)
    return {"kind": "center_rotate", "station_transition": station_transition,
            "angle": angle, "start": start, "end": end}


def connector(start, target_center, R, station_transition=0):
    """Ordered axial slide / center rotation commutator, returning float primitives.

    The exact displacement identity behind these float operations is
    sigma*R*(u(theta)-u(theta+alpha)) + t*u(theta) = A*u(theta)+B*u_perp(theta).
    """
    if R < 28:
        raise ValueError("R must be at least 28")
    theta = start["theta"]
    if not 0 <= theta <= math.pi:
        raise ValueError("connector angle must lie in [0, pi]")
    dx = target_center[0] - start["center"][0]
    dy = target_center[1] - start["center"][1]
    A = dx * math.cos(theta) + dy * math.sin(theta)
    B = -dx * math.sin(theta) + dy * math.cos(theta)
    if math.hypot(dx, dy) > 14:
        raise ValueError("station centers must be at most D=14 apart")
    if B == 0:
        return [slide(start, A, station_transition)]
    # Choose a positive alpha near zero, negative near pi. R>=2D gives
    # |alpha|<=pi/6, so either sign remains inside [0,pi].
    sigma = (-1 if B > 0 else 1) if theta <= math.pi / 2 else (1 if B > 0 else -1)
    alpha = math.asin(-B / (sigma * R))
    if not 0 <= theta + alpha <= math.pi:
        raise ValueError("connector intermediate angle leaves [0, pi]")
    t = A - sigma * R * (2 * math.sin(alpha / 2) ** 2)
    steps = []
    current = start
    for kind, value in (("slide", sigma * R), ("center_rotate", alpha),
                        ("slide", -sigma * R), ("center_rotate", -alpha),
                        ("slide", t)):
        step = (slide(current, value, station_transition) if kind == "slide"
                else turn(current, value, station_transition))
        steps.append(step)
        current = step["end"]
    return steps


def generate(eps):
    n = level(eps)
    M = 1 << n
    h = Fraction(1, M)
    R = max(28, M * M)
    triangles = [triangle(n, q) for q in range(M)]
    stations = [station(tri, block) for block in range(4) for tri in triangles]
    stations.append(station(triangles[-1], 3, lower=True))
    primitives = []
    current = pose(stations[0]["center"], stations[0]["theta"])
    for index, destination in enumerate(stations[1:]):
        local_turn = turn(current, destination["theta"] - current["theta"], index)
        primitives.append(local_turn)
        current = local_turn["end"]
        steps = connector(current, destination["center"], R, index)
        primitives.extend(steps)
        current = steps[-1]["end"]
    return {
        "eps": fraction_text(eps), "n": n, "M": M, "h": fraction_text(h), "R": R,
        "source_logic": {
            "level": "largest n >= 1 with eps <= 2^(-4n); reject n > MAX_N",
            "bits": "e_i is bit i of the exactly n-bit q, most significant first",
            "triangle": "a=q/2^n; b=-sum((i-1)*e_i*2^(-i))/n; c=a+6*b-2*h; vertices=(0,c),(0,c-h),(1,c+a)",
            "stations": "four rotated blocks: q=0..M-1 upper edge; final block 3, q=M-1 lower edge",
            "connector": "rotate at old center to next theta, then sigma*R, alpha, -sigma*R, -alpha, t; alpha=asin(-B/(sigma*R)), t=A-sigma*R*(1-cos(alpha))",
            "reference": SOURCE_URL, "pdf_sha256": SOURCE_SHA256,
            "theory": "docs/keich-explicit-motion.md",
        },
        "triangles": [{"q": tri["q"], "bits": tri["bits"],
                       "a": fraction_text(tri["a"]), "b": fraction_text(tri["b"]),
                       "c": fraction_text(tri["c"]),
                       "vertices": [[fraction_text(x), fraction_text(y)]
                                    for x, y in tri["vertices"]]}
                      for tri in triangles],
        "stations": stations, "primitives": primitives, "initial_pose": primitives[0]["start"],
        "final_pose": current,
        "limitations": [
            "Only the unrotated triangle data are exact Fractions; rotated station poses, unit segments and primitive poses use floating-point trigonometry.",
            "The formulas in the cited THEORY documents, not this float output, support the mathematical area bound; no swept area is evaluated or strictly certified here.",
            "This is a non-optimized finite demonstration with temporary angle reversals and long excursions; numerical drift is possible.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eps", help="positive rational decimal or numerator/denominator, at most 1/16")
    args = parser.parse_args(argv)
    try:
        eps = Fraction(args.eps)
        record = generate(eps)
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        parser.error(str(exc))
    print(json.dumps(record, separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    main()
