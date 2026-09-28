"""Exact-rational outer grid cover of the continuous pivot/slide motion.

Only the standard library is used in the proof path. Every input JSON number is
parsed as its printed decimal rational; polygons and closed-cell tests use integers.
The reported bound is deliberately coarse (closed grid cells are counted twice at
shared grid lines), but is an independently reproducible mathematical upper bound.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

D = 10**12  # Outward coordinate and trigonometric quantization denominator.


def floor(x: F) -> int:
    return x.numerator // x.denominator


def ceil(x: F) -> int:
    return -floor(-x)


def outward(a: F, b: F) -> tuple[int, int]:
    return floor(a * D), ceil(b * D)


def atan_remainder_inv(n: int, terms: int) -> tuple[F, F]:
    """Alternating arctan series; next signed term bounds the remainder."""
    s = sum(((-1)**k * F(1, (2*k+1)*n**(2*k+1)) for k in range(terms)), F(0))
    t = F(1, (2*terms+1)*n**(2*terms+1))
    return (s, s+t) if terms % 2 == 0 else (s-t, s)


def pi_interval() -> tuple[F, F]:
    # Machin: pi = 16 atan(1/5) - 4 atan(1/239).
    # Identity follows tan(4 atan(1/5))=120/119 and
    # tan(4 atan(1/5)-atan(1/239))=1, with angle in (0,pi/2).
    a, b = atan_remainder_inv(5, 32)
    c, d = atan_remainder_inv(239, 12)
    return 16*a-4*d, 16*b-4*c


def series_interval(x: F, sine: bool) -> tuple[F, F]:
    """Taylor alternating bounds for 0<=x<=pi/2, 17 and 18 terms."""
    assert 0 <= x <= F(11, 7)  # 11/7 > pi/2; tail terms decrease from k=16.
    term = x if sine else F(1)
    partial = F(0)
    sums = []
    for k in range(18):
        partial += term
        if k >= 16:
            sums.append(partial)
        power = 2*k+1 if sine else 2*k
        term *= -x*x/F((power+1)*(power+2))
    return min(sums), max(sums)


def trig_grid(K: int) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    pl, ph = pi_interval()
    assert F(3) < pl <= ph < F(22, 7)
    out = []
    for j in range(K+1):
        if j == 0:
            out.append(((D, D), (0, 0)))
        elif j == K:
            out.append(((0, 0), (D, D)))
        else:
            xl, xh = pl*j/F(2*K), ph*j/F(2*K)
            sl = series_interval(xl, True)[0]
            sh = series_interval(xh, True)[1]
            cl = series_interval(xh, False)[0]
            ch = series_interval(xl, False)[1]
            out.append((outward(cl, ch), outward(sl, sh)))
    return out


# Intervals below are integer numerators with implicit denominator D.
def add(a, b):
    return a[0]+b[0], a[1]+b[1]


def neg(a):
    return -a[1], -a[0]


def mul(a, scalar: F):
    l, h = (F(a[0], D)*scalar, F(a[1], D)*scalar)
    return outward(min(l, h), max(l, h))


def rect(p, u, f: F, eps: F):
    """Four outward interval corner boxes (pivot plus (t-f/2)u+v*u_perp)."""
    ux, uy = u
    hw = eps/2
    boxes = []
    for t in (-F(1, 2), F(1, 2)):
        for v in (-hw, hw):
            x = add(p[0], add(mul(ux, t-f/2), mul(uy, -v)))
            y = add(p[1], add(mul(uy, t-f/2), mul(ux, v)))
            boxes.append((x, y))
    return boxes


def box_points(boxes, pad: int = 0):
    for (xl, xh), (yl, yh) in boxes:
        for x in (xl-pad, xh+pad):
            for y in (yl-pad, yh+pad):
                yield x, y


def hull(points):
    pts = sorted(set(points))
    if len(pts) <= 1:
        return pts
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower, upper = [], []
    for chain, seq in ((lower, pts), (upper, reversed(pts))):
        for p in seq:
            while len(chain) >= 2 and cross(chain[-2], chain[-1], p) <= 0:
                chain.pop()
            chain.append(p)
    return lower[:-1]+upper[:-1]


def clip_f(f):
    return max(-F(1), min(F(1), f))


def number(value):
    """Only JSON numeric tokens (parsed to int/Fraction) define a motion."""
    if type(value) not in (int, F):
        raise ValueError('motion value must be a JSON number')
    return F(value)


def full_parameters(record):
    K = record['K']
    model = record.get('model')
    if model == 'pivot-slide':
        values = [number(v) for v in record['params']]
        if len(values) != 2*K:
            raise ValueError('pivot-slide parameter length')
        return values[0], [clip_f(v) for v in values[1:K+1]], values[K+1:]
    # Local refinement records omit 'model'; their explicit smooth layout
    # identifies the motion. Never reinterpret a different labeled model.
    if model not in (None, 'pivot-slide-smooth') or 'keyframes' in record or 'params' in record:
        raise ValueError('unsupported motion model for rational pivot certificate')
    if record['Nf'] < 2 or record['Nb'] < 2 or len(record['best_params']) != 1+record['Nf']+record['Nb']:
        raise ValueError('smooth parameter length')
    vals = [number(v) for v in record['best_params']]
    nf, nb = record['Nf'], record['Nb']
    def interpolate(ctrl, count, index):
        pos = F(index*(count-1), K)
        left = floor(pos)
        if left == count-1:
            return ctrl[-1]
        return ctrl[left]*(left+1-pos)+ctrl[left+1]*(pos-left)
    fctrl = [clip_f(v) for v in vals[1:1+nf]]
    bctrl = vals[1+nf:]
    return vals[0], [interpolate(fctrl, nf, i) for i in range(K)], [interpolate(bctrl, nb, i+1) for i in range(K-1)]


def polygons(record):
    K, eps = record['K'], number(record['eps'])
    if type(K) is not int or K < 1 or not F(0) < eps <= 1:
        raise ValueError('invalid K/eps')
    y0, f, beta = full_parameters(record)
    u = trig_grid(K)
    gamma = [beta[i]+(f[i+1]-f[i])/2 for i in range(K-1)]
    # Exact algebraic closure: x(P0)=-sum(gamma_j*cos(theta_{j+1}));
    # u(theta_K).x=0, so final center.x=0 without numerical tolerance.
    x0 = (0, 0)
    for i, g in enumerate(gamma):
        x0 = add(x0, neg(mul(u[i+1][0], g)))
    p = (x0, outward(y0, y0))
    pl, ph = pi_interval()
    sagitta = ceil((1+eps/2)*ph*ph*D/F(32*K*K))
    for i in range(K):
        start = rect(p, u[i], f[i], eps)
        end = rect(p, u[i+1], f[i], eps)
        # Rotation of each corner: linear endpoint interpolation has
        # Euclidean interpolation error <= radius*delta^2/8. The radius
        # is <=1+eps/2, so the enclosing L-infinity square suffices.
        yield hull(box_points(start+end, sagitta))
        if i+1 < K:
            displacement = (mul(u[i+1][0], beta[i]), mul(u[i+1][1], beta[i]))
            p_next = (add(p[0], mul(u[i+1][0], gamma[i])),
                      add(p[1], mul(u[i+1][1], gamma[i])))
            # Slide from the old pivot-relative pose to translated pose.
            slid = [((add(x, displacement[0])), (add(y, displacement[1]))) for x, y in end]
            yield hull(box_points(end+slid))
            p = p_next


def cell_intervals(poly, q):
    """All *closed* cells touched by convex polygon, row by row."""
    ys = [y for _, y in poly]
    for row in range(ceil(F(min(ys)*q, D))-1, floor(F(max(ys)*q, D))+1):
        bottom, top = F(row*D, q), F((row+1)*D, q)
        xs = []
        for a, b in zip(poly, poly[1:]+poly[:1]):
            if bottom <= a[1] <= top:
                xs.append(F(a[0]))
            if a[1] != b[1]:
                for y in (bottom, top):
                    if min(a[1], b[1]) <= y <= max(a[1], b[1]):
                        xs.append(F(a[0]) + F(b[0]-a[0], b[1]-a[1])*(y-a[1]))
        if xs:
            yield row, (ceil(min(xs)*q/D)-1, floor(max(xs)*q/D))


def count_cells(polys, q):
    if type(q) is not int or q < 1:
        raise ValueError('q must be positive integer')
    rows = {}
    for poly in polys:
        for reflected in (poly, [(-x, y) for x, y in poly]):
            for row, interval in cell_intervals(reflected, q):
                rows.setdefault(row, []).append(interval)
    n = 0
    for intervals in rows.values():
        end = None
        for lo, hi in sorted(intervals):
            if end is None or lo > end+1:
                n += hi-lo+1
                end = hi
            elif hi > end:
                n += hi-end
                end = hi
    return n


def unique_object(pairs):
    """Reject ambiguous JSON objects before interpreting motion or certificate."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field: ' + key)
        result[key] = value
    return result


