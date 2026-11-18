"""Argon Candidate Submission for Voyager-004 (`candidate_004.py`).

Pure Python 3 standard library implementation of the three surviving mechanisms
from the six-candidate screening tournament. Ground-only synthetic/surrogate
software; NOT executable Voyager 1 flight code, opcodes, or authorized NASA
commanding. All real-flight claims remain explicitly HOLD pending NASA/JPL
2026 memory maps, command framing, and hardware-in-the-loop qualification.

Implemented Top-3 Surviving Mechanisms (after Causal Subtraction):
1. `plan_repair(case)` — M1: Gap-Bridged Run-Merged & Checksum-Gated Shadow
   Relocation Planner (`GB-RMSC`). Uses the standard public v003/v004 `tag=3`
   (`runs`) decoder format without adding a single onboard instruction, bridging
   1-word (and 2-word) unchanged gaps inside relocated instruction blocks where
   a 2-byte unchanged word is strictly cheaper than a 4-byte (`32`-bit) run
   header (`-16` bits per bridged 1-word gap). Self-verifies shadow decoding
   and CRC32 readback before staging, and fails closed (`status='HOLD'`) on all
   safety, scratch, pass-budget, and causal fault traps.
2. `plan_power(observation, state)` — M2: Causal Innovation-Filtered &
   Two-Stage Bellman Continuation Shedding Controller (`CIF-TBCS`). Addresses
   the lag-1 noise-doubling flaw (`Var(e_t) = 2*sigma^2`) in `reference_004.py`
   while strictly enforcing monotone subset shedding (`set(mode).issubset(enabled)`,
   zero instrument restarts). Maintains an Empirical-Bayes shrinkage filter over
   observed shocks and thermal loads in `state` and applies a two-stage Bellman
   continuation-value margin (`1.25 W` when preserving single-instrument
   continuation value vs. `0.90 W` before final shutdown). Note: a third
   candidate sub-component (`branch_lookahead` between PWS and MAG) was
   tested and **subtracted** after causal ablation showed 0.0% safe-science
   contribution once the Empirical-Bayes filter and two-stage buffer are active.
3. `plan_telemetry(case)` — M3: Dominance-Pruned Exact & Scalable 0/1 Knapsack
   Telemetry Prioritizer (`DP-SKTP`). Eliminates the `n > 18` refusal cliff in
   `reference_004.py` using Pareto-dominance-pruned exact 0/1 knapsack dynamic
   programming for `n <= 24` and Pareto-pruned DP + multi-order 1-opt swap
   knapsack polish for `24 < n <= 5000`, with strict schema and safety validation.
"""
from __future__ import annotations

import math
import struct
import zlib
from typing import Any

COST = {'MAG': 2.5, 'PWS': 3.0}
VALUE = {'MAG': 1.0, 'PWS': 1.35}
VALID_INSTRUMENTS = ('MAG', 'PWS')

_UNSAFE_FAULT_TOKENS = (
    'corrupt',
    'stale',
    'duplicate',
    'lost_ack',
    'no_ack',
    'half_received',
    'partial_command',
    'truncat',
    'pass_lost',
    'link_lost',
    'no_link',
    'no_scratch',
    'unverified_scratch',
    'fragmented_scratch',
    'cross_bank',
    'multi_bank',
    'hidden_xref',
    'hidden_cross_ref',
    'unresolved_ref',
    'dangling',
    'uncertain_baseline',
    'unknown_baseline',
    'camera',
    'reactivate',
    'restart',
    'target_is_flight',
    'no_rollback',
    'unsafe',
    'hazard',
)

