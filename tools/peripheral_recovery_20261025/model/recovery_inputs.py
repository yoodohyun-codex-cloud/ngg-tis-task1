"""Deferred, published-provenance inputs for one finite peripheral recovery.

No NumPy, arrays, geometry derivation or file reads execute on import. Only the
root owner calls make_spec after partial-result publication. Two completed RHS
are reused verbatim; this module never authorizes their recalculation.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path

SOURCE=Path('/dev/shm/task1-peripheral-recovery-20261025/source')
FAILED=Path('/dev/shm/task1-peripheral-fourpad-20261025-run')
FAILED_SOURCE_COMMIT='3329379d39bd8632dc75308e32dc4e30fb9296e7'
SOURCE_PUBLICATION_SHA='d73f9f51cca8909849c66de98ee75bf4b4533ef07160cd098d16d7cb332f4753'
FAILED_MODEL_SHA='67dee0999a460b42442911f51b37c99e22a1b216b6edf616a8a2fb2f1a83cae7'
FAILED_SPEC_SHA='0d0b63e097df5d910b9a903b9b9e18feb8cde684cf6794dfde6c23e617f4a7de'
REUSE='P23p5-peripheral-polyomino225'
NEW='P12-square-c11p5-diagonal'
BLOCKED='P24-peripheral-polyomino225'
CONTROLS=('B0-square15-c10-diagonal','G1-square12-c10-diagonal')
MAX_METADATA_BYTES=8*1024**2
MAX_NATIVE_BYTES=80*1024**2

def require(ok,message):
 if not ok:raise ValueError(message)

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for chunk in iter(lambda:stream.read(1024**2),b''):h.update(chunk)
 return h.hexdigest()

def read_json(path,expected_sha=None):
 p=Path(path);require(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=MAX_METADATA_BYTES,'Bounded nonempty regular metadata file')
 raw=p.read_bytes();require(expected_sha is None or hashlib.sha256(raw).hexdigest()==expected_sha,'Exact metadata SHA256 before parsing')
 return json.loads(raw)

def validate_admission_fields(admission):
 require(isinstance(admission,dict)and admission.get('schema')=='task1-peripheral-recovery-root-admission-v1'and admission.get('status')=='selected_finite_peripheral_recovery'and admission.get('root_selected')is True,'Explicit root finite recovery selection required')
 require(admission.get('failed_run')==str(FAILED)and admission.get('failed_source_commit')==FAILED_SOURCE_COMMIT,'Exact failed run/source, no substituted prior calculation')
 require(admission.get('new_RHS')==2 and admission.get('reused_RHS')==2 and admission.get('new_metric_evaluations')==2 and admission.get('control_aliases')==2 and admission.get('candidate_adopted')is False,'Recovery scope: two reused RHS, two new RHS, two metrics, two original control aliases')
 require(admission.get('source_allocation_amplitudes')==[1.,1.],'Original equal raw voltage allocation retained')
 require(isinstance(admission.get('decision_basis'),str)and admission['decision_basis'].strip(),'Actual failed-stage recovery rationale required')
 for key,length in(('partial_result_publication_sha256',64),('partial_result_commit',40)):
  value=admission.get(key);require(isinstance(value,str)and len(value)==length and all(c in'0123456789abcdef'for c in value),'Explicit publication identity '+key)
 path=Path(admission['partial_result_publication_path']);require(path.is_absolute()and path==path.resolve()and not path.is_symlink(),'Canonical partial publication receipt path')
 return admission

def published_file_proof(publication,relative,expected_sha=None):
 """Exactly one direct full-readback proof; never accept receipt presence alone."""
 require(publication.get('status')=='published_readback_verified','Publication must have completed independent readback')
 matches=[(target,row)for target,row in publication.get('files',{}).items()if target.endswith('/'+relative)]
 require(len(matches)==1,'Unique direct published identity for '+relative)
 target,row=matches[0];require(row.get('readback_passed')is True,'Full readback must pass for '+relative)
 sha=row.get('SHA256');size=row.get('bytes');require(isinstance(sha,str)and len(sha)==64 and isinstance(size,int)and not isinstance(size,bool)and 0<size<=MAX_NATIVE_BYTES,'Bounded published SHA/byte record')
 require(expected_sha is None or sha==expected_sha,'Published identity differs from frozen SHA for '+relative)
 return dict(target=target,SHA256=sha,bytes=size,publication_commit=publication['commit'],readback_passed=True)

def unfinished_stage_proof(publication,exists=None):
 """Reject any evidence that a nominally missing solve/metric already ran."""
 absent=[]
 for f in(2000,2010):
  for suffix in('-solve-proof.json','-surface-state.npz','-raw.npz'):
   absent.append('rhs/'+NEW+'-'+str(f)+suffix)
  absent.append('checkpoint-'+NEW+'-'+str(f)+'.json')
 for cid in(REUSE,NEW):
  absent.extend(('candidates/'+cid+'-scalars.npz','candidates/'+cid+'-summary.json','checkpoint-'+cid+'-metrics.json'))
 probe=exists if exists is not None else lambda relative:(FAILED/relative).exists()
 for relative in absent:
  require(not any(target.endswith('/'+relative)for target in publication.get('files',{})),'Already published nominally-uncomputed artifact; cannot replay '+relative)
  require(not probe(relative),'Already present nominally-uncomputed artifact; cannot replay '+relative)
 return dict(status='exact_partial_stage_absence_verified',relative_paths_absent=absent,old_tree_read_only_required=True)

def make_spec(admission=None):
 if admission is None:admission=read_json(SOURCE/'root-admission.json')
 admission=validate_admission_fields(admission);partial_path=Path(admission['partial_result_publication_path']);partial=read_json(partial_path,admission['partial_result_publication_sha256'])
 require(partial.get('status')=='published_readback_verified'and partial.get('commit')==admission['partial_result_commit'],'Exact completed partial-result publication, not a prepared upload')
 absence=unfinished_stage_proof(partial)
 source_path=FAILED/'source-publication/result-publication.json';source=read_json(source_path,SOURCE_PUBLICATION_SHA);require(source.get('commit')==FAILED_SOURCE_COMMIT and source.get('status')=='published_readback_verified','Original source publication before prior RHS')
 pins={str(partial_path):admission['partial_result_publication_sha256'],str(source_path):SOURCE_PUBLICATION_SHA};proofs={}
 def record(relative,*,which='partial',expected=None,parse=False):
  publication=partial if which=='partial'else source;proof=published_file_proof(publication,relative,expected);path=FAILED/relative
  require(path.is_file()and not path.is_symlink()and path.stat().st_size==proof['bytes'],'Original published regular-file bytes '+relative)
  pins[str(path)]=proof['SHA256'];proofs[relative]=dict(path=str(path),**proof)
  return read_json(path,proof['SHA256'])if parse else dict(path=str(path),**proof)
 original=record('spec.json',which='source',expected=FAILED_SPEC_SHA,parse=True)
 catalog=record('catalog-inputs.json',which='source',parse=True);require(original['catalog']==catalog,'Original source spec and prepared catalog exact agreement')
 require(catalog['ready_new_candidate_ids']==[REUSE,NEW]and catalog['expected_new_RHS']==4 and catalog['expected_new_angular_metrics']==2,'Original pre-execution ready subset preserved')
 require(catalog['source_allocation_amplitudes']==[1.,1.]and catalog['grid']['cells']==793860 and catalog['frequencies']==[2000,2010],'Original phantom sampling/carriers/drive preserved')
 model_target='tools/peripheral_search_20261025/model/peripheral_screen.py';row=source['files'].get(model_target,{})
 require(row.get('SHA256')==FAILED_MODEL_SHA and row.get('readback_passed')is True,'Original calculation source was independently published')
 model_path=FAILED/'source/model/peripheral_screen.py';require(model_path.is_file()and digest(model_path)==FAILED_MODEL_SHA,'Frozen original model source identity');pins[str(model_path)]=FAILED_MODEL_SHA
 equivalent_inputs={}
 for path,sha in catalog['input_pins'].items():
  p=Path(path)
  if p.is_relative_to(FAILED):record(p.relative_to(FAILED).as_posix(),which='source',expected=sha)
  elif str(p)==catalog['source_catalog_path']:
   target='tools/peripheral_search_20261025/catalog/catalog.json';row=source['files'].get(target,{})
   require(row.get('SHA256')==sha and row.get('readback_passed')is True and p.is_file()and digest(p)==sha,'Published original source catalog identity');pins[str(p)]=sha;equivalent_inputs[str(p)]={'target':target,'SHA256':sha,'readback_passed':True}
  elif str(p)in('/dev/shm/task1-vs19-uniform-2000-20261025-run/material-input.json','/dev/shm/task1-vs19-uniform-2000-20261025-run/contact-receipt.json'):
   rel='input-material.json'if p.name=='material-input.json'else'input-contact.json';desc=record(rel,which='source',expected=sha)
   require(p.is_file()and digest(p)==sha,'Original receipt and actually published run snapshot byte identity');pins[str(p)]=sha;equivalent_inputs[str(p)]=desc
  else:raise ValueError('Unrecognized original prepared-input provenance path: '+str(p))
 worker=record('worker-receipt.json',parse=True)
 require(worker.get('status')=='failed_preserved'and worker.get('error_type')=='MemoryError'and worker.get('actual_parent_authentication',{}).get('source_publication_commit')==FAILED_SOURCE_COMMIT,'Actual preserved metrics MemoryError after the known source publication')
 grid=record('common-grid-and-ROI.npz');roi=record('ROI-receipt.json',parse=True)
 raw={};solve={}
 for frequency,output in((2000,0),(2010,1)):
  rel='rhs/'+REUSE+'-'+str(frequency)+'-solve-proof.json';p=record(rel,parse=True)
  require(p.get('candidate_id')==REUSE and p.get('frequency_Hz')==frequency and p.get('driven_output')==output and p.get('passed')is True and p.get('physical_gates',{}).get('passed')is True and p.get('actual_new_RHS')==1,'Completed saved frequency-specific physical solve proof')
  solve[str(frequency)]={**proofs[rel], 'record':p}
  raw[str(frequency)]=record('rhs/'+REUSE+'-'+str(frequency)+'-raw.npz')
 aliases={}
 for cid in CONTROLS:
  rel='candidates/'+cid+'-alias-proof.json';alias=record(rel,parse=True);aliases[cid]={**proofs[rel], 'record':alias}
  require(alias.get('candidate_id')==cid and alias.get('status')=='immutable_original_control_alias'and alias.get('actual_new_RHS')==0 and alias.get('actual_new_metric_evaluations')==0 and alias.get('no_field_reconstruction')is True and alias.get('no_angular_recalculation')is True,'Existing original full control aliases, no control recomputation')
 blocked=record('candidates/'+BLOCKED+'-recipe-BLOCKER.json',parse=True);require(blocked.get('status')=='recipe_blocked'and blocked.get('candidate_id')==BLOCKED,'Original geometry blocker preserved')
 # Root owns these checks at actual invocation. Do not decode or duplicate arrays here.
 admission_path=SOURCE/'root-admission.json'
 if admission_path.is_file():
  require(read_json(admission_path)==admission,'Immutable root-admission copy agrees');pins[str(admission_path)]=digest(admission_path)
 return dict(schema='task1-peripheral-recovery-inputs-v1',root_admission=admission,source_run=str(FAILED),original_spec=original,catalog=catalog,reuse_candidate_id=REUSE,new_candidate_id=NEW,reuse_raw_by_frequency=raw,reuse_proofs_by_frequency=solve,common_grid_ROI=grid,ROI_receipt=roi,ROI_receipt_file=proofs['ROI-receipt.json'],control_alias_proofs=aliases,blocked_recipe=blocked,input_sha256=pins,publication_file_proofs=proofs,equivalent_input_proofs=equivalent_inputs,unfinished_stage=absence,
  expected_new_RHS=2,expected_reused_RHS=2,expected_new_metric_evaluations=2,expected_control_alias_conditions=2,expected_completed_conditions=4,original_partial_provenance=dict(source_commit=FAILED_SOURCE_COMMIT,source_model_sha256=FAILED_MODEL_SHA,source_spec_sha256=FAILED_SPEC_SHA,partial_result_commit=partial['commit'],partial_result_publication_sha256=admission['partial_result_publication_sha256'],failure='MemoryError during first new metric evaluation after both P23p5 raw RHS completed'),
  no_saved_RHS_resolve=True,no_control_field_or_angle_recalculation=True,new_eigen_solves=0,candidate_adopted=False,Windows_saved_verified=False)

def required_inputs(admission=None):return dict(make_spec(admission)['input_sha256'])
