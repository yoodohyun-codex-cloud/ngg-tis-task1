"""Deferred small-metadata provenance for native scalar/probe postprocessing.

Import is stdlib-only and inert. No Q, native arrays, CSV, NumPy or scientific
code is imported/read. Root alone calls these APIs after an actual ellipse
outcome has been publicly preserved and explicitly reviewed.
"""
import copy,hashlib,json,math,re
from pathlib import Path
SOURCE=Path('/dev/shm/task1-native-light-post-20261025/source')
FINE=Path('/dev/shm/task1-P23-fineXY-20261025-run')
FIRST8=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
ELLIPSE=Path('/dev/shm/task1-centroid-ellipse-20261025-run')
B0='B0-square15-c10-diagonal';P23='P23p5-peripheral-polyomino225';E13='E13-tangent-P23-centroids-225'
FIELD_VERSION='native-lateral-half-face-v1+analytic-z-DtN-v1'
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
MAX_METADATA=8*1024**2
PUBLICATIONS={
 'fine_R':(FINE/'result-publication/result-publication.json','0a9f71adef7439f19c2334ffef96c5f83e271c75c2440af3582615bfb998e075','fd0b0becc1f38d5c8118c929e7c5c4f24cc64c47'),
 'first8_R':(FIRST8/'result-publication/result-publication.json','d20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159','4d6207caa60ae16ab7a7e997022ac72653b97ec3'),
 'first8_S':(FIRST8/'source-publication/result-publication.json','cb8939fdd21b3c4d7103eeb26c3591037402553d4369aa195888e30930b1eb49','c8e5f2f9d4fbba5646944772d526533ecedbbab1')}

def require(ok,message):
 if not ok:raise ValueError(message)
def fullhex(value,n):return isinstance(value,str)and re.fullmatch('[0-9a-f]{'+str(n)+'}',value)is not None
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def metadata(path,expected):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and 0<p.stat().st_size<MAX_METADATA,'Canonical bounded metadata only')
 require(fullhex(expected,64)and digest(p)==expected,'Full small-metadata SHA before parse');return json.loads(p.read_bytes())
def canonical_source_key(name):
 require(type(name)is str and Path(name).name==name and name not in('.','..'),'Canonical source basename only');return str(SOURCE/name)
