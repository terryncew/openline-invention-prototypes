import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
root=Path(__file__).parent
R=json.loads((root/'results'/'constructed_scenario_receipt.json').read_text())

def chart(values,labels,title,filename):
 fig,ax=plt.subplots(figsize=(8.2,3.3))
 bars=ax.barh(labels,values)
 ax.invert_yaxis();ax.set_xlim(0,1000)
 ax.set_xlabel('Constructed one-step cases (N=1,000)')
 ax.set_title(title,fontsize=13,weight='bold')
 for p,v in zip(bars,values):
  ax.text(v+7,p.get_y()+p.get_height()/2,str(v),va='center',fontsize=10)
 fig.tight_layout();fig.savefig(root/'figures'/filename,dpi=180)
 plt.close(fig)
chart([R['continuity_bridge'][k] for k in ('head_use','fallback_use','held')],
      ['Head-motion channel','Joystick fallback','Hold / deny'],
      'Input bridge: dry-run route decisions', 'A_route_decisions.png')
chart([R['modular_servo'][k] for k in ('primary_routes','backup_routes','held_or_denied')],
      ['Primary route','Backup route','Hold / deny'],
      'Modular servo: no-actuation route proposals','C_route_decisions.png')
rows=R['tremor_feasibility']['frequency_sweep']
fig,ax=plt.subplots(figsize=(8.2,3.7))
ax.plot([r['f_hz'] for r in rows],[r['response_ratio'] for r in rows],marker='.',markersize=3)
ax.axhline(1,linestyle='--',lw=1)
ax.set_xlabel('Excitation frequency (Hz)')
ax.set_ylabel('Amplitude ratio (absorber / reference)')
ax.set_title('Passive absorber: gain at tuning, amplification nearby',fontsize=13,weight='bold')
ax.annotate('5 Hz: 0.294',xy=(5,.294),xytext=(5.6,1.2),arrowprops={'arrowstyle':'->'})
ax.annotate('4 Hz: 4.588',xy=(4,4.588),xytext=(5.4,3.6),arrowprops={'arrowstyle':'->'})
fig.tight_layout();fig.savefig(root/'figures'/'D_tremor_sweep.png',dpi=180);plt.close(fig)
