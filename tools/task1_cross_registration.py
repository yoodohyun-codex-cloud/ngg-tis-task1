"""Register two fixed larger-area top crosses; no computation on import.

CloudShapeBasis consumes the explicit contact mask, including nonconvex masks.
The frozen convex-polygon geometry helper is deliberately not used for crosses.
Only the root controller may call preparation under both global execution locks.
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

TEMPLATE_ID = 'baseline-square15-xy80'
H_MM = .625
OUTER_MM = 17.5
WIDTHS_MM = (10., 12.5)
CASE_IDS = ('cross17p5-arm10-xy80', 'cross17p5-arm12p5-xy80')
CENTRES_MM = ((-10., -10.), (10., 10.), (10., -10.), (-10., 10.))
EXPECTED_CELLS = 351680
EXPECTED_RAW_BOUND_BYTES = 422016000


def cross_face_area_mm2(x0, y0, h, cx, cy, arm_mm):
    """Exact rectangle-union/face overlap for a later partial-face refinement.

    This pure geometry primitive registers no extra case. At h0.5, finite
    partial contacts must be retained: horizontal + vertical - central square.
    """
    core.require(arm_mm in WIDTHS_MM and math.isfinite(h) and h > 0, 'Registered cross/positive face required')
    def rectangle(width,height):
        dx=max(0.,min(x0+h,cx+width/2)-max(x0,cx-width/2))
        dy=max(0.,min(y0+h,cy+height/2)-max(y0,cy-height/2))
        return dx*dy
    area=rectangle(OUTER_MM,arm_mm)+rectangle(arm_mm,OUTER_MM)-rectangle(arm_mm,arm_mm)
    core.require(0 <= area <= h*h, 'Invalid exact rectangle-union overlap')
    return area


def validate_baseline_template(template, design, config):
    """The only physical changes permitted later are contact outline and area."""
    core.require(template['id'] == TEMPLATE_ID and template['channels'] == 2 and
        template['h_xy_mm'] == H_MM and template['sc_cells'] == 2 and
        template['bulk_counts'] == [14, 14, 40], 'Frozen XY80 baseline required')
    core.require(design['id'] == 'baseline-square15' and design['phantom_diameter_mm'] == 50 and
        design['contact_plane_z_mm'] == 0 and design['source_outputs'] == 2 and
        design['total_pads'] == 4 and len(design['pads']) == 4 and
        design['return_connection'] == 'all_return_pads_ideal_common_GND',
        'Fixed D50 top four-pad/two-output/common-GND design required')
    for i, (pad, centre) in enumerate(zip(design['pads'], CENTRES_MM)):
        core.require(pad['pad'] == i and tuple(pad['center_mm']) == centre and
            pad['shape'] == 'rectangle' and pad['width_mm'] == pad['height_mm'] == 15 and
            pad['rotation_deg'] == 0 and pad['corner_radius_mm'] == 0 and
            pad['analytic_area_mm2'] == 225 and
            pad['role'] == ('signal' if i < 2 else 'common_gnd_return') and
            pad['source_output'] == (i if i < 2 else None), 'Original four-pad geometry/wiring differs')
    p = _properties(config)
    core.require(p['h_mm'] == '0.625' and p['channels'] == '2' and
        p['validation.sc_cells'] == '2' and p['bulk.counts'] == '14,14,40' and
        p['frequencies'] == '3000,3030,9000,9090', 'Frozen mesh/carriers differ')
    for i, (x, y) in enumerate(CENTRES_MM):
        core.require(float(p[f'pad.{i}.x_mm']) == x and float(p[f'pad.{i}.y_mm']) == y and
            p[f'pad.{i}.shape'] == 'rectangle' and float(p[f'pad.{i}.width_mm']) == 15 and
            float(p[f'pad.{i}.height_mm']) == 15 and float(p[f'pad.{i}.rotation_deg']) == 0 and
            float(p[f'pad.{i}.analytic_area_mm2']) == 225, 'Baseline config geometry differs')


def cross_design(baseline, arm_mm):
    core.require(arm_mm in WIDTHS_MM, 'Only the two preregistered arm widths are allowed')
    design = copy.deepcopy(baseline)
    a, b = OUTER_MM/2, arm_mm/2
    outline = [(-b,-a),(b,-a),(b,-b),(a,-b),(a,b),(b,b),
               (b,a),(-b,a),(-b,b),(-a,b),(-a,-b),(-b,-b)]
    area = 2*OUTER_MM*arm_mm-arm_mm**2
    for pad, (x,y) in zip(design['pads'], CENTRES_MM):
        core.require(tuple(pad['center_mm']) == (x,y), 'Baseline pad centre cannot move')
        polygon = [[x+u,y+v] for u,v in outline]
        core.require(all(px*px+py*py < 625 for px,py in polygon), 'Cross polygon outside fixed D50')
        pad.update(shape='cross', width_mm=OUTER_MM, height_mm=OUTER_MM,
            outer_length_mm=OUTER_MM, arm_width_mm=arm_mm, polygon_mm=polygon,
            area_mm2=area, analytic_area_mm2=area, polygon_area_mm2=area,
            geometry_primitive='union_of_two_centered_axis_aligned_rectangles',
            union_rectangles_mm=[dict(center_mm=[x,y],width_mm=OUTER_MM,height_mm=arm_mm),
                                 dict(center_mm=[x,y],width_mm=arm_mm,height_mm=OUTER_MM)])
    design.update(id=CASE_IDS[WIDTHS_MM.index(arm_mm)].removesuffix('-xy80'),
        group='larger_contact_area_fixed_centres', channels=2,
        xy_mm=[p['center_mm'] for p in design['pads']], minimum_gap_mm=2.5,
        geometry_revision='exact_grid_aligned_concave_cross_v1',
        physical_total_contact_area_mm2=4*area,
        area_change_vs_four_square225_percent=100*(area/225-1),
        area_policy='Larger physical contact area, not equal-area geometry comparison')
    return design


def aligned_cross_mask(design):
    """Union integer face sets, so overlap is counted once without clipping."""
    arm = design['pads'][0]['arm_width_mm']
    core.require(arm in WIDTHS_MM and design['source_outputs'] == 2 and design['total_pads'] == 4 and
                 len(design['pads']) == 4, 'Registered four-pad cross required')
    face, rows, covered = (H_MM/1000)**2, [], set()
    outer_cells, arm_cells = round(OUTER_MM/H_MM), round(arm/H_MM)
    core.require(outer_cells == 28 and arm_cells in (16,20), 'Exact registered grid-aligned arms required')
    for p, (pad, (x,y)) in enumerate(zip(design['pads'], CENTRES_MM)):
        area=2*OUTER_MM*arm-arm**2
        core.require(pad['pad'] == p and tuple(pad['center_mm']) == (x,y) and
            pad['shape'] == 'cross' and pad['outer_length_mm'] == OUTER_MM and
            pad['arm_width_mm'] == arm and pad['rotation_deg'] == 0 and
            pad['width_mm'] == pad['height_mm'] == OUTER_MM and pad['corner_radius_mm'] == 0 and
            pad['analytic_area_mm2'] == pad['area_mm2'] == pad['polygon_area_mm2'] == area and
            pad['role'] == ('signal' if p < 2 else 'common_gnd_return') and
            pad['source_output'] == (p if p < 2 else None), 'Cross geometry/wiring changed')
        cx, cy = round((x+25)/H_MM), round((y+25)/H_MM)
        for k, value in ((cx,x),(cy,y)):
            core.require(abs(-25+k*H_MM-value) < 1e-12, 'Centre not on registered grid edge')
        faces = set()
        for width,height in ((outer_cells,arm_cells),(arm_cells,outer_cells)):
            faces.update((i,j) for j in range(cy-height//2,cy+height//2)
                         for i in range(cx-width//2,cx+width//2))
        core.require(not covered.intersection(faces), 'Physical cross pads overlap')
        covered.update(faces)
        for i,j in sorted(faces,key=lambda ij:(ij[1],ij[0])):
            # All actual face corners must lie in D50, not merely face centres.
            core.require(all((-25+ii*H_MM)**2+(-25+jj*H_MM)**2 < 625
                for ii in (i,i+1) for jj in (j,j+1)), 'Contact face outside fixed D50')
            core.require(cross_face_area_mm2(-25+i*H_MM,-25+j*H_MM,H_MM,x,y,arm)==H_MM**2,
                         'Registered aligned cross face is not fully covered')
            rows.append((p,i,j,face))
    count = 640 if arm == 10 else 720
    area = 2*OUTER_MM*arm-arm**2
    areas = [math.fsum(a for pad,_,_,a in rows if pad == p) for p in range(4)]
    core.require(len(rows) == 4*count and all(abs(a/(area*1e-6)-1) <= 1e-10 for a in areas),
                 'Exact cross face count/area differs')
    receipt = dict(rule='exact-integer-face-union-cross-v1', h_xy_mm=H_MM,
        outer_length_mm=OUTER_MM, arm_width_mm=arm, faces_per_pad=count, contacts=len(rows),
        full_face_area_m2=face, represented_pad_areas_m2=areas,
        physical_analytic_area_mm2_each=area, physical_total_area_mm2=4*area,
        area_change_vs_baseline_percent=100*(area/225-1), bounding_box_gap_mm=2.5,
        maximum_physical_vertex_radius_mm=max(math.hypot(x,y) for p in design['pads'] for x,y in p['polygon_mm']),
        discarded_slivers=0, snapped_partial_faces=0, renormalization=False,
        convex_polygon_mask_helper_used=False, geometry_convergence_claimed=False)
    return rows, areas, receipt


def changed_cross_config(data, design, mask_path, mask_sha256, areas):
    changes = {'mask.path':str(mask_path), 'mask.sha256':mask_sha256}
    for p,pad in enumerate(design['pads']):
        changes.update({f'pad.{p}.shape':'cross', f'pad.{p}.width_mm':str(OUTER_MM),
            f'pad.{p}.height_mm':str(OUTER_MM), f'pad.{p}.analytic_area_mm2':str(pad['analytic_area_mm2']),
            f'pad.{p}.represented_area_m2':format(areas[p],'.17g')})
    output = _changed_config(data,changes)
    # New properties are descriptive; mask faces alone define electrode contacts.
    additions = {f'pad.{p}.arm_width_mm':str(pad['arm_width_mm']) for p,pad in enumerate(design['pads'])}
    core.require(not set(additions).intersection(_properties(output)), 'Cross metadata keys already exist')
    if not output.endswith(b'\n'): output += b'\n'
    output += ''.join(k+'='+v+'\n' for k,v in additions.items()).encode()
    core.require(set(_properties(output)) == set(_properties(data))|set(additions), 'Unexpected config keys')
    return output, {**changes,**additions}


def _completed_baseline(template, old_config):
    """Reuse the eligible XY80 baseline; never schedule another baseline PDE."""
    original, matches = _properties(old_config.read_bytes()), []
    for path in (core.REPO/'data-native').glob('cloud-*/preregistration.json'):
        for case in core.read(path).get('cases',[]):
            if case['id'] != TEMPLATE_ID: continue
            record_path = path.parent/'cases'/(TEMPLATE_ID+'.json')
            if not record_path.is_file(): continue
            record = core.read(record_path)
            if record.get('status') != 'complete': continue
            post_path, config, mask = Path(record['postprocess_path']),Path(case['config_file']),Path(case['mask_file'])
            core.require(all(p.resolve().is_relative_to(path.parent.resolve()) for p in (post_path,config,mask)),
                         'Completed baseline paths must belong to its local run')
            core.require(core.sha(post_path)==record['postprocess_sha256'] and core.sha(config)==case['config_sha256'] and
                core.sha(mask)==case['mask_sha256']==template['mask_sha256'], 'Completed baseline pins differ')
            actual = _properties(config.read_bytes())
            core.require({k:v for k,v in original.items() if k!='mask.path'} ==
                         {k:v for k,v in actual.items() if k!='mask.path'}, 'Same-grid baseline physics differs')
            post = core.read(post_path)
            core.require(post['status']=='complete' and post['id']==TEMPLATE_ID and
                case['h_xy_mm']==H_MM and case['sc_cells']==2 and case['bulk_counts']==[14,14,40] and
                case['channels']==2 and all(record['validation'][k] <= v for k,v in core.GATES.items()),
                'Completed numerically eligible XY80 baseline required')
            matches.append(dict(run_id=path.parent.name,case_id=TEMPLATE_ID,
                registration_path=str(path),registration_sha256=core.sha(path),
                case_record_path=str(record_path),case_record_sha256=core.sha(record_path),
                postprocess_path=str(post_path),postprocess_sha256=core.sha(post_path),
                config_file=str(config),config_sha256=core.sha(config),mask_file=str(mask),mask_sha256=core.sha(mask),
                native_input_sha256=post['input_sha256']))
    core.require(len(matches)==1, 'One unique eligible completed XY80 baseline required; no duplicate PDE')
    return matches[0]


def prepare_cross(run):
    """Prepare exactly two contact geometries; actual execution stays with root."""
    start=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run==run.resolve() and not run.exists(), 'Unique canonical cross run required')
    _caller_owns_execution_lock();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    integrity=core.original_integrity()
    prereg,designs=core.HIST/'preregistration.json',core.HIST/'inputs/designs.json'
    template=copy.deepcopy(core.read(prereg)['case_pool'][TEMPLATE_ID])
    old_config=core.HIST/'configs'/Path(template['config_file']).name
    old_mask=core.HIST/'masks'/Path(template['mask_file']).name
    core.require(core.sha(old_config)==template['config_sha256'] and core.sha(old_mask)==template['mask_sha256'],
                 'Frozen baseline config/mask changed')
    baseline=next(d for d in core.read(designs) if d['id']=='baseline-square15')
    validate_baseline_template(template,baseline,old_config.read_bytes())
    reference=_completed_baseline(template,old_config)
    bound=2*EXPECTED_CELLS*600
    core.require(bound==EXPECTED_RAW_BOUND_BYTES and bound<=core.LIMITS['max_batch_added_bytes'], 'Cross raw bound differs')
    core.require(shutil.disk_usage(run.parent).free>2*core.GIB+bound, 'Cross raw output plus2GiB reserve unavailable')
    budget_path=core.REPO/'runtime/task1-budget.json';budget=core.read(budget_path)
    core.require(budget['limit_seconds']==6600 and 6600-budget['spent_seconds']>=1320,
                 'Need two600s conditions plus120s preparation allowance within6600s')
    jdk=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
    javac=shutil.which('javac') or str(jdk/'javac');java=str(Path(javac).parent/'java')
    core.require(Path(javac).is_file() and Path(java).is_file(), 'Java compiler/runtime unavailable')
    run.mkdir()
    for directory in ('configs','masks','bases','cases','postprocess','logs','classes','geometry-audit'):(run/directory).mkdir()
    succeeded=False;registration=None
    try:
        cases,mappings=[],[];pins=core.source_pins()
        for path in (Path(__file__),core.REPO/'tests/test_task1_cross_registration.py',prereg,designs,old_config,old_mask):
            pins[str(path)]=core.sha(path)
        for key in ('registration','case_record','postprocess'):pins[reference[key+'_path']]=reference[key+'_sha256']
        pins[reference['config_file']]=reference['config_sha256'];pins[reference['mask_file']]=reference['mask_sha256']
        pins.update(reference['native_input_sha256'])
        for ident,arm in zip(CASE_IDS,WIDTHS_MM):
            design=cross_design(baseline,arm);rows,areas,receipt=aligned_cross_mask(design)
            mask=run/'masks'/(ident+'.csv')
            with mask.open('x',newline='') as stream:
                writer=csv.writer(stream,lineterminator='\n');writer.writerow(['pad','i','j','area_m2'])
                for p,i,j,area in rows:writer.writerow([p,i,j,format(area,'.17g')])
            config=run/'configs'/(ident+'.properties')
            data,changes=changed_cross_config(old_config.read_bytes(),design,mask,core.sha(mask),areas)
            config.write_bytes(data);core.write(run/'geometry-audit'/(ident+'.json'),receipt)
            case=copy.deepcopy(template)
            case.update(id=ident,design_id=design['id'],design=design,template_case_id=TEMPLATE_ID,
                java_class='CloudShapeBasis',postprocessor='legacy_native',exporter_class='SelectivityShapeBasis',
                channels=2,n_outputs=2,n_pads=4,source_run_id=run.name,mesh_id='xy80_SC2_bulk14_14_40',
                source_coating_nm=10,source_Rs_fit_window_Hz=500,
                config_file=str(config),config_sha256=core.sha(config),mask_file=str(mask),mask_sha256=core.sha(mask),
                expected_pad_areas_m2=areas,baseline_same_grid_reference=reference,
                contact_area_policy=design['area_policy'],physical_total_contact_area_mm2=receipt['physical_total_area_mm2'],
                area_change_vs_baseline_percent=receipt['area_change_vs_baseline_percent'],
                status='preregistered_not_executed',candidate_adopted=False,
                mesh_convergence_validated=False,existing_XY_contact_model_holds_preserved=True)
            case.update(_mesh(case));core.require(case['cells']==EXPECTED_CELLS, 'Cross cell count differs')
            case['circuit']=dict(n_pads=4,n_outputs=2,n_signal_pads=2,n_return_pads=2,n_return_nodes=1,
                return_topology='all_return_pads_ideal_common_GND',pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
                source_Vpp_each=1.,source_peak_V=.5,source_resistance_ohm=50.,source_phase_deg=[0.,0.],
                carrier_assignment_Hz=[3000,3030],harmonics_Hz=[9000,9090],
                inactive_source_at_other_frequencies='0 V through50 ohm',exclusive_source_return_pair_assumed=False)
            case['cache_signature']=core.check_cached_operator(case,run);cases.append(case)
            mappings.append(dict(original_config=str(old_config),original_sha256=core.sha(old_config),
                new_config=str(config),new_sha256=core.sha(config),changed_fields=list(changes),
                new_mask=str(mask),mask_sha256=core.sha(mask),mask_rule=receipt['rule'],
                geometry_and_area_changed=True,material_contact_impedance_and_circuit_changed=False))
        def command(args,log):
            remaining=6600-budget['spent_seconds']-(time.monotonic()-start)
            core.require(remaining>1200 and shutil.disk_usage(run).free>=2*core.GIB, 'Cross preparation budget/reserve exhausted')
            core.write(run/'controller.json',dict(status='preparing',phase='cross_compile_selftest',command=args,
                pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now()))
            subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=min(120.,remaining-1200))
        with (run/'logs/compile-selftest.log').open('x') as log:
            command([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'),str(core.SOURCE/'ExploreBasis.java'),
                str(core.SOURCE/'SelectivityShapeBasis.java'),str(core.REPO/'tools/java/CloudShapeBasis.java')],log)
            command([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),
                'CloudShapeBasis','--selftest'],log)
        for path in [*(run/'configs').glob('*'),*(run/'masks').glob('*'),*(run/'classes').glob('*'),
                     *(run/'geometry-audit').glob('*')]:pins[str(path)]=core.sha(path)
        for path,expected in pins.items():core.require(core.sha(path)==expected,'Pinned cross input/source changed: '+path)
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='two_larger_contact_cross_geometries',
            status='prepared',created_utc=core.now(),source_commit=subprocess.check_output(
                ['git','rev-parse','HEAD'],cwd=core.REPO,text=True).strip(),
            historical_source_commit='8c3a30a778cc9bf19ccb52ca523598bff0a84650',package_integrity=integrity,
            limits=copy.deepcopy(core.LIMITS),gates=copy.deepcopy(core.GATES),cases=cases,
            new_PDE_conditions_maximum=2,expected_raw_bound_bytes=bound,java=java,source_and_input_sha256=pins,
            preparation_seconds=time.monotonic()-start,path_mapping=mappings,baseline_same_grid_reference=reference,
            scientific_scope='Larger contact area at unchanged centres: four top crosses/two50ohm commonGND outputs; no grid convergence comparison',
            comparison_waveforms=['square_3h','sine','triangle_3h'],
            planned_normalizations=['raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power',
                                    'skin_contact_only','legacy_composite_full_skin'],
            evaluation_required=['absolute targetROI r<=5mm/depth15to20mm mean andP10',
                'wholeXY depth15to20mm slab mean/P10 and non-target selectivity',
                'full SC+dermis skin losses and contact losses, plusJmax/J95/contactV/sourcepower',
                'all five burden normalizations with absolute ROI modulation retained'],
            normalization_results_available=False,matched_burden_evaluated=False,candidate_adopted=False,
            existing_XY_contact_model_holds_preserved=True,mesh_convergence_validated=False,experimental_validation=False,
            contact_uncertainty='Frozen PBS-derived specific interface Z unchanged; no newRs subtraction or second area scaling; skin validation pending',
            storage=dict(native_location=str(run),persistent_backup_verified=False,retirement_of_old_environment_allowed=False),
            frozen_source_snapshot_owner='root core.freeze_sources once after preparation',
            next_decision='Compare actual same-grid absoluteROImean/P10 and selectivity under all burden caps; no adoption before edge/contact/mesh checks')
        core.write(run/'preregistration.json',registration)
        core.write(run/'controller.json',dict(status='prepared',updated_utc=core.now()));succeeded=True
    except BaseException as error:
        core.write(run/'preparation-failure.json',dict(status='preparation_failed_preserved',error_type=type(error).__name__,
            error=str(error),observed_utc=core.now(),partial_evidence_preserved=True,automatic_retry=False));raise
    finally:
        elapsed=registration['preparation_seconds'] if succeeded else time.monotonic()-start
        budget['spent_seconds']+=elapsed;budget['runs'].append(dict(run_id=run.name,stage='preparation',seconds=elapsed,
            status='prepared' if succeeded else 'preparation_failed_preserved'));core.write(budget_path,budget)
    print(dict(status='prepared',run=str(run),cases=list(CASE_IDS),cells_each=EXPECTED_CELLS,raw_bound=bound))
    return registration
