"""Conditional same-physical-ellipse adjacent-XY study; sole Root executes.

Import is inert: no scientific import, mask, geometry, field, cache or solve.
Two new fine RHS, one cached coarse SC4 supplement and no full-Q allocation.
"""
import ast,csv,gc,hashlib,io,json,math,time
from contextlib import contextmanager
from fractions import Fraction as F
from pathlib import Path
import e13_inputs

SOURCE=Path('/dev/shm/task1-E13-fineXY-20261025/source')
RUN=Path('/dev/shm/task1-E13-fineXY-20261025-run')
ID='E13-tangent-P23-centroids-225';COUNTS=(4,19,18,56)

def require(ok,message):
    if not ok:raise ValueError(message)
def check(guard,deadline):
    guard()
    if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite conditional E13 fineXY stage deadline')
def cv(value):return complex(value['real'],value['imaginary'])
def sha(path,guard=lambda:None,deadline=None):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):check(guard,deadline);h.update(block)
    return h.hexdigest()
def new(path,value):
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,indent=2)+'\n').encode()
    with Path(path).open('xb')as stream:stream.write(raw)
    return dict(path=str(path),SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def verified(descriptor,pins,guard,deadline):
    p=Path(descriptor['path']);require(p.is_file()and not p.is_symlink()and p==p.resolve()
        and p.stat().st_size==descriptor['bytes']and pins.get(str(p))==descriptor['SHA256']
        and sha(p,guard,deadline)==descriptor['SHA256'],'Exact actual source/native artifact '+str(p));return p
def load(np,descriptor,keys,pins,guard,deadline):
    check(guard,deadline);path=verified(descriptor,pins,guard,deadline)
    with np.load(path,allow_pickle=False)as saved:
        require(set(keys).issubset(saved.files),'Required actual native fields unavailable; no invented aliases')
        values={key:np.array(saved[key],copy=True)for key in keys}
    require(all(np.isfinite(value).all()for value in values.values()),'Finite complete actual native arrays')
    require(sha(path,guard,deadline)==descriptor['SHA256'],'Native archive unchanged after decode');return values
def archive(np,path,arrays):
    with Path(path).open('xb')as stream:np.savez_compressed(stream,**arrays)
    require(Path(path).stat().st_size<80*1024**2,'Approved per-file bound80MiB; no output deletion')
    return dict(path=str(path),SHA256=sha(path),bytes=Path(path).stat().st_size)
def required_inputs(admission=None):return e13_inputs.required_inputs(admission)
def make_spec(admission=None):
    context=e13_inputs.make_spec(admission)
    return dict(schema='task1-E13-fineXY-screen-spec-v1',root_admission=context['root_admission'],inputs=context,
        candidate_id=ID,maximum_new_driven_RHS=2,expected_coarse_cached_SC4_responses=2,
        full_angular_metric_evaluations=1,SC4_only_angular_metric_evaluations=1,
        repeated_old93_bulk_angular_evaluations=0,repeated_fine_B0_RHS=0,repeated_fine_B0_angular_evaluations=0,
        expected_fine_B0_full_aliases=1,new_eigen_solves=0,whole_Q_materialization_allowed=False,
        geometry_definition='Same authenticated actual coarse E13 exact centres,13mm tangential semimajor,225/(pi*13)mm semiminor,225mm2/pad; only contact discretization/grid changes',
        fine_contact_h_mm_exact=dict(numerator=25,denominator=51),coarse_contact_h_mm_exact=dict(numerator=1,denominator=2),
        physical_body=dict(diameter_mm=50.,layer_thickness_mm=[.1,5.,5.,15.]),
        fine_cells=793848,coarse_common97_cells=762420,common97_layer_counts=list(COUNTS),
        initial_native_B0_restore_actual_published_PASS_required=True,
        field_estimator_version='native-lateral-half-face-v1+analytic-z-DtN-v1',
        primary_normalization_reference='Original published coarse101 B0',secondary_normalization_reference='Actual fine B0; shown explicitly as secondary',
        coarse_common97_available_scalar_metrics=['maxTIS','RMS','Jtotal_vector_RMS'],
        missing_coarse_directional_or_percarrier_statistics_invented=False,
        source_high_impedance_Vpp=1.,source_peak_V=.5,source_resistance_ohm=50.,
        physical_pads=4,independent_outputs=2,return_topology='Pads2/3hardcommonGND; other ideal output0V through its single50ohm',
        modal_restore_relative_limit=2e-7,modal_norm_floor_V=1e-12,
        raw_frames_return_only_metadata=True,Q_resident_during_metrics=False,
        child_RSS_forecast_bytes=350000000,new_output_forecast_bytes=150000000,forecasts_unmeasured=True,
        initial_numerical_child_seconds=1200,CPU_limit=4,total_RSS_plus_all_task_tmpfs_bytes=8000000000,
        max_physical_cells=800000,full_convergence=False,candidate_adopted=False)
def source_test_count():
    count=0
    for path in SOURCE.glob('test_*.py'):
        tree=ast.parse(path.read_text(),filename=str(path))
        count+=sum(1 for cls in tree.body if isinstance(cls,ast.ClassDef)for m in cls.body if isinstance(m,ast.FunctionDef)and m.name.startswith('test_'))
    return count
def validate_local_MFG(value,sources,count):
    require(value.get('status')=='passed'and value.get('model_source_sha256')==sources
        and type(value.get('model_source_test_count'))is int and value['model_source_test_count']==count
        and type(value.get('model_tests_run'))is int and value['model_tests_run']==count and type(count)is int and count>0,
        'Actual source-bound new shape/h manufactured test PASS required before candidate solve')
    require(type(value.get('tests_run'))is int and value['tests_run']>=count
        and value.get('expected_total_tests')==value['tests_run']
        and all(type(value.get(k))is int and value[k]==0 for k in('tests_failed','tests_errors','tests_skipped')),
        'Every prospectively counted local manufactured test succeeds; no relaxed contact criteria')
    return dict(passed=True,model_tests=count,actual_tests=value['tests_run'],source_sha256=sources)
def metadata_only(value):
    if value is None or type(value)in(str,bool,int):return True
    if type(value)is float:return math.isfinite(value)
    if isinstance(value,dict):return all(type(k)is str and metadata_only(v)for k,v in value.items())
    if isinstance(value,(list,tuple)):return all(metadata_only(v)for v in value)
    return False
def separated_stage(raw,collector=gc.collect):
    result=raw();require(metadata_only(result),'Q/profile/E objects may not leave raw frame');collector();return result
def exact_centres(proof):
    rows=proof['rows'];require(len(rows)==4 and {r['pad']for r in rows}=={0,1,2,3},'Actual published four-pad exact centroid proof')
    output=[]
    for pad in range(4):
        row=next(v for v in rows if v['pad']==pad);values=row['exact_centroid_mm']
        require(len(values)==2 and all(type(v['numerator'])is int and type(v['denominator'])is int and v['denominator']>0 for v in values),
            'Exact original rational centres, no rounded position/area fallback')
        output.append(tuple(F(v['numerator'],v['denominator'])for v in values))
    return output
def graph(np,context,which,guard,deadline):
    data=load(np,context['graph_arrays'][which],['eigenvalues_per_m2','XY_m','ij'],context['input_sha256'],guard,deadline)
    n=8184 if which=='fine'else 7860;e,xy,ij=data['eigenvalues_per_m2'],data['XY_m'],data['ij']
    require(e.shape==(n,)and xy.shape==ij.shape==(n,2),'Actual bounded graph/eigen ABI')
    declared=context['graph_summaries'][which]['graph']
    require(hashlib.sha256(xy.astype('<f8',copy=False).tobytes()).hexdigest()==declared['XY_float64_le_SHA256']
        and hashlib.sha256(ij.astype('<i4',copy=False).tobytes()).hexdigest()==declared['ij_int32_le_SHA256'],
        'Actual physical XY/index ordering before any streamed-Q use')
    return e,xy,ij
def depth_binding(np,context,which,xy,guard,deadline):
    n=len(xy);values=load(np,context['geometry'][which],['grid','z_faces_m','ij'],context['input_sha256'],guard,deadline)
    grid=values['grid'];faces=values['z_faces_m'];require(grid.shape==(97*n,5)and faces.shape==(98,),'Actual reused matched97 geometry')
    require(np.array_equal(faces,np.asarray(context['eval_faces_m'],float))and np.all(np.diff(faces)>0)
        and np.allclose(faces[[0,4,23,41,97]],[0.,.0001,.0051,.0101,.0251],rtol=0,atol=1e-12),'Same fixed physical depth faces')
    z=(faces[:-1]+faces[1:])/2.;layers=np.repeat(np.arange(4),COUNTS)
    for k in range(97):
        check(guard,deadline);plane=grid[k*n:(k+1)*n]
        require(np.array_equal(plane[:,:2],xy*1000)and np.allclose(plane[:,2],z[k]*1000,rtol=0,atol=1e-11)
            and np.all(plane[:,3]==layers[k]),'Exact actual coordinate/depth/layer alignment, not shape-only index reuse')
    del values,grid;gc.collect();return z,layers
@contextmanager
def operator(np,context,which,out,guard,deadline):
    import streamed_real_q
    Q=streamed_real_q.StreamedRealQ(np,context['cache_manifests'][which],context['remote_Q_chunk_proofs'][which],
        context['input_sha256'],guard,deadline_monotonic=deadline,cache_name='xy102'if which=='fine'else'xy100')
    try:
        with Q:yield Q
    finally:new(out/(which+'-streamed-Q-receipt.json'),Q.receipt())
def raw_arrays(solution,pads,cells,areas):
    return dict(modal_surface_coeff=solution['coeff'],phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],
        source_current_peak_A=solution['source_current'],contact_current_peak_A=solution['contact_current'],
        contact_normal_J_peak_A_m2=solution['contact_J'],contact_drop_peak_V=solution['contact_drop'],
        contact_pad=pads,contact_xy_index=cells,contact_area_m2=areas,layer_complex_power_W=solution['layer_power'])
