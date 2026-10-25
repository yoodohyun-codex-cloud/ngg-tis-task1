"""Memory-separated actual CEM comparison of two authenticated donor mixtures.

No I/O, scientific imports, arrays or solves occur on import. Root alone calls
build after positive admission binds the completed recovery publication. Only
footprints are mixed; existing fields are NEVER combined as a new geometry.
Exactly four new driven RHS are solved. Two control metrics/raw/scalars remain
immutable aliases. Q and profiles leave scope before any angular metric work.
"""
from __future__ import annotations
import copy,gc,math,time
from pathlib import Path
import frozen_design_screen as science
import mixed_catalog

SOURCE=Path('/dev/shm/task1-mixed-fourpad-r2-20261025/source')
RUN=Path('/dev/shm/task1-mixed-fourpad-r2-20261025-run')
IDS=('B0-square15-c10-diagonal','P23p5-peripheral-polyomino225','M_Speriph_Rsquare','M_Ssquare_Rperiph')
MAX_FILE=80*1024**2
LEGACY_ELECTRICAL=('source_Vpp_each','source_current_RMS_by_output_A','sum_output_current_RMS_A_bookkeeping','source_power_W','layers_power_W','SC_power_W','skin_power_W','contact_power_W','source_resistor_power_W','contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V')

def require(ok,message):
 if not ok:raise ValueError(message)
def check(guard,deadline):return science.check(guard,deadline)
def digest(path):return science.digest(path)
def new_json(path,value):return science.new_json(path,value)
def cv(value):return science.cv(value)
def _admission(value=None):
 if value is not None:return value
 path=SOURCE/'root-admission.json';return science.read_json(path)if path.is_file()else None
def metadata_only(value):
 if value is None or type(value)in(str,bool,int):return True
 if type(value)is float:return math.isfinite(value)
 if isinstance(value,dict):return all(type(k)is str and metadata_only(v)for k,v in value.items())
 if isinstance(value,(list,tuple)):return all(metadata_only(v)for v in value)
 return False
def separated_stages(raw_stage,metric_stage,collector=gc.collect):
 artifacts=raw_stage();require(metadata_only(artifacts),'Raw stage leaked Q/arrays/solver beyond its frame');collector();return metric_stage(artifacts)
def _memory():
 result={}
 try:
  for line in Path('/proc/self/status').read_text().splitlines():
   if line.startswith(('VmRSS:','VmSize:','VmPeak:')):
    key,value,_=line.split();result[key[:-1]+'_bytes']=int(value)*1024
 except OSError:result['proc_status']='unavailable'
 return result

def required_inputs(catalog_spec=None,root_admission=None):
 admission=_admission(root_admission);catalog=mixed_catalog.make_spec(RUN,admission)if catalog_spec is None else catalog_spec;refs=dict(catalog['input_pins']);refs.update(mixed_catalog.required_inputs(None,admission));refs.update(science.required_inputs(catalog));return refs

