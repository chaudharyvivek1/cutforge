# Conformance tests

The specification asserts behaviour: a conform map that is monotone and total, a speed that lands on a sample, a handle measured in the right domain, a beat grid that scales, a duration ladder with no gap. Until these tests existed, all of that was checked by re-deriving the numbers in `build/check_figures.py` — which proves the arithmetic, not the behaviour.

`spec_rules.py` is a reference implementation of the deterministic parts, named after the sections that specify them. It is deliberately not the engine: it is the smallest code that can be wrong in the same way the document can be.

`vfr_fixture.py` generates the variable-rate fixture §5.9.4 asks for — a nominal-30 fps stream with dropped frames and small jitter, plus a reordered delivery of the same packets. Generated rather than captured, so CI gets the same bytes every run.

```bash
cd tests && python -m unittest discover -s . -v
```

Every test names its section. A failure means the document and the code disagree, and the test does not decide which is right — that is a review decision, and it is recorded in the version's §0 table.

| Test class | Proves |
|---|---|
| `TestTimeModel` | §5.1 rounding, §5.5 samples, §5.6 versus §5.9.3 |
| `TestConformMap` | §5.9 monotonicity, totality, invertibility; Appendix A's five clips |
| `TestVFR` | §5.9.4 the worked excerpt, reordering, shared timestamps |
| `TestSpeed` | §5.11 exact ratios, non-integral counts, cascade range, precision |
| `TestTransitions` | §5.7 picture handles by speed, audio handles rounded once |
| `TestAnnotations` | §5.10 endpoints and beat scaling |
| `TestDurationLadder` | §7.7 the four bands |
| `TestErasureAndCost` | §16.6.1 jurisdictional deadlines, §20.3 tiered egress |
