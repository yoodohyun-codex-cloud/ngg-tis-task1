"""Deferred publication-only inventory. Import performs no IO or numerics."""
import hashlib,json,re
from pathlib import Path
SOURCE=Path('/dev/shm/task1-single-pair-comparison-gui-r2-20261025/source')
TIS_ID='P23p5-peripheral-polyomino225'
PAIR_IDS=('single-pair-square15-c12.5-y0','single-pair-square15-c15-y0')
MAX_FILE=80*1024**2
def require(ok,message):
 if not ok:raise ValueError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def read(path,expected=None):
 path=Path(path);require(path.is_absolute()and path==path.resolve()and path.is_file()and not path.is_symlink()and 0<path.stat().st_size<8*1024**2,'Canonical bounded metadata')
 raw=path.read_bytes();require(expected is None or hashlib.sha256(raw).hexdigest()==expected,'Metadata SHA before parse');return json.loads(raw)
def published_descriptor(path,publication,expected_sha=None):
 path=Path(path);require(publication.get('status')=='published_readback_verified'and re.fullmatch('[0-9a-f]{40}',publication.get('commit','')),'Actual complete immutable result publication')
 matches=[(target,row)for target,row in publication['files'].items()if target.endswith('/'+path.name)and row.get('SHA256')==(expected_sha or row.get('SHA256'))]
 require(len(matches)==1,'Unambiguous direct published identity '+path.name);target,row=matches[0]
 require(row.get('readback_passed')is True and type(row.get('bytes'))is int and 0<row['bytes']<MAX_FILE and re.fullmatch('[0-9a-f]{64}',row.get('SHA256','')),'Complete per-file full SHA readback')
 require(path.is_absolute()and path==path.resolve()and path.is_file()and not path.is_symlink()and path.stat().st_size==row['bytes'],'Canonical actual published file and byte length')
 return dict(path=str(path),SHA256=row['SHA256'],bytes=row['bytes'],publication_commit=publication['commit'],publication_target=target,readback_passed=True)
def existing_descriptor(row,pins):
 proof=row['publication_proof'];require(re.fullmatch('[0-9a-f]{64}',proof.get('SHA256',''))is not None and re.fullmatch('[0-9a-f]{64}',row.get('SHA256',''))is not None and re.fullmatch('[0-9a-f]{40}',row.get('publication_commit',''))is not None,'Original full proof SHA/file SHA/immutable commit')
 pub=read(proof['path'],proof['SHA256']);require(pub['commit']==row['publication_commit'],'Original descriptor publication identity')
 item=published_descriptor(row['path'],pub,row['SHA256']);require(item['publication_target']==row['publication_target'],'Original exact public target identity');pins[proof['path']]=proof['SHA256'];pins[item['path']]=item['SHA256'];return item
def at(value,pointer):
 for key in pointer:value=value[key]
 return value
