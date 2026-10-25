"""Cached linear two-carrier allocation electrical synthesis, no import work.

r is the relative active-current ratio multiplier, NOT an absolute I0/I1 target.
Only the root invokes these scalar/array functions; no files or PDE are accessed.
"""
from __future__ import annotations
import math
FREQUENCIES=(2000,2010)
LAYERS=('sc','dermis','fat','muscle')

def require(ok,message):
 if not ok:raise ValueError(message)
def pair(value):
 value=complex(value);require(math.isfinite(value.real)and math.isfinite(value.imag),'Finite signed complex quantity');return dict(real=value.real,imaginary=value.imag)
def _complex(value):
 result=complex(value['real'],value['imaginary'])if isinstance(value,dict)else complex(value)
 require(math.isfinite(result.real)and math.isfinite(result.imag),'Finite signed complex proof value');return result

def weights_for_relative_multiplier(I0base_RMS,I1base_RMS,r):
 """a0=min(1,r),a1=min(1,1/r); maximum original sourceVpp remains1."""
 I0=float(I0base_RMS);I1=float(I1base_RMS);r=float(r)
 require(all(math.isfinite(v)and v>0 for v in(I0,I1,r)),'Positive finite baseline active currents and relative allocation multiplier')
 a0=min(1.,r);a1=1. if r<=1. else 1./r
 require(0<a0<=1 and 0<a1<=1 and max(a0,a1)==1.,'Positive bounded normalized amplitudes; reject underflow')
 base_ratio=I0/I1;actual0=a0*I0;actual1=a1*I1;require(all(math.isfinite(v)and v>0 for v in(base_ratio,actual0,actual1)),'Finite nonzero representable active currents')
 achieved=actual0/actual1;relative=achieved/base_ratio;require(math.isfinite(achieved)and math.isfinite(relative)and abs(relative-r)<=1e-12*max(1.,r),'Achieved relative ratio identity')
 return dict(a0=a0,a1=a1,relative_multiplier_requested=r,relative_multiplier_achieved=relative,
  baseline_active_current_ratio_I0_over_I1=base_ratio,achieved_absolute_active_current_ratio_I0_over_I1=achieved,
  baseline_active_current_RMS_A=[I0,I1],achieved_active_current_RMS_A=[actual0,actual1],
  source_Vpp_by_frequency={'2000':a0,'2010':a1},source_peak_V_by_frequency={'2000':.5*a0,'2010':.5*a1},
  maximum_source_Vpp=1.,relative_multiplier_one_exact_original_alias=r==1.,
  ratio_definition='(Iactive2000/Iactive2010)/(Iactive2000base/Iactive2010base); NOT absolute equal-current matching',
  actual_PDE_runs=0,independent_outputs=2,source_resistance_ohm=50.)

def _raw(np,raw,frequency):
 I=np.asarray(raw['source_current_peak_A'],np.complex128);J=np.asarray(raw['contact_normal_J_peak_A_m2'],np.complex128);drop=np.asarray(raw['contact_drop_peak_V'],np.complex128);area=np.asarray(raw['contact_area_m2'],float);pad0=np.asarray(raw['contact_pad']);pad=pad0.astype(np.int64);layer=np.asarray(raw['layer_complex_power_W'],np.complex128)
 require(I.shape==(2,)and layer.shape==(4,)and J.ndim==1 and len(J)>0 and J.shape==drop.shape==area.shape==pad.shape,'Actual two-output/four-layer contact raw ABI')
 require(np.array_equal(pad0,pad)and np.all(pad>=0)and np.all(area>0),'Physical pad IDs exact nonnegative integers and actualpositive contact areas')
 require(all(np.isfinite(v).all()for v in(I,J,drop,area,layer)),'Finite actual cached phasors and signed complex layer powers')
 return dict(I=I,J=J,drop=drop,area=area,pad=pad,layer=layer,frequency=frequency)

def _p95(np,value,area):
 order=np.argsort(value,kind='stable');at=min(int(np.searchsorted(np.cumsum(area[order]),.95*float(area.sum()),side='left')),len(value)-1);return float(value[order[at]])

