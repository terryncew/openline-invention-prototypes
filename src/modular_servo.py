"""Self-Healing Modular Controller — deterministic simulated bus planner.

No wiring, servo actuation, physical eFuse-trip timing, or stability claims.
Returns a *proposed* command route; never sends serial or power commands.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class ServoObservation:
    t:float
    joint:int
    primary_online:bool
    backup_online:bool
    current_ma:float
    temperature_c:float=30.

class ServoController:
    def __init__(self,joints:int=6, current_limit_ma:float=420., stale_after_s:float=.2):
        self.joints=joints;self.current_limit_ma=current_limit_ma;self.stale_after_s=stale_after_s
        self.epoch=0;self.stopped=False
        self.last_t={i:-1. for i in range(1,joints+1)}
        self.obs={};self.isolated=set();self.committed=[]

    def stop(self):
        self.epoch+=1;self.stopped=True
        return {'STOPPED':True,'epoch':self.epoch}
    def resume(self,expected_epoch:int):
        if type(expected_epoch)!=int or not self.stopped or expected_epoch!=self.epoch:
            raise PermissionError('stale_owner_epoch')
        self.epoch+=1;self.stopped=False

    def observe(self,obs:ServoObservation):
        if obs.joint not in self.last_t or not math.isfinite(obs.current_ma) or not math.isfinite(obs.t) or not math.isfinite(obs.temperature_c):
            raise ValueError('invalid_observation')
        if obs.t <= self.last_t[obs.joint]:
            raise ValueError('non_monotonic_observation')
        self.last_t[obs.joint]=obs.t
        self.obs[obs.joint]=obs
        if obs.current_ma >= self.current_limit_ma or obs.temperature_c >= 80.:
            self.isolated.add(obs.joint)
        return {'joint':obs.joint,'isolated':obs.joint in self.isolated}

    def propose(self, joint:int, normalized_target:float, now_s:float, authorized:bool=False, expected_epoch:int|None=None)->dict:
        base={'joint':joint,'effect':'NONE','actuation':'NOT_IMPLEMENTED'}
        if self.stopped or not authorized or expected_epoch != self.epoch: return {**base,'status':'DENIED_AUTHORITY'}
        if joint not in self.last_t or not math.isfinite(normalized_target) or abs(normalized_target)>1:
            return {**base,'status':'DENIED_BAD_TARGET'}
        if joint in self.isolated:return {**base,'status':'ISOLATED_POWER_FAULT'}
        obs=self.obs.get(joint)
        if obs is None or now_s<obs.t or now_s-obs.t>self.stale_after_s:
            return {**base,'status':'HOLD_STALE_OBSERVATION'}
        if obs.primary_online: route='PRIMARY'
        elif obs.backup_online:route='BACKUP'
        else:return {**base,'status':'HOLD_NO_ROUTE'}
        proposal={**base,'status':'PROPOSED_NOT_SENT','route':route,'target':normalized_target,'epoch':self.epoch}
        self.committed.append(proposal)
        return proposal

    def reset_isolation(self,joint:int,owner_authorized:bool, inspected_safe:bool):
        if not owner_authorized or not inspected_safe or self.stopped:
            raise PermissionError('requires_owner_and_external_inspection')
        self.isolated.discard(joint)
