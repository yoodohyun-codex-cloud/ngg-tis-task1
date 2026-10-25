"""Structured metadata scaling for the NEW cached allocation normalizations.

Pure JSON-shaped metadata only. No imports or I/O on import, arrays or PDE work.
Original first8 metrics source is never changed by this extension.
"""

def _require(ok,message):
 if not ok:raise ValueError(message)

def _number(value):
 import math
 result=float(value);_require(math.isfinite(result),'Finite scaling input required');return result

def _complex_pair(value,factor):
 _require(isinstance(value,dict)and set(value)=={'real','imaginary'},'Explicit signed complex pair required')
 return dict(real=_number(value['real'])*factor,imaginary=_number(value['imaginary'])*factor)

def scale_electrical(e,s):
 import copy
 s=_number(s);_require(s>=0,'Nonnegative finite amplitude scale');square=s*s;out={}
 pair_keys=('source_complex_power_W','contact_complex_power_W')
 linear_maps=('source_Vpp_by_frequency','source_peak_V_by_frequency','active_source_current_RMS_by_frequency_A')
 linear_scalars=('source_Vpp_each','max_source_Vpp','sum_output_current_RMS_A_bookkeeping','contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V','skin_vector_J_RMS_max_A_m2','skin_vector_J_RMS_P95_A_m2')
 for key,value in e.items():
  if key in pair_keys:out[key]=_complex_pair(value,square)
  elif key=='layer_complex_power_W':out[key]=[_complex_pair(v,square)for v in value]
  elif key=='layers_power_W':out[key]={name:_number(v)*square for name,v in value.items()}
  elif key in linear_maps:out[key]={frequency:_number(v)*s for frequency,v in value.items()}
  elif key in linear_scalars:out[key]=_number(value)*s
  elif key=='source_current_RMS_by_output_A':out[key]=[_number(v)*s for v in value]
  elif key=='physical_pad_current_RMS_A':
   out[key]=[]
   for row in value:
    _require(type(row['physical_pad_id'])is int and row['physical_pad_id']>=0,'Physical pad IDs preserved as exact integers')
    out[key].append({**copy.deepcopy(row),'current_RMS_A':_number(row['current_RMS_A'])*s})
  elif key.endswith('_power_W'):
   _require(type(value)in(int,float),'Unknown structured power needs an explicit schema, never float(dict/list)')
   out[key]=_number(value)*square
  else:out[key]=copy.deepcopy(value) # Dimensionless ratios/topology/IDs/text.
 return out
