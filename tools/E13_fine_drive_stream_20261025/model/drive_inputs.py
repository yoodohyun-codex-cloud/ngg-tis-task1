"""Metadata-only immutable inputs for one cached E13 fine drive batch.

Neither this module's import nor make_spec/required_inputs opens native files.
Native bytes are authenticated only by the post-MFG coordinator.
"""
import hashlib,json
from pathlib import Path
from drive_contracts import require,fullhex,validate_descriptor

SOURCE=Path('/workspace/ngg-tis-task1/runtime/E13-fine-drive-stream-20261025/source')
OUT=Path('/dev/shm/task1-E13-fine-drive-stream-20261025-run')
FINE=Path('/dev/shm/task1-E13-fineXY-20261025-run')
GRID_RUN=Path('/dev/shm/task1-P23-fineXY-20261025-run')
CID='E13-tangent-P23-centroids-225-XY102-Z97'
PREFIX='data-native/E13-fineXY-20261025/'
CELLS=793848
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
WITNESSES={
 'E13_S':(FINE/'source-publication/result-publication.json','e85b52386ccf76452fd7391f8f8a3df756b4b07c6d238bfd19aae1fb52007b8f','50a930fbe1fe08b0b0af2d00d99c79eec3b96fb4'),
 'E13_R':(FINE/'result-publication/result-publication.json','128c64313c836a48f8cd3799ec6b18c0b583ec3a679dbc0f27a93c5f06956135','f394cc9c2570f47a29968bea134a8078b98826d4'),
 'grid_R':(GRID_RUN/'result-publication/result-publication.json','0a9f71adef7439f19c2334ffef96c5f83e271c75c2440af3582615bfb998e075','fd0b0becc1f38d5c8118c929e7c5c4f24cc64c47'),
 'post_S':(Path('/dev/shm/task1-E13-fine-light-post-20261025-run/source-publication/result-publication.json'),'d564f21313a6fddecce37a2ce04342b25ffc8691da3b7b678aaab3acbf22e853','10699c7cc15aba1853a75c679a67fdc0db4be1f0'),
 'post_R':(Path('/dev/shm/task1-E13-fine-light-post-20261025-run/result-publication/result-publication.json'),'1e08a842caed439f02b41ed55d216c626d86e317140dad35811ec0971a529dc0','1be99e442c88bc94b8ddecb4607671c3cf102b9d'),
 'safe_T':(Path('/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025-run/auto-transfer/T/result-publication.json'),'5040ebae6705827ed66339e4755e7088b9c9460f9e7145d38000934c327947b5','60235804f9e2f53aa4ef3356d1b11ea1c3ab8c65')}

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()

def metadata(path,expected=None):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and not p.is_symlink()and p.suffix=='.json'and 0<p.stat().st_size<8*1024**2,'Bounded canonical metadata JSON only')
 raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest();require(expected is None or sha==expected,'Exact metadata SHA '+str(p))
 return json.loads(raw),sha

def source_inventory():
 return {str(p):digest(p)for p in sorted(SOURCE.iterdir())if p.is_file()and p.suffix in('.py','.md','.json')and p.name not in('root-admission.json','SOURCE-HASHES.json')}

def validate_admission(a):
 require(type(a)is dict and a.get('schema')=='task1-E13-fine-drive-stream-root-admission-v1'and a.get('status')=='selected_finite_E13_fine_cached_drive_stream','Explicit finite cached-drive root decision')
 require(a.get('root_authorized')is True and a.get('safe_boundary_confirmed')is True and a.get('candidate_adopted')is False,'Positive safe-boundary selection without adoption')
 require(a.get('ratio_multipliers')==[.8,1.25]and a.get('baseline_multiplier')==1. and a.get('maximum_source_Vpp')==1.,'Fixed baseline and two attenuation-only relative allocations')
 for k in('new_PDE_RHS','new_Q_loads','new_eigen_solves'):
  require(type(a.get(k))is int and a[k]==0,'No hidden numerical field work '+k)
 require(type(a.get('decision_basis'))is str and a['decision_basis'].strip()and type(a.get('source_sha256'))is dict,'Root rationale and full canonical model source map')
 return a

