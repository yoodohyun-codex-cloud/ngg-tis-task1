"""Deferred E13-fine-only cached-native scalar/probe postbatch, no new physics.

No scientific import, arrays, native input reads or work occur on import.  Root
alone may execute after source publication and review of actual fine/ellipse R.
"""
import ast,gc,hashlib,json,math,time
from pathlib import Path
import light_inputs
import high_volume

SOURCE=Path('/dev/shm/task1-E13-fine-light-post-20261025/source')
RUN=Path('/dev/shm/task1-E13-fine-light-post-20261025-run')
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping',
       'same_source_real_power','joint_eight_surface_contact_burden_caps')
MAX_OUTPUT_BYTES=20000000

def require(ok,message):
    if not ok:raise ValueError(message)

def check(guard,deadline):
    guard()
    if deadline is not None and time.monotonic()>=deadline:
        raise TimeoutError('Finite low-RSS native scalar/probe postbatch deadline')

def digest(path,guard=lambda:None,deadline=None):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):
            check(guard,deadline);h.update(block)
    return h.hexdigest()

def verify(descriptor,pins,guard,deadline):
    path=Path(descriptor['path']);require(path.is_file()and not path.is_symlink()
        and path==path.resolve()and path.stat().st_size==descriptor['bytes']
        and pins.get(str(path))==descriptor['SHA256'],'Canonical published native input '+str(path))
    require(digest(path,guard,deadline)==descriptor['SHA256'],'Full SHA before native decode '+str(path))
    return path

def load(np,descriptor,keys,pins,guard,deadline):
    path=verify(descriptor,pins,guard,deadline)
    with np.load(path,allow_pickle=False)as saved:
        require(set(keys).issubset(saved.files),'Actual requested native fields absent; no reconstruction fallback')
        result={key:np.array(saved[key],copy=True)for key in keys}
    require(all(np.isfinite(value).all()for value in result.values()),'Finite complete original native arrays')
    require(digest(path,guard,deadline)==descriptor['SHA256'],'Full SHA after native decode '+str(path))
    return result

def output_budget(out):
    size=sum(p.stat().st_size for p in out.rglob('*')if p.is_file())
    require(size<=MAX_OUTPUT_BYTES,'Finite low-RAM postbatch output bound20MB; preserve partial evidence')
    return size

