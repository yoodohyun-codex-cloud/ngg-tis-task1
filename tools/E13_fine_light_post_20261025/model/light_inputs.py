"""Deferred E13-fine-only metadata adapter. No native/scientific IO on import."""
import copy,hashlib,json,math,re
from pathlib import Path
import recovery_contracts

SOURCE=Path('/dev/shm/task1-E13-fine-light-post-20261025/source')
FINE=Path('/dev/shm/task1-E13-fineXY-20261025-run')
RECOVERY=Path('/dev/shm/task1-E13-fineXY-publication-resume-20261025-run')
OLD_FINE=Path('/dev/shm/task1-P23-fineXY-20261025-run')
FIRST8=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
OLD_LIGHT=Path('/dev/shm/task1-native-light-post-r2-20261025-run')
E13='E13-tangent-P23-centroids-225';CANDIDATE_ID=E13+'-XY102-Z97'
B0='B0-square15-c10-diagonal'
FIELD_VERSION='native-lateral-half-face-v1+analytic-z-DtN-v1'
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
MAX_METADATA=8*1024**2
PREFIX='data-native/E13-fineXY-20261025/'
META_PREFIX='docs/TASK1_CONTACT_EDGE_20261025/E13-fineXY-recovered-20261025-metadata/'
TRANSFER_TARGET='docs/TASK1_CONTACT_EDGE_20261025/E13-fineXY-recovered-20261025-transfer-manifest.json'
PUBLICATIONS={
 'E13_R':(FINE/'result-publication/result-publication.json','128c64313c836a48f8cd3799ec6b18c0b583ec3a679dbc0f27a93c5f06956135','f394cc9c2570f47a29968bea134a8078b98826d4'),
 'E13_S':(FINE/'source-publication/result-publication.json','e85b52386ccf76452fd7391f8f8a3df756b4b07c6d238bfd19aae1fb52007b8f','50a930fbe1fe08b0b0af2d00d99c79eec3b96fb4'),
 'E13_M':(RECOVERY/'auto-transfer/M/result-publication.json','972f40a22f8880d4f0a3a14a2d7dbc92474f1bf2483f299e9335178ffb6076aa','98856535002b208cab94f93757b0ff1bfc4c8e04'),
 'E13_T':(RECOVERY/'auto-transfer/T/result-publication.json','9995e1c8dea9a4cbb91bc83a77240675f772b1f57d34d3a62972f7d282f3e62e','d8ab16d08d4d990162b06610178060b75d7b2a4f'),
 'fine_R':(OLD_FINE/'result-publication/result-publication.json','0a9f71adef7439f19c2334ffef96c5f83e271c75c2440af3582615bfb998e075','fd0b0becc1f38d5c8118c929e7c5c4f24cc64c47'),
 'first8_R':(FIRST8/'result-publication/result-publication.json','d20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159','4d6207caa60ae16ab7a7e997022ac72653b97ec3'),
 'first8_S':(FIRST8/'source-publication/result-publication.json','cb8939fdd21b3c4d7103eeb26c3591037402553d4369aa195888e30930b1eb49','c8e5f2f9d4fbba5646944772d526533ecedbbab1'),
 'old_light_S':(OLD_LIGHT/'source-publication/result-publication.json','cc08d308efba7436e899d9da639f6848779865422cf173cbbab47b31439c6ee9','04c75b29bdd325c8e037f7b048095490ad6f662a')}
FROZEN_FUNCTION_MODULES={
 'light_probe.py':'d3a3281fd2f39a960bc08c8ffa8eeb0f7686f2d5d4877c8d1ffefa55f15f25d6',
 'high_volume.py':'f3e1645d522f64e981c30076a5b091ded261321547112b68fdf8d0258f4b639b'}

def require(ok,message):
 if not ok:raise ValueError(message)
def fullhex(value,n):return type(value)is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',value)is not None
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def metadata(path,expected):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and 0<p.stat().st_size<MAX_METADATA,'Canonical bounded small metadata only')
 require(fullhex(expected,64)and digest(p)==expected,'Full small-metadata SHA before parse');return json.loads(p.read_bytes())
