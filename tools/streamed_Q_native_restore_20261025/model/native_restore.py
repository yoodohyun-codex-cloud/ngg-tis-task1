"""Deferred cached-native verification of the authenticated streamed real Q.

No numerical import, native/cache read, array, solve or work occurs on import.
The sole Root owner must first publish/pass the separate operator MFG batch.
"""
import ast,csv,gc,hashlib,io,json,math,time
from contextlib import contextmanager
from pathlib import Path
import restore_inputs

SOURCE=Path('/dev/shm/task1-streamed-Q-native-restore-20261025/source')
RUN=Path('/dev/shm/task1-streamed-Q-native-restore-20261025-run')
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
N=8184;CELLS=793848;FREQUENCIES=(2000,2010);COUNTS=(4,19,18,56)

def require(ok,message):
    if not ok:raise ValueError(message)

def check(guard,deadline):
    guard()
    if deadline is not None and time.monotonic()>=deadline:
        raise TimeoutError('Finite cached-native streamed-Q verification deadline')

def pair(value):return dict(real=float(complex(value).real),imaginary=float(complex(value).imag))
def cv(value):return complex(value['real'],value['imaginary'])

def sha(path,guard=lambda:None,deadline=None):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):
            check(guard,deadline);h.update(block)
    return h.hexdigest()

def verify(descriptor,pins,guard,deadline):
    path=Path(descriptor['path'])
    require(path.is_file()and not path.is_symlink()and path==path.resolve()
        and path.stat().st_size==descriptor['bytes']and pins.get(str(path))==descriptor['SHA256'],
        'Exact immutable native descriptor '+str(path))
    require(sha(path,guard,deadline)==descriptor['SHA256'],'Full actual input SHA before use '+str(path))
    return path

def load(np,descriptor,keys,pins,guard,deadline):
    path=verify(descriptor,pins,guard,deadline)
    with np.load(path,allow_pickle=False)as saved:
        require(set(keys).issubset(saved.files),'Required native ABI absent; never resolve or fabricate')
        result={key:np.array(saved[key],copy=True)for key in keys}
    require(all(np.isfinite(value).all()for value in result.values()),'Finite complete stored native arrays')
    require(sha(path,guard,deadline)==descriptor['SHA256'],'Full actual input SHA after decode '+str(path))
    return result

