# Contributing

Thanks for looking. This is a research repository first: the most valuable contribution is a reproducible result, a sharper certificate, or a clear negative result — not a larger diff.

## Before you start

Open an issue for a new motion family, a changed evaluator, or a new benchmark protocol. Small documentation fixes and test-only changes can go straight to a pull request.

## Local workflow

Use Python 3.12 with `numpy`, `scipy`, `shapely`, and `matplotlib`; the optional integer evaluator also needs `pyclipper==1.4.0`. See [`WORKSPACE.md`](WORKSPACE.md) for the recorded environment and known pitfalls.

Run the core regression set before sending a change:

```bash
python3 -m unittest -v test_pivot_enclosure test_v2_numerical_enclosure \
  test_rational_pivot_certificate test_keich_motion
```

When you touch the integer backend or the motion adapters, also run:

```bash
python3 -m unittest -v test_integer_motion_area test_motion_adapters \
  test_compare_integer_candidates
```

There is no hosted CI. Results from a local run belong in the pull request description, not as a replacement for the tests.

## Evidence rules

Every numerical claim needs its evidence layer stated: sampled estimate, numerical enclosure, or strict bound.

- A centered half-turn must reproduce `π/4` before a new evaluator or family is trusted.
- Comparisons need fixed resolution, at least three fresh seeds, and a measured CPU budget.
- Do not promote a floating-point value to an upper bound. Use the rational certificate path when a proof is claimed.
- Keep negative and superseded results in `results/`; explain the supersession in the relevant `docs/` note.
- Put new findings in the document that owns the question, and update the affected README/roadmap text in the same change.

## Style

Match the surrounding code and documentation. Keep modules focused, use the standard library where the proof path allows it, and avoid new dependencies unless they are necessary and their license is recorded.

## Commits

Use Conventional Commits, for example:

```text
feat: add a new motion adapter
fix: correct mirror-axis closure in v2 scoring
docs: record a negative seed-initialization result
```

Keep commits small and logical. Do not commit lockfiles, generated logs, or unfinished run artifacts.

## License

By contributing, you agree that your contribution is licensed under AGPL-3.0-only, the license in [`LICENSE`](LICENSE).
