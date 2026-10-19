"""Finite saved-basis C4 allocation/phase study; no PDE, Java or original writes.

One published execution registration covers original324 reproduction first,
then8064 grid slots. Existing controls are reused and every primary score keeps
2074 directions. Derived centre transfers are small postprocessing artifacts,
not new physical bases or extracellular potentials.
"""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from contextlib import contextmanager
import argparse
import copy
import fcntl
import hashlib
import itertools
import json
import math
import os
import shutil
import sys
import time

# This affects only a newly launched finite worker, before NumPy/BLAS import.
if '--worker' in sys.argv or '--execute' in sys.argv:
    for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[_name] = '1'
    if hasattr(os, 'sched_getaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

import numpy as np
import explore_tis as old
import mesh_validation as resources

ROOT = Path(__file__).resolve().parent
PREPARATION = ROOT/'runs/c4-phase-allocation-preparation-20261019T102803Z/preregistration.json'
PREPARATION_SHA = '4540aab933468cd7a730b0a2b3e6cf914fa760d4a69b5cd82ce458a16613d5d4'
FREQUENCIES = (3000,3005,9000,9015)
CASE_IDS = ('03739','03655','03740')
LIMITS = dict(cpu_count=1,max_RSS_bytes=3*1024**3,per_basis_wall_seconds=600,
    total_wall_seconds=6600,concurrency=1,minimum_free_disk_bytes=2*1024**3,
    new_PDE=0,new_transfer_bases=0,Java=0,compile=0,raw_cache_readonly=True)
METRICS = ('target20_modulation_V_m','target20_total_E_RMS_V_m',
    'surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2','contact_voltage_RMS_max_V',
    'max_source_current_RMS_mA','SC_power_W','contact_power_W','skin_power_W',
    'tissue_contact_power_W','source_power_W','charge_excursion_upper_mC_cm2')
LINEAR = METRICS[:6]+(METRICS[-1],)
QUADRATIC = METRICS[6:11]
CODE_NAMES = ('c4_phase_allocation.py','explore_tis.py','explore_inputs.py',
    'fit_ngg_eis.py','update_ngg_eis.py','mesh_validation.py')


def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return resources.sha256(Path(path))
def canonical(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
        separators=(',',':'),allow_nan=False).encode()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def write(path,value):
    path=Path(path)
    if path.exists(): raise FileExistsError('Preserve existing stage artifact: '+str(path))
    old.atomic(path,value)
class RequestedStop(RuntimeError):
    pass


def check_stop(output):
    for name in ('STOP','needs_attention','needs_physical_validation'):
        if (Path(output)/name).exists(): raise RequestedStop('New-run user/attention hold: '+name)
    controller=Path(output)/'controller.json'
    if controller.exists() and read(controller).get('status') in ('needs_attention','needs_physical_validation'):
        raise RequestedStop('New-run controller attention/physical hold')


def startticks(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])


def strict_match(actual,expected):
    a,b=float(actual),float(expected)
    return math.isfinite(a) and math.isfinite(b) and (a==0 if b==0 else abs(a-b)<=2e-7*abs(b))


def normalized_phases(group,phases_deg):
    group=list(group)
    if len(group)!=4 or set(group)!={0,1} or len(phases_deg)!=4:
        raise ValueError('Exactly four outputs and two nonempty actual carrier groups required')
    values=[Decimal(str(float(v))) for v in phases_deg]
    if not all(v.is_finite() for v in values): raise ValueError('Nonfinite phase')
    return [float((v-values[group.index(g)])%Decimal(360)+Decimal(360))%360
            for v,g in zip(values,group)]


def physical_key(config_sha,wave,group,phases_deg):
    if wave not in old.WAVES: raise ValueError('Unknown waveform')
    # Exact decimal wrapping, never a numerical near-equality or geometry merge.
    return canonical(dict(config_file_sha256=config_sha,waveform=wave,
        actual_transfer_frequencies_Hz=FREQUENCIES,carrier_group=list(group),
        canonical_carrier_gauge_phase_deg=normalized_phases(group,phases_deg),
        harmonic_coefficients=old.WAVES[wave],equivalence_scope='fixed_RMS_TIS_J_loss_only'))


def phase_grid():
    result=[]
    for group in itertools.product((0,1),repeat=4):
        if len(set(group))!=2: continue
        free=[i for i in range(4) if i not in (group.index(0),group.index(1))]
        for index,angles in enumerate(itertools.product(range(0,360,45),repeat=2)):
            phases=[0.]*4
            for i,angle in zip(free,angles): phases[i]=float(angle)
            result.append(dict(carrier_group=list(group),phase_deg=phases,phase_index=index,
                allocation=''.join(map(str,group)),allocation_family=f'{group.count(0)}plus{group.count(1)}'))
    return result