def publication_descriptor(pub,path,target,*,role,expected_role,expected_sha=None):
 require(pub.get('status')=='published_readback_verified'and fullhex(pub.get('commit'),40),'Actual complete immutable publication')
 row=pub.get('files',{}).get(target);require(type(row)is dict,'Actual exact publication target '+target)
 d=dict(path=str(path),SHA256=row.get('SHA256'),bytes=row.get('bytes'),publication_commit=pub['commit'],publication_target=target,readback_passed=row.get('readback_passed'),publication_role=role)
 validate_descriptor(d,expected_commit=pub['commit'],expected_target=target,publication_role=role,expected_role=expected_role)
 require(expected_sha is None or d['SHA256']==expected_sha,'Known native identity '+target)
 return d

def make_spec(admission=None):
 pins={};a=admission
 if a is None:
  a,sha=metadata(SOURCE/'root-admission.json');pins[str(SOURCE/'root-admission.json')]=sha
 validate_admission(a);sources=source_inventory();require(a['source_sha256']==sources,'Root-selected complete canonical source identity')
 pubs={}
 for name,(path,sha,commit)in WITNESSES.items():
  value,actual=metadata(path,sha);require(value.get('status')=='published_readback_verified'and value.get('commit')==commit,'Exact original source/result publication witness '+name);pubs[name]=value;pins[str(path)]=actual
 S,R,G=(pubs[k]for k in('E13_S','E13_R','grid_R'))
 safe_path=Path('/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025-run/auto-transfer/E13-fine-GUI-eight-20261025-transfer-manifest.json')
 safe=publication_descriptor(pubs['safe_T'],safe_path,'docs/TASK1_CONTACT_EDGE_20261025/E13-fine-GUI-eight-20261025-transfer-manifest.json',role='result',expected_role='result',expected_sha='b077f66a460bb1aab70c93d37b0e0991495a3aa04d3c4c11f30c7a523ff84e1a')
 require(safe_path.stat().st_size==2079504 and digest(safe_path)==safe['SHA256'],'Actual complete prior manifest bytes; references only, no old alias copies');pins[str(safe_path)]=safe['SHA256']
 postpath=Path('/dev/shm/task1-E13-fine-light-post-20261025-run/summary.json')
 postdesc=publication_descriptor(pubs['post_R'],postpath,'data-native/E13-fine-light-post-20261025/summary.json',role='result',expected_role='result')
 post,sha=metadata(postpath,postdesc['SHA256']);pins[str(postpath)]=sha
 require(post.get('status')=='E13_fine_cached_highvolume_and40probe_postbatch_computed_unadopted'and post.get('calculated_probes')==40 and post.get('candidate_adopted')is False,'Actual completed E13 fine post result retained as context, not recomputed')
 def saved(name,owner=R,role='result'):
  d=publication_descriptor(owner,FINE/name,PREFIX+name,role=role,expected_role=role)
  value,sha=metadata(d['path'],d['SHA256']);require(Path(d['path']).stat().st_size==d['bytes'],'Actual metadata publication byte count');pins[d['path']]=sha;return value,d
 oldspec,specdesc=saved('spec.json',S,'source');raw_manifest,manifestdesc=saved('raw-manifest.json');baseline,baselinedesc=saved(CID+'-summary.json')
 require(oldspec.get('candidate_id')=='E13-tangent-P23-centroids-225'and oldspec.get('fine_cells')==CELLS and oldspec.get('physical_pads')==4 and oldspec.get('independent_outputs')==2 and oldspec.get('source_resistance_ohm')==50.,'Original physical E13 fine identity/circuit')
 require(baseline.get('candidate_id')==CID and baseline.get('sampled_directions')==2074 and baseline.get('candidate_adopted')is False,'Actual original fine complete2074 scalar producer')
 require(baseline.get('saved_scalar_names')==['AM_max2074','carrier_RMS','Jtotal_vector_RMS','AM_direction_index'],'Actual original archive contains three Float64 maps and winner only; no invented saved axes/carrier splits')
 stats=('maxTIS','RMS','X_TIS','Y_TIS','Z_TIS','carrier0_RMS','carrier1_RMS','Jtotal_vector_RMS')
 require(all(set(region['statistics'])==set(stats)for region in baseline['metrics']['regions'].values()),'All eight original scalar summaries are available for complete ROI agreement')
 raw={};proofs=[]
 for f,sha in((2000,'2ab1dcaad605971d6d44a8267593c2b565057fd9197aef21e4cfea116f625afb'),(2010,'b37d975fcfe4e6c8f3fb8747635f95dcefb2c9fceaf9e146b7aa70a31acec314')):
  name='rhs/E13-XY102-'+str(f)+'-raw.npz';d=publication_descriptor(R,FINE/name,PREFIX+name,role='result',expected_role='result',expected_sha=sha)
  require(raw_manifest['fine']['E13'][str(f)]['raw']['SHA256']==sha,'Original raw manifest source binding')
  d.update(member='E_peak_V_m.npy',shape=[CELLS,3],dtype='<c16',fortran_order=False);raw[str(f)]=d
  proof,pd=saved('rhs/E13-XY102-'+str(f)+'-proof.json');require(proof.get('passed')is True and proof.get('driven_output')==(f-2000)//10,'Original complete source physical gates');proofs.append(proof)
 scalar=publication_descriptor(R,FINE/(CID+'-scalars.npz'),PREFIX+CID+'-scalars.npz',role='result',expected_role='result',expected_sha='36f8545581bc205cf44a8a3fa0f7975d111ebe3f288462b2f871c2447f0af382')
 grid=publication_descriptor(G,GRID_RUN/'fine-common97-grid-ROI.npz','data-native/P23-fineXY-20261025/fine-common97-grid-ROI.npz',role='result',expected_role='result',expected_sha='3c7fe58008698b4a4c345fe164e83f049a1ca6f6e9bf960d01ded3f9f4de411b')
 mask=publication_descriptor(R,FINE/'fine-E13-contact-mask.csv',PREFIX+'fine-E13-contact-mask.csv',role='result',expected_role='result')
 gamma=oldspec['inputs']['gamma_by_frequency'];require(set(gamma)=={'2000','2010'}and all(len(v)==4 for v in gamma.values()),'Unchanged exact two-frequency/four-layer admittivities')
 native=[raw['2000'],raw['2010'],scalar,grid,mask]
 for d in native:
  p=Path(d['path']);require(p.is_absolute()and p==p.resolve()and not p.is_symlink()and p.is_file()and p.stat().st_size==d['bytes'],'Native stat-only identity before MFG; no byte hash/decode')
 return dict(schema='task1-E13-fine-drive-stream-spec-v1',root_admission=a,source_sha256=sources,model_source_sha256=sources,metadata_input_sha256=pins,native_input_descriptors=native,
  candidate_id=CID,raw_by_frequency=raw,grid=grid,baseline_scalars=scalar,mask=mask,proofs=proofs,gamma_by_frequency=gamma,baseline_record=baseline,
  coarse_B0_reference=oldspec['inputs']['coarse_B0_record']['metrics'],fine_B0_reference=oldspec['inputs']['fine_B0_record']['metrics'],inherited_holds=oldspec['inputs']['inherited_holds'],
  baseline_multiplier=1.,ratio_multipliers=[.8,1.25],baseline_saved_float_maps=['AM_max2074','carrier_RMS','Jtotal_vector_RMS'],unavailable_saved_float_maps=['AM_x','AM_y','AM_z','carrier0_RMS','carrier1_RMS'],baseline_scalar_summary_count=8,expected_conditions=3,expected_new_metric_evaluations=2,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,cells=CELLS,
  physical_pads=4,independent_outputs=2,frequencies_Hz=[2000,2010],source_resistance_ohm=50.,source_peak_V=.5,maximum_source_Vpp=1.,target='native fractional r<=5mm, depth15..20mm; original weights without renormalization',
  per_condition_seconds=900,total_numeric_seconds=3000,chunk_rows=128,direction_block=2074,lazy_weights_required=True,output_arrays=['AM_max2074','carrier_RMS'],new_owned_tmp_forecast_bytes=35000000,output_forecast_is_quota=False,child_RSS_forecast_bytes=220000000,forecasts_measured=False,
  source_proofs=dict(E13_source=specdesc,E13_raw_manifest=manifestdesc,baseline_record=baselinedesc,prior_post=postdesc,prior_complete_manifest=safe),candidate_adopted=False)

def required_inputs(admission=None):
 spec=make_spec(admission);return dict(spec['metadata_input_sha256'])
