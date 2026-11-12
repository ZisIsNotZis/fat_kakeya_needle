"""Read-only independent range reduction and log enclosure checks (stdlib)."""
from fractions import Fraction as F
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finite_rectangle_lower_bound import D, log_interval, lower_bound


def explicit_series(x, terms=48):
    z = (x-1)/(x+1)
    lo = 2*sum((z**(2*k+1)/F(2*k+1) for k in range(terms)), F(0))
    hi = lo + 2*z**(2*terms+1)/((2*terms+1)*(1-z*z))
    return lo, hi


def independent_interval(x):
    # Different implementation from the tested bit-length reduction.
    y, shift = x, 0
    while y >= 2:
        y /= 2
        shift += 1
    lo2, hi2 = explicit_series(F(2))
    loy, hiy = explicit_series(y)
    return shift*lo2+loy, shift*hi2+hiy


if __name__ == '__main__':
    rng = random.Random(20261112)
    xs = [F(1), F(200), F(10**100)]
    xs += [F(rng.randrange(1000000, 2000000), rng.randrange(1, 1000000)) for _ in range(30)]
    for k in (0, 1, 5, 30, 100):
        for offset in (-F(1, 10**6), F(0), F(1, 10**6)):
            x = F(2)**k+offset
            if x >= 1:
                xs.append(x)
    for x in xs:
        lo, hi = log_interval(x)
        fine_lo, fine_hi = independent_interval(x)
        assert lo <= fine_lo <= fine_hi <= hi, x
    result = lower_bound(F(1, 200))
    _, fine_hi = independent_interval(F(200))
    integer_ceiling = -((-fine_hi.numerator*D)//fine_hi.denominator)
    assert integer_ceiling == result['log_upper_numerator'] == 5298317366549
    assert result['lower'] == '3141592653589/13596634733098'
    print('independent log enclosure nested comparisons:', len(xs))
    print(result)
