"""Unadmitted next physical four-pad family, using the cached coarse DtN graph.

No I/O, array construction, scientific import or solve occurs on import. Root
selects one finite batch only after the actual allocation result is verified.
Two original controls are full metric/raw/scalar aliases; they are never solved
or field-reconstructed here. New masks are immutable pixel unions, not smooth
annular sectors, and all previous uncertainty/convergence holds remain active.
"""
from __future__ import annotations
import copy,hashlib,importlib.util,json,math,time
from pathlib import Path
import frozen_design_screen as science

SOURCE=Path('/dev/shm/task1-peripheral-fourpad-20261025/source')
RUN=Path('/dev/shm/task1-peripheral-fourpad-20261025-run')
FIRST8=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
FIRST8_COMMIT='4d6207caa60ae16ab7a7e997022ac72653b97ec3'
FIRST8_PUB_SHA='d20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159'
IDS=('B0-square15-c10-diagonal','G1-square12-c10-diagonal','P24-peripheral-polyomino225','P23p5-peripheral-polyomino225','P12-square-c11p5-diagonal')
MAX_FILE=80*1024**2

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(path):return science.digest(path)
def read_json(path,expected=None):return science.read_json(path,expected)
def new_json(path,value):return science.new_json(path,value)
def check(guard,deadline):return science.check(guard,deadline)
def cv(value):return science.cv(value)

def _catalog(value=None):
 if value is not None:return value
 module_spec=importlib.util.spec_from_file_location('peripheral_catalog_source',SOURCE/'catalog.py');module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module);return module.make_spec(RUN)

def _admission(value=None):
 if value is not None:return value
 path=SOURCE/'root-admission.json';return read_json(path)if path.is_file()else None

def _first8():
 pubpath=FIRST8/'result-publication/result-publication.json';publication=read_json(pubpath,FIRST8_PUB_SHA);require(publication['status']=='published_readback_verified'and publication['commit']==FIRST8_COMMIT,'Completed original first8 publication')
 def proof(path,expected=None):
  p=Path(path);relative=p.relative_to(FIRST8).as_posix();matches=[v for target,v in publication['files'].items()if target.endswith('/'+relative)];require(len(matches)==1 and matches[0]['readback_passed']is True,'Direct first8 original readback proof');sha=matches[0]['SHA256'];require(expected is None or sha==expected,'Original control metadata SHA conflict');return sha
 summarypath=FIRST8/'summary.json';summary=read_json(summarypath,proof(summarypath));require(summary['status']=='provisional_eight_layout_screen_computed_unadopted'and summary['completed_candidates']==8,'First8 actually completed, not prepared source');refs={str(pubpath):FIRST8_PUB_SHA,str(summarypath):proof(summarypath)}
 controls={}
 for cid in IDS[:2]:
  row=next(r for r in summary['candidates']if r['candidate_id']==cid);require(all(p['passed']is True for p in row['source_physics_proofs']),'Original control physics proof');refs[row['scalar_arrays']['path']]=proof(row['scalar_arrays']['path'],row['scalar_arrays']['SHA256'])
  for f in(2000,2010):
   artifact=summary['raw_artifacts'][cid+'-'+str(f)];refs[artifact['path']]=proof(artifact['path'],artifact['SHA256'])
  controls[cid]=row
 return summary,controls,refs

