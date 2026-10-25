"""Deferred E13 matched97 metrics; no IO, science imports or work on import.

Root calls only after raw Q/solver/profile frames returned and GC completed.
The functions listed in FROZEN_FUNCTIONS are copied verbatim from authenticated
fine_post.py. New coarse scalar assembly deliberately supports only the four
actually saved E13 scalar arrays; missing axes/carrier splits stay unavailable.
"""
import copy,gc,hashlib,importlib,json,math,time
from pathlib import Path
SOURCE=Path('/dev/shm/task1-E13-fineXY-20261025/source')
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
LAYERS=('sc','dermis','fat','muscle')
SCALARS=('AM_max2074','carrier_RMS','Jtotal_vector_RMS','AM_direction_index')
ALL_FINE_SCALARS=('carrier_RMS','carrier0_RMS','carrier1_RMS','AM_x','AM_y','AM_z','AM_max2074','AM_direction_index','Jtotal_vector_RMS')
CONTACT_KEYS=('contact_normal_J_peak_A_m2','contact_drop_peak_V','contact_pad','contact_xy_index','contact_area_m2','source_current_peak_A','metal_peak_V','layer_complex_power_W')
MAX_FILE=80*1024**2
COARSE_UNAVAILABLE=('X_TIS','Y_TIS','Z_TIS','carrier0_RMS','carrier1_RMS')
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
FROZEN_FUNCTIONS=('require', 'check', 'digest', 'new_json', 'complex_value', 'complex_pair', 'projection_summary', '_load', '_archive', '_module', '_geometry', '_old_bulk_binding', '_electrical', '_am_reference', '_ratio4', '_normalization_scores', '_depth_overlap', 'relative_diagnostic', '_projection')

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


def raw_accounting(manifest):
    require(manifest.get('Q_frames_returned')is True and manifest.get('GC_before_postprocessing')is True,
            'All actual Q/profile/solver frames returned and GC completed')
    count={'fine':0,'coarse_SC4':0}
    for group in count:
        require(set(manifest[group])=={'E13'},'Only the unchanged physical E13 geometry has new raw frames')
        require(set(manifest[group]['E13'])=={'2000','2010'},'Exactly two original carrier frames')
        for frequency,output in (('2000',0),('2010',1)):
            p=manifest[group]['E13'][frequency]['proof'];expected=1 if group=='fine'else 0
            require(type(p.get('actual_new_RHS'))is int and p['actual_new_RHS']==expected,
                    'Exactly two new fine RHS, zero cached coarse RHS and no fallback')
            require(p.get('passed')is True and p.get('physical_gates',{}).get('passed')is True
                    and p.get('passivity_passed')is True and p.get('frequency_Hz')==int(frequency)
                    and p.get('driven_output')==output,'Actual frequency/output/five-gate/passivity linkage')
            count[group]+=p['actual_new_RHS']
    return dict(actual_new_fine_driven_RHS=count['fine'],actual_new_coarse_driven_RHS=count['coarse_SC4'],
                actual_control_RHS_repeated=0,actual_new_eigen_solves=0)


def finite_accounting(records):
    require(len(records)==2 and {r['grid_variant']for r in records}=={'XY102-Z97','XY100-Z97'},
            'Exactly one fine full and one coarse common97 E13 metric case')
    require(len({r['physical_geometry_id']for r in records})==1
            and all(type(r['metric_evaluations'])is int and r['metric_evaluations']==1
                    and r['candidate_adopted']is False for r in records),'One unchanged E13 physical geometry, two numerical grids')
    for r in records:
        w=r['angular_work'];fine=r['grid_variant']=='XY102-Z97'
        expected=dict(full_field_evaluations=int(fine),SC4_only_evaluations=int(not fine),
                      repeated_original_bulk_angular_evaluations=0)
        require(all(type(w.get(k))is int and w[k]==v for k,v in expected.items()),'Exact full/SC4 angular work; no original bulk scan')
    return dict(metric_evaluations=2,full_angular_evaluations=1,SC4_only_angular_evaluations=1,
                repeated_original_bulk_angular_evaluations=0,original_coarse101_angular_evaluations_repeated=0,
                duplicate_full_coarse_scalar_archives=0,immutable_fine_B0_control_aliases=1,
                control_metric_evaluations_repeated=0,control_RHS_repeated=0,candidate_adopted=False)