def make_spec(catalog_spec=None,root_admission=None):
 admission=_admission(root_admission);catalog=mixed_catalog.make_spec(RUN,admission)if catalog_spec is None else catalog_spec
 require(tuple(row['candidate_id']for row in catalog['candidates'])==IDS and catalog['frequencies']==[2000,2010]and catalog['source_allocation_amplitudes']==[1.,1.],'Four fixed equal-voltage donor-group conditions')
 mixed_catalog.validate_admission(admission);require(catalog['root_admission']==admission,'Catalog and model share the actual recovery-bound root selection')
 require(catalog['provisional_field']['derived_field_version']==science.provisional_field.VERSION,'Identical donor/new field reconstruction ABI, no control metric substitution')
 return dict(schema='task1-mixed-fourpad-screen-spec-v1',catalog=catalog,root_admission=admission,input_sha256=required_inputs(catalog,admission),expected_completed_conditions=4,expected_new_driven_RHS=4,expected_new_metric_evaluations=2,expected_alias_conditions=2,new_eigen_solves=0,
  raw_memory_plan='One Q-owning frame solves allnewmixedRHS onecarrier/time andwritesfullraw; returnsONLYJSONidentities, thenGC beforeANYangularmetrics. No cap/RLIMIT_AS override.',
  footprint_definition='S group means physicalpads0/1, including the inactive outputpad at each carrier; R group means physicalpads2/3 at commonGND. Mix donor contact-cell sets only, NEVER linear-combine old geometry field solutions.',
  interpretation='Within this fixed numerical model compare moving the two outputpad footprints versus moving the common-ground return footprints; does not establish isolated anatomy/physiology causality or validated depth focality.',
  holds=dict(old_5percent_interface_failures_preserved=True,old_XY_contact_burden_failures_preserved=True,full_SC_XY_bulk_edge_contact_convergence=False,material_contact_hardware_or_experiment_validated=False,global_SC_hotspot_not_cleared=True,provisional_screen_only=True),candidate_adopted=False,Windows_saved_verified=False)

def _load(np,descriptor,keys,guard,deadline):
 check(guard,deadline);path=Path(descriptor['path']);require(path.is_file()and path==path.resolve()and not path.is_symlink()and path.stat().st_size==descriptor['bytes']<=MAX_FILE and digest(path)==descriptor['SHA256'],'Actual saved new mixed raw SHA before decode')
 with np.load(path,allow_pickle=False)as saved:
  require(set(keys).issubset(saved.files),'Saved field ABI unavailable; no implicit solve fallback');value={key:np.array(saved[key],copy=True)for key in keys}
 require(all(np.isfinite(a).all()for a in value.values()),'All saved mixed fields finite');return value

def _raw_new_geometries(np,catalog,out,guard,deadline):
 phase,manifest=science.base._phase1_metadata();Q,cacheproof=science.base._load_cache(np,manifest,guard,deadline);phasepath=science.base.PHASE1/'arrays.npz';require(digest(phasepath)==science.base.PHASE1_ARRAYS_SHA,'Exact original graph/eigen arrays')
 with np.load(phasepath,allow_pickle=False)as source:eigen=np.array(source['eigenvalues_per_m2'],copy=True);xy=np.array(source['XY_m'],copy=True);ij=np.array(source['ij'],copy=True)
 require(eigen.shape==(science.NXY,)and xy.shape==ij.shape==(science.NXY,2),'Same cached coarse graph dimensions')
 import hashlib
 require(hashlib.sha256(xy.astype('<f8',copy=False).tobytes()).hexdigest()==phase['graph']['XY_float64_le_SHA256']and hashlib.sha256(ij.astype('<i4',copy=False).tobytes()).hexdigest()==phase['graph']['ij_int32_le_SHA256'],'Exact Q row ordering')
 faces,_,zlist=science.base.kernel.f.make_grid(.5,8,[19,18,56]);faces=np.asarray(faces,float);zs=np.asarray(zlist,float);layers=np.repeat(np.arange(4),science.COUNTS);rawdir=out/'rhs';rawdir.mkdir(exist_ok=True);artifacts={};proofs={};count=0
 for candidate in catalog['candidates'][2:]:
  cid=candidate['candidate_id'];pads,cells,areas=science._mask(np,candidate,ij)
  for frequency,output in((2000,0),(2010,1)):
   check(guard,deadline);profile=science._profiles(np,Q,eigen,[cv(v)for v in catalog['gamma_by_frequency'][str(frequency)]],zs,guard,deadline);za=cv(catalog['z_by_frequency'][str(frequency)]);solution=science._solve(np,Q,profile,pads,cells,areas,za,output,guard,deadline);proof=solution['proof'];proof.update(candidate_id=cid,frequency_Hz=frequency);key=cid+'-'+str(frequency);proofpath=rawdir/(key+'-solve-proof.json');new_json(proofpath,proof);science.archive(np,rawdir/(key+'-surface-state.npz'),phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],modal_surface_coeff=solution['coeff']);require(proof['passed'],'Mixed CEM physical gate failed; surface/proof retained')
   phi,E,interface=science._fields(np,Q,profile,solution,ij,layers,guard,deadline);artifacts[key]=science.archive(np,rawdir/(key+'-raw.npz'),phi_peak_V=phi,E_peak_V_m=E,interface_downward_J_peak_A_m2=interface,modal_surface_coeff=solution['coeff'],phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],contact_current_peak_A=solution['contact_current'],contact_normal_J_peak_A_m2=solution['contact_J'],contact_drop_peak_V=solution['contact_drop'],contact_pad=pads,contact_xy_index=cells,contact_area_m2=areas,layer_complex_power_W=solution['layer_power']);proofs[key]=dict(path=str(proofpath),SHA256=digest(proofpath),bytes=proofpath.stat().st_size);count+=1;new_json(out/('checkpoint-'+key+'-raw.json'),dict(status='new_mixed_raw_RHS_saved',actual_new_driven_RHS=count,actual_new_metric_evaluations=0,memory=_memory()));del phi,E,interface,profile,solution
 for item in cacheproof:check(guard,deadline);require(digest(item['path'])==item['SHA256'],'Original cached Q full SHA again after raw stage')
 require(count==4,'Exactly four new mixed RHS, no control solve')
 # The fixed physical grid/ROI is already authenticated from the first batch.
 # Return its identity rather than allocating/duplicating a grid while Q lives.
 return dict(raw_artifacts=artifacts,proofs=proofs,common_grid=catalog['common_grid_ROI'],actual_new_driven_RHS=4,new_eigen_solves=0)

