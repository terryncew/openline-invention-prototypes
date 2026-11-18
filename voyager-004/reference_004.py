"""Public strong conventional comparator for Voyager-004 surrogate.
Ground-only synthetic Python; NOT Voyager opcodes or NASA operating software.
Use identical input schema in candidate_004.py. MIT public code for reproducibility.
"""
import struct, math, zlib

COST={'MAG':2.5, 'PWS':3.0}
VALUE={'MAG':1.0, 'PWS':1.35}


def _mem_packet(old,new,kind):
    changes=[(i,v) for i,(a,v) in enumerate(zip(old,new)) if a!=v]
    if kind=='full':
        body=struct.pack('>BH',1,len(new))+b''.join(struct.pack('>H',v) for v in new)
    elif kind=='sparse':
        body=struct.pack('>BH',2,len(changes))+b''.join(struct.pack('>HH',i,v) for i,v in changes)
    elif kind=='runs':
        runs=[]
        for i,v in changes:
            if runs and i==runs[-1][0]+len(runs[-1][1]): runs[-1][1].append(v)
            else:runs.append([i,[v]])
        body=struct.pack('>BH',3,len(runs))+b''.join(struct.pack('>HH',i,len(vals))+b''.join(struct.pack('>H',v) for v in vals) for i,vals in runs)
    else:raise ValueError('codec')
    return body+struct.pack('>I',zlib.crc32(b''.join(struct.pack('>H',i) for i in new)))


def _safe(s):
    return (not s.get('target_is_flight',False) and
       s.get('telemetry_fresh',False) and s.get('epoch_match',False) and
       s.get('link_available',False) and s.get('receiver_ack',False) and
       s.get('known_rollback_path',False) and s.get('power_margin_w',-1)>=2.0 and
       s.get('temp_uncertainty_c',99)<=3.0)


def plan_repair(case):
    old=case['old_words']; new=case['new_words']; cap=case['cap_bits_per_pass']; s=case['safety']; mw=case['max_passes']
    hold={'status':'HOLD','packet_hex':'','pass_bits':[],'rtt':0,'requires_readback':False,'keeps_original_live':True}
    if not _safe(s) or len(old)!=len(new) or not old or len(old)>8198: return hold
    if case['scratch_words']<len(old) or case['scratch_words']+len(old)>8198:return hold
    if any(type(w)!=int or not 0<=w<65536 for w in old+new):return hold
    if cap<=64:return hold
    p=min((_mem_packet(old,new,c) for c in ('full','sparse','runs')),key=len)
    remaining=8*(len(p)+32); available=cap-64
    parts=[]
    while remaining>0 and len(parts)<mw:
        count=min(remaining,available)
        if count<=0:return hold
        parts.append(count+64);remaining-=count
    if remaining>0:return hold
    return {'status':'STAGED','packet_hex':p.hex(),'pass_bits':parts,'rtt':len(parts)+1,'requires_readback':True,'keeps_original_live':True}


def _usage(mode,thermal):
    sci=sum(COST[x] for x in mode)
    return sci+max(0.0,4+thermal-0.3*sci)


def plan_power(observation,state):
    enabled=tuple(x for x in ('MAG','PWS') if x in observation['enabled'])
    predicted=observation['nominal_margin_w']+observation['previous_shock_w']
    t=observation['previous_thermal_w']
    subsets=[m for m in (('MAG','PWS'),('MAG',),('PWS',),()) if set(m).issubset(enabled)]
    # Do not model instrument restart. Retain highest-value safe subset.
    ranked=sorted(subsets,key=lambda m:(sum(VALUE[x] for x in m),-sum(COST[x] for x in m)),reverse=True)
    feasible=next((m for m in ranked if predicted-_usage(m,t)>=0.8),())
    return {'status':'SCHEDULE','mode':list(feasible),'next_state':{'enabled':list(feasible)}}


def plan_telemetry(case):
    packets=case['packets']; cap=case['available_bits']; n=len(packets)
    # Exact 0/1 knapsack; values are the same public proxy available to all arms.
    if n>18 or cap<0:return {'status':'HOLD','selected_ids':[]}
    dp={0:(0.,())}
    for p in sorted(packets,key=lambda p:p['id']):
        size=p['size_bits'];value=p['value'];pid=p['id']
        for cost,(val,sel) in list(dp.items()):
            new_cost=cost+size
            if new_cost>cap:continue
            ov=dp.get(new_cost,(-float('inf'),()))
            if val+value>ov[0]+1e-9:
                dp[new_cost]=(val+value,sel+(pid,))
    best=max(dp.items(),key=lambda kv:(kv[1][0],-kv[0]))[1]
    return {'status':'SCHEDULE','selected_ids':list(best[1])}