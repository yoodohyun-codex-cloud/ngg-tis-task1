"""Cached modal/panel QA of two published periodic slab batches, no PDE solve.

Import performs no I/O, NumPy import or array construction. Actual raw reads and
all numerical work occur only when the sole root owner calls build(). This is
finite-series and finite-panel error analysis, never an actual four-pad field.
"""
from __future__ import annotations
import hashlib,json,math,time
from pathlib import Path

SOURCE=Path('/dev/shm/task1-contact-modal-audit-20261025/source')
RUNS={
 'coarse':dict(run='/dev/shm/task1-contact-edge-surrogate-20261025-run',prefix='data-native/contact-edge-surrogate-20261025/',commit='165f45e5954637d4ba4f49af6915363f38bd5dbf',publication_sha256='c7d8cb8678e3d517f3d6edf013ad59b60c73d1ffa11cac78d406b58a95103ef6'),
 'fine':dict(run='/dev/shm/task1-contact-edge-surrogate-fine-20261025-run',prefix='data-native/contact-edge-surrogate-fine-20261025/',commit='2fd23d6e23680816fce551c4fc7990df11a435d2',publication_sha256='ed773187e00301371c30e72b4574b3aff894bc2ffc819aac15c258d6d34ab2d5')}
LIMITS=dict(exact_modal_vector_E_relative_L2=.02,physical_panel_q_relative_L2=.05,contact_real_power_relative=.02,contact_panel_Jmax_relative=.05)
PAIRS=(
 ('coarse-panel-1','coarse','P64-H4096','coarse','P128-H4096',0),
 ('coarse-panel-2','coarse','P128-H4096','coarse','P256-H4096',1),
 ('coarse-harmonic-1','coarse','P256-H1024','coarse','P256-H2048',2),
 ('coarse-harmonic-2','coarse','P256-H2048','coarse','P256-H4096',3),
 ('fine-panel-1','fine','P256-H16384','fine','P512-H16384',0),
 ('fine-panel-2','fine','P512-H16384','fine','P1024-H16384',1),
 ('fine-harmonic-1','fine','P1024-H4096','fine','P1024-H8192',2),
 ('fine-harmonic-2','fine','P1024-H8192','fine','P1024-H16384',3),
 ('cross-finest','coarse','P256-H4096','fine','P1024-H16384',None))

def require(ok,message):
 if not ok:raise ValueError(message)
def pair(v):
 v=complex(v);return dict(real=float(v.real),imaginary=float(v.imag))
def cv(v):return complex(v['real'],v['imaginary'])
def sha_file(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def metadata(path,expected=None):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<=8_000_000,'Bounded canonical metadata required')
 raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest();require(expected is None or digest==expected,'Metadata SHA256 mismatch: '+str(p));return json.loads(raw),digest
