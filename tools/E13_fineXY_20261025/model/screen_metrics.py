"""Pure, owner-called two-carrier provisional screen; no IO or imports on import.

The fixed carriers are 2000/2010 Hz, peak phasors, independently solved at the
declared 1 Vpp high-Z source setting. The 2074-direction result is a sampled
angular LOWER BOUND, not a continuum maximum or physiological activation.
"""
FREQUENCIES_HZ=(2000,2010)
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
LAYER_NAMES=('sc','dermis','fat','muscle')
LINEAR_BURDENS=('contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2',
                'contact_voltage_RMS_max_V','skin_vector_J_RMS_max_A_m2','skin_vector_J_RMS_P95_A_m2')
POWER_BURDENS=('SC_power_W','skin_power_W','contact_power_W')


def _require(ok,message):
    if not ok:raise ValueError(message)


def _check(guard,deadline):
    import time
    guard()
    if deadline is not None and time.monotonic()>=deadline:
        raise TimeoutError('Incomplete provisional metrics: deadline reached; no partial maximum is valid')


def directions(np):
    """Exact original explore_tis.directions(2048) ordering: 26+2048 real units."""
    base=[]
    for x in(-1,0,1):
        for y in(-1,0,1):
            for z in(-1,0,1):
                if x or y or z:
                    v=np.asarray([x,y,z],float);base.append(v/np.linalg.norm(v))
    for i in range(2048):
        z=1.-2.*(i+.5)/2048.;p=i*np.pi*(3.-np.sqrt(5.));r=np.sqrt(1.-z*z)
        base.append([r*np.cos(p),r*np.sin(p),z])
    return np.asarray(base,float)


def weighted_stats(np,values,w,grid,order=None):
    """Inverse volume ECDF; native representative extrema, not continuum maxima."""
    values=np.asarray(values,float);w=np.asarray(w,float)
    _require(values.shape==w.shape and values.ndim==1 and np.isfinite(values).all()and
             np.isfinite(w).all()and np.all(w>=0),'Finite scalar values and nonnegative m3 weights required')
    use=w>0;indices=np.flatnonzero(use)
    if not len(indices):return dict(status='not_run_no_positive_volume',volume_m3=0.)
    total=float(np.sum(w));mean=float(np.sum(values*w)/total)
    std=float(np.sqrt(np.sum(w*(values-mean)**2)/total))
    if order is None:order=np.argsort(values,kind='stable')
    cumulative=np.cumsum(w[order]);lo=int(indices[np.argmin(values[use])]);hi=int(indices[np.argmax(values[use])])
    result=dict(status='complete',volume_m3=total,positive_weight_cells=len(indices),
                min=float(values[lo]),max=float(values[hi]),mean=mean,std=std,
                minimum_native_cell_index=lo,maximum_native_cell_index=hi,
                minimum_xyz_mm=[float(v)for v in grid[lo,:3]],maximum_xyz_mm=[float(v)for v in grid[hi,:3]],
                maximum_tied_cells=int(np.sum(use&(values==values[hi]))),
                maximum_tied_volume_m3=float(np.sum(w[values==values[hi]])),
                extrema_scope='Cell-constant samples with positive fractional ROI weight; representative centre may lie outside a fractional ROI boundary')
    for name,p in(('p10',.1),('median',.5),('p95',.95),('p99',.99)):
        k=min(int(np.searchsorted(cumulative,p*cumulative[-1],side='left')),len(values)-1)
        result[name]=float(values[order[k]])
    return result