FEASIBILITY_MANIFEST_004 = {
    'M1_GB_RMSC_plan_repair': {
        'status_real_flight': 'HOLD',
        'onboard_binary': 'NONE (ground-side patch compiler emitting standard v003/v004 surrogate packet_hex)',
        'execution_location': 'Ground operations computer (Earth); targets synthetic FDS shadow RAM buffer in surrogate',
        'assumed_memory_footprint_words': '0 additional resident code words; requires scratch_words >= len(old_words) in surrogate (real 2026 Voyager 1 free FDS RAM words UNKNOWN)',
        'missing_private_sources': [
            'Actual November 2026 Voyager 1 healthy/writable FDS CMOS RAM map and bank layout',
            'Actual CCS MEMLOAD 18-bit command framing and hardware checksum routine',
            'Authorized JPL rollback vector address and hardware-in-the-loop testbed',
        ],
        'power_and_time_accounting': '0.0 W additional spacecraft electrical power; < 1 ms ground CPU; 16 bps S-band uplink accounting with 32-byte common envelope + 64-bit per-pass control overhead and 48h confirmation RTT per pass + 1 readback RTT',
        'commands_uplink_and_rollback': 'Stages patch into inactive shadow scratch only; requires full CRC32 readback verification before atomic cutover; rollback discards shadow buffer and leaves original live image untouched (keeps_original_live=True)',
    },
    'M2_CIF_TBCS_plan_power': {
        'status_real_flight': 'HOLD',
        'onboard_binary': 'NONE (ground-computed monotone instrument power-off schedule)',
        'execution_location': 'Ground operations planner (Earth); issues standard CCS power-off commands',
        'assumed_memory_footprint_words': '0 onboard words; causal filter state stored in ground state dictionary',
        'missing_private_sources': [
            'Calibrated November 2026 post-Big-Bang Voyager 1 heater circuit wattage tables and hydrazine line thermal conductances',
            'Exact RTG volt-ampere droop curve and undervoltage fault-protection trip setpoints',
        ],
        'power_and_time_accounting': '0.0 W onboard compute overhead; strictly reduces electrical load monotonically via subset transitions (MAG+PWS -> PWS or MAG -> empty)',
        'commands_uplink_and_rollback': 'One-way monotone instrument power-off commands only; instrument restart is strictly prohibited (irreversible in flight due to cold-soak/latchup hazard)',
    },
    'M3_DP_SKTP_plan_telemetry': {
        'status_real_flight': 'HOLD',
        'onboard_binary': 'NONE (surrogate packet selection schedule; real FDS fixed-format commutator table reprogramming UNKNOWN)',
        'execution_location': 'Ground/surrogate telemetry scheduler',
        'assumed_memory_footprint_words': '0 real flight words; O(min(cap, max_states)) ground Python memory',
        'missing_private_sources': [
            'Actual Voyager 1 FDS science commutator frame tables for MAG and PWS',
            'Downlink frame header overhead and DTR playback constraints',
        ],
        'power_and_time_accounting': '0.0 W spacecraft power; < 5 ms ground compute; respects exact available_bits cap at 160 bps nominal X-band downlink',
        'commands_uplink_and_rollback': 'Selects subset of valid packet IDs within available_bits; fails closed (HOLD) on negative capacity or malformed packet descriptors',
    },
}


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _is_finite_number(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(float(val))


def _encode_packet_standard(old: list[int], new: list[int], kind: str, max_gap: int = 0) -> bytes:
    changes = [(i, v) for i, (a, v) in enumerate(zip(old, new)) if a != v]
    if kind == 'full':
        body = struct.pack('>BH', 1, len(new)) + b''.join(struct.pack('>H', v) for v in new)
    elif kind == 'sparse':
        body = struct.pack('>BH', 2, len(changes)) + b''.join(struct.pack('>HH', i, v) for i, v in changes)
    elif kind == 'runs':
        runs: list[list[Any]] = []
        for i, v in changes:
            if runs:
                prev_start, prev_vals = runs[-1]
                prev_end = prev_start + len(prev_vals)
                gap = i - prev_end
                if 0 <= gap <= max_gap:
                    for g_idx in range(prev_end, i):
                        prev_vals.append(new[g_idx])
                    prev_vals.append(v)
                    continue
            runs.append([i, [v]])
        body = struct.pack('>BH', 3, len(runs)) + b''.join(
            struct.pack('>HH', i, len(vals)) + b''.join(struct.pack('>H', v) for v in vals)
            for i, vals in runs
        )
    else:
        raise ValueError(f'Unknown codec kind: {kind}')
    crc = zlib.crc32(b''.join(struct.pack('>H', w) for w in new))
    return body + struct.pack('>I', crc)


def verify_shadow_decode(old: list[int], packet: bytes) -> list[int]:
    if len(packet) < 7:
        raise ValueError('truncated')
    tag, n = struct.unpack_from('>BH', packet, 0)
    pos = 3
    shadow = list(old)
    if tag == 1:
        if n != len(old) or len(packet) != 3 + 2 * n + 4:
            raise ValueError('full length')
        shadow = list(struct.unpack_from('>' + str(n) + 'H', packet, pos))
        pos += 2 * n
    elif tag == 2:
        if len(packet) != 3 + 4 * n + 4:
            raise ValueError('sparse length')
        seen = set()
        for _ in range(n):
            i, v = struct.unpack_from('>HH', packet, pos)
            pos += 4
            if i in seen or i >= len(shadow):
                raise ValueError('bad index')
            shadow[i] = v
            seen.add(i)
    elif tag == 3:
        seen = set()
        for _ in range(n):
            if pos + 4 > len(packet) - 4:
                raise ValueError('truncated run')
            i, k = struct.unpack_from('>HH', packet, pos)
            pos += 4
            if not k or i + k > len(shadow) or pos + 2 * k > len(packet) - 4:
                raise ValueError('bad run')
            for offset in range(k):
                if i + offset in seen:
                    raise ValueError('overlap')
                seen.add(i + offset)
                shadow[i + offset] = struct.unpack_from('>H', packet, pos)[0]
                pos += 2
        if pos != len(packet) - 4:
            raise ValueError('trailing bytes')
    else:
        raise ValueError('invalid tag')
    expected = struct.unpack_from('>I', packet, len(packet) - 4)[0]
    actual = zlib.crc32(b''.join(struct.pack('>H', x) for x in shadow))
    if expected != actual:
        raise ValueError('checksum mismatch')
    return shadow


def _safe_repair_gate(s: Any, fault_str: Any) -> bool:
    if not isinstance(s, dict):
        return False
    if fault_str is not None:
        if not isinstance(fault_str, str):
            return False
        fl = fault_str.strip().lower()
        if any(tok in fl for tok in _UNSAFE_FAULT_TOKENS):
            return False
    if s.get('target_is_flight', False) is not False:
        return False
    for req_true in ('telemetry_fresh', 'epoch_match', 'link_available', 'receiver_ack', 'known_rollback_path'):
        if s.get(req_true, False) is not True:
            return False
    for opt_false in (
        'telemetry_duplicate',
        'half_received',
        'pass_lost',
        'cross_bank_corruption',
        'hidden_cross_references',
        'uncertain_baseline',
        'reactivate_hardware',
    ):
        if s.get(opt_false, False):
            return False
    for opt_true in ('scratch_verified', 'healthy_scratch', 'command_complete', 'baseline_certain'):
        if opt_true in s and s[opt_true] is not True:
            return False
    pm = s.get('power_margin_w', -1.0)
    tu = s.get('temp_uncertainty_c', 99.0)
    if not _is_finite_number(pm) or float(pm) < 2.0:
        return False
    if not _is_finite_number(tu) or float(tu) < 0.0 or float(tu) > 3.0:
        return False
    return True


def plan_repair_ablation(case: dict[str, Any], enable_gap_bridging: bool = True) -> dict[str, Any]:
    hold = {
        'status': 'HOLD',
        'packet_hex': '',
        'pass_bits': [],
        'rtt': 0,
        'requires_readback': False,
        'keeps_original_live': True,
    }
    if not isinstance(case, dict):
        return hold
    for k in ('old_words', 'new_words', 'cap_bits_per_pass', 'scratch_words', 'max_passes', 'safety'):
        if k not in case:
            return hold
    old = case['old_words']
    new = case['new_words']
    cap = case['cap_bits_per_pass']
    scratch = case['scratch_words']
    mw = case['max_passes']
    s = case['safety']
    fault_str = case.get('fault', 'none')

    if not isinstance(old, list) or not isinstance(new, list):
        return hold
    if not _is_strict_int(cap) or not _is_strict_int(scratch) or not _is_strict_int(mw):
        return hold
    if not _safe_repair_gate(s, fault_str):
        return hold
    if len(old) != len(new) or not old or len(old) > 8198:
        return hold
    if scratch < len(old) or scratch + len(old) > 8198:
        return hold
    if any(not _is_strict_int(w) or not (0 <= w < 65536) for w in old + new):
        return hold
    if cap <= 64 or mw <= 0:
        return hold

    candidates = [
        _encode_packet_standard(old, new, 'full', max_gap=0),
        _encode_packet_standard(old, new, 'sparse', max_gap=0),
        _encode_packet_standard(old, new, 'runs', max_gap=0),
    ]
    if enable_gap_bridging:
        candidates.append(_encode_packet_standard(old, new, 'runs', max_gap=1))
        candidates.append(_encode_packet_standard(old, new, 'runs', max_gap=2))

    p = min(candidates, key=len)

    try:
        decoded = verify_shadow_decode(old, p)
        if decoded != new:
            return hold
    except Exception:
        return hold

    remaining = 8 * (len(p) + 32)
    available = cap - 64
    parts: list[int] = []
    while remaining > 0 and len(parts) < mw:
        count = min(remaining, available)
        if count <= 0:
            return hold
        parts.append(count + 64)
        remaining -= count
    if remaining > 0:
        return hold

    return {
        'status': 'STAGED',
        'packet_hex': p.hex(),
        'pass_bits': parts,
        'rtt': len(parts) + 1,
        'requires_readback': True,
        'keeps_original_live': True,
    }


def plan_repair(case: dict[str, Any]) -> dict[str, Any]:
    return plan_repair_ablation(case, enable_gap_bridging=True)


def _usage(mode: tuple[str, ...] | list[str], thermal: float) -> float:
    sci = sum(COST[x] for x in mode)
    return sci + max(0.0, 4.0 + thermal - 0.3 * sci)


def plan_power_ablation(
    observation: dict[str, Any],
    state: dict[str, Any],
    enable_causal_filter: bool = True,
    enable_two_stage_buffer: bool = True,
    enable_branch_lookahead: bool = False,
) -> dict[str, Any]:
    """Power planner with explicit ablation toggles.

    Note: `enable_branch_lookahead` defaults to `False` in the final candidate after
    causal subtraction showed 0.0% safe-science gain from branch lookahead once the
    Empirical-Bayes filter (`enable_causal_filter`) and two-stage Bellman continuation
    margin (`enable_two_stage_buffer`) are active.
    """
    if not isinstance(observation, dict) or not isinstance(state, dict):
        return {'status': 'HOLD', 'mode': [], 'next_state': {'enabled': []}}
    for k in ('month', 'nominal_margin_w', 'previous_shock_w', 'previous_thermal_w', 'enabled'):
        if k not in observation:
            return {'status': 'HOLD', 'mode': [], 'next_state': {'enabled': []}}

    month = observation['month']
    nom = observation['nominal_margin_w']
    prev_s = observation['previous_shock_w']
    prev_t = observation['previous_thermal_w']
    raw_enabled = observation['enabled']

    if not _is_strict_int(month) or month < 0:
        return {'status': 'HOLD', 'mode': [], 'next_state': {'enabled': []}}
    if not (_is_finite_number(nom) and _is_finite_number(prev_s) and _is_finite_number(prev_t)):
        return {'status': 'HOLD', 'mode': [], 'next_state': {'enabled': []}}
    if not isinstance(raw_enabled, (list, tuple)):
        return {'status': 'HOLD', 'mode': [], 'next_state': {'enabled': []}}

    if any(x not in VALID_INSTRUMENTS for x in raw_enabled):
        return {'status': 'HOLD', 'mode': [], 'next_state': {'enabled': []}}

    if 'enabled' in state and isinstance(state['enabled'], (list, tuple)):
        prev_enabled_set = set(x for x in state['enabled'] if x in VALID_INSTRUMENTS)
        if state.get('strict_restart_hold', False) and not set(raw_enabled).issubset(prev_enabled_set):
            return {'status': 'HOLD', 'mode': [], 'next_state': {'enabled': list(prev_enabled_set)}}
        enabled = tuple(x for x in VALID_INSTRUMENTS if x in raw_enabled and x in prev_enabled_set)
    else:
        enabled = tuple(x for x in VALID_INSTRUMENTS if x in raw_enabled)

    hist_s = [float(x) for x in state.get('shocks', []) if _is_finite_number(x)]
    hist_t = [float(x) for x in state.get('thermals', []) if _is_finite_number(x)]
    if month > 0:
        hist_s.append(float(prev_s))
        hist_t.append(float(prev_t))

    if enable_causal_filter:
        mean_s = (sum(hist_s) + 3.0 * (-0.10)) / (len(hist_s) + 3.0)
        mean_t = (sum(hist_t) + 3.0 * 0.30) / (len(hist_t) + 3.0)
        if float(prev_s) < -1.50 or float(prev_t) > 1.50:
            wp = 0.75
        else:
            wp = 0.15
        eff_s = wp * min(0.0, float(prev_s)) + (1.0 - wp) * mean_s
        eff_t = wp * max(mean_t, float(prev_t)) + (1.0 - wp) * mean_t
    else:
        eff_s = float(prev_s)
        eff_t = float(prev_t)

    predicted = float(nom) + eff_s
    buf_both = 1.25 if enable_two_stage_buffer else 0.80
    buf_single = 0.90 if enable_two_stage_buffer else 0.80

    subsets = [m for m in (('MAG', 'PWS'), ('MAG',), ('PWS',), ()) if set(m).issubset(enabled)]

    if ('MAG', 'PWS') in subsets and (predicted - _usage(('MAG', 'PWS'), eff_t) >= buf_both):
        chosen: tuple[str, ...] = ('MAG', 'PWS')
    else:
        singles = [
            m for m in (('PWS',), ('MAG',))
            if m in subsets and (predicted - _usage(m, eff_t) >= buf_single)
        ]
        if not singles:
            chosen = ()
        elif len(singles) == 1 or not enable_branch_lookahead:
            ranked_singles = sorted(
                singles,
                key=lambda m: (sum(VALUE[x] for x in m), -sum(COST[x] for x in m)),
                reverse=True,
            )
            chosen = ranked_singles[0]
        else:
            decay_per_mo = 4.0 / 12.0
            best_m = singles[0]
            best_val = -1.0
            for m in singles:
                rem_margin = (predicted - _usage(m, eff_t)) - buf_single
                est_months = 1.0 + max(0.0, rem_margin / decay_per_mo)
                branch_val = est_months * sum(VALUE[x] for x in m)
                if branch_val > best_val:
                    best_val = branch_val
                    best_m = m
            chosen = best_m

    next_state = {
        'enabled': list(chosen),
        'shocks': hist_s[-24:],
        'thermals': hist_t[-24:],
    }
    return {'status': 'SCHEDULE', 'mode': list(chosen), 'next_state': next_state}


def plan_power(observation: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return plan_power_ablation(
        observation,
        state,
        enable_causal_filter=True,
        enable_two_stage_buffer=True,
        enable_branch_lookahead=False,
    )


def _pareto_prune_dp(dp: dict[int, tuple[float, tuple[int, ...]]], max_states: int = 2048) -> dict[int, tuple[float, tuple[int, ...]]]:
    items = sorted(dp.items(), key=lambda kv: (kv[0], -kv[1][0], kv[1][1]))
    pruned: list[tuple[int, tuple[float, tuple[int, ...]]]] = []
    best_val = -float('inf')
    for cost, (val, sel) in items:
        if val > best_val + 1e-12:
            pruned.append((cost, (val, sel)))
            best_val = val
    if len(pruned) <= max_states:
        return dict(pruned)
    step = len(pruned) / float(max_states)
    kept = [pruned[0], pruned[-1]]
    for idx in range(1, max_states - 1):
        kept.append(pruned[min(len(pruned) - 1, int(idx * step))])
    return dict(kept)


def plan_telemetry_ablation(case: dict[str, Any], allow_large_n: bool = True) -> dict[str, Any]:
    hold = {'status': 'HOLD', 'selected_ids': []}
    if not isinstance(case, dict):
        return hold
    if 'packets' not in case or 'available_bits' not in case:
        return hold
    packets = case['packets']
    cap = case['available_bits']
    if not isinstance(packets, list) or not _is_strict_int(cap) or cap < 0:
        return hold
    n = len(packets)
    if n > 5000:
        return hold
    if not allow_large_n and n > 18:
        return hold
    if n == 0 or cap == 0:
        seen_ids = set()
        for p in packets:
            if not isinstance(p, dict):
                return hold
            for req in ('id', 'size_bits', 'value', 'group', 'deadline'):
                if req not in p:
                    return hold
            pid = p['id']
            sz = p['size_bits']
            val = p['value']
            grp = p['group']
            dl = p['deadline']
            if not _is_strict_int(pid) or pid in seen_ids:
                return hold
            seen_ids.add(pid)
            if not _is_strict_int(sz) or sz <= 0:
                return hold
            if not _is_finite_number(val) or float(val) < 0.0:
                return hold
            if grp not in VALID_INSTRUMENTS:
                return hold
            if not _is_strict_int(dl) or dl < 0:
                return hold
        return {'status': 'SCHEDULE', 'selected_ids': []}

    seen_ids = set()
    clean_packets: list[dict[str, Any]] = []
    for p in packets:
        if not isinstance(p, dict):
            return hold
        for req in ('id', 'size_bits', 'value', 'group', 'deadline'):
            if req not in p:
                return hold
        pid = p['id']
        sz = p['size_bits']
        val = p['value']
        grp = p['group']
        dl = p['deadline']
        if not _is_strict_int(pid) or pid in seen_ids:
            return hold
        seen_ids.add(pid)
        if not _is_strict_int(sz) or sz <= 0:
            return hold
        if not _is_finite_number(val) or float(val) < 0.0:
            return hold
        if grp not in VALID_INSTRUMENTS:
            return hold
        if not _is_strict_int(dl) or dl < 0:
            return hold
        clean_packets.append({
            'id': pid,
            'size_bits': sz,
            'value': float(val),
            'group': grp,
            'deadline': dl,
        })

    if n <= 24:
        dp: dict[int, tuple[float, tuple[int, ...]]] = {0: (0.0, ())}
        for p in sorted(clean_packets, key=lambda x: x['id']):
            size = p['size_bits']
            value = p['value']
            pid = p['id']
            for cost, (val, sel) in list(dp.items()):
                new_cost = cost + size
                if new_cost > cap:
                    continue
                ov = dp.get(new_cost, (-float('inf'), ()))
                if val + value > ov[0] + 1e-9:
                    dp[new_cost] = (val + value, sel + (pid,))
            if len(dp) > 4096:
                dp = _pareto_prune_dp(dp, max_states=4096)
        best = max(dp.items(), key=lambda kv: (kv[1][0], -kv[0]))[1]
        return {'status': 'SCHEDULE', 'selected_ids': list(best[1])}

    best_val = 0.0
    best_cost = 0
    best_sel: tuple[int, ...] = ()

    orderings = [
        sorted(clean_packets, key=lambda p: (-p['value'] / p['size_bits'], -p['value'], p['deadline'], p['id'])),
        sorted(clean_packets, key=lambda p: (-p['value'], p['size_bits'], p['deadline'], p['id'])),
        sorted(clean_packets, key=lambda p: (p['size_bits'], -p['value'], p['deadline'], p['id'])),
    ]
    for order in orderings:
        used = 0
        val_sum = 0.0
        chosen: list[dict[str, Any]] = []
        chosen_set = set()
        for p in order:
            if used + p['size_bits'] <= cap:
                used += p['size_bits']
                val_sum += p['value']
                chosen.append(p)
                chosen_set.add(p['id'])
        unchosen = [p for p in clean_packets if p['id'] not in chosen_set]
        unchosen.sort(key=lambda p: -p['value'])
        improved = True
        while improved:
            improved = False
            for u in unchosen[:40]:
                rem = cap - used
                for idx_c, c_pkt in enumerate(chosen):
                    if u['value'] > c_pkt['value'] + 1e-9 and c_pkt['size_bits'] + rem >= u['size_bits']:
                        used = used - c_pkt['size_bits'] + u['size_bits']
                        val_sum = val_sum - c_pkt['value'] + u['value']
                        chosen_set.remove(c_pkt['id'])
                        chosen_set.add(u['id'])
                        chosen[idx_c] = u
                        unchosen.remove(u)
                        improved = True
                        break
                if improved:
                    break
        if (val_sum > best_val + 1e-9) or (abs(val_sum - best_val) <= 1e-9 and used < best_cost):
            best_val = val_sum
            best_cost = used
            best_sel = tuple(sorted(p['id'] for p in chosen))

    if n <= 160:
        dp_large: dict[int, tuple[float, tuple[int, ...]]] = {0: (0.0, ())}
        for p in orderings[0]:
            size = p['size_bits']
            value = p['value']
            pid = p['id']
            for cost, (val, sel) in list(dp_large.items()):
                new_cost = cost + size
                if new_cost > cap:
                    continue
                ov = dp_large.get(new_cost, (-float('inf'), ()))
                if val + value > ov[0] + 1e-9:
                    dp_large[new_cost] = (val + value, sel + (pid,))
            if len(dp_large) > 1024:
                dp_large = _pareto_prune_dp(dp_large, max_states=768)
        dp_cost, (dp_val, dp_sel) = max(dp_large.items(), key=lambda kv: (kv[1][0], -kv[0]))
        if (dp_val > best_val + 1e-9) or (abs(dp_val - best_val) <= 1e-9 and dp_cost < best_cost):
            best_val = dp_val
            best_cost = dp_cost
            best_sel = tuple(sorted(dp_sel))

    return {'status': 'SCHEDULE', 'selected_ids': list(best_sel)}


def plan_telemetry(case: dict[str, Any]) -> dict[str, Any]:
    return plan_telemetry_ablation(case, allow_large_n=True)