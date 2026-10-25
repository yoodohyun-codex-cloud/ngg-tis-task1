"""Deferred authenticated inputs for a seven-case native GUI display only.

Import is inert. Parent preparation reads bounded JSON/source metadata only;
native NPZ/CSV bytes are never opened here. All native descriptors are direct
full-readback publication proofs; root-owned build verifies bytes after MFG.
"""
import copy
import hashlib
import json
import math
import re
from pathlib import Path

SOURCE=Path('/dev/shm/task1-native-GUI-lite-r2-owner-20261025/source')
MODEL=Path('/dev/shm/task1-native-GUI-lite-20261025/source')
OUT=Path('/dev/shm/task1-native-GUI-lite-r2-20261025-run')
POST=Path('/dev/shm/task1-native-light-post-r2-20261025-run')
FIRST=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
MP=Path('/dev/shm/task1-multipad-extension-20261025-run')
FINE=Path('/dev/shm/task1-P23-fineXY-20261025-run')
ELLIPSE=Path('/dev/shm/task1-centroid-ellipse-20261025-run')
CONSO=Path('/dev/shm/task1-results-consolidation-20261025-run')
B0='B0-square15-c10-diagonal'
P23='P23p5-peripheral-polyomino225'
E13='E13-tangent-P23-centroids-225'
MP_IDS=('MP8-vertical-strips','MP12-vertical-strips','MP16-subpad2x2')
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
MAX_METADATA=8*1024**2
MAX_NATIVE=80*1024**2
KNOWN={
 'post_R':(POST/'result-publication/result-publication.json','252c9918c3809ea4c9c8e12d8c6ddba2ad05743a763cdd3dc74c76f4ac5f24dd','fc7a67876fbcd52396df484a6e5f3fd16b26e6a1'),
 'post_S':(POST/'source-publication/result-publication.json','cc08d308efba7436e899d9da639f6848779865422cf173cbbab47b31439c6ee9','04c75b29bdd325c8e037f7b048095490ad6f662a'),
 'first_R':(FIRST/'result-publication/result-publication.json','d20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159','4d6207caa60ae16ab7a7e997022ac72653b97ec3'),
 'first_S':(FIRST/'source-publication/result-publication.json','cb8939fdd21b3c4d7103eeb26c3591037402553d4369aa195888e30930b1eb49','c8e5f2f9d4fbba5646944772d526533ecedbbab1'),
 'MP_R':(MP/'result-publication/result-publication.json','bbc67386d2dcefbf910a6d6f5698a99c7d852ef14803a417a8d0e5ae90922640','9299ac1ae665fbad5e083e2683ea5789a61e54ad'),
 'MP_S':(MP/'source-publication/result-publication.json','34f5ab39be690a594feccef70736479ff145b32815ff832ccd11c0ab53581a0e','ccc315467edab41b573ff58760baa635bd721b36'),
 'conso_R':(CONSO/'result-publication/result-publication.json','965122fda9670950f97fea5cccbe69ed8176b747602884089276276009335fdd','89c8d2c71fd30d1a4b421346f09b48107e1301b2'),
}

def require(ok,message):
    if not ok:raise ValueError(message)

def fullhex(value,n):return isinstance(value,str)and re.fullmatch('[0-9a-f]{'+str(n)+'}',value)is not None

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()

def metadata(path,expected):
    p=Path(path)
    require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and p.suffix in('.json','.py','.md')and 0<p.stat().st_size<=MAX_METADATA,'Bounded canonical metadata/source only; no native bytes before MFG')
    raw=p.read_bytes();require(fullhex(expected,64)and hashlib.sha256(raw).hexdigest()==expected,'Full metadata SHA before parse')
    return json.loads(raw)

