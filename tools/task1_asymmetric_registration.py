"""One fixed900mm2 mixed source/return allocation; no work on import.

This is a combined shape/area-allocation contrast, not an isolated area effect.
The standalone CLI only prepares under both global locks and freezes sources
once. It never executes a PDE; the existing cloud controller owns that step.
"""
from __future__ import annotations

import copy
import csv
import math
import os
from pathlib import Path
import shutil
import subprocess
import time

import task1_cloud_batch as core
import task1_cross_registration as cross
import task1_contact_sensitivity_registration as contact
from task1_grouped_registration import _caller_owns_execution_lock,_mesh
from task1_reference_registration import _changed_config,_properties

CASE_ID='asym-cross281p25-return168p75-xy80'
EXPECTED_CELLS=351680
EXPECTED_RAW_BOUND_BYTES=211008000
MIN_REMAINING_SECONDS=1020
SOURCE_RUN='cloud-cross-20261021T043000Z'
SOURCE_ID='cross17p5-arm12p5-xy80'
VOLUME=core.REPO/'docs/cloud-continuation-20261021/volume-cross.json'
DRIVE=core.REPO/'docs/cloud-continuation-20261021/drive-ratio-20261021T050400Z/summary.json'


def mixed_design(source_design):
    cross.aligned_cross_mask(source_design)
    core.require(all(p['arm_width_mm']==12.5 for p in source_design['pads']), 'Completed281.25mm2 cross prototype required')
    design=copy.deepcopy(source_design)
    for p in design['pads'][2:]:
        x,y=p['center_mm']
        for key in ('outer_length_mm','arm_width_mm','union_rectangles_mm'):p.pop(key,None)
        p.update(shape='rectangle',width_mm=15.,height_mm=11.25,area_mm2=168.75,
            analytic_area_mm2=168.75,polygon_area_mm2=168.75,
            polygon_mm=[[x-7.5,y-5.625],[x+7.5,y-5.625],[x+7.5,y+5.625],[x-7.5,y+5.625]],
            geometry_primitive='axis_aligned_rectangle')
    design.update(id=CASE_ID.removesuffix('-xy80'),group='fixed_total_area_asymmetric_shape_allocation',
        physical_total_contact_area_mm2=900.,minimum_gap_mm=3.75,
        area_change_vs_four_square225_percent=0.,
        area_policy='Combined shape and source/return area allocation at fixed900mm2; not a single-factor area effect',
        geometry_revision='exact-aligned-source-cross281p25-return-rectangle168p75-v1')
    return design


def aligned_mixed_mask(design):
    core.require(design['id']==CASE_ID.removesuffix('-xy80') and design['total_pads']==4 and
        design['source_outputs']==2 and len(design['pads'])==4 and design['phantom_diameter_mm']==50 and
        design['contact_plane_z_mm']==0 and design['return_connection']=='all_return_pads_ideal_common_GND',
        'Fixed top D50/four-pad/two-output common-GND allocation required')
    rows=[];covered=set();h=.625;face=(h/1000)**2
    for index,(p,(x,y)) in enumerate(zip(design['pads'],cross.CENTRES_MM)):
        core.require(p['pad']==index and tuple(p['center_mm'])==(x,y) and p['rotation_deg']==0 and
            p['corner_radius_mm']==0 and p['role']==('signal' if index<2 else 'common_gnd_return') and
            p['source_output']==(index if index<2 else None), 'Position/rotation/wiring differs')
        if index<2:
            core.require(p['shape']=='cross' and p['outer_length_mm']==17.5 and p['arm_width_mm']==12.5 and
                p['width_mm']==p['height_mm']==17.5 and p['analytic_area_mm2']==p['area_mm2']==281.25,
                'Source pads must remain281.25mm2 crosses')
        else:
            core.require(p['shape']=='rectangle' and p['width_mm']==15 and p['height_mm']==11.25 and
                p['analytic_area_mm2']==p['area_mm2']==168.75, 'Return pads must be15X by11.25Y rectangles')
        for j in range(80):
            for i in range(80):
                px,py=-25+(i+.5)*h,-25+(j+.5)*h
                active=(abs(px-x)<8.75 and abs(py-y)<6.25 or abs(px-x)<6.25 and abs(py-y)<8.75) if index<2 \
                    else abs(px-x)<7.5 and abs(py-y)<5.625
                if not active:continue
                core.require((i,j) not in covered and all((-25+ii*h)**2+(-25+jj*h)**2<625
                    for ii in (i,i+1) for jj in (j,j+1)), 'Mixed contact overlap/outside D50')
                covered.add((i,j));rows.append((index,i,j,face))
    counts=[sum(p==pad for p,_,_,_ in rows) for pad in range(4)]
    areas=[math.fsum(a for p,_,_,a in rows if p==pad) for pad in range(4)]
    core.require(counts==[720,720,432,432] and len(rows)==2304 and
        all(abs(a/(expected*1e-6)-1)<=1e-10 for a,expected in zip(areas,(281.25,281.25,168.75,168.75))),
        'Fixed full-face counts/physical area differs')
    return rows,areas,dict(rule='exact-aligned-mixed-cross-rectangle-full-faces-v1',h_xy_mm=h,
        faces_per_pad=counts,contacts=len(rows),represented_pad_areas_m2=areas,full_face_area_m2=face,
        physical_total_contact_area_mm2=900.,partial_faces=0,discarded_slivers=0,renormalization=False,
        question='Combined shape/area allocation at fixed900mm2; not an isolated area effect',
        geometry_convergence_claimed=False)