def encode(value):return (json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def new_json(path,value):
 raw=encode(value)
 with Path(path).open('xb')as f:f.write(raw)
def check(guard,deadline):
 guard();require(deadline is None or time.monotonic()<deadline,'Finite cached modal audit deadline')

def _inventory():
 """Read authenticated JSON only; NPZ identities are taken from direct proofs."""
 inputs={};batches={}
 for label,definition in RUNS.items():
  run=Path(definition['run']);publication=run/'result-publication/result-publication.json';proof,digest=metadata(publication,definition['publication_sha256']);inputs[str(publication)]=digest
  require(proof['status']=='published_readback_verified'and proof['commit']==definition['commit'],'Exact completed original result publication required')
  def authenticated(relative,read_metadata=True):
   target=definition['prefix']+relative;item=proof['files'][target]
   require(item.get('readback_passed')is True and isinstance(item['bytes'],int)and item['bytes']>=0 and len(item['SHA256'])==64,'Direct per-file publication readback proof required')
   path=run/relative;inputs[str(path)]=item['SHA256']
   if read_metadata:
    obj,_=metadata(path,item['SHA256']);require(path.stat().st_size==item['bytes'],'Published metadata size changed');return obj
   return dict(path=str(path),SHA256=item['SHA256'],bytes=item['bytes'],fixed_commit=proof['commit'],repo_relative_path=target)
  summary=authenticated('summary.json');spec=summary['spec'];cases={}
  require(summary['analytic_contract']['passed']is True and summary['completed_unique_cases']==5,'Completed five-case original batch required')
  for cid,declared in summary['cases'].items():
   actual=authenticated('cases/'+cid+'.json');raw=authenticated('cases/'+cid+'.npz',False)
   require(actual==declared and actual['case_id']==cid and actual['arrays_SHA256']==raw['SHA256'],'Original case metadata/raw identity mismatch')
   cases[cid]=dict(metadata=actual,raw=raw)
  batches[label]=dict(spec=spec,cases=cases,original_adjacent_diagnostics=summary['adjacent_diagnostics'],original_all_flags=summary['all_diagnostic_flags_pass'],commit=proof['commit'],summary_SHA256=inputs[str(run/'summary.json')])
 a=batches['coarse']['spec'];b=batches['fine']['spec'];keys=('period_width_m','SC_thickness_m','contact_endpoints_m','transferred_gamma_S_m','transferred_contact_ohm_m2','equipotential_contact_peak_V','bottom_peak_V','field_x_midpoints','field_z_midpoints','surface_x_midpoints')
 require(all(a['plan'][key]==b['plan'][key]for key in keys)and a['coefficient_transfer']==b['coefficient_transfer']and a['phasor']==b['phasor']and a['circuit']==b['circuit'],'Identical physical domain/coefficient/source/phase conventions required')
 return inputs,batches

def required_inputs():
 """Return exact input pins using metadata only; never open a native NPZ here."""
 return _inventory()[0]

def make_spec():
 inputs,batches=_inventory();plan=batches['fine']['spec']['plan']
 return dict(schema='task1-cached-contact-modal-audit-spec-v1',input_sha256=inputs,original_result_commits={key:value['commit']for key,value in batches.items()},
  physical=dict(period_width_m=plan['period_width_m'],SC_thickness_m=plan['SC_thickness_m'],contact_endpoints_m=plan['contact_endpoints_m'],gamma_S_m=plan['transferred_gamma_S_m'],contact_ohm_m2=plan['transferred_contact_ohm_m2']),
  pairs=[dict(pair_id=p[0],old_batch=p[1],old_case=p[2],new_batch=p[3],new_case=p[4],original_adjacent_index=p[5])for p in PAIRS],diagnostic_limits=dict(LIMITS),
  modal_formula='Integral |Delta E|^2 dx dz=L/|gamma|^2 [t|Delta q0|^2+sum_n tanh(kn*t)/kn (|Delta q+|^2+|Delta q-|^2)]; missing signed coefficients are zero',
  modal_RMS='sqrt(Integral |Delta E|^2/(2*L*t)); relative error uses the new finite-series field norm; no gauge/phase fit',
  contact_primary='Exact physical interval-pair length weighted complex L2; temporal RMS is peak-complex spatial norm/sqrt(2); relative uses max(old,new) spatial norm',
  contact_secondary='Covered-length average onto old panels before norm, explicitly labelled averaging; never replaces primary pairwise norm',
  power='Contact S=.5*zA*integral |q|^2 dl, W/m out-of-plane; signed new-minus-old complex difference preserved',
  original_flags='All original sampled-grid/delta flags and values are retained separately and unchanged; new modal flags do not clear or overwrite them',
  analytic_contract=dict(relative_tolerance=1e-10,absolute_tolerance=1e-24,quadrature='32x32 Gauss-Legendre, independent direct constant-plus-single-cosine Ex/Ez integration',synthetic_physical_points=1024),
  new_PDE_RHS=0,actual_four_pad_comparison=False,candidate_adopted=False,Windows_saved_verified=False,
  limitations=['Exact modal integration refers only to each stored finite Fourier field, not the unknown continuum solution','Native panel q and truncated Fourier top q are distinct; panel contact loss and modal bulk loss must not be interchanged','Transferred surrogate coefficients do not verify actual skin contact, anatomy, TIS, activation, safety or experiment'])

def modal_integral(np,q0,plus,minus,L,t,gamma):
 """Parseval integral of the full vector E, with independently complex +/-n."""
 plus=np.asarray(plus,dtype=np.complex128);minus=np.asarray(minus,dtype=np.complex128)
 require(plus.ndim==minus.ndim==1 and plus.shape==minus.shape and L>0 and t>0 and abs(gamma)>0,'Physical finite modal ABI')
 require(np.isfinite(plus).all()and np.isfinite(minus).all()and math.isfinite(abs(q0)),'Finite modal coefficients')
 k=2*math.pi*np.arange(1,len(plus)+1)/L
 coefficient=t*abs(complex(q0))**2+float(np.sum(np.tanh(k*t)/k*(abs(plus)**2+abs(minus)**2)))
 return float(L/abs(gamma)**2*coefficient)

def modal_difference(np,a,b,L,t,gamma):
 H=max(len(a['plus']),len(b['plus']));positive=np.zeros(H,np.complex128);negative=np.zeros(H,np.complex128)
 positive[:len(b['plus'])]+=b['plus'];positive[:len(a['plus'])]-=a['plus'];negative[:len(b['minus'])]+=b['minus'];negative[:len(a['minus'])]-=a['minus'];zero=complex(b['q0'])-complex(a['q0'])
 integral=modal_integral(np,zero,positive,negative,L,t,gamma);old=modal_integral(np,a['q0'],a['plus'],a['minus'],L,t,gamma);new=modal_integral(np,b['q0'],b['plus'],b['minus'],L,t,gamma)
 difference=math.sqrt(integral/(2*L*t));oldnorm=math.sqrt(old/(2*L*t));newnorm=math.sqrt(new/(2*L*t))
 return dict(summary=dict(difference_integral_peak_E_squared_V2=integral,difference_vector_carrier_RMS_L2_V_m=difference,old_vector_carrier_RMS_L2_V_m=oldnorm,new_vector_carrier_RMS_L2_V_m=newnorm,relative_L2=difference/max(newnorm,1e-300),denominator='New finite-series vector carrier RMS L2; floor1e-300 V/m',signed_coefficient_difference='new-minus-old',maximum_signed_mode_count=2*H+1),arrays=dict(delta_q0_peak_A_m2=np.asarray(zero),delta_q_positive_peak_A_m2=positive,delta_q_negative_peak_A_m2=negative))

def analytic_contract(np):
 """Independent direct Ex/Ez quadrature; no actual fields or PDE solve."""
 L=.002;t=.0001;gamma=1+.25j;q0=.2+.1j;cosine=.4-.3j;k=2*math.pi/L
 nodes,weights=np.polynomial.legendre.leggauss(32);x=nodes*L/2;z=(nodes+1)*t/2;wx=weights*L/2;wz=weights*t/2
 decay=np.sinh(k*(t-z))[:,None]/np.cosh(k*t);normal=np.cosh(k*(t-z))[:,None]/np.cosh(k*t)
 Ex=cosine/gamma*decay*np.sin(k*x)[None,:];Ez=q0/gamma+cosine/gamma*normal*np.cos(k*x)[None,:]
 direct=float(np.sum((abs(Ex)**2+abs(Ez)**2)*wz[:,None]*wx[None,:]));modal=modal_integral(np,q0,np.asarray([cosine/2]),np.asarray([cosine/2]),L,t,gamma)
 constant=modal_integral(np,q0,np.asarray([],dtype=complex),np.asarray([],dtype=complex),L,t,gamma);constant_exact=L*t*abs(q0/gamma)**2
 tol=1e-24+1e-10*max(abs(direct),abs(modal));require(abs(direct-modal)<=tol,'Independent analytic cosine vector-field quadrature contract');require(abs(constant-constant_exact)<=1e-24+1e-10*abs(constant_exact),'Independent constant-current slab contract')
 return dict(passed=True,constant=dict(modal_integral_V2=constant,analytic_integral_V2=constant_exact,absolute_error_V2=abs(constant-constant_exact)),constant_plus_cosine=dict(modal_integral_V2=modal,direct_vector_quadrature_integral_V2=direct,absolute_error_V2=abs(direct-modal)),new_PDE_RHS=0,synthetic_points=1024)

def _load(np,case,guard,deadline):
 check(guard,deadline);raw=case['raw'];path=Path(raw['path']);require(path.is_file()and path==path.resolve()and not path.is_symlink()and path.stat().st_size==raw['bytes']and sha_file(path)==raw['SHA256'],'Exact published original NPZ bytes required')
 keys=('panel_edges_m','q_panel_peak_A_m2','q_mode0_peak_A_m2','q_mode_positive_peak_A_m2','q_mode_negative_peak_A_m2')
 with np.load(path,allow_pickle=False)as data:arrays={name:np.asarray(data[name])for name in keys}
 meta=case['metadata'];P=meta['panels'];H=meta['positive_harmonics']
 require(arrays['panel_edges_m'].shape==(P+1,)and arrays['q_panel_peak_A_m2'].shape==(P,)and arrays['q_mode0_peak_A_m2'].shape==()and arrays['q_mode_positive_peak_A_m2'].shape==arrays['q_mode_negative_peak_A_m2'].shape==(H,),'Original panel/modal dimensions')
 require(all(np.isfinite(value).all()for value in arrays.values()),'All cached panel/modal fields finite')
 return dict(q0=complex(arrays['q_mode0_peak_A_m2']),plus=arrays['q_mode_positive_peak_A_m2'],minus=arrays['q_mode_negative_peak_A_m2'],edges=arrays['panel_edges_m'],q=arrays['q_panel_peak_A_m2'])

def _sampled_cross(np,a,b,guard,deadline):
 check(guard,deadline)
 with np.load(a['raw']['path'],allow_pickle=False)as da,np.load(b['raw']['path'],allow_pickle=False)as db:
  require(np.array_equal(da['x_m'],db['x_m'])and np.array_equal(da['z_m'],db['z_m']),'Cross-finest sampled coordinates must be physically identical')
  ae=da['Ex_peak_V_m'];az=da['Ez_peak_V_m'];be=db['Ex_peak_V_m'];bz=db['Ez_peak_V_m'];require(ae.shape==az.shape==be.shape==bz.shape==(128,512)and all(np.isfinite(v).all()for v in(ae,az,be,bz)),'Finite stored fixed-grid vector ABI')
  mean=float(np.mean(abs(ae-be)**2+abs(az-bz)**2));den=float(np.mean(abs(be)**2+abs(bz)**2));return dict(relative_L2=math.sqrt(mean/max(den,1e-300)),difference_vector_carrier_RMS_V_m=math.sqrt(mean/2),new_vector_carrier_RMS_V_m=math.sqrt(den/2),scope='Stored fixed512x128 samples, not modal integral; independently calculated cross-finest comparison')

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(spec==make_spec()and callable(guard),'Exact metadata-pinned cached QA specification and sole-owner guard');check(guard,deadline_monotonic)
 out=Path(output_dir);require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink()and out.parent==Path('/dev/shm')and out.name.startswith('task1-contact-modal-audit-'),'Owner-created unique output required')
 import numpy as np
 from panel_overlap import compare as compare_panels
 inputs,batches=_inventory();analytic=analytic_contract(np);physics=spec['physical'];L=physics['period_width_m'];t=physics['SC_thickness_m'];gamma=cv(physics['gamma_S_m']);zA=cv(physics['contact_ohm_m2']);cache={};rows=[];case_dir=out/'pairs';case_dir.mkdir(exist_ok=True)
 for label,batch in batches.items():
  for cid,case in batch['cases'].items():
   cache[label,cid]=_load(np,case,guard,deadline_monotonic);loaded=cache[label,cid];rms=math.sqrt(modal_integral(np,loaded['q0'],loaded['plus'],loaded['minus'],L,t,gamma)/(2*L*t));reported=case['metadata']['slab_field']['volume_L2_carrier_RMS_V_m'];require(abs(rms-reported)<=1e-10*max(rms,reported,1e-300),'Cached modal Parseval norm must reproduce original case statistic')
 for declaration in spec['pairs']:
  check(guard,deadline_monotonic);pid=declaration['pair_id'];a_key=declaration['old_batch'],declaration['old_case'];b_key=declaration['new_batch'],declaration['new_case'];a=cache[a_key];b=cache[b_key];modal=modal_difference(np,a,b,L,t,gamma);contact=compare_panels(a['edges'],a['q'],b['edges'],b['q'],zA,np,guard)
  old_meta=batches[a_key[0]]['cases'][a_key[1]]['metadata'];new_meta=batches[b_key[0]]['cases'][b_key[1]]['metadata'];index=declaration['original_adjacent_index']
  original=None if index is None else batches[a_key[0]]['original_adjacent_diagnostics'][index]
  if original is None:sampled=_sampled_cross(np,batches[a_key[0]]['cases'][a_key[1]],batches[b_key[0]]['cases'][b_key[1]],guard,deadline_monotonic)
  else:
   stored=[row for row in original['rows']if row['metric']=='same_grid_vector_field_relative_L2'];require(len(stored)==1,'Original sampled-vector diagnostic identity');sampled=dict(relative_L2=stored[0]['relative_difference'],original_flag=dict(stored[0]),scope='Original stored fixed512x128-grid diagnostic copied unchanged, not recomputed or replaced')
  # Contact power and percentile values are recomputed from original native
  # panel q on exact physical intervals, never from Fourier-projected surface q.
  for label,loaded,meta in(('old',a,old_meta),('new',b,new_meta)):
   actual=.5*zA*float(np.diff(loaded['edges'])@(abs(loaded['q'])**2));reported=cv(meta['contact_complex_power_W_per_m']);require(abs(actual-reported)<=1e-10*max(abs(actual),abs(reported),1e-300),'Native-panel contact power must reproduce original metadata')
  oldP=old_meta['contact_complex_power_W_per_m']['real'];newP=new_meta['contact_complex_power_W_per_m']['real'];oldJ=old_meta['contact_q_native_panel']['RMS_max_panel_A_m2'];newJ=new_meta['contact_q_native_panel']['RMS_max_panel_A_m2']
  # The helper provides a compact explicit metric ABI, checked below.
  primary=contact['summary']['primary'];relative_contact=primary['relative_L2']
  values=dict(exact_modal_vector_E_relative_L2=modal['summary']['relative_L2'],physical_panel_q_relative_L2=relative_contact,contact_real_power_relative=abs(newP-oldP)/max(abs(newP),1e-300),contact_panel_Jmax_relative=abs(newJ-oldJ)/max(abs(newJ),1e-300))
  flags=[dict(metric=key,value=float(value),limit=LIMITS[key],passed=bool(value<=LIMITS[key]))for key,value in values.items()]
  result=dict(pair_id=pid,old=dict(batch=a_key[0],case=a_key[1]),new=dict(batch=b_key[0],case=b_key[1]),exact_modal_vector_field=modal['summary'],physical_native_panel_contact=contact['summary'],raw_contact_pairwise_difference_convention='old A minus new B; norm is invariant to this sign, while modal coefficients are new minus old',sampled_vector_field=sampled,original_adjacent_diagnostics=original,diagnostic_flags=flags,all_new_diagnostic_flags_pass=all(row['passed']for row in flags),candidate_adopted=False)
  exported=dict(modal['arrays']);exported.update({'contact_'+key:value for key,value in contact['arrays'].items()});rawpath=case_dir/(pid+'.npz');metapath=case_dir/(pid+'.json');require(not rawpath.exists()and not metapath.exists(),'Preserve completed/partial cached audit; root must resume explicitly, never overwrite')
  with rawpath.open('xb')as f:np.savez_compressed(f,**exported)
  result['raw_difference_arrays_SHA256']=sha_file(rawpath);new_json(metapath,result);new_json(out/('checkpoint-%02d.json'%len(rows)),dict(pair_id=pid,status='cached_pair_complete',metadata_SHA256=sha_file(metapath),arrays_SHA256=result['raw_difference_arrays_SHA256'],new_PDE_RHS=0));rows.append(result)
 check(guard,deadline_monotonic)
 return dict(summary=dict(schema='task1-cached-contact-modal-audit-result-v1',status='nine_cached_modal_panel_comparisons_computed_unadopted',spec=spec,analytic_contract=analytic,pairs=rows,pair_count=len(rows),new_PDE_RHS=0,new_actual_four_pad_CEM_RHS=0,original_flags_preserved={key:dict(all_diagnostic_flags_pass=batch['original_all_flags'],adjacent_diagnostics=batch['original_adjacent_diagnostics'])for key,batch in batches.items()},all_new_diagnostic_flags_pass=all(row['all_new_diagnostic_flags_pass']for row in rows),limitations=spec['limitations'],candidate_adopted=False,Windows_saved_verified=False),arrays={})
