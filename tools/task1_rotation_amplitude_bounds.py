#!/usr/bin/env python3
"""JSON-only bounds for one fixed discrete positive two-amplitude family.

No PDE/native arrays, geometry sweep, drive candidate, global physical or
physiological impossibility claim. An unproved interval remains inconclusive.
"""
from __future__ import annotations
import argparse
import fcntl
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
import task1_cloud_batch as core
import task1_candidate_screen as screen
import task1_resource_policy as policy

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
SCHEMA = 'task1-rotation-amplitude-bounds-preregistration-v1'
SOURCE_SUMMARY = ROOT/'docs/cloud-rotation-ratio-20261021T180500Z/summary.json'
ROTATION_RUN = 'cloud-one-return-rotation-20261021T174000Z'
ROTATION_ID = 'asym-return2-rot90-xy80'
ROTATION_SUMMARY = ROOT/'data-native'/ROTATION_RUN/'postprocess'/ROTATION_ID/'summary.json'
ROTATION_AUDIT = ROOT/'data-native'/ROTATION_RUN/'audit'/(ROTATION_ID+'.json')
BASELINE_SUMMARY = ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json'
PRIMARY = 'primary_r5_depth15_20'
FREQUENCIES = (3000,3030,9000,9090)
CONDITIONS = (('rotation-ratio-o0-half',[.5,1.]),('rotation-ratio-o0-sqrt-half',[2**-.5,1.]),
              ('rotation-ratio-o1-sqrt-half',[1.,2**-.5]),('rotation-ratio-o1-half',[1.,.5]))
POWER_CAPS = ('SC_power_W','contact_power_W','skin_SC_plus_dermis_power_W')
ARITHMETIC_RELATIVE = 1e-8
ARITHMETIC_ABSOLUTE = 1e-8
IDENTITY_RELATIVE = 1e-10
IDENTITY_ABSOLUTE = 1e-14


def require(ok,message):
    if not ok: raise ValueError(message)


def number(x): return type(x) in (int,float) and math.isfinite(x)
def error(x): return ARITHMETIC_ABSOLUTE+ARITHMETIC_RELATIVE*abs(x)
def lower(x): return max(0.,math.nextafter(x-error(x),-math.inf))
def upper(x): return math.nextafter(x+error(x),math.inf)
def close(a,b): return math.isclose(a,b,rel_tol=IDENTITY_RELATIVE,abs_tol=IDENTITY_ABSOLUTE)


def exclusive_square_coefficients(coefficients,amplitudes):
    require(len(amplitudes)==2 and all(number(v) and v>0 for v in amplitudes),'Two positive actual sourceVpp values required')
    require(set(coefficients)==set(map(str,FREQUENCIES)),'Exactly four exclusive carrier/harmonic coefficients required')
    for f in FREQUENCIES:
        row=coefficients[str(f)]; real=row['real']; imaginary=row['imaginary']
        require(len(real)==len(imaginary)==2 and all(number(x) for x in real+imaginary),'Finite complex source vectors required')
        output=0 if f in (3000,9000) else 1
        factor=3/(2*math.sqrt(2)) if f in (3000,3030) else 1/(2*math.sqrt(2))
        for j in range(2):
            expected=-factor*amplitudes[j] if j==output else 0.
            require(abs(real[j])<=1e-15 and math.isclose(imaginary[j],expected,rel_tol=0,abs_tol=1e-15),
                'Only phase0 exclusive square3h source assignment is covered by this bound')


