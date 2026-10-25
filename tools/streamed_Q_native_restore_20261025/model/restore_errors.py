"""Owner-called, chunked field diagnostics. Import performs no IO or array work.

NumPy and authenticated native arrays/ROI chunks are supplied by the owner.
No Q, solve, angular scan, field export or input authentication occurs here.
"""
CHUNK_CELLS=65536
ABS_TOL_V_M=1e-8
REL_TOL=2e-7
REFERENCE_FLOOR_V_M=1e-8
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
LAYERS=('sc','dermis','fat','muscle')

def _require(ok,message):
 if not ok:raise ValueError(message)
def _check(guard,deadline):
 import time
 _require(callable(guard),'Authenticated finite owner guard required');guard()
 if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Incomplete native restore diagnostics; no partial PASS')
def _shape(np,grid,n):
 _require(isinstance(grid,np.ndarray)and grid.shape==(n,5)and grid.dtype==np.dtype('float64')and 0<n<=800000,'Original native N by5 float grid [x_mm,y_mm,z_mm,layer,volume_m3]')
def _grid_chunk(np,grid,a,b):
 g=grid[a:b];layer=g[:,3];volume=g[:,4]
 _require(np.isfinite(g).all()and np.all(volume>0)and np.all((layer>=0)&(layer<4))and np.equal(layer,np.floor(layer)).all(),'Finite coordinates, positive native volumes and exact four layer labels')
 return g,layer,volume

def _weights_mode(weights):
 if weights is None:return 'absent'
 _require(type(weights)is dict,'Original six weight arrays or explicit streaming weight contract')
 if set(weights)=={'regions','chunk'}:
  _require(tuple(weights['regions'])==REGIONS and callable(weights['chunk']),'Exact six original regions and chunk(name,start,stop) provider');return 'streamed'
 _require(set(weights)==set(REGIONS),'Exact six original fractional-volume region keys');return 'arrays'
def _weight(np,weights,mode,name,a,b,volume):
 w=weights['chunk'](name,a,b)if mode=='streamed'else weights[name][a:b]
 _require(isinstance(w,np.ndarray)and w.shape==(b-a,)and w.dtype==np.dtype('float64')and np.isfinite(w).all()and np.all(w>=0),'Finite nonnegative original fractional volume chunk '+name)
 _require(np.all(w<=volume*(1+1e-12)+1e-25),'ROI weights cannot exceed native volume '+name)
 if name=='total':_require(np.allclose(w,volume,rtol=1e-12,atol=1e-25),'Original total weight equals actual grid volume')
 return w

def _norm(np,values):
 mag=np.abs(values)
 return np.hypot(np.hypot(mag[:,0],mag[:,1]),mag[:,2])
def _maximum():return dict(value=None,index=None,component=None,tied_cells=0)
def _maximum_update(np,state,values,first,use=None,components=False):
 if use is None:indices=np.arange(len(values))
 else:indices=np.flatnonzero(use)
 if not len(indices):return
 selected=values[indices];value=float(np.max(selected));mask=selected==value;flat=int(np.argmax(mask))
 if components:
  row,component=divmod(flat,values.shape[1]);ties=int(np.count_nonzero(np.any(mask,axis=1)))
 else:row=flat;component=None;ties=int(np.count_nonzero(mask))
 index=first+int(indices[row])
 if state['value']is None or value>state['value']:state.update(value=value,index=index,component=component,tied_cells=ties)
 elif value==state['value']:
  state['tied_cells']+=ties
  if index<state['index']:state.update(index=index,component=component)
def _maximum_finish(state,grid):
 if state['index']is None:return dict(value=None,native_cell_index=None,xyz_mm=None,exact_float_tied_cells=0)
 result=dict(value=state['value'],native_cell_index=state['index'],xyz_mm=[float(v)for v in grid[state['index'],:3]],exact_float_tied_cells=state['tied_cells'])
 if state['component']is not None:result['component']='xyz'[state['component']]
 return result

