#!/usr/bin/env python3
"""Finite saved-field strip gap/XY diagnostic; no PDE, adoption or safety claims."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import threading
import time

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import numpy as np
import task1_resource_policy as policy
import task1_results_view as view
import task1_candidate_ranking as ranking
import task1_volume_selectivity as volume
import task1_candidate_screen as screen
import task1_waveform_check as waveform
import task1_grouped_gap_geometry as geometry

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
SCHEMA = 'task1-grouped-gap-diagnostic-preregistration-v1'
BASELINE = ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json'
RUNS = {'coarse':ROOT/'data-native/cloud-grouped-20261019T191500Z',
        'fine':ROOT/'data-native/cloud-grouped-fine-20261021T160000Z'}
FEEDBACK = ROOT/'docs/cloud-grouped-fine-recovery-20261021T161000Z/feedback-before.json'
FREQUENCIES = (3000, 3030, 9000, 9090)
MAX_SECONDS = 600
EPS0 = 8.8541878128e-12


def require(ok, message):
    if not ok: raise ValueError(message)


def now(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(Path(path).read_text())
def sha(path): return view.sha(Path(path))


def write(path, value, *, new=False):
    path = Path(path)
    raw = json.dumps(value, indent=2, allow_nan=False)+'\n'
    if new:
        with path.open('x') as stream: stream.write(raw)
    else:
        temporary = path.with_name(path.name+'.partial')
        temporary.write_text(raw); temporary.replace(path)


def implementation_refs():
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    paths = [Path(__file__).resolve(), ROOT/'tests/test_task1_grouped_gap_diagnostic.py',
        ROOT/'tests/test_task1_grouped_gap_geometry.py']
    paths += [Path(m.__file__).resolve() for m in (policy, view, ranking, volume, screen, waveform, geometry)]
    refs = {}
    for path in paths:
        require(subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT)
            == path.read_bytes(), 'Diagnostic implementation/tests must match committed HEAD: '+str(path))
        refs[str(path)] = sha(path)
    return dict(source_commit=commit, implementation_sha256=refs)


def native_path(summary, basename):
    paths = [Path(p) for p in summary['input_sha256'] if Path(p).name in (basename, basename+'.gz')]
    require(len(paths) == 1, 'Required saved native file missing/ambiguous: '+basename)
    path = paths[0]
    require(path.is_absolute() and path.resolve() == path and path.is_relative_to(ROOT/'data-native'),
        'Native input must be a canonical repository data path')
    return path


def inventory(path, *, fields):
    """Metadata only: bind declared native hashes without reading field arrays."""
    path = Path(path).resolve(); summary = read(path); run = path.parents[2]
    require(summary['status'] == 'complete', 'Completed source summary required')
    pre = read(run/'preregistration.json')
    cases = [c for c in pre['cases'] if c['id'] == summary['id']]
    require(len(cases) == 1, 'One registered source case required')
    case = cases[0]; record_path = run/'cases'/(case['id']+'.json'); record = read(record_path)
    require(record['status'] == 'complete' and record['postprocess_sha256'] == sha(path),
        'Completed case receipt must bind actual summary')
    refs = {str(p):sha(p) for p in (path, run/'preregistration.json', record_path,
        Path(case['config_file']), Path(case['mask_file']))}
    require(refs[case['config_file']] == case['config_sha256']
        and refs[case['mask_file']] == case['mask_sha256'], 'Source config/mask changed')
    audits = []
    for p in sorted((run/'audit').glob('*.json')):
        audit = read(p)
        if audit.get('case_id') == case['id'] and audit.get('summary_sha256') == sha(path):
            if (audit.get('status') == 'computed_spatial_and_skinJ_audit' and audit.get('native_inputs_unchanged') is True
                    and any('bulk_skin_J' in c and 'layer_contact_source_losses' in c for c in audit.get('conditions',[]))):
                audits.append(str(p)); refs[str(p)] = sha(p)
    require(len(audits) == 1, 'One completed source-bound skin audit required')
    names = ['grid.csv','mesh-metadata.json','validation.json','BASIS_COMPLETE']
    if fields:
        names += [f'{kind}-{f}'+('.csv' if kind == 'contacts' else '.bin')
            for f in FREQUENCIES for kind in ('field','density','source','contacts')]
    for name in names:
        p = native_path(summary,name); refs[str(p)] = summary['input_sha256'][str(p)]
        require(p.is_file(), 'Missing saved native input: '+str(p))
    for name in ('volume.npz','probes.json'):
        p = path.parent/name; expected = summary['artifacts']['files'][name]['SHA256']
        require(p.is_file(), 'Missing saved scalar/probe artifact: '+str(p)); refs[str(p)] = expected
    frozen = run/'frozen-source-manifest.json'
    if frozen.is_file(): refs[str(frozen)] = sha(frozen)
    return dict(case_id=case['id'], summary_path=str(path), source_commit=pre['source_commit'],
        config_sha256=case['config_sha256'], mask_sha256=case['mask_sha256'],
        audit_path=audits[0], native_fields_required=fields, inputs_sha256=refs)


def make_preregistration():
    """Call only after committing source; metadata registration does not decode native fields."""
    implementation = implementation_refs()
    cases = []
    for mesh, run in RUNS.items():
        for n in (4,8,12,16):
            ident = f'grouped-strip225-gap1-p{n:02d}-xy'+('40' if mesh == 'coarse' else '80')
            row = inventory(run/'postprocess'/ident/'summary.json', fields=True)
            row.update(mesh_label=mesh, n_pads=n); cases.append(row)
    baseline = inventory(BASELINE,fields=False)
    refs = dict(implementation['implementation_sha256'])
    for row in [baseline,*cases]: refs.update(row['inputs_sha256'])
    refs[str(FEEDBACK)] = sha(FEEDBACK)
    return dict(schema=SCHEMA,status='prepared',created_utc=now(),**implementation,
        baseline=baseline,cases=cases,source_and_input_sha256=refs,
        resource_policy_refs=policy.policy_refs(policy.load_ledger()),
        resource_limits=dict(max_seconds=MAX_SECONDS,CPU_count=1,RSS_bytes=3*GIB,
            minimum_free_disk_bytes=2*GIB,max_added_bytes=2*GIB),
        fixed_comparator=dict(baseline_path=str(BASELINE),numerical_burden_caps='all modes use original fine square4 raw burdens',
            cutoffs='original fine square4 native weighted primary/supplemental mean and P10, fixed across both meshes',
            ROI='central r<=5mm, surface depth z15..20mm; saved fractional native volume',
            depth='z=0 top; +z depth; SC0..0.1, dermis0.1..5.1mm',
            volume_weighting='native h^2 dz; saved primary fraction; exact depth overlap; no analytic renormalization',
            modes=list(screen.MODES),canonical_eight_gates=screen.GATE_DEFINITIONS,
            no_physiological_cutoff=True),feedback_id='6320375305',feedback_snapshot=str(FEEDBACK),
        new_PDE_solves=0,automatic_retry=False,adoption_allowed=False)


def verify_plan(path):
    plan = read(path)
    require(plan.get('schema') == SCHEMA and plan.get('status') == 'prepared'
        and plan.get('new_PDE_solves') == 0 and len(plan['cases']) == 8, 'Fixed eight-case diagnostic registration required')
    require(plan['baseline']['summary_path'] == str(BASELINE) and
        plan['fixed_comparator']['canonical_eight_gates'] == screen.GATE_DEFINITIONS and
        plan['resource_limits'] == dict(max_seconds=600,CPU_count=1,RSS_bytes=3*GIB,
            minimum_free_disk_bytes=2*GIB,max_added_bytes=2*GIB), 'Fixed baseline, gates and resource policy required')
    for mesh,run in RUNS.items():
        rows = [r for r in plan['cases'] if r['mesh_label'] == mesh]
        require(sorted(r['n_pads'] for r in rows) == [4,8,12,16], 'Exact four physical pad counts per mesh required')
        for row in rows:
            ident = f'grouped-strip225-gap1-p{row["n_pads"]:02d}-xy'+('40' if mesh == 'coarse' else '80')
            require(row['case_id'] == ident and row['summary_path'] == str(run/'postprocess'/ident/'summary.json'),
                'Source path/case identity differs')
    for row in [plan['baseline'],*plan['cases']]:
        current=inventory(row['summary_path'],fields=row['native_fields_required'])
        require(all(current[k] == row[k] for k in current),'Preregistered source metadata binding differs')
        require(all(plan['source_and_input_sha256'].get(p) == h for p,h in current['inputs_sha256'].items()),
            'Preregistration omitted source-native hash bindings')
    require(all(plan['source_and_input_sha256'].get(p) == h and sha(p) == h
        for p,h in plan['implementation_sha256'].items()),'Implementation pins omitted or changed')
    for p, expected_sha in plan['source_and_input_sha256'].items():
        require(sha(p) == expected_sha, 'Preregistered input changed: '+p)
    return plan


def native_matrix(summary, kind, frequency, shape, refs):
    path = native_path(summary,f'{kind}-{frequency}.bin'); expected = summary['input_sha256'][str(path)]
    require(sha(path) == expected, 'Native matrix input SHA changed')
    maximum = math.prod(shape)*16
    require(maximum <= 100*1024**2, 'Bounded native matrix allocation required')
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path,'rb') as stream: raw = stream.read(maximum+1)
    require(len(raw) == maximum, 'Native complex128 byte count differs')
    a = np.frombuffer(raw,dtype='<c16').reshape(shape)
    require(np.isfinite(a).all(), 'Finite native matrix required'); refs[str(path)] = expected
    return a


def complex_receipt(a):
    a = np.asarray(a,complex)
    return dict(real=a.real.tolist(),imaginary=a.imag.tolist())


def currents_from_arrays(density, source, contacts, coefficients, nodes):
    """Physical contact integration; output currents and common return are distinct."""
    n = len(nodes); labels = np.asarray(contacts['pad'],int); areas = np.asarray(contacts['area_m2'],float)
    require(density.shape == (2,len(labels)) and source.shape == (2,2) and coefficients.shape == (2,)
        and set(labels) == set(range(n)) and np.all(areas > 0), 'Explicit physical pads, positive contact areas and two output matrices required')
    require(all(np.isfinite(a).all() for a in (density,source,coefficients,areas)), 'Finite actual-frequency matrices required')
    d = coefficients@density
    pads = np.array([np.sum(d[labels == p]*areas[labels == p]) for p in range(n)])
    outputs = source@coefficients
    driven = np.array([sum(pads[p] for p in range(n) if nodes[p] == node) for node in (0,1)])
    ground = sum(pads[p] for p in range(n) if nodes[p] == -1)
    denominator = max(float(abs(pads).sum()),float(abs(outputs).sum()),1e-30)
    error = max(float(abs(driven-outputs).max()),float(abs(pads.sum())),float(abs(ground+outputs.sum())))/denominator
    require(error <= screen.NATIVE_GATES['max_current_error'], 'Integrated pad/output/common-GND current conservation failed')
    return dict(physical_pad_current_peak_A=complex_receipt(pads),output_current_peak_A=complex_receipt(outputs),
        common_GND_return_current_peak_A=complex_receipt(np.array([ground])),
        loaded_output_metal_voltage_peak_V=complex_receipt(.5*coefficients-50*outputs),
        conservation_relative_error=error,conservation_limit=screen.NATIVE_GATES['max_current_error']),pads,outputs


def skin_values_from_field(field,frequency,grid,config):
    require(field.shape == (len(grid),3) and np.isfinite(field).all(), 'Finite combined actual-frequency field required')
    layers = np.asarray(grid['layer'],int)
    gamma = np.array([float(config[k+'.sigma'])+2j*math.pi*frequency*EPS0*float(config[k+'.epsilon_r'])
        for k in ('sc','dermis','fat','muscle')])[layers]
    require(np.all(gamma.real > 0) and np.all(gamma.imag >= 0), 'Passive actual-frequency admittivity required')
    energy = np.sum(abs(field)**2,axis=1)/2
    return dict(total=abs(gamma)**2*energy,conductive=gamma.real**2*energy)


def nearest_pad_edge(x,y,pads):
    distances = []
    for pad in pads:
        dx,dy = abs(x-pad['x_mm'])-pad['width_mm']/2,abs(y-pad['y_mm'])-pad['height_mm']/2
        d = math.hypot(max(dx,0),max(dy,0)) if max(dx,dy) >= 0 else min(-dx,-dy)
        distances.append(d)
    index = int(np.argmin(distances))
    return dict(physical_pad_id=index,XY_projection_distance_to_analytic_pad_edge_mm=float(distances[index]),
        interpretation='XY projection only; native tissue cell center is not a contact-edge surface sample')


def skin_hotspots(squared,grid,pads,saved):
    result = {}
    for name,mask in [('SC',grid['layer'] == 0),('dermis',grid['layer'] == 1),('skin_SC_plus_dermis',grid['layer'] <= 1)]:
        require(np.any(mask),'Required native tissue region missing')
        result[name] = {}
        for kind,energy in squared.items():
            values = np.sqrt(energy); weights = np.where(mask,grid['volume_m3'],0.)
            stats = volume.weighted_statistics(values,weights)
            expected = saved['regions'][name][kind]
            for key,stat in [('J_vector_RMS_max_A_m2','max'),('J_vector_RMS_p95_A_m2','p95')]:
                require(math.isclose(stats[stat],expected[key],rel_tol=1e-10,abs_tol=1e-12),
                    'Saved full-skin '+name+'/'+kind+'/'+key+' does not reproduce')
            location = volume.hotspot(values,weights,grid)
            x,y,_ = location['center_xyz_mm']; location.update(nearest_pad_edge(x,y,pads))
            result[name][kind] = dict(J_vector_RMS_max_A_m2=stats['max'],J_vector_RMS_p95_A_m2=stats['p95'],
                hotspot=location,saved_audit_statistics_reproduced=True)
    return dict(regions=result,definition='sqrt(sum actual f ||gamma(f) Epeak(f)||^2 /2); total includes displacement current',
        conductive_definition='Re(gamma) E only; contact normal J is reported separately',
        coordinate_system='x/y horizontal; z=0 top, +z depth, native cell centers in mm',
        position_scope='native reconstructed E maximum; neither edge convergence nor continuum maximum established')


def contact_hotspots(j_squared,voltage_squared,contacts,case,saved_metrics):
    """Actual contact-normal density/polarization; preserve partial patch areas."""
    areas=np.asarray(contacts['area_m2'],float);h=case['h_xy_mm'];face=(h/1000)**2
    require(j_squared.shape==voltage_squared.shape==areas.shape and np.all(areas>0)
        and np.isfinite(j_squared).all() and np.isfinite(voltage_squared).all()
        and np.all(j_squared>=0) and np.all(voltage_squared>=0),'Finite per-contact spectral energies required')
    jrms=np.sqrt(j_squared);vrms=np.sqrt(voltage_squared)
    order=np.argsort(jrms,kind='stable');cumulative=np.cumsum(areas[order])
    p95=float(jrms[order[min(int(np.searchsorted(cumulative,.95*cumulative[-1],side='left')),len(order)-1)]])
    metrics=dict(surface_J_RMS_max_A_m2=float(jrms.max()),surface_J_RMS_p95_A_m2=p95,
        contact_voltage_RMS_max_V=float(vrms.max()))
    for key,value in metrics.items():
        require(math.isclose(value,saved_metrics[key],rel_tol=1e-10,abs_tol=1e-12),
            'Actual contact spectral reconstruction disagrees with saved '+key)
    def location(values):
        tied=np.flatnonzero(values==values.max());index=int(tied[0]);row=contacts[index];p=int(row['pad']);pad=case['pads'][p]
        x,y=float(row['x_mm']),float(row['y_mm'])
        bounds=[max(x-h/2,pad['x_mm']-pad['width_mm']/2),min(x+h/2,pad['x_mm']+pad['width_mm']/2),
            max(y-h/2,pad['y_mm']-pad['height_mm']/2),min(y+h/2,pad['y_mm']+pad['height_mm']/2)]
        require(bounds[1]>bounds[0] and bounds[3]>bounds[2],'Contact hotspot physical intersection missing')
        patchx,patchy=(bounds[0]+bounds[1])/2,(bounds[2]+bounds[3])/2
        return dict(contact_patch_index=index,physical_pad_id=p,node=case['pad_node_ids'][p],
            tissue_top_face_center_xyz_mm=[x,y,0.],physical_patch_centroid_xyz_mm=[patchx,patchy,0.],
            physical_patch_bounds_xy_mm=bounds,contact_patch_area_m2=float(areas[index]),
            patch_fraction_of_native_face=float(areas[index]/face),tied_contact_patch_count=len(tied),
            nearest_analytic_pad_edge=nearest_pad_edge(patchx,patchy,case['pads']),
            representation='density is constant on this saved physical pad/top-cell overlap; tissue face center and clipped physical patch centroid are distinct')
    return dict(metrics=metrics,normal_J_RMS_max_location=location(jrms),contact_voltage_RMS_max_location=location(vrms),
        saved_metrics_reproduced=True,
        definitions=dict(normal_J='sqrt(sum actual four spectral lines |c_f @ density_basis_f|² /2), A/m²; contact-area-weighted P95',
            contact_voltage='sqrt(sum actual f |specific_Z_area(f) * normal_density(f)|² /2), V; exact saved interface model',
            interface='existing config z.f.re/im in ohm*m² reused verbatim; no additional Rs subtraction or contact-area scaling',
            uncertainty='PBS-derived modeled interface, not experimentally validated skin contact; not a safety limit',
            locations='native overlap patches; no assumed coincidence of contact J and voltage maxima, no converged edge maximum claim'))


def reconstruct_native(data,refs,deadline):
    item,c,grid = data['item'],data['condition'],data['grid']; summary = item['summary']; case = item['case']
    meta=summary['mesh_metadata']
    require(meta['exporter_kind']=='grouped_native' and meta['exporter_class']=='GroupedPadBasis'
        and meta['frequencies_Hz']==list(FREQUENCIES) and meta['channels']==meta['n_outputs']==2
        and meta['n_pads']==case['n_pads'] and meta['pad_node_ids']==case['pad_node_ids']
        and meta['n_return_nodes']==1 and meta['return_topology']=='common_GND'
        and meta['source_peak_V']==.5 and meta['source_resistance_ohm']==50
        and meta['phasor_convention']=='peak,+jomega_t' and meta['sc_cells']==case['sc_cells']==2
        and meta['bulk_layer_counts']==list(case['bulk_counts'])==[14,14,40]
        and meta['h_xy_mm']==case['h_xy_mm'] and meta['cells']==case['cells']==len(grid),
        'Actual saved grouped native mesh/source/topology contract differs')
    coefficients = waveform.condition_coefficients(c,summary['mesh_metadata'])
    require(tuple(sorted(coefficients)) == FREQUENCIES, 'Exact frozen square fundamental and third harmonic frequencies required')
    squared = {k:np.zeros(len(grid)) for k in ('total','conductive')}; spectra=[]; pad_energy=np.zeros(case['n_pads']); out_energy=np.zeros(2)
    mask_rows = geometry.masks_from_csv(case['mask_file']); mask_receipt=geometry.audit_mask_geometry(mask_rows,case)
    expected_patches = {(p,i,j):a for p,i,j,a in mask_rows}; first_contacts=None;contact_j2=None;contact_v2=None;contact_Z=[]
    for f,coeff in sorted(coefficients.items()):
        require(time.monotonic() < deadline,'Finite diagnostic deadline exceeded')
        path = native_path(summary,f'contacts-{f}.csv'); expected = summary['input_sha256'][str(path)]
        require(sha(path) == expected and path.stat().st_size < 8*1024**2,'Bounded source-bound contacts required'); refs[str(path)] = expected
        contacts = np.atleast_1d(np.genfromtxt(path,delimiter=',',names=True))
        require(contacts.dtype.names == ('pad','x_mm','y_mm','area_m2') and
            all(np.isfinite(contacts[k]).all() for k in contacts.dtype.names),'Exact finite native physical contact columns required')
        if first_contacts is None:
            first_contacts=contacts.copy(); observed={}
            h=case['h_xy_mm']
            for row in contacts:
                i=round((float(row['x_mm'])+25)/h-.5);j=round((float(row['y_mm'])+25)/h-.5);p=int(row['pad'])
                require(float(row['pad']) == p and math.isclose(row['x_mm'],-25+(i+.5)*h,abs_tol=1e-10)
                    and math.isclose(row['y_mm'],-25+(j+.5)*h,abs_tol=1e-10) and (p,i,j) not in observed,'Native contact coordinates/physical IDs differ')
                observed[p,i,j]=float(row['area_m2'])
            require(observed.keys() == expected_patches.keys() and all(math.isclose(a,expected_patches[k],rel_tol=1e-10,abs_tol=1e-25)
                for k,a in observed.items()),'Actual native contacts differ from registered mask patches')
        else: require(np.array_equal(contacts,first_contacts),'Native contact ordering/area differs by frequency')
        density=native_matrix(summary,'density',f,(2,len(contacts)),refs);source=native_matrix(summary,'source',f,(2,2),refs)
        if contact_j2 is None:contact_j2=np.zeros(len(contacts));contact_v2=np.zeros(len(contacts))
        combined_density=coeff@density
        za=complex(float(item['config'][f'z.{f}.re']),float(item['config'][f'z.{f}.im']))
        require(math.isfinite(za.real) and math.isfinite(za.imag) and za.real>0,'Finite passive saved specific contact impedance required')
        contact_j2+=abs(combined_density)**2/2;contact_v2+=abs(za*combined_density)**2/2
        contact_Z.append(dict(frequency_Hz=f,specific_impedance_ohm_m2=complex_receipt(np.array([za])),
            source_config_sha256=meta['config_sha256']))
        current,pad,output=currents_from_arrays(density,source,contacts,coeff,case['pad_node_ids'])
        current['frequency_Hz']=f;current['coefficients']=complex_receipt(coeff);spectra.append(current)
        pad_energy += abs(pad)**2/2;out_energy += abs(output)**2/2
        fields=native_matrix(summary,'field',f,(2,len(grid),3),refs)
        combined=np.einsum('i,inj->nj',coeff,fields,optimize=False)
        energy=skin_values_from_field(combined,f,grid,item['config'])
        for kind in squared:squared[kind]+=energy[kind]
        del fields,combined,energy,density,combined_density
    expected=np.asarray(c['metrics']['source_current_RMS_by_output_mA'])
    require(np.allclose(1000*np.sqrt(out_energy),expected,rtol=1e-10,atol=1e-10),'Reconstructed actual output RMS disagrees with saved metrics')
    expected_pad=np.asarray(c['metrics']['physical_pad_current_RMS_mA'])
    require(np.allclose(1000*np.sqrt(pad_energy),expected_pad,rtol=1e-10,atol=1e-10),'Reconstructed physical pad RMS disagrees with saved metrics')
    skin=skin_hotspots(squared,grid,case['pads'],item['bulk_skin_J'][c['id']])
    contact=contact_hotspots(contact_j2,contact_v2,first_contacts,case,c['metrics']);contact['specific_impedance_by_frequency']=contact_Z
    return dict(mask_geometry=mask_receipt,contact_normal_J_and_voltage=contact,pad_currents=dict(per_frequency=spectra,
        physical_pad_RMS_mA=(1000*np.sqrt(pad_energy)).tolist(),output_RMS_mA=(1000*np.sqrt(out_energy)).tolist(),
        physical_pad_nodes=case['pad_node_ids'],saved_metrics_reproduced=True,
        convention='current entering tissue from each physical metal pad; +jomega_t peak spectra; common GND returns not exclusive output pairs'),skin_J=skin)


def frozen_cutoffs(data):
    return {m:{r+'_'+s:volume.weighted_statistics(data['arrays'][m],data['regions'][r])[s]
        for r in (volume.PRIMARY,volume.SLAB) for s in ('mean','p10')} for m in volume.METRICS}


def normalized_row(data,baseline,cutoffs,deadline):
    item,c=data['item'],data['condition']; burden,currents=volume.burdens(item,c)
    base_burden,base_current=volume.burdens(baseline['item'],baseline['condition'])
    modes=volume.normalization_modes(burden,base_burden,sum(currents),sum(base_current))
    for mode in modes.values():
        require(time.monotonic()<deadline,'Finite scalar diagnostic deadline exceeded')
        scale=mode['amplitude_scale'];mode['source_output_RMS_by_output_mA']=[x*scale for x in currents]
        mode['regions']=volume.summarize_regions(data['arrays'],data['regions'],data['grid'],scale,cutoffs)
        # The generic scalar helper uses historical same-grid wording. This new
        # cross-grid diagnostic explicitly records the true fixed fine source.
        for region in mode['regions'].values():
            for metric in region.values():
                for high in metric['fixed_baseline_threshold_volume'].values():
                    high['comparison']='scaled native scalar >= fixed ORIGINAL FINE square4 cutoff, across both meshes'
    skin=modes['skin_contact_only']
    require(all(skin['normalized_burdens'][k] <= base_burden[k]*(1+1e-12)+1e-15 for k in screen.CAP_DEGREES),
        'Normalized candidate exceeds a fixed fine skin/contact cap')
    return dict(case_id=item['summary']['id'],summary_path=str(item['path']),source_commit=item['registration']['source_commit'],
        config_sha256=item['summary']['mesh_metadata']['config_sha256'],comparison_signature=item['signature'],
        fixed_fine_baseline_summary_path=str(BASELINE),fixed_fine_baseline_cutoffs_V_m=cutoffs,
        primary_ROI_reproduction=data['reproduced'],normalizations=modes,circuit=item['circuit'],
        native_equation_gates={k:dict(value=item['summary']['validation'][k],limit=limit,
            passed=item['summary']['validation'][k] <= limit) for k,limit in screen.NATIVE_GATES.items()},
        mesh=item['summary']['mesh_metadata'],represented_volumes_m3={r:float(w.sum()) for r,w in data['regions'].items()},
        full_source_summary_reference=dict(path=str(item['path']),SHA256=sha(item['path'])),adopted=False)


def pair_comparison(coarse,fine):
    require(coarse['physical_geometry'] == fine['physical_geometry'] and coarse['circuit'] == fine['circuit'],
        'Same physical geometry/topology required; do not call a changed design a pure XY comparison')
    changes={}
    for mode in screen.MODES:
        changes[mode]={}
        for region in (volume.PRIMARY,'surface_0_5','primary_complement'):
            a=coarse['normalizations'][mode]['regions'][region]['maxTIS'];b=fine['normalizations'][mode]['regions'][region]['maxTIS']
            changes[mode][region]={key:dict(coarse=a[key],fine=b[key],fine_minus_coarse=b[key]-a[key],
                fine_relative_to_coarse_percent=100*(b[key]/a[key]-1) if a[key] else None) for key in ('mean','p10','p95','max','CV')}
    ca=coarse['native_diagnostic']['mask_geometry'];fa=fine['native_diagnostic']['mask_geometry']
    return dict(n_pads=coarse['n_pads'],coarse_case_id=coarse['case_id'],fine_case_id=fine['case_id'],
        physical_geometry_identical=True,electrical_metal_node_topology_identical=True,
        represented_pad_area_changes_m2=[b['represented_area_m2']-a['represented_area_m2'] for a,b in zip(ca['pads'],fa['pads'])],
        shared_tissue_top_face_counts=dict(coarse=ca['shared_tissue_top_faces']['count'],fine=fa['shared_tissue_top_faces']['count']),
        common_fixed_fine_comparator=True,absolute_metric_changes=changes,
        active_skin_contact_caps=dict(coarse=coarse['normalizations']['skin_contact_only']['active_skin_contact_caps'],
            fine=fine['normalizations']['skin_contact_only']['active_skin_contact_caps']),
        all_eight_screen_pass=dict(coarse=coarse['all_eight_screen_pass'],fine=fine['all_eight_screen_pass']),
        interpretation='Two XY grids diagnose sensitivity only; .625mm has1.6 cells per1mm physical gap; edge/gap/SC/contact convergence remains open')


def rank_stability(rows):
    result={}
    for mode in screen.MODES:
        result[mode]={}
        for metric in ('mean','p10'):
            orders={mesh:[r['n_pads'] for r in sorted((r for r in rows if r['mesh_label']==mesh),
                key=lambda r:(-r['normalizations'][mode]['regions'][volume.PRIMARY]['maxTIS'][metric],r['n_pads']))]
                for mesh in ('coarse','fine')}
            result[mode][metric]=dict(**orders,order_identical=orders['coarse']==orders['fine'],
                tie_rule='descending actual absolute value, physical pad count only for exact ties; no adoption threshold')
    return result


def build_report(plan,deadline,checkpoint=lambda *a,**k:None):
    refs=dict(plan['source_and_input_sha256']);checkpoint('baseline_loading',current_case='baseline-square15-xy80')
    baseline=volume.load_native(view.load_case(BASELINE));refs.update(baseline['refs'])
    require(ranking.baseline_identity(baseline['item']),'Original fine four-square baseline identity required')
    cutoffs=frozen_cutoffs(baseline);base_row=normalized_row(baseline,baseline,cutoffs,deadline)
    rows=[]
    for declared in plan['cases']:
        checkpoint('loading_saved_native',current_case=declared['case_id'])
        data=volume.load_native(view.load_case(Path(declared['summary_path'])));refs.update(data['refs'])
        item=data['item'];case=item['case']; require(item['physical_model_version']==baseline['item']['physical_model_version'],
            'Tissue/contact physical models differ from fixed fine baseline')
        require(all(math.isfinite(item['summary']['validation'][k]) and 0<=item['summary']['validation'][k]<=v
            for k,v in screen.NATIVE_GATES.items()),'Actual native equation gate failed')
        require(case['h_xy_mm']==(1.25 if declared['mesh_label']=='coarse' else .625), 'Fixed coarse/fine XY identity differs')
        row=normalized_row(data,baseline,cutoffs,deadline)
        row.update(mesh_label=declared['mesh_label'],n_pads=declared['n_pads'],physical_geometry=case['pads'],
            native_diagnostic=reconstruct_native(data,refs,deadline))
        row['canonical_eight_screen']=screen.screen_checks(row,base_row)
        row['all_eight_screen_pass']=all(c['passed'] for c in row['canonical_eight_screen'])
        row['skin_contact_only_J_scaling']=dict(amplitude_scale=row['normalizations']['skin_contact_only']['amplitude_scale'],
            interpretation='All per-frequency currents and native J RMS multiply by this scale; hotspot positions unchanged')
        rows.append(row);checkpoint('case_diagnostic_complete',case_result=row,current_case=declared['case_id'])
        del data
    pairs=[pair_comparison(next(r for r in rows if r['n_pads']==n and r['mesh_label']=='coarse'),
        next(r for r in rows if r['n_pads']==n and r['mesh_label']=='fine')) for n in (4,8,12,16)]
    for p,expected in refs.items(): require(sha(p)==expected,'Diagnostic input changed during execution: '+p)
    return dict(schema='task1-grouped-gap-diagnostic-result-v1',status='complete_diagnostic_not_adopted',created_utc=now(),
        source_commit=plan['source_commit'],inputs_sha256=refs,inputs_unchanged=True,feedback_id='6320375305',
        feedback_status='diagnostic implemented and computed; no independent review or convergence claim',
        baseline=base_row,cases=rows,pairs=pairs,rank_stability=rank_stability(rows),
        fixed_comparator=plan['fixed_comparator'],fixed_fine_baseline_cutoffs_V_m=cutoffs,
        new_PDE_solves=0,native_field_reconstruction='saved complex E source spectra combined; no phi reconstruction or solver',
        raw_probe_status='existing source-bound unloaded native potential Vpp artifact preserved, not recomputed or loaded',
        candidate_adopted=False,mesh_convergence_validated=False,experimental_validation=False,
        holds=['Same numerical operator; no independent solver validation',
            'Two XY grids do not establish SC/XY/bulk/edge/contact convergence',
            'Shared tissue DOFs do not imply metal pad merging or an electrical short',
            'Numerical burden limits/cutoffs do not establish human safety or physiological activation'])


def execute(plan_path,output):
    output=Path(output).resolve(); require(output.is_relative_to(ROOT/'docs') and output.is_dir(),'Existing unique docs output directory required')
    require(not any((output/n).exists() for n in ('execution-attempt.json','summary.json','failure.json')),'Never retry or overwrite an attempted diagnostic')
    ledger_path=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledger_path)
    require(policy.remaining_seconds(ledger)>=600,'Diagnostic admission requires600s remaining authorized time')
    require(shutil.disk_usage(output).free>=2*GIB+32*1024**2,'Preserve2GiB disk reserve and bounded output')
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();deadline=started+600
    state=dict(status='running',pid=os.getpid(),proc_start_ticks=Path('/proc/self/stat').read_text().split()[21],started_utc=now(),phase='verifying')
    write(output/'execution-attempt.json',state,new=True);stop=threading.Event();mutex=threading.RLock();errors=[]
    failure=None;status='failed_preserved';initial_free=shutil.disk_usage(output).free;peak=[0]
    def checkpoint(phase,**extra):
        case_result=extra.pop('case_result',None)
        with mutex:
            state.update(phase=phase,updated_utc=now(),elapsed_seconds=time.monotonic()-started,**extra)
            if case_result is not None: write(output/(case_result['case_id']+'.json'),case_result,new=True)
            write(output/'checkpoint.json',state)
    def interrupt(signum,frame): raise RuntimeError(errors[0] if errors else 'Controlled diagnostic signal '+str(signum))
    old={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGUSR1,signal.SIGALRM)}
    for sig in old:signal.signal(sig,interrupt)
    def monitor():
        last=0.
        while not stop.wait(.25):
            try:
                rss=int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE');peak[0]=max(peak[0],rss)
                free=shutil.disk_usage(output).free;t=time.monotonic()
                require(rss<3*GIB and free>=2*GIB and initial_free-free<=2*GIB,'Existing RSS/disk resource limit exceeded')
                require(t<deadline,'Finite600s diagnostic deadline exceeded')
                require(not any((output/name).exists() for name in ('STOP','needs_attention','needs_physical_validation')),'Controlled diagnostic stop marker')
                if t-last>=5:
                    with mutex:write(output/'heartbeat.json',dict(state,observed_utc=now(),RSS_bytes=rss))
                    last=t
            except BaseException as error:
                errors.append(type(error).__name__+': '+str(error));os.kill(os.getpid(),signal.SIGUSR1);return
    thread=threading.Thread(target=monitor,daemon=True);thread.start();signal.setitimer(signal.ITIMER_REAL,600)
    try:
        plan_sha=sha(plan_path);plan=verify_plan(plan_path)
        require(plan['resource_policy_refs']==policy.policy_refs(ledger),'Resource authorization changed')
        result=build_report(plan,deadline,checkpoint)
        require(sha(plan_path)==plan_sha,'Diagnostic preregistration changed');verify_plan(plan_path)
        result.update(preregistration=dict(path=str(Path(plan_path).resolve()),SHA256=plan_sha),
            resources=dict(wall_seconds=time.monotonic()-started,max_seconds=600,CPU_count=1,new_PDE_solves=0,
                peak_RSS_bytes=max(peak[0],resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),
                global_limit_seconds=policy.effective_limit(ledger)))
        write(output/'summary.json',result,new=True);status=result['status'];checkpoint('complete',status=status);return result
    except BaseException as error:
        failure=type(error).__name__+': '+str(error)
        write(output/'failure.json',dict(status=status,error=failure,phase=state['phase'],current_case=state.get('current_case'),
            new_PDE_solves=0,partial_evidence_preserved=True,automatic_retry=False,
            resume_condition='Inspect exact failed input/guard and preregister a new output; never overwrite this attempt'),new=True)
        checkpoint('failed_preserved',status=status);raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=1)
        elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
        ledger['runs'].append(dict(run_id=output.name,stage='grouped_gap_saved_field_diagnostic',seconds=elapsed,status=status,error=failure,finished_utc=now()))
        write(ledger_path,ledger)
        for sig,handler in old.items():signal.signal(sig,handler)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--preregistration',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    with policy.execution_lock(ROOT/'runtime/task1-budget.json'):
        if args.prepare:
            require(args.preregistration is None and not args.output.exists() and args.output.parent.is_dir()
                and args.output.resolve().is_relative_to(ROOT/'docs'),'New docs directory required for registration')
            plan=make_preregistration();args.output.mkdir();write(args.output/'preregistration.json',plan,new=True)
            print(json.dumps(dict(status='prepared',output=str(args.output.resolve()),new_PDE_solves=0)))
        else:
            require(args.preregistration is not None,'Explicit preregistration required')
            result=execute(args.preregistration,args.output);print(json.dumps(dict(status=result['status'],cases=len(result['cases']))))


if __name__ == '__main__': main()
