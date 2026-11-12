"""Universal exact-rational area lower bound from uniformly spaced directions.

No candidate motion or optimizer is used. The proof uses Cauchy-Schwarz and
intersection bounds for rectangles, then rigorous lower sine enclosures.
See docs/finite-eps-lower-bound.md. Standard library only.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
import json
from rational_pivot_certificate import D, ceil, trig_grid


def lower_bound(eps: F, n: int = 1024) -> dict:
    if type(eps) not in (int, F) or not 0 < eps <= 1:
        raise ValueError('eps must be a rational number in (0,1]')
    eps = F(eps)
    if type(n) is not int or n < 2 or n % 2:
        raise ValueError('n must be a positive even integer >=2')
    u = trig_grid(n//2)

    def cap(k):
        # min(1, eps/sin(k*pi/n)) <= cap(k)/D, rounded upward.
        sine_low = u[k][1][0]
        if sine_low <= 0:
            return D
        return min(D, ceil(eps*D*D/sine_low))

    # sin(k*pi/n) = sin((n-k)*pi/n); no duplicate endpoint direction.
    sum_caps = 2*sum(cap(k) for k in range(1, n//2)) + cap(n//2)
    lower = F(n)*eps*D/(D+sum_caps)
    return {'method': 'uniform-direction-overlap-rational-v1',
            'eps': str(eps), 'directions': n, 'rounding_denominator': D,
            'sum_cap_numerator': sum_caps, 'lower': str(lower)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--eps', default='0.005')
    parser.add_argument('--directions', type=int, default=1024)
    args = parser.parse_args()
    print(json.dumps(lower_bound(F(args.eps), args.directions), indent=2))


if __name__ == '__main__':
    main()