def _waveform_checks(np,E0,E1,maximum,winner,dirs,weights,guard,deadline):
    """Exact envelope extrema plus a complete .1 s/8192-sample real waveform."""
    indices={int(np.argmax(maximum))}
    target=np.flatnonzero(weights['target']>0)
    if len(target):indices.add(int(target[np.argmax(maximum[target])]))
    rows=[];t=np.arange(8192,dtype=float)*(.1/8192.)
    carrier0=np.exp(2j*np.pi*2000.*t);carrier1=np.exp(2j*np.pi*2010.*t)
    for index in sorted(indices):
        for label,u in [('x',np.asarray([1.,0.,0.])),('y',np.asarray([0.,1.,0.])),
                        ('z',np.asarray([0.,0.,1.])),('sampled_winner',dirs[winner[index]])]:
            _check(guard,deadline);a=complex(E0[index]@u);b=complex(E1[index]@u)
            constructive=(np.angle(a)-np.angle(b))/(2.*np.pi*10.)
            destructive=constructive+.05
            envelope_max=float(abs(a+b*np.exp(2j*np.pi*10.*constructive)))
            envelope_min=float(abs(a+b*np.exp(2j*np.pi*10.*destructive)))
            expected_am=2.*min(abs(a),abs(b));observed_am=envelope_max-envelope_min
            waveform=np.real(a*carrier0+b*carrier1)
            observed_rms=float(np.sqrt(np.mean(waveform**2)))
            expected_rms=float(np.sqrt((abs(a)**2+abs(b)**2)/2.))
            am_error=abs(observed_am-expected_am);rms_error=abs(observed_rms-expected_rms)
            _require(am_error<=1e-10+1e-10*expected_am and rms_error<=1e-10+1e-10*expected_rms,
                     'Exact two-carrier representative waveform check failed')
            rows.append(dict(native_cell_index=index,direction=label,unit_vector=u.tolist(),
                             envelope_max_V_m=envelope_max,envelope_min_V_m=envelope_min,
                             AM_formula_V_m=expected_am,AM_waveform_V_m=observed_am,
                             carrier_RMS_formula_V_m=expected_rms,carrier_RMS_time_V_m=observed_rms,
                             AM_absolute_error_V_m=am_error,RMS_absolute_error_V_m=rms_error,passed=True))
    return dict(status='passed',scope='Representative cells/directions, exact two actual carrier phasors only',
                duration_s=.1,samples=8192,sample_rate_Hz=81920.,rows=rows,
                full_field_time_sampled=False,multifrequency_formula_generalization_claimed=False)


