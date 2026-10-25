"""Deferred small-metadata proof chain for a zero-new-PDE native B0 restore.

Import is inert/std-library only. No native field, mask CSV, Q chunk, NumPy,
test or solver is accessed until the sole root owner separately admits work.
"""
import copy,hashlib,json,re
from pathlib import Path
SOURCE=Path('/dev/shm/task1-streamed-Q-native-restore-20261025/source')
FINE=Path('/dev/shm/task1-P23-fineXY-20261025-run')
GRAPH=Path('/dev/shm/task1-layer-dtn-xy102-20261025-run')
MFG=Path('/dev/shm/task1-streamed-Q-MFG-20261025-run')
OPERATOR=Path('/dev/shm/task1-streamed-Q-20261025/source/streamed_real_q.py')
OPERATOR_SHA='4a4276096f6eeb7d0e085bc7f9f3f0f0c97eb1a39c1c2de899b77b28668dcf0e'
FIELD_VERSION='native-lateral-half-face-v1+analytic-z-DtN-v1'
MAX_METADATA=8*1024**2
MATERIAL_SHA='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
CONTACT_SHA='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
REMOTE_Q_COMMIT='d725ee29ee568ef26a4b7579e9dfc55d23e0681a'
NORMALIZED_Q=Path('/dev/shm/task1-transfer-20261025/cache-publication-normalized.json')
NORMALIZED_Q_SHA='f05f5eb7f37aabdba649ca1c445217aed82663c3bbf875b7193afd7031e35a4f'
ORIGINAL_Q_RECEIPT=Path('/dev/shm/task1-cache-retention-20261025-run/public-receipt.json')
ORIGINAL_Q_RECEIPT_SHA='589dad62a301761c930e03f7a74fd33d53caf550e3e5613fbcd10143c4dfd634'
FINE_R=(FINE/'result-publication/result-publication.json','0a9f71adef7439f19c2334ffef96c5f83e271c75c2440af3582615bfb998e075','fd0b0becc1f38d5c8118c929e7c5c4f24cc64c47')
FINE_S_COMMIT='83a61fb55bd42a8ef778a8653c8aa31bbdf647e0'
MFG_MODEL_SHA={str(OPERATOR):OPERATOR_SHA,
 '/dev/shm/task1-streamed-Q-20261025/source/test_streamed_real_q.py':'8230fdc374d70942d46dd648ef01cf6da17c5d117f2a0072b70f2831fcfe46b9',
 '/dev/shm/task1-streamed-Q-20261025/source/OPERATOR_CONTRACT.md':'1c82247c211e9c65b00079feef58d69798a927803a42d10e58de5571489e896c'}
FINE_SOURCE_SHA={
 'fine_solver.py':'b322de0af743e3d6a6ae1cb7b9ecc7543225c8cd55b72d697e113d0327580a84',
 'fine_fields.py':'4541b2ed566d068d1a52e25a762e519f31e74d815961939055e8970e06703977',
 'frozen_layer_dtn_backend.py':'7ff50b6b30198abe4d2cfc5f4ac4fa2afa0873f040ca23175f0e881fb22e1d08',
 'provisional_field.py':'5cebbe9b18c0b5912de328cc66036e5a6abe015e268261c3a7e974d719df1e87',
 'frozen_fourier_v1.py':'6d855155d823d165fb51f4ce17b9ac607a23d9850cdd806ec354b3c577d415f5'}

def require(ok,message):
 if not ok:raise ValueError(message)
def fullhex(value,n):return isinstance(value,str)and re.fullmatch('[0-9a-f]{'+str(n)+'}',value)is not None
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def metadata(path,expected):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and not p.is_symlink()and p.is_file()and 0<p.stat().st_size<MAX_METADATA,'Canonical bounded metadata only')
 require(fullhex(expected,64),'Full expected metadata SHA required');raw=p.read_bytes();require(hashlib.sha256(raw).hexdigest()==expected,'Exact metadata bytes before parse');return json.loads(raw)
