"""Regression and analytic boundary checks for universal rational lower bound."""
from fractions import Fraction as F
import unittest

from direction_overlap_lower_bound import lower_bound


class DirectionOverlapTests(unittest.TestCase):
    def test_two_directions_exact(self):
        for eps in (F(1), F(1, 2), F(1, 200)):
            result = lower_bound(eps, 2)
            self.assertEqual(F(result['lower']), 2*eps/(1+eps))

    def test_square_is_at_least_its_own_area(self):
        for n in (2, 4, 8, 16):
            self.assertEqual(F(lower_bound(F(1), n)['lower']), 1)

    def test_four_directions_analytic_bracket(self):
        # sin(pi/4)=1/sqrt(2). Use 1.41421356237 < sqrt(2) < 1.41421356238.
        eps = F(1, 200)
        lower = F(lower_bound(eps, 4)['lower'])
        exact_lo = 4*eps/(1+eps+2*eps*F(141421356238, 10**11))
        exact_hi = 4*eps/(1+eps+2*eps*F(141421356237, 10**11))
        self.assertLessEqual(lower, exact_hi)
        self.assertGreater(lower, exact_lo-F(1, 10**11))

    def test_invalid_parameters(self):
        for eps in (True, 0.1, '0.1', F(0), F(-1), F(2)):
            with self.subTest(eps=eps), self.assertRaises(ValueError):
                lower_bound(eps, 2)
        for n in (True, 1, 3, 0, -2, F(2), 2.0):
            with self.subTest(n=n), self.assertRaises(ValueError):
                lower_bound(F(1, 200), n)


if __name__ == '__main__':
    unittest.main()