def source_inventory(root=SOURCE):
    root=Path(root);excluded={'root-admission.json','synthetic-test-receipt.json','tests-receipt.json'}
    files=sorted(p for p in root.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')and p.name not in excluded)
    require(files and all(not p.is_symlink()and p.stat().st_size<MAX_METADATA for p in files),'Complete bounded canonical source inventory')
    return {str(root/p.name):digest(root/p.name)for p in files}

def validate_admission(a):
    require(type(a)is dict and a.get('schema')=='task1-native-GUI-lite-build-root-admission-v1'and a.get('status')=='selected_finite_GUI_build'and a.get('root_authorized')is True and a.get('safe_boundary_confirmed')is True,'Separate positive finite GUI build decision')
    require(a.get('source_sha256')=={**source_inventory(MODEL),**source_inventory()}and a.get('model_source_sha256')==source_inventory(MODEL),'Canonical complete combined owner/model inventories, not __file__ deployment paths')
    require(a.get('candidate_adopted')is False and a.get('new_PDE_RHS')==0 and a.get('new_angular_evaluations')==0,'Display only; no scientific solve/rank/adoption')
    r=a.get('native_restore_review');require(type(r)is dict and r.get('status')in('actual_or_unavailable','actual_complete','actual_failed','unavailable')and type(r.get('decision_basis'))is str and r['decision_basis'].strip(),'Current native restore status explicitly actual or unavailable; no inferred PASS')
    require(type(a.get('decision_basis'))is str and a['decision_basis'].strip(),'Root reviewed actual native-post R2 and legacy provenance')
    return a

def publication_descriptor(pub,path,target,expected=None):
    require(pub.get('status')=='published_readback_verified'and fullhex(pub.get('commit'),40),'Complete actual publication only')
    row=pub.get('files',{}).get(target);require(type(row)is dict and row.get('readback_passed')is True and fullhex(row.get('SHA256'),64)and type(row.get('bytes'))is int and 0<row['bytes']<=MAX_NATIVE,'Exact direct full-file readback proof '+target)
    require(expected is None or row['SHA256']==expected,'Published artifact SHA conflict '+target)
    p=Path(path);require(p.is_absolute()and p==p.resolve()and not p.is_symlink(),'Canonical native descriptor; bytes not read during preparation')
    return dict(path=str(p),SHA256=row['SHA256'],bytes=row['bytes'],publication_commit=pub['commit'],publication_target=target,readback_passed=True)

def legacy_publication_role(namespace,artifact_kind):
    """Exact producer ownership; never search/fallback into another receipt.

    Prepared masks were published in S before computation. Stored native raw,
    scalar and grid arrays were published in R. S and R keep their true commit
    and direct SHA/bytes/readback proof; neither is relabelled as the other.
    """
    require(namespace in('first','MP')and artifact_kind in('mask','raw','scalar','grid'),'Explicit known legacy producer and artifact kind')
    return namespace+('_S'if artifact_kind=='mask'else'_R')

def normalization_rows(value):
    require(type(value)is dict and value.get('status')=='complete'and set(value.get('comparisons',{}))==set(MODES),'Four original independent normalization records')
    for mode,row in value['comparisons'].items():
        scale=row.get('amplitude_scale');require(type(scale)in(int,float)and math.isfinite(scale)and scale>=0,'Published amplitude only '+mode)
    return copy.deepcopy(value['comparisons'])

def _top5_only(path):
    """Read producer's small top-level list without materializing 600 probes.

    Caller has already streamed SHA of this complete published metadata file.
    The frozen producer uses two-space JSON indentation; fail if layout changes.
    """
    lines=[];matches=0;capture=False
    with Path(path).open('r',encoding='utf-8')as stream:
        for line in stream:
            if line.startswith('  "provisional_top5": ['):
                matches+=1;capture=True;lines=[line.split(':',1)[1]];continue
            if capture:
                lines.append(line)
                if line.startswith('  ]'):
                    capture=False
                    require(sum(map(len,lines))<4096,'Top5 metadata must be bounded')
    require(matches==1 and not capture,'Unique actual top-level legacy Top5 list')
    rows=json.loads(''.join(lines).rstrip().rstrip(','));require(type(rows)is list and len(rows)==5 and len(set(rows))==5 and all(type(x)is str for x in rows),'Original published five ordered IDs, never rerank')
    return rows

def make_spec(admission=None):
    if admission is None:
        ap=SOURCE/'root-admission.json';require(ap.is_file(),'Positive root GUI admission absent');admission=metadata(ap,digest(ap))
    a=validate_admission(admission);pins={**source_inventory(),**source_inventory(MODEL)};pubs={};pubmeta={};native={};proofs={}
    def addpub(name,path,sha,commit):
        pub=metadata(path,sha);require(pub.get('status')=='published_readback_verified'and pub.get('commit')==commit,'Actual publication identity '+name)
        pins[str(path)]=sha;pubs[name]=pub;pubmeta[name]=dict(path=str(path),SHA256=sha,commit=commit);return pub
    for name,(path,sha,commit)in KNOWN.items():addpub(name,path,sha,commit)
    def desc(name,path,target,expected=None):
        d=publication_descriptor(pubs[name],path,target,expected);proofs[str(path)]=d
        if Path(path).suffix not in('.json','.py','.md'):native[str(path)]=d
        return d
    def read(name,path,target,expected=None):
        d=desc(name,path,target,expected);pins[d['path']]=d['SHA256'];return metadata(d['path'],d['SHA256'])
    def relative(name,root,path,expected=None,parse=False):
        p=Path(path);require(p.is_relative_to(root),'Actual producer relative file identity')
        prefix={'post':'native-light-post-r2-20261025','first':'design-screen-coarse-20261025','MP':'multipad-extension-20261025','fine':'P23-fineXY-20261025','ellipse':'centroid-ellipse-20261025'}[name.split('_')[0]]
        target='data-native/'+prefix+'/'+p.relative_to(root).as_posix()
        return read(name,p,target,expected)if parse else desc(name,p,target,expected)
    post_spec=relative('post_S',POST,POST/'spec.json',parse=True);post_sum=relative('post_R',POST,POST/'summary.json',parse=True)
    receipt=relative('post_R',POST,POST/'synthetic-test-receipt.json',parse=True)
    require(receipt.get('status')=='passed'and receipt.get('tests_run')==30 and receipt.get('model_tests_run')==24 and receipt.get('owner_tests_run')==6 and all(receipt.get(k)==0 for k in('tests_failed','tests_errors','tests_skipped')),'Actual native-post R2 thirty tests all PASS')
    require(receipt.get('model_source_sha256')==post_spec['inputs']['source_sha256'],'Actual post result/test/source inventory binding')
    for path,sha in receipt['model_source_sha256'].items():
        hits=[(t,r)for t,r in pubs['post_S']['files'].items()if t.endswith('/'+Path(path).name)and r.get('SHA256')==sha]
        require(len(hits)==1 and hits[0][1].get('readback_passed')is True,'Full native-post source publication inventory')
    require(post_sum.get('status')=='cached_native_highvolume_and40probe_postbatch_computed_unadopted'and (post_sum.get('completed_native_geometries'),post_sum.get('requested_probes'),post_sum.get('calculated_probes'),post_sum.get('strict_same_layer_bracket_available_probes'),post_sum.get('same_layer_extrapolated_probes'))==(3,120,120,60,60),'Complete actual post R2 three-case/120probe/strict60/extrap60 contract')
    require(post_sum.get('candidate_adopted')is False and all(post_sum.get(k)==0 for k in('actual_new_PDE_RHS','actual_new_Q_loads','actual_new_eigen_solves','actual_new_angular_evaluations')),'Cached post only, no admission by inference')
    context=post_spec['inputs'];require(len(context['datasets'])==3 and context['optional_ellipse_missing']is None,'Actual complete fineB0/fineP23/E13 required; missing mandatory GUI case blocks')
    for name,p in context['publication_metadata'].items():
        if name in('fine_R','fine_S','ellipse_R','ellipse_S'):addpub(name,Path(p['path']),p['SHA256'],p['commit'])
    # Validate both original legacy batches using their source and result specs.
    first_summary=relative('first_R',FIRST,FIRST/'summary.json',parse=True);first_spec=relative('first_S',FIRST,FIRST/'spec.json',parse=True)
    mp_summary=relative('MP_R',MP,MP/'summary.json',parse=True);mp_spec=relative('MP_S',MP,MP/'spec.json',parse=True)
    require(first_summary['spec']==first_spec and mp_summary['spec']==mp_spec,'Published legacy S specs exactly match executed R summaries')
    require(first_spec['catalog']['gamma_by_frequency']==mp_spec['catalog']['gamma_by_frequency']and first_spec['catalog']['z_by_frequency']==mp_spec['catalog']['z_by_frequency'],'Legacy same actual material/contact model')
    fine_spec=relative('fine_S',FINE,FINE/'spec.json',parse=True)
    fine_summary=relative('fine_R',FINE,FINE/'summary.json',parse=True)
    ellipse_summary=relative('ellipse_R',ELLIPSE,ELLIPSE/'summary.json',parse=True)
    fine_inputs=fine_spec['inputs'];donor=fine_inputs['P23_mask'];pp=donor['publication_proof'];addpub('P23_donor',Path(pp['path']),pp['SHA256'],pp['commit'])
    donor_desc=desc('P23_donor',donor['path'],donor['publication_target'],donor['SHA256'])
    baseline=next(r for r in first_summary['candidates']if r['candidate_id']==B0)
    require(baseline==context['original_baseline']['record'],'Original coarse101 B0 remains authoritative reference')
    first_grid=relative('first_R',FIRST,FIRST/'common-grid-and-ROI.npz');mp_grid=relative('MP_R',MP,MP/'common-grid-and-ROI.npz')
    cases=[]
    for d in context['datasets']:
        d=copy.deepcopy(d);cid=d['candidate_id'];isellipse=cid==E13;producer='ellipse_R'if isellipse else'fine_R';root=ELLIPSE if isellipse else FINE
        actual_summary=ellipse_summary if isellipse else fine_summary
        require(d['record']==next(r for r in actual_summary['candidates']if r['candidate_id']==cid),'Float64 source stats/normalizations/geometry match their direct published executed R row')
        for key in('grid','scalars'):
            old=d[key]
            # E13 grid is the original first8 archive, not ellipse-recomputed.
            d[key]=relative('first_R',FIRST,old['path'],old['SHA256'])if Path(old['path']).is_relative_to(FIRST)else relative(producer,root,old['path'],old['SHA256'])
        d['E2000']=relative(producer,root,d['raw_by_frequency']['2000']['path'],d['raw_by_frequency']['2000']['SHA256']);d['section']='new_native';d['pad_count']=4
        d['normalizations']=normalization_rows(d['normalizations']);d['geometry']=dict(kind='ellipse',record=copy.deepcopy(d['record']['geometry']))if isellipse else dict(kind='polyomino',mask=donor_desc,pads=copy.deepcopy(fine_inputs['P23donor']['pads']),spacing_mm=.5)if d['physical_geometry_id']==P23 else dict(kind='rectangles',pads=copy.deepcopy(baseline['geometry']['pads']))
        if isellipse:
            d['fractional_mask']=relative('ellipse_R',ELLIPSE,ELLIPSE/'ellipse-fractional-contact-mask.csv')
            d['ellipse_geometry_receipt']=relative('ellipse_R',ELLIPSE,ELLIPSE/'ellipse-contact-quadrature-receipt.json',parse=True)
            require(d['ellipse_geometry_receipt']==d['record']['geometry']['preflight_and_contact'],'Actual fractional support receipt matches published analytic geometry metadata')
        postrow=next(r for r in post_sum['candidates']if r['candidate_id']==cid)
        for key,pkey in(('probe_json','probe_receipt'),('probe_arrays','probe_arrays'),('high_volume','high_volume_receipt')):
            old=postrow[pkey];d[key]=relative('post_R',POST,old['path'],old['SHA256'])
        pred=metadata(d['probe_json']['path'],d['probe_json']['SHA256']);pins[d['probe_json']['path']]=d['probe_json']['SHA256']
        require(pred.get('probe_count')==40 and pred.get('calculated_probe_count')==40 and pred.get('strict_same_layer_bracket_available_probe_count')==20 and pred.get('same_layer_extrapolated_probe_count')==20,'Actual forty probes and 20+20 per native case')
        d['probe_record']=pred;d['high_volume_record']=metadata(d['high_volume']['path'],d['high_volume']['SHA256']);pins[d['high_volume']['path']]=d['high_volume']['SHA256'];d['label']=('Fine B0'if cid.startswith(B0)else'Fine P23'if cid.startswith(P23)else'E13 (unadopted)');cases.append(d)
    for cid in(B0,)+MP_IDS:
        isbase=cid==B0;summary=first_summary if isbase else mp_summary;root=FIRST if isbase else MP;name='first_R'if isbase else'MP_R';r=next(r for r in summary['candidates']if r['candidate_id']==cid);geom=r['geometry']
        namespace='first'if isbase else'MP'
        mask=relative(legacy_publication_role(namespace,'mask'),root,geom['mask_path'],geom['mask_sha256']);scalar=relative(legacy_publication_role(namespace,'scalar'),root,r['scalar_arrays']['path'],r['scalar_arrays']['SHA256']);raw=summary['raw_artifacts'].get(cid+'-2000')
        require(type(raw)is dict,'Actual original legacy raw2000 descriptor, no regenerated field')
        rawdesc=relative(legacy_publication_role(namespace,'raw'),root,raw['path'],raw['SHA256'])
        cases.append(dict(candidate_id=cid,label='Original B0'if isbase else cid.split('-')[0],physical_geometry_id=cid,section='legacy_reference',grid_variant='XY100-Z101',pad_count=4 if isbase else int(cid.split('-')[0][2:]),grid=first_grid if isbase else mp_grid,scalars=scalar,E2000=rawdesc,mask=mask,geometry=dict(kind='rectangles',pads=copy.deepcopy(geom['pads'])),record=copy.deepcopy(r),normalizations=normalization_rows(r['normalizations']),provenance=dict(source_run_id=root.name,source_commit=pubs['first_S'if isbase else'MP_S']['commit'],result_commit=pubs[name]['commit'],field_version=context['field_version'],material_input_SHA256=first_spec['catalog']['material_sha256'],contact_input_SHA256=first_spec['catalog']['contact_sha256'])))
    require(len(cases)==7 and [c['pad_count']for c in cases[3:]]==[4,8,12,16],'Exactly fixed seven source cases')
    conso_target='data-native/results-consolidation-20261025/summary.json'
    hits=[t for t in pubs['conso_R']['files']if t.endswith('/summary.json')];require(len(hits)==1,'Unique consolidation summary proof')
    cs=desc('conso_R',CONSO/'summary.json',hits[0]);pins[cs['path']]=cs['SHA256'];require(digest(cs['path'])==cs['SHA256'],'Complete legacy Top5 source SHA before selective text read');top5=_top5_only(cs['path'])
    # All ranges are registered from original published Float64 statistics;
    # no native/display reduction or candidate switch can alter them later.
    ammax=max(float(row['absolute_ROI_fields_V_m']['total']['maxTIS']['max'])for c in cases for row in c['normalizations'].values())
    rmsmax=max(float(row['absolute_ROI_fields_V_m']['total']['RMS']['max'])for c in cases for row in c['normalizations'].values())
    jmax=max(float(row['electrical']['contact_normal_J_RMS_max_A_m2'])for c in cases for row in c['normalizations'].values())
    wave_peak=max(float(p['unloaded']['envelope_max_exact_V'])*float(row['amplitude_scale'])for c in cases[:3]for p in c['probe_record']['probes']for row in c['normalizations'].values())
    require(ammax>0 and rmsmax>0 and jmax>0,'Original positive published display ranges')
    require(wave_peak>0 and math.isfinite(wave_peak),'Original exact unloaded envelope peak defines registered waveform display range')
    ranges=dict(x_mm=[-25.,25.],y_mm=[-25.,25.],depth_mm=[0.,25.1],AM_V_m=[0.,ammax],RMS_V_m=[0.,rmsmax],J_A_m2=[0.,jmax],bar_value=[0.,max(float(row['absolute_ROI_fields_V_m'][region]['maxTIS'][stat])for c in cases for row in c['normalizations'].values()for region,stat in(('target','mean'),('target','p10'),('surface_0_5','mean'),('off_target','mean')))],wave_time_ms=[0.,100.],wave_voltage_V=[-wave_peak,wave_peak])
    ap=SOURCE/'root-admission.json'
    if ap.exists():require(metadata(ap,digest(ap))==a,'Actual immutable root admission');pins[str(ap)]=digest(ap)
    return dict(schema='task1-native-GUI-lite-inputs-v1',root_admission=copy.deepcopy(a),metadata_input_sha256=pins,native_input_descriptors=list(native.values()),publication_proofs=pubmeta,source_sha256={**source_inventory(MODEL),**source_inventory()},model_source_sha256=source_inventory(MODEL),cases=cases,original_B0=copy.deepcopy(baseline),legacy_provisional_top5=dict(ordered_ids=top5,publication=cs,ranking_recomputed=False),manual_ranges=ranges,holds=dict(inherited_post=copy.deepcopy(post_sum['inherited_holds']),actual_fine=copy.deepcopy(fine_summary['holds']),actual_fine_adjacent_grid_diagnostics=copy.deepcopy(fine_summary['prospective_adjacent_grid_diagnostics']),actual_ellipse=copy.deepcopy(ellipse_summary['holds'])),native_restore_review=copy.deepcopy(a['native_restore_review']),body=copy.deepcopy(context['body']),material_contact_metadata=copy.deepcopy(context['material_contact_metadata']),catalog_model_metadata=copy.deepcopy(context['catalog_model_metadata']),field_version=context['field_version'],native_bytes_opened_during_prepare=False,new_PDE_RHS=0,new_Q_loads=0,new_angular_evaluations=0,candidate_adopted=False)

def required_inputs(admission=None):return dict(make_spec(admission)['metadata_input_sha256'])