def source_inventory():
 excluded={'root-admission.json','synthetic-test-receipt.json','tests-receipt.json'}
 files=sorted(p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')and p.name not in excluded)
 require(any(p.name=='light_inputs.py'for p in files)and all(not p.is_symlink()and p.stat().st_size<MAX_METADATA for p in files),'Complete canonical bounded source inventory')
 return{str(SOURCE/p.name):digest(SOURCE/p.name)for p in files}
def validate_admission(a):
 require(type(a)is dict and a.get('schema')=='task1-E13-fine-light-post-root-admission-v1'and a.get('status')=='admitted_finite_E13_fine_cached_post'and a.get('root_review_positive')is True and a.get('sole_NUM_owner')is True,'Separate positive finite E13-fine-only postprocess decision')
 require(type(a.get('candidate_ids'))is list and all(type(x)is str for x in a['candidate_ids'])and a['candidate_ids']==[CANDIDATE_ID],'Exactly E13 fine97; no old-case or coarseSC4 repeat')
 fixed=dict(completed_native_geometries=1,requested_probes=40,threshold_subsets=48,new_driven_RHS=0,new_eigen_solves=0,new_angular_metric_evaluations=0,CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,child_RSS_forecast_bytes=170000000,new_output_forecast_bytes=10000000)
 for key,value in fixed.items():require(type(a.get(key))is int and a[key]==value,'Exact finite cached post scope '+key)
 for key in('native_Q_loaded','fields_reconstructed','old_statistics_recomputed','candidate_adopted'):require(a.get(key)is False,'Cached native postprocessing only '+key)
 require(a.get('owned_auxiliary_namespaces')==['/dev/shm/task1-*','/tmp/task1-*'],'Both owned auxiliary namespace roots remain within aggregate8e9 cap')
 require(type(a.get('decision_basis'))is str and a['decision_basis'].strip()and type(a.get('source_sha256'))is dict,'Root rationale and full canonical source inventory')
 return a
def direct(pub,path,target,expected=None):
 require(pub.get('status')=='published_readback_verified'and fullhex(pub.get('commit'),40),'Actual full readback publication')
 p=Path(path);require(p.is_absolute()and p==p.resolve()and not p.is_symlink(),'Canonical deferred artifact descriptor')
 row=pub['files'][target];require(row.get('readback_passed')is True and fullhex(row.get('SHA256'),64)and type(row.get('bytes'))is int and 0<row['bytes']<80*1024**2,'Direct full SHA/bytes/readback artifact proof')
 require(expected is None or row['SHA256']==expected,'Exact original artifact identity')
 return dict(path=str(p),SHA256=row['SHA256'],bytes=row['bytes'],publication_commit=pub['commit'],publication_target=target,readback_passed=True,arrays_decoded_here=False)
def validate_normalizations(value):
 require(type(value)is dict and value.get('status')=='complete'and set(value['comparisons'])==set(MODES),'All four actual original-coarse101 B0 normalizations retained')
 for mode,row in value['comparisons'].items():
  x=row.get('amplitude_scale');require(type(x)in(int,float)and math.isfinite(x)and x>=0,'Finite actual normalization scale '+mode)
 return value
def validate_completed_producer(summary,worker,stage,verification,local,spec,summary_SHA256,local_SHA256):
 recovery_contracts.validate_outcome('computed_complete_publication_recovered',summary,[])
 require(worker.get('status')=='E13_fineXY_computed'and worker.get('summary_SHA256')==summary_SHA256 and stage.get('status')=='E13_fineXY_computed'and type(stage.get('worker_exit_code'))is int and stage['worker_exit_code']==0 and stage.get('source_commit')==PUBLICATIONS['E13_S'][2],'Actual numerical worker/stage completed; terminal publication failure is separately retained')
 require(stage.get('accounting')==worker.get('E13_fineXY_accounting')and stage['accounting'].get('passed')is True and worker.get('actual_new_fine_RHS')==2 and worker.get('actual_new_coarse_RHS')==0,'Actual numerical accounting agreement')
 require(worker.get('input_verification')==verification and worker.get('manufactured_test_receipt_SHA256')==local_SHA256,'Actual published input-verification and local-MFG pin')
 for key in('before_tests_and_build','after_build'):
  r=verification.get(key,{});require(r.get('passed')is True and type(r.get('count'))is int and r['count']>0,'Actual full source/input SHA completion '+key)
 require(verification['after_build']['count']==verification['before_tests_and_build']['count']+1,'Actual one local-MFG receipt added after tests before build')
 require(local.get('status')=='passed'and local.get('source_publication_commit')==PUBLICATIONS['E13_S'][2]and local.get('model_source_sha256')==spec['inputs']['source_sha256'],'Actual source-bound producing MFG, not a new postbatch PASS')
 for key,n in dict(model_source_test_count=40,model_tests_run=40,owner_tests_run=5,tests_run=45,expected_total_tests=45,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_field_reads=0).items():require(type(local.get(key))is int and local[key]==n,'Exact original45 producing MFG count '+key)
 require(local.get('native_Q_loaded')is False and local.get('field_admission_granted')is False and local.get('scientific_API_spy_calls')==[],'Original local tests did not perform native physics')
 for record in(worker,stage):require(not any(k in record for k in('error','error_type','failed_phase','failed_stage')),'Incomplete numerical worker/stage cannot supply fine fields')
 return True
def validate_manifest_coverage(manifest,descriptors):
 require(manifest.get('schema')=='task1-safe-windows-transfer-manifest-v1'and manifest.get('public_reference_commit')==PUBLICATIONS['E13_M'][2]and manifest.get('Windows_backup_complete')is False and manifest.get('OneDrive_sync_verified')is False,'Actual manifest is artifact provenance, not Windows receipt or experimental validation')
 rows=manifest.get('files');aliases=manifest.get('logical_file_aliases');require(type(rows)is list and type(aliases)is list,'Actual full transfer inventory and aliases')
 for d in descriptors:
  require(any(row.get('fixed_commit')==d['publication_commit']and row.get('repo_relative_path')==d['publication_target']and row.get('SHA256')==d['SHA256']and row.get('bytes')==d['bytes']for row in rows+aliases),'Every used native artifact has exact existing full transfer provenance')
 return dict(status='existing_actual_manifest_covers_used_native_artifacts',used_native_artifacts=len(descriptors),Windows_saved_verified=False)

def make_spec(admission=None):
 if admission is None:
  p=SOURCE/'root-admission.json';require(p.is_file(),'Actual separate finite cached-post decision absent');admission=metadata(p,digest(p))
 a=validate_admission(admission);sources=source_inventory();require(a['source_sha256']==sources,'Full immutable canonical new source map')
 refs=dict(sources);pubs={};pubmeta={};artifacts={}
 def pub(name,path,expected,commit):
  value=metadata(path,expected);require(value.get('status')=='published_readback_verified'and value.get('commit')==commit,'Actual exact publication '+name);pubs[name]=value;refs[str(path)]=expected;pubmeta[name]=dict(path=str(path),SHA256=expected,commit=commit);return value
 for name,args in PUBLICATIONS.items():pub(name,*args)
 def item(name,path,target,expected=None,parse=False):
  d=direct(pubs[name],path,target,expected);refs[d['path']]=d['SHA256'];artifacts[d['path']]=d
  return metadata(d['path'],d['SHA256'])if parse else d
 def fine(name,parse=False,where='E13_R',expected=None):return item(where,FINE/name,PREFIX+name,expected,parse)
 for name,expected in FROZEN_FUNCTION_MODULES.items():
  matches=[r for target,r in pubs['old_light_S']['files'].items()if target=='tools/native_light_post_r2_20261025/model/'+name]
  require(len(matches)==1 and matches[0].get('readback_passed')is True and matches[0]['SHA256']==expected==sources.get(str(SOURCE/name)),'Unchanged published frozen probe/high-volume function bytes '+name)
 require(len(pubs['E13_R']['files'])==294 and all(r.get('readback_passed')is True and fullhex(r.get('SHA256'),64)for r in pubs['E13_R']['files'].values()),'Actual full294-file readback R retained; no array reread implied')
 sr=pubs['E13_R']['files'][PREFIX+'source-publication-receipt.json'];require(sr['SHA256']==PUBLICATIONS['E13_S'][1]and sr.get('readback_passed')is True,'Actual source receipt linked from completed R')
 spec=fine('spec.json',True,'E13_S','23fa9078085752c637ebdbc70aa343fde950d85f4abf0872e20ccaa4b416bfcb');summary=fine('summary.json',True,expected='fa807df9bd8ee46ebc5bb7998145deb37c1ea6321bfdb5723a39773b36c2d961');manifest=fine('raw-manifest.json',True,expected='46c67a33f51c43fd97ec4374066808e65cc7cfc3be53bd60cf033a0d2c7a3d72')
 require(manifest.get('Q_frames_returned')is True and manifest.get('GC_before_postprocessing')is True and spec['field_estimator_version']==FIELD_VERSION and spec['fine_cells']==793848 and spec['common97_layer_counts']==[4,19,18,56],'Actual full fine97 producer and released original Q frame')
 worker=fine('worker-receipt.json',True);stage=fine('execution-stage.json',True);verification=fine('input-SHA-verification.json',True);local=fine('synthetic-test-receipt.json',True)
 validate_completed_producer(summary,worker,stage,verification,local,spec,artifacts[str(FINE/'summary.json')]['SHA256'],artifacts[str(FINE/'synthetic-test-receipt.json')]['SHA256'])
 for path,expected in spec['inputs']['source_sha256'].items():
  target='tools/E13_fineXY_20261025/model/'+Path(path).name;row=pubs['E13_S']['files'][target];require(row.get('readback_passed')is True and row['SHA256']==expected,'Actual producing complete source map')
 recovered=item('E13_M',RECOVERY/'receipt.json',META_PREFIX+'owner-receipt.json','4192f6f71d87df92f8aecf1857bc04516240e45b0730a6bfcd0e8ba3dfb56eb0',True)
 prereg=item('E13_M',RECOVERY/'preregistration.json',META_PREFIX+'preregistration.json','09a14928114f8b7db82541aba7680ea8c09554d2ecadbd59c3b781cdce9162f4',True)
 failed=metadata(RECOVERY/'original-numerical-owner-failure.json','8d2b03f4879dda580e7745c6e8ffa55a9125e1db59b08f7a9e53cb09ac309044')
 recovery_contracts.validate_publication_recovery(recovered,prereg,failed,source_commit=PUBLICATIONS['E13_S'][2],result_commit=PUBLICATIONS['E13_R'][2],original_owner_SHA256='8d2b03f4879dda580e7745c6e8ffa55a9125e1db59b08f7a9e53cb09ac309044',supervisor_SHA256='73601dd67e6614347358f591f46c5dab055c4cee138102a1f45b55d2cd54f7bb')
 alias_refs={}
 expected_aliases={'original_S':(FINE/'source-publication/result-publication.json',RECOVERY/'source-publication/result-publication.json'),'result_R':(FINE/'result-publication/result-publication.json',RECOVERY/'result-publication/result-publication.json'),'original_failed_owner':(FINE/'receipt.json',RECOVERY/'original-numerical-owner-failure.json'),'original_publisher_attempt1':(Path('/dev/shm/task1-git-E13-fineXY-result-20261025/attempt-1.json'),RECOVERY/'original-publisher-attempt-1.json')}
 for key,(old,alias)in expected_aliases.items():
  d=recovery_contracts.validate_recovery_alias(recovered['evidence_aliases'][key],old,alias);v=metadata(alias,d['SHA256']);require(alias.stat().st_size==d['bytes'],'Exact original recovery alias bytes');refs[str(alias)]=d['SHA256'];alias_refs[key]=dict(path=str(alias),SHA256=d['SHA256'],bytes=d['bytes'])
  if key=='original_S':require(v==pubs['E13_S'],'Original scientific source alias remains exact')
  elif key=='result_R':require(v==pubs['E13_R'],'Late full readback R alias remains exact')
  elif key=='original_failed_owner':require(v==failed,'Original numerical failure remains failed, never rewritten')
  else:require(v==prereg['prior_publisher_failure']and v.get('status')=='failed_preserved'and v.get('attempt')==1 and v.get('recorded_commit')==PUBLICATIONS['E13_R'][2]and v.get('push_confirmed')is True,'Original first failed publisher retained')
 require(item('E13_M',FINE/'source-publication/result-publication.json',META_PREFIX+'source-publication-receipt.json')['SHA256']==PUBLICATIONS['E13_S'][1]and item('E13_M',FINE/'result-publication/result-publication.json',META_PREFIX+'result-publication-receipt.json')['SHA256']==PUBLICATIONS['E13_R'][1],'M independently preserves original S/R receipt bytes')
 grid_desc=spec['inputs']['geometry']['fine'];require(grid_desc==manifest['geometry']['fine'],'Actual fine grid descriptor identical to original computation')
 grid=item('fine_R',Path(grid_desc['path']),grid_desc['publication_target'],grid_desc['SHA256']);require(grid['bytes']==grid_desc['bytes']and Path(grid['path'])==OLD_FINE/'fine-common97-grid-ROI.npz','Exact unchanged original full fine97 grid/weights archive')
 roi=item('fine_R',OLD_FINE/'fine-ROI-receipt.json','data-native/P23-fineXY-20261025/fine-ROI-receipt.json','dbc4292c3407c8695a68ca907929f397e2cce0d3d8b22f34d4b9b9c741452b56');roi_value=metadata(roi['path'],roi['SHA256']);require(roi_value==spec['inputs']['ROI_receipts']['fine']and roi_value['cells']==793848 and roi_value['layer_counts']==[4,19,18,56],'Original fixed physical ROI definitions and volume weights retained')
 matches=[r for r in summary['candidates']if r['candidate_id']==CANDIDATE_ID];require(len(matches)==1,'Exactly actual full E13 fine case');record=matches[0]
 require(record['physical_geometry_id']==E13 and record['grid_variant']=='XY102-Z97'and record['scalar_archive_kind']=='full_new_fine97'and record['saved_scalar_names']==['AM_max2074','carrier_RMS','Jtotal_vector_RMS','AM_direction_index']and record['Q_resident_during_metrics']is False and record['candidate_adopted']is False,'Actual full fine97 scalar; never coarseSC patch or fabricated keys')
 scalar=record['scalar_arrays'];require(Path(scalar['path']).parent==FINE,'Actual fine scalar belongs to exact producer run');scalar=item('E13_R',Path(scalar['path']),PREFIX+Path(scalar['path']).name,scalar['SHA256'])
 raw={};native_descriptors=[grid,scalar]
 for f,output in((2000,0),(2010,1)):
  old=manifest['fine']['E13'][str(f)];proof=old['proof'];require(proof.get('passed')is True and proof.get('passivity_passed')is True and proof.get('physical_gates',{}).get('passed')is True and proof.get('frequency_Hz')==f and proof.get('driven_output')==output and proof.get('actual_new_RHS')==1 and proof.get('physical_pads')==4 and proof.get('independent_outputs')==2 and proof.get('source_high_impedance_Vpp')==1. and proof.get('source_peak_V')==.5,'Actual completed original carrier/circuit proof')
  p=FINE/'rhs'/('E13-XY102-'+str(f)+'-raw.npz');require(old['raw']['path']==str(p),'Exact original fine carrier raw path')
  d=item('E13_R',p,PREFIX+'rhs/'+p.name,old['raw']['SHA256']);require(d['bytes']==old['raw']['bytes'],'Exact original carrier raw bytes');native_descriptors.append(d)
  raw[str(f)]=dict(d,key='phi_peak_V',frequency_Hz=f,active_output=output,source_peak_V=.5)
 catalog=spec['inputs']['catalog'];require(catalog['common_ROI']==dict(depth_mm=[15,20],depth_origin='physicaltop,+zdown',radius_mm=5)and catalog['grid']['radius_mm']==25 and catalog['grid']['layer_thickness_mm']==[.1,5,5,15],'Fixed D50 layer stack and target ROI')
 first_spec=item('first8_S',FIRST8/'spec.json','data-native/design-screen-coarse-20261025/spec.json','c10bd163e9f8470e07a97e8adb0e8e81cdb7b0dc1b6bd9270d20bbb86ee6af4f',True)
 first_summary=item('first8_R',FIRST8/'summary.json','data-native/design-screen-coarse-20261025/summary.json','1a05816b0358ecf1f6f31590c90ffb3bc7552c3b60c7a9828b1a999bf5337422',True)
 baseline=next(r for r in first_summary['candidates']if r['candidate_id']==B0);require(baseline==spec['inputs']['coarse_B0_record']and first_spec['catalog']==catalog,'Same original coarse101 B0 normalization/cutoff source and exact tissue/contact/circuit catalog')
 cuts=[dict(cutoff_id='original-B0-target-AM-mean',value_V_m=baseline['metrics']['regions']['target']['statistics']['maxTIS']['mean']),dict(cutoff_id='original-B0-offtarget-AM-P95',value_V_m=baseline['metrics']['regions']['off_target']['statistics']['maxTIS']['p95'])]
 require(all(type(r['value_V_m'])in(int,float)and math.isfinite(r['value_V_m'])and r['value_V_m']>0 for r in cuts),'Two actual positive original-B0 numerical cutoffs, never physiological thresholds')
 transfer=item('E13_T',RECOVERY/'auto-transfer/E13-fineXY-recovered-20261025-transfer-manifest.json',TRANSFER_TARGET,'28f3e4120e359a93651f5e5f1c5d42946cc1b5e7847b00ad4172470f00bb4247',True);coverage=validate_manifest_coverage(transfer,native_descriptors)
 provenance=dict(source_run_id=FINE.name,result_commit=pubs['E13_R']['commit'],source_commit=pubs['E13_S']['commit'],batch_spec=artifacts[str(FINE/'spec.json')],field_version=FIELD_VERSION,material_input_SHA256=catalog['material_sha256'],contact_input_SHA256=catalog['contact_sha256'],physical_pad_count=4,independent_outputs=2,return_topology=spec['return_topology'],source_resistance_ohm=50.,arrays_recomputed=False,original_numerical_owner_status='failed_preserved',publication_recovery_completed=True)
 dataset=dict(candidate_id=CANDIDATE_ID,physical_geometry_id=E13,grid_variant='XY102-Z97',grid=dict(grid,key='grid'),weights=dict(grid,keys={r:r+'_volume_weight_m3'for r in REGIONS}),ROI_receipt=roi,scalars=dict(scalar,key='AM_max2074'),scalar_names=copy.deepcopy(record['saved_scalar_names']),raw_by_frequency=raw,record=copy.deepcopy(record),normalizations=copy.deepcopy(validate_normalizations(record['normalizations_to_original_coarse101_B0'])),provenance=provenance)
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(metadata(ap,digest(ap))==a,'Immutable source-published cached-post decision');refs[str(ap)]=digest(ap)
 recovery_evidence=dict(status=recovered['status'],terminal_receipt=artifacts[str(RECOVERY/'receipt.json')],preregistration=artifacts[str(RECOVERY/'preregistration.json')],source_commit=pubs['E13_S']['commit'],result_commit=pubs['E13_R']['commit'],original_numerical_owner_status='failed_preserved',old_numerical_owner_rewritten=False,recovery_only_not_new_numerical_success=True,readonly_aliases=alias_refs,full_transfer_manifest=artifacts[str(RECOVERY/'auto-transfer/E13-fineXY-recovered-20261025-transfer-manifest.json')],transfer_coverage=coverage)
 return dict(schema='task1-E13-fine-light-post-inputs-v1',root_admission=copy.deepcopy(a),datasets=[dataset],original_baseline=dict(candidate_id=B0,record=copy.deepcopy(baseline),cutoffs=cuts,source_commit=pubs['first8_S']['commit'],result_commit=pubs['first8_R']['commit']),E13_publication_recovery=recovery_evidence,provenance=dict(actual_publications=pubmeta,scope='Exactly E13fine stored native scalar/potential postprocessing; zero old-case/PDE/Q/eigen/field/angular/statistic repeats'),source_sha256=sources,input_sha256=refs,publication_metadata=pubmeta,publication_file_proofs=artifacts,holds=copy.deepcopy(summary['holds']),field_version=FIELD_VERSION,common_ROI=copy.deepcopy(catalog['common_ROI']),material_contact_metadata=dict(material=copy.deepcopy(spec['inputs']['material_value']),contact=copy.deepcopy(spec['inputs']['contact_value'])),catalog_model_metadata={k:copy.deepcopy(catalog[k])for k in('gamma_by_frequency','z_by_frequency','material_sha256','contact_sha256','drives','source_resistance_ohm')},body=dict(diameter_mm=50.,layer_thickness_mm=[.1,5.,5.,15.]),new_driven_RHS=0,new_eigen_solves=0,new_angular_metric_evaluations=0,Q_required=False,fields_reconstructed=False,candidate_adopted=False)
def required_inputs(admission=None):return dict(make_spec(admission)['input_sha256'])
