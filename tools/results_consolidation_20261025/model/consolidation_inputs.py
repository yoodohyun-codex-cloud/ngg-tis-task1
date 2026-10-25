"""Deferred full-publication input inventory for analysis of 15 geometries.

Only metadata is parsed here. No imports construct scientific arrays, masks,
fields, angular metrics or PDE solves. Root alone verifies/decode stored blobs.
"""
from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
SOURCE=Path('/dev/shm/task1-results-consolidation-20261025/source')
FIRST=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
MP=Path('/dev/shm/task1-multipad-extension-20261025-run')
REC=Path('/dev/shm/task1-peripheral-recovery-20261025-run')
FAILED=Path('/dev/shm/task1-peripheral-fourpad-20261025-run')
MIX=Path('/dev/shm/task1-mixed-fourpad-r2-20261025-run')
PARTIAL=Path('/dev/shm/task1-local-lease-and-cloud-failure-20261025-run/failure-publication/result-publication.json')
B0='B0-square15-c10-diagonal'
FIRST_IDS=(B0,'G1-square12-c10-diagonal','G2-square15-c8-diagonal','G3-square16-c9p5-diagonal','G4-equalarea-rect12p5x18-c9p75x9p5-diagonal','G5-signal200-return250','G6-signal250-return200','G7-square15-c10-adjacent')
MP_IDS=('MP8-vertical-strips','MP12-vertical-strips','MP16-subpad2x2')
REC_IDS=('P23p5-peripheral-polyomino225','P12-square-c11p5-diagonal')
MIX_IDS=('M_Speriph_Rsquare','M_Ssquare_Rperiph')
ALL_IDS=FIRST_IDS+MP_IDS+REC_IDS+MIX_IDS
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
GRID_KEYS=['grid']+[k+'_volume_weight_m3'for k in REGIONS]
MAX_META=8*1024**2;MAX_BLOB=80*1024**2
KNOWN={
 'FIRST8':dict(root=FIRST,S=('c8e5f2f9d4fbba5646944772d526533ecedbbab1','cb8939fdd21b3c4d7103eeb26c3591037402553d4369aa195888e30930b1eb49'),R=('4d6207caa60ae16ab7a7e997022ac72653b97ec3','d20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159')),
 'MULTIPAD':dict(root=MP,S=('ccc315467edab41b573ff58760baa635bd721b36','34f5ab39be690a594feccef70736479ff145b32815ff832ccd11c0ab53581a0e'),R=('9299ac1ae665fbad5e083e2683ea5789a61e54ad','bbc67386d2dcefbf910a6d6f5698a99c7d852ef14803a417a8d0e5ae90922640')),
 'RECOVERY':dict(root=REC,S=('0d689d4427d769965af88b991b6fe7bc72b5850c','2622f798c79715a20c6b4f7ab2cf91b2e25f52ccc0fe7d560f76d616cb6760a2'),R=('b30e7b7bd200170ff2b45f2a103c37ddff582a3f','5da8f476cacd4ee323d781f08f3a0a89e7e02d64c1b3a1674069d10ee1eb698d')),
 'MIXED':dict(root=MIX,S=('f1fc0c6b2ac6770ff3dd13071a49793d269e7570','bfb4a695fdb4e82b7f61390acdcf97401141b4b4f559d3422de4662509640641')),
}

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def read_json(path,expected_sha):
 p=Path(path);require(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=MAX_META,'Bounded nonempty regular metadata')
 raw=p.read_bytes();require(hashlib.sha256(raw).hexdigest()==expected_sha,'Metadata SHA before parsing');return json.loads(raw)
def source_pins():
 p=SOURCE/'consolidation_inputs.py';return{str(p):digest(p)}

def validate_admission(a):
 require(isinstance(a,dict)and a.get('schema')=='task1-results-consolidation-root-admission-v1'and a.get('status')=='selected_finite_results_consolidation'and a.get('root_selected')is True,'Root selection after actual mixedR2 publication')
 require(a.get('mixed_run')==str(MIX)and a.get('new_PDE_RHS')==0 and a.get('new_metric_evaluations')==0 and a.get('candidate_adopted')is False,'Consolidation only; no PDE/angular rerun or adoption')
 for key,n in(('mixed_result_publication_sha256',64),('mixed_result_commit',40)):
  require(isinstance(a.get(key),str)and len(a[key])==n and all(c in'0123456789abcdef'for c in a[key]),'Explicit actual mixedR2 identity')
 require(Path(a['mixed_result_publication_path'])==MIX/'result-publication/result-publication.json','MixedR2 actual receipt, never failedv1')
 require(isinstance(a.get('decision_basis'),str)and a['decision_basis'].strip(),'Root actual-result analysis rationale required');return a