def coefficients(wave,group,phase_rad,amplitude=1.):
    if wave not in old.WAVES or len(group)!=4 or len(phase_rad)!=4 or set(group)!={0,1}:
        raise ValueError('Exact C4 waveform/group/phase required')
    if not math.isfinite(amplitude) or amplitude<=0 or not np.isfinite(phase_rad).all():
        raise ValueError('Finite positive amplitude and finite phases required')
    group=np.asarray(group);phase=np.asarray(phase_rad);fund,third=old.WAVES[wave]
    return {f:-1j*(group==carrier)*np.exp(1j*harmonic*phase)*factor*amplitude
            for f,carrier,harmonic,factor in ((3000,0,1,fund),(3005,1,1,fund),
                (9000,0,3,third),(9015,1,3,third))}


def targets(basis,wave,group,phase_rad,amplitude=1.):
    return {f:c@basis['f'][f]['target'] for f,c in coefficients(wave,group,phase_rad,amplitude).items()}


def score(spectra,directions=None):
    if directions is None: return old.modulation(spectra[3000],spectra[3005])
    return float(2*np.minimum(abs(directions@spectra[3000]),abs(directions@spectra[3005])).max())


def validate_basis(basis,case):
    v=basis['validation']
    for key,limit in (('max_residual',2e-7),('max_power_error',2e-7),('max_current_error',2e-6)):
        if not math.isfinite(v[key]) or not 0<=v[key]<=limit: raise ValueError('Original numerical gate: '+key)
    if v['channels']!=4 or v['cells']!=case['cells'] or v['cells']>800000 or tuple(basis['f'])!=FREQUENCIES:
        raise ValueError('Original channel/grid/frequency identity differs')
    first=basis['f'][3000]['contacts']
    for f,row in basis['f'].items():
        contacts=row['contacts'];n=len(contacts)
        if not np.array_equal(contacts,first): raise ValueError('Contact ordering/areas differ across frequencies')
        for name,shape in (('target',(4,3)),('density',(4,n)),('source',(4,4)),('loss',(6,4,4))):
            if row[name].shape!=shape or not np.isfinite(row[name]).all(): raise ValueError('Nonfinite/wrong compact shape: '+name)
        if not np.allclose(row['loss'],row['loss'].conj().transpose(0,2,1),atol=1e-12):
            raise ValueError('Original Hermitian gate failed')
        area=contacts['area_m2']
        if not np.isfinite(area).all() or np.any(area<=0) or set(contacts['pad'].astype(int))!=set(range(8)):
            raise ValueError('Original physical contact area invalid')
        expected=(case['pad_size_mm']*1e-3)**2
        if any(abs(area[contacts['pad']==p].sum()/expected-1)>1e-10 for p in range(8)):
            raise ValueError('Original physical pad-area gate failed')


def evaluate(basis,boundaries,wave,group,phase_rad,*,amplitude=1.):
    """Pure coherent complex sums, original peak factors and area-weighted J95."""
    area=basis['f'][3000]['contacts']['area_m2'];pads=basis['f'][3000]['contacts']['pad']
    losses=np.zeros(6);power=0.;j2=np.zeros(len(area));v2=np.zeros(len(area));charge=np.zeros(len(area))
    i2=np.zeros(4);metal2=np.zeros(4);spectra={};current_errors=[];power_errors=[]
    for f,c in coefficients(wave,group,phase_rad,amplitude).items():
        row=basis['f'][f];j=c@row['density'];current=row['source']@c
        spectra[f]=c@row['target'];parts=np.einsum('i,kij,j->k',c.conj(),row['loss'],c).real
        supplied=float(.25*np.vdot(c,current).real)
        difference=abs(float(parts.sum())-supplied)
        if supplied<0 or np.any(parts<0) or (difference!=0 if supplied==0 else difference>2e-7*abs(supplied)):
            raise ValueError('Passive loss/combined-source power conservation failed')
        integrated=np.array([np.sum(j[pads==p]*area[pads==p]) for p in range(8)])
        denominator=float(np.sum(abs(current)))
        error=float(np.max(abs(integrated[:4]-current)))
        if (error!=0 if denominator==0 else error>2e-7*denominator):
            raise ValueError('Integrated signal-pad/source current mismatch')
        global_error=float(abs(integrated.sum()));global_scale=float(np.sum(abs(integrated)))
        if (global_error!=0 if global_scale==0 else global_error>2e-7*global_scale):
            raise ValueError('Combined common-ground current conservation failed')
        current_errors.append(dict(frequency_Hz=f,absolute_signal_error_A=error,
            relative_signal_error=error/denominator if denominator else 0.,
            relative_all_pad_balance=global_error/global_scale if global_scale else 0.))
        power_errors.append(dict(frequency_Hz=f,relative_error=difference/abs(supplied) if supplied else 0.))
        losses+=parts;power+=supplied;i2+=abs(current)**2/2;metal2+=abs(.5*c-50*current)**2/2
        j2+=abs(j)**2/2;v2+=abs(j*boundaries[f])**2/2
        charge+=2*abs(j)/(2*np.pi*f)*.1
    rms=np.sqrt(j2);order=np.argsort(rms)
    index=min(np.searchsorted(np.cumsum(area[order]),area.sum()*.95),len(order)-1)
    return dict(target20_modulation_V_m=score(spectra),
        target20_total_E_RMS_V_m=float(np.sqrt(sum(np.vdot(e,e).real for e in spectra.values())/2)),
        surface_J_RMS_max_A_m2=float(rms.max()),surface_J_RMS_p95_A_m2=float(rms[order][index]),
        contact_voltage_RMS_max_V=float(np.sqrt(v2.max())),max_source_current_RMS_mA=float(np.sqrt(i2.max())*1000),
        SC_power_W=float(losses[0]),contact_power_W=float(losses[4]),skin_power_W=float(losses[0]+losses[4]),
        tissue_contact_power_W=float(losses[:5].sum()),source_power_W=float(power),
        charge_excursion_upper_mC_cm2=float(charge.max()),source_current_RMS_by_output_mA=(np.sqrt(i2)*1000).tolist(),
        source_load_voltage_RMS_by_output_V=np.sqrt(metal2).tolist(),
        loss_by_region_W=dict(zip(('sc','dermis','fat','muscle','contact','source50ohm'),losses.tolist())),
        current_consistency=current_errors,power_consistency=power_errors)


