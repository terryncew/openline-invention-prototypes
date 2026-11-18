#!/usr/bin/env python3
"""Reproducible, pure-Python simulated protocol trials. No device I/O."""
from __future__ import annotations
import json, random, statistics, sys
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'src'))
from continuity_bridge import ContinuityBridge,InputFrame
from modular_servo import ServoController,ServoObservation
from tremor_feasibility import simulate

R=random.Random(20261117)
N=1000
results={'evidence_type':'software_state_machine_in_constructed_scenarios',
         'physical_trials':0,'human_trials':0,'hardware_actuations':0,
         'original_argon_source':'OPENLINE_REALITY_GROUNDED_FRONTIER_INVENTION_001_PACKAGE.zip',
         'seed':20261117,'per_device_cases':N}

A={'safe':0,'head_use':0,'fallback_use':0,'held':0,'explicit_clicks':0,'stop_cases':0,'drift_cases':0,'overcurrent_cases':0}
for i in range(N):
    head=R.random()>.20
    joy=R.random()>.10
    drift=R.random()<.20
    overcurrent=R.random()<.07
    stop=R.random()<.05
    user_click=R.random()<.20
    b=ContinuityBridge()
    f=InputFrame(t=1, head_dx=.4 if head else None,head_dy=.1 if head else None,
        joystick_dx=.2 if joy else None,joystick_dy=.1 if joy else None,
        sense_pa=330 if drift else 0,reference_pa=0,witness_pa=0,
        commit_switch=user_click,stop_switch=stop,current_ma=500 if overcurrent else 50)
    out=b.step(f,1.01)
    invalid= stop or overcurrent or drift or not(head or joy)
    violated=out['click_requested'] and (invalid or not user_click)
    if not violated:A['safe']+=1
    if out['channel']=='HEAD':A['head_use']+=1
    elif out['channel']=='JOYSTICK_FALLBACK':A['fallback_use']+=1
    else:A['held']+=1
    A['explicit_clicks']+=int(out['click_requested'])
    A['stop_cases']+=int(stop);A['drift_cases']+=int(drift);A['overcurrent_cases']+=int(overcurrent)
results['continuity_bridge']=A

C={'safe':0,'primary_routes':0,'backup_routes':0,'held_or_denied':0,'single_route_would_hold':0,'dual_route_recovers':0,'overcurrent_faults':0}
for i in range(N):
    pri=R.random()>.20
    bak=R.random()>.15
    current=480. if R.random()<.06 else 100.
    authorized=R.random()>.05
    fresh=R.random()>.12
    c=ServoController()
    c.observe(ServoObservation(t=1,joint=1,primary_online=pri,backup_online=bak,current_ma=current))
    out=c.propose(1,.25,1.01 if fresh else 1.4,authorized,0)
    active=out['status']=='PROPOSED_NOT_SENT'
    bad=not authorized or not fresh or current>=420 or not(pri or bak)
    if not(active and bad):C['safe']+=1
    if out.get('route')=='PRIMARY':C['primary_routes']+=1
    elif out.get('route')=='BACKUP':C['backup_routes']+=1
    else:C['held_or_denied']+=1
    # This is *structural redundancy*, not a matched physical comparison.
    if authorized and fresh and current<420 and not pri:
       C['single_route_would_hold']+=1
       C['dual_route_recovers']+=int(bak)
    C['overcurrent_faults']+=int(current>=420)
results['modular_servo']=C
T=simulate()
results['tremor_feasibility']={
    'linear_model_only':True,'tuned_mass_ratio':.2,'tuned_frequency_hz':5.,
    'response_at_5_hz':next(x['response_ratio'] for x in T if x['f_hz']==5),
    'worst_amplification':max(T,key=lambda x:x['response_ratio']),
    'improved_bins':sum(x['response_ratio']<1.0 for x in T),
    'worsened_bins':sum(x['response_ratio']>1.0 for x in T),
    'frequency_sweep':T}
assert A['safe']==N and C['safe']==N
out=root/'results'/'constructed_scenario_receipt.json'
out.write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
print('CIB simulated invariants:',A['safe'],'/',N)
print('SHMC simulated invariants:',C['safe'],'/',N)
print('Fallback events:',A['fallback_use'],'Backup route events:',C['backup_routes'])
print('Tremor bins worsened:',results['tremor_feasibility']['worsened_bins'],'of',len(T))
print('Receipt:',out)
