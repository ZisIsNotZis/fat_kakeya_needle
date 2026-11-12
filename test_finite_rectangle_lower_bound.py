"""Checks for exact log enclosures and finite-rectangle lower certificates."""
from fractions import Fraction as F
import unittest

from finite_rectangle_lower_bound import D, log_interval, log_unit_interval, lower_bound


class FiniteRectangleLowerTests(unittest.TestCase):
    def test_log_one_exact(self):
        self.assertEqual(log_interval(F(1)), (F(0), F(0)))
        self.assertEqual(log_unit_interval(F(1), 1), (F(0), F(0)))

    def test_log_two_decimal_bracket(self):
        lo, hi = log_unit_interval(F(2))
        self.assertLess(F(69314718055994530941, 10**20), lo)
        self.assertLess(hi, F(69314718055994530942, 10**20))

    def test_range_reduction_and_nested_intervals(self):
        for x in (F(1), F(2), F(3), F(200), F(5, 4), F(10**100)):
            lo, hi = log_interval(x, 12)
            finer_lo, finer_hi = log_interval(x, 24)
            self.assertLessEqual(lo, finer_lo)
            self.assertLessEqual(finer_lo, finer_hi)
            self.assertLessEqual(finer_hi, hi)
        lo2, hi2 = log_interval(F(2))
        lo8, hi8 = log_interval(F(8))
        self.assertEqual((lo8, hi8), (3*lo2, 3*hi2))
        # Independent rational decimal bracket for log(200).
        lo, hi = log_interval(F(200))
        self.assertLess(F(52983173665480366774, 10**19), lo)
        self.assertLess(hi, F(52983173665480366775, 10**19))

    def test_certificate_outward_rounding(self):
        for eps in (F(1), F(1, 2), F(1, 200)):
            result = lower_bound(eps)
            lo, hi = log_interval(1/eps)
            self.assertGreaterEqual(F(result['log_upper_numerator'], D), hi)
            self.assertEqual(F(result['lower']),
                             F(result['pi_lower_numerator'], 2*result['log_upper_numerator']+3*D))
        self.assertGreater(F(lower_bound(F(1, 200))['lower']), F(23, 100))
        self.assertEqual(F(lower_bound(F(1))['lower']), F(3141592653589, 3*D))

    def test_invalid_parameters(self):
        for eps in (True, '0.1', 0.1, F(0), F(-1), F(2)):
            with self.subTest(eps=eps), self.assertRaises(ValueError):
                lower_bound(eps)
        for terms in (True, 0, -1, F(2), 2.0):
            with self.subTest(terms=terms), self.assertRaises(ValueError):
                lower_bound(F(1, 200), terms)
        for x in (True, 1.5, '2', F(1, 2), F(3)):
            with self.subTest(x=x), self.assertRaises(ValueError):
                log_unit_interval(x)


if __name__ == '__main__':
    unittest.main()