def evaluate(np,grid,weights,E0,E1,gamma0_by_layer,gamma1_by_layer,electrical,guard=lambda:None,deadline=None):
    """Return {summary,arrays}; any deadline interrupts without a partial result.

    grid is N×5 [x_mm,y_mm,z_mm,layer,volume_m3]. weights are the exact six
    original native_region_weights arrays, passed by the owner without changes.
    The function never regenerates or silently changes ROI masks. E0/E1 are
    the coherently composed 2000/2010 Hz vectors, shape(N,3), at 1Vpp high-Z.
    """
    _check(guard,deadline);grid=np.asarray(grid,float);a=np.asarray(E0,np.complex128);b=np.asarray(E1,np.complex128)
    _require(grid.ndim==2 and grid.shape[1]==5 and a.shape==b.shape==(len(grid),3)and len(grid)>0 and
             np.isfinite(grid).all()and np.isfinite(a).all()and np.isfinite(b).all(),
             'Complete finite native grid and matching peak complex carrier vectors required')
    n=len(grid);layers=grid[:,3].astype(int)
    _require(np.array_equal(layers,grid[:,3])and np.all((layers>=0)&(layers<4)), 'Four exact integer layer labels required')
    _require(set(weights)==set(REGIONS),'Exact original six native-region weight keys required')
    w={key:np.asarray(weights[key],float)for key in REGIONS}
    for key,value in w.items():
        _require(value.shape==(n,)and np.isfinite(value).all()and np.all(value>=0),'Complete finite m3 weights: '+key)
    _require(np.allclose(w['total'],grid[:,4],rtol=1e-12,atol=1e-25)and np.all(w['target']<=w['total']*(1+1e-12))and
             np.allclose(w['off_target'],w['total']-w['target'],rtol=1e-12,atol=1e-25),
             'Native total/off-target weights must agree with the supplied actual grid')
    g0=np.asarray(gamma0_by_layer,np.complex128);g1=np.asarray(gamma1_by_layer,np.complex128)
    _require(g0.shape==g1.shape==(4,)and np.isfinite(g0).all()and np.isfinite(g1).all()and
             np.all(abs(g0)>0)and np.all(abs(g1)>0),'Actual four-layer complex admittivities required per carrier')
    _require(float(electrical['source_Vpp_each'])==1.,'This screen is registered at 1 Vpp high-Z per active source')
    dirs=directions(np);_require(dirs.shape==(2074,3),'Original exact 2074 sampled directions required')
    sq0=np.sum(abs(a)**2,axis=1);sq1=np.sum(abs(b)**2,axis=1)
    rms=np.sqrt((sq0+sq1)/2.);xyz=2.*np.minimum(abs(a),abs(b))
    maximum=np.empty(n,float);winner=np.empty(n,np.int32)
    for first in range(0,n,256):
        _check(guard,deadline);last=min(n,first+256)
        pa=np.abs(a[first:last]@dirs.T);pb=np.abs(b[first:last]@dirs.T)
        np.minimum(pa,pb,out=pa);k=np.argmax(pa,axis=1)
        winner[first:last]=k;maximum[first:last]=2.*pa[np.arange(last-first),k]
    _check(guard,deadline)
    upper=2.*np.minimum(np.sqrt(sq0),np.sqrt(sq1));tol=256.*np.finfo(float).eps*np.maximum(rms,upper)
    _require(np.isfinite(rms).all()and np.isfinite(maximum).all()and np.all(maximum<=upper+tol),
             'Completed sampled modulation must be finite and respect analytic vector upper bound')
    # Algebraically ||gamma E||²=|gamma|²||E||² for scalar isotropic gamma.
    # This is derived total current density including displacement, not an
    # independent field/current verification or conduction-only current.
    jrms=np.sqrt((abs(g0[layers])**2*sq0+abs(g1[layers])**2*sq1)/2.)
    _require(np.isfinite(jrms).all(),'Derived total-current RMS must be finite')
    scalars=dict(maxTIS=maximum,RMS=rms,X_TIS=xyz[:,0],Y_TIS=xyz[:,1],Z_TIS=xyz[:,2],
                 carrier0_RMS=np.sqrt(sq0/2.),carrier1_RMS=np.sqrt(sq1/2.),Jtotal_vector_RMS=jrms)
    scopes=dict(w);scopes['surface_without_SC']=w['surface_0_5']*(layers!=0)
    scopes['skin_SC_plus_dermis']=w['total']*(layers<=1)
    for layer,name in enumerate(LAYER_NAMES):scopes['layer_'+name]=w['total']*(layers==layer)
    regions={key:dict(volume_m3=float(np.sum(value)),statistics={})for key,value in scopes.items()}
    for name,values in scalars.items():
        _check(guard,deadline);order=np.argsort(values,kind='stable')
        for key,weight in scopes.items():
            _check(guard,deadline);regions[key]['statistics'][name]=weighted_stats(np,values,weight,grid,order)
    electrical=dict(electrical);skin=regions['skin_SC_plus_dermis']['statistics']['Jtotal_vector_RMS']
    electrical['skin_vector_J_RMS_max_A_m2']=skin['max'];electrical['skin_vector_J_RMS_P95_A_m2']=skin['p95']
    checks=_waveform_checks(np,a,b,maximum,winner,dirs,w,guard,deadline);_check(guard,deadline)
    summary=dict(schema='task1-provisional-coarse-dtn-screen-metrics-v1',status='calculated_provisional_complete',
                 frequencies_Hz=list(FREQUENCIES_HZ),pads=4,independent_outputs=2,
                 return_topology='Two driven pads; two returns at common ground; inactive output retained through 50 ohm',
                 regions=regions,electrical=electrical,waveform_checks=checks,
                 directional_search=dict(completed=True,directions=2074,chunk_cells=256,
                    method='Exact original 26 lattice directions plus 2048 Fibonacci directions, original order',
                    metric='max_sampled_real_unit_u 2 min(abs(E2000 dot u),abs(E2010 dot u))',
                    angular_maximum_scope='Sampled lower bound; not continuum angular maximum'),
                 coordinate_system=dict(surface_z_mm=0.,depth_axis='+z',target='r<=5 mm;15<=z<=20 mm',
                    weighting='Caller-passed original fractional native ROI weights in m3; stable inverse volume ECDF'),
                 units=dict(E='V/m',Jtotal='A/m2',volume='m3'),
                 conventions=dict(phasor='peak,+jomega*t',carrier_RMS='sqrt((||E2000||²+||E2010||²)/2)',
                    current='Derived gamma*E total current including displacement; not independent validation',
                    modulation='Two actual distinct sinusoidal carriers only; no multi-frequency extrapolation'),
                 thresholds=dict(high_modulation_volume='not_run; no preregistered numerical cutoffs in this provisional batch',
                    physiological_activation_threshold='unvalidated'),
                 holds=dict(candidate_adopted=False,full_numerical_convergence=False,experimental_validation=False,
                    old_5percent_failures_preserved=True,SC_XY_bulk_edge_contact_uncertainty=True,
                    electrical_proxy_is_not_activation_or_safety=True))
    arrays=dict(carrier_RMS=rms,carrier0_RMS=scalars['carrier0_RMS'],carrier1_RMS=scalars['carrier1_RMS'],
                AM_x=xyz[:,0],AM_y=xyz[:,1],AM_z=xyz[:,2],AM_max2074=maximum,
                AM_direction_index=winner,Jtotal_vector_RMS=jrms)
    return dict(summary=summary,arrays=arrays)