def new(path,value):
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,indent=2)+'\n').encode()
    require(len(raw)<20*1024**2,'Small verification JSON only, no duplicate native field/cache output')
    with Path(path).open('xb')as stream:stream.write(raw)
    return dict(path=str(path),SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def required_inputs(admission=None):return restore_inputs.required_inputs(admission)

def make_spec(admission=None):
    context=restore_inputs.make_spec(admission)
    return dict(schema='task1-streamed-Q-native-restore-spec-v1',root_admission=context['root_admission'],inputs=context,
        frequencies_Hz=list(FREQUENCIES),driven_outputs=[0,1],expected_cached_native_responses=2,
        maximum_new_PDE_RHS=0,maximum_new_Krylov_calls=0,maximum_new_eigen_solves=0,
        maximum_new_angular_evaluations=0,whole_Q_materialization_allowed=False,
        native_Q_read_required=True,physical_cells=CELLS,XY_columns=N,depth_layer_counts=list(COUNTS),
        field_estimator_version='native-lateral-half-face-v1+analytic-z-DtN-v1',
        component_and_vector_diagnostic=dict(relative_tolerance=2e-7,absolute_tolerance_V_m=1e-8,
            rule='abs(new-old) <= absolute + relative*abs(original), complex components and native vector norm',
            phase_alignment=False,gauge_alignment=False,numerical_diagnostic_not_mesh_convergence=True),
        modal_restore_relative_limit=2e-7,modal_norm_denominator_floor_V=1e-12,
        cached_circuit_relative_tolerance=2e-7,cached_circuit_absolute_current_A=1e-12,
        cached_power_restore_relative_tolerance=2e-7,cached_power_denominator_floor_W=1e-12,
        field_storage='Reconstructed one-frequency E exists only in RAM and is compared before freeing; no phi/E/Q archive duplicated',
        AM_error_bound='Per cell:2max(norm(deltaE2000),norm(deltaE2010)); bounds same fixed2074 real-direction sampled maximum without rescanning',
        carrier_RMS_error_bound='Per cell:sqrt((norm(deltaE2000)^2+norm(deltaE2010)^2)/2)',
        child_RSS_forecast_bytes=300000000,new_output_forecast_bytes=20000000,forecasts_unmeasured=True,
        CPU_limit=4,total_RSS_plus_all_task_tmpfs_bytes=8000000000,max_physical_cells=800000,
        candidate_adopted=False,full_mesh_convergence=False)

def source_test_count():
    count=0
    for path in SOURCE.glob('test_*.py'):
        tree=ast.parse(path.read_text(),filename=str(path))
        count+=sum(1 for cls in tree.body if isinstance(cls,ast.ClassDef)for method in cls.body
            if isinstance(method,ast.FunctionDef)and method.name.startswith('test_'))
    return count

def contacts(np,raw,ij,h):
    reader=csv.DictReader(io.StringIO(raw.decode()));require(reader.fieldnames==['pad','i','j','area_m2'],'Published exact fine mask CSV ABI')
    lookup={(int(i),int(j)):k for k,(i,j)in enumerate(ij)};pads=[];cells=[];areas=[]
    for row in reader:
        pad=int(row['pad']);key=(int(row['i']),int(row['j']));area=float(row['area_m2'])
        require(pad in(0,1,2,3)and key in lookup and math.isfinite(area)and 0<area<=h*h*(1+1e-10),
            'Actual four-pad fractional physical patch, no area/mask repair')
        pads.append(pad);cells.append(lookup[key]);areas.append(area)
    p=np.asarray(pads,np.int32);c=np.asarray(cells,np.int32);a=np.asarray(areas,float)
    require(len(set(zip(p.tolist(),c.tolist())))==len(p)and set(p.tolist())=={0,1,2,3},'Unique actual contact tuple/order')
    require(np.max(np.bincount(c,weights=a,minlength=len(ij)))<=h*h*(1+1e-10),'Physical face not overcovered')
    for pad in range(4):require(abs(float(a[p==pad].sum())-.000225)/.000225<=1e-10,'Original225mm2 pad areas; no rescale')
    return p,c,a

def graph(np,context,guard,deadline):
    result=load(np,context['graph_arrays'],['eigenvalues_per_m2','XY_m','ij'],context['input_sha256'],guard,deadline)
    eigen,xy,ij=result['eigenvalues_per_m2'],result['XY_m'],result['ij']
    require(eigen.shape==(N,)and xy.shape==ij.shape==(N,2),'Exact fine graph dimension')
    declared=context['graph_summary']['graph']
    require(hashlib.sha256(xy.astype('<f8',copy=False).tobytes()).hexdigest()==declared['XY_float64_le_SHA256']
        and hashlib.sha256(ij.astype('<i4',copy=False).tobytes()).hexdigest()==declared['ij_int32_le_SHA256'],
        'Same actual physical XY/index ordering, not assumed index identity')
    h=.05/102
    require(np.allclose(xy,-.025+(ij+.5)*h,rtol=0,atol=1e-14),'Actual graph physical coordinates')
    return eigen,xy,ij

def checked_geometry(np,context,xy,guard,deadline):
    grid=load(np,context['grid_ROI'],['grid'],context['input_sha256'],guard,deadline)['grid']
    faces=np.asarray(context['eval_face_receipt_value']['z_faces_m'],float);layers=np.repeat(np.arange(4),COUNTS)
    require(grid.shape==(CELLS,5)and faces.shape==(98,)and np.all(np.diff(faces)>0)
        and np.allclose(faces[[0,4,23,41,97]],[0.,.0001,.0051,.0101,.0251],rtol=0,atol=1e-12),
        'Same fixedD50/layers/common97 actual native geometry')
    zs=(faces[:-1]+faces[1:])/2.;h=.05/102;coordinate_error=0.
    for k in range(97):
        check(guard,deadline);row=grid[k*N:(k+1)*N]
        coordinate_error=max(coordinate_error,float(np.max(abs(row[:,:2]-xy*1000))))
        require(np.all(row[:,2]==zs[k]*1000)and np.all(row[:,3]==layers[k])
            and np.allclose(row[:,4],h*h*(faces[k+1]-faces[k]),rtol=0,atol=1e-23),
            'Exact actual physical z/layer/volume plane binding')
    require(coordinate_error<=1e-12,'Actual fine native coordinate order differs; no projection/gauge fit in same-grid restore')
    del grid;gc.collect()
    return zs,layers,dict(passed=True,grid=context['grid_ROI'],maximum_XY_difference_mm=coordinate_error,
        actual_common_physical_z_layer_volumes_verified=True,phase_fit=False,gauge_fit=False,index_only_assumption=False)

def cached_gate(np,Q,profile,pads,cells,areas,za,output,h,cached,guard,deadline):
    """The unchanged solver can only enter its published cached response path."""
    import fine_solver
    from unittest.mock import patch
    require(type(cached)is dict and set(cached)=={'phi_surface','metal'}
        and cached['phi_surface'].shape==(N,)and cached['metal'].shape==(2,),
        'Actual cached surface/metal response mandatory; no solve fallback')
    attempts=[]
    def forbidden(*args,**kwargs):
        attempts.append('gmres');raise RuntimeError('New Krylov/PDE solve forbidden in cached-native restoration')
    with patch('scipy.sparse.linalg.gmres',side_effect=forbidden):
        solution=fine_solver.solve(np,Q,profile,pads,cells,areas,za,output,h,guard,deadline,cached=cached)
    proof=solution['proof'];require(not attempts and proof['actual_new_RHS']==0
        and proof['iterations']==0 and proof['matvec_count']==0 and proof['reused_published_baseline_surface']is True,
        'No new PDE RHS/Krylov iteration or fallback was executed')
    proof.update(native_Q_read=True,whole_Q_loaded=False,new_Krylov_calls=0,
        original_five_gate_limits_unchanged=True,unchanged_cached_solver_branch=True)
    return solution

class RegionWeights:
    """One authenticated fractional ROI array resident at a time."""
    def __init__(self,np,descriptor,pins,guard,deadline):
        self.np=np;self.descriptor=descriptor;self.pins=pins;self.guard=guard;self.deadline=deadline
        self.current=None;self.values=None
    def chunk(self,name,start,stop):
        require(name in REGIONS and type(start)is int and type(stop)is int and 0<=start<=stop<=CELLS,
            'Bounded requested original physical ROI chunk')
        if name!=self.current:
            self.values=None;gc.collect();key=name+'_volume_weight_m3'
            self.values=load(self.np,self.descriptor,[key],self.pins,self.guard,self.deadline)[key]
            require(self.values.shape==(CELLS,),'Original fractional ROI weights, no regenerated mask')
            self.current=name
        return self.values[start:stop]
    def release(self):self.values=None;self.current=None;gc.collect()

@contextmanager
def checked_operator(np,context,guard,deadline,out,frequency):
    """Preserve actual chunk-use audit even when a gate/field operation fails."""
    import streamed_real_q
    Q=streamed_real_q.StreamedRealQ(np,context['Q_manifest'],context['remote_Q_chunk_proofs'],
        context['input_sha256'],guard,deadline_monotonic=deadline,cache_name='xy102')
    try:
        with Q:yield Q
    finally:
        new(out/('B0-'+str(frequency)+'-streamed-Q-receipt.json'),Q.receipt())

def power_comparison(new_value,old_value,relative_limit,floor_W):
    delta=abs(complex(new_value)-complex(old_value));den=max(abs(complex(old_value)),floor_W)
    return dict(original_complex_W=pair(old_value),restored_complex_W=pair(new_value),
        absolute_complex_difference_W=float(delta),relative_difference=float(delta/den),
        relative_denominator_W=float(den),denominator_floor_W=float(floor_W),
        relative_limit=float(relative_limit),passed=bool(delta/den<=relative_limit),
        scope='Prospective cached-value numerical equivalence diagnostic; not mesh convergence or human safety')

def frequency_frame(np,spec,frequency,output,out,guard,deadline):
    import fine_fields
    import restore_errors
    context=spec['inputs'];h=.05/102;eigen,xy,ij=graph(np,context,guard,deadline)
    original_proof=context['B0_proofs_by_frequency'][str(frequency)]['value']
    require(original_proof['passed']is True and original_proof['physical_gates']['passed']is True
        and original_proof['passivity_passed']is True and original_proof['frequency_Hz']==frequency
        and original_proof['driven_output']==output and original_proof['source_peak_V']==.5,
        'Actual published baseline carrier/output/peak/passivity proof before any Q application')
    zs,layers,geometry_proof=checked_geometry(np,context,xy,guard,deadline)
    mask=verify(context['B0_mask'],context['input_sha256'],guard,deadline)
    pads,cells,areas=contacts(np,mask.read_bytes(),ij,h)
    descriptor=context['B0_raw_by_frequency'][str(frequency)]
    keys=['phi_surface_peak_V','metal_peak_V','modal_surface_coeff','source_current_peak_A',
        'contact_pad','contact_xy_index','contact_area_m2','layer_complex_power_W']
    cached=load(np,descriptor,keys,context['input_sha256'],guard,deadline)
    require(cached['phi_surface_peak_V'].shape==cached['modal_surface_coeff'].shape==(N,)
        and cached['metal_peak_V'].shape==cached['source_current_peak_A'].shape==(2,)
        and np.array_equal(cached['contact_pad'],pads)and np.array_equal(cached['contact_xy_index'],cells)
        and np.array_equal(cached['contact_area_m2'],areas),'Actual fineB0 flat response/contact order/areas; no alias assumption')
    gamma=[cv(v)for v in context['catalog']['gamma_by_frequency'][str(frequency)]]
    za=cv(context['catalog']['z_by_frequency'][str(frequency)])
    with checked_operator(np,context,guard,deadline,out,frequency)as Q:
        profile=fine_fields.profiles(np,Q,eigen,gamma,zs,h,guard,deadline)
        solution=cached_gate(np,Q,profile,pads,cells,areas,za,output,h,
            dict(phi_surface=cached['phi_surface_peak_V'],metal=cached['metal_peak_V']),guard,deadline)
        proof=solution['proof'];modal_delta=float(np.linalg.norm(solution['coeff']-cached['modal_surface_coeff']))
        modal_den=max(float(np.linalg.norm(cached['modal_surface_coeff'])),spec['modal_norm_denominator_floor_V'])
        modal_pass=modal_delta/modal_den<=spec['modal_restore_relative_limit']
        current_error=float(np.max(abs(solution['source_current']-cached['source_current_peak_A'])))
        current_limit=spec['cached_circuit_absolute_current_A']+spec['cached_circuit_relative_tolerance']*float(np.max(abs(cached['source_current_peak_A'])))
        proof.update(frequency_Hz=frequency,driven_output=output,original_native_raw=descriptor,
            original_native_gate_proof=context['B0_proofs_by_frequency'][str(frequency)]['descriptor'],
            physical_geometry=geometry_proof,modal_restore_relative_error=modal_delta/modal_den,
            modal_restore_denominator_floor_V=spec['modal_norm_denominator_floor_V'],
            modal_restore_limit=spec['modal_restore_relative_limit'],modal_restore_passed=bool(modal_pass),
            stored_source_current_maximum_error_A=current_error,stored_source_current_error_limit_A=current_limit,
            stored_source_current_restore_passed=bool(current_error<=current_limit),
            source_high_impedance_Vpp=1.,source_resistance_ohm=50.,inactive_ideal_output_V=0.,
            physical_pads=4,independent_outputs=2,return_topology='Pads2/3hardcommonGND')
        require(cached['layer_complex_power_W'].shape==(4,),'Original four-layer signed power ABI')
        old_power=dict(source=cv(original_proof['source_complex_power_W']),
            contact=cv(original_proof['contact_complex_power_W']),resistor=original_proof['source_resistor_power_W'])
        fresh_power=dict(source=solution['source_power'],contact=solution['contact_power'],resistor=solution['resistor_power'])
        comparisons={name:power_comparison(fresh_power[name],value,
            spec['cached_power_restore_relative_tolerance'],spec['cached_power_denominator_floor_W'])for name,value in old_power.items()}
        for k,name in enumerate(('sc','dermis','fat','muscle')):
            comparisons[name]=power_comparison(solution['layer_power'][k],cached['layer_complex_power_W'][k],
                spec['cached_power_restore_relative_tolerance'],spec['cached_power_denominator_floor_W'])
        power_pass=all(row['passed']for row in comparisons.values())
        proof['stored_power_restore_comparison']=dict(passed=power_pass,values=comparisons,
            original_five_physical_gates_unchanged=True)
        gate_receipt=new(out/('B0-'+str(frequency)+'-fresh-cached-gates.json'),proof)
        require(proof['passed']and modal_pass and current_error<=current_limit and power_pass,
            'Cached response/five physical gates/passivity/modal/current/power check failed; preserve proof, never run fallback')
        phi,E,interface=fine_fields.fields(np,Q,profile,solution['coeff'],ij,layers,h,guard,deadline)
        del phi,interface,profile,solution,cached
    operator_path=out/('B0-'+str(frequency)+'-streamed-Q-receipt.json')
    operator_receipt=json.loads(operator_path.read_bytes());require(operator_receipt['closed']is True
        and operator_receipt['whole_Q_loaded']is False and operator_receipt['complex_Q_materialized']is False
        and operator_receipt['audit']['loaded_chunk_visits']>0
        and operator_receipt['all_loaded_chunks_before_after_verified']is True,'Actual bounded chunk use and closed operator; no full Q')
    operator_proof=dict(path=str(operator_path),SHA256=sha(operator_path,guard,deadline),bytes=operator_path.stat().st_size)
    del Q,eigen,xy,ij,pads,cells,areas;gc.collect();check(guard,deadline)
    # Profiles/Q lifetimes ended before native field/error arrays are decoded.
    grid=load(np,context['grid_ROI'],['grid'],context['input_sha256'],guard,deadline)['grid']
    original=load(np,descriptor,['E_peak_V_m'],context['input_sha256'],guard,deadline)['E_peak_V_m']
    require(E.shape==original.shape==(CELLS,3)and np.iscomplexobj(E)and np.iscomplexobj(original),
        'Same actual complex peak vector field/order; no phase/gauge alignment or index-only projection')
    weights=RegionWeights(np,context['grid_ROI'],context['input_sha256'],guard,deadline)
    result=restore_errors.compare_fields(np,E,original,grid,
        {'regions':REGIONS,'chunk':weights.chunk},guard,deadline)
    weights.release();record=dict(frequency_Hz=frequency,active_output=output,
        cached_native_raw=descriptor,cached_gate_receipt=gate_receipt,streamed_Q_receipt=operator_proof,
        field_error=result['summary'],native_Q_read=True,whole_Q_loaded=False,
        Q_closed_and_profiles_released_before_error_reduction=True,new_PDE_RHS=0,new_Krylov_calls=0,
        new_eigen_solves=0,new_angular_evaluations=0,field_reconstruction_saved=False,
        candidate_adopted=False)
    new(out/('B0-'+str(frequency)+'-native-field-error.json'),record)
    norm=result['norm_delta_V_m'];require(norm.shape==(CELLS,)and np.isfinite(norm).all(),'Bounded error norms only leave frequency frame')
    del E,original,grid,weights,result;gc.collect();return record,norm

def build(spec,guard,deadline_monotonic=None,output_dir=None):
    require(callable(guard)and spec==make_spec(spec['root_admission']),
        'Actual Root/operator-MFG/fine-data/source proof binding before native Q reads')
    out=Path(output_dir or RUN);require(out==RUN and out.is_dir()and out==out.resolve()
        and not out.is_symlink()and not(out/'native-restore-result.json').exists(),'Unique canonical native verification output')
    check(guard,deadline_monotonic)
    import numpy as np
    import restore_errors
    records=[];norms=[]
    for frequency,output in((2000,0),(2010,1)):
        record,norm=frequency_frame(np,spec,frequency,output,out,guard,deadline_monotonic)
        records.append(record);norms.append(norm)
        new(out/('checkpoint-cached-native-'+str(frequency)+'.json'),dict(status='cached_carrier_restore_and_error_complete',
            completed_cached_carriers=len(records),new_PDE_RHS=0,new_Krylov_calls=0,new_eigen_solves=0,new_angular_evaluations=0))
    context=spec['inputs'];grid=load(np,context['grid_ROI'],['grid'],context['input_sha256'],guard,deadline_monotonic)['grid']
    weights=RegionWeights(np,context['grid_ROI'],context['input_sha256'],guard,deadline_monotonic)
    bound=restore_errors.combine_carrier_bounds(np,norms[0],norms[1],grid,
        {'regions':REGIONS,'chunk':weights.chunk},guard,deadline_monotonic)
    weights.release();del norms,grid,weights;gc.collect()
    bound_receipt=new(out/'two-carrier-AM-RMS-error-bounds.json',bound)
    summary=dict(schema='task1-streamed-Q-native-restore-result-v1',
        status='two_cached_native_carriers_streamed_Q_restore_computed_unadopted',
        completed_cached_native_responses=2,frequencies_Hz=list(FREQUENCIES),responses=records,
        actual_native_E_reconstructions=2,actual_native_field_comparisons=2,
        actual_new_PDE_RHS=0,actual_new_Krylov_calls=0,actual_new_eigen_solves=0,actual_new_angular_evaluations=0,
        actual_native_Q_read=True,whole_Q_loaded=False,complex_Q_materialized=False,
        full_Q_materialized=False,
        new_native_phi_or_E_archives=0,new_Q_archives=0,native_restore_verification_passed=all(r['field_error']['passed']for r in records),
        AM_RMS_error_bound_receipt=bound_receipt,source_sha256=context['source_sha256'],
        provenance=dict(actual_publications=context['publication_metadata'],
            streamed_operator_source=context['streamed_operator_source'],fine_math_sources=context['fine_sources'],
            actual_operator_MFG=context['MFG_evidence'],native_B0_raw_by_frequency=context['B0_raw_by_frequency']),
        inherited_holds=context['holds'],
        same_physical_coordinates_and_grid_verified=True,phase_fit=False,gauge_fit=False,
        original_results_overwritten=False,full_mesh_convergence=False,experimental_validation=False,
        physiological_activation_or_safety_claim=False,candidate_adopted=False,Windows_saved_verified=False)
    new(out/'native-restore-result.json',summary);check(guard,deadline_monotonic)
    return dict(summary=summary,arrays={})
