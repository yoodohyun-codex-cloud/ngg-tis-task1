"""Finite memory-separated recovery; exactly two P12 RHS, never repeat P23.5.

No I/O/scientific imports/arrays/solves occur on import. The registered root
owner calls build after the partial failure is published and authenticated.
The raw-PDE stage owns Q/profiles in a separate function scope and returns JSON
identities only. That scope ends and GC runs BEFORE any angular metric work.
Original failure/source/test evidence and all original arrays remain read-only.
"""
from __future__ import annotations
import gc,json,math,time
from pathlib import Path
import peripheral_screen as original
import recovery_inputs

SOURCE=Path('/dev/shm/task1-peripheral-recovery-20261025/source')
RUN=Path('/dev/shm/task1-peripheral-recovery-20261025-run')
MAX_FILE=80*1024**2

def require(ok,message):
 if not ok:raise ValueError(message)
def check(guard,deadline):return original.check(guard,deadline)
def digest(path):return original.digest(path)
def new_json(path,value):return original.new_json(path,value)
def cv(value):return original.cv(value)

def metadata_only(value):
 """Reject any array/solver/cache object leaking past the raw-stage boundary."""
 if value is None or type(value)in(str,bool,int):return True
 if type(value)is float:return math.isfinite(value)
 if isinstance(value,dict):return all(type(key)is str and metadata_only(item)for key,item in value.items())
 if isinstance(value,(list,tuple)):return all(metadata_only(item)for item in value)
 return False

def separated_stages(raw_stage,metrics_stage,collector=gc.collect):
 """The raw-stage frame MUST return before metrics, with JSON identities only."""
 artifacts=raw_stage();require(metadata_only(artifacts),'Raw stage leaked numerical arrays/Q/profiles; refuse metric execution');collector();return metrics_stage(artifacts)

def required_inputs(root_admission=None):
 inputs=recovery_inputs.make_spec(root_admission);refs=dict(inputs['input_sha256']);refs.update(original.required_inputs(inputs['catalog'],inputs['original_spec']['root_admission']));return refs

def make_spec(root_admission=None):
 inputs=recovery_inputs.make_spec(root_admission)
 return dict(schema='task1-memory-separated-peripheral-recovery-spec-v1',recovery_inputs=inputs,input_sha256=required_inputs(root_admission),expected_new_driven_RHS=2,expected_reused_saved_RHS=2,expected_new_metric_evaluations=2,expected_control_metric_aliases=2,expected_completed_conditions=4,requested_original_conditions=5,new_eigen_solves=0,
  memory_plan='Stage1 P12-only raw PDE/profile reconstruction withQ, writeeachcarrier independently and deletephi/E before nextcarrier. Exitstagefunction andcollect; Stage2 P23cached+P12savedfullmetrics with NOQ/profiles/solver retained. No RLIMIT_AS/resource-cap enlargement.',
  reused_candidate_id=inputs['reuse_candidate_id'],new_candidate_id=inputs['new_candidate_id'],blocked_recipe=inputs['blocked_recipe'],source_failure_preserved=True,original_failed_source_and_25_passed_test_evidence_preserved=True,old_physics_criteria_unchanged=True,candidate_adopted=False,Windows_saved_verified=False)

def _memory_status():
 result={}
 try:
  for line in Path('/proc/self/status').read_text().splitlines():
   if line.startswith(('VmRSS:','VmSize:','VmPeak:')):
    name,value,unit=line.split();result[name[:-1]+'_bytes']=int(value)*1024
 except OSError:result['proc_status']='unavailable'
 return result

def _load(np,descriptor,keys,guard,deadline):
 check(guard,deadline);p=Path(descriptor['path']);require(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size==descriptor['bytes']<=MAX_FILE and digest(p)==descriptor['SHA256'],'Authenticated original partial/recovery raw bytes before decode')
 with np.load(p,allow_pickle=False)as data:
  require(set(keys).issubset(data.files),'Actual saved array ABI lacks required field; never recompute missing P23 RHS implicitly');values={name:np.array(data[name],copy=True)for name in keys}
 require(all(np.isfinite(value).all()for value in values.values()),'Finite authenticated saved arrays');return values

