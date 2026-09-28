"""Regression tests for non-certified finite-motion area diagnostics."""
import unittest

from probe_keich_demo import probe


class KeichProbeTests(unittest.TestCase):
    def test_small_finite_motions_have_ordered_numerical_areas(self):
        for n in (1, 2):
            row = probe(n, 128)
            self.assertEqual(row['status'], 'ok')
            self.assertEqual(row['K_stations'], 4 * (1 << n) + 1)
            self.assertGreater(row['sampled_area'], 0)
            self.assertGreaterEqual(row['numerical_outer_area'] + 1e-8,
                                    row['sampled_area'])
            self.assertIn('not a rigorous', row['limitation'])


if __name__ == '__main__':
    unittest.main()