def selected_high_rows(rows):
    selected=set()
    for wave in old.WAVES:
        group=[r for r in rows if r['waveform']==wave]
        best=max(r['metrics_SI']['target20_modulation_V_m'] for r in group)
        selected.update(r['id'] for r in group if r['metrics_SI']['target20_modulation_V_m']>=.99*best)
        for family in ('1plus3','2plus2','3plus1'):
            part=sorted((r for r in group if r['allocation_family']==family),
                key=lambda r:(-r['metrics_SI']['target20_modulation_V_m'],r['id']))
            cutoff=part[min(1,len(part)-1)]['metrics_SI']['target20_modulation_V_m']
            selected.update(r['id'] for r in part if r['metrics_SI']['target20_modulation_V_m']>=cutoff)
    return selected


def rank_crossings(rows):
    result=[]
    for wave in old.WAVES:
        selected=[r for r in rows if r['waveform']==wave and r['direction_sensitivity']['8218'] is not None]
        for a,b in itertools.combinations(selected,2):
            before=a['metrics_SI']['target20_modulation_V_m']-b['metrics_SI']['target20_modulation_V_m']
            after=a['direction_sensitivity']['8218']-b['direction_sensitivity']['8218']
            if (before>0 and after<0) or (before<0 and after>0):
                result.append(dict(first=a['id'],second=b['id'],nominal_2074_gap_V_m=before,
                    nominal_8218_gap_V_m=after,interpretation='floating-point sampled-score ordering, not uncertainty or improvement proof'))
    return result


def _spec():
    if sha(PREPARATION)!=PREPARATION_SHA: raise ValueError('Pinned original preparation changed')
    spec=read(PREPARATION)
    if spec['resource_limits']!=LIMITS or tuple(c['case_id'] for c in spec['case_plan'])!=CASE_IDS:
        raise ValueError('Exact C4 source order/resource scope changed')
    if len(spec['original_rows'])!=324 or spec['scope']['planned_final_score_rows_total']!=8064:
        raise ValueError('Exact finite row scope changed')
    return spec


def verify_hashes(pins):
    for name,expected in pins.items():
        if sha(name)!=expected: raise ValueError('Pinned input/code bytes changed: '+name)


