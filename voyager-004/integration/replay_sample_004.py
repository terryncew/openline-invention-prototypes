#!/usr/bin/env python3
"""Generates and replays the concrete 93-byte gap-bridged surrogate patch sample (`integration/`)."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
for p in (ROOT_DIR, THIS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import candidate_004 as cand004
import reference_004 as ref004


def main() -> None:
    THIS_DIR.mkdir(parents=True, exist_ok=True)
    old_words = [100 + i for i in range(60)]
    new_words = list(old_words)
    for k in range(5, 45, 3):
        new_words[k] = 9000 + k
        new_words[k + 1] = 8000 + k

    case = {
        'old_words': old_words,
        'new_words': new_words,
        'cap_bits_per_pass': 1100,
        'scratch_words': 60,
        'max_passes': 1,
        'safety': {
            'telemetry_fresh': True,
            'epoch_match': True,
            'link_available': True,
            'receiver_ack': True,
            'power_margin_w': 3.5,
            'temp_uncertainty_c': 0.8,
            'known_rollback_path': True,
            'target_is_flight': False,
        },
        'fault': 'none',
    }

    res_cand = cand004.plan_repair(case)
    res_ref = ref004.plan_repair(case)
    ref_raw_pkt = min((ref004._mem_packet(old_words, new_words, c) for c in ('full', 'sparse', 'runs')), key=len)

    assert res_cand['status'] == 'STAGED', res_cand
    assert res_ref['status'] == 'HOLD', res_ref

    patch_bytes = bytes.fromhex(res_cand['packet_hex'])
    reconstructed = cand004.verify_shadow_decode(old_words, patch_bytes)
    assert reconstructed == new_words

    orig_bin = b''.join(struct.pack('>H', w) for w in old_words)
    (THIS_DIR / 'sample_004_original_words.bin').write_bytes(orig_bin)
    (THIS_DIR / 'sample_004_gap_bridged_patch.bin').write_bytes(patch_bytes)

    manifest = {
        'description': 'Concrete surrogate FDS relocation patch demonstrating M1 Gap-Bridging Run Merging (tag=3)',
        'not_flight_code_notice': 'SURROGATE ONLY — DO NOT TRANSMIT TO VOYAGER 1. Real 2026 FDS map and CCS framing are UNKNOWN (HOLD).',
        'image_length_words': len(old_words),
        'modified_words_count': sum(1 for a, b in zip(old_words, new_words) if a != b),
        'unchanged_1word_gaps_bridged': 13,
        'reference_004_shortest_packet_bytes': len(ref_raw_pkt),
        'reference_004_required_pass_bits': 8 * (len(ref_raw_pkt) + 32) + 64,
        'reference_004_status_at_1100bit_cap': res_ref['status'],
        'candidate_004_packet_bytes': len(patch_bytes),
        'candidate_004_pass_bits': res_cand['pass_bits'],
        'candidate_004_rtt': res_cand['rtt'],
        'candidate_004_status_at_1100bit_cap': res_cand['status'],
        'candidate_004_packet_hex': res_cand['packet_hex'],
        'crc32_verified': True,
    }
    (THIS_DIR / 'sample_004_manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )
    print('sample_004 replay PASS:', json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()