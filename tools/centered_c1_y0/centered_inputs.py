"""New centered C1 input files only; no solver/API/ledger work on import.

The old one-pair mask moves exactly +16 native Y cells (+10mm). Fields and
potentials are never moved or reused. All original files remain unchanged.
"""
from __future__ import annotations
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path('/workspace/ngg-tis-task1')
CASE_ID = 'centered-square15-C1-y0-xy80-f3000'
OLD_RUN = ROOT/'data-native/cloud-mesh-c1-20261019T190000Z'
OLD_ID = 'baseline-square15-C1pair0-xy80'
PREFIX = 'task1-centered-c1-y0-20261025-run'
H_MM = .625


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def properties(text):
    result = {}
    for line in text.splitlines():
        if line.strip() and not line.lstrip().startswith(('#','!')):
            key,value = line.split('=',1)
            require(key not in result,'Duplicate configuration property')
            result[key] = value
    return result


def transform_inputs(config_text, old_rows, new_mask_path):
    """Pure exact-cell geometry/config transformation, used by fixtures too."""
    p = properties(config_text)
    require(float(p['h_mm']) == H_MM and p['channels'] == '1' and p['validation.sc_cells'] == '2' and
            p['bulk.counts'] == '14,14,40' and p['frequencies'] == '3000,3030,9000,9090', 'Exact original fine C1 template required')
    for pad,x in enumerate((-10.,10.)):
        require(float(p[f'pad.{pad}.x_mm']) == x and float(p[f'pad.{pad}.y_mm']) == -10. and
                p[f'pad.{pad}.shape'] == 'rectangle' and float(p[f'pad.{pad}.width_mm']) == 15 and
                float(p[f'pad.{pad}.height_mm']) == 15 and float(p[f'pad.{pad}.rotation_deg']) == 0 and
                float(p[f'pad.{pad}.analytic_area_mm2']) == 225 and
                math.isclose(float(p[f'pad.{pad}.represented_area_m2']),225e-6,rel_tol=1e-12), 'Original two square pads required')
    expected = {(pad,i,j) for pad,begin in ((0,12),(1,44)) for j in range(12,36) for i in range(begin,begin+24)}
    actual = {}
    for row in old_rows:
        key = (int(row['pad']),int(row['i']),int(row['j']))
        require(key not in actual and math.isclose(float(row['area_m2']),(H_MM/1000)**2,rel_tol=1e-12), 'Unique original full-face patches required')
        actual[key] = float(row['area_m2'])
    require(actual.keys() == expected, 'Original geometry must be exactly the registered off-centre pair')
    rows = [dict(pad=pad,i=i,j=j+16,area_m2=actual[(pad,i,j)]) for pad,i,j in sorted(expected,key=lambda a:(a[0],a[2],a[1]))]
    for row in rows:
        x,y = (-25+(row[k]+.5)*H_MM for k in ('i','j'))
        require(x*x+y*y < 625 and 0 <= row['i'] < 80 and 0 <= row['j'] < 80, 'Translated contact must stay inside the fixed D50 mesh')
    buffer = io.StringIO(); writer = csv.writer(buffer,lineterminator='\n')
    writer.writerow(['pad','i','j','area_m2'])
    for row in rows: writer.writerow([row['pad'],row['i'],row['j'],format(row['area_m2'],'.17g')])
    mask = buffer.getvalue().encode()
    changes = {'frequencies':'3000','pad.0.y_mm':'0.0','pad.1.y_mm':'0.0',
               'mask.path':str(new_mask_path),'mask.sha256':sha(mask)}
    lines = []
    for line in config_text.splitlines(keepends=True):
        key = line.split('=',1)[0]
        lines.append(key+'='+changes[key]+'\n' if key in changes else line)
    config = ''.join(lines).encode(); after = properties(config.decode())
    require({k:v for k,v in p.items() if k not in changes} == {k:v for k,v in after.items() if k not in changes},
            'Only Y coordinates, selected frequency and mask path/hash may change')
    areas = [math.fsum(r['area_m2'] for r in rows if r['pad'] == pad) for pad in range(2)]
    require(all(math.isclose(a,225e-6,rel_tol=1e-12) for a in areas), 'Each actual pad must remain225mm2')
    pads = []
    for pad,cx in enumerate((-10.,10.)):
        polygon = [[cx-7.5,-7.5],[cx+7.5,-7.5],[cx+7.5,7.5],[cx-7.5,7.5]]
        require(all(x*x+y*y < 625 for x,y in polygon), 'Entire physical rectangle must fit the fixed cylinder')
        pads.append(dict(pad=pad,shape='rectangle',center_mm=[cx,0.],width_mm=15.,height_mm=15.,rotation_deg=0.,
            area_mm2=225.,analytic_area_mm2=225.,polygon_area_mm2=225.,polygon_mm=polygon,
            role='signal' if pad == 0 else 'common_gnd_return',source_output=0 if pad == 0 else None))
    return config,mask,dict(pads=pads,areas_m2=areas,patches=len(rows),changed_fields=sorted(changes),
        centre_distance_mm=20.,edge_gap_mm=5.,physical_vertex_radius_squared_max_mm2=362.5,
        y_shift_mm=10.,native_j_shift=16,old_fields_translated=False)