def validate_admission(admission):
 require(admission is not None and admission.get('schema')=='task1-peripheral-fourpad-root-admission-v1'and admission.get('status')=='selected_finite_peripheral_screen'and admission.get('root_selected')is True,'Separate root finite selection after actual allocation results')
 require(admission.get('maximum_new_RHS')==6 and admission.get('maximum_new_metric_evaluations')==3 and admission.get('control_metric_aliases')==2 and admission.get('physical_pads')==4 and admission.get('independent_outputs')==2 and admission.get('candidate_adopted')is False,'Exact prospective peripheral family scope')
 require(admission.get('source_allocation_amplitudes')==[1.,1.],'Equal raw voltage geometry screen; unequal future allocation needs separately matched control metrics')
 require(isinstance(admission.get('decision_basis'),str)and len(admission['decision_basis'])>0,'Actual previous-result rationale required, no guaranteed improvement claim')
 prior=Path(admission['current_allocation_run']);pubpath=prior/'result-publication/result-publication.json';publication=read_json(pubpath,admission['current_allocation_publication_sha256']);require(publication['status']=='published_readback_verified'and publication['commit']==admission['current_allocation_result_commit']and len(publication['commit'])==40,'Actual current-allocation result publication')
 matches=[r for target,r in publication['files'].items()if target.endswith('/summary.json')];require(len(matches)==1 and matches[0]['readback_passed']is True,'Direct current-allocation summary readback proof');summarypath=prior/'summary.json';summary=read_json(summarypath,matches[0]['SHA256']);require(summary['status']=='current_allocation_cached_search_computed'and summary['completed_conditions']==10 and summary['actual_new_metric_evaluations']==8 and summary['actual_alias_conditions']==2 and summary['new_PDE_RHS']==0,'Actually completed allocation search before next geometry selection')
 return {str(pubpath):admission['current_allocation_publication_sha256'],str(summarypath):matches[0]['SHA256']}

def required_inputs(catalog_spec=None,root_admission=None):
 catalog=_catalog(catalog_spec);refs=science.required_inputs(catalog);_,_,controlrefs=_first8();refs.update(controlrefs);admission=_admission(root_admission)
 if admission is not None:
  refs.update(validate_admission(admission));path=SOURCE/'root-admission.json'
  if path.is_file():refs[str(path)]=digest(path)
 return refs

def make_spec(catalog_spec=None,root_admission=None):
 catalog=_catalog(catalog_spec);admission=_admission(root_admission);require(tuple(r['candidate_id']for r in catalog['candidates'])==IDS and catalog['frequencies']==[2000,2010]and catalog['source_allocation_amplitudes']==[1.,1.],'Frozen five equal-voltage recipes; no automatic condition extension')
 require(all(row['status']!='recipe_blocked'for row in catalog['candidates'][:2]),'Required original controls must have exact ready geometry')
 ready=[row['candidate_id']for row in catalog['candidates'][2:]if row['status']!='recipe_blocked'];blocked=[dict(candidate_id=row['candidate_id'],blocker=row['blocker'])for row in catalog['candidates'][2:]if row['status']=='recipe_blocked']
 return dict(schema='task1-proposed-peripheral-fourpad-screen-spec-v1',catalog=catalog,root_admission=admission,input_sha256=required_inputs(catalog,admission),maximum_conditions=5,maximum_new_RHS=6,maximum_new_metric_evaluations=3,expected_new_geometries=len(ready),ready_new_candidate_ids=ready,expected_new_driven_RHS=2*len(ready),expected_new_metric_evaluations=len(ready),expected_completed_conditions=2+len(ready),prepared_recipe_blockers=blocked,control_metric_aliases=2,new_eigen_solves=0,raw_source_Vpp_by_frequency={'2000':1.,'2010':1.},source_only_unadmitted=admission is None,
  recipe_blocker_policy='Freeze READY subset before source publication; preserve failed exact-count/connectivity recipes as blocked evidence. Only the prospectively frozen whole-orbit selection rule may select cells; no orbit splitting, smoothing, widening, area renormalization or post-count repair. Nready0 is an explicit pre-PDE blocker; Nready>0 runs the declared READY subset.',
  control_policy='B0/G1 copy exact original metrics and reference original scalar/raw SHA identities; no control E reconstruction, angular search or PDE rerun',
  physical_gates=dict(science.base.LIMITS),geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001,provisional_field=science.provisional_field.provenance(),
  source_convention='Original activeout0@2000/activeout1@2010 .5Vpeak/1Vpp before50ohm; other idealoutput0Vthrough50ohm; physicalpad2/3 common0V; exactlytwo outputs',
  comparison_scope=catalog['comparison_scope'],holds=dict(old_5percent_interface_failures_preserved=True,old_XY_contact_burden_failures_preserved=True,full_SC_XY_bulk_edge_contact_convergence=False,material_contact_hardware_or_experiment_validated=False,provisional_screen_only=True),candidate_adopted=False,Windows_saved_verified=False)