def unit_power_contributions(losses,amplitudes):
    """Passive distinct-frequency powers divide by actual sourceVpp squared."""
    require(len(amplitudes)==2 and all(number(v) and v>0 for v in amplitudes),'Positive source amplitudes required')
    rows=losses['per_frequency'];require(len(rows)==4 and {r['frequency_Hz'] for r in rows}==set(FREQUENCIES),
        'Exactly all four actual per-frequency loss receipts required')
    require(losses.get('actual_active_harmonics_included') is True and losses.get('no_extra_peak_RMS_factor_applied') is True,
        'Existing average-power coefficients and actual harmonics required; no extra factor1/2')
    groups=[{key:0. for key in POWER_CAPS} for _ in range(2)]
    for row in rows:
        v=row['layer_contact_resistor_losses_W']
        require(len(v)==6 and all(number(x) for x in v),'Finite six-compartment powers required')
        require(all(x>=0 for x in v),'Passive nonnegative frequency losses required for the outer bound')
        native_power_gate=core.GATES['max_power_error']
        require(number(row['source_power_W']) and row['source_power_W']>=0 and
            number(row.get('power_balance_relative_error')) and 0<=row['power_balance_relative_error']<=native_power_gate and
            abs(sum(v)-row['source_power_W'])<=native_power_gate*max(abs(row['source_power_W']),1e-20),
            'Original per-frequency2e-7 power-conservation gate failed')
        output=0 if row['frequency_Hz'] in (3000,9000) else 1
        for key,value in zip(POWER_CAPS,(v[0],v[4],v[0]+v[1])):
            groups[output][key]+=value/amplitudes[output]**2
    for key in POWER_CAPS:
        reconstructed=sum(groups[j][key]*amplitudes[j]**2 for j in range(2))
        require(close(reconstructed,losses['metrics'][key]),'Grouped frequency/total compartment power identity failed')
    return groups


def crosscheck_unit_powers(samples):
    require(len(samples)==5,'Four ratio conditions and the cached1/1 power control required')
    detailed=[s for s in samples if 'losses' in s]
    require(4<=len(detailed)<=5,'All four ratio per-frequency power receipts are required')
    estimates=[unit_power_contributions(s['losses'],s['source_Vpp_by_output']) for s in detailed]
    proof=[]; bounds=[{} for _ in range(2)]
    for output in range(2):
        for key in POWER_CAPS:
            values=[p[output][key] for p in estimates]
            require(all(close(v,values[0]) for v in values),'Source-unit compartment power changed across fixed geometry/drive family')
            bounds[output][key]=dict(lower_W=lower(min(values)),upper_W=upper(max(values)),values_W=values)
            proof.append(dict(output_index=output,metric=key,values_W=values,passed=True))
    for sample in samples:
        if 'cached_total_powers' not in sample: continue
        require(sample['source_Vpp_by_output']==[1.,1.],'Only cached1/1 may use total-power fallback')
        for key in POWER_CAPS:
            total=sample['cached_total_powers'][key]
            require(number(total) and total>=0 and all(close(p[0][key]+p[1][key],total) for p in estimates),
                    'Unit output contributions do not reproduce cached1/1 compartment total')
            proof.append(dict(output_index=None,metric=key,cached_total_W=total,
                crosscheck_scope='Sum of independently recovered output0+output1 unit powers versus cached1/1 total; no unavailable per-output control value fabricated',passed=True))
    return bounds,proof