def _cap(reference,candidate,exponent):
    import math
    reference=float(reference);candidate=float(candidate)
    _require(math.isfinite(reference)and math.isfinite(candidate)and reference>=0 and candidate>=0,
             'Finite nonnegative normalization quantities required')
    if candidate==0:return None
    return (reference/candidate)**(1./exponent)


def _scaled_electrical(e,s):
    result={}
    for key,value in e.items():
        if key=='layers_power_W':result[key]={k:float(v)*s*s for k,v in value.items()}
        elif key=='source_current_RMS_by_output_A':result[key]=[float(v)*s for v in value]
        elif key.endswith('_power_W')or key in POWER_BURDENS:result[key]=float(value)*s*s
        elif key=='source_Vpp_each'or key in LINEAR_BURDENS or key=='sum_output_current_RMS_A_bookkeeping':result[key]=float(value)*s
        else:result[key]=value
    return result


def normalize(metrics,baseline):
    """Separate global-amplitude comparisons; never assume simultaneous equality.

    Inputs are evaluate()['summary'] dicts. Joint8 uses FIVE linear contact/skin
    burdens and THREE loss powers with quadratic scaling. Baseline quantities
    are numerical comparison caps, not human safety limits. A zero candidate
    burden gives no cap for that constraint, explicitly represented as None.
    """
    import math
    e=metrics['electrical'];b=baseline['electrical'];required=('source_Vpp_each',
        'sum_output_current_RMS_A_bookkeeping','source_power_W')+LINEAR_BURDENS+POWER_BURDENS
    missing=[key for key in required if key not in e or key not in b]
    if missing:return dict(status='not_run_missing_normalization_inputs',missing_keys=missing)
    caps={key:_cap(b[key],e[key],1 if key in LINEAR_BURDENS else 2)for key in LINEAR_BURDENS+POWER_BURDENS}
    finite=[v for v in caps.values()if v is not None]
    scenarios=dict(same_source_voltage=_cap(b['source_Vpp_each'],e['source_Vpp_each'],1),
        same_sum_output_RMS_current_bookkeeping=_cap(b['sum_output_current_RMS_A_bookkeeping'],e['sum_output_current_RMS_A_bookkeeping'],1),
        same_source_real_power=_cap(b['source_power_W'],e['source_power_W'],2),
        joint_eight_surface_contact_burden_caps=min(finite)if finite else None)
    rows={}
    for name,s in scenarios.items():
        if s is None:rows[name]=dict(status='not_run_unbounded_or_zero_candidate_reference');continue
        _require(math.isfinite(s)and s>=0,'Finite normalization scale required')
        fields={}
        for region in('target','surface_0_5','surface_without_SC','off_target','total'):
            fields[region]={}
            for metric in('maxTIS','RMS','X_TIS','Y_TIS','Z_TIS'):
                values=metrics['regions'][region]['statistics'][metric]
                fields[region][metric]={key:float(values[key])*s for key in('mean','p10','median','p95','p99','max','std')if key in values}
        rows[name]=dict(status='calculated_global_amplitude_rescaling',amplitude_scale=s,
                       absolute_ROI_fields_V_m=fields,electrical=_scaled_electrical(e,s))
        if name=='joint_eight_surface_contact_burden_caps':
            rows[name]['individual_amplitude_caps']=caps
            rows[name]['limiting_constraints']=[key for key,v in caps.items()if v is not None and abs(v-s)<=1e-12*max(1.,s)]
    return dict(schema='task1-provisional-normalization-v1',status='complete',comparisons=rows,
                current_definition='Sum of individual independent-output RMS magnitudes as bookkeeping, not a unique total-current physical invariant',
                simultaneous_equal_current_power_burden_assumed=False,
                burden_caps_scope='Baseline numerical values only; not human safety limits',
                fixed_voltage_raw_result_preserved=True,candidate_adopted=False)