def make_spec(admission=None):
 if admission is None:admission=read(SOURCE/'root-admission.json')
 require(admission.get('schema')=='task1-single-pair-comparison-gui-root-admission-v1'and admission.get('status')=='selected_finite_single_pair_comparison_gui'and admission.get('root_selected')is True,'Positive root selection after actual single-pair result publication')
 require(admission.get('new_PDE_RHS')==0 and admission.get('new_angular_evaluations')==0 and admission.get('candidate_adopted')is False,'Cached GUI only; no solve, angular reevaluation or adoption')
 require(re.fullmatch('[0-9a-f]{64}',admission.get('single_pair_result_publication_sha256',''))is not None and re.fullmatch('[0-9a-f]{40}',admission.get('single_pair_result_commit',''))is not None,'Explicit full single-pair result receipt SHA and immutable commit')
 require(isinstance(admission.get('decision_basis'),str)and admission['decision_basis'].strip(),'Root quantitative comparison rationale')
 run=Path(admission['single_pair_run']);require(run.is_absolute()and run==run.resolve()and run.parent==Path('/dev/shm')and run.name.startswith('task1-single-pair-refresh'),'Explicit actual root-created refresh run, never an assumed completed run')
 receipt=Path(admission['single_pair_result_publication_path']);require(receipt==run/'result-publication/result-publication.json','Actual single-pair R receipt')
 pub=read(receipt,admission['single_pair_result_publication_sha256']);require(pub.get('commit')==admission['single_pair_result_commit'],'Actual admitted single-pair R commit')
 descriptor=published_descriptor(run/'summary.json',pub);summary=read(descriptor['path'],descriptor['SHA256']);pins={str(receipt):admission['single_pair_result_publication_sha256'],descriptor['path']:descriptor['SHA256']}
 require(summary.get('schema')=='task1-single-pair-refresh-result-v1'and summary.get('status')=='calculated_provisional_single_pair_comparison_unadopted'and summary.get('actual_new_driven_RHS')==2 and summary.get('existing_PDE_repeated')is False and summary.get('TIS_angular_computation_performed')is False and summary.get('Q_resident_during_metrics')is False and summary.get('candidate_adopted')is False,'Actual completed two-pair result, not source/preflight-only status')
 centre=published_descriptor(run/'centre-physical-interpolation.json',pub);pins[centre['path']]=centre['SHA256'];centre_value=read(centre['path'],centre['SHA256']);require(centre_value['physical_point_xyz_mm']==[0.,0.,20.]and centre_value['components_interpolated_before_magnitude']is True and centre_value['nearest_cell_substituted']is False,'Actual physical complex-vector centre interpolation')
 rows=summary['candidates'];require(tuple(row['candidate_id']for row in rows)==PAIR_IDS,'Exact two new y=0 single-pair geometries')
 pairs=[]
 for row in rows:
  cid=row['candidate_id'];require(row['geometry']['physical_pads']==2 and row['geometry']['connected_sources']==1 and row['geometry']['total_contact_area_mm2']==450. and row['single_carrier_envelope_AM_10Hz_V_m']==0. and row['TIS_angular_computation_performed']is False,'Physical two-pad/one-source/zero10HzAM identity')
  files={}
  for suffix in ('-summary.json','-solve-proof.json','-raw-receipt.json','-Q-release-boundary.json','-2000-raw.npz','-RMS-J-scalars.npz'):
   item=published_descriptor(run/(cid+suffix),pub);pins[item['path']]=item['SHA256'];files[suffix]=item
  require(read(files['-summary.json']['path'],files['-summary.json']['SHA256'])==row,'Per-case and consolidated result metadata agree')
  proof=read(files['-solve-proof.json']['path'],files['-solve-proof.json']['SHA256']);require(proof.get('passed')is True and proof['physical_topology']['passed']is True and proof['physical_pads']==2 and proof['connected_sources']==1,'Actual solved physical single-pair gates')
  release=read(files['-Q-release-boundary.json']['path'],files['-Q-release-boundary.json']['SHA256']);require(release.get('raw_frame_returned')is True and release.get('Q_passed_to_metrics')is False,'Actual single-pair Q release before metrics')
  require(row['raw']['SHA256']==files['-2000-raw.npz']['SHA256']and row['scalars']['SHA256']==files['-RMS-J-scalars.npz']['SHA256'],'Direct raw and saved scalar identity')
  pairs.append(dict(candidate_id=cid,record=row,files=files))
 selected=summary['spec']['admission']['selected_TIS_reference'];require(selected['candidate_id']==TIS_ID and summary['selected_TIS_reference']['candidate_id']==TIS_ID,'Root-selected actual latest P23 reference, never an old C1 reference')
 record_descriptor=existing_descriptor(selected['summary'],pins);record=at(read(record_descriptor['path'],record_descriptor['SHA256']),selected['record_pointer']);require(record['candidate_id']==TIS_ID and record['metrics']['frequencies_Hz']==[2000,2010]and record['metrics']['pads']==4 and record['metrics']['independent_outputs']==2,'P23 four pads/two connected outputs/two actual carriers')
 raw={f:existing_descriptor(selected['raw_by_frequency'][f],pins)for f in ('2000','2010')}
 common=existing_descriptor(summary['spec']['admission']['common_grid'],pins);roi=existing_descriptor(summary['spec']['admission']['ROI_receipt'],pins)
 require(common['SHA256']=='f88e921b2d2877482ff368f39e52fea2bd4217fb70037072cda96892b5891d6b','Original full physical grid and fractional-volume ROI masks')
 roi_value=read(roi['path'],roi['SHA256']);require(roi_value==summary['ROI_receipt'],'Original and single-pair ROI receipt identity')
 definition_path=SOURCE/'ECDF_SOURCE_DEFINITIONS.json';definitions=read(definition_path);pins[str(definition_path)]=sha(definition_path)
 for definition in definitions['sources'].values():
  path=Path(definition['path']);require(path.is_file()and not path.is_symlink()and path==path.resolve()and sha(path)==definition['SHA256'],'Exact preserved producer/failed-GUI source bytes');pins[str(path)]=definition['SHA256']
 failed=Path('/dev/shm/task1-single-pair-comparison-gui-20261025-run');failure={}
 for name in ('worker-receipt.json','receipt.json','source-publication/result-publication.json'):
  path=failed/name;value=read(path);pins[str(path)]=sha(path);failure[name]=dict(path=str(path),SHA256=pins[str(path)],record=value)
 require(failure['worker-receipt.json']['record']['status']=='failed_preserved'and 'subsurface_5_10/p95'in failure['worker-receipt.json']['record']['error'],'Preserved actual first-GUI ECDF regression failure, never a successful result')
 failure_path=SOURCE/'prior-GUI-failure-evidence.json';pack=read(failure_path);require(pack['schema']=='task1-prior-single-pair-GUI-failure-evidence-v1'and pack['previous_run']==str(failed)and pack['old_actual_GUI_status']=='failed_preserved','Bounded old GUI failure source package');pins[str(failure_path)]=sha(failure_path)
 for evidence in pack['evidence'].values():
  path=Path(evidence['path']);require(path.is_file()and path==path.resolve()and not path.is_symlink()and path.stat().st_size==evidence['bytes']and sha(path)==evidence['SHA256'],'Preserved original failure evidence remains byte-identical');pins[str(path)]=evidence['SHA256']
 sourcepins={str(SOURCE/name):sha(SOURCE/name)for name in ('pair_gui_inputs.py','pair_gui_post.py','pair_gui_render.py','frozen_pixel_outline.py','ecdf_definitions.py')}
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(read(ap)==admission,'Root admission is immutable');pins[str(ap)]=sha(ap)
 return dict(schema='task1-single-pair-comparison-gui-r2-spec-v1',root_admission=admission,input_sha256=pins,source_sha256=sourcepins,single_pair_summary=descriptor,single_pair_result=summary,centre_interpolation=centre_value,pairs=pairs,TIS=dict(candidate_id=TIS_ID,record=record,raw_by_frequency=raw,reference_metrics=summary['selected_TIS_reference']),common_grid=common,ROI_receipt=roi_value,ECDF_source_definitions=definitions,prior_GUI_failure=failure,expected_comparison_geometries=3,expected_single_pair_geometries=2,new_PDE_RHS=0,new_angular_evaluations=0,Q_loaded=False,candidate_adopted=False)
def required_inputs(admission=None):
 spec=make_spec(admission);return{**spec['input_sha256'],**spec['source_sha256']}
