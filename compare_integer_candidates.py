"""Checkpointed, non-certified common-backend re-evaluation of saved motions.

This compares already discovered candidate constructions, not equal-budget
optimization. Float pose/roundoff errors remain uncertified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import integer_motion_area as geometry
from motion_adapters import evaluate_saved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', action='append', required=True,
                        help='source.json:zero-based-record-index')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--max-wall-s', type=float, default=90)
    parser.add_argument('--quality-tolerance', type=float, default=.005)
    args = parser.parse_args()
    if args.out.exists() or not 0 < args.quality_tolerance < 1:
        parser.error('output must be new and quality tolerance in (0,1)')
    rows = []
    for label in args.candidate:
        source_text, separator, index_text = label.rpartition(':')
        if not separator or not index_text.isdecimal():
            parser.error(f'bad candidate {label}; expected source.json:index')
        source, index = Path(source_text), int(index_text)
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        checks = []
        for scale in (1 << 38, 1 << 40):
            geometry.SCALE = scale
            for fraction in (.0001, .00005):
                result = evaluate_saved(source, index, max_wall_s=args.max_wall_s,
                                        step_fraction=fraction)
                checks.append(result)
        scores = [item['numeric_outer_area'] for item in checks if item['status'] == 'ok']
        relative_spread = ((max(scores)-min(scores))/max(scores)
                           if len(scores) == 4 else None)
        status = ('ok' if len(scores) == 4 and relative_spread <= args.quality_tolerance
                  else 'quality_limited')
        row = {'source': str(source), 'source_sha256': source_hash,
               'source_record_index': index, 'status': status,
               'relative_spread': relative_spread,
               'quality_tolerance': args.quality_tolerance,
               'checks': checks,
               'limitation': 'numeric integer polygon outer approximations of floating motions; not strict certificates or equal-budget searches'}
        if status == 'ok':
            row['numeric_range'] = [min(scores), max(scores)]
        rows.append(row)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=2) + '\n')
        print(f'{label}: {status} range={row.get("numeric_range")} '
              f'spread={relative_spread}', flush=True)


if __name__ == '__main__':
    main()