def family_bounds(baseline_target,baseline_surface,equal_surface,half_targets,power_caps,unit_bounds):
    """Conditional theorem on cached scalar tolerances; arbitrary common A>0."""
    values=[baseline_target,baseline_surface,equal_surface,*half_targets,*power_caps.values()]
    require(all(number(v) and v>0 for v in values) and len(half_targets)==2,'Positive finite cached scalars/caps required')
    # Include the existing screen's permissive numerical tolerance as well as
    # outward arithmetic guard; we do not silently tighten the accepted gates.
    target_required=max(0.,lower(baseline_target)-screen.tolerance(baseline_target))
    surface_allowed=upper(baseline_surface)+screen.tolerance(baseline_surface)
    require(target_required>0,'Conservative baseline mean threshold unresolved')
    allowed_ratio=upper(surface_allowed/target_required)
    branches=[]
    for variable_output,half_target in enumerate(half_targets):
        # For l<=t<=u: T(t)<=t/l*T(l), S(t)>=t/u*S(u).
        # A cancels. This is a necessary ratio constraint for every common A,
        # regardless of which of the eight burden constraints would be active.
        ratio_lower=lower(.5*lower(equal_surface)/upper(half_target))
        inner_excluded=ratio_lower>allowed_ratio
        constant_output=1-variable_output; cap_rows=[]
        for key in POWER_CAPS:
            p=unit_bounds[constant_output][key]['lower_W']
            if p<=0:
                cap_rows.append(dict(metric=key,usable=False,reason='Positive constant-output power not resolved by outward arithmetic bound'))
                continue
            common_upper=upper(math.sqrt(upper(power_caps[key])/p))
            cap_rows.append(dict(metric=key,usable=True,constant_output=constant_output,
                constant_unit_power_lower_W=p,baseline_cap_upper_W=upper(power_caps[key]),common_A_upper=common_upper))
        usable=[r for r in cap_rows if r['usable']]
        amplitude_upper=min((r['common_A_upper'] for r in usable),default=None)
        target_upper=upper(upper(half_target)*amplitude_upper) if amplitude_upper is not None else None
        outer_excluded=target_upper is not None and target_upper<target_required
        branches.append(dict(variable_output=variable_output,constant_output=constant_output,
            parameterization='A*[t,1]' if variable_output==0 else 'A*[1,t]',common_A='arbitrary positive, no1Vpp ceiling assumed',
            inner=dict(interval_t=[.5,1.],endpoints='both included',surface_over_target_lower_bound=ratio_lower,
                baseline_allowed_ratio_upper_bound=allowed_ratio,excluded=inner_excluded,
                proof='coordinatewise monotone+degree1 homogeneous: S/T >=(l/u)*S(u)/T(l),l=.5,u=1; commonA cancels'),
            outer=dict(interval_t=[0.,.5],endpoints='both open; t=.5 covered by inner',
                constant_output_power_caps=cap_rows,common_A_upper=amplitude_upper,target_mean_upper_V_m=target_upper,
                target_mean_required_lower_V_m=target_required,excluded=outer_excluded,
                proof='T(t)<=T(.5); Pj(A,t)=A²*(t²Pvariable,j+Pconstant,j)>=A²Pconstant,j; combine3necessary power caps'),
            branch_excluded=inner_excluded and outer_excluded))
    passed=all(b['branch_excluded'] for b in branches)
    return dict(overall_proof_passed=passed,conclusion='excluded_fixed_discrete_positive_amplitude_family' if passed else 'inconclusive',
        branches=branches,zero_amplitude_endpoints=dict(basic_two_carrier_maxTIS=0,
            scope='Analytic endpoint; carrierRMS need not be zero and no physiological inference is made'),
        baseline_mean_required_lower_V_m=target_required,baseline_surface_p95_allowed_upper_V_m=surface_allowed,
        necessary_conditions_only='Targetmean retention andsurfaceP95 plus3of8skin caps. If this subset is impossible, simultaneous8gate/8cap acceptance is also impossible in the stated fixed family.',
        arithmetic_guard=dict(relative=ARITHMETIC_RELATIVE,absolute=ARITHMETIC_ABSOLUTE,
            unit='Applied outward separately in the units of each scalar,ratio,power andamplitude; conservative numerical diagnostic, not model uncertainty or continuum error bound'))


def json_source(value,refs,expected=None):
    p=Path(value);require(p.is_absolute() and p==p.resolve() and p.is_relative_to(ROOT) and p.is_file()
        and not p.is_symlink() and p.suffix=='.json' and p.stat().st_size<=25*1024**2,'Only canonical bounded JSON evidence is read')
    digest=core.sha(p);require(expected is None or digest==expected,'JSON source hash mismatch: '+str(p))
    obj=core.read(p);require(core.sha(p)==digest,'JSON changed while reading');refs[str(p)]=digest
    return obj


