# OpenLine — Invention Prototypes: Continuity Input Bridge and Self-Healing Servo Controller

**Terrynce Anson White — Independent Researcher, OpenLine**

Two independently runnable **dry-run control-logic prototypes**, not assembled
devices. Both use Python 3.10+ standard library only and never perform USB or
servo I/O. No physical devices were assembled, no user studies were conducted,
and no real USB HID or servo actuation was demonstrated.

- Paper A: `papers/PAPER_A_CONTINUITY_INPUT_BRIDGE.pdf` — a fault-aware,
  user-controlled input bridge for accessible computer interaction.
  Computational engineering technical report.
- Paper C: `papers/PAPER_C_SELF_HEALING_SERVO.pdf` — a conservative
  dual-route, fault-isolation state machine for modular servo systems.
  Computational engineering technical report.
- Supporting note: `papers/NEGATIVE_D_PASSIVE_TREMOR_ABSORBER.pdf` — a
  negative feasibility result for a passive handheld tuned-mass concept.
  Kept as a supporting technical note, not a third invention claim.

## Licenses

Manuscripts: CC BY 4.0. Original executable code: Apache License 2.0
(see `LICENSE`). Third-party prior art is cited in the papers; no
third-party material is redistributed here.

## Run

```bash
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 run_portfolio.py
python3 demo.py
```

Expected: 27/27 unit tests pass in normal and optimized Python;
1,000/1,000 defined input safety invariants and 1,000/1,000 defined servo
route safety invariants on deterministic constructed cases (fixed seed
20261117). Outputs: `results/constructed_scenario_receipt.json`. The
scenario generator is fixed-seed and synthetic. All files are listed in
`SHA256SUMS.txt`.

## What the numbers are — and are not

The 1,000-case figures are constructed checks of software invariants, not
real-world reliability statistics. The tremor model is an uncalibrated
illustrative oscillator: it improves 6 of 37 frequency bins and worsens 31.
Head tracking, sip-and-puff input, and robot bus redundancy are established
prior art, cited in the papers; this package claims no invention of them.
Its candidate contributions are the two explicit failover/authority
protocols and their executable tests.

## Citation

Cite the Zenodo records for each paper (DOIs in the paper headers and in
`CITATION.md` once issued). The repository is the public source for the
reproducible bundle attached to those records.