def _control_alias(candidate,catalog,original,source_summary):
 cid=candidate['candidate_id'];require(candidate['reuse_first8_case_id']==cid and candidate['mask_sha256']==original['geometry']['mask_sha256'],'Exact immutable control mask, no geometry substitution');old=source_summary['spec'];require(old['catalog']['gamma_by_frequency']==catalog['gamma_by_frequency']and old['catalog']['z_by_frequency']==catalog['z_by_frequency']and old['provisional_field']['derived_field_version']==science.provisional_field.VERSION,'Exact control material/contact/field ABI')
 require(old['catalog']['common_ROI']==catalog['common_ROI']and old['catalog']['grid']==catalog['grid']and old['catalog']['drives']==catalog['drives']and old['catalog']['source_resistance_ohm']==catalog['source_resistance_ohm']==50.,'Exact original control ROI/grid/drive/resistor definitions, not merely matching mask')
 return dict(candidate_id=cid,status='immutable_original_control_alias',geometry=candidate,source_physics_proofs=copy.deepcopy(original['source_physics_proofs']),metrics=copy.deepcopy(original['metrics']),normalizations=copy.deepcopy(original['normalizations']),scalar_arrays={**copy.deepcopy(original['scalar_arrays']),'fixed_commit':FIRST8_COMMIT,'kind':'immutable_original_scalar_alias'},original_raw={str(f):copy.deepcopy(source_summary['raw_artifacts'][cid+'-'+str(f)])for f in(2000,2010)},actual_new_RHS=0,actual_new_metric_evaluations=0,no_field_reconstruction=True,no_angular_recalculation=True,candidate_adopted=False)

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(spec==make_spec(spec['catalog'],spec['root_admission'])and callable(guard),'Exact selected immutable peripheral spec');validate_admission(spec['root_admission']);require(spec['expected_new_geometries']>0,'All three prospective geometry recipes are blocked; preserve prepared blockers and select a new source recipe before any PDE');check(guard,deadline_monotonic);out=Path(output_dir or RUN);require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink()and out.parent==Path('/dev/shm'),'Unique root-owned output')
 import numpy as np
 import screen_metrics
 import sys
 sys.path.insert(0,'/workspace/ngg-tis-task1/tis-java')
 from selectivity_volume import native_region_weights
 source_summary,original_controls,_=_first8();catalog=spec['catalog'];records=[];blocked=[];raw_artifacts={};actual_RHS=new_metrics=0;rawdir=out/'rhs';rawdir.mkdir(exist_ok=True);cdir=out/'candidates';cdir.mkdir(exist_ok=True)
 for candidate in catalog['candidates'][:2]:
  require(candidate['status']!='recipe_blocked','A required control recipe is blocked');record=_control_alias(candidate,catalog,original_controls[candidate['candidate_id']],source_summary);new_json(cdir/(candidate['candidate_id']+'-alias-proof.json'),record);records.append(record)
 baseline=records[0]['metrics'];phase,manifest=science.base._phase1_metadata();Q,cacheproof=science.base._load_cache(np,manifest,guard,deadline_monotonic);phasepath=science.base.PHASE1/'arrays.npz';require(digest(phasepath)==science.base.PHASE1_ARRAYS_SHA,'Exact original graph/eigen arrays')
 with np.load(phasepath,allow_pickle=False)as saved:eigen=np.array(saved['eigenvalues_per_m2'],copy=True);xy=np.array(saved['XY_m'],copy=True);ij=np.array(saved['ij'],copy=True)
 require(eigen.shape==(science.NXY,)and xy.shape==ij.shape==(science.NXY,2),'Fixed cached graph dimensions');require(hashlib.sha256(xy.astype('<f8',copy=False).tobytes()).hexdigest()==phase['graph']['XY_float64_le_SHA256']and hashlib.sha256(ij.astype('<i4',copy=False).tobytes()).hexdigest()==phase['graph']['ij_int32_le_SHA256'],'Exact original graph ordering')
 faces,_,zlist=science.base.kernel.f.make_grid(.5,8,[19,18,56]);faces=np.asarray(faces,float);zs=np.asarray(zlist,float);layers=np.repeat(np.arange(4),science.COUNTS);grid=np.column_stack((np.tile(xy[:,0]*1000,len(zs)),np.tile(xy[:,1]*1000,len(zs)),np.repeat(zs*1000,science.NXY),np.repeat(layers,science.NXY),np.repeat(science.H**2*np.diff(faces),science.NXY)))
 weights,roi=native_region_weights({key:grid[:,i]for i,key in enumerate(('x_mm','y_mm','z_mm','layer','volume_m3'))},dict(h_xy_mm=.5,radius_mm=25,z_faces_mm=faces*1000,layer_counts=list(science.COUNTS),geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001),deadline_monotonic=deadline_monotonic);science.archive(np,out/'common-grid-and-ROI.npz',grid=grid,ij=ij,z_faces_m=faces,**{key+'_volume_weight_m3':value for key,value in weights.items()});new_json(out/'ROI-receipt.json',roi)
 profiles={f:science._profiles(np,Q,eigen,[cv(v)for v in catalog['gamma_by_frequency'][str(f)]],zs,guard,deadline_monotonic)for f in(2000,2010)}
 for candidate in catalog['candidates'][2:]:
  check(guard,deadline_monotonic);cid=candidate['candidate_id']
  if candidate['status']=='recipe_blocked':
   blocked.append(copy.deepcopy(candidate));new_json(cdir/(cid+'-recipe-BLOCKER.json'),candidate);continue
  require(candidate['reuse_first8_case_id']is None,'New geometry must not impersonate an original control');pads,cells,areas=science._mask(np,candidate,ij);fields=[];proofs=[];losses=np.zeros(4);current2=np.zeros(2);J2=np.zeros(len(areas));V2=np.zeros(len(areas));sourceP=contactP=resistorP=0.
  for frequency,output in((2000,0),(2010,1)):
   check(guard,deadline_monotonic);za=cv(catalog['z_by_frequency'][str(frequency)]);solution=science._solve(np,Q,profiles[frequency],pads,cells,areas,za,output,guard,deadline_monotonic);proof=solution['proof'];proof.update(candidate_id=cid,frequency_Hz=frequency);new_json(rawdir/(cid+'-'+str(frequency)+'-solve-proof.json'),proof);science.archive(np,rawdir/(cid+'-'+str(frequency)+'-surface-state.npz'),phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],modal_surface_coeff=solution['coeff']);require(proof['passed'],'New geometry physical gate failed; original iterate/proof preserved')
   actual_RHS+=1;require(actual_RHS<=6,'Selected maximumsixnewRHS');phi,E,interface=science._fields(np,Q,profiles[frequency],solution,ij,layers,guard,deadline_monotonic);artifact=science.archive(np,rawdir/(cid+'-'+str(frequency)+'-raw.npz'),phi_peak_V=phi,E_peak_V_m=E,interface_downward_J_peak_A_m2=interface,modal_surface_coeff=solution['coeff'],phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],contact_current_peak_A=solution['contact_current'],contact_normal_J_peak_A_m2=solution['contact_J'],contact_drop_peak_V=solution['contact_drop'],contact_pad=pads,contact_xy_index=cells,contact_area_m2=areas,layer_complex_power_W=solution['layer_power']);raw_artifacts[cid+'-'+str(frequency)]=artifact;fields.append(E);proofs.append(proof)
   losses+=solution['layer_power'].real;sourceP+=float(solution['source_power'].real);contactP+=float(solution['contact_power'].real);resistorP+=solution['resistor_power'];current2+=abs(solution['source_current'])**2/2;J2+=abs(solution['contact_J'])**2/2;V2+=abs(solution['contact_drop'])**2/2;new_json(out/('checkpoint-'+cid+'-'+str(frequency)+'.json'),dict(status='new_peripheral_raw_RHS_complete',candidate_id=cid,frequency_Hz=frequency,actual_new_RHS=actual_RHS,new_eigen_solves=0));del solution,phi,interface
  J=np.sqrt(J2);order=np.argsort(J,kind='stable');at=min(int(np.searchsorted(np.cumsum(areas[order]),.95*float(areas.sum()),side='left')),len(order)-1);electrical=dict(source_Vpp_each=1.,source_current_RMS_by_output_A=np.sqrt(current2).tolist(),sum_output_current_RMS_A_bookkeeping=float(np.sqrt(current2).sum()),source_power_W=sourceP,layers_power_W={name:float(losses[i])for i,name in enumerate(science.LAYERS)},SC_power_W=float(losses[0]),skin_power_W=float(losses[:2].sum()),contact_power_W=contactP,source_resistor_power_W=resistorP,contact_normal_J_RMS_max_A_m2=float(J.max()),contact_normal_J_RMS_P95_A_m2=float(J[order[at]]),contact_voltage_RMS_max_V=float(np.sqrt(V2.max())))
  result=screen_metrics.evaluate(np,grid,weights,fields[0],fields[1],np.asarray([cv(v)for v in catalog['gamma_by_frequency']['2000']]),np.asarray([cv(v)for v in catalog['gamma_by_frequency']['2010']]),electrical,guard,deadline_monotonic);new_metrics+=1;record=dict(candidate_id=cid,status='new_peripheral_geometry_computed_unadopted',geometry=candidate,source_physics_proofs=proofs,metrics=result['summary'],normalizations=screen_metrics.normalize(result['summary'],baseline),scalar_arrays=science.archive(np,cdir/(cid+'-scalars.npz'),**result['arrays']),actual_new_RHS=2,actual_new_metric_evaluations=1,candidate_adopted=False);new_json(cdir/(cid+'-summary.json'),record);records.append(record);new_json(out/('checkpoint-'+cid+'-metrics.json'),dict(status='new_peripheral_geometry_metrics_complete',candidate_id=cid,actual_new_RHS=actual_RHS,actual_new_metric_evaluations=new_metrics));del fields,result
 for item in cacheproof:check(guard,deadline_monotonic);require(digest(item['path'])==item['SHA256'],'Full original Q SHA again after new geometry batch')
 require(actual_RHS==spec['expected_new_driven_RHS']and new_metrics==spec['expected_new_metric_evaluations']and len(records)==spec['expected_completed_conditions'],'Actual counts must equal the prospectively frozen READY subset, not a posterior subset')
 summary=dict(schema='task1-peripheral-fourpad-screen-result-v1',status='peripheral_fourpad_geometry_screen_computed_unadopted'if not blocked else'peripheral_fourpad_screen_completed_with_recipe_blockers',spec=spec,candidates=records,completed_conditions=len(records),requested_conditions=5,recipe_blockers=blocked,actual_new_RHS=actual_RHS,actual_new_driven_RHS=actual_RHS,actual_new_metric_evaluations=new_metrics,actual_alias_conditions=2,actual_control_metric_aliases=2,represented_control_carrier_responses=4,control_PDE_or_field_or_angle_repeated=False,new_eigen_solves=0,raw_artifacts=raw_artifacts,ROI_receipt=roi,holds=spec['holds'],candidate_adopted=False,Windows_saved_verified=False)
 return dict(summary=summary,arrays={})