def new_json(path,value):
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,indent=2)+'\n').encode()
    require(len(raw)<MAX_OUTPUT_BYTES,'Single JSON below whole postbatch output cap')
    with Path(path).open('xb')as stream:stream.write(raw)
    return dict(path=str(path),SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def archive(np,path,arrays):
    require(all(value.nbytes<=2*1024**2 for value in arrays.values()),'Only small probe arrays, no duplicate native fields')
    with Path(path).open('xb')as stream:np.savez_compressed(stream,**arrays)
    require(Path(path).stat().st_size<=4*1024**2,'Small probe archive bound4MiB')
    return dict(path=str(path),SHA256=digest(path),bytes=Path(path).stat().st_size)

def required_inputs(admission=None):return light_inputs.required_inputs(admission)

def make_spec(admission=None):
    context=light_inputs.make_spec(admission)
    import light_probe
    require(light_probe.SAMPLES==32768 and light_probe.CHECK_SAMPLES==65536
        and light_probe.DURATION_S==.1 and light_probe.VPP_RELATIVE_DELTA_LIMIT==2e-4,
        'Source-bound prospective native waveform sampling policy')
    require(len(context['datasets'])==1 and context['datasets'][0]['candidate_id']==light_inputs.CANDIDATE_ID,'Exactly one actual E13 fine97 case; no old-case repeats')
    cutoffs=context['original_baseline']['cutoffs']
    require(len(cutoffs)==2 and all(math.isfinite(float(row['value_V_m']))and row['value_V_m']>0 for row in cutoffs),
            'Two fixed original-coarse101 B0 numerical scalar cutoffs')
    return dict(schema='task1-E13-fine-light-post-spec-v1',root_admission=context['root_admission'],inputs=context,
        ROI_names=list(REGIONS),normalization_modes=list(MODES),diagnostic_cutoffs=cutoffs,
        cutoff_timing='Fixed before this postbatch from original coarse101 B0; original PDE already computed',
        threshold_scope='Numerical cached modulation-volume classification, not physiological activation or safety',
        expected_native_geometries=len(context['datasets']),requested_probes_per_geometry=40,
        expected_native_candidate_ids=[light_inputs.CANDIDATE_ID],expected_threshold_subsets=48,
        old_case_repeats=0,
        allow_same_layer_extrapolation=True,maximum_same_layer_extrapolation_spacings=1.,
        probe_estimator_id=light_probe.ESTIMATOR_ID,
        probe_estimator_scope='New explicit same-layer interpolation/extrapolation estimator; old600 predictions preserved',
        waveform=dict(period_s=.1,samples_primary=32768,samples_check=65536,
            Vpp_relative_sample_refinement_diagnostic=2e-4,representative_samples_maximum=256,
            RMS='Exact two-distinct-carrier complex peak phasor RMS',
            AM='Two-tone scalar directional differential-potential envelope depth2min amplitudes'),
        maximum_new_PDE_RHS=0,maximum_new_Q_loads=0,maximum_new_eigen_solves=0,
        maximum_new_angular_evaluations=0,old_statistics_recomputed=False,
        child_RSS_forecast_bytes=170000000,new_output_forecast_bytes=10000000,
        child_RSS_target_below_bytes=180000000,whole_postbatch_output_limit_bytes=MAX_OUTPUT_BYTES,
        forecast_unmeasured=True,CPU_limit=4,total_RSS_plus_all_task_tmpfs_bytes=8000000000,
        max_physical_evaluation_cells=800000,experimental_validation=False,candidate_adopted=False)

def source_test_count():
    count=0
    for path in SOURCE.glob('test_*.py'):
        tree=ast.parse(path.read_text(),filename=str(path))
        count+=sum(1 for cls in tree.body if isinstance(cls,ast.ClassDef)for method in cls.body
                   if isinstance(method,ast.FunctionDef)and method.name.startswith('test_'))
    return count

def normalization_rows(dataset):
    rows=dataset['normalizations'];require(rows.get('status')=='complete'and set(MODES).issubset(rows['comparisons']),
        'Preserved four original-B0 normalization rows')
    for mode in MODES:
        scale=rows['comparisons'][mode]['amplitude_scale']
        require(type(scale)in(int,float)and math.isfinite(scale)and scale>=0,'Published finite cached amplitude scale')
    return rows['comparisons']

def cached_absolute_ROIs(normalizations,record):
    # Algebraic amplitude scaling of already published statistics is distinct
    # from rerunning native weighted reductions. Producer normalization rows
    # contain five scopes; the other two stored ROI statistics stay explicit.
    result={}
    for mode in MODES:
        row=normalizations[mode];values=row['absolute_ROI_fields_V_m']
        scale=row['amplitude_scale'];scaled={}
        for name in REGIONS:
            native=record['metrics']['regions'][name]['statistics']['maxTIS']
            scaled[name]={key:float(native[key])*scale for key in
                ('mean','p10','median','p90','p95','p99','max','min','std')if key in native}
        result[mode]=dict(amplitude_scale=row['amplitude_scale'],
            producer_normalized_AM_by_available_ROI={name:value['maxTIS']for name,value in values.items()},
            all_six_ROI_AM_statistics_by_algebraic_amplitude_scaling=scaled,
            electrical=row.get('electrical'),source='Original producer normalization rows plus explicitly labelled scalar scaling of cached native statistics; no new weighted-statistic evaluation')
    return result

def validate_probe_accounting(summary):
    rows=summary.get('probes');require(type(rows)is list and len(rows)==40
        and summary.get('requested_probe_count')==40 and summary.get('probe_count')==40,
        'Exactly forty retained probe rows/requests, including unavailable points')
    ids=[row.get('probe_id')for row in rows]
    require(all(type(v)is str and v for v in ids)and len(set(ids))==40,'Forty unique physical probe IDs')
    calculated=[row for row in rows if row.get('status')=='calculated_unloaded_only']
    unavailable=[row for row in rows if str(row.get('status','')).startswith('unavailable_')]
    require(len(calculated)+len(unavailable)==40,'Every requested row has one explicit calculated/unavailable state')
    require(all(type(row.get('same_layer_extrapolation_used'))is bool for row in calculated),
        'Every calculated point explicitly states whether same-layer extrapolation was used')
    extrapolated=sum(row.get('same_layer_extrapolation_used')is True for row in calculated)
    strict=len(calculated)-extrapolated
    expected=dict(calculated_probe_count=len(calculated),unavailable_probe_count=len(unavailable),
        same_layer_extrapolated_probe_count=extrapolated,strict_same_layer_bracket_available_probe_count=strict)
    require(all(type(summary.get(k))is int and summary[k]==v for k,v in expected.items()),
        'Actual calculated/unavailable/extrapolated/strict counts match retained rows')
    require(all(row.get('strict_same_layer_bracket_available')is (not row.get('same_layer_extrapolation_used'))for row in calculated)
        and all(row.get('strict_same_layer_bracket_available')is False for row in unavailable),
        'Strict availability remains separate from explicitly extrapolated predictions')
    return dict(requested_probe_count=40,**expected)

def build(spec,guard,deadline_monotonic=None,output_dir=None):
    require(callable(guard)and spec==make_spec(spec['root_admission']),
            'Exact positive-root-reviewed actual result/source/native input binding')
    out=Path(output_dir or RUN);require(out==RUN and out.is_dir()and out==out.resolve()
        and not out.is_symlink()and not(out/'native-light-result.json').exists(),'Unique root-owned postbatch output')
    check(guard,deadline_monotonic)
    import numpy as np
    import light_probe
    context=spec['inputs'];records=[];touched={};directory=out/'candidates';directory.mkdir()
    for dataset in context['datasets']:
        check(guard,deadline_monotonic);ident=dataset['candidate_id'];case=directory/ident
        require(Path(ident).name==ident and ident not in('.','..'),'Safe authenticated candidate ID')
        case.mkdir();normalizations=normalization_rows(dataset)
        keys=['grid']+[name+'_volume_weight_m3'for name in REGIONS]
        require(dataset['grid']['SHA256']==dataset['weights']['SHA256']
                and dataset['grid']['path']==dataset['weights']['path'],'Same published shared grid/ROI archive')
        geometry=load(np,dataset['grid'],keys,context['input_sha256'],guard,deadline_monotonic)
        grid=geometry.pop('grid');n=len(grid)
        require(grid.shape==(n,5)and 0<n<=800000 and np.all(np.isin(grid[:,3],[0.,1.,2.,3.])),
                'Authenticated native physical grid with four fixed layers below cell cap')
        scalar=load(np,dataset['scalars'],['AM_max2074'],context['input_sha256'],guard,deadline_monotonic)['AM_max2074']
        require(scalar.shape==(n,)and np.all(scalar>=0),'Existing sampled-direction native scalar only; no angular reevaluation')
        thresholded={}
        for mode in MODES:
            thresholded[mode]={}
            for cutoff in spec['diagnostic_cutoffs']:
                thresholded[mode][cutoff['cutoff_id']]={name:high_volume.threshold_summary(np,grid,scalar,
                    geometry[name+'_volume_weight_m3'],cutoff['value_V_m'],normalizations[mode]['amplitude_scale'],
                    guard=guard,deadline_monotonic=deadline_monotonic)for name in REGIONS}
        threshold_subset_count=sum(len(regions)for cutoffs in thresholded.values()for regions in cutoffs.values())
        require(threshold_subset_count==48,'Exactly6ROIs x2 original-B0 cutoffs x4 original normalizations')
        threshold_receipt=new_json(case/'cached-high-modulation-volumes.json',dict(candidate_id=ident,
            source_scalar=dataset['scalars'],source_grid_and_ROI=dataset['grid'],thresholds=thresholded,
            actual_threshold_subsets=threshold_subset_count,
            original_absolute_values_preserved=cached_absolute_ROIs(normalizations,dataset['record']),
            old_diagnostics_not_run_rewritten=False,classification_added_by_this_postbatch=True,
            threshold_timing=spec['cutoff_timing'],source_provenance=dataset['provenance']))
        del scalar,geometry,thresholded;gc.collect();check(guard,deadline_monotonic)
        prepared=light_probe.prepare(np,grid,allow_same_layer_extrapolation=True,
                                    guard=guard,deadline_monotonic=deadline_monotonic)
        samples=[]
        for frequency in('2000','2010'):
            descriptor=dataset['raw_by_frequency'][frequency]
            phi=load(np,descriptor,['phi_peak_V'],context['input_sha256'],guard,deadline_monotonic)['phi_peak_V']
            require(phi.shape==(n,)and np.iscomplexobj(phi),'Actual native complex peak potential at this carrier')
            samples.append(light_probe.sample_carrier(np,prepared,phi,int(frequency),guard=guard,
                deadline_monotonic=deadline_monotonic));del phi;gc.collect()
            touched[descriptor['path']]=descriptor
        prediction=light_probe.finish(np,prepared,samples,candidate_id=ident,
            run_id=dataset['provenance'].get('source_run_id'),guard=guard,deadline_monotonic=deadline_monotonic)
        accounting=validate_probe_accounting(prediction['summary'])
        require(prediction['summary']['estimator_id']==spec['probe_estimator_id']
            and prediction['summary']['waveform_window']['primary_samples']==32768
            and prediction['summary']['waveform_window']['check_samples']==65536
            and prediction['summary']['waveform_window']['duration_s']==.1,
            'Actual probe output retains exact source-preregistered estimator/sample policy')
        probe_archive=archive(np,case/'native-probe-small-arrays.npz',prediction['arrays'])
        probe_receipt=new_json(case/'native-probe-predictions.json',dict(prediction['summary'],
            small_arrays=probe_archive,source_raw_by_frequency=dataset['raw_by_frequency'],
            source_grid=dataset['grid'],source_provenance=dataset['provenance'],
            normalization_scope='Original native fixed1Vpp carrier phasors; no burden scaling silently applied'))
        records.append(dict(candidate_id=ident,physical_geometry_id=dataset['physical_geometry_id'],
            grid_variant=dataset['grid_variant'],high_volume_receipt=threshold_receipt,
            probe_receipt=probe_receipt,probe_arrays=probe_archive,
            requested_probes=40,calculated_probes=prediction['summary']['calculated_probe_count'],
            unavailable_probes=prediction['summary']['unavailable_probe_count'],
            strict_same_layer_bracket_available_probes=accounting['strict_same_layer_bracket_available_probe_count'],
            same_layer_extrapolated_probes=accounting['same_layer_extrapolated_probe_count'],
            source_provenance=dataset['provenance'],new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,
            new_angular_evaluations=0,actual_threshold_subsets=threshold_subset_count,candidate_adopted=False))
        touched[dataset['grid']['path']]=dataset['grid'];touched[dataset['scalars']['path']]=dataset['scalars']
        del prediction,prepared,samples,grid;gc.collect()
        new_json(out/('checkpoint-native-post-%d.json'%len(records)),dict(status='native_cached_postcase_complete',
            completed_geometries=len(records),new_PDE_RHS=0,new_Q_loads=0,new_angular_evaluations=0))
        output_budget(out)
    after=[]
    for descriptor in touched.values():
        verify(descriptor,context['input_sha256'],guard,deadline_monotonic)
        after.append(dict(path=descriptor['path'],SHA256=descriptor['SHA256'],before_after_full_SHA_passed=True))
    proof=new_json(out/'used-native-input-SHA-proof.json',dict(files=after,new_Q_loads=0))
    summary=dict(schema='task1-E13-fine-light-post-result-v1',status='E13_fine_cached_highvolume_and40probe_postbatch_computed_unadopted',
        candidates=records,completed_native_geometries=len(records),requested_probes=40*len(records),
        calculated_probes=sum(row['calculated_probes']for row in records),
        unavailable_probes=sum(row['unavailable_probes']for row in records),
        strict_same_layer_bracket_available_probes=sum(row['strict_same_layer_bracket_available_probes']for row in records),
        same_layer_extrapolated_probes=sum(row['same_layer_extrapolated_probes']for row in records),
        expected_threshold_subsets_per_geometry=len(MODES)*2*len(REGIONS),
        actual_threshold_subsets=sum(row['actual_threshold_subsets']for row in records),
        actual_new_PDE_RHS=0,actual_new_Q_loads=0,actual_new_eigen_solves=0,actual_new_angular_evaluations=0,
        original_statistics_recomputed=False,original_results_overwritten=False,old600probe_predictions_preserved=True,
        old_case_repeats=0,
        source_sha256=context['source_sha256'],source_provenance=context['provenance'],
        E13_publication_recovery=context['E13_publication_recovery'],inherited_holds=context['holds'],
        diagnostic_cutoffs=spec['diagnostic_cutoffs'],cutoff_timing=spec['cutoff_timing'],
        input_SHA_proof=proof,GUI=dict(status='not_run',reason='Native scientific postbatch only'),
        hardware_loading_validated=False,experimental_validation=False,full_convergence=False,
        physiological_activation_or_safety_claim=False,candidate_adopted=False,Windows_saved_verified=False)
    new_json(out/'native-light-result.json',summary);output_budget(out);check(guard,deadline_monotonic)
    return dict(summary=summary,arrays={})