def operator_evidence(out,which):
    path=out/(which+'-streamed-Q-receipt.json');value=json.loads(path.read_bytes())
    require(value['closed']is True and value['whole_Q_loaded']is False and value['complex_Q_materialized']is False
        and value['all_loaded_chunks_before_after_verified']is True and value['audit']['loaded_chunk_visits']>0,
        'Positive actual bounded-Q use, closed operator and unchanged chunk identities')
    return dict(path=str(path),SHA256=sha(path),bytes=path.stat().st_size)
def fine_frame(np,spec,out,guard,deadline):
    import ellipse_contact,fine_fields,fine_solver
    context=spec['inputs'];eigen,xy,ij=graph(np,context,'fine',guard,deadline)
    zs,layers=depth_binding(np,context,'fine',xy,guard,deadline)
    centres=exact_centres(context['E13_centroid_proof_value'])
    curve=ellipse_contact.contact_patches(centres,ij,h_mm=F(25,51),guard=guard,deadline=deadline)
    new(out/'fine-E13-contact-certificate.json',curve['receipt']);require(curve['receipt']['passed']is True
        and curve['receipt']['graph_nx']==102 and curve['receipt']['exact_h_mm']==dict(numerator=25,denominator=51),
        'New h-specific area/positive-support certificate; no area/fmin/body/centroid repair')
    lookup={(int(i),int(j)):k for k,(i,j)in enumerate(ij)};patch=curve['patches']
    pads=np.asarray([p['pad']for p in patch],np.int32);cells=np.asarray([lookup[int(p['i']),int(p['j'])]for p in patch],np.int32)
    areas=np.asarray([p['area_m2']for p in patch],float);h=.05/102
    require(np.all(areas>0)and np.all(areas<=h*h*(1+1e-10))and len(set(zip(pads.tolist(),cells.tolist())))==len(pads),
        'Actual positive unique fine contacts, no minimum-fraction pruning')
    for pad in range(4):require(abs(float(areas[pads==pad].sum())-.000225)/.000225<=1e-10,'Same225mm2/pad without scaling')
    require(np.max(np.bincount(cells,weights=areas,minlength=8184))<=h*h*(1+1e-10),'No physical contact overlap')
    with(out/'fine-E13-contact-mask.csv').open('x')as stream:
        stream.write('pad,i,j,area_m2\n'+'\n'.join(str(p['pad'])+','+str(p['i'])+','+str(p['j'])+','+format(p['area_m2'],'.17e')for p in patch)+'\n')
    result={};del curve,patch,lookup;gc.collect()
    with operator(np,context,'fine',out,guard,deadline)as Q:
        for frequency,output in((2000,0),(2010,1)):
            profile=fine_fields.profiles(np,Q,eigen,[cv(v)for v in context['gamma_by_frequency'][str(frequency)]],zs,h,guard,deadline)
            new(out/('checkpoint-fine-E13-'+str(frequency)+'-started.json'),dict(status='new_fine_RHS_started',frequency_Hz=frequency,
                active_output=output,maximum_new_driven_RHS=2,completed_new_RHS=len(result),fine_B0_repeated_RHS=0))
            solution=fine_solver.solve(np,Q,profile,pads,cells,areas,cv(context['z_by_frequency'][str(frequency)]),output,h,guard,deadline,cached=None)
            proof=solution['proof'];proof.update(candidate_id=ID,frequency_Hz=frequency,physical_pads=4,independent_outputs=2)
            new(out/'rhs'/('E13-XY102-'+str(frequency)+'-proof.json'),proof)
            require(proof['passed']and proof['actual_new_RHS']==1,'Unchanged fine source/current/power/passivity gate failure; no additional solve')
            phi,E,J=fine_fields.fields(np,Q,profile,solution['coeff'],ij,layers,h,guard,deadline)
            arrays=raw_arrays(solution,pads,cells,areas);arrays.update(phi_peak_V=phi,E_peak_V_m=E,interface_downward_J_peak_A_m2=J)
            desc=archive(np,out/'rhs'/('E13-XY102-'+str(frequency)+'-raw.npz'),arrays)
            result[str(frequency)]=dict(raw=desc,proof=proof)
            new(out/('checkpoint-fine-E13-'+str(frequency)+'-complete.json'),dict(status='new_fine_RHS_raw_saved',completed_new_RHS=len(result),raw=desc))
            del phi,E,J,arrays,solution,profile;gc.collect()
    operator_evidence(out,'fine');return dict(E13=result)