def _new_P12_raw(np,context,out,guard,deadline):
 """Only this frame may own Q/profiles; return solely file/proof identities."""
 science=original.science;candidate=next(c for c in context['catalog']['candidates']if c['candidate_id']==context['new_candidate_id']);require(candidate['status']!='recipe_blocked'and candidate['reuse_first8_case_id']is None,'Exactly the previously uncomputed ready P12 geometry')
 phase,manifest=science.base._phase1_metadata();Q,cacheproof=science.base._load_cache(np,manifest,guard,deadline);phasepath=science.base.PHASE1/'arrays.npz';require(digest(phasepath)==science.base.PHASE1_ARRAYS_SHA,'Exact unchanged cached graph/eigen arrays')
 with np.load(phasepath,allow_pickle=False)as source:eigen=np.array(source['eigenvalues_per_m2'],copy=True);xy=np.array(source['XY_m'],copy=True);ij=np.array(source['ij'],copy=True)
 require(eigen.shape==(science.NXY,)and xy.shape==ij.shape==(science.NXY,2),'Actual original graph ordering ABI')
 import hashlib
 require(hashlib.sha256(xy.astype('<f8',copy=False).tobytes()).hexdigest()==phase['graph']['XY_float64_le_SHA256']and hashlib.sha256(ij.astype('<i4',copy=False).tobytes()).hexdigest()==phase['graph']['ij_int32_le_SHA256'],'Exact sameQ node ordering')
 _,_,zlist=science.base.kernel.f.make_grid(.5,8,[19,18,56]);zs=np.asarray(zlist,float);layers=np.repeat(np.arange(4),science.COUNTS);pads,cells,areas=science._mask(np,candidate,ij);directory=out/'rhs';directory.mkdir(exist_ok=True);raw={};proofs={}
 for frequency,output in((2000,0),(2010,1)):
  check(guard,deadline);gamma=[cv(v)for v in context['catalog']['gamma_by_frequency'][str(frequency)]];profile=science._profiles(np,Q,eigen,gamma,zs,guard,deadline);za=cv(context['catalog']['z_by_frequency'][str(frequency)]);solution=science._solve(np,Q,profile,pads,cells,areas,za,output,guard,deadline);proof=solution['proof'];proof.update(candidate_id=candidate['candidate_id'],frequency_Hz=frequency,recovery_new_RHS=True);proofpath=directory/(candidate['candidate_id']+'-'+str(frequency)+'-solve-proof.json');new_json(proofpath,proof)
  science.archive(np,directory/(candidate['candidate_id']+'-'+str(frequency)+'-surface-state.npz'),phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],modal_surface_coeff=solution['coeff']);require(proof['passed'],'New P12 physical gate failed; preserved iterate, never relax criteria')
  phi,E,interface=science._fields(np,Q,profile,solution,ij,layers,guard,deadline);artifact=science.archive(np,directory/(candidate['candidate_id']+'-'+str(frequency)+'-raw.npz'),phi_peak_V=phi,E_peak_V_m=E,interface_downward_J_peak_A_m2=interface,modal_surface_coeff=solution['coeff'],phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],contact_current_peak_A=solution['contact_current'],contact_normal_J_peak_A_m2=solution['contact_J'],contact_drop_peak_V=solution['contact_drop'],contact_pad=pads,contact_xy_index=cells,contact_area_m2=areas,layer_complex_power_W=solution['layer_power']);raw[str(frequency)]=artifact;proofs[str(frequency)]={**artifact,'path':str(proofpath),'bytes':proofpath.stat().st_size,'SHA256':digest(proofpath),'record':proof}
  new_json(out/('checkpoint-new-P12-'+str(frequency)+'.json'),dict(status='new_P12_raw_RHS_saved',new_driven_RHS=len(raw),reused_P23_RHS=0,angular_metric_evaluations=0,raw=artifact,memory=_memory_status()));del phi,E,interface,solution,profile
 for chunk in cacheproof:check(guard,deadline);require(digest(chunk['path'])==chunk['SHA256'],'Full Q cache SHA again after two new RHS')
 require(len(raw)==2,'Exactly two new P12 RHS and no P23 solve in raw stage')
 return dict(new_raw_by_frequency=raw,new_proofs_by_frequency=proofs,new_driven_RHS=2,no_new_eigen_solve=True,cache_manifest_SHA256=science.base.CACHE_MANIFEST_SHA)

def _record(proof_descriptor):
 p=Path(proof_descriptor['path']);require(digest(p)==proof_descriptor['SHA256'],'Exact saved passed source proof');value=original.read_json(p,proof_descriptor['SHA256']);require(value.get('passed')is True,'Saved source proof must pass unchanged physical gates');return value