def scalar_assembly_description(original_descriptor,patch_descriptor):
    return dict(status='authenticated_original93_bulk_four_scalars_reused_new_SC4_only',
        original_scalar_archive=copy.deepcopy(original_descriptor),original_full_cells=101*7860,
        original_bulk_selection=dict(start=8*7860,stop=101*7860,depth_planes=93),
        new_SC4_patch=copy.deepcopy(patch_descriptor),new_SC4_cells=4*7860,logical_common97_cells=97*7860,
        scalar_keys_reused=list(SCALARS),unavailable_coarse_statistics=list(COARSE_UNAVAILABLE),
        same_bulk_physical_z_layer_volumes_proof='coarse-common97-original93-bulk-binding.json',
        original_bulk_angular_scan_repeated=False,full_coarse_scalar_archive_written=False,
        missing_scalar_values_invented=False)


def fine_B0_alias(context):
    original=context['fine_B0_record'];row=copy.deepcopy(original)
    require(original.get('candidate_adopted')is False and original.get('grid_variant')=='XY102-Z97'
            and original.get('physical_geometry_id')=='B0-square15-c10-diagonal','Only actual full fineB0 reference record')
    row.update(control_alias=True,alias_source_raw_by_frequency=copy.deepcopy(context['fine_B0_raw_by_frequency']),
        alias_source_scalar=copy.deepcopy(context['fine_B0_scalar']),alias_provenance=copy.deepcopy(context['fine_B0_provenance']),
        new_PDE_RHS=0,new_angular_metric_evaluations=0,control_field_reconstruction_repeated=False,
        control_statistics_recomputed=False,candidate_adopted=False)
    return row


def objective_vector(normalized):
    result=dict(target_mean=None,target_P10=None,target_to_surface_mean=None,target_to_offtarget_mean=None)
    if normalized.get('status')!='calculated_global_amplitude_rescaling':return result
    fields=normalized.get('absolute_ROI_fields_V_m',{});target=fields.get('target',{}).get('maxTIS',{})
    def number(value):
        return float(value)if type(value)in(int,float)and math.isfinite(value)else None
    mean=number(target.get('mean'));p10=number(target.get('p10'))
    surface=number(fields.get('surface_0_5',{}).get('maxTIS',{}).get('mean'))
    off=number(fields.get('off_target',{}).get('maxTIS',{}).get('mean'))
    result.update(target_mean=mean,target_P10=p10,
        target_to_surface_mean=mean/surface if mean is not None and surface is not None and surface>0 else None,
        target_to_offtarget_mean=mean/off if mean is not None and off is not None and off>0 else None)
    return result


def objective_score(value,baseline):
    ratios={k:value[k]/baseline[k]if value[k]is not None and baseline[k]is not None and baseline[k]>0 else None for k in baseline}
    losses={k:(value[k]<baseline[k]if value[k]is not None and baseline[k]is not None else None)for k in ('target_mean','target_P10')}
    ratio_gain=any(value[k]is not None and baseline[k]is not None and value[k]>baseline[k]for k in ('target_to_surface_mean','target_to_offtarget_mean'))
    return dict(objectives=copy.deepcopy(value),four_ratios_to_fine_B0=ratios,
        robust_minimum_four_ratio=min(ratios.values())if all(v is not None for v in ratios.values())else None,
        absolute_target_losses=losses,ratio_only_improvement_with_absolute_loss=bool(any(v is True for v in losses.values())and ratio_gain))


def strict_pareto(vectors):
    result={}
    for ident,value in vectors.items():
        if any(v is None for v in value.values()):
            result[ident]=dict(status='not_ranked_missing_objective',dominated_by=[]);continue
        dominated=[]
        for other,alternative in vectors.items():
            if other==ident or any(v is None for v in alternative.values()):continue
            require(set(alternative)==set(value),'Exactly identical four-objective definitions')
            if all(alternative[k]>=value[k]for k in value)and any(alternative[k]>value[k]for k in value):dominated.append(other)
        result[ident]=dict(status='provisional_dominated'if dominated else'provisional_nondominated',dominated_by=dominated)
    return result