def coarse_frame(np,spec,out,guard,deadline):
    import fine_fields,fine_solver
    from unittest.mock import patch
    context=spec['inputs'];eigen,xy,ij=graph(np,context,'coarse',guard,deadline)
    zs,layers=depth_binding(np,context,'coarse',xy,guard,deadline);zs=zs[:4];layers=layers[:4];result={}
    with operator(np,context,'coarse',out,guard,deadline)as Q:
        for frequency,output in((2000,0),(2010,1)):
            original=load(np,context['coarse_raw']['E13'][str(frequency)],
                ['phi_surface_peak_V','metal_peak_V','modal_surface_coeff','contact_pad','contact_xy_index','contact_area_m2'],
                context['input_sha256'],guard,deadline)
            pads,cells,areas=original['contact_pad'],original['contact_xy_index'],original['contact_area_m2']
            require(original['phi_surface_peak_V'].shape==original['modal_surface_coeff'].shape==(7860,)
                and original['metal_peak_V'].shape==(2,)and pads.shape==cells.shape==areas.shape
                and set(pads.tolist())=={0,1,2,3}and np.all(areas>0),'Actual original coarse E13 cached ABI')
            for pad in range(4):require(abs(float(areas[pads==pad].sum())-.000225)/.000225<=1e-10,'Unchanged original coarse225mm2 contacts')
            profile=fine_fields.profiles(np,Q,eigen,[cv(v)for v in context['gamma_by_frequency'][str(frequency)]],zs,.0005,guard,deadline)
            def forbidden(*args,**kwargs):raise RuntimeError('Coarse E13 is cached only; new Krylov solve forbidden')
            with patch('scipy.sparse.linalg.gmres',side_effect=forbidden):
                solution=fine_solver.solve(np,Q,profile,pads,cells,areas,cv(context['z_by_frequency'][str(frequency)]),output,.0005,guard,deadline,
                    cached=dict(phi_surface=original['phi_surface_peak_V'],metal=original['metal_peak_V']))
            proof=solution['proof'];relative=float(np.linalg.norm(solution['coeff']-original['modal_surface_coeff']))/max(float(np.linalg.norm(original['modal_surface_coeff'])),spec['modal_norm_floor_V'])
            proof.update(candidate_id=ID,frequency_Hz=frequency,SC4_only=True,original_native_raw=context['coarse_raw']['E13'][str(frequency)],
                modal_restore_relative_error=relative,modal_restore_limit=spec['modal_restore_relative_limit'],new_Krylov_calls=0)
            new(out/'rhs'/('E13-XY100-SC4-'+str(frequency)+'-proof.json'),proof)
            require(proof['passed']and proof['actual_new_RHS']==0 and proof['iterations']==proof['matvec_count']==0
                and relative<=spec['modal_restore_relative_limit'],'Cached coarse fresh gates/modal mismatch; no solve or tolerance fallback')
            phi,E,J=fine_fields.fields(np,Q,profile,solution['coeff'],ij,layers,.0005,guard,deadline)
            arrays=raw_arrays(solution,pads,cells,areas);arrays.update(phi_SC4_peak_V=phi,E_SC4_peak_V_m=E)
            desc=archive(np,out/'rhs'/('E13-XY100-SC4-'+str(frequency)+'-raw.npz'),arrays);result[str(frequency)]=dict(raw=desc,proof=proof)
            del original,phi,E,J,arrays,solution,profile;gc.collect()
    operator_evidence(out,'coarse');return dict(E13=result)