def _accumulator():return dict(volume=0.,positive=0,error2=0.,reference2=0.,maximum=_maximum())
def _accumulate(np,state,error,reference,weight,first):
 positive=weight>0
 if not np.any(positive):return
 state['volume']+=float(np.sum(weight));state['positive']+=int(np.count_nonzero(positive))
 state['error2']+=float(np.sum(weight*error*error));state['reference2']+=float(np.sum(weight*reference*reference))
 _maximum_update(np,state['maximum'],error,first,positive)
def _finish(np,state,grid):
 import math
 volume=state['volume']
 if not volume:return dict(status='unavailable_no_positive_volume',volume_m3=0.,positive_weight_cells=0)
 _require(all(math.isfinite(state[k])and state[k]>=0 for k in('volume','error2','reference2')),'Finite accumulated physical-volume L2 diagnostics')
 error=math.sqrt(state['error2']);reference=math.sqrt(state['reference2']);floor=REFERENCE_FLOOR_V_M*math.sqrt(volume);denominator=max(reference,floor)
 return dict(status='complete',volume_m3=volume,positive_weight_cells=state['positive'],
  absolute_vector_L2_V_m_sqrt_m3=error,reference_vector_L2_V_m_sqrt_m3=reference,
  absolute_vector_RMS_error_V_m=error/math.sqrt(volume),reference_vector_RMS_V_m=reference/math.sqrt(volume),
  relative_vector_L2=error/denominator,relative_denominator_V_m_sqrt_m3=denominator,
  relative_denominator_floor_V_m_sqrt_m3=floor,relative_floor_dominates=reference<=floor,
  maximum_vector_delta_V_m=_maximum_finish(state['maximum'],grid))