def published_file_matches(publication,relative,expected_sha=None):
 require(publication.get('status')=='published_readback_verified','Only complete independent publication readback accepted')
 matches=[(t,r)for t,r in publication.get('files',{}).items()if t.endswith('/'+relative)]
 require(len(matches)<=1,'Ambiguous published relative identity')
 if not matches:return None
 target,row=matches[0];require(row.get('readback_passed')is True and type(row.get('bytes'))is int and 0<row['bytes']<=MAX_BLOB and isinstance(row.get('SHA256'),str)and len(row['SHA256'])==64,'Full bounded file readback proof')
 require(expected_sha is None or row['SHA256']==expected_sha,'Published identity conflict')
 return dict(target=target,SHA256=row['SHA256'],bytes=row['bytes'],publication_commit=publication['commit'],readback_passed=True)

def classify_records(records):
 """First occurrence canonical; exact ID+scalarSHA aliases; conflicts retained."""
 canonical=[];aliases=[];variants=[];byid={};seen={}
 for record in records:
  cid=record['candidate_id'];key=(cid,record['scalar']['SHA256'])
  if key in seen:
   require(record['mask']['SHA256']==seen[key]['mask']['SHA256'],'Same scalar identity has conflicting physical mask')
   aliases.append(dict(candidate_id=cid,identity_key=list(key),canonical_dataset=seen[key]['provenance']['dataset_id'],alias_dataset=record['provenance']['dataset_id'],record=record))
  elif cid in byid:
   require(record['mask']['SHA256']==byid[cid]['mask']['SHA256'],'Same candidate ID cannot hide a different physical mask behind a scalar variant')
   variants.append(dict(candidate_id=cid,canonical_scalar_SHA256=byid[cid]['scalar']['SHA256'],variant_scalar_SHA256=key[1],record=record,status='same_ID_different_scalar_identity_preserved_not_silently_merged'));seen[key]=record
  else:canonical.append(record);byid[cid]=record;seen[key]=record
 return canonical,aliases,variants