def raw_metric(row,raw,region,stat): return row['normalizations'][raw]['regions'][region]['maxTIS'][stat]


def source_bundle(refs):
    summary=json_source(SOURCE_SUMMARY,refs)
    require(summary['schema']=='task1-rotation-drive-ratio-scout-v1' and summary['status']=='calculated_unadopted' and
        summary['inputs_unchanged'] is True and summary['new_PDE']==0 and summary['waveform']=='square_3h' and
        summary['actual_fundamental_Hz']==[3000,3030] and summary['all_active_frequencies_Hz']==list(FREQUENCIES),
        'Exact completed fixed-rotation four-ratio square3h source required')
    require([(r['id'],r['source_Vpp_by_output']) for r in summary['conditions']]==list(CONDITIONS),'Exact four saved amplitude vectors required')
    geometry=summary['source_geometry'];require(geometry['source_run_id']==ROTATION_RUN and geometry['source_case_id']==ROTATION_ID
        and geometry['summary_path']==str(ROTATION_SUMMARY),'Fixed one-return90 source geometry required')
    source=json_source(ROTATION_SUMMARY,refs,summary['input_sha256'][str(ROTATION_SUMMARY)])
    baseline=json_source(BASELINE_SUMMARY,refs,summary['input_sha256'][str(BASELINE_SUMMARY)])
    native_pre_path=ROOT/'data-native'/ROTATION_RUN/'preregistration.json'
    native_pre=json_source(native_pre_path,refs,summary['input_sha256'][str(native_pre_path)])
    case=next(c for c in native_pre['cases'] if c['id']==ROTATION_ID)
    require(case['config_sha256']==geometry['configuration_sha256'] and case['mask_sha256']==geometry['mask_sha256'] and
        case['applied_physical_rotation_deg']==90 and case['rotated_physical_pad_id']==2 and case['rotation_only_contrast'] is True,
        'Completed one-return90 configuration/mask identity required')
    circuit=case['circuit'];require(circuit['n_pads']==4 and circuit['n_outputs']==2 and circuit['n_return_nodes']==1 and
        circuit['source_resistance_ohm']==50 and circuit['pad_to_node']=={'0':'out0','1':'out1','2':'GND','3':'GND'},'Fixed4pad2output/commonGND50ohm scope required')
    condition=next(c for c in source['conditions'] if c['id']==ROTATION_ID+'-square_3h')
    require(condition['waveform']=='square_3h' and condition['phase_deg']==[0.,0.] and condition['carrier_group']==[0,1]
        and condition['source_Vpp_per_output']==1. and condition['actual_fundamental_Hz']==[3000,3030], 'Cached equal-drive exclusive phase0 square control required')
    for post in (source,baseline):
        meta=post['mesh_metadata'];require(meta['h_xy_mm']==.625 and meta['sc_cells']==2 and meta['bulk_layer_counts']==[14,14,40]
            and meta['cells']==351680 and meta['radius_mm']==25 and meta['tissue_boundaries_mm']==[0,.1,5.1,10.1,25.1], 'Fixed D50/layers/SC2/XY.625/bulk grid required')
    report=json_source(geometry['cached_control_volume']['path'],refs,geometry['cached_control_volume']['SHA256'])
    require(report['status']=='calculated_unadopted' and report['inputs_unchanged'] is True,'Actual source-bound cached control volume required')
    controls=summary['cached_controls']
    for key,post_path in [('canonical_original_square',BASELINE_SUMMARY),('rotation_equal_drive',ROTATION_SUMMARY)]:
        rows=[r for r in report['cases'] if r['summary_path']==str(post_path)]
        require(len(rows)==1 and rows[0]==controls[key] and report['inputs_sha256'][str(post_path)]==refs[str(post_path)],'Cached raw control/source binding differs')
        require(rows[0]['normalizations']['raw_1Vpp']['amplitude_scale']==1.,'Raw cached control must retain actual1/1Vpp')
    audit=json_source(ROTATION_AUDIT,refs,summary['input_sha256'][str(ROTATION_AUDIT)])
    require(audit['status']=='computed_spatial_and_skinJ_audit' and audit['native_inputs_unchanged'] is True and
        audit['config_sha256']==case['config_sha256'] and audit['summary_sha256']==refs[str(ROTATION_SUMMARY)] and
        audit['registration_sha256']==refs[str(native_pre_path)],'Cached equal-drive six-loss audit provenance differs')
    losses=next(r.get('layer_contact_source_losses',{}) for r in audit['conditions'] if r['condition_id']==condition['id'])
    if 'per_frequency' in losses:
        samples=[dict(id='cached-rotation-equal',source_Vpp_by_output=[1.,1.],losses=losses)]
    else:
        raw_powers=controls['rotation_equal_drive']['normalizations']['raw_1Vpp']['normalized_burdens']
        samples=[dict(id='cached-rotation-equal',source_Vpp_by_output=[1.,1.],cached_total_powers={k:raw_powers[k] for k in POWER_CAPS})]
    conditions=[]
    source_geometry=condition['volume_metrics']['geometry'];cutoffs=None
    for row,(ident,amplitudes) in zip(summary['conditions'],CONDITIONS):
        artifact=row['artifacts']['condition.json'];p=Path(artifact['path'])
        require(p==SOURCE_SUMMARY.parent/ident/'condition.json','Only declared conditionJSON artifact is consumed')
        c=json_source(p,refs,artifact['SHA256'])
        require(c['schema']=='task1-rotation-drive-ratio-condition-v1' and c['status']=='calculated_unadopted' and c['id']==ident and
            c['source_Vpp_by_output']==amplitudes and c['source_case_id']==ROTATION_ID and c['source_run_id']==ROTATION_RUN and
            c['configuration_sha256']==case['config_sha256'] and c['waveform']=='square_3h' and c['actual_fundamental_Hz']==[3000,3030] and
            c['active_frequencies_Hz']==list(FREQUENCIES) and c['source_geometry_unchanged'] is True and c['new_PDE']==0,
            'Saved ratio condition changes source geometry/circuit/frequency/waveform identity')
        exclusive_square_coefficients(c['coefficient_vectors'],amplitudes)
        require(c['native_volume_metrics']['total_sampled_directions']==2074 and c['native_volume_metrics']['geometry']==source_geometry,
            'Same fixed2074 sampled directions/ROI/positive-volume weighting required')
        require(c['source_waveform']['actual_source_Vpp_by_output']==amplitudes and c['source_waveform']['source_waveform_check_passed'] is True,
            'Actual analytic square sourceVpp proof required')
        if cutoffs is None:cutoffs=c['shared_original_square_cutoffs_V_m']
        require(c['shared_original_square_cutoffs_V_m']==cutoffs,'Common baseline cutoff contract differs')
        samples.append(dict(id=ident,source_Vpp_by_output=amplitudes,losses=c['layer_contact_source_losses']));conditions.append(c)
    original=controls['canonical_original_square'];rotated=controls['rotation_equal_drive'];reference=summary['canonical_square_reference']
    caps=reference['burdens'];require(original['normalizations']['raw_1Vpp']['normalized_burdens']==caps,'Original canonical eight-cap reference differs')
    t0=raw_metric(original,'raw_1Vpp',PRIMARY,'mean');s0=raw_metric(original,'raw_1Vpp','surface_0_5','p95')
    require(close(t0,reference['screen_baseline']['normalizations']['skin_contact_only']['regions'][PRIMARY]['maxTIS']['mean']) and
        close(s0,reference['screen_baseline']['normalizations']['skin_contact_only']['regions']['surface_0_5']['maxTIS']['p95']), 'Same existing screen baseline mean/surfaceP95 required')
    return dict(baseline_target=t0,baseline_surface=s0,equal_surface=raw_metric(rotated,'raw_1Vpp','surface_0_5','p95'),
        half_targets=[raw_metric(conditions[i],'raw_declared_Vpp',PRIMARY,'mean') for i in (0,3)],
        power_caps={k:caps[k] for k in POWER_CAPS},power_samples=samples,
        source_configuration_sha256=case['config_sha256'],fixed_ROI=source_geometry,shared_original_cutoffs=cutoffs,
        circuit=circuit,native_fields_configuration_or_archive_bytes_revalidated=False)