def _metrics_without_Q(np,context,new_raw,out,guard,deadline):
 """Load only saved fields/contact arrays; no Q, profiles, eigendata or solver."""
 import screen_metrics
 import allocation_electrical
 common=_load(np,context['common_grid_ROI'],['grid']+[k+'_volume_weight_m3'for k in screen_metrics.REGIONS],guard,deadline);grid=common.pop('grid');require(grid.shape==(793860,5),'Exact published common evaluation grid');weights={k:common[k+'_volume_weight_m3']for k in screen_metrics.REGIONS};catalog=context['catalog'];rows=[];cdir=out/'candidates';cdir.mkdir(exist_ok=True)
 for cid,descriptor in context['control_alias_proofs'].items():
  require(digest(descriptor['path'])==descriptor['SHA256'],'Exact original completed control alias metadata');row=original.read_json(descriptor['path'],descriptor['SHA256']);require(row['candidate_id']==cid and row['actual_new_RHS']==0 and row['actual_new_metric_evaluations']==0,'Control remains complete immutable alias');new_json(cdir/(cid+'-alias-proof.json'),row);rows.append(row)
 baseline=next(r['metrics']for r in rows if r['candidate_id'].startswith('B0-'));metrics_count=0;raw_records={}
 for cid,rawmap,proofmap,reused in((context['reuse_candidate_id'],context['reuse_raw_by_frequency'],context['reuse_proofs_by_frequency'],True),(context['new_candidate_id'],new_raw['new_raw_by_frequency'],new_raw['new_proofs_by_frequency'],False)):
  fields=[];raw=[];proofs=[]
  for f in(2000,2010):
   descriptor=rawmap[str(f)];data=_load(np,descriptor,['E_peak_V_m','source_current_peak_A','contact_normal_J_peak_A_m2','contact_drop_peak_V','contact_area_m2','contact_pad','contact_xy_index','layer_complex_power_W'],guard,deadline);require(data['E_peak_V_m'].shape==(len(grid),3),'Same saved fullcomplexvector ABI');fields.append(data['E_peak_V_m']);raw.append(data);proofs.append(_record(proofmap[str(f)]));raw_records[cid+'-'+str(f)]=dict(descriptor)
  electrical,spectral=allocation_electrical.synthesize(np,raw[0],raw[1],proofs[0],proofs[1],1.,1.)
  # The copied original metric normalizer has its original scalar-only ABI.
  # Keep exact signed powers in separate spectral metadata rather than passing
  # complex dict/list powers through its float suffix rule.
  legacy=('source_Vpp_each','source_current_RMS_by_output_A','sum_output_current_RMS_A_bookkeeping','source_power_W','layers_power_W','SC_power_W','skin_power_W','contact_power_W','source_resistor_power_W','contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V')
  scalar_electrical={key:electrical[key]for key in legacy};result=screen_metrics.evaluate(np,grid,weights,fields[0],fields[1],np.asarray([cv(v)for v in catalog['gamma_by_frequency']['2000']]),np.asarray([cv(v)for v in catalog['gamma_by_frequency']['2010']]),scalar_electrical,guard,deadline);metrics_count+=1
  candidate=next(c for c in catalog['candidates']if c['candidate_id']==cid);record=dict(candidate_id=cid,status='saved_P23_metric_recovery_computed'if reused else'new_P12_geometry_and_metrics_computed',geometry=candidate,source_physics_proofs=proofs,metrics=result['summary'],normalizations=screen_metrics.normalize(result['summary'],baseline),per_frequency_signed_circuit=spectral,scalar_arrays=original.science.archive(np,cdir/(cid+'-scalars.npz'),**result['arrays']),actual_new_RHS=0 if reused else 2,previous_published_RHS_reused=2 if reused else 0,actual_new_metric_evaluations=1,Q_or_solver_resident_during_metrics=False,candidate_adopted=False);new_json(cdir/(cid+'-summary.json'),record);rows.append(record);new_json(out/('checkpoint-'+cid+'-metrics.json'),dict(status='recovery_metrics_complete_without_Q',completed_new_metric_evaluations=metrics_count,reused_saved_RHS=2,new_driven_RHS=2,memory=_memory_status()));del fields,raw,result
 require(metrics_count==2 and len(rows)==4,'Two full new metric evaluations plus two original control aliases')
 return dict(candidates=rows,raw_artifacts=raw_records,completed_conditions=len(rows),actual_new_driven_RHS=2,actual_reused_saved_RHS=2,actual_new_metric_evaluations=2,actual_alias_conditions=2)

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(spec==make_spec(spec['recovery_inputs'].get('root_admission'))and callable(guard),'Exact positive partial-R-bound recovery specification');check(guard,deadline_monotonic);out=Path(output_dir or RUN);require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink()and out.parent==Path('/dev/shm'),'Unique root-created recovery output')
 import numpy as np
 context=spec['recovery_inputs'];before=_memory_status();new_json(out/'memory-plan.json',dict(plan=spec['memory_plan'],before=before,new_P23_RHS=0,new_P12_RHS=2,no_RLIMIT_AS_override=True))
 def raw_stage():return _new_P12_raw(np,context,out,guard,deadline_monotonic)
 def collect():
  collected=gc.collect();new_json(out/'Q-release-boundary.json',dict(status='raw_stage_frame_returned_Q_and_profiles_out_of_scope',retained_stage_return='JSON identities only, numerical objects rejected',collected=collected,memory=_memory_status(),before=before,angular_metric_evaluations_started=0,no_new_eigen_solve=True))
 def metric_stage(artifacts):
  check(guard,deadline_monotonic);new_json(out/'new-P12-raw-identities.json',artifacts);return _metrics_without_Q(np,context,artifacts,out,guard,deadline_monotonic)
 result=separated_stages(raw_stage,metric_stage,collect);check(guard,deadline_monotonic)
 summary=dict(schema='task1-memory-separated-peripheral-recovery-result-v1',status='peripheral_recovery_computed_without_P23_PDE_repeat',spec=spec,**result,requested_original_conditions=5,recipe_blockers=[context['blocked_recipe']],ROI_receipt=context['ROI_receipt'],memory_plan=spec['memory_plan'],source_failure_preserved=True,old_25_passed_tests_and_MemoryError_evidence_preserved=True,new_P23_RHS=0,new_P12_RHS=2,new_eigen_solves=0,holds=context['original_spec']['holds'],candidate_adopted=False,Windows_saved_verified=False)
 return dict(summary=summary,arrays={})