def make_spec(admission=None):
 ap=SOURCE/'root-admission.json'
 if admission is None:
  require(ap.is_file(),'Positive root consolidation admission required');admission=read_json(ap,digest(ap))
 admission=validate_admission(admission);pins=source_pins();registry=[];dataset_receipts={};fileproofs={}
 def register(dataset_id,role,root,path,commit,receipt_sha):
  pub=read_json(path,receipt_sha);require(pub.get('status')=='published_readback_verified'and pub.get('commit')==commit,'Actual verified '+dataset_id+'/'+role+' publication')
  pins[str(path)]=receipt_sha;entry=dict(dataset_id=dataset_id,role=role,root=root,path=str(path),SHA256=receipt_sha,commit=commit,publication=pub);registry.append(entry);return entry
 for name,known in KNOWN.items():
  root=known['root'];scommit,ssha=known['S'];s=register(name,'source',root,root/'source-publication/result-publication.json',scommit,ssha)
  if name=='MIXED':rcommit=admission['mixed_result_commit'];rsha=admission['mixed_result_publication_sha256'];rp=Path(admission['mixed_result_publication_path'])
  else:rcommit,rsha=known['R'];rp=root/'result-publication/result-publication.json'
  r=register(name,'result',root,rp,rcommit,rsha);dataset_receipts[name]=dict(source={k:v for k,v in s.items()if k not in('publication','root')},result={k:v for k,v in r.items()if k not in('publication','root')})
 register('PERIPHERAL_PARTIAL','source',FAILED,FAILED/'source-publication/result-publication.json','3329379d39bd8632dc75308e32dc4e30fb9296e7','d73f9f51cca8909849c66de98ee75bf4b4533ef07160cd098d16d7cb332f4753')
 register('PERIPHERAL_PARTIAL','result',FAILED,PARTIAL,'2d8ad63f714e549c60e1db4d78792a193ed83c2c','2cae4bdbc3580ec14653eb5b23e1b48ca15c2851323bf89386e2e02e52040a07')
 def authenticate(path,expected=None):
  p=Path(path);found=[]
  for entry in registry:
   if p.is_relative_to(entry['root']):
    proof=published_file_matches(entry['publication'],p.relative_to(entry['root']).as_posix(),expected)
    if proof is not None:found.append(dict(dataset_id=entry['dataset_id'],role=entry['role'],**proof))
  require(found,'No full direct readback proof for actual path '+str(p));identities={(r['SHA256'],r['bytes'])for r in found};require(len(identities)==1,'Source/result disagree about immutable file')
  sha,size=next(iter(identities));require(p.is_file()and not p.is_symlink()and p.stat().st_size==size,'Actual published regular-file size')
  pins[str(p)]=sha;descriptor=dict(path=str(p),SHA256=sha,bytes=size,proofs=found,publication_commit=found[-1]['publication_commit']);fileproofs[str(p)]=descriptor;return descriptor
 def metadata(path):
  desc=authenticate(path);return read_json(path,desc['SHA256'])
 summaries={name:metadata(known['root']/'summary.json')for name,known in KNOWN.items()}
 require(summaries['FIRST8']['status']=='provisional_eight_layout_screen_computed_unadopted'and summaries['FIRST8']['completed_candidates']==8,'Eight original geometries actually complete')
 require(summaries['MULTIPAD']['status']=='provisional_four_recipe_multipad_screen_computed_unadopted'and summaries['MULTIPAD']['completed_candidates']==4,'Actual grouped8/12/16 family complete')
 require(summaries['RECOVERY']['status']=='peripheral_recovery_computed_without_P23_PDE_repeat'and summaries['RECOVERY']['completed_conditions']==4,'Actual peripheral recovery complete')
 require(summaries['MIXED']['status']=='mixed_fourpad_screen_computed_unadopted'and summaries['MIXED']['completed_conditions']==4 and summaries['MIXED']['actual_new_driven_RHS']==4 and summaries['MIXED']['actual_new_metric_evaluations']==2,'Actual mixedR2 complete, not source/preflightonly')
 def catalog(summary):
  spec=summary['spec'];return spec['recovery_inputs']['catalog']if'recovery_inputs'in spec else spec['catalog']
 def version(summary):
  spec=summary['spec']
  if'recovery_inputs'in spec:return spec['recovery_inputs']['original_spec']['provisional_field']['derived_field_version']
  return(spec.get('provisional_field')or spec['catalog']['provisional_field'])['derived_field_version']
 basecat=catalog(summaries['FIRST8']);baseversion=version(summaries['FIRST8']);model_metadata={};gridkeys=('h_mm','nx','nxy','layer_counts','cells','radius_mm','layer_thickness_mm')
 for name,summary in summaries.items():
  cat=catalog(summary)
  for key in('gamma_by_frequency','z_by_frequency','common_ROI','drives','source_resistance_ohm'):require(cat[key]==basecat[key],'Same material/contact/ROI/circuit metadata '+name+'/'+key)
  require(all(cat['grid'][k]==basecat['grid'][k]for k in gridkeys)and version(summary)==baseversion,'Same physical grid and reconstructed field ABI '+name)
  batch=authenticate(KNOWN[name]['root']/'spec.json');material_desc=authenticate(cat['material_path'],cat['material_sha256']);contact_desc=authenticate(cat['contact_path'],cat['contact_sha256']);material=read_json(material_desc['path'],material_desc['SHA256']);contact=read_json(contact_desc['path'],contact_desc['SHA256'])
  model_metadata[name]=dict(registered_batch_spec=batch,material_input_SHA256=material_desc['SHA256'],contact_input_SHA256=contact_desc['SHA256'],material_receipt_schema=material.get('schema'),material_version=material.get('material_model_id')or material.get('model_id')or material.get('version'),material_version_if_absent='No separate version declared; use receipt SHA/schema',contact_schema=contact.get('schema'),contact_model_version=contact.get('model_version')or contact.get('version'),contact_version_if_absent='No separate version declared; use receipt SHA/schema',body_and_grid=copy.deepcopy(cat['grid']),common_ROI=copy.deepcopy(cat['common_ROI']),field_version=baseversion,source_drives=copy.deepcopy(cat['drives']),source_resistance_ohm=cat['source_resistance_ohm'],return_topology=cat.get('return_topology'))
 allrecords=[]
 raw_sources={str(FIRST):KNOWN['FIRST8']['S'][0],str(MP):KNOWN['MULTIPAD']['S'][0],str(REC):KNOWN['RECOVERY']['S'][0],str(MIX):KNOWN['MIXED']['S'][0],str(FAILED):'3329379d39bd8632dc75308e32dc4e30fb9296e7'}
 for name,summary in summaries.items():
  for row in summary['candidates']:
   cid=row['candidate_id'];require(cid in ALL_IDS,'Unknown geometry cannot silently enter consolidation')
   scalar=authenticate(row['scalar_arrays']['path'],row['scalar_arrays']['SHA256']);geometry=row['geometry'];mask=authenticate(geometry['mask_path'],geometry['mask_sha256']);raw={}
   for f in(2000,2010):
    item=summary.get('raw_artifacts',{}).get(cid+'-'+str(f))
    if item is None:item=(row.get('original_raw_by_frequency')or row.get('original_raw'))[str(f)]
    raw[str(f)]=authenticate(item['path'],item['SHA256'])
   # Direct source and result proofs remain attached even when controls alias.
   configuration_identity=dict(schema='task1-composite-input-identity-v1',batch_spec_SHA256=model_metadata[name]['registered_batch_spec']['SHA256'],mask_SHA256=mask['SHA256'],material_input_SHA256=model_metadata[name]['material_input_SHA256'],contact_input_SHA256=model_metadata[name]['contact_input_SHA256'],field_version=baseversion)
   configuration_sha=hashlib.sha256(json.dumps(configuration_identity,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
   record=dict(candidate_id=cid,record=copy.deepcopy(row),scalar=scalar,raw_by_frequency=raw,mask=mask,padmetadata=copy.deepcopy(geometry['pads']),identity_key=[cid,scalar['SHA256']],provenance=dict(dataset_id=name,source_run_id=KNOWN[name]['root'].name,**copy.deepcopy(model_metadata[name]),configuration_identity=configuration_identity,configuration_identity_SHA256=configuration_sha,configuration_identity_definition='SHA256 of canonical JSON identity tuple; this is not a fabricated per-case configuration file',source_commit=dataset_receipts[name]['source']['commit'],result_commit=dataset_receipts[name]['result']['commit'],summary=fileproofs[str(KNOWN[name]['root']/'summary.json')],physical_pads=row.get('physical_pad_count',geometry.get('physical_pad_count',len(geometry['pads']))),independent_outputs=2,original_source_payload_retained=True,metric_dataset_source_commit=dataset_receipts[name]['source']['commit'],raw_export_source_commit_by_frequency={f:next(source for root,source in raw_sources.items()if Path(d['path']).is_relative_to(Path(root)))for f,d in raw.items()},raw_export_source_label='Source that exported stored response; reused old carrier PDE is not counted as a new solve'))
   allrecords.append(record)
 canonical,aliases,variants=classify_records(allrecords);require(tuple(r['candidate_id']for r in canonical)==ALL_IDS and len(canonical)==15,'Exactly eight+three+two+two native geometries; aliases not counted twice')
 grids=[]
 for name,summary in summaries.items():
  if name in('FIRST8','MULTIPAD'):path=KNOWN[name]['root']/'common-grid-and-ROI.npz'
  elif name=='RECOVERY':path=Path(summary['spec']['recovery_inputs']['common_grid_ROI']['path'])
  else:path=Path(summary['spec']['catalog']['common_grid_ROI']['path'])
  desc=authenticate(path);grids.append(dict(dataset_id=name,**desc,requiredkeys=list(GRID_KEYS),optionalkeys=['ij','z_faces_m'],comparison_required='Root must compare grid+six physical ROI weight arrays, not archive SHA alone'))
 roi=metadata(FIRST/'ROI-receipt.json');local=copy.deepcopy(admission.get('reported_local_candidates',[]));require(isinstance(local,list),'Local user reports remain a separate list')
 if ap.exists():require(read_json(ap,digest(ap))==admission,'Root admission bytes agree');pins[str(ap)]=digest(ap)
 return dict(schema='task1-results-consolidation-inputs-v1',root_admission=admission,canonical_candidates=canonical,all_candidate_records=allrecords,aliases=aliases,identity_variants=variants,canonical_candidate_count=15,input_sha256=pins,datasets=dataset_receipts,model_metadata=model_metadata,publication_file_proofs=fileproofs,common_grid_ROI=grids[0],common_grids=grids,ROI_receipt=roi,common_ROI=copy.deepcopy(basecat['common_ROI']),grid=copy.deepcopy(basecat['grid']),gamma_by_frequency=copy.deepcopy(basecat['gamma_by_frequency']),z_by_frequency=copy.deepcopy(basecat['z_by_frequency']),field_version=baseversion,frequencies=[2000,2010],baseline_candidate_id=B0,reported_local_candidates=local,reported_local_scope='User-reported native fields/circuit/normalization pending verification; separate unranked list, no invented data or physiology claim',new_PDE_RHS=0,new_metric_evaluations=0,no_new_angular_search=True,holds={name:copy.deepcopy(s.get('holds',{}))for name,s in summaries.items()},candidate_adopted=False,Windows_saved_verified=False)

def required_inputs(admission=None):return dict(make_spec(admission)['input_sha256'])
