# Voyager 004 — Ground-side software experiment

Voyager 1 is almost 50 years old. What might modern *ground-side* software do to help a mission with fading electrical power, damaged memory and a roughly two-day command/confirmation cycle?

This repository snapshot contains three **runnable Python surrogate prototypes**, not Voyager flight code:

- `plan_repair`: generates smaller checksum-gated synthetic memory repair packets. A concrete test case is 93 bytes versus 119 bytes with the included conventional reference implementation.
- `plan_power`: explores irreversible instrument shedding without restarting a disabled instrument. Modeled watts and shock distributions are **assumptions**, not current NASA telemetry.
- `plan_telemetry`: chooses which fictional MAG/PWS science packets fit inside a constrained return-link budget.

## Try it

Requires Python 3; no network or paid API:

```sh
python3 public_smoke.py
python3 integration/replay_sample_004.py
```

The complete frozen Argon-004 research package has additional development evaluations and depends on the original Voyager-003 baseline. These tests are not a blinded or independent demonstration of improvement. In follow-on review, standard exact optimization matched the candidate repair packing and telemetry scheduling on additional synthetic tests, and the physical-power model has not shown a safe real-world mission-life extension.

## Critical boundaries

These files do not communicate with Voyager, do not contain NASA-compatible command formats, do not know Voyager's 2026 surviving memory layout, and cannot be used for spacecraft commanding. **NASA/JPL authorization, actual flight mapping and hardware-in-loop testing would be required before any operational proposal.** The experiments support possible directions for research, not claims that additional science has been recovered or additional mission years gained.

The private sealed referee and withheld cases are deliberately not here.

This snapshot preserves the contestant implementation for public inspection, including limitations and conventional comparator, without claiming novelty or NASA endorsement.