def source_inventory():
 excluded={'root-admission.json','synthetic-test-receipt.json','tests-receipt.json'}
 files=sorted(p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')and p.name not in excluded)
 require(any(p.name=='light_inputs.py'for p in files)and all(not p.is_symlink()and p.stat().st_size<MAX_METADATA for p in files),'Complete bounded canonical source inventory')
 return{canonical_source_key(p.name):digest(SOURCE/p.name)for p in files}
def validate_admission(a):
 require(type(a)is dict and a.get('schema')=='task1-native-light-post-root-admission-v1'and a.get('status')=='admitted_finite_native_light_post'and a.get('root_review_positive')is True and a.get('sole_NUM_owner')is True,'Actual separate positive finite native-light-post decision')
 for key in('new_driven_RHS','new_eigen_solves','new_angular_metric_evaluations'):
  require(type(a.get(key))is int and a[key]==0,'Zero new scientific solves/angles '+key)
 require(a.get('native_Q_loaded')is False and a.get('fields_reconstructed')is False and a.get('candidate_adopted')is False,'Postprocess only stored native scalar/potential records; no Q/field reconstruction/adoption')
 require(a.get('CPU_limit')==4 and a.get('total_RSS_plus_all_owned_tmpfs_bytes')==8000000000,'Unchanged whole-research resource cap')
 require(type(a.get('decision_basis'))is str and bool(a['decision_basis'].strip())and type(a.get('source_sha256'))is dict,'Actual rationale and canonical source inventory required')
 r=a.get('ellipse_review');require(type(r)is dict and r.get('run')==str(ELLIPSE)and r.get('root_reviewed')is True and type(r.get('decision_basis'))is str and bool(r['decision_basis'].strip()),'Actual ellipse outcome must be reviewed before this postbatch')
 require(r.get('outcome')in('computed_complete','failed_preserved')and fullhex(r.get('publication_SHA256'),64)and fullhex(r.get('publication_commit'),40),'Explicit publicly preserved ellipse outcome identity')
 require(r.get('publication_path')==str(ELLIPSE/'result-publication/result-publication.json'),'Exact actual ellipse result/failure publication receipt, never a synthetic or other run')
 require(type(r.get('primary_record'))is dict and type(r.get('missing_fields'))is list and all(type(x)is str and x.strip()for x in r['missing_fields']),'Actual primary outcome descriptor and explicit missing fields')
 return a

def direct(pub,path,target,expected=None):
 p=Path(path);require(pub.get('status')=='published_readback_verified'and fullhex(pub.get('commit'),40),'Actual full-readback publication, not a prepared plan')
 require(p.is_absolute()and p==p.resolve()and not p.is_symlink(),'Canonical deferred native descriptor')
 row=pub['files'][target];require(row.get('readback_passed')is True and fullhex(row.get('SHA256'),64)and type(row.get('bytes'))is int and 0<row['bytes']<80*1024**2,'Direct full file SHA/bytes proof '+target)
 require(expected is None or row['SHA256']==expected,'Exact advertised native artifact identity '+target)
 return dict(path=str(p),SHA256=row['SHA256'],bytes=row['bytes'],publication_commit=pub['commit'],publication_target=target,readback_passed=True,arrays_decoded_here=False)
def validate_normalizations(value):
 require(type(value)is dict and value.get('status')=='complete'and set(value['comparisons'])==set(MODES),'All four original-B0 normalizations remain separate')
 for mode,row in value['comparisons'].items():
  x=row.get('amplitude_scale');require(type(x)in(int,float)and math.isfinite(x)and x>=0,'Finite existing normalization amplitude, no inferred rescaling '+mode)
 return value
def validate_ellipse_outcome(kind,primary,missing):
 require(kind in('computed_complete','failed_preserved')and type(primary)is dict and type(missing)is list,'Explicit actual ellipse status')
 if kind=='computed_complete':
  require(not missing and primary.get('status')=='single_centroid_area_matched_ellipse_screen_computed_unadopted','Only actual complete ellipse fields may be used')
  for key,value in dict(completed_conditions=3,actual_new_driven_RHS=2,actual_new_angular_metric_evaluations=1,actual_immutable_control_aliases=2,actual_control_RHS_repeated=0,actual_control_angular_metrics_repeated=0,new_eigen_solves=0).items():
   require(type(primary.get(key))is int and primary[key]==value,'Actual complete ellipse accounting '+key)
  require(primary.get('Q_resident_during_metrics')is False and primary.get('candidate_adopted')is False,'No Q-resident metrics or adoption assumed')
  return dict(status=kind,ellipse_fields_available=True,missing_fields=[],computed_missing_fields_invented=False)
 status=primary.get('status','');allowed=('failed_preserved','failed_partial_preserved_no_automatic_resolve','centroid_ellipse_failed_or_partial_preserved','centroid_ellipse_failed_or_partial_published');require(status in allowed and primary.get('candidate_adopted')is not True and bool(missing)and all(type(x)is str and x.strip()for x in missing),'Published failed ellipse outcome needs known actual owner status, no adoption and named missing fields')
 return dict(status=kind,ellipse_fields_available=False,missing_fields=copy.deepcopy(missing),computed_missing_fields_invented=False)

def _context(a):
 sources=source_inventory();require(a['source_sha256']==sources,'Root decision binds complete canonical postprocess source inventory')
 refs=dict(sources);pubs={};pubproofs={};artifacts={}
 def pub(name,path,expected,commit):
  obj=metadata(path,expected);require(obj.get('status')=='published_readback_verified'and obj.get('commit')==commit,'Actual known publication '+name);pubs[name]=obj;refs[str(path)]=expected;pubproofs[name]=dict(path=str(path),SHA256=expected,commit=commit);return obj
 for name,(path,expected,commit)in PUBLICATIONS.items():pub(name,path,expected,commit)
 def item(name,path,target,expected=None,parse=False):
  d=direct(pubs[name],path,target,expected);refs[d['path']]=d['SHA256'];artifacts[d['path']]=d;return metadata(path,d['SHA256'])if parse else d
 fineR=pubs['fine_R'];fineSrow=fineR['files']['data-native/P23-fineXY-20261025/source-publication-receipt.json'];require(fineSrow['readback_passed']is True,'Fine source receipt itself preserved in actual result')
 fineSpath=FINE/'source-publication/result-publication.json';pub('fine_S',fineSpath,fineSrow['SHA256'],'83a61fb55bd42a8ef778a8653c8aa31bbdf647e0')
 def fine(path,expected=None,parse=False,where='fine_R'):return item(where,path,'data-native/P23-fineXY-20261025/'+Path(path).relative_to(FINE).as_posix(),expected,parse)
 spec=fine(FINE/'spec.json','ef39c4d106fbb33ce23a58793faf10a35a067f5c7e1eb0506ebf95225d92c4aa',True,'fine_S');fine(FINE/'spec.json',digest(FINE/'spec.json'))
 summary=fine(FINE/'summary.json','fa3239f8a56d2c26558d40bb2afd834adabea3a24d4292ec5632dd7586d4c22f',True);require(summary['status']=='four_matched97_metric_cases_and_physical_overlap_computed_unadopted'and summary['candidate_adopted']is False and summary['Q_resident_during_postprocessing']is False,'Actual complete unadopted fine batch only')
 manifest=fine(FINE/'raw-manifest.json','88d36157b7574ff2337072a572d434a1f6f2c3aeb90a67c2d22c59d95a33b78e',True);require(manifest['Q_frames_returned']is True and manifest['GC_before_postprocessing']is True,'Native raw frame was released before stored scalars')
 first_summary=item('first8_R',FIRST8/'summary.json','data-native/design-screen-coarse-20261025/summary.json','1a05816b0358ecf1f6f31590c90ffb3bc7552c3b60c7a9828b1a999bf5337422',True)
 first_spec=item('first8_S',FIRST8/'spec.json','data-native/design-screen-coarse-20261025/spec.json','c10bd163e9f8470e07a97e8adb0e8e81cdb7b0dc1b6bd9270d20bbb86ee6af4f',True)
 baseline=next(r for r in first_summary['candidates']if r['candidate_id']==B0);require(baseline==spec['inputs']['coarse_B0_record'],'Original coarse101-B0 record remains the primary fixed cap/cutoff source')
 require(spec['field_estimator_version']==FIELD_VERSION and spec['inputs']['first8catalog']==first_spec['catalog'],'Same physical/material/contact/circuit/field model')
 catalog=first_spec['catalog'];require(catalog['common_ROI']==dict(depth_mm=[15,20],depth_origin='physicaltop,+zdown',radius_mm=5)and catalog['grid']['radius_mm']==25 and catalog['grid']['layer_thickness_mm']==[.1,5,5,15],'Fixed D50/layers/target ROI')
 grid=fine(FINE/'fine-common97-grid-ROI.npz',manifest['geometry']['fine']['SHA256']);roi=fine(FINE/'fine-ROI-receipt.json',parse=False)
 datasets=[]
 for label,ident in(('B0',B0+'-XY102-Z97'),('P23',P23+'-XY102-Z97')):
  record=next(r for r in summary['candidates']if r['candidate_id']==ident);require(record['scalar_archive_kind']=='full_new_fine97'and record['Q_resident_during_metrics']is False and record['candidate_adopted']is False,'Use full actual fine97 scalars; no coarseSC patch pretending to be full')
  scalar=fine(Path(record['scalar_arrays']['path']),record['scalar_arrays']['SHA256']);normalizations=validate_normalizations(record['normalizations_to_original_coarse101_B0']);raw={}
  for f,out in((2000,0),(2010,1)):
   old=manifest['fine'][label][str(f)];p=old['proof'];require(p['passed']is True and p['passivity_passed']is True and p['physical_gates']['passed']is True and p['frequency_Hz']==f and p['driven_output']==out,'Actual completed fine carrier proof and frequency/output identity')
   raw[str(f)]=dict(fine(Path(old['raw']['path']),old['raw']['SHA256']),key='phi_peak_V',optional_E_key='E_peak_V_m',frequency_Hz=f,active_output=out,source_peak_V=.5)
  datasets.append(dict(candidate_id=ident,physical_geometry_id=record['physical_geometry_id'],grid_variant='XY102-Z97',grid=dict(grid,key='grid'),weights=dict(grid,keys={r:r+'_volume_weight_m3'for r in REGIONS}),ROI_receipt=roi,scalars=dict(scalar,key='AM_max2074'),scalar_names=copy.deepcopy(record['saved_scalar_names']),raw_by_frequency=raw,record=copy.deepcopy(record),normalizations=copy.deepcopy(normalizations),provenance=dict(source_run_id=FINE.name,result_commit=pubs['fine_R']['commit'],source_commit=pubs['fine_S']['commit'],batch_spec=artifacts[str(FINE/'spec.json')],field_version=FIELD_VERSION,material_input_SHA256=catalog['material_sha256'],contact_input_SHA256=catalog['contact_sha256'],physical_pad_count=4,independent_outputs=2,return_topology='Common GND pads2/3; inactive ideal output0V through its single50ohm',source_resistance_ohm=50.,arrays_recomputed=False)))
 cuts=[dict(cutoff_id='original-B0-target-AM-mean',value_V_m=baseline['metrics']['regions']['target']['statistics']['maxTIS']['mean']),dict(cutoff_id='original-B0-offtarget-AM-P95',value_V_m=baseline['metrics']['regions']['off_target']['statistics']['maxTIS']['p95'])]
 for cutoff in cuts:require(type(cutoff['value_V_m'])in(int,float)and math.isfinite(cutoff['value_V_m'])and cutoff['value_V_m']>0,'Existing originalB0 positive numerical cutoff')
 original_grid=item('first8_R',FIRST8/'common-grid-and-ROI.npz','data-native/design-screen-coarse-20261025/common-grid-and-ROI.npz','f88e921b2d2877482ff368f39e52fea2bd4217fb70037072cda96892b5891d6b')
 original_roi=item('first8_R',FIRST8/'ROI-receipt.json','data-native/design-screen-coarse-20261025/ROI-receipt.json','3b2ea58b3dfb9e25d716e23e6b2f29950512efe25e396dc44560498078799e20')
 review=a['ellipse_review'];epath=Path(review['publication_path']);pub('ellipse_R',epath,review['publication_SHA256'],review['publication_commit']);provided=review['primary_record'];ppath=Path(provided['path']);require(ppath.is_relative_to(ELLIPSE)and provided['publication_target']=='data-native/centroid-ellipse-20261025/'+ppath.relative_to(ELLIPSE).as_posix(),'Ellipse primary actual record belongs to exact new run and matching direct publication target')
 d=item('ellipse_R',ppath,provided['publication_target'],provided['SHA256']);require(d['bytes']==provided['bytes'],'Exact ellipse primary readback byte count');primary=metadata(ppath,d['SHA256'])
 pointer=review.get('primary_record_pointer',[]);require(type(pointer)is list and all(type(k)in(str,int)for k in pointer),'Explicit actual failure-record pointer')
 for k in pointer:primary=primary[k]
 ellipse_outcome=validate_ellipse_outcome(review['outcome'],primary,review['missing_fields']);ellipse_outcome.update(publication=pubproofs['ellipse_R'],primary_record=d,root_decision_basis=review['decision_basis'])
 if ellipse_outcome['ellipse_fields_available']:
  require(ppath==ELLIPSE/'summary.json'and pointer==[],'Completed ellipse uses its actual complete overall summary')
  er=next(r for r in primary['candidates']if r['candidate_id']==E13);require(er['control_alias']is False and er['candidate_adopted']is False,'New actual ellipse record only')
  espan=primary['spec'];ec=espan['inputs'];require(espan['field_version']==FIELD_VERSION and ec['catalog']==catalog,'Ellipse uses same actual baseline/material/contact/circuit and provisional field definition')
  srow=pubs['ellipse_R']['files']['data-native/centroid-ellipse-20261025/source-publication-receipt.json'];require(srow['readback_passed']is True,'Actual ellipse source publication preserved')
  espath=ELLIPSE/'source-publication/result-publication.json';es=metadata(espath,srow['SHA256']);pub('ellipse_S',espath,srow['SHA256'],es['commit'])
  edspec=item('ellipse_S',ELLIPSE/'spec.json','data-native/centroid-ellipse-20261025/spec.json',parse=True);require(edspec==espan,'Published ellipse source spec matches actual overall summary')
  def eitem(desc):return item('ellipse_R',Path(desc['path']),'data-native/centroid-ellipse-20261025/'+Path(desc['path']).relative_to(ELLIPSE).as_posix(),desc['SHA256'])
  escalar=eitem(er['scalar_arrays']);eraw={}
  for f,out in((2000,0),(2010,1)):
   entry=er['raw_by_frequency'][str(f)];proof=entry['proof'];require(proof['passed']is True and proof['physical_gates']['passed']is True and proof['frequency_Hz']==f and proof['driven_output']==out,'Actual complete ellipse source carrier proof')
   eraw[str(f)]=dict(eitem(entry['raw']),key='phi_peak_V',optional_E_key='E_peak_V_m',frequency_Hz=f,active_output=out,source_peak_V=.5)
  require(ec['common_grid_ROI']['SHA256']==original_grid['SHA256'],'Ellipse original coarse101 native grid identity')
  datasets.append(dict(candidate_id=E13,physical_geometry_id=E13,grid_variant='XY100-Z101',grid=dict(original_grid,key='grid'),weights=dict(original_grid,keys={r:r+'_volume_weight_m3'for r in REGIONS}),ROI_receipt=original_roi,scalars=dict(escalar,key='AM_max2074'),scalar_names=copy.deepcopy(er['scalar_saved_names']),raw_by_frequency=eraw,record=copy.deepcopy(er),normalizations=copy.deepcopy(validate_normalizations(er['normalizations'])),provenance=dict(source_run_id=ELLIPSE.name,result_commit=pubs['ellipse_R']['commit'],source_commit=pubs['ellipse_S']['commit'],batch_spec=artifacts[str(ELLIPSE/'spec.json')],field_version=FIELD_VERSION,material_input_SHA256=catalog['material_sha256'],contact_input_SHA256=catalog['contact_sha256'],physical_pad_count=4,independent_outputs=2,return_topology='Common GND pads2/3; inactive ideal output0V through its single50ohm',source_resistance_ohm=50.,arrays_recomputed=False)))
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(metadata(ap,digest(ap))==a,'Immutable postprocess root decision');refs[str(ap)]=digest(ap)
 return dict(schema='task1-native-light-post-inputs-v1',root_admission=copy.deepcopy(a),datasets=datasets,original_baseline=dict(candidate_id=B0,record=copy.deepcopy(baseline),normalizations=copy.deepcopy(validate_normalizations(baseline['normalizations'])),cutoffs=cuts,common_grid_ROI=original_grid,ROI_receipt=original_roi,source_commit=pubs['first8_S']['commit'],result_commit=pubs['first8_R']['commit'],cutoff_policy='Fixed original coarse101-B0-relative numerical cutoffs selected before this postbatch, after original PDE; not physiological/safety thresholds'),ellipse_outcome=ellipse_outcome,optional_ellipse_missing=None if ellipse_outcome['ellipse_fields_available']else copy.deepcopy(ellipse_outcome),provenance=dict(actual_publications=copy.deepcopy(pubproofs),fine_complete_result=pubproofs['fine_R'],fine_source_publication=pubproofs['fine_S'],original_B0_result=pubproofs['first8_R'],ellipse_outcome=copy.deepcopy(ellipse_outcome),scope='Stored native scalar/potential postprocess only; input descriptors authenticated without array decode; no Q/eigen/PDE/field/angular work'),source_sha256=sources,input_sha256=refs,publication_metadata=pubproofs,publication_file_proofs=artifacts,holds=copy.deepcopy(summary['holds']),field_version=FIELD_VERSION,common_ROI=copy.deepcopy(catalog['common_ROI']),material_contact_metadata=copy.deepcopy(spec['inputs']['original_material_contact_values']),catalog_model_metadata={k:copy.deepcopy(catalog[k])for k in('gamma_by_frequency','z_by_frequency','material_sha256','contact_sha256','drives','source_resistance_ohm')},body=dict(diameter_mm=50.,layer_thickness_mm=[.1,5.,5.,15.]),native_array_work_deferred_to_sole_root=True,new_driven_RHS=0,new_eigen_solves=0,new_angular_metric_evaluations=0,Q_required=False,fields_reconstructed=False,candidate_adopted=False)
def make_spec(admission=None):
 if admission is None:
  p=SOURCE/'root-admission.json';require(p.is_file(),'New actual-outcome-bound light postprocess decision absent');admission=metadata(p,digest(p))
 return _context(validate_admission(admission))
def required_inputs(admission=None):return dict(make_spec(admission)['input_sha256'])