def implementation_receipt():
    paths=(Path(__file__).resolve(),ROOT/'tests/test_task1_rotation_amplitude_bounds.py',Path(core.__file__).resolve(),Path(screen.__file__).resolve(),Path(policy.__file__).resolve())
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for p in paths: require(p.read_bytes()==subprocess.check_output(['git','show',commit+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT),'Commit bound implementation/helpers/tests before preparation')
    return dict(implementation_git_commit=commit,implementation_files_sha256={str(p):core.sha(p) for p in paths})


def metric_definition_evidence(refs):
    run=ROOT/'data-native'/ROTATION_RUN
    manifest=json_source(run/'frozen-source-manifest.json',refs)['files']
    result=[]
    for name,needles in [('selectivity_volume.py',('dirs = directions(fibonacci_count)','np.minimum(projected_a, projected_b, out=projected_a)')),
                         ('explore_tis.py',('def directions(',))]:
        original=str(ROOT/'tis-java'/name);entry=manifest[original];p=Path(entry['path'])
        require(p.is_absolute() and p==p.resolve() and p.is_relative_to(ROOT) and p.suffix=='.py' and p.is_file()
            and not p.is_symlink() and p.stat().st_size<2*1024**2 and core.sha(p)==entry['sha256'], 'Frozen metric definition code must match native source manifest')
        text=p.read_text();locations=[]
        for needle in needles:
            at=text.find(needle);require(at>=0,'Frozen scalar definition differs from reviewed monotone sampled-direction metric')
            locations.append(dict(literal=needle,line=text[:at].count('\n')+1))
        refs[str(p)]=entry['sha256'];result.append(dict(path=str(p),SHA256=entry['sha256'],locations=locations))
    return dict(code=result,directions='26 fixed +2048 Fibonacci directions, total2074; no amplitude-dependent direction selection',
        metric='At each cached native cell max_n2min(a|n.E3000|,b|n.E3030|); positive fixed weightedmean andweighted inverse-ECDFP95 inherit monotonicity anddegree1 homogeneity',
        native_arrays_read=False)


def make_preregistration(output,decision_path,feedback_path):
    refs={};decision=json_source(decision_path,refs);feedback=json_source(feedback_path,refs)
    require(decision.get('schema')=='task1-rotation-amplitude-bound-root-decision-v1' and decision.get('status')=='selected_not_executed' and
        decision.get('root_selected') is True and decision.get('peer_endorsed') is False and decision.get('new_PDE')==0 and
        isinstance(decision.get('question'),str) and decision['question'].strip(),'Root-selected bounded JSON-only scientific question required')
    require(decision['source_summary']==dict(path=str(SOURCE_SUMMARY),SHA256=core.sha(SOURCE_SUMMARY)) and
        decision['feedback']==dict(path=str(Path(feedback_path)),SHA256=refs[str(Path(feedback_path))]), 'Exact source summary and actual feedback context pins required')
    require(feedback.get('schema')=='task1-queue-feedback-v1' and feedback.get('status')=='read_only_feedback_checked' and feedback.get('error') is None
        and feedback.get('new_PDE')==0 and feedback.get('messages_sent')==0 and feedback.get('public_GitHub_only') is True and feedback.get('peer_agreement_inferred') is False,
        'Actual public read-only feedback context required')
    require(isinstance(decision.get('input_sha256'),dict) and decision['input_sha256'],'Completed JSON decision evidence required')
    for p,digest in decision['input_sha256'].items(): json_source(p,refs,digest)
    source_bundle(refs)  # Validate scope/hash provenance, not bounds or field arrays.
    definitions=metric_definition_evidence(refs)
    implementation=implementation_receipt();refs.update(implementation['implementation_files_sha256']);ledger=policy.load_ledger();refs.update(policy.policy_refs(ledger))
    return dict(schema=SCHEMA,status='preregistered_not_executed',created_utc=core.now(),output_directory=str(output),
        source_summary=str(SOURCE_SUMMARY),input_sha256=refs,metric_definition_evidence=definitions,root_selection=dict(decision=dict(path=str(decision_path),SHA256=refs[str(Path(decision_path))]),
            feedback=dict(path=str(feedback_path),SHA256=refs[str(Path(feedback_path))]),root_selected=True,peer_endorsed=False),
        inner_interval=[.5,1.],outer_interval=[0.,.5],common_amplitude='arbitrary A>0, not limited to maximum skin-cap normalization',
        fixed_gate_definitions=screen.GATE_DEFINITIONS,fixed_skin_cap_degrees=screen.CAP_DEGREES,
        arithmetic_tolerance=dict(relative=ARITHMETIC_RELATIVE,absolute=ARITHMETIC_ABSOLUTE),
        power_identity_tolerance=dict(relative=IDENTITY_RELATIVE,absolute=IDENTITY_ABSOLUTE),
        inherited_native_power_conservation_gate=core.GATES['max_power_error'],
        new_PDE=0,native_arrays_read=False,resource_limits=dict(CPU_count=1,total_seconds=60,RSS_bytes=3*GIB,free_disk_bytes=2*GIB,cumulative_seconds=policy.effective_limit(ledger)),
        scope='Conditional bound only for fixed one-return90 geometry,SC2/XY.625/bulk14/14/40,nominal tissue/contact,2074directions,fixedpositive ROIweights,exclusive square3h phase0/0,two50ohmoutputs/commonGND',
        holds=['No geometry/globalphysical/continuous-direction/continuum/convergence/hardware/experimental/activation/safety impossibility claim',
            'The mathematical implication is conditional on the cached discrete scalar/power identities within stated outward arithmetic tolerance; unproved intervals remain inconclusive'],**implementation)


def verify_plan(p,output,expected=None):
    refs={};plan=json_source(p,refs);digest=refs[str(Path(p))]
    require(expected is None or digest==expected,'Bound preregistration changed')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed' and plan['output_directory']==str(output) and plan['source_summary']==str(SOURCE_SUMMARY)
        and plan['new_PDE']==0 and plan['native_arrays_read'] is False and plan['fixed_gate_definitions']==screen.GATE_DEFINITIONS and plan['fixed_skin_cap_degrees']==screen.CAP_DEGREES,
        'Exact fixed discrete family/gates required')
    for name,d in plan['input_sha256'].items():
        path=Path(name);require(path.suffix in('.json','.py') and path.is_absolute() and path==path.resolve() and path.is_relative_to(ROOT)
            and path.is_file() and not path.is_symlink() and core.sha(path)==d,'Only unchanged small JSON/code evidence is consumed')
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'],'Bound implementation changed')
    return plan,digest


