# Public candidate interface — v004

Deliver `candidate_004.py` as pure Python 3 stdlib plus your own documented modules. Core calls:

```python
plan_repair(case: dict) -> dict
plan_power(observation: dict, state: dict) -> dict
plan_telemetry(case: dict) -> dict
```

Repair case fields: `old_words` and `new_words` (list of synthetic uint16), `cap_bits_per_pass` (int), `scratch_words` (int), `max_passes` (int), `safety` (dict of booleans and numerical power and thermal margins), `fault` (string). Return `status` ('HOLD' or 'STAGED'), `packet_hex` (hex text), `pass_bits` (list of actual consumed bits per pass), and `rtt` (int). The referee performs its OWN patch decode and readback; it does not trust an asserted 'recovered'. No actual flight memory address or code. Valid codecs for this interface: the public v003 full/sparse/run packet format; codec expansion requires independently documented decoder and no free onboard compute or memory.

Power observation: `month`, `nominal_margin_w`, `previous_shock_w`, `previous_thermal_w`, `enabled` list (only MAG/PWS), `remaining_margin_unknown` (always true for real flight). State carries only previously returned state, not future shocks. Return `mode` as a subset of currently enabled instruments, `next_state`, and `status` ('HOLD' or 'SCHEDULE'). Cannot restart a removed instrument. We do not know live heater, instrument or thermal margins; all measurements are synthetic.

Telemetry case: `packets` list of dicts `{id,size_bits,value,group,deadline}` and `available_bits` total (synthetic). Return `selected_ids`, `status` ('HOLD' or 'SCHEDULE'). Referee checks unique valid ids and the actual sum of sizes/values. The 'value' is a synthetic proxy and does not imply a flight instrument can reorder real data.

**Separately include** a general real-spacecraft feasibility manifest for each candidate: onboard binary if genuine (otherwise `NONE`), location, assumed memory footprint, missing private sources, power and time accounting, commands/uplink and rollback. If not known, explicitly HOLD.

Public smoke tests are not an independent holdout. Referee may vary the number of words, fragmented scratch, corruption, stale epochs, missing acknowledgements, DSN pass caps, lost telemetry, thermal shocks, and instrument availability. Fail closed. Candidate may return HOLD rather than invent a flight update.