def fine_design_comparisons(records,alias):
    fine=next(r for r in records if r['grid_variant']=='XY102-Z97')
    require(alias['grid_variant']==fine['grid_variant']=='XY102-Z97','Design comparison only within the same full fine physical grid')
    bases={
        'primary_original_coarse101_B0_caps':(fine['normalizations_to_original_coarse101_B0'],alias['normalizations_to_original_coarse101_B0']),
        'secondary_fine_B0_caps':(fine['secondary_fine_B0_derived_caps']['normalizations'],alias['secondary_fine_B0_derived_caps']['normalizations'])}
    result={}
    for basis,(candidate,baseline)in bases.items():
        modes={}
        for mode in MODES:
            vectors={fine['candidate_id']:objective_vector(candidate.get('comparisons',{}).get(mode,{})),alias['candidate_id']:objective_vector(baseline.get('comparisons',{}).get(mode,{}))}
            reference=vectors[alias['candidate_id']]
            modes[mode]=dict(scores={cid:objective_score(v,reference)for cid,v in vectors.items()},pareto=strict_pareto(vectors))
        result[basis]=dict(grid_variant='XY102-Z97',candidate_ids=[fine['candidate_id'],alias['candidate_id']],modes=modes,
            coarse_common97_or_original101_design_frontier_included=False,original_reference_normalizations_recomputed=False,
            scope='Four strict scalar objectives within full fineXY102 only; numerical/contact uncertainty persists, no adoption')
    return result


def contact_fraction(area_m2,h_m):
    require(math.isfinite(area_m2)and math.isfinite(h_m)and area_m2>0 and h_m>0,
            'Actual positive physical contact area and explicit grid spacing')
    return area_m2/(h_m*h_m)


def _contact_peaks(np,geometry,raws,h_m):
    areas=raws[0]['contact_area_m2'];pads=raws[0]['contact_pad'];cells=raws[0]['contact_xy_index']
    fractions=areas/(h_m*h_m)
    require(np.all(fractions>0)and np.all(fractions<=1.+1e-10),'Actual partial faces use this grid spacing, no correction')
    j=np.sqrt((abs(raws[0]['contact_normal_J_peak_A_m2'])**2+abs(raws[1]['contact_normal_J_peak_A_m2'])**2)/2.)
    v=np.sqrt((abs(raws[0]['contact_drop_peak_V'])**2+abs(raws[1]['contact_drop_peak_V'])**2)/2.)
    def site(index):
        return dict(contact_row=int(index),physical_pad=int(pads[index]),surface_xy_mm=[float(x)for x in geometry['grid'][int(cells[index]),:2]],
            physical_depth_mm=0.,actual_area_m2=float(areas[index]),fraction_of_this_grid_surface_face=float(fractions[index]),
            contact_normal_J_RMS_A_m2=float(j[index]),contact_drop_RMS_V=float(v[index]),
            is_partial_cell_with_float_tolerance=bool(fractions[index]<1.-1e-12))
    rows=[]
    for pad in range(4):
        use=np.flatnonzero(pads==pad)
        rows.append(dict(physical_pad=pad,minimum_positive_fraction=float(fractions[use].min()),
            partial_cell_count=int(np.sum(fractions[use]<1.-1e-12)),contact_rows=len(use),
            Jmax_site=site(int(use[np.argmax(j[use])])),contact_voltage_max_site=site(int(use[np.argmax(v[use])]))))
    return dict(schema='task1-E13-grid-specific-partial-contact-peaks-v1',h_m=float(h_m),full_face_area_m2=float(h_m*h_m),
        minimum_positive_fraction=float(fractions.min()),partial_cell_count=int(np.sum(fractions<1.-1e-12)),
        maximum_J_RMS_site=site(int(np.argmax(j))),maximum_contact_voltage_RMS_site=site(int(np.argmax(v))),pads=rows,
        partial_classification_float_tolerance=1e-12,fraction_definition='Actual patch area divided by this grid h squared',
        no_correction_factor_applied=True,minimum_fraction_used_as_cutoff=False,source_and_return_pads_all_included=True,
        contact_model='Containing surface-node potential on a physical partial patch; subcell edge variation remains unresolved',
        old_coarse_fmin_substituted_for_fine=False,physiological_or_safety_inference=False)


