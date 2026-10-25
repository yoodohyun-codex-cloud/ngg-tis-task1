"""Cached relative-carrier-current allocation screen: no new PDE or eigensolve.

Import performs no I/O, NumPy imports or array work. The sole finite root owner
calls make_spec/build. Original equal-drive conditions are immutable aliases;
new fields are represented by explicit two carrier weights and source hashes,
without duplicating raw original potentials or vectors.
"""
from __future__ import annotations
import copy,hashlib,json,math,time
from pathlib import Path

FIRST8=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
FIRST8_COMMIT='4d6207caa60ae16ab7a7e997022ac72653b97ec3'
FIRST8_PUB_SHA='d20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159'
MULTIPAD=Path('/dev/shm/task1-multipad-extension-20261025-run')
MULTIPAD_COMMIT='9299ac1ae665fbad5e083e2683ea5789a61e54ad'
MULTIPAD_PUB_SHA='bbc67386d2dcefbf910a6d6f5698a99c7d852ef14803a417a8d0e5ae90922640'
GEOMETRIES=('B0-square15-c10-diagonal','G3-square16-c9p5-diagonal')
RELATIVE_MULTIPLIERS=(.5,.7071067811865476,1.,1.4142135623730951,2.)
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
MAX_FILE=80*1024**2

def require(ok,message):
 if not ok:raise ValueError(message)
