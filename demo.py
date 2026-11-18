"""Small readable offline demo of both *dry-run* control prototypes."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'src'))
from continuity_bridge import ContinuityBridge,InputFrame
from modular_servo import ServoController,ServoObservation

b=ContinuityBridge()
a=b.step(InputFrame(t=1,head_dx=.5,head_dy=.2,joystick_dx=.1,joystick_dy=.1,sense_pa=0,reference_pa=0,witness_pa=0,drag_switch=True),1.01)
f=b.step(InputFrame(t=1.1,joystick_dx=.15,joystick_dy=.1,sense_pa=0,reference_pa=0,witness_pa=0,drag_switch=True),1.11)
s=b.stop()
h=b.step(InputFrame(t=1.2,joystick_dx=.2,joystick_dy=.2,sense_pa=0,reference_pa=0,witness_pa=0,commit_switch=True),1.21)
c=ServoController();c.observe(ServoObservation(t=1.,joint=1,primary_online=False,backup_online=True,current_ma=100))
r=c.propose(1,.35,1.01,authorized=True,expected_epoch=0)
print(json.dumps({'continuity_initial':a,'continuity_fallback':f,'stop':s,'effect_after_stop':h,'robot_backup_proposal':r,'scope':'NO PHYSICAL OR OPERATING SYSTEM EFFECTS'},indent=2))