def _carrier(np,context,manifest,grid_name,frequency,guard,deadline,need_bulk=True):
    group='fine'if grid_name=='XY102-Z97'else'coarse_SC4';entry=manifest[group]['E13'][frequency];proof=entry['proof']
    require(proof['passed']is True and proof['physical_gates']['passed']is True and proof['passivity_passed']is True,
            'Unchanged actual signed-circuit source proof before any E13 metrics')
    if group=='fine':
        raw=_load(np,entry['raw'],list(CONTACT_KEYS)+['E_peak_V_m'],guard,deadline)
        require(raw['E_peak_V_m'].shape==(97*8184,3),'Actual full fine97 E13 field ABI')
        return raw,proof
    supplement=_load(np,entry['raw'],list(CONTACT_KEYS)+['E_SC4_peak_V_m'],guard,deadline)
    old_keys=list(CONTACT_KEYS)+(['E_peak_V_m']if need_bulk else [])
    old=_load(np,context['coarse_raw']['E13'][frequency],old_keys,guard,deadline)
    require(supplement['E_SC4_peak_V_m'].shape==(4*7860,3),
            'Only coarse SC4 is new; original93 bulk E samples remain intact')
    for key in CONTACT_KEYS:
        require(supplement[key].shape==old[key].shape and np.allclose(supplement[key],old[key],rtol=1e-12,atol=1e-20),
                'Depth-only SC4 sampling cannot change cached original contacts/currents/layer powers: '+key)
    raw={key:supplement[key]for key in CONTACT_KEYS}
    if not need_bulk:
        raw['E_peak_V_m']=supplement['E_SC4_peak_V_m']
        return raw,proof
    require(old['E_peak_V_m'].shape==(101*7860,3),'Original coarse101 full E needed only for physical projection')
    raw['E_peak_V_m']=np.concatenate((supplement['E_SC4_peak_V_m'],old['E_peak_V_m'][8*7860:]),axis=0)
    del old,supplement
    require(raw['E_peak_V_m'].shape==(97*7860,3),'Ephemeral common97 coarse E, no duplicate bulk archive')
    return raw,proof


def _summarize_four(np,geometry,arrays,electrical,metrics,guard,deadline,sc_checks):
    grid=geometry['grid'];weights=geometry['weights'];n=len(grid)
    require(set(arrays)==set(SCALARS)and all(v.shape==(n,)and np.isfinite(v).all()for v in arrays.values()),
            'Exactly the four actually saved original/new-SC E13 scalar arrays')
    require(all(np.all(arrays[k]>=0)for k in SCALARS[:3])and np.issubdtype(arrays['AM_direction_index'].dtype,np.integer)
            and np.all((arrays['AM_direction_index']>=0)&(arrays['AM_direction_index']<2074)),
            'Nonnegative completed scalar values and original2074 winner indices')
    layer=grid[:,3].astype(int);scopes=dict(weights)
    scopes['surface_without_SC']=weights['surface_0_5']*(layer!=0)
    scopes['skin_SC_plus_dermis']=weights['total']*(layer<=1)
    for k,name in enumerate(LAYERS):scopes['layer_'+name]=weights['total']*(layer==k)
    regions={name:dict(volume_m3=float(w.sum()),statistics={})for name,w in scopes.items()}
    for key,saved in (('maxTIS','AM_max2074'),('RMS','carrier_RMS'),('Jtotal_vector_RMS','Jtotal_vector_RMS')):
        check(guard,deadline);values=arrays[saved];order=np.argsort(values,kind='stable')
        for name,w in scopes.items():
            check(guard,deadline);regions[name]['statistics'][key]=metrics.weighted_stats(np,values,w,grid,order)
    e=dict(electrical);skin=regions['skin_SC_plus_dermis']['statistics']['Jtotal_vector_RMS']
    require(skin['status']=='complete','Actual positive-volume skin current statistic')
    e['skin_vector_J_RMS_max_A_m2']=skin['max'];e['skin_vector_J_RMS_P95_A_m2']=skin['p95']
    return dict(schema='task1-E13-four-cached-scalar-common97-metrics-v1',status='calculated_provisional_available_fields',
        frequencies_Hz=[2000,2010],pads=4,independent_outputs=2,regions=regions,electrical=e,
        available_statistics=['maxTIS','RMS','Jtotal_vector_RMS'],unavailable_statistics={name:dict(status='unavailable_not_saved_in_original_E13_scalar_archive',values_invented=False)for name in COARSE_UNAVAILABLE},
        waveform_checks=dict(status='original_bulk_checks_not_repeated',new_SC4_checks=sc_checks,
            original_coarse101_checks_preserved_in_record=True),
        directional_search=dict(completed=True,directions=2074,newly_scanned_cells=4*7860,
            authenticated_original_bulk_cells=93*7860,bulk_spatial_angular_scan_repeated=False,
            coverage='New SC4 prefix plus original93 bulk scalar samples; no axes or split-carrier values invented',
            angular_maximum_scope='Sampled lower bound, not continuum maximum'),
        coordinate_system=dict(surface_z_mm=0.,depth_axis='+z',target='r<=5 mm;15<=z<=20 mm',weighting='Original physical fractional native volumes, unchanged stable inverse-volume ECDF'),
        units=dict(E='V/m',Jtotal='A/m2',volume='m3'),
        holds=dict(candidate_adopted=False,full_numerical_convergence=False,experimental_validation=False,
            SC_XY_bulk_edge_contact_uncertainty=True,electrical_proxy_is_not_activation_or_safety=True))