def cv(v):return complex(v['real'],v['imaginary'])
def sha_file(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def metadata(path,expected=None):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<8_000_000,'Canonical bounded original JSON metadata');raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest();require(expected is None or digest==expected,'Metadata SHA mismatch: '+str(p));return json.loads(raw),digest
def new_json(path,value):
 raw=(json.dumps(value,allow_nan=False,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
 with Path(path).open('xb')as f:f.write(raw)
def check(guard,deadline):
 guard();require(deadline is None or time.monotonic()<deadline,'Finite cached current-allocation deadline')
def condition_id(geometry,multiplier):return geometry+'__relative-current-mult-'+format(multiplier,'.17g').replace('.','p')

def _inventory():
 pins={};publication,sha=metadata(FIRST8/'result-publication/result-publication.json',FIRST8_PUB_SHA);pins[str(FIRST8/'result-publication/result-publication.json')]=sha
 require(publication['status']=='published_readback_verified'and publication['commit']==FIRST8_COMMIT,'Actual first8 result publication')
 prior,sha=metadata(MULTIPAD/'result-publication/result-publication.json',MULTIPAD_PUB_SHA);pins[str(MULTIPAD/'result-publication/result-publication.json')]=sha;require(prior['status']=='published_readback_verified'and prior['commit']==MULTIPAD_COMMIT,'Actual completed prior multipad result, not an active worker')
 def proof(path,expected=None):
  p=Path(path);require(p.is_relative_to(FIRST8)and p==p.resolve()and not p.is_symlink(),'Only original first8 files may supply cached fields');relative=p.relative_to(FIRST8).as_posix();matches=[item for target,item in publication['files'].items()if target.endswith('/'+relative)];require(len(matches)==1 and matches[0]['readback_passed']is True,'Exactly one direct original readback proof');item=matches[0];require(expected is None or item['SHA256']==expected,'Original metadata/raw identity conflict');pins[str(p)]=item['SHA256'];return item['SHA256']
 summarypath=FIRST8/'summary.json';summary,_=metadata(summarypath,proof(summarypath));require(summary['status']=='provisional_eight_layout_screen_computed_unadopted'and summary['completed_candidates']==8,'Actually completed original eight designs')
 proof(FIRST8/'common-grid-and-ROI.npz');selected={}
 for cid in GEOMETRIES:
  row=next(v for v in summary['candidates']if v['candidate_id']==cid);require(row['metrics']['frequencies_Hz']==[2000,2010]and all(p['passed']is True for p in row['source_physics_proofs']),'Exact two-carrier original physical gates')
  scalar=row['scalar_arrays'];proof(scalar['path'],scalar['SHA256'])
  for f in(2000,2010):
   raw=summary['raw_artifacts'][cid+'-'+str(f)];proof(raw['path'],raw['SHA256'])
  selected[cid]=row
 return dict(summary=summary,candidates=selected,input_sha256=pins)

def required_inputs():
 """Metadata-only authenticated inventory; no cached NPZ is opened here."""
 return _inventory()['input_sha256']

def make_spec():
 original=_inventory()
 return dict(schema='task1-relative-current-allocation-spec-v1',input_sha256=original['input_sha256'],first8_result_commit=FIRST8_COMMIT,prior_completed_multipad_result_commit=MULTIPAD_COMMIT,geometries=list(GEOMETRIES),relative_activecarrierallocation_multipliers=list(RELATIVE_MULTIPLIERS),maximum_conditions=10,expected_new_metric_evaluations=8,expected_alias_conditions=2,new_PDE_RHS=0,
  allocation_definition='r=(active I2000/output0 RMS divided by active I2010/output1 RMS)/(the same ratio in this geometry original equal1Vpp drive). This is a RELATIVE multiplier, never an absolute equal-current target.',
  amplitude_definition='a2000=min(1,r); a2010=min(1,1/r), real positive, preserve original phasor phases; max(raw source Vpp)=1. r1 is EXACT original alias even when absolute carrier currents are unequal.',
  current_definition='Active carrier RMS magnitudes determine achieved absolute I0/I1. Both independent output currents including induced inactive-output currents at each carrier are retained in every RMS/power calculation.',
  circuit='Original two outputnodes/commonGND/one50ohm peroutput; inactive ideal output0V through50ohm. Scaling a carrier scales its entire original solved field/current state; no topology change.',
  powers='Source/layer/contact signed complex powers and50ohm real losses scale separately by each carrier a_f squared; no whole-condition single factor is substituted for unequal carrier weights.',
  baseline_caps='Original unscaled B0 first8 electrical values; same V/current bookkeeping/real power/joint8 burden comparisons remain separate. Above-1Vpp normalized predictions explicitly report required voltages.',
  alias_policy='r1 copies original metrics and points to original scalar/raw SHA/readback identities; no redundant angular evaluation and no duplicate potential/vector archive.',
  pareto=dict(comparison='joint_eight_surface_contact_burden_caps',maximize=['target_AM_mean_V_m','target_AM_P10_V_m'],minimize=['surface_AM_mean_V_m','off_target_AM_mean_V_m'],relative_tolerance=1e-12,absolute_tolerance_V_m=1e-15,scope='Finite electrical-proxy candidate Pareto relation; not physical accuracy, adoption, activation or safety'),
  holds=original['summary']['holds'],candidate_adopted=False,Windows_saved_verified=False)

def relation(a,b,tolerance=1e-12):
 """Signed scalar comparison with an explicit relative/absolute numerical floor."""
 delta=float(a)-float(b);eps=1e-15+tolerance*max(abs(float(a)),abs(float(b)))
 return 1 if delta>eps else -1 if delta<-eps else 0

def dominates(a,b):
 """Four-objective finite Pareto dominance; no ratio-only success criterion."""
 signs=[relation(a[k],b[k])for k in('target_AM_mean_V_m','target_AM_P10_V_m')]+[-relation(a[k],b[k])for k in('surface_AM_mean_V_m','off_target_AM_mean_V_m')]
 return all(s>=0 for s in signs)and any(s>0 for s in signs)

def distribution_comparison(normalized):
 fields=normalized['absolute_ROI_fields_V_m'];target=fields['target']['maxTIS'];surface=fields['surface_0_5']['maxTIS'];off=fields['off_target']['maxTIS']
 mean=target['mean'];p10=target['p10'];smean=surface['mean'];omean=off['mean']
 return dict(target_AM_mean_V_m=mean,target_AM_P10_V_m=p10,target_AM_max_V_m=target['max'],target_AM_std_V_m=target['std'],target_AM_CV=target['std']/mean if mean>0 else None,target_P10_mean=p10/mean if mean>0 else None,surface_AM_mean_V_m=smean,surface_AM_P95_V_m=surface['p95'],surface_AM_max_V_m=surface['max'],off_target_AM_mean_V_m=omean,off_target_AM_P95_V_m=off['p95'],off_target_AM_P99_V_m=off['p99'],off_target_AM_max_V_m=off['max'],target_to_surface_mean_ratio=mean/smean if smean>0 else None,target_to_offtarget_mean_ratio=mean/omean if omean>0 else None)

def normalization_input(metrics):
 """The NEW metric copy uses the explicit expanded electrical schema scaler."""
 return metrics

def scaled_complex_pair(value,scale):
 return dict(real=float(value['real'])*scale*scale,imaginary=float(value['imaginary'])*scale*scale)

def tradeoffs(a,reference):
 absolute_loss=relation(a['target_AM_mean_V_m'],reference['target_AM_mean_V_m'])<0 or relation(a['target_AM_P10_V_m'],reference['target_AM_P10_V_m'])<0
 ratio_gains={key:(relation(a[key],reference[key])>0 if a[key]is not None and reference[key]is not None else None)for key in('target_to_surface_mean_ratio','target_to_offtarget_mean_ratio')}
 return dict(target_mean_change=relation(a['target_AM_mean_V_m'],reference['target_AM_mean_V_m']),target_P10_change=relation(a['target_AM_P10_V_m'],reference['target_AM_P10_V_m']),ratio_improvements=ratio_gains,ratio_gain_with_absolute_target_loss=absolute_loss and any(value is True for value in ratio_gains.values()),interpretation='Ratios cannot replace absolute target mean/P10; all four objective changes remain visible')

def _load(np,path,expected,keys,guard,deadline):
 check(guard,deadline);p=Path(path);require(p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<MAX_FILE and sha_file(p)==expected,'Exact published raw/scalar file before decoding')
 with np.load(p,allow_pickle=False)as saved:
  require(set(keys).issubset(saved.files),'Original array ABI unavailable, no missing field invented');data={key:np.array(saved[key],copy=True)for key in keys}
 require(all(np.isfinite(v).all()for v in data.values()),'Finite original cached arrays');return data

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(spec==make_spec()and callable(guard),'Exact finite cached-allocation method/spec');check(guard,deadline_monotonic);out=Path(output_dir);require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink()and out.parent==Path('/dev/shm'),'Unique sole-owner output directory')
 import numpy as np
 import screen_metrics
 import allocation_electrical as electrical
 original=_inventory();commonpath=FIRST8/'common-grid-and-ROI.npz';names=['grid']+[key+'_volume_weight_m3'for key in screen_metrics.REGIONS];common=_load(np,commonpath,spec['input_sha256'][str(commonpath)],names,guard,deadline_monotonic);grid=common.pop('grid');require(grid.shape==(793860,5),'Unchanged shared physical grid');weights={key:common[key+'_volume_weight_m3']for key in screen_metrics.REGIONS};catalog=original['summary']['spec']['catalog'];g0=np.asarray([cv(v)for v in catalog['gamma_by_frequency']['2000']]);g1=np.asarray([cv(v)for v in catalog['gamma_by_frequency']['2010']]);baseline=original['candidates'][GEOMETRIES[0]]['metrics'];rows=[];new_evaluations=aliases=0;cdir=out/'conditions';cdir.mkdir(exist_ok=True)
 for geometry in GEOMETRIES:
  row=original['candidates'][geometry];raw=[];proofs=[];identities={}
  for frequency in(2000,2010):
   artifact=original['summary']['raw_artifacts'][geometry+'-'+str(frequency)];data=_load(np,artifact['path'],artifact['SHA256'],['E_peak_V_m','source_current_peak_A','contact_normal_J_peak_A_m2','contact_drop_peak_V','contact_area_m2','contact_pad','contact_xy_index','layer_complex_power_W'],guard,deadline_monotonic);require(data['E_peak_V_m'].shape==(len(grid),3)and data['source_current_peak_A'].shape==(2,)and data['layer_complex_power_W'].shape==(4,),'Original coherent field/two-output/layer ABI');raw.append(data);proofs.append(next(p for p in row['source_physics_proofs']if p['frequency_Hz']==frequency));identities[str(frequency)]=dict(original_raw_path=artifact['path'],SHA256=artifact['SHA256'],fixed_commit=FIRST8_COMMIT)
  active0=float(abs(raw[0]['source_current_peak_A'][0])/math.sqrt(2));active1=float(abs(raw[1]['source_current_peak_A'][1])/math.sqrt(2));require(active0>0 and active1>0,'Nonzero actual active source-current RMS')
  for multiplier in RELATIVE_MULTIPLIERS:
   check(guard,deadline_monotonic);cid=condition_id(geometry,multiplier);allocation=electrical.weights_for_relative_multiplier(active0,active1,multiplier);a0=allocation['a0'];a1=allocation['a1'];is_alias=multiplier==1.;array_identity=None
   if is_alias:
    require(a0==a1==1.,'Original alias must preserve both drives exactly');metrics=copy.deepcopy(row['metrics']);aliases+=1;array_identity=dict(kind='immutable_original_scalar_alias',path=row['scalar_arrays']['path'],SHA256=row['scalar_arrays']['SHA256'],fixed_commit=FIRST8_COMMIT,no_angular_recalculation=True)
   else:
    e,frequency_details=electrical.synthesize(np,raw[0],raw[1],proofs[0],proofs[1],a0,a1);result=screen_metrics.evaluate(np,grid,weights,a0*raw[0]['E_peak_V_m'],a1*raw[1]['E_peak_V_m'],g0,g1,e,guard,deadline_monotonic);metrics=result['summary'];path=cdir/(cid+'-scalars.npz')
    with path.open('xb')as f:np.savez_compressed(f,**result['arrays'])
    require(path.stat().st_size<MAX_FILE,'Preserved allocation scalar output exceeds80MiB');array_identity=dict(kind='new_resynthesized_scalar_metrics',path=str(path),SHA256=sha_file(path),bytes=path.stat().st_size);new_evaluations+=1;del result
   # Always retain exact spectral current/power bookkeeping, including aliases.
   e,frequency_details=electrical.synthesize(np,raw[0],raw[1],proofs[0],proofs[1],a0,a1)
   for key,value in e.items():
    if key not in('skin_vector_J_RMS_max_A_m2','skin_vector_J_RMS_P95_A_m2'):metrics['electrical'][key]=value
   norm=screen_metrics.normalize(normalization_input(metrics),normalization_input(baseline));comparisons={}
   for mode in MODES:
    normalized=norm['comparisons'][mode];scale=normalized['amplitude_scale'];normalized['electrical']['source_Vpp_by_frequency']={'2000':a0*scale,'2010':a1*scale};normalized['electrical']['source_peak_V_by_frequency']={'2000':.5*a0*scale,'2010':.5*a1*scale};normalized['electrical']['max_source_Vpp']=max(a0,a1)*scale;normalized['normalization_requires_source_voltage_above_raw1Vpp']=bool(max(a0,a1)*scale>1+1e-12)
    normalized['electrical']['source_complex_power_W']=scaled_complex_pair(e['source_complex_power_W'],scale);normalized['electrical']['contact_complex_power_W']=scaled_complex_pair(e['contact_complex_power_W'],scale);normalized['electrical']['layer_complex_power_W']=[scaled_complex_pair(value,scale)for value in e['layer_complex_power_W']]
    normalized['per_frequency_circuit']=[dict(frequency_Hz=detail['frequency_Hz'],source_high_impedance_Vpp=detail['source_high_impedance_Vpp']*scale,scaled_source_current_peak_A=[dict(real=v['real']*scale,imaginary=v['imaginary']*scale)for v in detail['scaled_source_current_peak_A']],source_complex_power_W=scaled_complex_pair(detail['source_complex_power_W'],scale),contact_complex_power_W=scaled_complex_pair(detail['contact_complex_power_W'],scale),layer_complex_power_W=[scaled_complex_pair(v,scale)for v in detail['layer_complex_power_W']],source_resistor_power_W=detail['source_resistor_power_W']*scale*scale)for detail in frequency_details]
    comparisons[mode]=distribution_comparison(normalized)
   record=dict(condition_id=cid,geometry_id=geometry,relative_activecarrierallocation_mult=multiplier,allocation=allocation,is_original_alias=is_alias,raw_source_Vpp_by_frequency={'2000':a0,'2010':a1},raw_max_source_Vpp=max(a0,a1),raw_voltage_cap_Vpp=1.,original_fields=identities,resynthesis='At each carrier every original potential/vector/contact/current phasor is multiplied coherently by its real positive a_f; only new scalar metrics stored',scalar_array_identity=array_identity,per_frequency_circuit=frequency_details,metrics=metrics,normalizations=norm,comparisons=comparisons,holds=spec['holds'],candidate_adopted=False)
   new_json(cdir/(cid+('-alias-proof.json'if is_alias else'-summary.json')),record);rows.append(record);new_json(out/('checkpoint-%02d.json'%len(rows)),dict(status='allocation_condition_complete',condition_id=cid,completed_conditions=len(rows),actual_new_metric_evaluations=new_evaluations,actual_alias_conditions=aliases,new_PDE_RHS=0))
  del raw
 joint='joint_eight_surface_contact_burden_caps';original_alias={r['geometry_id']:r for r in rows if r['is_original_alias']}
 for row in rows:
  objectives=row['comparisons'][joint];dominated=[other['condition_id']for other in rows if other is not row and dominates(other['comparisons'][joint],objectives)];row['pareto_joint_burden']=dict(non_dominated=not dominated,dominated_by=dominated,objectives=objectives,scope=spec['pareto']['scope']);row['tradeoffs_vs_same_geometry_original']={mode:tradeoffs(row['comparisons'][mode],original_alias[row['geometry_id']]['comparisons'][mode])for mode in MODES};row['tradeoffs_vs_B0_original']={mode:tradeoffs(row['comparisons'][mode],original_alias[GEOMETRIES[0]]['comparisons'][mode])for mode in MODES}
  new_json(cdir/(row['condition_id']+'-comparison-classification.json'),dict(condition_id=row['condition_id'],pareto_joint_burden=row['pareto_joint_burden'],tradeoffs_vs_same_geometry_original=row['tradeoffs_vs_same_geometry_original'],tradeoffs_vs_B0_original=row['tradeoffs_vs_B0_original'],candidate_adopted=False))
 require(len(rows)==10 and new_evaluations==8 and aliases==2,'Exactly ten conditions, eight new angular metrics and two immutable aliases')
 check(guard,deadline_monotonic)
 summary=dict(schema='task1-relative-current-allocation-result-v1',status='current_allocation_cached_search_computed',spec=spec,conditions=rows,completed_conditions=len(rows),actual_new_metric_evaluations=new_evaluations,actual_alias_conditions=aliases,new_PDE_RHS=0,new_eigen_solves=0,provisional_pareto_condition_ids=[r['condition_id']for r in rows if r['pareto_joint_burden']['non_dominated']],pareto_scope=spec['pareto']['scope'],reference_caps_condition=condition_id(GEOMETRIES[0],1.),raw_original_phi_E_duplicated=False,holds=spec['holds'],candidate_adopted=False,Windows_saved_verified=False)
 return dict(summary=summary,arrays={})