def prepare(output):
    output=Path(output).resolve();spec=_spec()
    if output.parent!=ROOT/'runs' or not output.name.startswith('c4-phase-allocation-') or output.exists():
        raise ValueError('Use a new c4-phase-allocation-* run under tis-java/runs')
    output.mkdir()
    for name in ('logs','reproduction','derived-target','cases'): (output/name).mkdir()
    draft=dict(schema_version=1,status='execution_draft_not_published_not_executed',created_utc=now(),
        preparation_path=str(PREPARATION),preparation_file_sha256=PREPARATION_SHA,
        user_authorization='시뮬레이션 계속 돌려봐 변수 알아서 바꿔서',
        resource_limits=LIMITS,source_cases=list(CASE_IDS),original_controls=324,grid_slots=8064,
        primary_direction_count=2074,paired_direction_count=512,high_direction_count=8218,
        high_selection_rule=spec['direction_resolution_plan']['higher_resolution_selected'],
        reuse_policy='Exact physical wrapped carrier-gauge phase key only; source frequency label swaps remain distinct. Grid slots are not new unique numerical evaluations.',
        phases='First output of each actual carrier fixed0; remaining two8×8angles0..315step45degrees.',
        stages=['Reproduce324 controls with original summarize and new pure evaluator; exact metadata and strict2e-7/exactzero.',
                'Only after all324 pass, evaluate/reuse8064 slots, paired512 and selected8218 sensitivity; report all selected pair crossings.'],
        derived_cache='Only centre complexE transfer metadata; original field read once per source. No new physical transfer basis or phi.',
        comparison_reference_policy=spec['comparison_reference_policy'],
        limits_not_predictions=True,original_workers_and_GUI_pointers_unchanged=True,
        cost=dict(raw_fullfield_bytes=369511378,all_original_controls=324,
            planned_grid_slots=8064,expected_original_lattice_reuse_slots=108,
            estimated_unique_new_fullmetric_slots=7956,
            scalar_rows_output_order_of_magnitude_bytes=8064*2500*2,
            maximum_selected_pair_crossing_records=9*(896*895//2),
            crossing_output_worst_order_of_magnitude_bytes=9*(896*895//2)*250,
            note='Byte estimates are serialization planning assumptions, not measured sizes or extra limits;2GiB reserve and600/6600seconds remain hard stop gates.',
            largest_direction_dot_products_per_case=2688*2074*2*3,
            description='Four small4×3target dot products,4×contact coherent sums and4×4circuits per new row; no candidate×fullfield array. Runtime is unmeasured; hard caps cause preserved interruption, never expansion.'),
        numeric_execution_started=False,new_PDE=0,Java=0)
    write(output/'preregistration.json',draft)
    code={str(ROOT/name):sha(ROOT/name) for name in CODE_NAMES}
    manifest=dict(schema_version=1,status='prepared',run_id=output.name,output=str(output),
        preparation_file_sha256=PREPARATION_SHA,preregistration_file_sha256=sha(output/'preregistration.json'),
        input_file_sha256=spec['input_file_sha256'],code_file_sha256=code,resource_limits=LIMITS,
        source_case_ids=list(CASE_IDS),original_controls=324,grid_slots=8064,
        worker_command=[sys.executable,'-u',str(ROOT/'c4_phase_allocation.py'),'--output',str(output),'--worker','STAGE','CASE'],
        holds=spec['holds'],physical_bare_comparison='held_missing_matching_C4_bare_basis',native_phi='held_absent')
    write(output/'manifest.json',manifest)
    (output/'README.md').write_text('# C4 유한 후처리 실행 초안\n\n입력/코드·범위를 동결한 초안이며 실제 원324 재현/새8064 슬롯 계산은0이다. '
        '원기저 새PDE·Java·컴파일0, 원GUI/worker/원자료/실패는 보존한다. '
        '정상 사전등록 게시 후 `python -u tis-java/c4_phase_allocation.py --output '+str(output)+' --execute` 한 번만 실행한다. '
        '324개 모두 통과한 뒤만 새 슬롯 단계에 진입하며, 원 격자108개 예상중복은 재현 수치와 원 ID를 재사용한다. '
        '실제 중복수/새 계산수는 별도 집계한다. 같은 기저의 두 단계 wall과 저장/감도를 합산하여600초, 전체6600초·RSS3GiB·1CPU·동시1·여유2GiB를 유지한다. '
        '실행된 state나 실패/부분 run은 재호출·재시도하지 않는다. 동일 bare·nativeφ·독립SC/XY/전체3D·생리/계측은 보류다.\n')
    return manifest


def validate_execution(output):
    output=Path(output).resolve();spec=_spec();manifest=read(output/'manifest.json')
    if output.parent!=ROOT/'runs' or not output.name.startswith('c4-phase-allocation-'):
        raise ValueError('Unexpected execution output namespace')
    if (manifest.get('output')!=str(output) or manifest.get('resource_limits')!=LIMITS
            or manifest.get('source_case_ids')!=list(CASE_IDS)
            or manifest.get('original_controls')!=324 or manifest.get('grid_slots')!=8064
            or manifest.get('input_file_sha256')!=spec['input_file_sha256']
            or manifest.get('preparation_file_sha256')!=PREPARATION_SHA):
        raise ValueError('Execution manifest differs from exact frozen scope')
    if sha(output/'preregistration.json')!=manifest['preregistration_file_sha256']:
        raise ValueError('Execution preregistration bytes changed')
    if set(manifest['code_file_sha256'])!={str(ROOT/n) for n in CODE_NAMES}:
        raise ValueError('Code hash namespace differs')
    verify_hashes(manifest['code_file_sha256'])
    publication=read(output/'execution-publication.json')
    if (publication.get('status')!='published_before_postprocessing'
            or publication.get('manifest_file_sha256')!=sha(output/'manifest.json')
            or publication.get('preregistration_file_sha256')!=manifest['preregistration_file_sha256']):
        raise ValueError('Exact preregistration must be published before any numeric stage')
    return spec,manifest


def _metadata_pins(spec):
    raw={item['path'] for case in spec['case_plan'] for item in case['raw_basis_files']}
    return {p:s for p,s in spec['input_file_sha256'].items() if p not in raw}


def _boundaries(case,profile):
    return {r['frequency_Hz']:complex(r['area_real_ohm_m2'],r['area_imag_ohm_m2'])
            for r in old.contact_rows(case['design'],profile)}


def reproduce_case(spec,case,output):
    pins={i['path']:i['sha256'] for i in case['raw_basis_files']};verify_hashes(pins)
    stored=read(case['case_path']);profile=read(spec['profile_and_evidence']['EIS_profile_file'])['50']
    if len(stored['candidates'])!=108: raise ValueError('Exactly108 source control rows required')
    basis=old.load_basis(Path(case['basis_dir']),4,FREQUENCIES);validate_basis(basis,case)
    reconstructed=old.summarize(basis,case['design'],profile,case['basis_id'],case['h_mm'],
        reference=None,seed=int(case['case_id']))
    patterns=old.drive_patterns(4,int(case['case_id']));boundaries=_boundaries(case,profile)
    original_pins=[p for p in spec['original_rows'] if p['source_case_id']==case['case_id']]
    lower_dirs=old.directions(486);checks=[];control_cache={}
    for index,(original,rebuilt,pin) in enumerate(zip(stored['candidates'],reconstructed,original_pins)):
        check_stop(output)
        if canonical(original)!=pin['original_row_canonical_sha256'] or pin['source_local_candidate_index']!=index:
            raise ValueError('Original row identity/canonical content differs')
        group,phase=patterns[index//3]
        if (rebuilt['waveform']!=original['waveform'] or rebuilt['carrier_group']!=original['carrier_group']
                or rebuilt['phase_deg']!=original['phase_deg'] or np.rad2deg(phase).tolist()!=original['phase_deg']):
            raise ValueError('Original waveform/group/phase exact reproduction failed')
        fresh=evaluate(basis,boundaries,original['waveform'],group,phase)
        for key in METRICS:
            if not strict_match(rebuilt[key],original[key]) or not strict_match(fresh[key],original[key]):
                raise ValueError('Original/new evaluator reproduction failed: '+str(index)+' '+key)
        source_id=pin['source_candidate_id'];key=physical_key(case['config_sha256'],original['waveform'],group,original['phase_deg'])
        entry=control_cache.setdefault(key,dict(original_candidate_ids=[],metrics_SI=fresh,
            paired_512_score_V_m=score(targets(basis,original['waveform'],group,phase),lower_dirs)))
        entry['original_candidate_ids'].append(source_id)
        checks.append(dict(source_candidate_id=source_id,original_row_canonical_sha256=canonical(original),
            status='passed',metrics_checked=list(METRICS),old_function_and_new_evaluator_passed=True))
    if len(checks)!=108 or len(reconstructed)!=108: raise ValueError('Original108 coverage incomplete')
    compact=dict(case_id=case['case_id'],config_file_sha256=case['config_sha256'],
        original_raw_file_sha256=pins,physical_transfer_basis_created=False,
        cache_kind='derived_centre_complexE_metadata_not_phi',
        target={str(f):np.stack((row['target'].real,row['target'].imag),axis=-1).tolist()
                for f,row in basis['f'].items()})
    verify_hashes(pins);verify_hashes(_metadata_pins(spec))
    target_path=output/'derived-target'/(case['case_id']+'.json');write(target_path,compact)
    receipt=dict(status='passed',case_id=case['case_id'],original_rows=108,checks=checks,
        control_cache=control_cache,derived_target_path=str(target_path),derived_target_file_sha256=sha(target_path),
        original_input_file_sha256=pins,new_physical_basis_count=0,new_PDE=0)
    write(output/'reproduction'/(case['case_id']+'.json'),receipt)
    return receipt


def require_all_controls(output,require_pin=False):
    gate=output/'all-controls-verification.json'
    if require_pin and not gate.is_file(): raise ValueError('Pinned all324 verification receipt required')
    if gate.is_file():
        proof=read(gate)
        if proof.get('status')!='passed' or proof.get('original_rows')!=324:
            raise ValueError('All324 verification receipt failed')
        for ident in CASE_IDS:
            if sha(output/'reproduction'/(ident+'.json'))!=proof['per_case_receipt_file_sha256'].get(ident):
                raise ValueError('Pinned reproduction receipt changed: '+ident)
    records=[read(output/'reproduction'/(ident+'.json')) for ident in CASE_IDS]
    if any(r.get('status')!='passed' or r.get('original_rows')!=108 or len(r.get('checks',[]))!=108
            or any(c.get('status')!='passed' for c in r['checks']) for r in records):
        raise ValueError('All324 original controls must pass before any grid slot')
    return records


def _compact_basis(case,receipt):
    target_path=Path(receipt['derived_target_path'])
    if sha(target_path)!=receipt['derived_target_file_sha256']: raise ValueError('Derived target cache changed')
    compact=read(target_path)
    if compact.get('case_id')!=case['case_id'] or compact.get('config_file_sha256')!=case['config_sha256']:
        raise ValueError('Derived target cache namespace differs')
    pins={i['path']:i['sha256'] for i in case['raw_basis_files']
            if not Path(i['path']).name.startswith('field-') and Path(i['path']).name!='grid.csv'}
    verify_hashes(pins);folder=Path(case['basis_dir']);basis={'validation':read(folder/'validation.json'),'f':{}}
    for f in FREQUENCIES:
        target=np.asarray(compact['target'][str(f)],float)
        basis['f'][f]=dict(target=target[...,0]+1j*target[...,1],
            contacts=np.genfromtxt(folder/f'contacts-{f}.csv',delimiter=',',names=True),
            density=np.fromfile(folder/f'density-{f}.bin',dtype='<c16').reshape(4,-1),
            source=np.fromfile(folder/f'source-{f}.bin',dtype='<c16').reshape(4,4),
            loss=np.fromfile(folder/f'loss-{f}.bin',dtype='<c16').reshape(6,4,4))
    validate_basis(basis,case)
    return basis,pins


def analyze_case(spec,case,output):
    receipts=require_all_controls(output,require_pin=True)
    receipt=next(r for r in receipts if r['case_id']==case['case_id'])
    raw_pins={i['path']:i['sha256'] for i in case['raw_basis_files']};verify_hashes(raw_pins)
    basis,pins=_compact_basis(case,receipt)
    profile=read(spec['profile_and_evidence']['EIS_profile_file'])['50'];boundaries=_boundaries(case,profile)
    lower_dirs=old.directions(486);higher_dirs=old.directions(8192);rows=[];by_key={}
    partial=output/'cases'/(case['case_id']+'.partial.jsonl')
    with partial.open('x') as stream:
        for plan in phase_grid():
            check_stop(output)
            for wave in old.WAVES:
                key=physical_key(case['config_sha256'],wave,plan['carrier_group'],plan['phase_deg'])
                old_control=receipt['control_cache'].get(key)
                phase=np.deg2rad(plan['phase_deg'])
                if old_control:
                    metric=copy.deepcopy(old_control['metrics_SI']);paired=old_control['paired_512_score_V_m']
                else:
                    metric=evaluate(basis,boundaries,wave,plan['carrier_group'],phase)
                    paired=score(targets(basis,wave,plan['carrier_group'],phase),lower_dirs)
                row=dict(id=case['case_id']+'-g'+plan['allocation']+'-p'+str(plan['phase_index']).zfill(2)+'-'+wave,
                    source_run=Path(spec['source_run']).name,source_condition_id=case['case_id'],
                    source_case_file_sha256=case['case_sha256'],config_file_sha256=case['config_sha256'],
                    original_producer_source_file_sha256=spec['producer_solver_source_hashes'],
                    original_basis_id=case['basis_id'],waveform=wave,**plan,
                    metrics_SI=metric,source_Vpp_each_output=1,source_resistance_ohm=50,
                    carrier_frequencies_Hz=[3000,3005],transfer_frequencies_Hz=list(FREQUENCIES),
                    physical_electrical_key=key,primary_direction_count=2074,
                    numeric_origin='reused_reproduced_original' if old_control else 'new_saved_basis_postprocessing',
                    reused_original_candidate_ids=old_control['original_candidate_ids'] if old_control else [],
                    direction_sensitivity={'512':paired,'8218':None},
                    same_bare_burden_comparison='held_missing_matching_C4_bare_basis',native_phi='held_absent',
                    independent_SC_XY_full3D_contact_physiology='held')
                if key in by_key: raise ValueError('Unexpected duplicate new grid slot')
                rows.append(row);by_key[key]=row
                stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
                if len(rows)%128==0:
                    stream.flush();old.atomic(output/'cases'/(case['case_id']+'-checkpoint.json'),
                        dict(status='partial',slots_computed=len(rows),expected_slots=2688,new_PDE=0))
    if len(rows)!=2688: raise ValueError('Exact2688 slots per case required')
    selected=selected_high_rows(rows)
    for row in rows:
        check_stop(output)
        if row['id'] in selected:
            row['direction_sensitivity']['8218']=score(targets(basis,row['waveform'],row['carrier_group'],
                np.deg2rad(row['phase_deg'])),higher_dirs)
        if row['allocation_family']!='2plus2':
            references=[]
            for group in itertools.product((0,1),repeat=4):
                if group.count(0)!=2: continue
                other=physical_key(case['config_sha256'],row['waveform'],group,row['phase_deg'])
                references.append(by_key[other]['id'])
            row['same_absolute_phase_2plus2_control_ids']=references
    verify_hashes(raw_pins);verify_hashes(_metadata_pins(spec))
    result=dict(status='complete',case_id=case['case_id'],grid_slots=2688,
        reused_original_grid_slots=sum(r['numeric_origin']=='reused_reproduced_original' for r in rows),
        unique_new_fullmetric_slots=sum(r['numeric_origin']=='new_saved_basis_postprocessing' for r in rows),
        high_direction_selected_rows=len(selected),rank_crossings=rank_crossings(rows),
        original_324_gate='passed',rows=rows,new_PDE=0,new_physical_transfer_bases=0,
        native_phi='held_absent',same_bare_burden='held_missing_matching_C4_bare_basis')
    check_stop(output)
    result_path=output/'cases'/(case['case_id']+'.json')
    write(result_path,result)
    write(output/'cases'/(case['case_id']+'-receipt.json'),
        dict({k:v for k,v in result.items() if k not in ('rows','rank_crossings')},
             rank_crossing_count=len(result['rank_crossings']),
             result_path=str(result_path),result_file_sha256=sha(result_path)))
    old.atomic(output/'cases'/(case['case_id']+'-checkpoint.json'),
        dict(status='complete',slots_computed=2688,expected_slots=2688,new_PDE=0))
    return result


@contextmanager
def execution_lock(output):
    with resources.diagnostic_lock():
        with (output/'.controller.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            yield


def parent_command_matches(argv,cwd,output):
    cwd=Path(cwd)
    script_ok=any((Path(a) if Path(a).is_absolute() else cwd/a).resolve()
        ==(ROOT/'c4_phase_allocation.py').resolve() for a in argv[1:] if not a.startswith('-'))
    try:
        target=Path(argv[argv.index('--output')+1])
    except (ValueError,IndexError): return False
    target=target if target.is_absolute() else cwd/target
    return script_ok and '--execute' in argv and '--worker' not in argv and target.resolve()==Path(output).resolve()


def _worker_impl(output,stage,ident):
    check_stop(output)
    spec,manifest=validate_execution(output);state=read(output/'controller.json')
    parent=state['pid']
    if (state.get('status')!='running' or state.get('stage')!=stage or state.get('current_case')!=ident
            or startticks(parent)!=state['proc_start_ticks'] or os.getppid()!=parent):
        raise ValueError('Worker lacks the exact live finite-controller identity')
    argv=[p.decode() for p in Path(f'/proc/{parent}/cmdline').read_bytes().split(b'\0') if p]
    parent_cwd=Path(f'/proc/{parent}/cwd').resolve()
    if not parent_command_matches(argv,parent_cwd,output):
        raise ValueError('Unexpected parent command; direct workers are forbidden')
    if stage=='analyze':
        gate=output/'all-controls-verification.json'
        if not gate.is_file() or sha(gate)!=state.get('controls_verification_file_sha256'):
            raise ValueError('Parent-pinned324 verification changed')
    with (output/'.controller.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:pass
        else:raise ValueError('Finite-controller lock is not held')
    case=next(c for c in spec['case_plan'] if c['case_id']==ident)
    verify_hashes(_metadata_pins(spec))
    write(output/'logs'/(stage+'-'+ident+'-process.json'),dict(pid=os.getpid(),
        proc_start_ticks=startticks(os.getpid()),command=sys.argv,cpu_affinity=sorted(os.sched_getaffinity(0)),
        kind='finite_saved_data_Python_worker',new_PDE=0,Java=0))
    try:
        if stage=='reproduce':reproduce_case(spec,case,output)
        elif stage=='analyze':analyze_case(spec,case,output)
        else:raise ValueError('Unknown finite stage')
    except RequestedStop as error:
        write(output/'logs'/(stage+'-'+ident+'-requested-stop.json'),dict(status='user_stopped',reason=str(error),observed_utc=now()))
        raise
    verify_hashes(manifest['code_file_sha256'])


def worker(output,stage,ident):
    try:
        return _worker_impl(output,stage,ident)
    except RequestedStop as error:
        path=output/'logs'/(stage+'-'+ident+'-requested-stop.json')
        if not path.exists():write(path,dict(status='user_stopped',reason=str(error),observed_utc=now()))
        raise


def execute(output):
    output=Path(output).resolve();spec,manifest=validate_execution(output)
    check_stop(output)
    with execution_lock(output):
        if (output/'controller.json').exists() or (output/'completion.json').exists():
            raise ValueError('Previously started/partial/failed/complete execution is preserved; no retry')
        started=time.monotonic();deadline=started+6600;elapsed={ident:0. for ident in CASE_IDS}
        state=dict(status='running',pid=os.getpid(),proc_start_ticks=startticks(os.getpid()),
            command=sys.argv,started_utc=now(),stage=None,current_case=None,case_elapsed_seconds=elapsed,
            stage_resources=[],reproduction_file_sha256={},original_controls_passed=0,new_grid_slots_complete=0,new_PDE=0,Java=0)
        old.atomic(output/'controller.json',state)
        try:
            for stage in ('reproduce','analyze'):
                if stage=='analyze':
                    controls=require_all_controls(output)
                    if any(sha(output/'reproduction'/(ident+'.json'))!=state['reproduction_file_sha256'].get(ident) for ident in CASE_IDS):
                        raise ValueError('Completed baseline receipt changed before all324 gate')
                    write(output/'all-controls-verification.json',dict(status='passed',original_rows=324,
                        per_case_receipt_file_sha256={r['case_id']:sha(output/'reproduction'/(r['case_id']+'.json')) for r in controls}))
                    state['controls_verification_file_sha256']=sha(output/'all-controls-verification.json')
                    state['original_controls_passed']=324
                for case in spec['case_plan']:
                    check_stop(output)
                    ident=case['case_id'];budget=600-elapsed[ident]
                    if budget<=0 or time.monotonic()>=deadline: raise RuntimeError('Registered cumulative wall budget exhausted')
                    if shutil.disk_usage(output).free<2*1024**3: raise RuntimeError('Registered2GiB disk reserve exhausted')
                    state.update(stage=stage,current_case=ident,updated_utc=now());old.atomic(output/'controller.json',state)
                    command=[sys.executable,'-u',str(ROOT/'c4_phase_allocation.py'),'--output',str(output),'--worker',stage,ident]
                    try:
                        report=resources.run_guarded(command,output/'logs'/(stage+'-'+ident+'.log'),
                            timeout_s=budget,rss_limit_bytes=3*1024**3,total_deadline=deadline)
                    except resources.ValidationStop as error:
                        elapsed[ident]+=error.resources.get('wall_seconds',0)
                        state['stage_resources'].append(dict(case_id=ident,stage=stage,**error.resources))
                        if (output/'logs'/(stage+'-'+ident+'-requested-stop.json')).is_file():
                            raise RequestedStop('Worker preserved a requested new-run stop') from error
                        raise
                    elapsed[ident]+=report['wall_seconds']
                    check_stop(output)
                    if elapsed[ident]>600: raise RuntimeError('Cumulative basis600second cap exceeded')
                    state['stage_resources'].append(dict(case_id=ident,stage=stage,**report))
                    if stage=='reproduce':state['reproduction_file_sha256'][ident]=sha(output/'reproduction'/(ident+'.json'))
                    if stage=='analyze':state['new_grid_slots_complete']+=2688
                    old.atomic(output/'controller.json',state)
                    if resources.process_rss_bytes(os.getpid())>3*1024**3:raise RuntimeError('Controller RSS cap exceeded')
            check_stop(output)
            verify_hashes(spec['input_file_sha256']);verify_hashes(manifest['code_file_sha256'])
            completed=[read(output/'cases'/(ident+'-receipt.json')) for ident in CASE_IDS]
            for case in completed:
                if sha(case['result_path'])!=case['result_file_sha256']:
                    raise ValueError('Completed case body differs from its small receipt')
            if sum(c['grid_slots'] for c in completed)!=8064: raise ValueError('Final8064 coverage incomplete')
            if resources.process_rss_bytes(os.getpid())>3*1024**3:raise RuntimeError('Controller RSS cap exceeded')
            total=time.monotonic()-started
            if total>6600:raise RuntimeError('Whole-run6600second cap exceeded')
            summary=dict(status='complete',finished_utc=now(),original_controls_reproduced=324,
                grid_slots=8064,reused_original_grid_slots=sum(c['reused_original_grid_slots'] for c in completed),
                unique_new_fullmetric_slots=sum(c['unique_new_fullmetric_slots'] for c in completed),
                case_elapsed_seconds=elapsed,total_wall_seconds=total,stage_resources=state['stage_resources'],
                output_file_sha256={str(p.relative_to(output)):sha(p) for folder in ('cases','derived-target','reproduction') for p in (output/folder).iterdir() if p.is_file()},
                input_code_unchanged=True,new_PDE=0,new_physical_transfer_bases=0,Java=0,
                original_physical_hold_preserved=True,holds=spec['holds'])
            check_stop(output)
            write(output/'completion.json',summary)
            state.update(status='complete',stage='finished',current_case=None,finished_utc=now())
            old.atomic(output/'controller.json',state)
            return summary
        except BaseException as error:
            state.update(status='user_stopped' if isinstance(error,RequestedStop) else 'interrupted' if isinstance(error,(KeyboardInterrupt,SystemExit)) else 'failed',
                error_type=type(error).__name__,error=str(error),finished_utc=now(),
                total_wall_seconds=time.monotonic()-started,failed_partial_outputs_preserved=True)
            old.atomic(output/'controller.json',state)
            write(output/'failure.json',state)
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--execute',action='store_true')
    mode.add_argument('--worker',nargs=2,metavar=('STAGE','CASE'))
    args=parser.parse_args()
    if args.prepare:answer=prepare(args.output)
    elif args.execute:answer=execute(args.output)
    else:answer=worker(args.output.resolve(),*args.worker)
    print(json.dumps(answer,ensure_ascii=False,allow_nan=False))
