"""Deferred matched-depth B0/P23 metrics and physical-overlap comparison.

No I/O, scientific imports, arrays or calculations occur on import. Only the
sole owner calls build after every Q/profile/solver frame has exited and GC ran.
"""
from __future__ import annotations
import gc
import hashlib
import importlib
import json
import math
import time
from pathlib import Path

SOURCE = Path('/dev/shm/task1-P23-fineXY-20261025/source')
B0 = 'B0-square15-c10-diagonal'
P23 = 'P23p5-peripheral-polyomino225'
REGIONS = ('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
LAYERS = ('sc','dermis','fat','muscle')
SCALARS = ('AM_max2074','carrier_RMS','Jtotal_vector_RMS','AM_direction_index')
ALL_SCALARS = ('carrier_RMS','carrier0_RMS','carrier1_RMS','AM_x','AM_y','AM_z',
               'AM_max2074','AM_direction_index','Jtotal_vector_RMS')
CONTACT_KEYS = ('contact_normal_J_peak_A_m2','contact_drop_peak_V','contact_pad',
                'contact_xy_index','contact_area_m2','source_current_peak_A',
                'metal_peak_V','layer_complex_power_W')
MAX_FILE = 80 * 1024 ** 2


def require(ok,message):
    if not ok:raise ValueError(message)


def check(guard,deadline):
    guard()
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError('Fine-XY matched-depth postprocessing incomplete')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def new_json(path,value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode())


def complex_value(value):
    return complex(value['real'],value['imaginary']) if isinstance(value,dict) else complex(value)


def complex_pair(value):
    return dict(real=float(complex(value).real),imaginary=float(complex(value).imag))


def projection_summary(volume,reference_square_integral,fine_square_integral,difference_square_integral):
    """Pure scalar reduction of pairwise overlap-volume second moments."""
    require(all(math.isfinite(v) and v >= 0 for v in
                (volume,reference_square_integral,fine_square_integral,difference_square_integral)),
            'Finite nonnegative physical-volume overlap moments')
    if volume == 0:
        return dict(status='not_run_no_common_weighted_volume',common_volume_m3=0.)
    ref=math.sqrt(reference_square_integral/volume)
    fine=math.sqrt(fine_square_integral/volume)
    error=math.sqrt(difference_square_integral/volume)
    denominator=max(ref,1e-12)
    return dict(status='diagnostic_not_gated',common_volume_m3=volume,
                coarse_reference_spatial_norm=ref,fine_spatial_norm=fine,
                pairwise_primary_absolute_L2=error,pairwise_primary_normalized_L2=error/denominator,
                denominator=denominator,denominator_floor_V_m=1e-12,
                denominator_floor_used=ref < 1e-12,automatic_convergence_gate_applied=False,
                projected_average_secondary=dict(status='not_run',reason='Pairwise norm retains within-cell variation; no pre-averaging substitutes for it'))


def finite_accounting(records):
    require(len(records)==4,'Exactly four matched97 metric evaluations')
    identities={(row['grid_variant'],row['physical_geometry_id']) for row in records}
    require(identities=={(g,c) for g in ('XY102-Z97','XY100-Z97') for c in (B0,P23)},
            'Distinct physical geometry and numerical grid identities')
    require(all(type(row['metric_evaluations']) is int and row['metric_evaluations']==1 and row['candidate_adopted'] is False for row in records),
            'Four complete finite provisional metrics, no adoption')
    require(sum(row['angular_work']['full_field_evaluations'] for row in records)==2
            and sum(row['angular_work']['SC4_only_evaluations'] for row in records)==2
            and all(row['angular_work']['repeated_original_bulk_angular_evaluations']==0 for row in records),
            'Exactly two fine full and two SC4-only angular evaluations; no coarse bulk repeat')
    return dict(metric_evaluations=4,new_fine_driven_RHS=3,reused_fine_B0_2000_RHS=1,
                new_coarse_driven_RHS=0,new_eigen_solves=0,matched_depth_planes=97,
                full_angular_evaluations=2,SC4_only_angular_evaluations=2,
                repeated_original_bulk_angular_evaluations=0,duplicate_full_coarse_scalar_archives=0,
                original_coarse101_angular_evaluations_repeated=0,candidate_adopted=False)


def raw_accounting(manifest):
    counts={'fine':0,'coarse_SC4':0};reused=0
    for group in counts:
        require(set(manifest[group])=={'B0','P23'},'Exactly B0/P23 raw geometry variants')
        for name in ('B0','P23'):
            require(set(manifest[group][name])=={'2000','2010'},'Exactly two actual carrier entries')
            for frequency in ('2000','2010'):
                proof=manifest[group][name][frequency]['proof']
                expected=1 if group=='fine' and (name!='B0' or frequency!='2000') else 0
                actual=proof.get('actual_new_RHS')
                require(type(actual) is int and actual==expected,'Actual per-response RHS identity; never a fourth-RHS fallback')
                counts[group]+=actual
                if group=='fine' and actual==0:reused+=1
    require(counts=={'fine':3,'coarse_SC4':0} and reused==1,'Actual three new plus one fine reuse, no coarse PDE')
    return dict(actual_new_fine_driven_RHS=counts['fine'],actual_reused_fine_B0_2000_RHS=reused,
                actual_new_coarse_driven_RHS=counts['coarse_SC4'])


def _load(np,descriptor,keys,guard,deadline):
    check(guard,deadline)
    path=Path(descriptor['path'])
    require(path.is_absolute() and path==path.resolve() and path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size < MAX_FILE and digest(path)==descriptor['SHA256'],
            'Actual saved archive full SHA before decode: '+str(path))
    with np.load(path,allow_pickle=False) as saved:
        require(set(keys).issubset(saved.files),'Required actual archive ABI: '+str(path))
        arrays={key:np.array(saved[key],copy=True) for key in keys}
    require(all(np.isfinite(value).all() for value in arrays.values()),'Finite complete saved arrays')
    return arrays


def _archive(np,path,arrays):
    with Path(path).open('xb') as stream:np.savez_compressed(stream,**arrays)
    require(Path(path).stat().st_size<MAX_FILE,'Per-file 80MiB publication bound')
    return dict(path=str(path),bytes=Path(path).stat().st_size,SHA256=digest(path))


def _module(name,context):
    path=SOURCE/(name+'.py')
    require(str(path) in context['source_sha256'] and digest(path)==context['source_sha256'][str(path)],
            'Canonical source-bound postprocessing dependency')
    module=importlib.import_module(name)
    loaded=Path(module.__spec__.origin)
    # Runtime deployment authentication only. Spec/inventory identity above
    # always remains the fixed original SOURCE, including in a frozen child.
    deployed=Path(__file__).resolve().parent/(name+'.py')
    require(loaded.is_absolute() and loaded==loaded.resolve() and not loaded.is_symlink()
            and loaded in (path,deployed)
            and digest(loaded)==context['source_sha256'][str(path)],
            'Only canonical or same-directory byte-identical deployed dependency')
    return module


def _geometry(np,descriptor,nxy,guard,deadline):
    keys=['grid','ij','z_faces_m']+[r+'_volume_weight_m3' for r in REGIONS]
    value=_load(np,descriptor,keys,guard,deadline)
    grid=value['grid'];faces=value['z_faces_m']
    require(grid.shape==(97*nxy,5) and value['ij'].shape==(nxy,2) and faces.shape==(98,),
            'Exact matched97 geometry archive ABI')
    require(np.all(np.diff(faces)>0) and abs(float(faces[0]))<1e-15
            and abs(float(faces[-1])-.0251)<1e-14,'Fixed physical layer depth bounds')
    centres=(faces[:-1]+faces[1:])/2.
    require(np.allclose(grid[:,2],np.repeat(centres*1000,nxy),rtol=0,atol=1e-11)
            and np.array_equal(grid[:,3],np.repeat(np.repeat(np.arange(4),[4,19,18,56]),nxy))
            and np.array_equal(grid[:,:2],np.tile(grid[:nxy,:2],(97,1))),
            'Actual physical centre-depth/XY/layer ordering')
    weights={r:value[r+'_volume_weight_m3'] for r in REGIONS}
    require(all(w.shape==(len(grid),) and np.all(w>=0) for w in weights.values())
            and np.allclose(weights['total'],grid[:,4],rtol=1e-12,atol=1e-25)
            and np.allclose(weights['target']+weights['off_target'],weights['total'],rtol=1e-12,atol=1e-25)
            and np.allclose(weights['surface_0_5']+weights['subsurface_5_10']+weights['target']+weights['remaining'],weights['total'],rtol=1e-12,atol=1e-25),
            'Unchanged six physical fractional-volume definitions')
    return dict(grid=grid,ij=value['ij'],z_faces_m=faces,weights=weights,nxy=nxy)


def _old_bulk_binding(np,context,coarse,guard,deadline):
    original=_load(np,context['common_grid_original'],['grid','z_faces_m'],guard,deadline)
    grid=original['grid'];n=coarse['nxy'];new=coarse['grid']
    require(grid.shape==(101*n,5) and np.array_equal(grid[:n,:2],new[:n,:2]),
            'Same actual coarse XY row order before SC-only supplement assembly')
    require(np.array_equal(grid[8*n:,2:],new[4*n:,2:]),
            'Original93 bulk planes retain EXACT physical z/layer/volume identity')
    require(np.array_equal(original['z_faces_m'][8:],coarse['z_faces_m'][4:]),
            'Exact original coarse bulk faces; no nearest-plane substitution')
    return dict(passed=True,original_planes=101,new_planes=97,replaced_SC_planes=[8,4],
                untouched_bulk_planes=93,XY_row_order_identical=True,
                bulk_z_layer_volume_and_faces_identical=True,bulk_raw_duplicated=False)


def _carrier(np,context,manifest,grid_name,name,frequency,guard,deadline):
    group='fine' if grid_name=='XY102-Z97' else 'coarse_SC4'
    entry=manifest[group][name][frequency]
    proof=entry['proof']
    require(proof.get('passed') is True and proof.get('physical_gates',{}).get('passed') is True,
            'Passed actual frequency-specific signed-circuit proof required')
    if 'frequency_Hz' in proof:require(proof['frequency_Hz']==int(frequency),'Proof carrier identity')
    require(proof.get('driven_output')==(0 if frequency=='2000' else 1),'Original carrier/output assignment')
    if group=='fine':
        raw=_load(np,entry['raw'],list(CONTACT_KEYS)+['E_peak_V_m'],guard,deadline)
        require(raw['E_peak_V_m'].shape==(793848,3),'Fine full97-plane E ABI')
    else:
        supplement=_load(np,entry['raw'],list(CONTACT_KEYS)+['E_SC4_peak_V_m'],guard,deadline)
        old=_load(np,context['coarse_raw'][name][frequency],list(CONTACT_KEYS)+['E_peak_V_m'],guard,deadline)
        require(old['E_peak_V_m'].shape==(793860,3) and supplement['E_SC4_peak_V_m'].shape==(4*7860,3),
                'SC4-only supplement plus actual original101-plane E')
        for key in CONTACT_KEYS:
            require(supplement[key].shape==old[key].shape
                    and np.allclose(supplement[key],old[key],rtol=1e-12,atol=1e-20),
                    'SC resampling cannot change cached coarse circuit/contact/layer values: '+key)
        raw={key:supplement[key] for key in CONTACT_KEYS}
        raw['E_peak_V_m']=np.concatenate((supplement['E_SC4_peak_V_m'],old['E_peak_V_m'][8*7860:]),axis=0)
        del old,supplement
        require(raw['E_peak_V_m'].shape==(762420,3),'Assembled matched97 coarse E without bulk archive duplication')
    return raw,proof


def _electrical(np,raws,proofs):
    require(np.array_equal(raws[0]['contact_pad'],raws[1]['contact_pad'])
            and np.array_equal(raws[0]['contact_xy_index'],raws[1]['contact_xy_index'])
            and np.array_equal(raws[0]['contact_area_m2'],raws[1]['contact_area_m2']),
            'Same physical contact tuple/order at both carriers')
    areas=raws[0]['contact_area_m2'];pads=raws[0]['contact_pad']
    require(areas.ndim==1 and np.all(areas>0) and set(np.unique(pads).tolist())=={0,1,2,3},
            'Four original physical pads and positive actual fractional areas')
    for pad in range(4):
        require(abs(float(areas[pads==pad].sum())-.000225)<=1e-10*.000225,'225mm2 physical pad, no rescale')
    I2=np.zeros(2);J2=np.zeros(len(areas));V2=np.zeros(len(areas));layers=np.zeros(4,complex)
    source=0j;contact=0j;resistor=0.;spectral=[]
    for output,(raw,proof) in enumerate(zip(raws,proofs)):
        I=raw['source_current_peak_A'];metal=raw['metal_peak_V'];power=raw['layer_complex_power_W']
        require(I.shape==metal.shape==(2,) and power.shape==(4,), 'Original two-output/four-layer circuit ABI')
        ideal=np.zeros(2,complex);ideal[output]=.5
        require(float(np.max(abs(metal+50*I-ideal)))<=1e-10+2e-7*.5,'Original loaded50ohm source relation')
        S=complex_value(proof['source_complex_power_W']);C=complex_value(proof['contact_complex_power_W']);R=float(proof['source_resistor_power_W'])
        require(math.isfinite(R) and R>=0 and abs(R-.5*50*float(np.sum(abs(I)**2)))<=2e-7*max(R,1e-12),
                'All active and induced inactive resistor losses retained')
        require(abs(S-complex(power.sum())-C-R)<=2e-7*max(abs(S),abs(complex(power.sum())+C+R),1e-12),
                'Saved signed complex layer/contact/source/50ohm power balance')
        I2+=abs(I)**2/2.;J2+=abs(raw['contact_normal_J_peak_A_m2'])**2/2.;V2+=abs(raw['contact_drop_peak_V'])**2/2.
        layers+=power;source+=S;contact+=C;resistor+=R
        spectral.append(dict(frequency_Hz=2000+10*output,active_output=output,
            source_current_peak_A=[complex_pair(v) for v in I],
            source_complex_power_W=complex_pair(S),contact_complex_power_W=complex_pair(C),
            layer_complex_power_W=[complex_pair(v) for v in power],source_resistor_power_W=R,
            signed_complex_power_sum_W=complex_pair(complex(power.sum())+C+R)))
    J=np.sqrt(J2);order=np.argsort(J,kind='stable');at=min(int(np.searchsorted(np.cumsum(areas[order]),.95*float(areas.sum()),side='left')),len(order)-1)
    currents=np.sqrt(I2)
    # Legacy metric normalization expects scalar *_power_W fields. Signed
    # complex power dictionaries are preserved separately in spectral metadata.
    electrical=dict(source_Vpp_each=1.,source_current_RMS_by_output_A=currents.tolist(),
        sum_output_current_RMS_A_bookkeeping=float(currents.sum()),source_power_W=float(source.real),
        layers_power_W={name:float(layers[i].real) for i,name in enumerate(LAYERS)},
        SC_power_W=float(layers[0].real),skin_power_W=float(layers[:2].real.sum()),
        contact_power_W=float(contact.real),source_resistor_power_W=resistor,
        contact_normal_J_RMS_max_A_m2=float(J.max()),contact_normal_J_RMS_P95_A_m2=float(J[order[at]]),
        contact_voltage_RMS_max_V=float(np.sqrt(V2.max())))
    return electrical,spectral


def _am_reference(metrics):
    r=metrics['regions'];t=r['target']['statistics']['maxTIS'];mean=float(t['mean'])
    return dict(target_mean=mean,target_P10=float(t['p10']),
        target_to_surface=mean/float(r['surface_0_5']['statistics']['maxTIS']['mean']),
        target_to_offtarget=mean/float(r['off_target']['statistics']['maxTIS']['mean']))


def _ratio4(value,reference):
    require(all(math.isfinite(reference[k]) and reference[k]>0 for k in reference),'Positive actual original AM ratio denominators')
    ratios={k:float(value[k])/reference[k] for k in reference}
    return dict(four_ratios=ratios,minimum_four_ratio=min(ratios.values()))


def _normalization_scores(normalizations,reference):
    result={}
    for mode,row in normalizations['comparisons'].items():
        if row['status']!='calculated_global_amplitude_rescaling':result[mode]=dict(status=row['status']);continue
        fields=row['absolute_ROI_fields_V_m'];target=fields['target']['maxTIS']
        value=dict(target_mean=target['mean'],target_P10=target['p10'],
            target_to_surface=target['mean']/fields['surface_0_5']['maxTIS']['mean'],
            target_to_offtarget=target['mean']/fields['off_target']['maxTIS']['mean'])
        result[mode]=dict(_ratio4(value,reference),amplitude_scale=row['amplitude_scale'])
    return result


def _metric_case(np,spec,manifest,geometry,grid_name,name,metrics,guard,deadline,out):
    context=spec['inputs'];cid=B0 if name=='B0' else P23
    case_id=cid+'-'+grid_name
    raws=[];proofs=[]
    for frequency in ('2000','2010'):
        raw,proof=_carrier(np,context,manifest,grid_name,name,frequency,guard,deadline)
        raws.append(raw);proofs.append(proof)
    electrical,spectral=_electrical(np,raws,proofs)
    gamma=[np.asarray([complex_value(v) for v in context['gamma_by_frequency'][frequency]]) for frequency in ('2000','2010')]
    scalar_assembly=None
    if grid_name=='XY102-Z97':
        result=metrics.evaluate(np,geometry['grid'],geometry['weights'],raws[0]['E_peak_V_m'],raws[1]['E_peak_V_m'],gamma[0],gamma[1],electrical,guard,deadline)
        selected={key:result['arrays'][key] for key in SCALARS}
        archive=_archive(np,out/(case_id+'-scalars.npz'),selected)
        scalar_kind='full_new_fine97'
        angular_work=dict(full_field_evaluations=1,SC4_only_evaluations=0,
                          newly_scanned_cells=793848,reused_original_bulk_cells=0,
                          repeated_original_bulk_angular_evaluations=0)
    else:
        cut=4*7860
        sc=metrics.evaluate(np,geometry['grid'][:cut],{key:value[:cut] for key,value in geometry['weights'].items()},
            raws[0]['E_peak_V_m'][:cut],raws[1]['E_peak_V_m'][:cut],gamma[0],gamma[1],electrical,guard,deadline)
        original_descriptor=context['coarse_scalars'][name]
        original=_load(np,original_descriptor,list(ALL_SCALARS),guard,deadline)
        require(all(value.shape==(793860,) for value in original.values()),'Actual original101 scalar ABI for exact93-plane bulk reuse')
        require(np.issubdtype(original['AM_direction_index'].dtype,np.integer)
                and np.all((original['AM_direction_index']>=0)&(original['AM_direction_index']<2074)),
                'Original completed2074-direction winner indices')
        composed={key:np.concatenate((sc['arrays'][key],original[key][8*7860:])) for key in ALL_SCALARS}
        del original
        cached=_module('cached_metrics',context)
        result=cached.summarize(np,geometry['grid'],geometry['weights'],composed,electrical,
                               raws[0]['E_peak_V_m'],raws[1]['E_peak_V_m'],guard,deadline)
        selected={key:sc['arrays'][key] for key in SCALARS}
        archive=_archive(np,out/(case_id+'-SC4-scalars.npz'),selected)
        scalar_kind='SC4_patch_plus_authenticated_original_bulk93'
        scalar_assembly=dict(status='authenticated_original93_bulk_scalars_reused_new_SC4_only',
            original_scalar_archive=original_descriptor,original_full_cells=793860,
            original_bulk_selection=dict(start=8*7860,stop=793860,depth_planes=93),
            new_SC4_patch=archive,new_SC4_cells=cut,logical_common97_cells=762420,
            scalar_keys_reused=list(ALL_SCALARS),same_two_carriers_gamma_contacts=True,
            same_bulk_physical_z_layer_volumes_proof='coarse-common97-original93-bulk-binding.json',
            source_grid_and_field_estimator_preserved=True,original_bulk_angular_scan_repeated=False,
            full_coarse_scalar_archive_written=False)
        new_json(out/(case_id+'-scalar-assembly-proof.json'),scalar_assembly)
        angular_work=dict(full_field_evaluations=0,SC4_only_evaluations=1,
                          newly_scanned_cells=cut,reused_original_bulk_cells=93*7860,
                          repeated_original_bulk_angular_evaluations=0)
        del composed,sc
    del raws
    summary=result['summary'];summary['numerical_grid_variant']=grid_name
    for region in summary['regions'].values():
        for values in region['statistics'].values():
            if values.get('status')=='complete':values['CV']=float(values['std']/values['mean']) if values['mean']>0 else None
    original=context['coarse_B0_record']['metrics']
    normalizations=metrics.normalize(summary,original)
    require(normalizations['status']=='complete','Original four independent fixed-cap normalizations complete')
    record=dict(candidate_id=case_id,physical_geometry_id=cid,grid_variant=grid_name,
        physical_mask_variant='Original225mm2 physical union with grid-specific contact integration',
        metrics=summary,normalizations_to_original_coarse101_B0=normalizations,
        min4_to_original_coarse101_B0=_normalization_scores(normalizations,_am_reference(original)),
        per_frequency_signed_circuit=spectral,source_physics_proofs=proofs,
        scalar_arrays=archive,scalar_archive_kind=scalar_kind,scalar_assembly_proof=scalar_assembly,
        saved_scalar_names=list(SCALARS),metric_evaluations=1,angular_work=angular_work,
        sampled_directions=2074,full_convergence=False,Q_resident_during_metrics=False,
        candidate_adopted=False)
    del result,selected
    gc.collect();check(guard,deadline)
    return record


def _depth_overlap(a,b,lo,hi):return max(0.,min(b,hi)-max(a,lo))


def relative_diagnostic(reference,value,limit,units):
    require(all(math.isfinite(v) for v in (reference,value,limit)) and limit>0,'Finite prospective diagnostic')
    denominator=max(abs(reference),1e-12);difference=abs(value-reference)
    relative=difference/denominator
    return dict(reference=float(reference),value=float(value),absolute_difference=float(difference),
        relative_difference=float(relative),relative_limit=float(limit),passed=relative<=limit,
        units=units,denominator=float(denominator),denominator_floor=1e-12,
        denominator_floor_used=abs(reference)<1e-12,
        interpretation='Prospective adjacent-grid numerical diagnostic only; does not clear old failures or establish convergence/safety')


def _adjacent_diagnostics(records):
    lookup={(r['grid_variant'],r['physical_geometry_id']):r for r in records};rows=[]
    for cid in (B0,P23):
        coarse=lookup['XY100-Z97',cid]['metrics'];fine=lookup['XY102-Z97',cid]['metrics'];checks=[]
        for name in ('mean','p10'):
            a=coarse['regions']['target']['statistics']['maxTIS'][name];b=fine['regions']['target']['statistics']['maxTIS'][name]
            checks.append(dict(metric='target_AM_'+name,**relative_diagnostic(float(a),float(b),.01,'V/m')))
        for name in ('contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2',
                     'skin_vector_J_RMS_max_A_m2','skin_vector_J_RMS_P95_A_m2','contact_voltage_RMS_max_V'):
            checks.append(dict(metric=name,**relative_diagnostic(float(coarse['electrical'][name]),float(fine['electrical'][name]),.05,'V' if name.endswith('_V') else 'A/m2')))
        for name in ('SC_power_W','skin_power_W','contact_power_W','source_power_W','source_resistor_power_W'):
            checks.append(dict(metric=name,**relative_diagnostic(float(coarse['electrical'][name]),float(fine['electrical'][name]),.02,'W')))
        for output in (0,1):
            checks.append(dict(metric='output%d_two_carrier_RMS_A'%output,
                **relative_diagnostic(float(coarse['electrical']['source_current_RMS_by_output_A'][output]),
                                      float(fine['electrical']['source_current_RMS_by_output_A'][output]),.05,'A')))
        for layer in LAYERS:
            checks.append(dict(metric='layer_'+layer+'_power_W',
                **relative_diagnostic(float(coarse['electrical']['layers_power_W'][layer]),
                                      float(fine['electrical']['layers_power_W'][layer]),.02,'W')))
        rows.append(dict(physical_geometry_id=cid,reference_grid='XY100-Z97',candidate_grid='XY102-Z97',
                         rows=checks,passed_count=sum(row['passed'] for row in checks),
                         failed_count=sum(not row['passed'] for row in checks),
                         old_13_of_14_and_interface_failures_cleared=False,full_convergence=False))
    return rows


def _projection(np,coarse,fine,links,disk_area,faces,guard,deadline):
    nzc,nc=coarse.shape[:2];nzf,nf=fine.shape[:2]
    require(nzc==nzf==97,'Only exactly matched97 depths enter physical projection')
    ci=links['coarse_index'];fi=links['fine_index'];area=links['area_m2']
    moments={r:[0.,0.,0.,0.] for r in REGIONS}
    for iz in range(97):
        check(guard,deadline);a=coarse[iz,ci];b=fine[iz,fi]
        if a.ndim==2:
            ref=np.sum(abs(a)**2,axis=1);other=np.sum(abs(b)**2,axis=1);delta=np.sum(abs(a-b)**2,axis=1)
        else:ref=abs(a)**2;other=abs(b)**2;delta=abs(a-b)**2
        z0,z1=float(faces[iz]),float(faces[iz+1]);total=area*(z1-z0)
        target=disk_area*_depth_overlap(z0,z1,.015,.020)
        surface=area*_depth_overlap(z0,z1,0.,.005);sub=area*_depth_overlap(z0,z1,.005,.010)
        weights=dict(total=total,target=target,surface_0_5=surface,subsurface_5_10=sub,
                     remaining=total-surface-sub-target,off_target=total-target)
        for region,w in weights.items():
            require(float(w.min())>=-1e-24,'Physical overlap partition cannot have negative volume')
            w=np.maximum(w,0.)
            row=moments[region];row[0]+=float(w.sum());row[1]+=float(np.dot(w,ref));row[2]+=float(np.dot(w,other));row[3]+=float(np.dot(w,delta))
    return {region:projection_summary(*row) for region,row in moments.items()}


def _case_scalars(np,context,record,name,keys,guard,deadline):
    saved=_load(np,record['scalar_arrays'],keys,guard,deadline)
    if record['scalar_archive_kind']=='full_new_fine97':
        require(all(v.shape==(793848,) for v in saved.values()),'Fine97 full scalar identity')
        return saved
    require(record['scalar_archive_kind']=='SC4_patch_plus_authenticated_original_bulk93'
            and all(v.shape==(4*7860,) for v in saved.values()),'SC4-only scalar patch identity')
    old=_load(np,context['coarse_scalars'][name],keys,guard,deadline)
    require(all(v.shape==(793860,) for v in old.values()),'Authenticated original101 bulk scalars')
    return {key:np.concatenate((saved[key],old[key][8*7860:])) for key in keys}


def _cross_grid(np,spec,manifest,geometry,records,projector,guard,deadline,out):
    coarse=geometry['XY100-Z97'];fine=geometry['XY102-Z97']
    require(np.array_equal(coarse['z_faces_m'],fine['z_faces_m']), 'Exact common physical97 depth faces')
    links=projector.build_overlap(coarse['grid'][:7860,:2],.5,fine['grid'][:8184,:2],50./102,lambda:check(guard,deadline))
    disk=projector.analyticdisk_rect_area(links['rectangle_mm'],5.)
    require(abs(float(disk.sum())-math.pi*25.e-6)<=1e-9*math.pi*25.e-6,
            'Target disk fully represented on common physical overlap, without area renormalization')
    link_archive=_archive(np,out/'physical-common-overlap-links.npz',dict(
        coarse_index=links['coarse_index'],fine_index=links['fine_index'],area_m2=links['area_m2'],
        rectangle_mm=links['rectangle_mm'],target_disk_intersection_area_m2=disk))
    lookup={(r['grid_variant'],r['physical_geometry_id']):r for r in records}
    rows=[]
    for name,cid in (('B0',B0),('P23',P23)):
        carriers={}
        for frequency in ('2000','2010'):
            a,_=_carrier(np,spec['inputs'],manifest,'XY100-Z97',name,frequency,guard,deadline)
            b,_=_carrier(np,spec['inputs'],manifest,'XY102-Z97',name,frequency,guard,deadline)
            carriers[frequency]=_projection(np,a['E_peak_V_m'].reshape((97,7860,3)),b['E_peak_V_m'].reshape((97,8184,3)),links,disk,coarse['z_faces_m'],guard,deadline)
            del a,b;gc.collect()
        a=_case_scalars(np,spec['inputs'],lookup['XY100-Z97',cid],name,['AM_max2074','carrier_RMS'],guard,deadline)
        b=_case_scalars(np,spec['inputs'],lookup['XY102-Z97',cid],name,['AM_max2074','carrier_RMS'],guard,deadline)
        scalars={key:_projection(np,a[key].reshape((97,7860)),b[key].reshape((97,8184)),links,disk,coarse['z_faces_m'],guard,deadline) for key in ('AM_max2074','carrier_RMS')}
        del a,b;gc.collect()
        rows.append(dict(physical_geometry_id=cid,carrier_peak_complex_vector_comparison=carriers,
            native_own_carrier_scalar_comparison=scalars,
            primary='Pairwise physical-overlap-volume L2; no pre-averaging, no potential/gauge/phase fit',
            AM_definition='Each grid independently evaluates its own carriers over the exact same2074 directions before scalar comparison',
            unmatched_native_domain=dict(coarse=links['summary']['coarse'],fine=links['summary']['fine']),
            automatic_convergence_or_activation_gate_applied=False))
    return dict(schema='task1-P23-fineXY-physical-overlap-v1',overlap=links['summary'],
        overlap_links=link_archive,depth_faces_matched_exactly=True,target_disk_radius_mm=5.,
        comparisons=rows,whole_native_domain_metrics_preserved_separately=True,
        unmatched_volume_m3={name:links['summary'][name]['unmatched_area_m2']*.0251 for name in ('coarse','fine')},
        candidate_adopted=False)


def build(np,spec,raw_manifest,guard,deadline,out):
    """Run only after the caller proves every raw Q frame returned and GC ran."""
    check(guard,deadline);out=Path(out);context=spec['inputs']
    require(raw_manifest.get('Q_frames_returned') is True and raw_manifest.get('GC_before_postprocessing') is True,
            'Every raw Q/profile/solver frame must return and GC finish before postprocessing')
    actual_rhs=raw_accounting(raw_manifest)
    require(out.is_absolute() and out==out.resolve() and out.is_dir() and not out.is_symlink(), 'Owner-created canonical output')
    metrics=_module('screen_metrics',context);projector=_module('physical_projector',context)
    geometry={name:_geometry(np,raw_manifest['geometry'][key],n,guard,deadline)
              for name,key,n in (('XY102-Z97','fine',8184),('XY100-Z97','coarse',7860))}
    binding=_old_bulk_binding(np,context,geometry['XY100-Z97'],guard,deadline)
    new_json(out/'coarse-common97-original93-bulk-binding.json',binding)
    records=[]
    for grid_name in ('XY102-Z97','XY100-Z97'):
        for name in ('B0','P23'):
            records.append(_metric_case(np,spec,raw_manifest,geometry[grid_name],grid_name,name,metrics,guard,deadline,out))
            new_json(out/('checkpoint-metrics-%d.json'%len(records)),dict(status='matched97_metrics_complete',complete_metric_cases=len(records),Q_resident_during_metrics=False))
    accounting=finite_accounting(records)
    fine_b0=next(r for r in records if r['grid_variant']=='XY102-Z97' and r['physical_geometry_id']==B0)
    for row in records:
        if row['grid_variant']=='XY102-Z97':
            row['secondary_fine_B0_derived_caps']=dict(scope='Explicit secondary comparison only; original coarse101 B0 caps above are unchanged',
                normalizations=metrics.normalize(row['metrics'],fine_b0['metrics']))
        new_json(out/(row['candidate_id']+'-summary.json'),row)
    cross=_cross_grid(np,spec,raw_manifest,geometry,records,projector,guard,deadline,out)
    new_json(out/'cross-grid-physical-comparison.json',cross)
    diagnostics=_adjacent_diagnostics(records)
    new_json(out/'prospective-adjacent-grid-diagnostics.json',diagnostics)
    summary=dict(schema='task1-P23-fineXY-post-result-v1',status='four_matched97_metric_cases_and_physical_overlap_computed_unadopted',
        candidates=records,comparison_accounting=dict(accounting,**actual_rhs),physical_overlap_comparison=cross,
        actual_new_driven_RHS=actual_rhs['actual_new_fine_driven_RHS'],
        actual_reused_fine_B0_2000_RHS=actual_rhs['actual_reused_fine_B0_2000_RHS'],
        actual_new_coarse_driven_RHS=0,actual_new_metric_evaluations=4,
        actual_full_angular_evaluations=2,actual_SC4_only_angular_evaluations=2,
        actual_repeated_original_bulk_angular_evaluations=0,
        actual_duplicate_full_coarse_scalar_archives=0,new_eigen_solves=0,
        prospective_adjacent_grid_diagnostics=diagnostics,
        coarse_common97_bulk_binding=binding,
        original_coarse101_records_preserved=dict(B0=context['coarse_B0_record'],P23=context['P23record']),
        original_fine_electrical_comparison=context['old_fine_electrical_screen'],
        normalization_reference='Original published first-eight coarse101 B0 numerical caps; fine-B0-derived caps explicitly secondary',
        fields=dict(angular_lower_bound_directions=2074,AM_is_not_carrier_RMS=True,
                    lateral='Frozen native half-face XY estimator with actual spacing',
                    normal='Analytic same-depth J/gamma; interface currents never interpolated into centre E'),
        diagnostics_not_run=dict(high_modulation_volume='No prospective numerical cutoff supplied; no fabricated physiological threshold',
                                  same_candidate_probe_prediction='Deferred until successful field comparison review',
                                  full_mesh_convergence='Adjacent XY100/102 check cannot establish full convergence'),
        holds=dict(old_13_of_14_electrical_failures_per_basis_preserved=True,
            old_independent_5percent_interface_failures_preserved=True,
            SC_XY_contact_edge_material_uncertainty_preserved=True,full_convergence=False,
            physiological_activation_or_safety_claim=False,experimental_validation=False,
            candidate_adopted=False),Q_resident_during_postprocessing=False,candidate_adopted=False)
    check(guard,deadline)
    return dict(summary=summary,arrays={})