def changed_mask_config(data,path,sha,areas):
    core.require(len(areas)==4 and all(abs(a/(v*1e-6)-1)<1e-10
        for a,v in zip(areas,(281.25,281.25,168.75,168.75))), 'Exact four asymmetric physical areas required')
    changes={'mask.path':str(path),'mask.sha256':sha}
    changes.update({f'pad.{p}.represented_area_m2':format(a,'.17g') for p,a in enumerate(areas)})
    for p in (2,3):
        changes.update({f'pad.{p}.shape':'rectangle',f'pad.{p}.width_mm':'15',
            f'pad.{p}.height_mm':'11.25',f'pad.{p}.analytic_area_mm2':'168.75'})
    output=_changed_config(data,changes);removed={f'pad.{p}.arm_width_mm' for p in (2,3)}
    before=_properties(output);core.require(removed<=set(before), 'Cross prototype metadata missing')
    output=b''.join(line for line in output.splitlines(keepends=True)
                   if line.split(b'=',1)[0].decode() not in removed)
    changes.update({key:None for key in removed});after=_properties(output);original=_properties(data)
    core.require(set(after)==set(original)-removed and
        all(after[k]==v for k,v in original.items() if k not in changes), 'Unregistered physical/electrical config mutation')
    return output,changes


def prepare_asymmetric(run):
    started=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run==run.resolve() and not run.exists(), 'New unique canonical asymmetric run required')
    _caller_owns_execution_lock();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    budget_path=core.REPO/'runtime/task1-budget.json';budget=core.read(budget_path)
    core.require(budget['limit_seconds']==6600 and 6600-budget['spent_seconds']>=MIN_REMAINING_SECONDS,
        'Need120s prep+600s condition+180s validation+120s UI within original6600s')
    integrity=core.original_integrity();volume,drive=core.read(VOLUME),core.read(DRIVE)
    core.require(volume['status']==drive['status']=='calculated_unadopted' and
        volume['inputs_unchanged'] is True and drive['inputs_unchanged'] is True and drive['new_PDE']==0 and
        drive['new_conditions']==2 and drive['adopted'] is False, 'Completed uniform-cross/drive decisions required')
    source,old_config,old_mask,source_pins=contact._source_case(core,SOURCE_RUN,SOURCE_ID,volume)
    baseline,base_config,base_mask,base_pins=contact._source_case(core,'cloud-mesh-c1-20261019T190000Z',
        'baseline-square15-xy80',volume)
    core.require(source['source_Rs_fit_window_Hz']==500 and source['source_coating_nm']==10,
                 'Only nominal10nm Rs500 cross prototype allowed')
    core.require({k:v for k,v in _properties(old_config.read_bytes()).items() if k.startswith('z.') or
        k.endswith(('.sigma','.epsilon_r'))}=={k:v for k,v in _properties(base_config.read_bytes()).items()
        if k.startswith('z.') or k.endswith(('.sigma','.epsilon_r'))}, 'Nominal contact/tissue models differ')
    design=mixed_design(source['design']);rows,areas,receipt=aligned_mixed_mask(design)
    core.require(EXPECTED_RAW_BOUND_BYTES==EXPECTED_CELLS*600 and
        shutil.disk_usage(run.parent).free>2*core.GIB+EXPECTED_RAW_BOUND_BYTES, 'Raw output plus2GiB reserve unavailable')
    pins=core.source_pins();test=core.REPO/'tests/test_task1_asymmetric_registration.py'
    for p in (Path(__file__).resolve(),test,Path(cross.__file__).resolve(),Path(contact.__file__).resolve(),VOLUME,DRIVE):pins[str(p)]=core.sha(p)
    pins.update(source_pins);pins.update(base_pins)
    pins[drive['preregistration']['path']]=drive['preregistration']['SHA256']
    for condition in drive['conditions']:
        for artifact in condition['artifacts'].values():pins[artifact['path']]=artifact['SHA256']
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=core.REPO,text=True).strip()
    for name,expected in pins.items():
        p=Path(name);core.require(core.sha(p)==expected,'Pinned source/decision changed: '+name)
        if p.suffix in ('.py','.java'):
            core.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(core.REPO))],cwd=core.REPO)==p.read_bytes(),
                         'All consumed implementation sources/tests must be committed before preparation: '+name)
    jdk=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
    javac=shutil.which('javac') or str(jdk/'javac');java=str(Path(javac).resolve().parent/'java')
    core.require(Path(java).is_file() and Path(javac).is_file(), 'Matching installed Java compiler/runtime required')
    run.mkdir();succeeded=False;registration=None
    try:
        for d in ('configs','masks','bases','cases','postprocess','logs','classes','geometry-audit'):(run/d).mkdir()
        mask=run/'masks'/(CASE_ID+'.csv')
        with mask.open('x',newline='') as stream:
            writer=csv.writer(stream,lineterminator='\n');writer.writerow(['pad','i','j','area_m2'])
            for p,i,j,a in rows:writer.writerow([p,i,j,format(a,'.17g')])
        config=run/'configs'/(CASE_ID+'.properties')
        data,changes=changed_mask_config(old_config.read_bytes(),mask,core.sha(mask),areas);config.write_bytes(data)
        core.write(run/'geometry-audit/mixed-design.json',design);core.write(run/'geometry-audit/mask-receipt.json',receipt)
        case=copy.deepcopy(source)
        case.update(id=CASE_ID,design_id=design['id'],design=design,source_run_id=run.name,
            config_file=str(config),config_sha256=core.sha(config),mask_file=str(mask),mask_sha256=core.sha(mask),
            expected_pad_areas_m2=areas,physical_total_contact_area_mm2=900.,area_change_vs_baseline_percent=0.,
            contact_area_policy=design['area_policy'],status='preregistered_not_executed',candidate_adopted=False,
            prototype_reference=dict(run_id=SOURCE_RUN,case_id=SOURCE_ID,config_file=str(old_config),config_sha256=core.sha(old_config)),
            combined_geometry_and_area_allocation=True,isolated_area_effect_claimed=False,
            mesh_convergence_validated=False,existing_XY_contact_model_holds_preserved=True)
        case.update(_mesh(case));core.require(case['cells']==EXPECTED_CELLS,'Asymmetric cell count changed')
        case['cache_signature']=core.check_cached_operator(case,run)
        def allowance():
            elapsed=time.monotonic()-started
            return min(120-elapsed,6600-budget['spent_seconds']-elapsed-900)
        def command(args,log):
            remaining=allowance();core.require(remaining>0 and shutil.disk_usage(run).free>=2*core.GIB,'Preparation/reserve exhausted')
            core.write(run/'controller.json',dict(status='preparing',phase='asymmetric_compile_selftest',command=args,
                pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now()))
            subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=remaining)
        with (run/'logs/compile-selftest.log').open('x') as log:
            command([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'),str(core.SOURCE/'ExploreBasis.java'),str(core.SOURCE/'SelectivityShapeBasis.java'),
                str(core.REPO/'tools/java/CloudShapeBasis.java')],log)
            command([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),
                'CloudShapeBasis','--selftest'],log)
        for p in [*(run/'configs').glob('*'),*(run/'masks').glob('*'),*(run/'classes').glob('*'),*(run/'geometry-audit').glob('*')]:pins[str(p)]=core.sha(p)
        for p,expected in pins.items():core.require(core.sha(p)==expected,'Pinned asymmetric input changed: '+p)
        core.require(allowance()>0,'120s preparation allowance exhausted')
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='one_fixed_total900_asymmetric_geometry',status='prepared',
            created_utc=core.now(),source_commit=commit,package_integrity=integrity,limits=copy.deepcopy(core.LIMITS),
            gates=copy.deepcopy(core.GATES),cases=[case],java=java,new_PDE_conditions_maximum=1,
            expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,source_and_input_sha256=pins,preparation_seconds=time.monotonic()-started,
            path_mapping=[dict(original_config=str(old_config),original_sha256=core.sha(old_config),new_config=str(config),
                new_sha256=core.sha(config),changed_fields=list(changes),
                geometry_metadata_changed_fields=[k for k in changes if k not in ('mask.path','mask.sha256') and not k.endswith('represented_area_m2')],
                electrical_physics_grid_changed_fields=[],geometry_is_explicit_mask=True)],
            scientific_question='At same900mm2 total, does larger source-cross/smaller rectangle-return allocation retain absolute ROI under skin caps?',
            combined_shape_area_allocation=True,isolated_area_effect_claimed=False,
            decision_sources=dict(uniform_cross_volume=dict(path=str(VOLUME),SHA256=core.sha(VOLUME)),
                drive_ratio=dict(path=str(DRIVE),SHA256=core.sha(DRIVE))),
            planned_normalizations=['raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin'],
            comparison_waveforms=['square_3h','sine','triangle_3h'],
            fixed_ROIs='Primary r<=5mm depth15to20; supplementalwholeXYsame-depth; surface0to5 and bothcomplements',
            root_validation_reserve_seconds=180,root_UI_reserve_seconds=120,candidate_adopted=False,
            mesh_convergence_validated=False,experimental_validation=False,existing_XY_contact_model_holds_preserved=True,
            contact_uncertainty='Frozen nominalPBSRs500 specificZ; noRs re-subtraction or doublearea; actualskinvalidation held',
            frozen_source_snapshot_owner='standalone CLI calls core.freeze_sources once under dual global lock',
            storage=dict(native_location=str(run),persistent_backup_verified=False,retirement_of_old_environment_allowed=False),
            next_decision='Actual5normalizations basicROImean/P10+wholeXY+burdens; no adoption or secondPDE in this registration')
        core.write(run/'preregistration.json',registration);core.write(run/'controller.json',dict(status='prepared',updated_utc=core.now()));succeeded=True
    except BaseException as error:
        core.write(run/'preparation-failure.json',dict(status='preparation_failed_preserved',error_type=type(error).__name__,
            error=str(error),observed_utc=core.now(),partial_evidence_preserved=True,automatic_retry=False));raise
    finally:
        elapsed=time.monotonic()-started;budget['spent_seconds']+=elapsed
        budget['runs'].append(dict(run_id=run.name,stage='preparation',seconds=elapsed,status='prepared' if succeeded else 'preparation_failed_preserved'))
        core.write(budget_path,budget)
    return registration


def main():
    import argparse
    import fcntl
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with (core.REPO/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=prepare_asymmetric(args.output);core.freeze_sources(args.output.resolve())
    print(dict(status=result['status'],run=str(args.output),case_id=CASE_ID))


if __name__=='__main__':main()