def source_record(path, seed):
    if type(seed) is not int:
        raise ValueError('seed must be an integer')
    data = Path(path).read_bytes()
    records = json.loads(data, parse_float=F, parse_int=int,
                         object_pairs_hook=unique_object)
    if not isinstance(records, list):
        raise ValueError('expected list of records')
    matches = [r for r in records if type(r['seed']) is int and r['seed'] == seed]
    if len(matches) != 1:
        raise ValueError('seed must match exactly once')
    return hashlib.sha256(data).hexdigest(), matches[0]


def certificate(path, seed, q):
    sha, record = source_record(path, seed)
    n = count_cells(polygons(record), q)
    return {'method': 'rational-pivot-grid-v1', 'input_sha256': sha,
            'source': str(path), 'seed': seed, 'eps': str(record['eps']),
            'K': record['K'], 'q': q, 'N': n, 'upper': str(F(n, q*q))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--q', type=int, default=128)
    parser.add_argument('--verify', help='recompute and compare a certificate JSON')
    args = parser.parse_args()
    result = certificate(args.source, args.seed, args.q)
    if args.verify:
        stored = json.loads(Path(args.verify).read_text(),
                            object_pairs_hook=unique_object)
        if (stored != result or set(stored) != set(result)
                or any(type(stored[key]) is not type(result[key]) for key in result)):
            raise SystemExit('certificate mismatch')
        print('verified N=%d, upper=%s' % (result['N'], result['upper']))
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
