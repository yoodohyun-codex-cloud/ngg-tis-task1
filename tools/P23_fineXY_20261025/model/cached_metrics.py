"""No repeated coarse bulk angular search: cached scalar reaggregation only.

Root injects numerical dependencies and authenticated old/new scalar arrays.
No I/O, NumPy import, data or work on import. 2074 coverage is inherited for
unchanged93bulk planes and newly evaluated only onSC4 by the caller.
"""
import screen_metrics as original
REGIONS=original.REGIONS
LAYER_NAMES=original.LAYER_NAMES
FREQUENCIES_HZ=original.FREQUENCIES_HZ
_require=original._require
_check=original._check
weighted_stats=original.weighted_stats
_waveform_checks=original._waveform_checks

def summarize(np,grid,weights,arrays,electrical,E0,E1,guard=lambda:None,deadline=None):
    _check(guard,deadline);grid=np.asarray(grid,float);a=np.asarray(E0,np.complex128);b=np.asarray(E1,np.complex128);n=len(grid)
    keys=('carrier_RMS','carrier0_RMS','carrier1_RMS','AM_x','AM_y','AM_z','AM_max2074','AM_direction_index','Jtotal_vector_RMS')
    _require(set(keys)==set(arrays)and all(np.asarray(arrays[k]).shape==(n,)and np.isfinite(arrays[k]).all()for k in keys),'Nine complete cached+SC scalar arrays, no missing-field invention')
    _require(grid.shape==(n,5)and a.shape==b.shape==(n,3)and np.isfinite(grid).all()and np.isfinite(a).all()and np.isfinite(b).all(),'Actual matched-depth complex E vectors and geometry')
    layers=grid[:,3].astype(int);_require(np.array_equal(layers,grid[:,3])and np.all((layers>=0)&(layers<4)),'Four exact physical layer IDs')
    _require(set(weights)==set(REGIONS),'Same six physical ROI definitions');w={k:np.asarray(weights[k],float)for k in REGIONS}
    _require(all(v.shape==(n,)and np.isfinite(v).all()and np.all(v>=0)for v in w.values())and np.allclose(w['total'],grid[:,4],rtol=1e-12,atol=1e-25),'Actual physical fractional volume weights')
    sq0=np.sum(abs(a)**2,axis=1);sq1=np.sum(abs(b)**2,axis=1);rms=np.asarray(arrays['carrier_RMS']);xyz=np.column_stack([arrays[k]for k in ('AM_x','AM_y','AM_z')]);maximum=np.asarray(arrays['AM_max2074']);winner=np.asarray(arrays['AM_direction_index']).astype(np.int32);jrms=np.asarray(arrays['Jtotal_vector_RMS'])
    _require(np.array_equal(winner,arrays['AM_direction_index'])and np.all((winner>=0)&(winner<2074)),'Authenticated sampled direction indices')
    _require(np.allclose(rms,np.sqrt((sq0+sq1)/2.),rtol=2e-7,atol=1e-10)and np.allclose(xyz,2*np.minimum(abs(a),abs(b)),rtol=2e-7,atol=1e-10)and np.allclose(arrays['carrier0_RMS'],np.sqrt(sq0/2.),rtol=2e-7,atol=1e-10)and np.allclose(arrays['carrier1_RMS'],np.sqrt(sq1/2.),rtol=2e-7,atol=1e-10),'Cached RMS/directional axes correspond to the same unchanged raw carriers')
    dirs=original.directions(np);chosen=dirs[winner];selected=2*np.minimum(abs(np.sum(a*chosen,axis=1)),abs(np.sum(b*chosen,axis=1)));upper=2*np.minimum(np.sqrt(sq0),np.sqrt(sq1))
    _require(np.allclose(maximum,selected,rtol=2e-7,atol=1e-10)and np.all(maximum<=upper+1e-10+2e-7*upper)and np.all(maximum+1e-10>=np.max(xyz,axis=1)),'Cached selected-direction values remain consistent without rescanning bulk directions')
    _require(np.all(jrms>=0)and float(electrical['source_Vpp_each'])==1.,'Finite cached total-current density and fixed1Vpp source')
    scalars=dict(maxTIS=maximum,RMS=rms,X_TIS=xyz[:,0],Y_TIS=xyz[:,1],Z_TIS=xyz[:,2],carrier0_RMS=np.asarray(arrays['carrier0_RMS']),carrier1_RMS=np.asarray(arrays['carrier1_RMS']),Jtotal_vector_RMS=jrms)
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
                 directional_search=dict(completed=True,directions=2074,chunk_cells=256,bulk_spatial_angular_scan_repeated=False,coverage='Original authenticated93 bulk planes plus newly scannedSC4; metrics reaggregated on common97',
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

