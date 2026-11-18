"""Public smoke test for the Argon v004 interface. These are NOT hidden holdouts."""
import importlib,sys
m=importlib.import_module('candidate_004')
a={'old_words':[1,2,3,4], 'new_words':[1,2,5,4], 'cap_bits_per_pass':2000,'scratch_words':4,'max_passes':4,'safety':{'telemetry_fresh':True,'epoch_match':True,'link_available':True,'receiver_ack':True,'power_margin_w':4,'temp_uncertainty_c':0.5,'known_rollback_path':True,'target_is_flight':False}, 'fault':'none'}
for name,args in [('plan_repair',(a,)),('plan_power',({'month':0,'nominal_margin_w':10,'previous_shock_w':0,'previous_thermal_w':0,'enabled':['MAG','PWS'],'remaining_margin_unknown':True},{})),('plan_telemetry',({'packets':[{'id':1,'size_bits':400,'value':4,'group':'MAG','deadline':2},{'id':2,'size_bits':600,'value':7,'group':'PWS','deadline':1}], 'available_bits':600},))]:
    v=getattr(m,name)(*args)
    assert isinstance(v,dict),name
    print(name,v)
print('interface smoke PASS (NOT independent flight safety validation)')