def compare_fields(np,newE,oldE,grid,weights=None,guard=None,deadline=None):
 """Return {summary,norm_delta_V_m}; the sole full new array is float64[N].

 Original arrays must be complex128 N by3; grid is the unchanged mm/native
 volume grid. weights is six float arrays, or {'regions':REGIONS,'chunk':
 provider(name,start,stop)}. Regions are the OUTER loop so the owner may cache
 just one original ROI array at a time. This helper authenticates no file.
 Component and vector tests are separate, both at atol1e-8 +rtol2e-7*old.
 Missing ROI weights never produce an overall restore PASS.
 """
 _check(guard,deadline)
 _require(isinstance(newE,np.ndarray)and isinstance(oldE,np.ndarray)and newE.shape==oldE.shape and newE.ndim==2 and newE.shape[1]==3 and newE.dtype==oldE.dtype==np.dtype('complex128'),'Matching original complex128 peak vector fields, no implicit full conversion')
 n=len(oldE);_shape(np,grid,n);mode=_weights_mode(weights);delta_norm=np.empty(n,dtype=np.float64)
 all_state=_accumulator();layers={name:_accumulator()for name in LAYERS};component_abs=_maximum();component_ratio=_maximum();vector_ratio=_maximum();component_relative=_maximum();vector_relative=_maximum()
 component_failures=component_failure_cells=vector_failures=0
 for a in range(0,n,CHUNK_CELLS):
  _check(guard,deadline);b=min(n,a+CHUNK_CELLS);g,layer,volume=_grid_chunk(np,grid,a,b);new=newE[a:b];old=oldE[a:b]
  _require(np.isfinite(new).all()and np.isfinite(old).all(),'Finite authenticated old and restored field chunks')
  difference=new-old;error=np.abs(difference);reference=np.abs(old);dn=_norm(np,difference);rn=_norm(np,old)
  _require(np.isfinite(error).all()and np.isfinite(dn).all()and np.isfinite(rn).all(),'Finite component and vector field differences')
  delta_norm[a:b]=dn;ctol=ABS_TOL_V_M+REL_TOL*reference;vtol=ABS_TOL_V_M+REL_TOL*rn;bad=error>ctol
  component_failures+=int(np.count_nonzero(bad));component_failure_cells+=int(np.count_nonzero(np.any(bad,axis=1)));vector_failures+=int(np.count_nonzero(dn>vtol))
  _maximum_update(np,component_abs,error,a,components=True);_maximum_update(np,component_ratio,error/ctol,a,components=True);_maximum_update(np,vector_ratio,dn/vtol,a)
  _maximum_update(np,component_relative,error/np.maximum(reference,REFERENCE_FLOOR_V_M),a,components=True);_maximum_update(np,vector_relative,dn/np.maximum(rn,REFERENCE_FLOOR_V_M),a)
  _accumulate(np,all_state,dn,rn,volume,a)
  for layer_id,name in enumerate(LAYERS):_accumulate(np,layers[name],dn,rn,volume*(layer==layer_id),a)
  del difference,error,reference,dn,rn,ctol,vtol,bad,new,old
 regions={}
 if mode!='absent':
  for name in REGIONS:
   state=_accumulator()
   for a in range(0,n,CHUNK_CELLS):
    _check(guard,deadline);b=min(n,a+CHUNK_CELLS);g,layer,volume=_grid_chunk(np,grid,a,b)
    w=_weight(np,weights,mode,name,a,b,volume);rn=_norm(np,oldE[a:b]);_require(np.isfinite(rn).all(),'Finite original reference norms for ROI diagnostics')
    _accumulate(np,state,delta_norm[a:b],rn,w,a);del w,rn
   regions[name]=_finish(np,state,grid)
 _check(guard,deadline);pointwise=component_failures==0 and vector_failures==0
 summary=dict(schema='task1-streamed-Q-native-field-errors-v1',status='complete'if mode!='absent'else'ROI_weights_unavailable',passed=pointwise and mode!='absent',
  pointwise_passed=pointwise,component_passed=component_failures==0,vector_passed=vector_failures==0,
  cells=n,components=3*n,component_failures=component_failures,component_failure_cells=component_failure_cells,vector_failure_cells=vector_failures,
  tolerances=dict(component='abs(new-old)<=atol+rtol*abs(old)',vector='norm(new-old)<=atol+rtol*norm(old)',absolute_V_m=ABS_TOL_V_M,relative=REL_TOL),
  relative_context_floor_V_m=REFERENCE_FLOOR_V_M,relative_context_is_not_an_additional_acceptance_gate=True,
  maximum_component_absolute_delta_V_m=_maximum_finish(component_abs,grid),maximum_component_tolerance_ratio=_maximum_finish(component_ratio,grid),maximum_vector_tolerance_ratio=_maximum_finish(vector_ratio,grid),
  maximum_component_relative_context=_maximum_finish(component_relative,grid),maximum_vector_relative_context=_maximum_finish(vector_relative,grid),
  global_volume_L2=_finish(np,all_state,grid),layers={name:_finish(np,s,grid)for name,s in layers.items()},regions=regions,
  ROI_weights_available=mode!='absent',ROI_provider_mode=mode,ROI_identity_authentication='External caller precondition, not verified by this pure helper',cross_ROI_algebra_recomputed=False,
  maximum_chunk_cells=CHUNK_CELLS,unbounded_full_complex_delta_allocated=False,full_new_arrays=['float64 per-cell norm_delta_V_m'],
  old_physical_gates_changed=False,angular_search_performed=False,native_restore_admission_granted=False,full_mesh_convergence_claimed=False)
 return dict(summary=summary,norm_delta_V_m=delta_norm)

def _bound_accumulator():return dict(volume=0.,positive=0,weighted=0.,squared=0.,maximum=_maximum())
def _bound_accumulate(np,state,value,weight,first):
 use=weight>0
 if not np.any(use):return
 state['volume']+=float(np.sum(weight));state['positive']+=int(np.count_nonzero(use));state['weighted']+=float(np.sum(weight*value));state['squared']+=float(np.sum(weight*value*value));_maximum_update(np,state['maximum'],value,first,use)