def _normalize_available(summary,baseline,metrics):
    # Same frozen four electrical caps/scales; iterate only actually available
    # field statistics. Missing axes are never represented as zeros or {}.
    e=summary['electrical'];b=baseline['electrical'];linear=metrics.LINEAR_BURDENS;power=metrics.POWER_BURDENS
    required=('source_Vpp_each','sum_output_current_RMS_A_bookkeeping','source_power_W')+linear+power
    missing=[k for k in required if k not in e or k not in b]
    if missing:return dict(status='not_run_missing_normalization_inputs',missing_keys=missing)
    caps={k:metrics._cap(b[k],e[k],1 if k in linear else 2)for k in linear+power};finite=[v for v in caps.values()if v is not None]
    scenarios=dict(same_source_voltage=metrics._cap(b['source_Vpp_each'],e['source_Vpp_each'],1),
        same_sum_output_RMS_current_bookkeeping=metrics._cap(b['sum_output_current_RMS_A_bookkeeping'],e['sum_output_current_RMS_A_bookkeeping'],1),
        same_source_real_power=metrics._cap(b['source_power_W'],e['source_power_W'],2),joint_eight_surface_contact_burden_caps=min(finite)if finite else None)
    rows={};available=set(summary['regions']['target']['statistics'])
    for mode,scale in scenarios.items():
        if scale is None:rows[mode]=dict(status='not_run_unbounded_or_zero_candidate_reference');continue
        require(math.isfinite(scale)and scale>=0,'Finite independent normalization scale')
        fields={}
        for region in ('target','surface_0_5','surface_without_SC','off_target','total'):
            fields[region]={}
            for field in ('maxTIS','RMS','X_TIS','Y_TIS','Z_TIS'):
                if field not in available:continue
                values=summary['regions'][region]['statistics'][field]
                fields[region][field]={key:float(values[key])*scale for key in ('mean','p10','median','p95','p99','max','std')if key in values}
        row=dict(status='calculated_global_amplitude_rescaling',amplitude_scale=scale,absolute_ROI_fields_V_m=fields,
                 electrical=metrics._scaled_electrical(e,scale),unavailable_field_statistics=[k for k in ('X_TIS','Y_TIS','Z_TIS')if k not in available])
        if mode=='joint_eight_surface_contact_burden_caps':
            row['individual_amplitude_caps']=caps;row['limiting_constraints']=[k for k,v in caps.items()if v is not None and abs(v-scale)<=1e-12*max(1.,scale)]
        rows[mode]=row
    return dict(schema='task1-E13-available-field-normalization-v1',status='complete',comparisons=rows,
        current_definition='Independent-output RMS magnitude sum is bookkeeping, not unique physical total current',
        simultaneous_equal_current_power_burden_assumed=False,burden_caps_scope='Original B0 numerical values, not safety limits',
        missing_field_statistics_invented=False,candidate_adopted=False)


