"""Ranking gate tests: unstable/missing numerical checks cannot be ranked."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import compare_integer_candidates as benchmark


class CandidateComparisonTests(unittest.TestCase):
    def test_spread_and_failure_remove_ranked_area(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'candidate.json'
            source.write_text('[{"seed":0}]')
            target = Path(directory) / 'comparison.json'
            argv = ['compare_integer_candidates.py', '--candidate', f'{source}:0',
                    '--out', str(target)]
            with patch('sys.argv', argv), patch.object(benchmark, 'evaluate_saved',
                    side_effect=[{'status': 'ok', 'numeric_outer_area': 1.0},
                                 {'status': 'ok', 'numeric_outer_area': 1.01},
                                 {'status': 'ok', 'numeric_outer_area': 1.0},
                                 {'status': 'ok', 'numeric_outer_area': 1.0}]):
                benchmark.main()
            row = json.loads(target.read_text())[0]
            self.assertEqual(row['status'], 'quality_limited')
            self.assertNotIn('numeric_range', row)
            self.assertEqual(len(row['checks']), 4)
            target.unlink()
            with patch('sys.argv', argv), patch.object(benchmark, 'evaluate_saved',
                    side_effect=[{'status': 'ok', 'numeric_outer_area': 1.0},
                                 {'status': 'error', 'error': 'bad geometry'},
                                 {'status': 'ok', 'numeric_outer_area': 1.0},
                                 {'status': 'ok', 'numeric_outer_area': 1.0}]):
                benchmark.main()
            row = json.loads(target.read_text())[0]
            self.assertEqual(row['status'], 'quality_limited')
            self.assertNotIn('numeric_range', row)

    def test_agreeing_checks_produce_range_not_certificate(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'candidate.json'
            source.write_text('[{"seed":0}]')
            target = Path(directory) / 'comparison.json'
            argv = ['compare_integer_candidates.py', '--candidate', f'{source}:0',
                    '--out', str(target)]
            with patch('sys.argv', argv), patch.object(benchmark, 'evaluate_saved',
                    side_effect=[{'status': 'ok', 'numeric_outer_area': 1.0},
                                 {'status': 'ok', 'numeric_outer_area': 1.001},
                                 {'status': 'ok', 'numeric_outer_area': 1.0001},
                                 {'status': 'ok', 'numeric_outer_area': 1.0005}]):
                benchmark.main()
            row = json.loads(target.read_text())[0]
            self.assertEqual(row['status'], 'ok')
            self.assertEqual(row['numeric_range'], [1.0, 1.001])
            self.assertIn('not strict', row['limitation'])


if __name__ == '__main__':
    unittest.main()