def _bound_finish(state,grid):
 import math
 if not state['volume']:return dict(status='unavailable_no_positive_volume',volume_m3=0.,positive_weight_cells=0)
 _require(all(math.isfinite(state[k])and state[k]>=0 for k in('volume','weighted','squared')),'Finite analytic bound diagnostics')
 return dict(status='complete',volume_m3=state['volume'],positive_weight_cells=state['positive'],mean_upper_bound_V_m=state['weighted']/state['volume'],RMS_upper_bound_V_m=math.sqrt(state['squared']/state['volume']),L2_upper_bound_V_m_sqrt_m3=math.sqrt(state['squared']),maximum_upper_bound_V_m=_maximum_finish(state['maximum'],grid))
def combine_carrier_bounds(np,delta0,delta1,grid,weights=None,guard=None,deadline=None):
 """Small conditional bounds only; never calculate actual AM or its directions.

 For two correctly paired carrier vector errors d0,d1, the absolute error of
 2min(|E0.u|,|E1.u|), and maxima over the SAME real-unit direction set, is
 <=2max(d0,d1). The two-carrier vector RMS error is <=hypot(d0,d1)/sqrt(2).
 Native ABI, phasor pairing, frequencies and input identity are caller duties.
 """
 _check(guard,deadline)
 _require(isinstance(delta0,np.ndarray)and isinstance(delta1,np.ndarray)and delta0.shape==delta1.shape and delta0.ndim==1 and delta0.dtype==delta1.dtype==np.dtype('float64'),'Two matching float64 per-cell carrier vector errors')
 n=len(delta0);_shape(np,grid,n);mode=_weights_mode(weights);all_states={k:_bound_accumulator()for k in('AM','RMS')};layers={name:{k:_bound_accumulator()for k in('AM','RMS')}for name in LAYERS}
 def values(a,b):
  d0=delta0[a:b];d1=delta1[a:b];_require(np.isfinite(d0).all()and np.isfinite(d1).all()and np.all(d0>=0)and np.all(d1>=0),'Finite nonnegative actual carrier vector errors')
  return dict(AM=2*np.maximum(d0,d1),RMS=np.hypot(d0,d1)/(2.**.5))
 for a in range(0,n,CHUNK_CELLS):
  _check(guard,deadline);b=min(n,a+CHUNK_CELLS);g,layer,volume=_grid_chunk(np,grid,a,b);v=values(a,b)
  for key,value in v.items():
   _bound_accumulate(np,all_states[key],value,volume,a)
   for layer_id,name in enumerate(LAYERS):_bound_accumulate(np,layers[name][key],value,volume*(layer==layer_id),a)
 regions={}
 if mode!='absent':
  for name in REGIONS:
   states={k:_bound_accumulator()for k in('AM','RMS')}
   for a in range(0,n,CHUNK_CELLS):
    _check(guard,deadline);b=min(n,a+CHUNK_CELLS);g,layer,volume=_grid_chunk(np,grid,a,b);w=_weight(np,weights,mode,name,a,b,volume);v=values(a,b)
    for key,value in v.items():_bound_accumulate(np,states[key],value,w,a)
    del w,v
   regions[name]={key:_bound_finish(state,grid)for key,state in states.items()}
 _check(guard,deadline)
 return dict(schema='task1-two-carrier-field-error-upper-bounds-v1',status='conditional_analytic_bounds_complete',
  formula=dict(AM='2*max(norm_delta_E0,norm_delta_E1)',RMS='hypot(norm_delta_E0,norm_delta_E1)/sqrt(2)'),
  global_bounds={key:_bound_finish(state,grid)for key,state in all_states.items()},layers={name:{key:_bound_finish(state,grid)for key,state in states.items()}for name,states in layers.items()},regions=regions,
  ROI_weights_available=mode!='absent',ROI_provider_mode=mode,maximum_chunk_cells=CHUNK_CELLS,full_bound_arrays_allocated=False,
  conditions='Two authenticated paired carrier fields in identical physical grid/peak-phasor ABI; AM maxima use identical direction sets',
  actual_AM_error_measured=False,angular_search_performed=False,acceptance_gate_applied=False,old_physical_gates_changed=False,full_mesh_convergence_claimed=False,native_restore_admission_granted=False)