def source_inventory():
 excluded={'root-admission.json','synthetic-test-receipt.json','tests-receipt.json'}
 files=sorted(p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')and p.name not in excluded)
 require(any(p.name=='restore_inputs.py'for p in files)and all(not p.is_symlink()and p.stat().st_size<MAX_METADATA for p in files),'Complete canonical bounded source inventory')
 return{str(SOURCE/p.name):digest(SOURCE/p.name)for p in files}
def direct(pub,path,target,expected=None):
 require(pub.get('status')=='published_readback_verified'and fullhex(pub.get('commit'),40),'Actual complete Git readback, not a plan')
 p=Path(path);require(p.is_absolute()and p==p.resolve()and not p.is_symlink(),'Canonical deferred descriptor only')
 row=pub['files'][target];require(row.get('readback_passed')is True and fullhex(row.get('SHA256'),64)and type(row.get('bytes'))is int and 0<row['bytes']<=80*1024**2,'Direct full SHA/bytes/readback proof')
 require(expected is None or row['SHA256']==expected,'Unchanged original descriptor identity')
 return dict(path=str(p),SHA256=row['SHA256'],bytes=row['bytes'],publication_target=target,publication_commit=pub['commit'],readback_passed=True,decoded_here=False)
def validate_admission(a):
 require(type(a)is dict and a.get('schema')=='task1-streamed-Q-native-B0-restore-root-admission-v1'and a.get('status')=='admitted_cached_native_B0_restore_after_published_MFG'and a.get('root_review_positive')is True and a.get('sole_NUM_owner')is True,'Separate root admission after actual published Q MFG PASS')
 fixed=dict(new_driven_RHS=0,new_eigen_solves=0,new_angular_metric_evaluations=0,expected_cached_restored_carriers=2,physical_pads=4,independent_outputs=2,frequencies_Hz=[2000,2010],fine_layer_counts=[4,19,18,56],fine_evaluation_cells=793848,max_physical_evaluation_cells=800000,Q_rows=8184,cache_name='xy102',CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,candidate_adopted=False)
 for key,value in fixed.items():require(key in a and type(a[key])is type(value)and a[key]==value,'Exact prospective zero-new-PDE restore scope '+key)
 require(type(a.get('source_sha256'))is dict and type(a.get('decision_basis'))is str and a['decision_basis'].strip(),'Exact frozen sources and explicit root review rationale')
 r=a.get('MFG_review');require(type(r)is dict and r.get('run')==str(MFG)and r.get('publication_path')==str(MFG/'result-publication/result-publication.json')and r.get('root_reviewed')is True,'Only actual exact Q-MFG publication can admit native restore')
 require(fullhex(r.get('publication_SHA256'),64)and fullhex(r.get('publication_commit'),40)and type(r.get('decision_basis'))is str and r['decision_basis'].strip(),'Actual future full Q-MFG identity and review basis')
 return a
def validate_mfg(value,model_sources,source_commit):
 require(type(value)is dict and value.get('status')=='passed'and value.get('kind')=='actual_tiny_streamed_real_Q_operator_fixtures_only','Actual passed manufactured operator fixture receipt required')
 require(value.get('source_publication_commit')==source_commit and value.get('model_source_sha256')==model_sources and value.get('source_sha256')==model_sources,'Actual MFG source bindings')
 for key,num in dict(model_source_test_count=12,tests_run=20,expected_total_tests=20,model_tests_run=12,owner_tests_run=8,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_field_reads=0,native_file_reads=0,native_eigen_solves=0,native_full_field_exports=0,native_field_angular_work=0).items():
  require(type(value.get(key))is int and value[key]==num,'Actual frozen12+8 MFG accounting '+key)
 for key in('native_Q_loaded','native_eigen_performed','native_restore_performed','field_admission_granted','candidate_adopted'):require(value.get(key)is False,'MFG never grants native work '+key)
 require(value.get('forbidden_field_calls')==[]and value.get('native_IO_attempts')==[]and value.get('IO_audit_installed')is True and value.get('synthetic_metadata_proofs_are_fixture_values')is True,'No actual native data or caught scope violations in manufactured PASS')
 events=value.get('test_events');require(type(events)is list and len(events)==20 and len({r['test_id']for r in events})==20 and all(r.get('outcome')=='passed'for r in events),'Every actual frozen synthetic method passed, no invented aggregate')
 for key in('operator_constructors','metadata_validation_calls','forward_attempts','transpose_attempts','slice_attempts','chunk_visits_started','chunk_visits_completed','operator_receipts'):
  require(type(value.get('manufactured_work_counts',{}).get(key))is int and value['manufactured_work_counts'][key]>0,'Actual synthetic operator calls '+key)
 return True


def validate_chunk_receipts(manifest, normalized, original, *, n, grid_name):
    """Pure proof-chain validation; never overwrites historical manifest flags."""
    require(normalized.get('status') == 'published_readback_verified'
            and normalized.get('commit') == REMOTE_Q_COMMIT
            and normalized.get('original_public_receipt_SHA256') == ORIGINAL_Q_RECEIPT_SHA,
            'Actual standard retained-Q publication receipt')
    require(original.get('schema') == 'task1-retained-cache-public-readback-receipt-v1'
            and original.get('commit') == REMOTE_Q_COMMIT and isinstance(original.get('files'), list),
            'Original retained-Q receipt list and fixed commit')
    require(manifest['shape'] == [n, n] and manifest['dtype'] == '<f8'
            and manifest['order'] == 'F', 'Exact original real-Q matrix ABI')
    original_files = {row['repo_relative_path']: row for row in original['files']}
    require(len(original_files) == len(original['files']), 'Unique original remote file proofs')
    at, total, proofs = 0, 0, []
    for chunk in manifest['chunks']:
        require(chunk['row_start'] == 0 and chunk['row_stop'] == n
                and chunk['column_start'] == at and at < chunk['column_stop'] <= n
                and chunk['dtype'] == '<f8' and chunk['order'] == 'F'
                and chunk['bytes'] == n * (chunk['column_stop'] - at) * 8,
                'Ordered disjoint complete original Q chunk ABI')
        target = 'data-native/retained-eigen-cache-20261025/' + grid_name + '/' + Path(chunk['path']).name
        require(target in normalized['files'] and target in original_files, 'Every actual Q chunk needs direct remote proof')
        a, b = normalized['files'][target], original_files[target]
        require(a['readback_passed'] is True and b['readback_passed'] is True
                and b['commit'] == REMOTE_Q_COMMIT
                and a['SHA256'] == b['SHA256'] == chunk['SHA256']
                and a['bytes'] == b['bytes'] == chunk['bytes']
                and a['Git_blob_SHA'] == b['Git_blob_SHA'], 'Exact remote Q full SHA/bytes/Git blob readback')
        proofs.append(dict(path=chunk['path'], SHA256=chunk['SHA256'], bytes=chunk['bytes'],
                           publication_target=target, publication_commit=REMOTE_Q_COMMIT,
                           Git_blob_SHA=a['Git_blob_SHA'], readback_passed=True))
        total += chunk['bytes']
        at = chunk['column_stop']
    require(at == n and total == n * n * 8, 'All Q columns/bytes authenticated without decoding')
    return proofs

def make_spec(admission=None):
 if admission is None:
  path=SOURCE/'root-admission.json';require(path.is_file(),'Native restore admission absent; no data/input work authorized');admission=metadata(path,digest(path))
 a=validate_admission(admission);sources=source_inventory();require(a['source_sha256']==sources,'Exact complete canonical restore source map')
 require(sources.get(str(SOURCE/'streamed_real_q.py'))==OPERATOR_SHA,'Only byte-exact independently tested streamed operator source')
 refs=dict(sources);descriptors={};publications={};pub_descriptors={}
 def pub(name,path,expected,commit):
  value=metadata(path,expected);require(value.get('status')=='published_readback_verified'and value.get('commit')==commit,'Actual immutable publication '+name);refs[str(path)]=expected;publications[name]=value;pub_descriptors[name]=dict(path=str(path),SHA256=expected,commit=commit);return value
 def item(name,path,target,expected=None,parse=False):
  d=direct(publications[name],path,target,expected);refs[d['path']]=d['SHA256'];descriptors[d['path']]=d;return metadata(d['path'],d['SHA256'])if parse else d
 fineR=pub('fine_R',*FINE_R);source_row=fineR['files']['data-native/P23-fineXY-20261025/source-publication-receipt.json'];require(source_row.get('readback_passed')is True and fullhex(source_row.get('SHA256'),64),'Fine source receipt exact actual R readback')
 fineS=pub('fine_S',FINE/'source-publication/result-publication.json',source_row['SHA256'],FINE_S_COMMIT)
 def fine(path,expected=None,parse=False,where='fine_R'):return item(where,path,'data-native/P23-fineXY-20261025/'+Path(path).relative_to(FINE).as_posix(),expected,parse)
 spec=fine(FINE/'spec.json','ef39c4d106fbb33ce23a58793faf10a35a067f5c7e1eb0506ebf95225d92c4aa',True,'fine_S');fine(FINE/'spec.json','ef39c4d106fbb33ce23a58793faf10a35a067f5c7e1eb0506ebf95225d92c4aa')
 old=spec['inputs'];catalog=copy.deepcopy(old['first8catalog'])
 require(spec['field_estimator_version']==FIELD_VERSION and spec['common_depth_layer_counts']==[4,19,18,56]and spec['fine_evaluation_cells']==793848,'Exact actually executed fine97 native field/grid ABI')
 summary=fine(FINE/'summary.json','fa3239f8a56d2c26558d40bb2afd834adabea3a24d4292ec5632dd7586d4c22f',True)
 require(summary.get('status')=='four_matched97_metric_cases_and_physical_overlap_computed_unadopted'and summary.get('candidate_adopted')is False and summary.get('Q_resident_during_postprocessing')is False,'Existing actual fine batch complete/unadopted')
 B0_metric_record=next(row for row in summary['candidates']if row['candidate_id']=='B0-square15-c10-diagonal-XY102-Z97')
 require(B0_metric_record['physical_geometry_id']=='B0-square15-c10-diagonal'and B0_metric_record['grid_variant']=='XY102-Z97'and B0_metric_record['candidate_adopted']is False,'Actual fine B0 metric metadata only, no scalar-array loading')
 manifest=fine(FINE/'raw-manifest.json','88d36157b7574ff2337072a572d434a1f6f2c3aeb90a67c2d22c59d95a33b78e',True)
 require(manifest.get('Q_frames_returned')is True and manifest.get('GC_before_postprocessing')is True,'Existing source raw frames were released, not guessed')
 def embedded(value,parse=False):
  require(type(value)is dict and type(value.get('publication_proof'))is dict,'Actual old direct descriptor with receipt chain')
  p=value['publication_proof'];name='embedded:'+p['path']
  if name not in publications:pub(name,Path(p['path']),p['SHA256'],p['commit'])
  d=item(name,Path(value['path']),value['publication_target'],value['SHA256']);require(d['bytes']==value['bytes']and d['publication_commit']==value['publication_commit'],'Exact embedded descriptor/receipt bytes/commit')
  return metadata(d['path'],d['SHA256'])if parse else d
 material=embedded(old['original_material_contact_receipts']['material']);contact=embedded(old['original_material_contact_receipts']['contact'])
 require(material['SHA256']==catalog['material_sha256']==MATERIAL_SHA and contact['SHA256']==catalog['contact_sha256']==CONTACT_SHA,'Unchanged HREF surrogate/PBS-contact bytes')
 material_value=metadata(material['path'],MATERIAL_SHA);contact_value=metadata(contact['path'],CONTACT_SHA)
 require(dict(material=material_value,contact=contact_value)==old['original_material_contact_values'],'Actual executed material/contact metadata, not new constants')
 require(contact_value['Rs_subtractions']==1 and contact_value['measurement_area_multiplications']==1 and contact_value['division_by_two']is False,'Existing Rs and area conversion exactly once')
 require(catalog['drives']=={'2000':{'output':0,'source_Vpp':1.,'source_peak_V':.5},'2010':{'output':1,'source_Vpp':1.,'source_peak_V':.5}}and catalog['source_resistance_ohm']==50.,'Same actual carriers/output high-Z1Vpp/R50/inactive termination')
 require(catalog['common_ROI']==dict(depth_mm=[15,20],depth_origin='physicaltop,+zdown',radius_mm=5)and catalog['grid']['radius_mm']==25 and catalog['grid']['layer_thickness_mm']==[.1,5,5,15],'Fixed D50/physical layers/target ROI')
 fine_sources={}
 for name,expected in FINE_SOURCE_SHA.items():
  require(sources.get(str(SOURCE/name))==expected,'Byte-exact frozen mathematical source copy '+name)
  original=item('fine_S',FINE/'source/model'/name,'tools/P23_fineXY_20261025/model/'+name,expected)
  fine_sources[name]=dict(path=str(SOURCE/name),SHA256=expected,original_source=original,byte_exact_copy=True)
 raws={};proofs={}
 for frequency,output in((2000,0),(2010,1)):
  entry=manifest['fine']['B0'][str(frequency)];raws[str(frequency)]=fine(Path(entry['raw']['path']),entry['raw']['SHA256'])
  pd=fine(FINE/'rhs'/('B0-XY102-'+str(frequency)+'-proof.json'));proof=metadata(pd['path'],pd['SHA256'])
  require(proof==entry['proof']and proof['candidate']=='B0'and proof['frequency_Hz']==frequency and proof['driven_output']==output and proof['grid']=='XY102','Exact actual B0 carrier/grid/output proof')
  require(proof['passed']is True and proof['physical_gates']['passed']is True and proof['passivity_passed']is True and proof['source_peak_V']==.5 and proof['source_high_impedance_Vpp']==1.,'Existing actual five source physical gates/passivity')
  proofs[str(frequency)]=dict(descriptor=pd,value=proof)
 grid=fine(FINE/'fine-common97-grid-ROI.npz',manifest['geometry']['fine']['SHA256']);roi=fine(FINE/'fine-ROI-receipt.json');roi_value=metadata(roi['path'],roi['SHA256'])
 faces=embedded(old['eval_faces']['fine']);faces_value=metadata(faces['path'],faces['SHA256']);require(faces_value==old['eval_face_receipts']['fine']and faces_value['layer_counts']==[4,19,18,56]and len(faces_value['z_faces_m'])==98 and faces_value['evaluation_cells']==793848,'Actual fine97 depth faces and physical evaluation count')
 mask=embedded(old['fine_B0_mask']);mask_receipt=embedded(old['fine_B0_mask_receipt']);mask_value=metadata(mask_receipt['path'],mask_receipt['SHA256'])
 require(mask_value==old['fine_B0_mask_receipt_value']and mask_value['mask_sha256']==mask['SHA256']and mask_value['contact_area_gate_passed']is True,'Same actual native fractional B0 mask; no remeshing/area repair')
 graph_arrays=embedded(old['graph_arrays']['fine']);graph_desc=old['publication_file_proofs'][str(GRAPH/'summary.json')];graph_summary=embedded(graph_desc,True)
 require(graph_summary==old['graph_summaries']['fine']and graph_summary['analytic']['passed']is True,'Original fine graph/eigen/analytic proof, no new eigen')
 qdesc=embedded(old['publication_file_proofs'][str(GRAPH/'eigen-cache/manifest.json')]);qmanifest=metadata(qdesc['path'],qdesc['SHA256'])
 require(qmanifest==old['cache_manifests']['fine']==graph_summary['eigen']['cache']and qmanifest['shape']==[8184,8184]and qdesc['SHA256']=='26da99d7edfcb24a418ab56e1091bab5cb156eccd998653631d5852108c683aa','Exact original real fineQ manifest, flags unchanged')
 normalized=metadata(NORMALIZED_Q,NORMALIZED_Q_SHA);original=metadata(ORIGINAL_Q_RECEIPT,ORIGINAL_Q_RECEIPT_SHA);refs[str(NORMALIZED_Q)]=NORMALIZED_Q_SHA;refs[str(ORIGINAL_Q_RECEIPT)]=ORIGINAL_Q_RECEIPT_SHA
 remote=validate_chunk_receipts(qmanifest,normalized,original,n=8184,grid_name='xy102');require(remote==old['remote_Q_chunk_proofs']['fine'],'Same complete actually executed fine retained-Q chain')
 for row in remote:require(Path(row['path']).parent==GRAPH/'eigen-cache','Original fineQ local directory');refs[row['path']]=row['SHA256']
 # Native restore cannot use a source-only/synthetic proposal as a MFG PASS.
 review=a['MFG_review'];mfgR=pub('MFG_R',Path(review['publication_path']),review['publication_SHA256'],review['publication_commit']);prefix='data-native/streamed-Q-MFG-20261025/'
 mfgSrow=mfgR['files'][prefix+'source-publication-receipt.json'];require(mfgSrow.get('readback_passed')is True,'Actual MFG source receipt preserved in actual result')
 mfgS=metadata(MFG/'source-publication/result-publication.json',mfgSrow['SHA256']);pub('MFG_S',MFG/'source-publication/result-publication.json',mfgSrow['SHA256'],mfgS['commit'])
 mprereg=item('MFG_S',MFG/'preregistration.json',prefix+'preregistration.json',parse=True);require(mprereg['model_source_sha256']==MFG_MODEL_SHA and mprereg['expected_principal_tests']==12 and mprereg['expected_owner_tests']==8,'Frozen actual12model/8owner MFG source identity')
 oporiginal=item('MFG_S',OPERATOR,'tools/streamed_Q_MFG_20261025/model/streamed_real_q.py',OPERATOR_SHA)
 mreceipt_desc=item('MFG_R',MFG/'synthetic-test-receipt.json',prefix+'synthetic-test-receipt.json');mreceipt=metadata(mreceipt_desc['path'],mreceipt_desc['SHA256']);validate_mfg(mreceipt,MFG_MODEL_SHA,mfgS['commit'])
 events_expected={module+'.'+method for section in('principal','owner')for module,methods in mprereg['test_inventory'][section].items()for method in methods};require({row['test_id']for row in mreceipt['test_events']}==events_expected,'Actual passed MFG method identities equal published inventory')
 mworker=item('MFG_R',MFG/'worker-receipt.json',prefix+'worker-receipt.json',parse=True);require(mworker.get('status')=='synthetic_tests_executed'and mworker.get('principal_tests_passed')is True and mworker.get('test_receipt_SHA256')==mreceipt_desc['SHA256'],'Actual MFG worker corroborates receipt')
 mverification=item('MFG_R',MFG/'input-SHA-verification.json',prefix+'input-SHA-verification.json',parse=True);require(all(mverification.get(stage,{}).get('passed')is True for stage in('before_tests','after_tests')),'Actual MFG source before/after SHA checks')
 mfg_evidence=dict(publications=dict(S=pub_descriptors['MFG_S'],R=pub_descriptors['MFG_R']),receipt_descriptor=mreceipt_desc,receipt=mreceipt,worker=mworker,source_verification=mverification,root_review_basis=review['decision_basis'],native_restore_or_PDE_admission_from_MFG=False)
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(metadata(ap,digest(ap))==a,'Immutable native restore root decision');refs[str(ap)]=digest(ap)
 return dict(schema='task1-streamed-Q-native-B0-restore-inputs-v1',root_admission=copy.deepcopy(a),source_sha256=sources,input_sha256=refs,publication_metadata=pub_descriptors,publication_file_proofs=descriptors,
  fine_spec=spec,original_fine_CEM_spec=copy.deepcopy(old['fine_spec']),catalog=catalog,material=material,contact=contact,material_value=material_value,contact_value=contact_value,
  fine_sources=fine_sources,streamed_operator_source=dict(path=str(SOURCE/'streamed_real_q.py'),SHA256=OPERATOR_SHA,original_source=oporiginal,byte_exact_copy=True),MFG_evidence=mfg_evidence,
  B0_raw_by_frequency=raws,B0_proofs_by_frequency=proofs,B0_metric_record=copy.deepcopy(B0_metric_record),B0_mask=mask,B0_mask_receipt=mask_receipt,B0_mask_receipt_value=mask_value,
  native_raw_keys=dict(surface_phi='phi_surface_peak_V',metal='metal_peak_V',modal_coefficients='modal_surface_coeff',source_current='source_current_peak_A',contact_current='contact_current_peak_A',contact_J='contact_normal_J_peak_A_m2',contact_drop='contact_drop_peak_V',contact_pad='contact_pad',contact_xy_index='contact_xy_index',contact_area='contact_area_m2',layer_power='layer_complex_power_W',potential='phi_peak_V',electric_field='E_peak_V_m',interface_downward_J='interface_downward_J_peak_A_m2'),
  grid_ROI=grid,ROI_receipt=roi,ROI_receipt_value=roi_value,eval_face_receipt=faces,eval_face_receipt_value=faces_value,graph_arrays=graph_arrays,graph_summary=graph_summary,graph_summary_descriptor=descriptors[graph_desc['path']],
  Q_manifest=qmanifest,Q_manifest_descriptor=qdesc,remote_Q_chunk_proofs=remote,cache_name='xy102',historical_manifest_flags_preserved=True,
  field_version=FIELD_VERSION,frequencies_Hz=[2000,2010],grid=dict(h_m_definition='0.05/102',h_numerator_m=.05,h_divisor=102,XY_rows=8184,depth_layer_counts=[4,19,18,56],physical_evaluation_cells=793848),
  circuit=dict(physical_pads=4,independent_outputs=2,source_high_impedance_Vpp=1.,source_peak_V=.5,source_resistance_ohm=50.,inactive_output='Ideal0V through its original single50ohm',return_topology='Physicalpads2/3hardcommonGND',top_attached=True),
  holds=copy.deepcopy(summary['holds']),prospective_adjacent_grid_diagnostics=copy.deepcopy(summary['prospective_adjacent_grid_diagnostics']),old_fine_electrical_screen=copy.deepcopy(old['old_fine_electrical_screen']),
  prior_fine14_of18_and16_of18_failures_not_cleared=True,skin_material_HREF_surrogate_and_PBS_contact_not_human_experimentally_validated=True,
  new_driven_RHS=0,new_eigen_solves=0,new_angular_metric_evaluations=0,native_restore_has_not_run_here=True,candidate_adopted=False)
def required_inputs(admission=None):return dict(make_spec(admission)['input_sha256'])
