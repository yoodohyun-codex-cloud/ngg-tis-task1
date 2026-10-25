"""Owner-called streamed cached E13 allocation. No scientific work on import.

Three finite complete 2074-direction evaluations: one original QA, then two
new allocations. No PDE, Q, eigenproblem, changed geometry or material.
"""
import gc,hashlib,importlib,json,math,time
from pathlib import Path
import drive_inputs
from drive_contracts import require,fullhex,require_baseline_QA,relative_multipliers,UNAVAILABLE_SAVED_FLOAT_MAPS

SOURCE=drive_inputs.SOURCE
OUT=drive_inputs.OUT
RAW_KEYS=('source_current_peak_A','metal_peak_V','contact_normal_J_peak_A_m2','contact_drop_peak_V','contact_area_m2','contact_pad','contact_xy_index','layer_complex_power_W')

def make_spec(admission=None):return drive_inputs.make_spec(admission)
def required_inputs(admission=None):return drive_inputs.required_inputs(admission)

def check(guard,deadline):
 guard()
 if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Incomplete cached drive batch preserved; no partial sampled maximum finalizes')

def new_json(path,value):
 raw=(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
 with Path(path).open('xb')as f:f.write(raw)
 return dict(path=str(path),SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def module(name,spec):
 canonical=SOURCE/(name+'.py');expected=spec['source_sha256'].get(str(canonical));require(fullhex(expected,64)and drive_inputs.digest(canonical)==expected,'Canonical registered dependency '+name)
 mod=importlib.import_module(name);loaded=Path(mod.__spec__.origin).resolve();deployed=Path(__file__).resolve().parent/(name+'.py')
 require(loaded in(canonical,deployed)and drive_inputs.digest(loaded)==expected,'Only canonical or byte-identical frozen scientific module '+name)
 return mod

def verify_native(spec,guard,deadline):
 proofs=[]
 for d in spec['native_input_descriptors']:
  check(guard,deadline);p=Path(d['path']);require(p==p.resolve()and not p.is_symlink()and p.is_file()and p.stat().st_size==d['bytes'],'Exact registered native artifact size/path')
  h=hashlib.sha256()
  with p.open('rb')as f:
   for block in iter(lambda:f.read(1024**2),b''):check(guard,deadline);h.update(block)
  require(h.hexdigest()==d['SHA256'],'Full native SHA before/after data use '+str(p));proofs.append(dict(d,full_SHA_verified=True))
 return proofs

def validate_MFG(receipt,spec):
 require(receipt.get('status')=='passed'and receipt.get('model_source_sha256')==spec['source_sha256'],'Actual complete source-bound manufactured receipt required before native bytes')
 for key in('tests_failed','tests_errors','tests_skipped'):
  require(type(receipt.get(key))is int and receipt[key]==0,'No manufactured errors/failures/skips '+key)
 require(type(receipt.get('tests_run'))is int and receipt['tests_run']==receipt.get('expected_total_tests')and receipt['tests_run']>0,'Actual prospective source test inventory count')
 require(fullhex(receipt.get('source_publication_commit'),40),'Public source readback precedes tests/native data')
 for key in('native_RHS','native_Q_loads','native_field_reads','native_eigen_solves'):
  require(type(receipt.get(key))is int and receipt[key]==0,'Manufactured phase did no native work '+key)

class LazyWeights:
 """Only one exact supplied N-vector materializes per statistics scope."""
 def __init__(self,np,descriptor,archive,guard,deadline):
  self.np=np;self.descriptor=descriptor;self.archive=archive;self.guard=guard;self.deadline=deadline
 def __iter__(self):return iter(drive_inputs.REGIONS)
 def __len__(self):return len(drive_inputs.REGIONS)
 def __getitem__(self,key):
  require(key in drive_inputs.REGIONS,'Only original six native ROI weights');check(self.guard,self.deadline)
  with self.np.load(self.descriptor['path'],allow_pickle=False)as saved:
   value=saved[key+'_volume_weight_m3']
  require(value.dtype==self.np.dtype('<f8')and value.shape==(drive_inputs.CELLS,),'Exact native Float64 ROI shape')
  return value
 def read_rows(self,key,first,last):
  require(key in drive_inputs.REGIONS,'Only original native ROI weight rows')
  return self.archive.read_rows(key+'_volume_weight_m3',first,last)

def load_geometry(np,spec,archive,guard,deadline):
 check(guard,deadline)
 with np.load(spec['grid']['path'],allow_pickle=False)as saved:
  grid=saved['grid'];faces=saved['z_faces_m'];ij=saved['ij']
 require(grid.dtype==np.dtype('<f8')and grid.shape==(spec['cells'],5)and faces.shape==(98,)and ij.shape==(8184,2),'Actual saved fine97/XY102 geometry ABI')
 require(np.isfinite(grid).all()and np.isfinite(faces).all()and np.all(np.diff(faces)>0)and abs(float(faces[0]))<1e-15 and abs(float(faces[-1])-.0251)<1e-14,'Fixed D50 physical layered depth grid')
 layerids=[0]*4+[1]*19+[2]*18+[3]*56
 for z,layer in enumerate(layerids):
  check(guard,deadline);part=grid[z*8184:(z+1)*8184]
  require(np.array_equal(part[:,:2],grid[:8184,:2])and np.all(part[:,3]==layer)and np.allclose(part[:,2],(faces[z]+faces[z+1])*500,rtol=0,atol=1e-11),'Original native z-major/XY/layer row ordering')
 # Exact saved weights are subsequently validated against these original rows;
 # no analytical ROI masks, interpolated fields, or volume renormalization.
 del faces,ij
 return grid,LazyWeights(np,spec['grid'],archive,guard,deadline)

def small_electrical(np,spec,guard,deadline):
 raws=[]
 for i,f in enumerate(('2000','2010')):
  check(guard,deadline)
  with np.load(spec['raw_by_frequency'][f]['path'],allow_pickle=False)as saved:
   require(set(RAW_KEYS).issubset(saved.files),'Actual original contact/circuit raw ABI; no absent field invented')
   raw={key:saved[key]for key in RAW_KEYS}
  require(all(np.isfinite(v).all()for v in raw.values())and sum(v.nbytes for v in raw.values())<2*1024**2,'Finite bounded contact/circuit metadata arrays only; no fullE decoded')
  I=raw['source_current_peak_A'];metal=raw['metal_peak_V'];require(I.shape==metal.shape==(2,),'Two physical output phasors')
  ideal=np.zeros(2,complex);ideal[i]=.5
  require(float(np.max(abs(metal+50*I-ideal)))<=1e-10+2e-7*.5,'Original inactive0V-through50 and loaded ideal source relation')
  p=spec['proofs'][i];cv=lambda v:complex(v['real'],v['imaginary'])
  S=cv(p['source_complex_power_W']);C=cv(p['contact_complex_power_W']);R=float(p['source_resistor_power_W']);L=complex(raw['layer_complex_power_W'].sum())
  require(R>=0 and abs(S-L-C-R)<=2e-7*max(abs(S),abs(L+C+R),1e-12),'Saved signed VI*/2 layer/contact/source/R50 balance')
  require(abs(R-.5*50*float(np.sum(abs(I)**2)))<=2e-7*max(R,1e-12),'All induced inactive-output resistor losses retained')
  pads=raw['contact_pad'];areas=raw['contact_area_m2'];require(set(np.unique(pads).tolist())=={0,1,2,3},'Exactly four original physical pads')
  for pad in range(4):require(abs(float(areas[pads==pad].sum())-.000225)<=1e-10*.000225,'Original225mm2 physical pad without area adjustment')
  raws.append(raw)
 return raws

def add_CV(summary):
 for region in summary['regions'].values():
  for value in region['statistics'].values():
   if value.get('status')=='complete':value['CV']=float(value['std']/value['mean'])if value['mean']>0 else None

def objective(metrics):
 r=metrics['regions'];t=r['target']['statistics']['maxTIS'];s=r['surface_0_5']['statistics']['maxTIS'];o=r['off_target']['statistics']['maxTIS'];mean=t['mean']
 return dict(target_mean=mean,target_P10=t['p10'],target_to_surface_mean=mean/s['mean'],target_to_offtarget_mean=mean/o['mean'],target_CV=t['std']/mean if mean>0 else None,target_P10_mean=t['p10']/mean if mean>0 else None)

def baseline_receipt(gate,cells):
 maps={k:dict(passed=v.get('failed_cells')==0 and v.get('compared_cells')==cells,**v)for k,v in gate.get('array_agreement',{}).get('float_maps',{}).items()}
 failures=gate.get('summary_failures',[])
 return dict(schema='task1-E13-fine-drive-baseline-QA-v1',status=gate.get('status'),passed=gate.get('status')=='passed',baseline_multiplier=1.,map_checks=maps,
  statistics_passed=not any(v.get('path','').startswith(('regions/','waveform_checks/'))for v in failures),electrical_passed=not any(v.get('path','').startswith('electrical/')for v in failures),source_identity_passed=True,
  full_agreement=gate,unavailable_saved_float_maps=list(UNAVAILABLE_SAVED_FLOAT_MAPS),all_eight_original_scalar_ROI_summaries_checked=True,duplicate_baseline_arrays=0,baseline_recomputed_for_QA_only=True)

def output_forecast_observation(out,forecast):
 size=0
 for p in out.rglob('*'):
  try:
   if p.is_file():size+=p.stat().st_size
  except FileNotFoundError:continue
 return dict(observed_output_bytes=size,forecast_bytes=forecast,forecast_exceeded=size>forecast,storage_quota_applied=False,
  enforcement='Actual aggregate all-research RSS plus all task temporary bytes hard cap remains decisive; output forecast is not a storage-capacity guard')

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 """Called only by authenticated finite root owner after source-bound MFG."""
 out=Path(output_dir or OUT);require(out==OUT and out.is_dir()and not out.is_symlink(),'Only unique preregistered new output directory')
 check(guard,deadline_monotonic);require(spec==make_spec(spec['root_admission']),'Exact immutable metadata/source spec; no waiver after source publication')
 receipt,_=drive_inputs.metadata(out/'synthetic-test-receipt.json');validate_MFG(receipt,spec)
 new_json(out/'execution-stage-model.json',dict(status='native_hash_verification_after_manufactured_PASS',new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0))
 before=verify_native(spec,guard,deadline_monotonic);new_json(out/'native-input-SHA-before.json',dict(passed=True,files=before))
 import numpy as np
 io=module('stream_io',spec);metrics=module('stream_metrics',spec);electrical=module('allocation_electrical',spec)
 memory_plan=metrics.allocation_budget(spec['cells'],resident_grid=True,resident_weights=1)
 require(spec.get('lazy_weights_required')is True and memory_plan['within_provisional_workspace_limit']is True,'Only one lazy supplied weight fits the prospective220MB child estimate')
 new_json(out/'model-allocation-forecast.json',dict(memory_plan,measured=False,actual_global_cap_bytes=8000000000,output_forecast_is_quota=False))
 grid_archive=io.NativeArchive(np,spec['grid'],'grid',guard=guard,deadline=deadline_monotonic)
 scalars_archive=io.NativeArchive(np,spec['baseline_scalars'],'scalars',guard=guard,deadline=deadline_monotonic)
 grid,weights=load_geometry(np,spec,grid_archive,guard,deadline_monotonic);raws=small_electrical(np,spec,guard,deadline_monotonic)
 gamma=[[complex(v['real'],v['imaginary'])for v in spec['gamma_by_frequency'][f]]for f in('2000','2010')]
 conditions=out/'conditions';conditions.mkdir(exist_ok=False);completed=[];gate=None;baseline=None
 try:
  for index,(cid,r)in enumerate((('baseline-r1',1.),('r0p8',.8),('r1p25',1.25))):
   guard(force=True);check(guard,deadline_monotonic);start=time.monotonic();case_deadline=min(start+spec['per_condition_seconds'],deadline_monotonic)if deadline_monotonic is not None else start+spec['per_condition_seconds']
   if index:require_baseline_QA(baseline)
   reader=io.PairedEReader(spec['raw_by_frequency']['2000'],spec['raw_by_frequency']['2010'],np=np,guard=guard,deadline=case_deadline,expected_cells=spec['cells'],chunk_rows=spec['chunk_rows'])
   a0,a1=relative_multipliers(r);e,frequencies=electrical.synthesize(np,raws[0],raws[1],spec['proofs'][0],spec['proofs'][1],a0,a1)
   allocation=electrical.weights_for_relative_multiplier(abs(raws[0]['source_current_peak_A'][0])/math.sqrt(2),abs(raws[1]['source_current_peak_A'][1])/math.sqrt(2),r)
   new_json(conditions/(cid+'-started.json'),dict(condition_id=cid,relative_multiplier=r,a0=a0,a1=a1,finite_seconds=spec['per_condition_seconds'],new_PDE_RHS=0))
   result=metrics.evaluate(np,grid,weights,reader.iter_chunks,gamma[0],gamma[1],e,a0=a0,a1=a1,take_rows=reader.take_rows,guard=guard,deadline=case_deadline,
    baseline_arrays=(lambda name,first,last:scalars_archive.read_rows(name,first,last))if index==0 else None,baseline_summary=spec['baseline_record']['metrics']if index==0 else None,baseline_gate=gate,export_maps=index!=0)
   summary=result['summary'];add_CV(summary)
   if index==0:
    gate=result['baseline_agreement'];baseline=baseline_receipt(gate,spec['cells']);new_json(out/'baseline-agreement-proof.json',baseline);require_baseline_QA(baseline)
    require(result['arrays']=={},'Baseline QA never exports duplicate arrays')
   maps=None
   if index:
    arrays=result['arrays'];require(set(arrays)==set(spec['output_arrays'])and all(v.shape==(spec['cells'],)and v.dtype==np.dtype('<f8')for v in arrays.values()),'Only two complete Float64 new scalar maps')
    path=conditions/(cid+'-maps.npz')
    with path.open('xb')as f:np.savez_compressed(f,**arrays)
    maps=dict(path=str(path),bytes=path.stat().st_size,SHA256=drive_inputs.digest(path),arrays=list(arrays),native_complex_fields_copied=False)
   normalizations=metrics.normalize(summary,spec['coarse_B0_reference']);secondary=metrics.normalize(summary,spec['fine_B0_reference'])
   for norm in(normalizations,secondary):
    for value in norm.get('comparisons',{}).values():
     if value.get('status')=='calculated_global_amplitude_rescaling':value['normalization_requires_source_voltage_above_raw1Vpp']=value['electrical']['source_Vpp_each']>1.+1e-12
   row=dict(condition_id=cid,relative_multiplier=r,allocation=allocation,metrics=summary,per_frequency_signed_circuit=frequencies,normalizations_to_original_coarse101_B0=normalizations,secondary_fine_B0_derived_caps=secondary,
    objectives=objective(summary),maps=maps,elapsed_seconds=time.monotonic()-start,complete_directions=2074,baseline_QA_only=index==0,candidate_adopted=False)
   completed.append(row);new_json(conditions/(cid+'-summary.json'),row);new_json(out/('checkpoint-'+str(index+1)+'.json'),dict(completed_conditions=len(completed),completed_new_metric_evaluations=max(0,len(completed)-1),baseline_passed=baseline['status']=='passed',condition_id=cid,all2074directions_complete=True))
   del result,summary,normalizations,secondary
   if index:del arrays
   # Each reader iterator owns/finishes/closes its streams in its own finally;
   # PairedEReader itself retains descriptors only, not an open archive.
   del reader;gc.collect();new_json(out/('output-forecast-'+str(index+1)+'.json'),output_forecast_observation(out,spec['new_owned_tmp_forecast_bytes']))
   guard(force=True)
 except BaseException:
  # Force the same complete parent/lease audit on a failing condition exit;
  # ordinary per-operation deadline/STOP/PID checks remain uncached.
  guard(force=True)
  raise
 finally:
  grid_archive.close();scalars_archive.close()
 del grid,weights,raws;gc.collect()
 after=verify_native(spec,guard,deadline_monotonic);new_json(out/'native-input-SHA-after.json',dict(passed=True,files=after))
 reference=completed[0]['objectives']
 for row in completed:
  v=row['objectives'];row['four_ratios_to_same_E13_original']={k:v[k]/reference[k]for k in('target_mean','target_P10','target_to_surface_mean','target_to_offtarget_mean')}
  row['ratio_gain_with_absolute_target_loss']=any(v[k]>reference[k]for k in('target_to_surface_mean','target_to_offtarget_mean'))and any(v[k]<reference[k]for k in('target_mean','target_P10'))
 summary=dict(schema='task1-E13-fine-drive-stream-result-v1',status='e13_fine_streamed_allocation_complete_unadopted',candidate_id=spec['candidate_id'],completed_conditions=3,baseline_multiplier=1.,baseline_verification_conditions=1,baseline_agreement_passed=True,actual_new_metric_evaluations=2,actual_directional_metric_evaluations=3,
  ratio_multipliers=[.8,1.25],baseline_saved_float_maps=spec['baseline_saved_float_maps'],unavailable_saved_float_maps=spec['unavailable_saved_float_maps'],baseline_scalar_summary_count=8,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,duplicate_baseline_arrays=0,conditions=completed,output_artifacts=[r['maps']for r in completed if r['maps']],
  original_native_artifacts=spec['native_input_descriptors'],source_proofs=spec['source_proofs'],inherited_holds=spec['inherited_holds'],candidate_adopted=False,original_results_overwritten=False,full_convergence=False,physiological_activation_or_safety_claim=False,hardware_loading_validated=False,
  quantiles='Full stable inverse-volume ECDF; sorted cumsum[-1] threshold; original saved fractional weights',reconstruction='Original SHA-pinned complex E carrier archives and relative amplitudes reconstruct all deliberately unsaved derived scalar maps',child_RSS_forecast_bytes=220000000,forecast_measured=False)
 summary['output_forecast_observation']=output_forecast_observation(out,spec['new_owned_tmp_forecast_bytes'])
 new_json(out/'drive-stream-result.json',summary);return dict(summary=summary,arrays={})