def _metrics_without_Q(np,catalog,artifacts,out,guard,deadline):
 import screen_metrics,allocation_electrical
 common=_load(np,artifacts['common_grid'],['grid']+[key+'_volume_weight_m3'for key in screen_metrics.REGIONS],guard,deadline);grid=common.pop('grid');require(grid.shape==(793860,5),'Same complete physical grid');weights={key:common[key+'_volume_weight_m3']for key in screen_metrics.REGIONS};roi=catalog['ROI_receipt'];new_json(out/'ROI-receipt.json',roi);new_json(out/'common-grid-ROI-alias.json',artifacts['common_grid']);rows=[];cdir=out/'candidates';cdir.mkdir(exist_ok=True)
 for candidate in catalog['candidates'][:2]:
  require(candidate['cached_alias_only']is True,'Control must remain immutable full alias');source=copy.deepcopy(candidate['source_control_record']);row=dict(candidate_id=candidate['candidate_id'],status='immutable_full_control_alias',geometry=candidate,metrics=source['metrics'],normalizations=source['normalizations'],scalar_arrays=copy.deepcopy(candidate['source_scalar']),original_raw_by_frequency=copy.deepcopy(candidate['source_raw_by_frequency']),source_record=source,actual_new_driven_RHS=0,actual_new_metric_evaluations=0,no_control_field_reconstruction=True,no_control_angle_recalculation=True,candidate_adopted=False);new_json(cdir/(candidate['candidate_id']+'-alias-proof.json'),row);rows.append(row)
 baseline=rows[0]['metrics'];new_metrics=0
 for candidate in catalog['candidates'][2:]:
  cid=candidate['candidate_id'];raw=[];proofs=[]
  for frequency in(2000,2010):
   key=cid+'-'+str(frequency);data=_load(np,artifacts['raw_artifacts'][key],['E_peak_V_m','source_current_peak_A','contact_normal_J_peak_A_m2','contact_drop_peak_V','contact_area_m2','contact_pad','contact_xy_index','layer_complex_power_W'],guard,deadline);require(data['E_peak_V_m'].shape==(len(grid),3),'Complete coherent new field vectors');raw.append(data);proof_descriptor=artifacts['proofs'][key];require(digest(proof_descriptor['path'])==proof_descriptor['SHA256'],'New physics proof identity');proof=science.read_json(proof_descriptor['path'],proof_descriptor['SHA256']);require(proof['passed']is True,'New physical gates unchanged');proofs.append(proof)
  electrical,spectral=allocation_electrical.synthesize(np,raw[0],raw[1],proofs[0],proofs[1],1.,1.);scalar_keys=('source_Vpp_each','source_current_RMS_by_output_A','sum_output_current_RMS_A_bookkeeping','source_power_W','layers_power_W','SC_power_W','skin_power_W','contact_power_W','source_resistor_power_W','contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V');e={key:electrical[key]for key in scalar_keys};result=screen_metrics.evaluate(np,grid,weights,raw[0]['E_peak_V_m'],raw[1]['E_peak_V_m'],np.asarray([cv(v)for v in catalog['gamma_by_frequency']['2000']]),np.asarray([cv(v)for v in catalog['gamma_by_frequency']['2010']]),e,guard,deadline);new_metrics+=1;row=dict(candidate_id=cid,status='new_mixed_geometry_computed_unadopted',geometry=candidate,source_physics_proofs=proofs,metrics=result['summary'],normalizations=screen_metrics.normalize(result['summary'],baseline),per_frequency_signed_circuit=spectral,scalar_arrays=science.archive(np,cdir/(cid+'-scalars.npz'),**result['arrays']),actual_new_driven_RHS=2,actual_new_metric_evaluations=1,Q_resident_during_metrics=False,candidate_adopted=False);new_json(cdir/(cid+'-summary.json'),row);rows.append(row);new_json(out/('checkpoint-'+cid+'-metrics.json'),dict(status='new_mixed_metrics_without_Q',actual_new_metric_evaluations=new_metrics,memory=_memory()));del raw,result,data
 require(len(rows)==4 and new_metrics==2,'Two immutable controls and exactly two new metric evaluations')
 return dict(candidates=rows,ROI_receipt=roi,completed_conditions=4,actual_new_metric_evaluations=2,actual_alias_conditions=2)

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(spec==make_spec(spec['catalog'],spec['root_admission'])and callable(guard),'Exact positive root-selected mixed footprint specification');check(guard,deadline_monotonic);out=Path(output_dir or RUN);require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink()and out.parent==Path('/dev/shm'),'Unique owner-created mixed run')
 import numpy as np
 catalog=spec['catalog'];before=_memory();new_json(out/'memory-plan.json',dict(plan=spec['raw_memory_plan'],before=before,no_RLIMIT_AS_override=True))
 def raw_stage():return _raw_new_geometries(np,catalog,out,guard,deadline_monotonic)
 def collect():
  count=gc.collect();new_json(out/'Q-release-boundary.json',dict(status='raw_frame_exited_Q_profiles_out_of_scope',retained_return='JSON identities only',collected=count,before=before,after=_memory(),angular_metrics_started=0))
 raw_holder={}
 def metric_stage(artifacts):
  raw_holder.update(artifacts);new_json(out/'raw-stage-identities.json',artifacts);return _metrics_without_Q(np,catalog,artifacts,out,guard,deadline_monotonic)
 result=separated_stages(raw_stage,metric_stage,collect);check(guard,deadline_monotonic)
 return dict(summary=dict(schema='task1-mixed-fourpad-screen-result-v1',status='mixed_fourpad_screen_computed_unadopted',spec=spec,**result,actual_new_driven_RHS=4,raw_artifacts=raw_holder['raw_artifacts'],new_eigen_solves=0,no_control_PDE_field_or_angle_repeat=True,memory_plan=spec['raw_memory_plan'],holds=spec['holds'],candidate_adopted=False,Windows_saved_verified=False),arrays={})
