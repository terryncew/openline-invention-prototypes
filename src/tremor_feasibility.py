"""Passive tremor tuned-mass concept: mass and bandwidth tradeoff calculator.
This is only a frequency-response illustration, not a human biomechanics model.
"""
from __future__ import annotations
import math, cmath

def normalized_absorber_response(f_hz:float, tuned_hz:float=5., damping:float=.1, mass_ratio:float=.2)->float:
    """Primary mass 1, k=(2pi 5)^2; absorber mass mu, ka=ma*(2pi ft)^2.
    Harmonic force F=1 on primary. Return |X1| / |X1_unattached|.
    A simplified linear two-DOF oscillator model; no joint/bio coupling.
    """
    if f_hz<=0 or mass_ratio<=0 or tuned_hz<=0 or damping<0:raise ValueError
    w=2*math.pi*f_hz; w0=2*math.pi*5;wa=2*math.pi*tuned_hz
    m1=1.;m2=mass_ratio; k1=w0*w0; k2=m2*wa*wa;c2=2*damping*m2*wa
    z=k2+1j*w*c2
    a=k1+z-w*w*m1;b=-z;d=z-w*w*m2
    det=a*d-b*b
    if abs(det)<1e-12:return float('inf')
    x=d/det
    incumbent=1/complex(k1-w*w,2*.15*w0*w)
    return abs(x)/abs(incumbent)

def simulate():
    freq=[3+i*.25 for i in range(37)]
    return [{'f_hz':round(f,2),'response_ratio':round(normalized_absorber_response(f),3)} for f in freq]