def _metric_case(np,spec,manifest,geometry,grid_name,metrics,guard,deadline,out):
    context=spec['inputs'];cid=spec['candidate_id'];case_id=cid+'-'+grid_name;raws=[];proofs=[]
    for frequency in ('2000','2010'):
        data,proof=_carrier(np,context,manifest,grid_name,frequency,guard,deadline,need_bulk=grid_name=='XY102-Z97');raws.append(data);proofs.append(proof)
    electrical,spectral=_electrical(np,raws,proofs)
    contact_peaks=_contact_peaks(np,geometry,raws,.05/102 if grid_name=='XY102-Z97'else .0005)
    gamma=[np.asarray([complex_value(v)for v in context['gamma_by_frequency'][f]])for f in ('2000','2010')]
    assembly=None
    if grid_name=='XY102-Z97':
        result=metrics.evaluate(np,geometry['grid'],geometry['weights'],raws[0]['E_peak_V_m'],raws[1]['E_peak_V_m'],gamma[0],gamma[1],electrical,guard,deadline)
        summary=result['summary'];selected={k:result['arrays'][k]for k in SCALARS}
        archive=_archive(np,out/(case_id+'-scalars.npz'),selected)
        scalar_kind='full_new_fine97';work=dict(full_field_evaluations=1,SC4_only_evaluations=0,newly_scanned_cells=97*8184,reused_original_bulk_cells=0,repeated_original_bulk_angular_evaluations=0)
        del result
    else:
        cut=4*7860
        sc=metrics.evaluate(np,geometry['grid'][:cut],{k:v[:cut]for k,v in geometry['weights'].items()},raws[0]['E_peak_V_m'][:cut],raws[1]['E_peak_V_m'][:cut],gamma[0],gamma[1],electrical,guard,deadline)
        original=_load(np,context['coarse_scalars']['E13'],list(SCALARS),guard,deadline)
        require(all(v.shape==(101*7860,)for v in original.values()),'Original E13 four-scalar101-plane ABI')
        selected={k:sc['arrays'][k]for k in SCALARS};archive=_archive(np,out/(case_id+'-SC4-scalars.npz'),selected)
        composed={k:np.concatenate((selected[k],original[k][8*7860:]))for k in SCALARS};del original
        summary=_summarize_four(np,geometry,composed,electrical,metrics,guard,deadline,sc['summary']['waveform_checks'])
        scalar_kind='SC4_patch_plus_authenticated_original_bulk93';assembly=scalar_assembly_description(context['coarse_scalars']['E13'],archive)
        new_json(out/(case_id+'-scalar-assembly-proof.json'),assembly)
        work=dict(full_field_evaluations=0,SC4_only_evaluations=1,newly_scanned_cells=cut,reused_original_bulk_cells=93*7860,repeated_original_bulk_angular_evaluations=0)
        del composed,sc
    del raws;gc.collect();summary['numerical_grid_variant']=grid_name
    for region in summary['regions'].values():
        for values in region['statistics'].values():
            if values.get('status')=='complete':values['CV']=float(values['std']/values['mean'])if values['mean']>0 else None
    original=context['coarse_B0_record']['metrics'];normalizations=_normalize_available(summary,original,metrics)
    require(normalizations['status']=='complete','All four original coarse101-B0 numerical normalization definitions available')
    secondary=_normalize_available(summary,context['fine_B0_record']['metrics'],metrics)
    record=dict(candidate_id=case_id,physical_geometry_id=cid,grid_variant=grid_name,
        metrics=summary,normalizations_to_original_coarse101_B0=normalizations,
        min4_to_original_coarse101_B0=_normalization_scores(normalizations,_am_reference(original)),
        secondary_fine_B0_derived_caps=dict(scope='Explicit secondary fineB0 reference; original coarse101-B0 caps unchanged',normalizations=secondary),
        per_frequency_signed_circuit=spectral,source_physics_proofs=proofs,fractional_contact_diagnostics=contact_peaks,scalar_arrays=archive,
        scalar_archive_kind=scalar_kind,scalar_assembly_proof=assembly,saved_scalar_names=list(SCALARS),
        metric_evaluations=1,angular_work=work,sampled_directions=2074,full_convergence=False,Q_resident_during_metrics=False,candidate_adopted=False)
    del selected;gc.collect();check(guard,deadline);return record


def _case_scalars(np,context,record,keys,guard,deadline):
    saved=_load(np,record['scalar_arrays'],keys,guard,deadline)
    if record['scalar_archive_kind']=='full_new_fine97':
        require(all(v.shape==(97*8184,)for v in saved.values()),'Actual fine97 E13 saved scalar identity');return saved
    require(record['scalar_archive_kind']=='SC4_patch_plus_authenticated_original_bulk93'and all(v.shape==(4*7860,)for v in saved.values()),'Only the SC4 scalar patch is new for coarse E13')
    old=_load(np,context['coarse_scalars']['E13'],keys,guard,deadline)
    require(all(v.shape==(101*7860,)for v in old.values()),'Exact original101 E13 scalar arrays')
    return{k:np.concatenate((saved[k],old[k][8*7860:]))for k in keys}


def _projection_geometry(np,descriptor,nxy,guard,deadline):
    # Full ROI arrays were already authenticated/used in each metric frame.
    # Retain only surface XY and depth faces for the pairwise overlap stage.
    value=_load(np,descriptor,['grid','z_faces_m'],guard,deadline)
    grid=value['grid'];faces=value['z_faces_m']
    require(grid.shape==(97*nxy,5)and faces.shape==(98,)and np.all(np.diff(faces)>0),
            'Exact common97 physical geometry for overlap, no retained ROI arrays')
    xy=grid[:nxy,:2].copy();centres=(faces[:-1]+faces[1:])/2.
    for plane in range(97):
        check(guard,deadline);row=grid[plane*nxy:(plane+1)*nxy]
        require(np.array_equal(row[:,:2],xy)and np.allclose(row[:,2],centres[plane]*1000,rtol=0,atol=1e-11),
                'Actual physical XY/depth ordering before releasing full projection grid')
    del grid,value,row;gc.collect()
    return dict(xy_mm=xy,z_faces_m=faces,nxy=nxy)