def execute(plan):
    refs={};bundle=source_bundle(refs);units,identity=crosscheck_unit_powers(bundle['power_samples'])
    result=family_bounds(bundle['baseline_target'],bundle['baseline_surface'],bundle['equal_surface'],bundle['half_targets'],bundle['power_caps'],units)
    result.update(schema='task1-rotation-amplitude-bounds-v1',status='completed_bounds_diagnostic',power_unit_identity_checks=identity,
        power_unit_bounds=units,source_scalars={k:bundle[k] for k in ('baseline_target','baseline_surface','equal_surface','half_targets','power_caps')},
        source_configuration_sha256=bundle['source_configuration_sha256'],fixed_ROI=bundle['fixed_ROI'],circuit=bundle['circuit'],
        root_selection=plan['root_selection'],metric_definition_evidence=plan['metric_definition_evidence'],scope=plan['scope'],holds=plan['holds'],new_PDE=0,native_arrays_read=False,
        independent_field_recalculation=False,global_physical_feasibility_inferred=False,candidate_adopted=False)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',type=Path);group.add_argument('--preregistration',type=Path)
    parser.add_argument('--decision',type=Path);parser.add_argument('--feedback',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output
    require(output.is_absolute() and output==output.resolve() and output.is_relative_to(ROOT/'docs') and output.parent.is_dir() and not output.exists(),'New canonical docs output required')
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledger_path)
        require(policy.remaining_seconds(ledger)>=60 and shutil.disk_usage(output.parent).free>=2*GIB+10*1024**2,'Reserve60s and2GiB free+10MiB allowance')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();status='failed_preserved';failure=None;state={};count=0;stop=threading.Event();mutex=threading.RLock();thread=None
        def guard(): require(core.rss(os.getpid())<3*GIB and shutil.disk_usage(output.parent).free>=2*GIB,'Bound diagnostic RSS/disk cap exceeded')
        def checkpoint(phase):
            nonlocal count
            with mutex:
                guard();count+=1;state.update(phase=phase,status=status if phase=='complete' else 'running',pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now(),elapsed_seconds=time.monotonic()-started)
                core.write(output/f'checkpoint-{count:03d}-{phase}.json',dict(state));core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5):
                try:
                    with mutex:guard();core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-started))
                except BaseException as e:state['resource_guard_failure']=str(e);os.kill(os.getpid(),signal.SIGTERM);return
        def interrupted(signum,frame):raise TimeoutError('Finite60s JSON amplitude bound interrupted '+str(signum))
        old={s:signal.getsignal(s) for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for sig in old:signal.signal(sig,interrupted)
        signal.setitimer(signal.ITIMER_REAL,60)
        try:
            if args.prepare:
                require(args.prepare.is_absolute() and args.prepare==args.prepare.resolve() and args.prepare.is_relative_to(ROOT/'docs') and
                    not args.prepare.exists() and not args.prepare.is_relative_to(output),'New external canonical docs preregistration required')
                plan=make_preregistration(output,args.decision,args.feedback);args.prepare.parent.mkdir(parents=True,exist_ok=True)
                with args.prepare.open('x') as stream:stream.write(json.dumps(plan,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
                status='preregistered_not_executed'
            else:
                require(args.decision is None and args.feedback is None,'Frozen selection context only at execution')
                output.mkdir();thread=threading.Thread(target=heartbeat,daemon=True);thread.start();checkpoint('verify_plan');plan,digest=verify_plan(args.preregistration,output)
                checkpoint('json_theorem_bounds');result=execute(plan);verify_plan(args.preregistration,output,digest);guard()
                result.update(implementation_receipt(),inputs_unchanged=True,input_sha256=plan['input_sha256'],preregistration=dict(path=str(args.preregistration),SHA256=digest),
                    resources=dict(wall_seconds=time.monotonic()-started,max_seconds=60,CPU_count=1,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
                core.write(output/'summary.json',result);status=result['status'];checkpoint('complete')
        except BaseException as e:
            failure=type(e).__name__+': '+str(e)
            if output.exists():core.write(output/'failure.json',dict(status=status,error=failure,phase=state.get('phase'),partial_evidence_preserved=True,automatic_retry=False,new_PDE=0))
            elif args.prepare:
                p=args.prepare.with_name(args.prepare.stem+'.failure.json')
                if p.parent.is_dir() and not p.exists():core.write(p,dict(status=status,error=failure,partial_evidence_preserved=True,automatic_retry=False,new_PDE=0))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.name,stage='rotation_amplitude_bounds_prepare' if args.prepare else 'rotation_amplitude_bounds',seconds=elapsed,status=status,error=failure,finished_utc=core.now()));core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for sig,handler in old.items():signal.signal(sig,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
