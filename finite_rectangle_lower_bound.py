"""Universal rational lower bound using maximal finite-rectangle overlaps.

The proved corollary is f(eps) >= pi / (2*log(1/eps)+3), for 0<eps<=1.
Only exact rational arithmetic is used, with outward quantization at the end.
See docs/finite-rectangle-overlap.md for geometry and proof.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
import json
from rational_pivot_certificate import D, ceil, floor, pi_interval


def log_unit_interval(x: F, terms: int = 32) -> tuple[F, F]:
    """Enclose log(x), 1<=x<=2, using its positive atanh series."""
    if type(x) not in (int, F) or not 1 <= x <= 2:
        raise ValueError('x must be rational and in [1,2]')
    if type(terms) is not int or terms < 1:
        raise ValueError('terms must be a positive integer')
    x = F(x)
    z = (x-1)/(x+1)
    z2, power, lower = z*z, z, F(0)
    for k in range(terms):
        lower += 2*power/(2*k+1)
        power *= z2
    # power=z^(2*terms+1); all remaining denominators >=2*terms+1.
    upper = lower + 2*power/((2*terms+1)*(1-z2))
    return lower, upper


def log_interval(x: F, terms: int = 32) -> tuple[F, F]:
    """Range reduction x=2^shift*y, 1<=y<2, for rational x>=1."""
    if type(x) not in (int, F) or x < 1:
        raise ValueError('x must be a rational number >=1')
    x = F(x)
    shift = max(0, x.numerator.bit_length()-x.denominator.bit_length())
    y = x/F(1 << shift)
    if y < 1:
        shift -= 1
        y *= 2
    if y >= 2:
        shift += 1
        y /= 2
    lo2, hi2 = log_unit_interval(F(2), terms)
    loy, hiy = log_unit_interval(y, terms)
    return shift*lo2+loy, shift*hi2+hiy


def lower_bound(eps: F, terms: int = 32) -> dict:
    if type(eps) not in (int, F) or not 0 < eps <= 1:
        raise ValueError('eps must be rational and in (0,1]')
    eps = F(eps)
    _, log_hi = log_interval(1/eps, terms)
    pi_lo, _ = pi_interval()
    # pi numerator rounded down, denominator rounded up: conservative lower bound.
    pn, ln = floor(pi_lo*D), ceil(log_hi*D)
    return {'method': 'finite-rectangle-overlap-simple-rational-v1',
            'eps': str(eps), 'log_terms': terms, 'rounding_denominator': D,
            'pi_lower_numerator': pn, 'log_upper_numerator': ln,
            'lower': str(F(pn, 2*ln+3*D))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--eps', default='0.005')
    parser.add_argument('--terms', type=int, default=32)
    args = parser.parse_args()
    print(json.dumps(lower_bound(F(args.eps), args.terms), indent=2))


if __name__ == '__main__':
    main()