def _cross_grid(np,spec,manifest,records,projector,guard,deadline,out):
    geometry={name:_projection_geometry(np,manifest['geometry'][key],n,guard,deadline)for name,key,n in (('XY100-Z97','coarse',7860),('XY102-Z97','fine',8184))}
    coarse=geometry['XY100-Z97'];fine=geometry['XY102-Z97'];require(np.array_equal(coarse['z_faces_m'],fine['z_faces_m']),'Exactly common97 physical depth faces')
    links=projector.build_overlap(coarse['xy_mm'],.5,fine['xy_mm'],50./102,lambda:check(guard,deadline))
    disk=projector.analyticdisk_rect_area(links['rectangle_mm'],5.)
    require(abs(float(disk.sum())-math.pi*25.e-6)<=1e-9*math.pi*25.e-6,'Actual full common physical target disk without renormalizing areas')
    archive=_archive(np,out/'physical-common-overlap-links.npz',dict(coarse_index=links['coarse_index'],fine_index=links['fine_index'],area_m2=links['area_m2'],rectangle_mm=links['rectangle_mm'],target_disk_intersection_area_m2=disk))
    carriers={}
    for frequency in ('2000','2010'):
        a,_=_carrier(np,spec['inputs'],manifest,'XY100-Z97',frequency,guard,deadline)
        b,_=_carrier(np,spec['inputs'],manifest,'XY102-Z97',frequency,guard,deadline)
        carriers[frequency]=_projection(np,a['E_peak_V_m'].reshape((97,7860,3)),b['E_peak_V_m'].reshape((97,8184,3)),links,disk,coarse['z_faces_m'],guard,deadline)
        del a,b;gc.collect()
    lookup={r['grid_variant']:r for r in records}
    a=_case_scalars(np,spec['inputs'],lookup['XY100-Z97'],['AM_max2074','carrier_RMS'],guard,deadline)
    b=_case_scalars(np,spec['inputs'],lookup['XY102-Z97'],['AM_max2074','carrier_RMS'],guard,deadline)
    scalars={k:_projection(np,a[k].reshape((97,7860)),b[k].reshape((97,8184)),links,disk,coarse['z_faces_m'],guard,deadline)for k in ('AM_max2074','carrier_RMS')}
    del a,b,geometry;gc.collect()
    return dict(schema='task1-E13-fineXY-physical-overlap-v1',physical_geometry_id=spec['candidate_id'],overlap=links['summary'],overlap_links=archive,
        depth_faces_matched_exactly=True,target_disk_radius_mm=5.,carrier_peak_complex_vector_comparison=carriers,native_own_carrier_scalar_comparison=scalars,
        primary='Exact frozen pairwise physical-overlap-volume L2; no spatial averaging, phase rotation or potential-gauge fit',
        AM_definition='Each grid own carriers, identical fixed2074 directions; original93 bulk maxima inherited without angular work',
        unmatched_native_domain={k:links['summary'][k]for k in ('coarse','fine')},
        unmatched_volume_m3={k:links['summary'][k]['unmatched_area_m2']*.0251 for k in ('coarse','fine')},automatic_convergence_or_activation_gate_applied=False,candidate_adopted=False)


def _adjacent_diagnostics(records):
    lookup={r['grid_variant']:r['metrics']for r in records};coarse=lookup['XY100-Z97'];fine=lookup['XY102-Z97'];checks=[]
    for name in ('mean','p10'):
        checks.append(dict(metric='target_AM_'+name,**relative_diagnostic(float(coarse['regions']['target']['statistics']['maxTIS'][name]),float(fine['regions']['target']['statistics']['maxTIS'][name]),.01,'V/m')))
    for name in ('contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','skin_vector_J_RMS_max_A_m2','skin_vector_J_RMS_P95_A_m2','contact_voltage_RMS_max_V'):
        checks.append(dict(metric=name,**relative_diagnostic(float(coarse['electrical'][name]),float(fine['electrical'][name]),.05,'V'if name.endswith('_V')else'A/m2')))
    for name in ('SC_power_W','skin_power_W','contact_power_W','source_power_W','source_resistor_power_W'):
        checks.append(dict(metric=name,**relative_diagnostic(float(coarse['electrical'][name]),float(fine['electrical'][name]),.02,'W')))
    for output in (0,1):checks.append(dict(metric='output%d_two_carrier_RMS_A'%output,**relative_diagnostic(float(coarse['electrical']['source_current_RMS_by_output_A'][output]),float(fine['electrical']['source_current_RMS_by_output_A'][output]),.05,'A')))
    for layer in LAYERS:checks.append(dict(metric='layer_'+layer+'_power_W',**relative_diagnostic(float(coarse['electrical']['layers_power_W'][layer]),float(fine['electrical']['layers_power_W'][layer]),.02,'W')))
    return dict(physical_geometry_id=records[0]['physical_geometry_id'],reference_grid='XY100-Z97',candidate_grid='XY102-Z97',rows=checks,passed_count=sum(r['passed']for r in checks),failed_count=sum(not r['passed']for r in checks),old_13_of_14_and_interface_failures_cleared=False,full_convergence=False)


