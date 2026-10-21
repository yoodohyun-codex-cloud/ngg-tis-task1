"""One fixed small-square XY-only convergence diagnostic; no work on import.

No original four-pad normalization reference is eligible at XY120: the historical
Best1 matrix reproduction remains held. This registration never adopts a
candidate or clears earlier XY/contact-edge failures merely because a new pair
passes. The root owns the global lock, source freezing and actual execution.
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
from task1_grouped_registration import _caller_owns_execution_lock, _mesh
from task1_reference_registration import _changed_config, _properties
from task1_candidate_coupled_registration import (
    DESIGN_ID, TEMPLATE_ID, GATE_PERCENT, _comparison_values,
    _completed_same_candidate_xy, validate_candidate_template)

CASE_ID = DESIGN_ID+'-xy120'
H_MM = 50/120
EXPECTED_CELLS = 791280
EXPECTED_RAW_BOUND_BYTES = 474768000
HISTORY_ID = DESIGN_ID+'-xy80'


def aligned_full_face_mask(design):
    """Construct integer-aligned10mm squares directly; no clipping or slivers."""
    expected_centres = [(-12.5,-12.5),(12.5,12.5),(12.5,-12.5),(-12.5,12.5)]
    ranges = [(18,42,18,42),(78,102,78,102),(78,102,18,42),(18,42,78,102)]
    pads = design['pads']
    core.require(design['id'] == DESIGN_ID and len(pads) == 4 and
                 design['source_outputs'] == 2 and design['total_pads'] == 4,
                 'Exact four-pad/two-output small-square design required')
    face, rows = (H_MM/1000)**2, []
    for index, (pad, centre, bounds) in enumerate(zip(pads, expected_centres, ranges)):
        core.require(pad['pad'] == index and pad['shape'] == 'rectangle' and
                     tuple(pad['center_mm']) == centre and pad['width_mm'] == pad['height_mm'] == 10 and
                     pad['rotation_deg'] == 0 and pad['corner_radius_mm'] == 0 and
                     pad['analytic_area_mm2'] == 100 and
                     pad['role'] == ('signal' if index < 2 else 'common_gnd_return') and
                     pad['source_output'] == (index if index < 2 else None),
                     'Small-square position/size/rotation/wiring must remain frozen')
        xlo,xhi,ylo,yhi = bounds
        for edge, position in ((xlo,centre[0]-5),(xhi,centre[0]+5),
                               (ylo,centre[1]-5),(yhi,centre[1]+5)):
            core.require(abs(-25+edge*H_MM-position) <= 1e-12,
                         'Physical square boundary does not align with an integer grid edge')
        for j in range(ylo,yhi):
            for i in range(xlo,xhi):
                x,y = -25+(i+.5)*H_MM, -25+(j+.5)*H_MM
                core.require(x*x+y*y < 625, 'Aligned contact outside native D50 cylinder')
                rows.append((index,i,j,face))
    core.require(len(rows) == 2304 and len({(i,j) for _,i,j,_ in rows}) == 2304,
                 'Expected2304 nonoverlapping full contact faces')
    areas = [math.fsum(area for pad,_,_,area in rows if pad == p) for p in range(4)]
    core.require(all(abs(area/(100e-6)-1) <= 1e-10 for area in areas), 'Every physical pad must preserve100mm2')
    receipt = dict(rule='exact-integer-grid-edges-small-square10-v1', h_xy_mm=H_MM,
        grid_edge_indices=[18,42,78,102], pad_index_ranges=ranges, contacts=2304,
        faces_per_pad=576, physical_analytic_area_mm2_each=100,
        full_face_area_m2=face, represented_pad_areas_m2=areas,
        discarded_slivers=0, snapped_partial_faces=0, renormalization=False,
        scope='Exact aligned contact construction only; no convergence/adoption claim')
    return rows, areas, receipt


def changed_xy_config(data, mask_path, mask_sha256):
    """Only XY, native mask reference/hash and explicit per-pad area may change."""
    changes = {'h_mm':repr(H_MM), 'mask.path':str(mask_path), 'mask.sha256':mask_sha256}
    for pad in range(4):
        changes[f'pad.{pad}.represented_area_m2'] = format(100*1e-6,'.17g')
    return _changed_config(data,changes), changes


def _history_reference():
    """Pin the preceding XY80 cache so its failed XY step remains visible."""
    matches=[]
    for path in (core.REPO/'data-native').glob('cloud-*/preregistration.json'):
        pre=core.read(path)
        for case in pre.get('cases',[]):
            if case.get('id') != HISTORY_ID:
                continue
            record_path=path.parent/'cases'/(HISTORY_ID+'.json')
            if not record_path.is_file():
                continue
            record=core.read(record_path)
            if record.get('status') != 'complete':
                continue
            post_path=Path(record['postprocess_path']).resolve()
            core.require(post_path.is_relative_to(path.parent) and core.sha(post_path)==record['postprocess_sha256'],
                         'Pinned earlier XY80 summary/path differs')
            post=core.read(post_path)
            core.require(post['status']=='complete' and post['id']==HISTORY_ID and
                         case['h_xy_mm']==.625 and case['sc_cells']==2 and
                         case['bulk_counts']==[14,14,40] and case['channels']==2,
                         'Earlier same-candidate XY80 mesh differs')
            config,mask=Path(case['config_file']),Path(case['mask_file'])
            core.require(core.sha(config)==case['config_sha256'] and core.sha(mask)==case['mask_sha256'],
                         'Earlier XY80 config/mask pins differ')
            matches.append(dict(run_id=path.parent.name,case_id=HISTORY_ID,
                registration_path=str(path),registration_sha256=core.sha(path),
                case_record_path=str(record_path),case_record_sha256=core.sha(record_path),
                postprocess_path=str(post_path),postprocess_sha256=core.sha(post_path),
                config_file=str(config),config_sha256=core.sha(config),
                mask_file=str(mask),mask_sha256=core.sha(mask),native_input_sha256=post['input_sha256']))
    core.require(len(matches)==1,'One unique preceding same-candidate XY80 cache required')
    return matches[0]


def _wave_rows(before,after,before_h,after_h):
    rows=[]
    for wave in ('square_3h','sine','triangle_3h'):
        a=[c for c in before['conditions'] if c['waveform']==wave]
        b=[c for c in after['conditions'] if c['waveform']==wave]
        core.require(len(a)==len(b)==1,'Exactly three same-wave XY comparison conditions required')
        for condition in (a[0],b[0]):
            core.require(condition['actual_fundamental_Hz']==[3000,3030] and condition['phase_deg']==[0.,0.] and
                         condition['source_Vpp_per_output']==1.,'Actual carrier/phase/voltage differs')
        av,bv=_comparison_values(a[0]),_comparison_values(b[0])
        core.require(all(value>0 for value in (*av.values(),*bv.values())), 'Positive finite XY metrics required')
        changes={}
        for key,limit in GATE_PERCENT.items():
            change=100*(bv[key]-av[key])/abs(av[key])
            changes[key]=dict(before=av[key],after=bv[key],relative_change_percent=change,
                limit_percent=limit,passed=abs(change)<=limit,
                descriptive_logh_sensitivity=math.log(bv[key]/av[key])/math.log(after_h/before_h))
        rows.append(dict(waveform=wave,before_condition_id=a[0]['id'],after_condition_id=b[0]['id'],
                         changes=changes,passed=all(c['passed'] for c in changes.values())))
    return rows


def compare_candidate_xy(run,case,post):
    core.require(case['id']==CASE_ID and post['id']==CASE_ID and post['status']=='complete',
                 'Exact completed candidate XY120 case required')
    reference=case['candidate_coarser_xy_reference'];history=case['candidate_xy80_history_reference']
    old_path,hist_path=Path(reference['postprocess_path']),Path(history['postprocess_path'])
    core.require(core.sha(old_path)==reference['postprocess_sha256'] and core.sha(hist_path)==history['postprocess_sha256'],
                 'Pinned same-candidate prior XY summaries changed')
    old,previous=core.read(old_path),core.read(hist_path)
    a,b=old['mesh_metadata'],post['mesh_metadata']
    pm=previous['mesh_metadata']
    core.require(previous['status']=='complete' and previous['id']==HISTORY_ID and pm['h_xy_mm']==.625 and
                 pm['sc_cells']==2 and pm['bulk_layer_counts']==[14,14,40], 'Earlier XY80 history differs')
    for key in ('radius_mm','total_depth_mm','tissue_boundaries_mm','z_faces_mm','sc_cells',
                'bulk_layer_counts','field_reconstruction','source_resistance_ohm','source_peak_V','channels'):
        core.require(a[key]==b[key],'XY-only physical/normalization property differs: '+key)
    core.require(old['status']=='complete' and old['id']==TEMPLATE_ID and a['h_xy_mm']==.5 and
                 b['h_xy_mm']==H_MM and b['sc_cells']==2 and b['bulk_layer_counts']==[14,14,40] and
                 a['cells']==550200 and b['cells']==EXPECTED_CELLS,
                 'XY comparison must retain SC2/bulk14,14,40 and fixed cells')
    current=_wave_rows(old,post,.5,H_MM)
    preceding=_wave_rows(previous,old,.625,.5)
    passed=all(row['passed'] for row in current)
    return dict(schema='task1-candidate-XY-only-comparison-v1',run_id=Path(run).name,case_id=CASE_ID,
        status='passed_registered_candidate_XY_pair' if passed else 'failed_registered_candidate_XY_pair',
        all_registered_comparison_gates_passed=passed,gate_count=36,waveform_comparisons=current,
        preceding_XY_comparison=preceding,preceding_failed_gates_preserved=True,
        grid_spacing_history_mm=[.625,.5,H_MM],grid_step_ratios=[1.25,1.2],
        logh_scope='Descriptive sensitivity for unequal finite steps only; not extrapolated order/error or continuum convergence',
        candidate_coarser_xy_reference=reference,candidate_xy80_history_reference=history,
        same_grid_original_four_pad_reference_status='held_no_eligible_reference',
        matched_burden_evaluated=False,across_mesh_normalization_performed=False,
        candidate_adopted=False,XY_convergence_hold_resolved=False,
        mesh_convergence_validated=False,continuum_convergence_validated=False,
        experimental_validation=False,safety_or_activation_validated=False,no_threshold_relaxation=True)


def prepare_candidate_xy(run):
    start=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run==run.resolve() and not run.exists(),
                 'Unique canonical candidate XY run required; no retries')
    _caller_owns_execution_lock();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    integrity=core.original_integrity()
    prereg,design_file=core.HIST/'preregistration.json',core.HIST/'inputs/designs.json'
    template=copy.deepcopy(core.read(prereg)['case_pool'][TEMPLATE_ID]);validate_candidate_template(template)
    old_config=core.HIST/'configs'/Path(template['config_file']).name
    old_mask=core.HIST/'masks'/Path(template['mask_file']).name
    core.require(core.sha(old_config)==template['config_sha256'] and core.sha(old_mask)==template['mask_sha256'],
                 'Frozen candidate XY100 config/mask changed')
    reference=_completed_same_candidate_xy(template);history=_history_reference()
    old_history_config=_properties(Path(history['config_file']).read_bytes())
    current_config=_properties(old_config.read_bytes())
    excluded={'h_mm','mask.path','mask.sha256'}
    core.require({k:v for k,v in old_history_config.items() if k not in excluded}==
                 {k:v for k,v in current_config.items() if k not in excluded},
                 'Earlier XY80 material/contact/geometry differs')
    design=copy.deepcopy(next(d for d in core.read(design_file) if d['id']==DESIGN_ID))
    rows,areas,receipt=aligned_full_face_mask(design)
    case=copy.deepcopy(template)
    case.update(id=CASE_ID,h_xy_mm=H_MM,sc_cells=2,bulk_counts=[14,14,40],channels=2,n_outputs=2,n_pads=4,
        java_class='CloudShapeBasis',postprocessor='legacy_native',exporter_class='SelectivityShapeBasis',
        design_id=DESIGN_ID,mesh_id='xy120_SC2_bulk14_14_40',source_run_id=run.name,
        candidate_coarser_xy_reference=reference,candidate_xy80_history_reference=history,
        requires_candidate_xy_comparison_after_postprocess=True,status='preregistered_not_executed',
        same_grid_original_four_pad_reference_status='held_no_eligible_reference',candidate_adopted=False)
    case.update(_mesh(case));bound=case['cells']*600
    core.require(case['cells']==EXPECTED_CELLS and bound==EXPECTED_RAW_BOUND_BYTES and
                 bound<=core.LIMITS['max_batch_added_bytes'],'XY791280cell/raw474768000byte bound differs')
    core.require(shutil.disk_usage(run.parent).free>2*core.GIB+bound,'Raw output plus2GiB reserve unavailable')
    budget_path=core.REPO/'runtime/task1-budget.json';budget=core.read(budget_path)
    core.require(budget['limit_seconds']==6600 and 6600-budget['spent_seconds']>=720,
                 'Need600s execution plus120s preparation allowance inside6600s')
    jdk=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
    javac=shutil.which('javac') or str(jdk/'javac');java=str(Path(javac).parent/'java')
    core.require(Path(javac).is_file() and Path(java).is_file(),'Java compiler/runtime unavailable')
    run.mkdir()
    for directory in ('configs','masks','bases','cases','postprocess','logs','classes','geometry-audit'):
        (run/directory).mkdir()
    succeeded=False;registration=None
    try:
        mask=run/'masks'/(CASE_ID+'.csv')
        with mask.open('x',newline='') as stream:
            writer=csv.writer(stream,lineterminator='\n');writer.writerow(['pad','i','j','area_m2'])
            for pad,i,j,area in rows:writer.writerow([pad,i,j,format(area,'.17g')])
        config=run/'configs'/(CASE_ID+'.properties')
        data,changes=changed_xy_config(old_config.read_bytes(),mask,core.sha(mask));config.write_bytes(data)
        core.write(run/'geometry-audit'/'aligned-contact-mask.json',receipt)
        case.update(config_file=str(config),config_sha256=core.sha(config),mask_file=str(mask),
                    mask_sha256=core.sha(mask),expected_pad_areas_m2=areas)
        design['channels']=2;design['xy_mm']=[p['center_mm'] for p in design['pads']];case['design']=design
        case['circuit']=dict(n_pads=4,n_outputs=2,n_signal_pads=2,n_return_pads=2,n_return_nodes=1,
            return_topology='common_GND',pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
            source_Vpp_each=1.,source_peak_V=.5,source_resistance_ohm=50.,source_phase_deg=[0.,0.],
            carrier_assignment_Hz=[3000,3030],harmonics_Hz=[9000,9090],
            inactive_source_at_other_frequencies='0V through50ohm',exclusive_source_return_pair_assumed=False)
        case['cache_signature']=core.check_cached_operator(case,run)
        pins=core.source_pins()
        for path in (Path(__file__),core.REPO/'tests/test_task1_candidate_xy_registration.py',
                     core.REPO/'tools/task1_candidate_coupled_registration.py',prereg,design_file,old_config,old_mask):
            pins[str(path)]=core.sha(path)
        for ref in (reference,history):
            for key in ('registration','case_record','postprocess'):
                pins[ref[key+'_path']]=ref[key+'_sha256']
            pins[ref['config_file']]=ref['config_sha256'];pins[ref['mask_file']]=ref['mask_sha256']
            pins.update(ref['native_input_sha256'])
        def command(args,log):
            remaining=6600-budget['spent_seconds']-(time.monotonic()-start)
            core.require(remaining>600 and shutil.disk_usage(run).free>=2*core.GIB,'Preparation budget/reserve exhausted')
            core.write(run/'controller.json',dict(status='preparing',phase='XY_compile_selftest',command=args,
                pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now()))
            subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=min(120.,remaining-600))
        with (run/'logs/compile-selftest.log').open('x') as log:
            command([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'),str(core.SOURCE/'ExploreBasis.java'),
                str(core.SOURCE/'SelectivityShapeBasis.java'),str(core.REPO/'tools/java/CloudShapeBasis.java')],log)
            command([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1',
                     '-cp',str(run/'classes'),'CloudShapeBasis','--selftest'],log)
        for path in [*(run/'configs').glob('*'),*(run/'masks').glob('*'),*(run/'classes').glob('*'),
                     *(run/'geometry-audit').glob('*')]:pins[str(path)]=core.sha(path)
        for path,expected in pins.items():core.require(core.sha(path)==expected,'Pinned input/source changed: '+path)
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='one_candidate_XY_only_validation',
            status='prepared',created_utc=core.now(),source_commit=subprocess.check_output(
                ['git','rev-parse','HEAD'],cwd=core.REPO,text=True).strip(),
            historical_source_commit='8c3a30a778cc9bf19ccb52ca523598bff0a84650',package_integrity=integrity,
            limits=copy.deepcopy(core.LIMITS),gates=copy.deepcopy(core.GATES),cases=[case],
            new_PDE_conditions_maximum=1,expected_raw_bound_bytes=bound,java=java,source_and_input_sha256=pins,
            preparation_seconds=time.monotonic()-start,
            path_mapping=[dict(original_config=str(old_config),original_sha256=core.sha(old_config),
                new_config=str(config),new_sha256=core.sha(config),changed_fields=list(changes),
                new_mask=str(mask),mask_sha256=core.sha(mask),mask_rule=receipt['rule'],
                physical_geometry_material_contact_circuit_changed=False)],
            scientific_scope='Same small-square4pads/2outputs XY-only SC2bulk14/14/40; no normalization to heldXY120 baseline',
            fixed_comparison_gate_percent=GATE_PERCENT,fixed_gate_count=36,comparison_waveforms=['square_3h','sine','triangle_3h'],
            grid_spacing_history_mm=[.625,.5,H_MM],grid_step_ratios=[1.25,1.2],
            preceding_XY_failure_status='preserved; newpairpass cannot clear earlier5%failure',
            same_grid_original_four_pad_reference_status='held_no_eligible_reference',
            matched_burden_evaluated=False,candidate_adopted=False,XY_convergence_hold_resolved=False,
            storage=dict(native_location=str(run),persistent_backup_verified=False,retirement_of_old_environment_allowed=False),
            frozen_source_snapshot_owner='root core.freeze_sources once after preparation',
            next_decision='Preserve all36 pairgates plus precedingXY failures; no globalXYhold/adoption/normalization promotion')
        core.write(run/'preregistration.json',registration);core.write(run/'controller.json',dict(status='prepared',updated_utc=core.now()))
        succeeded=True
    except BaseException as error:
        core.write(run/'preparation-failure.json',dict(status='preparation_failed_preserved',error_type=type(error).__name__,
            error=str(error),observed_utc=core.now(),partial_evidence_preserved=True,automatic_retry=False));raise
    finally:
        elapsed=registration['preparation_seconds'] if succeeded else time.monotonic()-start
        budget['spent_seconds']+=elapsed
        budget['runs'].append(dict(run_id=run.name,stage='preparation',seconds=elapsed,
            status='prepared' if succeeded else 'preparation_failed_preserved'));core.write(budget_path,budget)
    print(dict(status='prepared',run=str(run),case=CASE_ID,cells=EXPECTED_CELLS,raw_bound=bound))
    return registration