def build_inputs(outputroot):
    """Create new config/mask in one explicitly named canonical tmpfs run."""
    run = Path(outputroot).absolute()
    require(run == run.resolve() and run.parent == Path('/dev/shm').resolve() and run.name.startswith(PREFIX) and
            not run.is_symlink(), 'Only the approved canonical new tmpfs run is allowed')
    pre_path = OLD_RUN/'preregistration.json'
    raw_pre = pre_path.read_bytes(); pre = json.loads(raw_pre)
    original = next(c for c in pre['cases'] if c['id'] == OLD_ID)
    config_path,mask_path = Path(original['config_file']),Path(original['mask_file'])
    require(original['source_coating_nm'] == 10 and original['source_Rs_fit_window_Hz'] == 500 and
            original['circuit']['n_pads'] == 2 and original['circuit']['n_outputs'] == 1, 'Nominal PBS10nm/Rs500 genuine C1 source required')
    old_config,old_mask = config_path.read_bytes(),mask_path.read_bytes()
    require(sha(old_config) == original['config_sha256'] and sha(old_mask) == original['mask_sha256'], 'Original frozen C1 template hashes changed')
    require(not (run/'preregistration.json').exists() and not (run/'execution-attempt.json').exists(),
            'Never overwrite prepared, failed or partial centered inputs')
    run.mkdir(exist_ok=True)
    for name in ('configs','masks'):
        directory = run/name
        if directory.exists():
            require(directory.is_dir() and directory == directory.resolve() and not directory.is_symlink() and
                    not any(directory.iterdir()), 'Input directories must be regular and empty')
        else: directory.mkdir()
    config = run/'configs'/(CASE_ID+'.properties'); mask = run/'masks'/(CASE_ID+'.csv')
    rows = list(csv.DictReader(io.StringIO(old_mask.decode())))
    config_bytes,mask_bytes,proof = transform_inputs(old_config.decode(),rows,mask)
    with mask.open('xb') as stream: stream.write(mask_bytes)
    with config.open('xb') as stream: stream.write(config_bytes)
    require(config_path.read_bytes() == old_config and mask_path.read_bytes() == old_mask and pre_path.read_bytes() == raw_pre,
            'Original input bytes must remain unchanged')
    case = copy.deepcopy(original)
    design = dict(id=CASE_ID+'-geometry',pads=proof['pads'],phantom_diameter_mm=50.,contact_plane_z_mm=0.,
        source_outputs=1,total_pads=2,channels=1,xy_mm=[[-10.,0.],[10.,0.]],
        return_connection='one_actual_return_pad_at_GND',geometry_revision='Y_centred_controlled_position_only',
        source_geometry_id=OLD_ID,physical_total_contact_area_mm2=450.,centre_distance_mm=20.,edge_gap_mm=5.)
    case.update(id=CASE_ID,design_id=design['id'],design=design,control_design=copy.deepcopy(design),source_run_id=run.name,
        config_file=str(config),config_sha256=sha(config_bytes),mask_file=str(mask),mask_sha256=sha(mask_bytes),
        expected_pad_areas_m2=proof['areas_m2'],actual_frequencies_Hz=[3000],source_coating_nm=10,source_Rs_fit_window_Hz=500)
    case['circuit'] = dict(n_pads=2,n_outputs=1,n_signal_pads=1,n_return_pads=1,n_return_nodes=1,
        pad_to_node={'0':'out0','1':'GND'},return_topology='one_actual_return_pad_at_GND',source_Vpp_each=1.,source_peak_V=.5,
        source_resistance_ohm=50.,carrier_assignment_Hz=[3000],basis_phase='cosine peak0.5+0j; pure-sine postprocessing coefficient-j',
        inactive_impedance_keys_Hz=[3030,9000,9090],other_TIS_pads_physically_present=False,other_TIS_output_present=False)
    case.update(input_sha256={str(config):sha(config_bytes),str(mask):sha(mask_bytes)},
        original_source_sha256={str(pre_path):sha(raw_pre),str(config_path):sha(old_config),str(mask_path):sha(old_mask)},
        geometry_proof=proof,source_case_id=OLD_ID,new_native_rhs=1,actual_frequencies_Hz=[3000])
    return case