def build(np,spec,raw_manifest,guard,deadline,out):
    check(guard,deadline);out=Path(out);context=spec['inputs'];actual=raw_accounting(raw_manifest)
    require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink(),'Owner-created canonical E13 output')
    require(spec['candidate_id']==context['coarse_E13_record']['candidate_id'],'Numerical grid refinement cannot change the original E13 physical identity')
    metrics=_module('screen_metrics',context);projector=_module('physical_projector',context);records=[];binding=None
    for grid_name,key,n in (('XY102-Z97','fine',8184),('XY100-Z97','coarse',7860)):
        geometry=_geometry(np,raw_manifest['geometry'][key],n,guard,deadline)
        if grid_name=='XY100-Z97':
            binding=_old_bulk_binding(np,context,geometry,guard,deadline);new_json(out/'coarse-common97-original93-bulk-binding.json',binding)
        record=_metric_case(np,spec,raw_manifest,geometry,grid_name,metrics,guard,deadline,out);records.append(record)
        new_json(out/(record['candidate_id']+'-summary.json'),record);del geometry;gc.collect()
        new_json(out/('checkpoint-E13-metrics-%d.json'%len(records)),dict(status='matched97_E13_metric_case_complete',completed_new_metric_cases=len(records),Q_resident_during_metrics=False))
    accounting=finite_accounting(records);alias=fine_B0_alias(context)
    designs=fine_design_comparisons(records,alias)
    new_json(out/'same-grid-fine-four-objective-comparison.json',designs)
    new_json(out/'fine-B0-immutable-control-alias.json',alias)
    cross=_cross_grid(np,spec,raw_manifest,records,projector,guard,deadline,out);new_json(out/'cross-grid-physical-comparison.json',cross)
    diagnostics=_adjacent_diagnostics(records);new_json(out/'prospective-adjacent-grid-diagnostics.json',diagnostics)
    summary=dict(schema='task1-E13-fineXY-post-result-v1',status='two_E13_matched97_metric_cases_and_physical_overlap_computed_unadopted',
        candidates=records+[alias],new_E13_metric_cases=records,comparison_accounting=dict(accounting,**actual),
        actual_new_driven_RHS=2,actual_new_coarse_driven_RHS=0,actual_new_metric_evaluations=2,
        actual_full_angular_evaluations=1,actual_SC4_only_angular_evaluations=1,actual_repeated_original_bulk_angular_evaluations=0,
        actual_duplicate_full_coarse_scalar_archives=0,actual_immutable_fine_B0_aliases=1,actual_control_RHS_repeated=0,actual_control_angular_metrics_repeated=0,new_eigen_solves=0,
        physical_overlap_comparison=cross,prospective_adjacent_grid_diagnostics=diagnostics,coarse_common97_bulk_binding=binding,
        same_grid_fine_design_comparisons=designs,
        original_coarse101_records_preserved=dict(B0=context['coarse_B0_record'],E13=context['coarse_E13_record']),
        original_fine_B0_record_preserved=context['fine_B0_record'],
        normalization_reference='Original coarse101 B0 numerical caps primary; full original fineB0-derived caps explicitly secondary',
        fields=dict(angular_lower_bound_directions=2074,AM_is_not_carrier_RMS=True,coarse_unavailable_statistics=list(COARSE_UNAVAILABLE),lateral='Frozen native half-face estimator at actual spacing',normal='Analytic same-depth J/gamma'),
        diagnostics_not_run=dict(full_mesh_convergence='Adjacent XY and changed SC quadrature are numerical diagnostics, not full convergence',physiological_threshold='Unvalidated; no activation/safety inference'),
        holds=dict(old_independent_5percent_interface_failures_preserved=True,prior_fine14_of18_and16_of18_failures_preserved=True,
            SC_XY_contact_edge_material_uncertainty_preserved=True,full_convergence=False,physiological_activation_or_safety_claim=False,experimental_validation=False,candidate_adopted=False),
        Q_resident_during_postprocessing=False,originals_overwritten=False,candidate_adopted=False)
    check(guard,deadline);return dict(summary=summary,arrays={})
