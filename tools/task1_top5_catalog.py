"""Bounded metadata-only catalog of distinct Task1 electrode layouts.

No native fields, grid CSV, masks, NPZ archives, solver, ledger or worker launch
is opened here. The owning root registers and runs this CLI under its finite
resource guard. Ranking is a discrete-model diagnostic, never adoption.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import time
import task1_candidate_screen as screen

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='task1-top5-layout-catalog-v1'
BASELINE_VOLUME=Path('docs/cloud-next-20261021T085200Z/return-role-volume.json')
BASELINE_NATIVE=Path('data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json')
V8_RECEIPT=Path('docs/CLOUD_VOLUME_RESULTS_20261021_v8.receipt.json')
MAX_DISCOVERY_FILES=512
MAX_METADATA_FILES=2048
MAX_FILE_BYTES=25*1024**2
MAX_TOTAL_METADATA_BYTES=256*1024**2
MAX_OUTPUT_BYTES=2*1024**2
METRICS=('maxTIS','fixedTIS','RMS')
REGIONS=('total',screen.PRIMARY,'supplemental_wholeXY_depth15_20','surface_0_5','primary_complement','supplemental_complement')
GATE_NAMES=[x['name']for x in screen.GATE_DEFINITIONS]
require=screen.require


def digest_json(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def finite(v):return type(v)in(int,float)and math.isfinite(v)


class MetadataStore:
    """Allow only bounded canonical JSON/properties; all raw paths are metadata."""
    def __init__(self,root=ROOT):
        self.root=Path(root).resolve();self.cache={};self.hashes={};self.bytes_read=0
    def path(self,path):
        p=Path(path);p=p if p.is_absolute()else self.root/p
        require(p==p.resolve()and p.is_relative_to(self.root)and p.is_file()and not p.is_symlink(),'Canonical existing repository path required: '+str(p))
        require(p.suffix in('.json','.properties'),'Catalog only reads JSON/properties metadata: '+str(p))
        return p
    def load(self,path,expected=None):
        p=self.path(path);key=str(p)
        if key not in self.cache:
            size=p.stat().st_size
            require(len(self.cache)<MAX_METADATA_FILES and size<=MAX_FILE_BYTES and self.bytes_read+size<=MAX_TOTAL_METADATA_BYTES,'Finite metadata read bound exceeded')
            raw=p.read_bytes();require(len(raw)==size,'Metadata changed during read');self.bytes_read+=len(raw)
            self.hashes[key]=hashlib.sha256(raw).hexdigest()
            if p.suffix=='.json':value=json.loads(raw)
            else:
                value={}
                for line in raw.decode().splitlines():
                    if line.strip()and not line.lstrip().startswith('#'):
                        k,v=line.split('=',1);value[k.strip()]=v.strip()
            self.cache[key]=value
        require(expected is None or self.hashes[key]==expected,'Metadata SHA mismatch: '+key)
        return self.cache[key]
    def ref(self,path,expected=None):
        self.load(path,expected);p=self.path(path);return dict(path=str(p),SHA256=self.hashes[str(p)])
    def verify_unchanged(self):
        for path,expected in self.hashes.items():
            p=self.path(path);size=p.stat().st_size
            require(size<=MAX_FILE_BYTES and self.bytes_read+size<=MAX_TOTAL_METADATA_BYTES,'Finite metadata preservation-check bound exceeded')
            raw=p.read_bytes();self.bytes_read+=len(raw)
            require(len(raw)==size and hashlib.sha256(raw).hexdigest()==expected,'Catalog metadata changed during collection: '+path)


def native_active_frequencies(condition):
    spectrum=condition['metrics']['source_current_spectrum']
    frequencies=sorted({s['frequency_Hz']for s in spectrum if any(v!=0 for key in('real_A','imaginary_A')for v in s[key])})
    require(frequencies and all(finite(v)and v>0 for v in frequencies),'Native actual nonzero frequency spectrum required')
    return frequencies


def _scientific_content(row):
    def clean(value):
        if isinstance(value,dict):return {k:clean(v)for k,v in value.items()if k!='interpretation'}
        if isinstance(value,list):return [clean(v)for v in value]
        return value
    return clean({k:row.get(k)for k in('normalizations','electrical_metrics','coefficient_vectors','source_waveform')})


def scientific_equivalent(a,b):
    if finite(a)and finite(b):return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-18)
    if isinstance(a,dict)and isinstance(b,dict):return set(a)==set(b)and all(scientific_equivalent(a[k],b[k])for k in a)
    if isinstance(a,list)and isinstance(b,list):return len(a)==len(b)and all(scientific_equivalent(x,y)for x,y in zip(a,b))
    return type(a)is type(b)and a==b


def _polygon(points):
    require(isinstance(points,list)and len(points)>=3,'At least three physical polygon vertices required')
    vertices=[]
    for p in points:
        require(isinstance(p,(list,tuple))and len(p)==2 and all(finite(v)for v in p),'Finite physical polygon coordinates required')
        q=tuple(0. if round(float(v),12)==0 else round(float(v),12)for v in p)
        if not vertices or vertices[-1]!=q:vertices.append(q)
    if vertices[0]==vertices[-1]:vertices.pop()
    require(len(vertices)>=3,'Nondegenerate physical polygon required')
    variants=[]
    for seq in(vertices,list(reversed(vertices))):
        start=min(range(len(seq)),key=lambda i:seq[i]);variants.append(tuple(seq[start:]+seq[:start]))
    return [list(p)for p in min(variants)]


def geometry_identity(case):
    """Intended physical polygons remove CSV/path/vertex-order aliases only."""
    circuit=case['circuit'];pads=case.get('design',{}).get('pads');mapping=circuit['pad_to_node']
    topology=dict(n_pads=circuit['n_pads'],n_outputs=circuit['n_outputs'],n_return_nodes=circuit['n_return_nodes'],
        return_topology=circuit['return_topology'])
    if isinstance(pads,list)and len(pads)==circuit['n_pads']and all(isinstance(p.get('polygon_mm'),list)and len(p['polygon_mm'])>=3 for p in pads):
        physical=[]
        for index,pad in enumerate(pads):
            i=int(pad.get('pad',index));require(str(i)in mapping,'Physical pad node mapping missing')
            physical.append(dict(node=mapping[str(i)],polygon_mm=_polygon(pad['polygon_mm'])))
        physical.sort(key=lambda p:json.dumps(p,sort_keys=True,separators=(',',':')))
        identity=dict(**topology,physical_pads=physical)
        return digest_json(identity),dict(method='physical_polygons_and_node_assignment',polygon_coordinate_rounding_mm=1e-12,
            physical_definition=identity,operative_mask_SHA256=case['mask_sha256'],scope='Grouping only, never rounds numerical fields or model parameters')
    identity=dict(**topology,operative_mask_SHA256=case['mask_sha256'],pad_to_node=mapping)
    return digest_json(identity),dict(method='operative_mask_SHA256_and_node_assignment_fallback',physical_definition=identity,
        scope='No complete polygon metadata; encoding aliases may remain distinct and are disclosed')


def spatial_checks(modes,baseline):
    row=dict(normalizations=modes);checks=screen.screen_checks(row,dict(normalizations=baseline))
    for check in checks:
        delta=check['baseline']-check['candidate']if check['required_direction']=='greater'else check['candidate']-check['baseline']
        check['relative_violation']=max(0.,(delta-check['arithmetic_tolerance'])/check['baseline'])
    target=modes['skin_contact_only']['regions'][screen.PRIMARY]['maxTIS']
    return checks,[max(x['relative_violation']for x in checks),sum(x['relative_violation']for x in checks),-target['p10'],-target['mean']]


def validate_modes(modes,baseline):
    require(set(modes)==set(screen.MODES),'All five complete normalizations required')
    limits=baseline['raw_1Vpp']['normalized_burdens']
    for name,mode in modes.items():
        require(finite(mode['amplitude_scale'])and mode['amplitude_scale']>0,'Positive finite amplitude required')
        require(set(mode['regions'])==set(REGIONS),'Six fixed full-volume ROI masks required')
        require(mode.get('baseline_derived_numerical_limits')==limits,'Original four-pad numerical limits must remain fixed')
        require(set(screen.CAP_DEGREES)<=set(mode['normalized_burdens'])and all(finite(v)and v>=0 for v in mode['normalized_burdens'].values()),'Actual finite burdens required')
        require(len(mode['source_output_RMS_by_output_mA'])==2 and all(finite(v)and v>=0 for v in mode['source_output_RMS_by_output_mA']),'Two actual output RMS currents required')
        for region,metrics in mode['regions'].items():
            for metric in METRICS:
                stat=metrics[metric];reference=baseline[name]['regions'][region][metric]
                require(all(finite(stat[k])and stat[k]>=0 for k in('mean','p10','p95','min','max','std','CV','volume_m3'))and stat['volume_m3']>0,
                    'Complete native weighted statistics required; truncated GUI rows cannot be ranked')
                require(stat['min']<=stat['p10']<=stat['p95']<=stat['max']and stat['min']<=stat['mean']<=stat['max']and
                    type(stat['positive_weight_cells'])is int and stat['positive_weight_cells']>0,'Native percentile ordering and positive weighted cell count required')
                require(math.isclose(stat['volume_m3'],reference['volume_m3'],rel_tol=1e-10,abs_tol=1e-15),'Same physical fine ROI represented volume required')
                cutoffs=stat['fixed_baseline_threshold_volume'];original=reference['fixed_baseline_threshold_volume']
                require(set(cutoffs)==set(original),'Fixed original cutoff identifiers required')
                for key,value in cutoffs.items():
                    require(value['cutoff_V_m']==original[key]['cutoff_V_m']and finite(value['volume_m3'])and 0<=value['volume_m3']<=stat['volume_m3']+1e-18,
                        'Original fixed cutoff and actual high-field volumes required')
    skin=modes['skin_contact_only'];require(skin.get('includes_source_power_cap')is False and skin.get('includes_1Vpp_ceiling')is False,
        'Skin8 excludes source power and1Vpp ceiling')
    cap_checks={}
    for key in screen.CAP_DEGREES:
        actual=skin['normalized_burdens'][key];limit=limits[key]
        require(finite(limit)and limit>0,'Positive original cap required')
        passed=actual<=limit*(1+1e-10)+1e-18
        cap_checks[key]=dict(actual=actual,limit=limit,ratio=actual/limit,passed=passed)
    require(all(v['passed']for v in cap_checks.values()),'Actual normalized skin/contact cap violation')
    return cap_checks


def discover(store):
    docs=store.root/'docs';paths=set();proofs={}
    for p in docs.glob('cloud*/**/*volume*.json'):
        n=p.name.lower()
        if not any(s in n for s in('native-volume-metrics','checkpoint','plan','attempt','failure','spec')):paths.add(p)
    for pattern in('*RESULTS*.result-brief.json','cloud*/**/*result-brief.json'):
        paths.update(docs.glob(pattern))
    receipt=store.root/V8_RECEIPT
    if receipt.is_file():
        obj=store.load(receipt)
        refs=obj.get('historical_snapshot',{}).get('historical_input_artifact_proofs',[])+obj.get('current_audits',[])
        for ref in refs:
            if isinstance(ref,dict)and ref.get('path')and str(ref['path']).endswith('.json'):
                p=store.path(ref['path']);paths.add(p);proofs[str(p)]=ref['SHA256']
    require(len(paths)<=MAX_DISCOVERY_FILES,'Bounded discovery file cap exceeded')
    return sorted(paths,key=lambda p:str(p)),proofs


def _descriptor(paths,names):
    found=[(p,h)for p,h in paths.items()if Path(p).name in names]
    require(len(found)==1,'Exactly one declared native descriptor required: '+str(names))
    p,h=found[0];return dict(path=p,SHA256=h,verification='declared_native_digest_no_array_read')


class CatalogBuilder:
    def __init__(self,root=ROOT):
        self.store=MetadataStore(root);self.native_cache={};self.rows={};self.aliases=[];self.exclusions=[];self.report_counts={};self.baseline=None;self.conflicted_keys=set()
    def reject(self,path,reason,row=None):
        self.exclusions.append(dict(source=str(path),condition_id=None if row is None else row.get('condition_id',row.get('id',row.get('case_id'))),reason=str(reason)))
    def native(self,path,expected=None):
        st=self.store;p=st.path(path);summary=st.load(p,expected)
        if str(p)in self.native_cache:return self.native_cache[str(p)]
        run=p.parents[2];pre_path=run/'preregistration.json';pre=st.load(pre_path);ident=summary['id'];cases=[c for c in pre['cases']if c['id']==ident]
        require(len(cases)==1,'One native registered case required');case=cases[0];record_path=run/'cases'/(ident+'.json');record=st.load(record_path)
        config_path=st.path(case['config_file']);config=st.load(config_path,case['config_sha256']);refs={str(x):st.hashes[str(x)]for x in(p,pre_path,record_path,config_path)}
        require(summary['status']==record['status']=='complete'and record['id']==ident and record['postprocess_sha256']==st.hashes[str(p)]and
            record['config_sha256']==case['config_sha256']==summary['mesh_metadata']['config_sha256'],'Completed native source/config/case SHA identity required')
        require(pre['gates']==screen.NATIVE_GATES and all(finite(record['validation'][k])and 0<=record['validation'][k]<=v and
            summary['validation'][k]==record['validation'][k]and summary['validation_gate_status'][k]['status']=='passed'and
            summary['validation_gate_status'][k]['value']==record['validation'][k]and summary['validation_gate_status'][k]['limit']==v
            for k,v in screen.NATIVE_GATES.items()),'Five matching completed native equation gates required')
        require(summary.get('source_inputs_unchanged')is True,'Native source-input preservation receipt required')
        meta=summary['mesh_metadata'];circuit=case['circuit']
        require(config.get('mask.sha256')==case['mask_sha256'],'Operative config mask digest differs from native case')
        require(meta['h_xy_mm']==.625 and meta['sc_cells']==2 and meta['bulk_layer_counts']==[14,14,40]and meta['cells']==351680,
            'Exclude SC4/coarse or different bulk grid')
        require(case.get('source_coating_nm')==10 and case.get('source_Rs_fit_window_Hz')==500,'Nominal PBS10nm/Rs-fit-window500Hz model required')
        require(circuit['n_outputs']==2 and circuit['n_return_nodes']==1 and circuit['source_resistance_ohm']==50 and circuit['source_peak_V']==.5 and
            circuit['source_Vpp_each']==1 and circuit['return_topology']=='all_return_pads_ideal_common_GND'and circuit['n_pads']in(4,8,12,16),'Physical pad count, two outputs and one commonGND50ohm required')
        require(case.get('design',{}).get('contact_plane_z_mm',0)==0,'Only top surface contacts eligible')
        signature=screen.comparison_signature(summary,config_path)
        raw=summary['input_sha256'];grid=_descriptor(raw,{'grid.csv','grid.csv.gz'});mesh=_descriptor(raw,{'mesh-metadata.json'})
        actualmeta=st.load(mesh['path'],mesh['SHA256']);require(actualmeta==meta,'Native mesh metadata differs from post summary')
        refs[mesh['path']]=mesh['SHA256'];geometry_key,geometry=geometry_identity(case)
        obj=dict(native_summary=dict(path=str(p),SHA256=st.hashes[str(p)]),native_registration=dict(path=str(pre_path),SHA256=st.hashes[str(pre_path)]),
            native_case_record=dict(path=str(record_path),SHA256=st.hashes[str(record_path)]),native_config=dict(path=str(config_path),SHA256=case['config_sha256']),
            case=case,circuit=circuit,summary=summary,source_commit=pre['source_commit'],configuration_sha256=case['config_sha256'],source_run_id=run.name,
            source_case_id=ident,mesh_metadata=meta,grid=grid,mesh=mesh,geometry_key=geometry_key,geometry_identity=geometry,
            declared_native_inputs=raw,mask=dict(path=config['mask.path'],SHA256=config['mask.sha256'],verification='declared_mask_digest_no_array_read'),source_refs=refs,comparison_signature=signature)
        self.native_cache[str(p)]=obj;return obj
    def normalize(self,native,modes,condition_id,waveform,source_path,*,condition=None,producer=None,label=None):
        st=self.store;require(self.baseline is None or native['comparison_signature']==self.baseline['comparison_signature'],'Nominal model/grid/ROI comparison signature differs')
        n=native;native_conditions=[c for c in n['summary']['conditions']if c['id']==condition_id]
        native_condition=native_conditions[0]if len(native_conditions)==1 else None
        if condition is not None:
            require(condition['status']=='calculated_unadopted'and condition['source_run_id']==n['source_run_id']and condition['source_case_id']==n['source_case_id']and
                condition['configuration_sha256']==n['configuration_sha256']and condition['source_commit']==n['source_commit'],'Derived command must bind exact native source/config/commit')
            require(condition.get('candidate_adopted')is False,'Unadopted derived source required')
        else:require(native_condition is not None,'Exact native source condition required')
        refs=dict(n['source_refs']);p=st.path(source_path);refs[str(p)]=st.hashes[str(p)]
        condition_ref=None;archive=None;probe_ref=None
        if condition is not None:
            condition_ref=dict(path=str(p),SHA256=st.hashes[str(p)]);require(producer is not None,'Completed derived producer receipt required')
            parent_path,parent,entry=producer;refs[str(parent_path)]=st.hashes[str(parent_path)]
            for name in('volume.npz','probes.json'):
                artifact=entry.get('artifacts',{}).get(name)
                if artifact:
                    if name=='volume.npz':archive=artifact
                    else:probe_ref=artifact
        else:
            name=native_condition['native_volume_archive'];archive=dict(path=str(Path(n['native_summary']['path']).parent/name),SHA256=n['summary']['artifacts']['files'][name]['SHA256'])
            probe_name=n['summary']['artifacts']['probes_json'];probe_ref=dict(path=str(Path(n['native_summary']['path']).parent/probe_name),SHA256=n['summary']['artifacts']['files'][probe_name]['SHA256'])
        scalar=dict(available=archive is not None,verification='declared_archive_digest_no_array_read',prefix='',keys={k:k for k in(*METRICS,'maxTIS_direction_index')})
        if archive:scalar.update(path=str(st.root/Path(archive['path']))if not Path(archive['path']).is_absolute()else archive['path'],SHA256=archive['SHA256'])
        else:scalar['reason']='Producer deliberately omitted derivative scalar archive; reconstruction not executed'
        row={k:copy.deepcopy(v)for k,v in n.items()if k!='summary'}
        row.update(id=n['source_case_id']+'__'+condition_id,condition_id=condition_id,label=label or condition_id,waveform=waveform,
            normalizations=copy.deepcopy(modes),scales={k:v['amplitude_scale']for k,v in modes.items()},source_refs=refs,scalar_archive=scalar,
            condition_source=condition_ref,native_condition=copy.deepcopy(native_condition),probe_artifact=copy.deepcopy(probe_ref),
            electrical_metrics=copy.deepcopy(condition['electrical_metrics']if condition is not None else native_condition['metrics']),
            coefficient_vectors=copy.deepcopy(condition.get('coefficient_vectors'))if condition is not None else None,
            source_waveform=copy.deepcopy(condition.get('source_waveform'))if condition is not None else None,
            actual_fundamental_Hz=copy.deepcopy(condition.get('actual_fundamental_Hz'))if condition is not None else native_condition['actual_fundamental_Hz'],
            active_frequencies_Hz=copy.deepcopy(condition.get('active_frequencies_Hz',condition.get('actual_fundamental_Hz')))if condition is not None else native_active_frequencies(native_condition),
            calculation_status='calculated_unadopted',numerical_validation_scope='Native equation gates and stored sampled2074 volume metrics; mesh/contact/experiment validation held',candidate_adopted=False)
        return row
    def add(self,row,source_path):
        if self.baseline is None:raise ValueError('Canonical baseline must be established before collection')
        row['skin_cap_checks']=validate_modes(row['normalizations'],self.baseline['normalizations'])
        checks,score=spatial_checks(row['normalizations'],self.baseline['normalizations']);row['gate_checks']=checks
        row['eight_gate_values']={c['name']:c['candidate']for c in checks};row['ranking_score']=score+[row['id']]
        key=digest_json([row['condition_id'],row['configuration_sha256'],row['waveform']]);row['row_key']=key
        require(key not in self.conflicted_keys,'Previously conflicting duplicate actual condition remains quarantined')
        old=self.rows.get(key)
        if old:
            consistent=scientific_equivalent(_scientific_content(row),_scientific_content(old))
            if not consistent:
                self.rows.pop(key);self.conflicted_keys.add(key)
                self.reject(source_path,'Conflicting duplicate metrics/scales: both variants quarantined',row)
                raise ValueError('Conflicting duplicate metrics/scales: both variants quarantined')
            self.aliases.append(dict(row_key=key,id=row['id'],source=str(source_path),alias_of=old['id'],reason='same_condition_native_config_waveform_replayed_no_new_computation'))
            # Prefer an actual source command over cached presentation copies.
            if row['condition_source']and not old['condition_source']:self.rows[key]=row
        else:self.rows[key]=row
    def producer(self,condition_path,condition):
        st=self.store;p=st.path(condition_path)
        for folder in list(p.parents)[:5]:
            q=folder/'summary.json'
            if not folder.is_relative_to(st.root)or not q.is_file()or q==p:continue
            parent=st.load(q)
            if parent.get('status')!='calculated_unadopted'or parent.get('inputs_unchanged')is not True:continue
            for entry in parent.get('conditions',[]):
                ref=entry.get('artifacts',{}).get('condition.json')
                if ref and st.path(ref['path'])==p and ref['SHA256']==st.hashes[str(p)]:return q,parent,entry
        raise ValueError('Actual condition has no completed SHA-bound producer summary')
    def volume(self,path,obj):
        require(obj.get('schema')=='task1-volume-selectivity-v1'and obj.get('status')=='calculated_unadopted'and obj.get('inputs_unchanged')is True,'Not a completed native-volume comparison report')
        refs=obj['inputs_sha256']
        for raw in obj['cases']:
            try:
                native=self.native(raw['summary_path'],refs.get(raw['summary_path']));require(refs.get(raw['summary_path'])==native['native_summary']['SHA256'],'Report must pin exact native summary SHA')
                require(raw['configuration_sha256']==native['configuration_sha256']and raw['source_commit']==native['source_commit'],'Volume row native source/config differs')
                row=self.normalize(native,raw['normalizations'],raw['condition_id'],next(c['waveform']for c in native['summary']['conditions']if c['id']==raw['condition_id']),path,label=raw.get('label'))
                self.add(row,path)
            except(ValueError,KeyError,StopIteration,TypeError)as error:self.reject(path,error,raw)
    def brief(self,path,obj):
        require(obj.get('status')not in('failed','failed_preserved','failed_preregistration','error')and obj.get('candidate_adopted',False)is False,'Failed execution/adopted presentation is excluded; failed comparison screens remain eligible stored results')
        for raw in obj.get('rows',obj.get('cases',obj.get('conditions',[]))):
            if not isinstance(raw,dict)or not isinstance(raw.get('normalizations'),dict):continue
            try:
                proof=raw.get('source_proof')or raw.get('condition_JSON')or raw.get('artifacts',{}).get('condition.json')
                if not proof:
                    summary_path=raw.get('summary_path')
                    if summary_path:
                        # Its authoritative full volume comparison is collected first.
                        matches=[r for r in self.rows.values()if r['source_case_id']==raw.get('case_id')and r['condition_id']==raw.get('condition_id')]
                        require(bool(matches),'Truncated brief without resolved authoritative volume row')
                        self.aliases.append(dict(id=matches[0]['id'],source=str(path),alias_of=matches[0]['id'],reason='brief_replays_resolved_native_volume_row'));continue
                    raise ValueError('No explicit actual source JSON proof')
                source_path=self.store.path(proof['path']);source=self.store.load(source_path,proof['SHA256'])
                if source.get('status')=='complete'and 'mesh_metadata'in source:
                    native=self.native(source_path,proof['SHA256']);cond=next(c for c in native['summary']['conditions']if c['waveform']==raw.get('waveform','square_3h'))
                    matches=[r for r in self.rows.values()if r['configuration_sha256']==native['configuration_sha256']and r['condition_id']==cond['id']]
                    require(bool(matches),'Native presentation control has no authoritative full volume row')
                    self.aliases.append(dict(id=matches[0]['id'],source=str(path),alias_of=matches[0]['id'],reason='native_control_presentation_alias'));continue
                require(isinstance(source.get('normalizations'),dict),'Fixed-amplitude mesh/contact/bounds diagnostic is outside ranking scope')
                native_path=self.store.root/'data-native'/source['source_run_id']/'postprocess'/source['source_case_id']/'summary.json';native=self.native(native_path)
                row=self.normalize(native,source['normalizations'],source['id'],source['waveform'],source_path,condition=source,
                    producer=self.producer(source_path,source),label=raw.get('label'))
                row['source_refs'][str(path)]=self.store.hashes[str(path)];self.add(row,path)
            except(ValueError,KeyError,StopIteration,TypeError)as error:self.reject(path,error,raw)
    def collect(self):
        st=self.store;bp=st.root/BASELINE_VOLUME;report=st.load(bp)
        require(report.get('schema')=='task1-volume-selectivity-v1'and report.get('status')=='calculated_unadopted'and report.get('inputs_unchanged')is True,'Completed canonical baseline volume receipt required')
        raw=next(c for c in report['cases']if c['summary_path']==str(st.root/BASELINE_NATIVE))
        native=self.native(raw['summary_path'],report['inputs_sha256'][raw['summary_path']]);self.baseline=self.normalize(native,raw['normalizations'],raw['condition_id'],'square_3h',bp,label='Original four-square baseline')
        self.add(copy.deepcopy(self.baseline),bp);self.baseline=self.rows[next(iter(self.rows))]
        paths,proofs=discover(st);briefs=[]
        for path in paths:
            try:
                obj=st.load(path,proofs.get(str(path)))
                if obj.get('schema')=='task1-volume-selectivity-v1':self.volume(path,obj);self.report_counts['volume']=self.report_counts.get('volume',0)+1
                elif path.name.endswith('result-brief.json'):briefs.append((path,obj))
                else:self.reject(path,'Unsupported metadata schema; no completed full-volume candidate rows')
            except(ValueError,KeyError,TypeError,json.JSONDecodeError)as error:self.reject(path,error)
        for path,obj in briefs:
            try:self.brief(path,obj)
            except(ValueError,KeyError,TypeError)as error:self.reject(path,error)
        return self.finish()
    def finish(self):
        st=self.store
        st.verify_unchanged()
        require(self.baseline is not None,'Canonical baseline missing');basekey=self.baseline['geometry_key']
        groups={}
        for row in self.rows.values():
            if row['geometry_key']!=basekey:groups.setdefault(row['geometry_key'],[]).append(row)
        ranked=[]
        for key,rows in groups.items():
            representative=min(rows,key=lambda r:tuple(r['ranking_score']));representative=copy.deepcopy(representative)
            representative['layout_competitor_count']=len(rows);ranked.append(representative)
        ranked.sort(key=lambda r:tuple(r['ranking_score']))
        selected=ranked[:5]
        for index,row in enumerate(selected,1):row['rank']=index
        def compact(row):
            return {**{k:row[k]for k in('id','condition_id','source_case_id','source_run_id','configuration_sha256','source_commit','geometry_key','row_key','ranking_score')},
                'gate_values':[c['candidate']for c in row['gate_checks']],'gate_relative_violations':[c['relative_violation']for c in row['gate_checks']],
                'failed_gate_indices':[i for i,c in enumerate(row['gate_checks'])if not c['passed']],
                'condition_source':row['condition_source'],'native_summary':row['native_summary'],'baseline_geometry':row['geometry_key']==basekey}
        return dict(schema=SCHEMA,status='catalogued_unadopted',created_utc=datetime.now(timezone.utc).isoformat(),canonical_baseline=self.baseline,
            selected_layouts=selected,ranked_layouts=[dict(compact(r),layout_competitor_count=r['layout_competitor_count'],rank=i+1)for i,r in enumerate(ranked)],
            all_competitor_rows=[compact(r)for r in sorted(self.rows.values(),key=lambda r:tuple(r['ranking_score']))],aliases=self.aliases,excluded_rows=self.exclusions,
            gate_definitions=screen.GATE_DEFINITIONS,gate_names=GATE_NAMES,canonical_gate_values=self.baseline['eight_gate_values'],
            ranking_definition='Per distinct nonbaseline physical polygons/node assignment: min(max eight relative violation,sum violations,-targetP10,-targetmean,id); all actual eight skin caps must pass. Numerical arithmetic tolerances are retained.',
            baseline_layout_all_drives_excluded_from_top5=True,counts=dict(discovered_metadata_files=len(st.cache),unique_completed_compatible_conditions=len(self.rows),
                distinct_nonbaseline_layouts=len(ranked),selected_layouts=len(selected),aliases=len(self.aliases),excluded_rows=len(self.exclusions),quarantined_conflicting_conditions=len(self.conflicted_keys),**self.report_counts),
            input_sha256=st.hashes,inputs_unchanged=True,metadata_bytes_read=st.bytes_read,new_PDE=0,native_arrays_read=False,native_raw_hashes_independently_verified=False,
            candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,
            holds=['Top5 means best ranked stored distinct layouts under this fixed numerical comparison, not successful deep focus or accepted candidates',
                '2074 sampled maximum remains a directional lower bound; no new field projections, mesh/contact validation, instrument loading, activation or human safety inference',
                'Full metadata only for baseline+selected5; compact all-competitor records retain ordered eight values/violations/failures and source IDs',
                'Native grid/NPZ/contacts/density/field/potential/mask digests are declared from completed producers and require separate guarded export verification'])


def collect(root=ROOT):return CatalogBuilder(root).collect()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve();require(output.is_relative_to(ROOT/'docs')and not output.exists(),'Unique new docs JSON output required')
    started=time.monotonic();catalog=collect();catalog['wall_seconds']=time.monotonic()-started
    raw=json.dumps(catalog,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()+b'\n'
    require(len(raw)<=MAX_OUTPUT_BYTES,'Catalog exceeds preregistered2MiB compact output bound; no originals removed')
    with output.open('xb')as stream:stream.write(raw)
    print(json.dumps(dict(status=catalog['status'],output=str(output),bytes=len(raw),counts=catalog['counts'])))


if __name__=='__main__':main()
