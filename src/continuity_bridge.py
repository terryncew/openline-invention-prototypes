"""Continuity Input Bridge — executable, offline control-logic prototype.

No physical sensors, USB HID, or users were tested. Output is a proposed HID
packet only, never sent to an OS. This code is not an assistive medical device.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json, math


@dataclass(frozen=True)
class InputFrame:
    t: float
    head_dx: float | None = None
    head_dy: float | None = None
    joystick_dx: float | None = None
    joystick_dy: float | None = None
    sense_pa: float | None = None
    reference_pa: float | None = None
    witness_pa: float | None = None
    commit_switch: bool = False
    drag_switch: bool = False
    stop_switch: bool = False
    current_ma: float = 30.0


class InvalidFrame(ValueError): pass
class StaleAuthority(PermissionError): pass


class ContinuityBridge:
    """State machine for human-authorized control; no implicit hardware outputs."""
    def __init__(self, max_age_s: float = .15, max_current_ma: float = 420.,
                 pneumatic_commit_enabled: bool = False, pneumatic_dwell_s: float = .15):
        self.epoch = 0
        self.stopped = False
        self.last_t: float | None = None
        self.x = self.y = 0.
        self.dragging = False
        self.active_channel = 'NONE'
        self.witness_standing = 'UNKNOWN'
        self._prev_commit = False
        self.pneumatic_commit_enabled = pneumatic_commit_enabled
        self.pneumatic_dwell_s = pneumatic_dwell_s
        self._pressure_since: float | None = None
        self._pressure_latched = False
        self._events: list[dict] = []
        self.max_age_s = max_age_s
        self.max_current_ma = max_current_ma

    def stop(self, reason='operator_stop'):
        self.epoch += 1
        self.stopped = True
        self.dragging = False
        self._pressure_since = None
        self._pressure_latched = False
        self._events.append({'event':'STOP', 'epoch':self.epoch,'reason':reason})
        return {'status':'STOPPED','epoch':self.epoch}

    def resume(self, expected_epoch: int):
        if type(expected_epoch) is not int or expected_epoch != self.epoch or not self.stopped:
            raise StaleAuthority('resume_requires_current_stopped_epoch')
        self.epoch += 1
        self.stopped = False
        self._events.append({'event':'RESUME','epoch':self.epoch})
        return {'status':'ACTIVE','epoch':self.epoch}

    def step(self, frame: InputFrame, now_s: float) -> dict:
        values = asdict(frame)
        for v in values.values():
            if isinstance(v, (float, int)) and not isinstance(v, bool) and not math.isfinite(v):
                raise InvalidFrame('non_finite_input')
        if self.last_t is not None and frame.t <= self.last_t:
            raise InvalidFrame('non_monotonic_sample_time')
        if frame.t > now_s + 0.001 or now_s - frame.t > self.max_age_s:
            raise InvalidFrame('stale_or_future_sample')
        self.last_t = frame.t
        if frame.stop_switch:
            self.stop('user_pressed_stop')
        if self.stopped:
            self._prev_commit = bool(frame.commit_switch)
            return self._packet(0, 0, False, 'STOPPED', 'NO_EFFECT')
        if frame.current_ma >= self.max_current_ma:
            self.dragging = False
            self.witness_standing = 'OVERCURRENT'
            self._prev_commit = bool(frame.commit_switch)
            return self._packet(0,0,False,'POWER_ISOLATED','ABSTAIN')
        head_good = frame.head_dx is not None and frame.head_dy is not None
        joy_good = frame.joystick_dx is not None and frame.joystick_dy is not None
        if head_good and all(abs(v) <= 1 for v in (frame.head_dx,frame.head_dy)):
            dx, dy, channel = frame.head_dx, frame.head_dy, 'HEAD'
        elif joy_good and all(abs(v) <= 1 for v in (frame.joystick_dx,frame.joystick_dy)):
            dx, dy, channel = frame.joystick_dx,frame.joystick_dy,'JOYSTICK_FALLBACK'
        else:
            dx=dy=0.;channel='NO_KINEMATIC_INPUT'
            self.dragging=False
        self.active_channel = channel
        if None in (frame.sense_pa,frame.reference_pa,frame.witness_pa):
            self.witness_standing='UNKNOWN'
        else:
            # This is a predeclared engineering *screen*, not calibrated physical observability.
            sensor_diff=frame.sense_pa-frame.reference_pa
            witness_diff=frame.witness_pa-frame.reference_pa
            self.witness_standing=('SUSPECT_DRIFT' if abs(sensor_diff-witness_diff)>180
                                   else 'CONSISTENT_WITH_MODEL')
        # Optional pneumatic trigger is an explicit *user-configured command channel*.
        # It does not automatically grant external authority or drive the computer.
        pressure_request = False
        coherent = self.witness_standing == 'CONSISTENT_WITH_MODEL'
        if self.pneumatic_commit_enabled and coherent and frame.sense_pa is not None and frame.reference_pa is not None:
            magnitude = frame.sense_pa - frame.reference_pa
            if magnitude >= 160.0:
                if self._pressure_since is None: self._pressure_since = frame.t
                if frame.t - self._pressure_since >= self.pneumatic_dwell_s and not self._pressure_latched:
                    pressure_request = True
                    self._pressure_latched = True
            elif magnitude <= 70.0:
                self._pressure_since = None
                self._pressure_latched = False
        else:
            self._pressure_since = None
            self._pressure_latched = False
        click = bool((frame.commit_switch and not self._prev_commit or pressure_request)
                     and coherent)
        self._prev_commit = bool(frame.commit_switch)
        if click and channel != 'NO_KINEMATIC_INPUT':
            self._events.append({'event':'PROPOSED_CLICK','epoch':self.epoch,'t':frame.t})
        else:
            click=False
        if frame.drag_switch and channel != 'NO_KINEMATIC_INPUT':
            self.dragging=True
        elif not frame.drag_switch:
            self.dragging=False
        self.x += dx
        self.y += dy
        return self._packet(dx,dy,click,channel,self.witness_standing)

    def _packet(self,dx,dy,click,channel,witness):
        return {'dx':dx,'dy':dy,'click_requested':click,'drag_requested':self.dragging,
                'channel':channel,'witness':witness,'stopped':self.stopped,'epoch':self.epoch,
                'output_class':'DRY_RUN_PROPOSED_HID_ONLY'}

    def snapshot(self)->dict:
        body={k:getattr(self,k) for k in ('epoch','stopped','last_t','x','y','dragging','active_channel','witness_standing','_prev_commit','_pressure_since','_pressure_latched','pneumatic_commit_enabled','pneumatic_dwell_s')}
        digest=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return {'state':body,'sha256_integrity_only_not_authenticity':digest}

    @classmethod
    def from_snapshot(cls, envelope):
        body=envelope['state']; digest=envelope['sha256_integrity_only_not_authenticity']
        if hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=digest:
            raise ValueError('tampered_snapshot')
        if set(body)!={'epoch','stopped','last_t','x','y','dragging','active_channel','witness_standing','_prev_commit','_pressure_since','_pressure_latched','pneumatic_commit_enabled','pneumatic_dwell_s'}:
            raise ValueError('wrong_snapshot_schema')
        obj=cls()
        for k,v in body.items(): setattr(obj,k,v)
        return obj
