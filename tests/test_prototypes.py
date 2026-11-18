import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from continuity_bridge import ContinuityBridge, InputFrame, InvalidFrame, StaleAuthority
from modular_servo import ServoController,ServoObservation
from tremor_feasibility import simulate,normalized_absorber_response

class Continuity(unittest.TestCase):
 def f(self,t,**kwargs):
  base=dict(t=t,head_dx=.5,head_dy=.2,joystick_dx=.1,joystick_dy=.1,sense_pa=0.,reference_pa=0.,witness_pa=0.)
  base.update(kwargs); return InputFrame(**base)
 def test_primary_motion(self):
  x=ContinuityBridge().step(self.f(1.),1.01);self.assertEqual(x['channel'],'HEAD');self.assertEqual(x['dx'],.5)
 def test_fallback_continuity(self):
  b=ContinuityBridge();b.step(self.f(1.,drag_switch=True),1.01)
  x=b.step(self.f(1.1,head_dx=None,head_dy=None,drag_switch=True),1.11)
  self.assertEqual(x['channel'],'JOYSTICK_FALLBACK');self.assertTrue(x['drag_requested'])
 def test_no_inferred_click_from_pressure(self):
  b=ContinuityBridge();x=b.step(self.f(1.,sense_pa=150,witness_pa=150),1.01);self.assertFalse(x['click_requested'])
 def test_explicit_click_with_witness(self):
  b=ContinuityBridge();x=b.step(self.f(1.,commit_switch=True),1.01);self.assertTrue(x['click_requested'])
 def test_refuse_click_on_mismatched_witness(self):
  b=ContinuityBridge();x=b.step(self.f(1.,sense_pa=450,witness_pa=0,commit_switch=True),1.01);self.assertFalse(x['click_requested'])
 def test_click_edge_not_hold(self):
  b=ContinuityBridge();b.step(self.f(1.,commit_switch=True),1.01)
  self.assertFalse(b.step(self.f(1.1,commit_switch=True),1.11)['click_requested'])
 def test_stop_zero_effects_and_epoch(self):
  b=ContinuityBridge();b.step(self.f(1.,drag_switch=True),1.01)
  x=b.step(self.f(1.1,stop_switch=True,commit_switch=True),1.11)
  self.assertTrue(x['stopped']);self.assertFalse(x['drag_requested']);self.assertFalse(x['click_requested'])
  with self.assertRaises(StaleAuthority):b.resume(0)
  b.resume(1);self.assertEqual(b.epoch,2)
 def test_overcurrent_isolates(self):
  x=ContinuityBridge().step(self.f(1.,current_ma=500,commit_switch=True),1.01)
  self.assertEqual(x['channel'],'POWER_ISOLATED');self.assertFalse(x['click_requested'])
 def test_stale_sample_rejected(self):
  with self.assertRaises(InvalidFrame):ContinuityBridge().step(self.f(1.),2.)
 def test_resume_state_snapshot_integrity(self):
  b=ContinuityBridge();b.step(self.f(1.),1.01);snap=b.snapshot();n=ContinuityBridge.from_snapshot(snap)
  self.assertEqual(n.snapshot(),snap)
  snap['state']['x']=5000
  with self.assertRaises(ValueError):ContinuityBridge.from_snapshot(snap)
 def test_pneumatic_optin_dwell(self):
  b=ContinuityBridge(pneumatic_commit_enabled=True)
  self.assertFalse(b.step(self.f(1.,sense_pa=230,witness_pa=220),1.01)['click_requested'])
  self.assertTrue(b.step(self.f(1.2,sense_pa=230,witness_pa=220),1.21)['click_requested'])
  self.assertFalse(b.step(self.f(1.3,sense_pa=230,witness_pa=220),1.31)['click_requested'])
 def test_pneumatic_drift_never_commits(self):
  b=ContinuityBridge(pneumatic_commit_enabled=True)
  self.assertFalse(b.step(self.f(1.,sense_pa=400,witness_pa=0),1.01)['click_requested'])
  self.assertFalse(b.step(self.f(1.2,sense_pa=400,witness_pa=0),1.21)['click_requested'])
 def test_no_head_or_joystick_holds_drag(self):
  b=ContinuityBridge();x=b.step(self.f(1.,head_dx=None,head_dy=None,joystick_dx=None,joystick_dy=None,drag_switch=True),1.01)
  self.assertFalse(x['drag_requested']);self.assertEqual(x['dx'],0)

class ModularServo(unittest.TestCase):
 def obs(self,t=1.,joint=1,**kw):
  d=dict(t=t,joint=joint,primary_online=True,backup_online=True,current_ma=100);d.update(kw);return ServoObservation(**d)
 def test_normal_route(self):
  c=ServoController();c.observe(self.obs());self.assertEqual(c.propose(1,.3,1.01,True,0)['route'],'PRIMARY')
 def test_backup_route(self):
  c=ServoController();c.observe(self.obs(primary_online=False));self.assertEqual(c.propose(1,.3,1.01,True,0)['route'],'BACKUP')
 def test_both_failed_holds(self):
  c=ServoController();c.observe(self.obs(primary_online=False,backup_online=False));self.assertEqual(c.propose(1,.3,1.01,True,0)['status'],'HOLD_NO_ROUTE')
 def test_overcurrent_isolate(self):
  c=ServoController();c.observe(self.obs(current_ma=500));self.assertEqual(c.propose(1,.3,1.01,True,0)['status'],'ISOLATED_POWER_FAULT')
 def test_stale_observation_holds(self):
  c=ServoController();c.observe(self.obs());self.assertEqual(c.propose(1,.3,2.,True,0)['status'],'HOLD_STALE_OBSERVATION')
 def test_requires_authorization(self):
  c=ServoController();c.observe(self.obs());self.assertEqual(c.propose(1,.3,1.01,False,0)['status'],'DENIED_AUTHORITY')
 def test_stop_revokes_stale_epoch(self):
  c=ServoController();c.observe(self.obs());c.stop()
  self.assertEqual(c.propose(1,.3,1.01,True,0)['status'],'DENIED_AUTHORITY')
  with self.assertRaises(PermissionError):c.resume(0)
  c.resume(1);self.assertEqual(c.propose(1,.3,1.01,True,0)['status'],'DENIED_AUTHORITY')
  self.assertEqual(c.propose(1,.3,1.01,True,2)['status'],'PROPOSED_NOT_SENT')
 def test_bad_target_denied(self):
  c=ServoController();c.observe(self.obs());self.assertEqual(c.propose(1,3,1.01,True,0)['status'],'DENIED_BAD_TARGET')
 def test_fault_reset_requires_independent_inspection(self):
  c=ServoController();c.observe(self.obs(current_ma=550))
  with self.assertRaises(PermissionError):c.reset_isolation(1,True,False)
  c.reset_isolation(1,True,True);self.assertNotIn(1,c.isolated)
 def test_no_hardware_output(self):
  c=ServoController();c.observe(self.obs());self.assertEqual(c.propose(1,0,1.01,True,0)['actuation'],'NOT_IMPLEMENTED')
 def test_monotonic_observation(self):
  c=ServoController();c.observe(self.obs())
  with self.assertRaises(ValueError):c.observe(self.obs())

class Tremor(unittest.TestCase):
 def test_response_finite(self):
  self.assertEqual(len(simulate()),37)
 def test_invalid(self):
  with self.assertRaises(ValueError):normalized_absorber_response(0)
 def test_broadband_not_uniform(self):
  a=simulate();self.assertTrue(any(x['response_ratio']>1 for x in a))

if __name__=='__main__':unittest.main()