def synthesize(np,raw0,raw1,proof0,proof1,a0,a1):
 """Return (electrical,per_frequency), preserving all signed cached powers.

 Each complete complex frequency response scales coherently by its own a_f,
 including the induced current in the other, zero-ideal-voltage output. Powers
 scale by a_f² separately. Skin vectorJ remains the responsibility of the fullE
 metrics; this helper never substitutes contactJ for tissue vectorJ.
 """
 a0=float(a0);a1=float(a1);require(all(math.isfinite(a)and 0<a<=1 for a in(a0,a1))and max(a0,a1)==1.,'This allocation protocol fixes maximum sourceVpp1 withpositive amplitudes')
 rows=[_raw(np,raw0,2000),_raw(np,raw1,2010)];require(np.array_equal(rows[0]['area'],rows[1]['area'])and np.array_equal(rows[0]['pad'],rows[1]['pad']),'Same actual geometry/contact order at both carriers; no index remapping')
 if 'contact_xy_index'in raw0 or'contact_xy_index'in raw1:require('contact_xy_index'in raw0 and'contact_xy_index'in raw1 and np.array_equal(raw0['contact_xy_index'],raw1['contact_xy_index']),'Same actual contact-cell ordering')
 I2=np.zeros(2);J2=np.zeros(len(rows[0]['area']));V2=np.zeros_like(J2);layer_total=np.zeros(4,np.complex128);source_total=0j;contact_total=0j;resistor_total=0.;details=[];active_base=[];active_actual=[];physical_ids=np.unique(rows[0]['pad']);pad_current2={int(p):0. for p in physical_ids}
 for row,proof,amplitude,output in zip(rows,(proof0,proof1),(a0,a1),(0,1)):
  frequency=row['frequency'];require('frequency_Hz'not in proof or int(proof['frequency_Hz'])==frequency,'Frequency-specific proof, no swapped or reused carrier')
  require('passed'not in proof or proof['passed']is True,'Failed physical source proof cannot become a valid allocation')
  current=amplitude*row['I'];density=amplitude*row['J'];drop=amplitude*row['drop'];square=amplitude*amplitude
  source=square*_complex(proof['source_complex_power_W']);contact=square*_complex(proof['contact_complex_power_W']);resistor=square*float(proof['source_resistor_power_W']);require(math.isfinite(resistor)and resistor>=0,'Finite nonnegative original50ohm real loss')
  layers=square*row['layer'];I2+=abs(current)**2/2;J2+=abs(density)**2/2;V2+=abs(drop)**2/2;layer_total+=layers;source_total+=source;contact_total+=contact;resistor_total+=resistor
  base_active=float(abs(row['I'][output])/math.sqrt(2));actual_active=float(abs(current[output])/math.sqrt(2));require(base_active>0 and actual_active>0,'Nonzero active-carrier source current')
  active_base.append(base_active);active_actual.append(actual_active);per_pad=[]
  for p in physical_ids:
   selection=row['pad']==p;inward=complex(np.sum(density[selection]*row['area'][selection]));pad_current2[int(p)]+=abs(inward)**2/2
   per_pad.append(dict(physical_pad_id=int(p),inward_current_peak_A=pair(inward),current_RMS_A=abs(inward)/math.sqrt(2)))
  details.append(dict(frequency_Hz=frequency,active_output=output,amplitude=amplitude,source_high_impedance_Vpp=amplitude,source_peak_V=.5*amplitude,
   scaled_source_current_peak_A=[pair(v)for v in current],all_output_currents_scaled_including_induced=True,active_source_current_RMS_A=actual_active,baseline_active_source_current_RMS_A=base_active,
   source_complex_power_W=pair(source),contact_complex_power_W=pair(contact),layer_complex_power_W=[pair(v)for v in layers],source_resistor_power_W=resistor,
   signed_complex_power_sum_W=pair(complex(layers.sum())+contact+resistor),physical_pad_currents=per_pad,
   power_scaling='Each signed frequency-specific source/layer/contact power multiplied by its own amplitude², not a common aggregate scale',new_PDE_runs=0))
 J=np.sqrt(J2);voltage=np.sqrt(V2);currents=np.sqrt(I2);base_ratio=active_base[0]/active_base[1];actual_ratio=active_actual[0]/active_actual[1]
 electrical=dict(source_Vpp_each=max(a0,a1),source_Vpp_by_frequency={'2000':a0,'2010':a1},source_peak_V_by_frequency={'2000':.5*a0,'2010':.5*a1},
  source_Vpp_each_semantics='Legacy screen_metrics API maximum active sourceVpp, NOT a claim that unequal frequency drives are identical',
  unequal_source_Vpp=bool(a0!=a1),source_current_RMS_by_output_A=currents.tolist(),sum_output_current_RMS_A_bookkeeping=float(currents.sum()),
  active_source_current_RMS_by_frequency_A={'2000':active_actual[0],'2010':active_actual[1]},baseline_active_current_ratio_I0_over_I1=base_ratio,achieved_absolute_active_current_ratio_I0_over_I1=actual_ratio,achieved_relative_active_current_ratio_multiplier=actual_ratio/base_ratio,
  source_power_W=float(source_total.real),source_complex_power_W=pair(source_total),layers_power_W={name:float(layer_total[i].real)for i,name in enumerate(LAYERS)},layer_complex_power_W=[pair(v)for v in layer_total],
  SC_power_W=float(layer_total[0].real),skin_power_W=float(layer_total[:2].real.sum()),contact_power_W=float(contact_total.real),contact_complex_power_W=pair(contact_total),source_resistor_power_W=float(resistor_total),
  contact_normal_J_RMS_max_A_m2=float(J.max()),contact_normal_J_RMS_P95_A_m2=_p95(np,J,rows[0]['area']),contact_voltage_RMS_max_V=float(voltage.max()),
  physical_pad_current_RMS_A=[dict(physical_pad_id=int(p),current_RMS_A=math.sqrt(pad_current2[int(p)]))for p in physical_ids],
  independent_outputs=2,source_resistance_ohm=50.,return_topology='Unchanged commonGND; inactive idealoutput0Vbehind its50ohm',
  power_definition='Signed complexVI*/2 preserved; real losses not absolute-valued/clipped; two-frequency RMS sums squares after coherent per-frequency scaling',
  skin_vector_J_burdens='Not calculated here; full weightedE metric evaluation supplies skin_vector_J_RMS_max/P95',new_PDE_runs=0)
 return electrical,details