def build(spec,guard,deadline_monotonic=None,output_dir=None):
    require(callable(guard)and spec==make_spec(spec['root_admission']),'Actual native-B0 publicPASS/newpositiveRoot/source/model binding')
    out=Path(output_dir or RUN);require(out==RUN and out.is_dir()and out==out.resolve()and not out.is_symlink()
        and not(out/'raw-manifest.json').exists(),'Unique canonical E13fine attempt; no old result overwrite')
    receipt=out/'synthetic-test-receipt.json';require(receipt.is_file()and not receipt.is_symlink()and receipt.stat().st_size<2*1024**2,
        'Actual local newh/shape source-bound manufactured tests required first')
    local=validate_local_MFG(json.loads(receipt.read_bytes()),spec['inputs']['source_sha256'],source_test_count());new(out/'before-new-RHS-MFG-proof.json',local)
    import numpy as np
    (out/'rhs').mkdir();context=spec['inputs'];manifest=dict(geometry=context['geometry'])
    manifest['fine']=separated_stage(lambda:fine_frame(np,spec,out,guard,deadline_monotonic))
    new(out/'fine-Q-release-boundary.json',dict(raw_frame_returned_only_JSON=True,new_driven_RHS=2,Q_passed_to_post=False))
    manifest['coarse_SC4']=separated_stage(lambda:coarse_frame(np,spec,out,guard,deadline_monotonic))
    manifest['operator_receipts']={which:operator_evidence(out,which)for which in('fine','coarse')}
    manifest['Q_frames_returned']=True;manifest['GC_before_postprocessing']=True
    new(out/'all-Q-release-boundary.json',dict(raw_frames_returned_only_JSON=True,new_driven_RHS=2,new_coarse_RHS=0,Q_passed_to_post=False))
    new(out/'raw-manifest.json',manifest)
    import e13_post
    return e13_post.build(np,spec,manifest,guard,deadline_monotonic,out)
