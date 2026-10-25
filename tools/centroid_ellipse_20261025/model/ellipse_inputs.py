"""Deferred metadata-only tangent-ellipse input contract; import is inert.

No CSV, Q chunk, field/scalar NPZ or native array is read here. Root alone may
call these APIs after the ACTUAL native fine-XY outcome has been published and
reviewed. Its evidence may be a complete result or an explicitly failed one.
"""
from __future__ import annotations
import copy,hashlib,json,math,re
from pathlib import Path
SOURCE=Path('/dev/shm/task1-centroid-ellipse-20261025/source')
FIRST8=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
P23_RUN=Path('/dev/shm/task1-peripheral-fourpad-20261025-run')
RECOVERY=Path('/dev/shm/task1-peripheral-recovery-20261025-run')
GRAPH=Path('/dev/shm/task1-layer-dtn-20261025-run')
FINE_RUN=Path('/dev/shm/task1-P23-fineXY-20261025-run')
B0='B0-square15-c10-diagonal';P23='P23p5-peripheral-polyomino225'
NEW_ID='E13-tangent-P23-centroids-225'
FIELD_VERSION='native-lateral-half-face-v1+analytic-z-DtN-v1'
MATERIAL_SHA='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
CONTACT_SHA='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
MANIFEST_SHA='99753623e06525d86b86cc1c659323e06012d4ddd145e02fd6fc0af514dba4ba'
REMOTE_Q_COMMIT='d725ee29ee568ef26a4b7579e9dfc55d23e0681a'
ORIGINAL_Q_RECEIPT=Path('/dev/shm/task1-cache-retention-20261025-run/public-receipt.json')
ORIGINAL_Q_RECEIPT_SHA='589dad62a301761c930e03f7a74fd33d53caf550e3e5613fbcd10143c4dfd634'
NORMALIZED_Q=Path('/dev/shm/task1-transfer-20261025/cache-publication-normalized.json')
NORMALIZED_Q_SHA='f05f5eb7f37aabdba649ca1c445217aed82663c3bbf875b7193afd7031e35a4f'
MAX_METADATA=8*1024**2
PUBLICATIONS={
 'first8_S':(FIRST8/'source-publication/result-publication.json','cb8939fdd21b3c4d7103eeb26c3591037402553d4369aa195888e30930b1eb49','c8e5f2f9d4fbba5646944772d526533ecedbbab1'),
 'first8_R':(FIRST8/'result-publication/result-publication.json','d20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159','4d6207caa60ae16ab7a7e997022ac72653b97ec3'),
 'P23_S':(P23_RUN/'source-publication/result-publication.json','d73f9f51cca8909849c66de98ee75bf4b4533ef07160cd098d16d7cb332f4753','3329379d39bd8632dc75308e32dc4e30fb9296e7'),
 'P23_partial':(Path('/dev/shm/task1-local-lease-and-cloud-failure-20261025-run/failure-publication/result-publication.json'),'2cae4bdbc3580ec14653eb5b23e1b48ca15c2851323bf89386e2e02e52040a07','2d8ad63f714e549c60e1db4d78792a193ed83c2c'),
 'P23_R':(RECOVERY/'result-publication/result-publication.json','5da8f476cacd4ee323d781f08f3a0a89e7e02d64c1b3a1674069d10ee1eb698d','b30e7b7bd200170ff2b45f2a103c37ddff582a3f'),
 'graph_R':(GRAPH/'result-publication/result-publication.json','41e21c0eb3551b628083aa8e32c5f4ddcb4a8407cfa0202f9e46ddfd064eba1f','815327e978ec5e3976ba9a462510d6faac6f318a')}

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def fullhex(value,n):return isinstance(value,str)and re.fullmatch('[0-9a-f]{'+str(n)+'}',value)is not None
def read_metadata(path,expected):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and 0<p.stat().st_size<MAX_METADATA,'Bounded canonical metadata only');require(fullhex(expected,64),'Full expected metadata SHA');raw=p.read_bytes();require(hashlib.sha256(raw).hexdigest()==expected,'Metadata SHA before parse');return json.loads(raw)
def source_inventory():
 require(SOURCE.is_dir()and not SOURCE.is_symlink(),'Canonical source namespace')
 excluded={'root-admission.json','synthetic-test-receipt.json','tests-receipt.json'}
 paths=sorted(p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')and p.name not in excluded)
 require(any(p.name=='ellipse_inputs.py'for p in paths)and all(not p.is_symlink()and p.stat().st_size<MAX_METADATA for p in paths),'Canonical bounded original source files')
 return{str(p):digest(p)for p in paths}
def publication_file(pub,path,*,relative=None,expected=None):
 """Direct descriptor only; never opens CSV/NPZ/Q content."""
 require(pub.get('status')=='published_readback_verified'and fullhex(pub.get('commit'),40),'Actual complete publication')
 p=Path(path);require(p.is_absolute()and p==p.resolve()and not p.is_symlink(),'Canonical immutable descriptor path')
 tail=relative or p.name;matches=[(key,row)for key,row in pub['files'].items()if key.endswith('/'+tail)];require(len(matches)==1,'Unique direct published relative file '+tail)
 target,row=matches[0];require(row.get('readback_passed')is True and type(row.get('bytes'))is int and row['bytes']>0 and fullhex(row.get('SHA256'),64),'Actual full file SHA/bytes readback')
 require(expected is None or row['SHA256']==expected,'Declared original file identity')
 return dict(path=str(p),SHA256=row['SHA256'],bytes=row['bytes'],publication_commit=pub['commit'],publication_target=target,readback_passed=True,decoded_here=False)

def validate_fine_outcome(kind,primary,missing_fields):
 require(kind in('computed_complete','failed_preserved')and type(primary)is dict and type(missing_fields)is list and all(isinstance(x,str)and x.strip()for x in missing_fields),'Explicit actual native-fine outcome and missing-field list')
 if kind=='computed_complete':
  counters=dict(actual_new_driven_RHS=3,actual_reused_fine_B0_2000_RHS=1,actual_new_metric_evaluations=4)
  require(primary.get('status')=='four_matched97_metric_cases_and_physical_overlap_computed_unadopted'and all(type(primary.get(k))is int and primary[k]==v for k,v in counters.items())and primary.get('candidate_adopted')is False,'Actual completed fine3new/1reuse/four-metric result, never a synthetic47MMS report')
 else:
  require(primary.get('status')in('failed_preserved','adjacent_fineXY_failed_or_partial_preserved','P23_fineXY_failed_or_partial_published')and missing_fields,'Actual known fine-failure status plus explicit missing fields')
  require(primary.get('candidate_adopted')is not True,'Failure cannot adopt a candidate')
 return dict(outcome=kind,primary_status=primary['status'],missing_fields=copy.deepcopy(missing_fields),fine_numeric_fields_used_in_new_ellipse=False,computed_missing_fields_invented=False)
def copy_review_diagnostics(primary):
 """Copy authenticated fine QA evidence only; never derive solver parameters."""
 require(type(primary)is dict,'Actual parsed primary metadata')
 fields=('holds','prospective_adjacent_grid_diagnostics','diagnostics_not_run')
 return dict(source_primary_fields_present={key:key in primary for key in fields},
  **{key:copy.deepcopy(primary[key])if key in primary else None for key in fields},
  diagnostic_metadata_copied_only=True,fine_diagnostic_values_used_as_solver_inputs=False,
  missing_diagnostics_invented=False)
def validate_admission(a):
 require(type(a)is dict and a.get('schema')=='task1-centroid-ellipse-root-admission-v1'and a.get('status')=='admitted_finite_centroid_tangent_ellipse'and a.get('root_review_positive')is True and a.get('sole_NUM_owner')is True,'Separate positive root decision AFTER actual native fineR review')
 fixed=dict(maximum_new_driven_RHS=2,new_angular_metric_evaluations=1,control_metric_aliases=2,new_eigen_solves=0,physical_pads=4,independent_outputs=2,source_high_impedance_Vpp=1.,source_peak_V=.5,source_resistance_ohm=50.,source_allocation_amplitudes=[1.,1.],frequencies_Hz=[2000,2010],common_depth_layer_counts=[8,19,18,56],physical_evaluation_cells=793860,max_physical_evaluation_cells=800000,CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,candidate_adopted=False)
 for key,value in fixed.items():require(key in a and type(a[key])is type(value)and a[key]==value,'Unchanged prospective scope '+key)
 require(type(a.get('source_sha256'))is dict and isinstance(a.get('decision_basis'),str)and a['decision_basis'].strip(),'Exact frozen sources and actual-feedback rationale')
 review=a.get('fine_review');require(type(review)is dict and review.get('run')==str(FINE_RUN)and review.get('root_reviewed')is True and isinstance(review.get('decision_basis'),str)and review['decision_basis'].strip(),'Review ACTUALnative fine run only; reject fineXY-synthetic[-r2]')
 require(review.get('publication_path')==str(FINE_RUN/'result-publication/result-publication.json'),'Exact native fine result publication path; another or synthetic publication cannot stand in')
 require(fullhex(review.get('publication_SHA256'),64)and fullhex(review.get('publication_commit'),40),'Future actual fine publication full identity')
 return a

def _fine_review(a,refs):
 review=a['fine_review'];path=Path(review['publication_path']);pub=read_metadata(path,review['publication_SHA256']);require(pub.get('status')=='published_readback_verified'and pub.get('commit')==review['publication_commit'],'Actual future fineR complete readback, not prepared owner')
 refs[str(path)]=review['publication_SHA256'];given=review['primary_record'];p=Path(given['path']);require(p.is_relative_to(FINE_RUN),'Fine primary record belongs to exact native-fine run')
 desc=publication_file(pub,p,relative=p.relative_to(FINE_RUN).as_posix(),expected=given['SHA256']);require(desc['publication_target']==given['publication_target']and desc['bytes']==given['bytes'],'Exact actual fine primary descriptor')
 refs[str(p)]=desc['SHA256'];primary=read_metadata(p,desc['SHA256'])
 pointer=review.get('primary_record_pointer',[]);require(type(pointer)is list and all(type(k)in(str,int)for k in pointer),'Explicit actual primary-record pointer')
 for key in pointer:primary=primary[key]
 result=validate_fine_outcome(review['outcome'],primary,review['missing_fields']);return dict(**result,run=str(FINE_RUN),publication_path=str(path),publication_SHA256=review['publication_SHA256'],publication_commit=pub['commit'],primary_record=desc,primary_record_pointer=review.get('primary_record_pointer',[]),root_decision_basis=review['decision_basis'],reviewed_primary_diagnostics=copy_review_diagnostics(primary))


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
  path=SOURCE/'root-admission.json';require(path.is_file(),'Positive ellipse admission absent; no input/data work authorized');admission=read_metadata(path,digest(path))
 a=validate_admission(admission);sources=source_inventory();require(a['source_sha256']==sources,'Root binds complete canonical ellipse source inventory')
 refs=dict(sources);review=_fine_review(a,refs);pubs={};proofs={}
 for name,(path,expected,commit)in PUBLICATIONS.items():
  pub=read_metadata(path,expected);require(pub.get('status')=='published_readback_verified'and pub.get('commit')==commit,'Actual original publication '+name);pubs[name]=pub;refs[str(path)]=expected
 def record(name,path,expected=None,parse=False,relative=None):
  desc=publication_file(pubs[name],path,relative=relative,expected=expected);refs[desc['path']]=desc['SHA256'];proofs[desc['path']]=desc;return read_metadata(path,desc['SHA256'])if parse else desc
 first_spec=record('first8_S',FIRST8/'spec.json','c10bd163e9f8470e07a97e8adb0e8e81cdb7b0dc1b6bd9270d20bbb86ee6af4f',True);catalog=copy.deepcopy(first_spec['catalog'])
 summary=record('first8_R',FIRST8/'summary.json','1a05816b0358ecf1f6f31590c90ffb3bc7552c3b60c7a9828b1a999bf5337422',True);require(summary.get('status')=='provisional_eight_layout_screen_computed_unadopted'and summary.get('completed_candidates')==8,'Actual original first8 complete')
 B0record=next(r for r in summary['candidates']if r['candidate_id']==B0)
 pcatalog=record('P23_partial',P23_RUN/'catalog-inputs.json','123c580b2c9ec1128174ddb9c5840fb6f27b6d4ba351cc0039fff77cc56bcdf0',True);donor=next(r for r in pcatalog['candidates']if r['candidate_id']==P23)
 p23record=record('P23_R',RECOVERY/'candidates'/(P23+'-summary.json'),'6318ddcfe9ed1156c3ce632e54bb2d2939d8f8f41e5f4cb0344fa3fbd90e136b',True)
 require(p23record['geometry']==donor and p23record['actual_new_RHS']==0 and p23record['previous_published_RHS_reused']==2,'Actual P23 recovered metrics, not repeated controls')
 field=first_spec['provisional_field'];require(field['derived_field_version']==FIELD_VERSION,'Exact original provisional discreteXY/analyticZ field ABI')
 recovery_summary=record('P23_R',RECOVERY/'summary.json','4562a3915cd7fcd85aedec82fe3a1fc44887b73e94a9037785b08e6fef4ef069',True)
 require(recovery_summary['spec']['recovery_inputs']['original_spec']['provisional_field']['derived_field_version']==FIELD_VERSION,'Same P23 recovered field ABI')
 for key in('gamma_by_frequency','z_by_frequency','common_ROI','grid','drives','source_resistance_ohm'):
  require(catalog[key]==pcatalog[key]==recovery_summary['spec']['recovery_inputs']['catalog'][key],'Exact existing coarse comparison model '+key)
 require(catalog['grid']['h_mm']==.5 and catalog['grid']['nxy']==7860 and catalog['grid']['layer_counts']==[8,19,18,56]and catalog['grid']['cells']==793860 and catalog['grid']['radius_mm']==25 and catalog['grid']['layer_thickness_mm']==[.1,5,5,15],'Preserved D50/coarse101/physical layers')
 require(catalog['common_ROI']==dict(depth_mm=[15,20],depth_origin='physicaltop,+zdown',radius_mm=5),'Original physical target ROI')
 require(catalog['source_resistance_ohm']==50. and catalog['drives']=={'2000':{'output':0,'source_Vpp':1.,'source_peak_V':.5},'2010':{'output':1,'source_Vpp':1.,'source_peak_V':.5}},'Original exact2000/2010 high-Z circuit/output assignment')
 for key,expected in(('material',MATERIAL_SHA),('contact',CONTACT_SHA)):
  require(catalog[key+'_sha256']==pcatalog[key+'_sha256']==expected,'Exact original model receipt SHA')
 material=record('P23_partial',Path(pcatalog['material_path']),MATERIAL_SHA);contact=record('P23_partial',Path(pcatalog['contact_path']),CONTACT_SHA);material_value=read_metadata(material['path'],material['SHA256']);contact_value=read_metadata(contact['path'],contact['SHA256'])
 require(contact_value['Rs_subtractions']==1 and contact_value['measurement_area_multiplications']==1 and contact_value['division_by_two']is False,'Existing Rs/area conversion once; PBS remains uncertain')
 p_mask=record('P23_partial',Path(donor['mask_path']),'09f29590ff68d7768550a20013ce3748e8ff5ea2df71af746eb42577b703540d');record('P23_S',Path(donor['mask_path']),p_mask['SHA256'])
 p_receipt=record('P23_partial',Path(donor['mask_receipt_path']),'03cdc589407f50753dbf1203723909bc1bf4f8581b915e77027da5658d26634e');record('P23_S',Path(donor['mask_receipt_path']),p_receipt['SHA256']);p_value=read_metadata(p_receipt['path'],p_receipt['SHA256'])
 require(p_value['candidate_id']==P23 and p_value['mask_sha256']==p_mask['SHA256']and p_value['exact_area_proof']is True and p_value['no_overlap']is True and p_value['physical_pads']==4 and p_value['independent_outputs']==2,'Actual published centroid donor geometry')
 centres=[]
 require([r['pad']for r in p_value['pads']]==[0,1,2,3],'Exact donor physical-pad order')
 for row in p_value['pads']:
  c=row['area_weighted_centroid_mm'];node=row['pad']if row['pad']<2 else-1
  require(len(c)==2 and all(type(v)in(int,float)and math.isfinite(v)for v in c)and row['node_index']==node and row['analytic_area_m2']==row['represented_area_m2']==.000225,'Published true pad-area centroid and225mm2 only')
  centres.append(dict(pad=row['pad'],centroid_mm=copy.deepcopy(c),node_index=node,node=row['node'],centroid_provenance='Published P23 native full-face mask receipt, not nominalr23.5 or analytic boundary centre',mask_SHA256=p_mask['SHA256'],receipt_SHA256=p_receipt['SHA256'],CSV_centroid_check_pending=True))
 controls={}
 for label,cid,original,raw_pub,mask_pub,scalar_pub,run in(('B0',B0,B0record,'first8_R','first8_S','first8_R',FIRST8),('P23',P23,p23record,'P23_partial','P23_partial','P23_R',P23_RUN)):
  g=original['geometry'];mask=record(mask_pub,Path(g['mask_path']),g['mask_sha256']);scalar=record(scalar_pub,Path(original['scalar_arrays']['path']),original['scalar_arrays']['SHA256']);raw={}
  require(all(p['passed']is True for p in original['source_physics_proofs']),'Actual immutable control physics passed')
  for f,out in((2000,0),(2010,1)):
   raw[str(f)]=record(raw_pub,run/'rhs'/(cid+'-'+str(f)+'-raw.npz'));proof=record(raw_pub,run/'rhs'/(cid+'-'+str(f)+'-solve-proof.json'),parse=True);require(proof['passed']is True and proof['physical_gates']['passed']is True and proof['candidate_id']==cid and proof['frequency_Hz']==f and proof['driven_output']==out,'Actual control carrier/node proof')
  controls[label]=dict(candidate_id=cid,record=copy.deepcopy(original),scalar=scalar,raw_by_frequency=raw,mask=mask,provenance=dict(metric_publication_commit=pubs[scalar_pub]['commit'],raw_publication_commit=pubs[raw_pub]['commit'],immutable_full_metric_scalar_raw_alias=True,new_PDE_RHS=0,new_field_reconstruction=0,new_angular_evaluations=0))
 graph_summary_descriptor=record('graph_R',GRAPH/'summary.json','086053634ae8329c422b16d7bd1b4777395a6925467e47c6dda254f32ad3632f');graph_summary=read_metadata(graph_summary_descriptor['path'],graph_summary_descriptor['SHA256']);graph_arrays=record('graph_R',GRAPH/'arrays.npz','f17d6962e9a1c564de85e0734c5549281168f5a7ff15bb2df85b71f5b1277154')
 manifest_descriptor=record('graph_R',GRAPH/'eigen-cache/manifest.json',MANIFEST_SHA,relative='local-eigen-cache-manifest.json');manifest=read_metadata(manifest_descriptor['path'],manifest_descriptor['SHA256']);require(graph_summary['eigen']['cache']==manifest,'Exact original local coarse graph/cache manifest')
 normalized=read_metadata(NORMALIZED_Q,NORMALIZED_Q_SHA);original_q=read_metadata(ORIGINAL_Q_RECEIPT,ORIGINAL_Q_RECEIPT_SHA);refs[str(NORMALIZED_Q)]=NORMALIZED_Q_SHA;refs[str(ORIGINAL_Q_RECEIPT)]=ORIGINAL_Q_RECEIPT_SHA;remote=validate_chunk_receipts(manifest,normalized,original_q,n=7860,grid_name='xy100')
 for row in remote:require(Path(row['path']).parent==GRAPH/'eigen-cache','Original coarseQ chunk directory');refs[row['path']]=row['SHA256']
 common=record('first8_R',FIRST8/'common-grid-and-ROI.npz','f88e921b2d2877482ff368f39e52fea2bd4217fb70037072cda96892b5891d6b');roi_desc=record('first8_R',FIRST8/'ROI-receipt.json','3b2ea58b3dfb9e25d716e23e6b2f29950512efe25e396dc44560498078799e20');roi=read_metadata(roi_desc['path'],roi_desc['SHA256'])
 pads=[]
 # Evaluated only by admitted ROOT, never on source import. This is a recipe,
 # not a generated mask or a claim that quadrature/physical checks have passed.
 for row in centres:
  x,y=row['centroid_mm'];radius=math.hypot(x,y);require(radius>0,'Nonzero published centroid for tangent direction')
  pads.append(dict(pad=row['pad'],center_mm=copy.deepcopy(row['centroid_mm']),node=row['node'],node_index=row['node_index'],shape='ellipse',semimajor_mm=13.,semiminor_mm=225./(math.pi*13.),semiminor_definition='225/(pi*13)mm',major_axis_unit_xy=[-y/radius,x/radius],minor_axis_unit_xy=[x/radius,y/radius],analytic_area_mm2=225.,mounting='top',represented_contact_area_pending_ROOT_quadrature=True,CSV_centroid_check_pending=True))
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(read_metadata(ap,digest(ap))==a,'Immutable root decision');refs[str(ap)]=digest(ap)
 return dict(schema='task1-centroid-ellipse-inputs-v1',root_admission=copy.deepcopy(a),fine_review=review,source_sha256=sources,input_sha256=refs,catalog=catalog,controls=controls,field_version=FIELD_VERSION,provisional_field=copy.deepcopy(field),P23_mask=p_mask,P23_mask_receipt=p_receipt,P23_mask_receipt_value=p_value,centres_metadata=centres,new_geometry=dict(candidate_id=NEW_ID,physical_pads=4,independent_outputs=2,pads=pads,total_analytic_area_mm2=900.,source_allocation_amplitudes=[1.,1.],new_RHS=2,new_angular_evaluations=1,geometry_validation_status='pending_ROOT_CSV_centroid_check_and_predeclared_quadrature_containment_overlap_area_gates'),graph_arrays=graph_arrays,graph_summary=graph_summary,graph_summary_descriptor=graph_summary_descriptor,Q_manifest=manifest,Q_manifest_descriptor=manifest_descriptor,remote_Q_chunk_proofs=remote,normalized_Q_receipt=dict(path=str(NORMALIZED_Q),SHA256=NORMALIZED_Q_SHA,commit=REMOTE_Q_COMMIT),original_Q_receipt=dict(path=str(ORIGINAL_Q_RECEIPT),SHA256=ORIGINAL_Q_RECEIPT_SHA,commit=REMOTE_Q_COMMIT),historical_manifest_remote_flags_unchanged=True,common_grid_ROI=common,ROI_receipt=roi,ROI_receipt_descriptor=roi_desc,material=material,contact=contact,material_value=material_value,contact_value=contact_value,publication_file_proofs=proofs,CPU_limit=4,total_memory_bytes=8000000000,max_physical_evaluation_cells=800000,new_eigen_solves=0,control_metric_aliases=2,controls_PDE_field_or_angular_repeated=False,holds=copy.deepcopy(first_spec['holds']),candidate_adopted=False)
def required_inputs(admission=None):return dict(make_spec(admission)['input_sha256'])
