"""Owner-called unloaded physical differential probes; NumPy is injected.

No imports of numerical packages, files, processes or research work at import.
Streaming API: prepare grid stencils, sample one carrier, release native phi,
then finish from 40 complex differences/carrier. No E, Q, PDE or angular scan.
"""
import math
import time

ESTIMATOR_ID='native-physical-probe-same-layer-explicit-v2-N32768-N65536'
INTERFACES_MM=(0.,.1,5.1,10.1,25.1)
DEPTHS_MM=(5.,10.,15.,20.)
CENTRES_XY_MM=((0.,0.),(5.,0.),(-5.,0.),(0.,5.),(0.,-5.))
TIP_SPACING_MM=5.
DURATION_S=.1
SAMPLES=32768
CHECK_SAMPLES=65536
VPP_RELATIVE_DELTA_LIMIT=2e-4
COORDINATE_TOLERANCE_MM=1e-9
SOURCE_PRODUCER='tools/results_consolidation_20261025/model/probe_prediction.py: physical bilinear XY and per-layer Z recipe; adapted prospectively, not old600 prediction identity'


def _require(condition,message):
    if not condition:raise ValueError(message)


def _check(guard,deadline_monotonic):
    if guard is not None:guard()
    if deadline_monotonic is not None and time.monotonic()>=deadline_monotonic:
        raise TimeoutError('Unloaded native probe prediction incomplete: deadline reached')


def _complex(value):
    value=complex(value)
    return dict(real=float(value.real),imaginary=float(value.imag))


def instrument_metadata():
    return dict(status='user-supplied specifications; actual switches/menus unconfirmed; unloaded calculation only',
        probe=dict(model='ETA5001',bandwidth_Hz=15e6,
            differential_input=dict(resistance_ohm=8e6,capacitance_F=3.5e-12),
            each_input_to_ground=dict(resistance_ohm=4e6,capacitance_F=7e-12),attenuation_choices=[50,500]),
        oscilloscope=dict(model='Keysight DSOX1202A',input_resistance_ohm=1e6,
            input_resistance_tolerance_fraction=.02,input_capacitance_F=16e-12,
            input_capacitance_tolerance_F=3e-12,possible_body_bandwidths_Hz=[70e6,100e6,200e6],actual_body_option_verified=False),
        recommended_start=dict(probe_attenuation=50,scope_display_ratio=50,coupling='DC',
            scope_bandwidth_limit_Hz=20e6,external_50ohm_termination=False,actual_switch_menu_settings_verified=False),
        probe_input_load_applied=False,probe_loaded_PDE_performed=False,
        scope_input_connected_directly_in_parallel_with_phantom=False,
        bandwidth_or_probe_output_loading_transfer_applied=False,hardware_validation=False,
        load_scope='ETA input R/C would load the phantom; scope R/C is downstream of the active probe and has not been assembled as a phantom-parallel load.',
        ideal_gain_definition='Physical active-probe output=unloaded tip voltage/attenuation; scope display=physical output*scope display ratio. This is ideal gain bookkeeping, not a loaded prediction.')


def _layout(np,grid):
    grid=np.asarray(grid)
    _require(grid.ndim==2 and grid.shape[1]==5 and len(grid)>0 and np.isfinite(grid).all(),
             'Finite native grid N x5: x_mm,y_mm,depth_mm,layer_id,volume_m3')
    _require(np.all(grid[:,4]>0),'Positive native physical cell volumes required')
    zs,first,counts=np.unique(grid[:,2],return_index=True,return_counts=True)
    nxy=int(counts[0]);nz=len(zs)
    _require(np.all(counts==nxy)and np.array_equal(first,np.arange(nz)*nxy)and nxy*nz==len(grid),
             'Native grid must be z-major with equal XY nodes per depth')
    planes=grid.reshape(nz,nxy,5);xy=planes[0,:,:2]
    _require(np.array_equal(planes[:,:,0],np.broadcast_to(xy[:,0],(nz,nxy)))and
             np.array_equal(planes[:,:,1],np.broadcast_to(xy[:,1],(nz,nxy)))and
             np.array_equal(planes[:,:,2],np.broadcast_to(zs[:,None],(nz,nxy))),
             'Every physical depth plane must retain identical ordered XY coordinates')
    layers=planes[:,0,3].astype(int)
    _require(np.array_equal(planes[:,:,3],np.broadcast_to(layers[:,None],(nz,nxy))),
             'One exact integer physical layer ID per depth plane')
    bounds=np.asarray(INTERFACES_MM);expected=np.searchsorted(bounds,zs,side='right')-1
    _require(np.all(zs>0)and np.all(zs<bounds[-1])and np.array_equal(layers,expected),
             'Layer IDs must match physical interfaces 0/.1/5.1/10.1/25.1 mm')
    xs=np.unique(xy[:,0]);ys=np.unique(xy[:,1]);ix=np.searchsorted(xs,xy[:,0]);iy=np.searchsorted(ys,xy[:,1])
    _require(len(np.unique(iy*len(xs)+ix))==nxy,'Unique physical XY cells required')
    lookup=np.full((len(ys),len(xs)),-1,np.int64);lookup[iy,ix]=np.arange(nxy)
    return dict(xs=xs,ys=ys,zs=zs,layers=layers,lookup=lookup,nxy=nxy,nz=nz,cell_count=len(grid))


def _axis_stencil(np,axis,coordinate):
    nearest=int(np.argmin(abs(axis-coordinate)))
    if abs(float(axis[nearest])-coordinate)<=COORDINATE_TOLERANCE_MM:return [nearest],[1.]
    high=int(np.searchsorted(axis,coordinate,side='right'))
    _require(0<high<len(axis),'Physical XY interpolation would extrapolate outside native coordinates')
    low=high-1;fraction=(coordinate-float(axis[low]))/(float(axis[high])-float(axis[low]))
    return [low,high],[1.-fraction,fraction]


def _z_stencil(np,layout,depth,allow_same_layer_extrapolation):
    bounds=np.asarray(INTERFACES_MM);layer=int(np.searchsorted(bounds,depth,side='right')-1)
    _require(0<=layer<4 and bounds[layer]<depth<bounds[layer+1],
             'Requested tip depth must lie strictly inside one physical layer; interface values need a separate explicit reconstruction')
    indices=np.flatnonzero(layout['layers']==layer);z=layout['zs'][indices]
    _require(len(indices)>0,'No native depth samples in requested physical layer')
    nearest=int(np.argmin(abs(z-depth)));nearest_global=int(indices[nearest])
    info=dict(layer=layer,physical_layer_bounds_mm=[float(bounds[layer]),float(bounds[layer+1])],
        requested_depth_mm=float(depth),nearest_native_depth_mm=float(z[nearest]),
        distance_to_nearest_physical_layer_boundary_mm=float(min(depth-bounds[layer],bounds[layer+1]-depth)),
        cross_layer_interpolation=False,allow_same_layer_extrapolation=bool(allow_same_layer_extrapolation))
    if abs(float(z[nearest])-depth)<=COORDINATE_TOLERANCE_MM:
        info.update(method='exact_native_depth_plane',sample_depths_mm=[float(z[nearest])],signed_weights=[1.],
                    extrapolation_distance_mm=0.,extrapolation_distance_over_sample_spacing=0.,native_depth_exact=True)
        return [nearest_global],[1.],info,nearest_global
    if len(indices)<2:
        info.update(method='unavailable_same_layer_bracket_missing',reason='Fewer than two same-layer depth samples')
        return None,None,info,nearest_global
    high=int(np.searchsorted(z,depth,side='right'))
    if high==0:local=[0,1];outside=True
    elif high==len(z):local=[len(z)-2,len(z)-1];outside=True
    else:local=[high-1,high];outside=False
    za,zb=(float(z[k])for k in local);spacing=zb-za;fraction=(depth-za)/spacing
    distance=max(za-depth,depth-zb,0.);weights=[1.-fraction,fraction]
    info.update(sample_depths_mm=[za,zb],signed_weights=weights,sample_spacing_mm=spacing,
        extrapolation_distance_mm=distance,extrapolation_distance_over_sample_spacing=distance/spacing,native_depth_exact=False,
        uncertainty='Physical potential reconstruction only; same-layer curvature error is not bounded by this calculation')
    if outside and not allow_same_layer_extrapolation:
        info.update(method='unavailable_same_layer_bracket_missing',reason='Requested depth outside same-layer centre range; extrapolation not authorized')
        return None,None,info,nearest_global
    if outside and distance>spacing+COORDINATE_TOLERANCE_MM:
        info.update(method='unavailable_same_layer_extrapolation_beyond_one_spacing',reason='Explicit within-layer extrapolation exceeds one nearest spacing')
        return None,None,info,nearest_global
    info['method']='same_layer_one_sided_linear_extrapolation_explicit'if outside else'same_layer_linear_interpolation'
    return [int(indices[k])for k in local],weights,info,nearest_global


def _tip(np,layout,xyz,allow_same_layer_extrapolation):
    x,y,z=(float(v)for v in xyz);xi,xw=_axis_stencil(np,layout['xs'],x);yi,yw=_axis_stencil(np,layout['ys'],y)
    zi,zw,zinfo,nearest_z=_z_stencil(np,layout,z,allow_same_layer_extrapolation)
    nx=int(np.argmin(abs(layout['xs']-x)));ny=int(np.argmin(abs(layout['ys']-y)));nearest_xy=int(layout['lookup'][ny,nx])
    _require(nearest_xy>=0,'Nearest requested XY cell is outside represented physical domain')
    nearest_cell=nearest_z*layout['nxy']+nearest_xy
    actual=[float(layout['xs'][nx]),float(layout['ys'][ny]),float(layout['zs'][nearest_z])]
    info=dict(requested_tip_xyz_mm=[x,y,z],XY_method='bilinear physical coordinates; no XY extrapolation',
        x_sample_coordinates_mm=[float(layout['xs'][i])for i in xi],x_weights=[float(w)for w in xw],
        y_sample_coordinates_mm=[float(layout['ys'][i])for i in yi],y_weights=[float(w)for w in yw],Z=zinfo,
        nearest_native_cell_index=nearest_cell,nearest_native_xyz_mm=actual,
        nearest_distance_mm=float(math.sqrt(sum((a-b)**2 for a,b in zip(actual,[x,y,z])))),
        nearest_tie_policy='first smaller sorted coordinate; same physical layer')
    if zi is None:return dict(available=False,indices=[],weights=[],nearest_index=nearest_cell,metadata=info)
    indices=[];weights=[]
    for kz,wz in zip(zi,zw):
        for ky,wy in zip(yi,yw):
            for kx,wx in zip(xi,xw):
                xy=int(layout['lookup'][ky,kx]);_require(xy>=0,'A bilinear physical tip corner is outside represented domain')
                indices.append(int(kz*layout['nxy']+xy));weights.append(float(wz*wy*wx))
    _require(abs(sum(weights)-1.)<=1e-12,'Affine physical interpolation weights sum to one')
    return dict(available=True,indices=indices,weights=weights,nearest_index=nearest_cell,metadata=info)


def prepare(np,grid,*,allow_same_layer_extrapolation=False,guard=None,deadline_monotonic=None):
    """Prepare only small physical stencils; no full-grid lookup or field copy."""
    _check(guard,deadline_monotonic);layout=_layout(np,grid);probes=[]
    for depth in DEPTHS_MM:
        for cx,cy in CENTRES_XY_MM:
            for axis in('x','y'):
                _check(guard,deadline_monotonic);dx=TIP_SPACING_MM/2. if axis=='x'else 0.;dy=TIP_SPACING_MM/2. if axis=='y'else 0.
                negative=[cx-dx,cy-dy,depth];positive=[cx+dx,cy+dy,depth]
                neg=_tip(np,layout,negative,allow_same_layer_extrapolation);pos=_tip(np,layout,positive,allow_same_layer_extrapolation)
                probes.append(dict(probe_id='d%g_cx%g_cy%g_%s'%(depth,cx,cy,axis),centre_xyz_mm=[cx,cy,depth],
                    differential_axis=axis,tip_spacing_mm=TIP_SPACING_MM,negative_tip_xyz_mm=negative,positive_tip_xyz_mm=positive,
                    polarity='phi(positive tip)-phi(negative tip)',available=bool(neg['available']and pos['available']),negative=neg,positive=pos))
    _require(len(probes)==40,'Twenty physical centres times two horizontal probe axes')
    return dict(schema='task1-light-probe-physical-stencils-v2',estimator_id=ESTIMATOR_ID,requested_probe_count=40,probes=probes,
        cell_count=layout['cell_count'],native_XY_nodes=layout['nxy'],native_depth_planes=layout['nz'],
        memory_scope='Only 2D XY lookup used transiently; retained stencils contain at most eight native indices per tip, no full grid/phi/Q',
        allow_same_layer_extrapolation=bool(allow_same_layer_extrapolation),extrapolation_maximum_nearest_spacings=1.)


def sample_carrier(np,prepared,phi_peak_V,frequency_Hz,*,guard=None,deadline_monotonic=None):
    """Sample one actual native peak-phasor carrier; caller can then free phi."""
    _check(guard,deadline_monotonic);phi=np.asarray(phi_peak_V)
    _require(phi.shape==(prepared['cell_count'],)and np.iscomplexobj(phi)and np.isfinite(phi).all(),
             'Actual finite flat complex native peak potential, exact prepared grid order')
    frequency=float(frequency_Hz);_require(math.isfinite(frequency)and frequency>0,'Positive finite carrier frequency')
    difference=np.full(40,complex(float('nan'),float('nan')),np.complex128);nearest=np.empty(40,np.complex128)
    available=np.asarray([p['available']for p in prepared['probes']],bool)
    for i,probe in enumerate(prepared['probes']):
        _check(guard,deadline_monotonic);neg=probe['negative'];pos=probe['positive']
        nearest[i]=phi[pos['nearest_index']]-phi[neg['nearest_index']]
        if available[i]:
            a=sum(float(w)*phi[k]for k,w in zip(pos['indices'],pos['weights']))
            b=sum(float(w)*phi[k]for k,w in zip(neg['indices'],neg['weights']))
            difference[i]=a-b
    return dict(frequency_Hz=frequency,differential_phasors_V_peak=difference,
        nearest_native_differential_phasors_V_peak=nearest,available=available)


def waveform_metrics(np,phasors,frequencies_Hz,*,guard=None,deadline_monotonic=None):
    """Actual summed peak-phasor waveform; one/two scalar carriers only."""
    _check(guard,deadline_monotonic);delta=np.asarray(phasors,np.complex128);freq=np.asarray(frequencies_Hz,float)
    _require(delta.ndim==freq.ndim==1 and len(delta)==len(freq)and len(freq)in(1,2)and np.isfinite(delta).all()and np.isfinite(freq).all()and np.all(freq>0)and len(np.unique(freq))==len(freq),
             'One or two distinct finite scalar carrier peak phasors required; no multi-tone modulation-formula extension')
    bins=np.rint(freq*DURATION_S).astype(int)
    _require(np.all(abs(freq*DURATION_S-bins)<=1e-10)and np.all(bins>0)and np.all(bins<SAMPLES//2),
             'Coherent 0.1s window and frequencies below both sampled Nyquist limits required')
    t=np.arange(SAMPLES,dtype=float)*(DURATION_S/SAMPLES);analytic=np.zeros(SAMPLES,np.complex128)
    for a,f in zip(delta,freq):analytic+=a*np.exp(2j*np.pi*f*t)
    wave=analytic.real;envelope=np.abs(analytic);vpp=float(wave.max()-wave.min());rms=float(np.sqrt(np.mean(wave**2)))
    exact_rms=float(np.sqrt(np.sum(abs(delta)**2)/2.));spectrum=np.fft.rfft(wave)*(2./SAMPLES);spectrum[0]*=.5;spectrum[-1]*=.5
    observed=spectrum[bins]
    _require(np.all(abs(observed-delta)<=1e-10+1e-10*abs(delta))and abs(rms-exact_rms)<=1e-10+1e-10*exact_rms,
             'Actual real-waveform coherent DFT and exact carrier-RMS regression failed')
    _check(guard,deadline_monotonic);t2=np.arange(CHECK_SAMPLES,dtype=float)*(DURATION_S/CHECK_SAMPLES);wave2=np.zeros(CHECK_SAMPLES,float)
    for a,f in zip(delta,freq):wave2+=np.real(a*np.exp(2j*np.pi*f*t2))
    vpp2=float(wave2.max()-wave2.min());vpp_delta=abs(vpp2-vpp)/max(abs(vpp2),1e-15)
    am=0. if len(delta)==1 else 2.*float(min(abs(delta[0]),abs(delta[1])))
    beat=0. if len(freq)==1 else float(abs(freq[1]-freq[0]));envelope_spectrum=np.fft.rfft(envelope-envelope.mean())*(2./SAMPLES)
    ten_bin=int(round(10.*DURATION_S));other=np.abs(spectrum).copy();other[bins]=0.;other[0]=0.;other_index=int(np.argmax(other))
    excerpt_indices=np.arange(128,dtype=int)*4;envelope_indices=np.linspace(0,SAMPLES-1,128,dtype=int)
    metrics=dict(carrier_waveform_Vpp=vpp,carrier_waveform_N65536_Vpp=vpp2,carrier_RMS_V=rms,carrier_RMS_exact_V=exact_rms,
        Vpp_sampling_diagnostic=dict(N32768_Vpp=vpp,N65536_Vpp=vpp2,relative_delta=float(vpp_delta),denominator_floor_V=1e-15,
            relative_delta_limit=VPP_RELATIVE_DELTA_LIMIT,passed=bool(vpp_delta<=VPP_RELATIVE_DELTA_LIMIT),scope='Prospective numerical waveform-sampling diagnostic, not a tissue/human safety or spatial-convergence gate'),
        envelope_AM_exact_V_peak=am,envelope_AM_sampled_V_peak=float(envelope.max()-envelope.min()),
        envelope_max_exact_V=float(np.sum(abs(delta))),envelope_min_exact_V=float(abs(abs(delta[0])-abs(delta[1])))if len(delta)==2 else float(abs(delta[0])),
        envelope_difference_frequency_Hz=beat,envelope_10Hz_DFT_peak_V=float(abs(envelope_spectrum[ten_bin])),
        physical_voltage_10Hz_DFT_peak_V=float(abs(spectrum[ten_bin])),physical_voltage_DC_mean_V=float(spectrum[0].real),
        carrier_phasors_V_peak=[_complex(a)for a in delta],spectrum_coherent_DFT_phasors_V_peak=[_complex(a)for a in observed],
        maximum_other_voltage_DFT_peak_V=float(other[other_index]),maximum_other_voltage_DFT_frequency_Hz=float(other_index/DURATION_S),
        modulation_scope='Scalar differential-voltage two-tone analytic-envelope depth; no vector TIS metric or physiological equivalence. Envelope 10Hz is demodulation, not necessarily a physical voltage Fourier component at10Hz.',
        single_carrier_has_two_tone_AM=False if len(delta)==1 else None)
    small=dict(carrier_excerpt_time_s=t[excerpt_indices].copy(),carrier_excerpt_V=wave[excerpt_indices].copy(),
        envelope_time_s=t[envelope_indices].copy(),envelope_V=envelope[envelope_indices].copy())
    return metrics,small


def finish(np,prepared,carrier_samples,*,candidate_id=None,run_id=None,guard=None,deadline_monotonic=None):
    """Reconstruct only 40 small sampled differences, never native fields."""
    _check(guard,deadline_monotonic);samples=list(carrier_samples)
    _require(len(samples)in(1,2),'Exactly one or two actual sampled carriers, no generic multi-tone AM extension')
    samples=sorted(samples,key=lambda s:s['frequency_Hz']);freq=[float(s['frequency_Hz'])for s in samples]
    _require(len(set(freq))==len(freq)and all(math.isfinite(f)and f>0 and abs(f*DURATION_S-round(f*DURATION_S))<=1e-10 and 0<round(f*DURATION_S)<SAMPLES//2 for f in freq),'Distinct coherent positive frequencies required even when every probe is unavailable')
    available=np.asarray([p['available']for p in prepared['probes']],bool)
    for sample in samples:
        _require(np.array_equal(sample['available'],available)and sample['differential_phasors_V_peak'].shape==(40,)and sample['nearest_native_differential_phasors_V_peak'].shape==(40,),
                 'Each carrier must use exact same 40 physical probe stencils/availability')
    phasors=np.column_stack([s['differential_phasors_V_peak']for s in samples]);nearest=np.column_stack([s['nearest_native_differential_phasors_V_peak']for s in samples])
    rows=[];waveforms=[];envelopes=[];ids=[];actual_extrapolated=0;diagnostic_failures=[];carrier_time=None;envelope_time=None
    for i,p in enumerate(prepared['probes']):
        _check(guard,deadline_monotonic);row={k:p[k]for k in('probe_id','centre_xyz_mm','differential_axis','tip_spacing_mm','negative_tip_xyz_mm','positive_tip_xyz_mm','polarity')}
        row.update(negative_tip_sampling=p['negative']['metadata'],positive_tip_sampling=p['positive']['metadata'])
        if not available[i]:
            row.update(status='unavailable_same_layer_bracket_missing',unloaded=None,strict_same_layer_bracket_available=False,reason='At least one tip has no permitted same-layer depth reconstruction; nearest values are not substituted')
        else:
            metrics,small=waveform_metrics(np,phasors[i],freq,guard=guard,deadline_monotonic=deadline_monotonic)
            extrap=any('one_sided_linear_extrapolation'in tip['metadata']['Z']['method']for tip in(p['negative'],p['positive']))
            actual_extrapolated+=int(extrap);difference=nearest[i]-phasors[i]
            row.update(status='calculated_unloaded_only',unloaded=metrics,same_layer_extrapolation_used=bool(extrap),strict_same_layer_bracket_available=not bool(extrap),
                nearest_point_sensitivity=dict(nearest_native_differential_phasors_V_peak=[_complex(a)for a in nearest[i]],
                    nearest_minus_interpolated_complex_V_peak=[_complex(a)for a in difference],absolute_difference_V_peak=[float(a)for a in abs(difference)],
                    relative_complex_difference=[float(a)for a in abs(difference)/np.maximum(abs(phasors[i]),1e-12)],denominator_floor_V=1e-12,
                    scope='Nearest-versus-reconstructed sampling sensitivity only; not a validated interpolation-error bound'),
                ideal_gain_only_unloaded=dict(nominal_50x=dict(physical_probe_output_Vpp=metrics['carrier_waveform_Vpp']/50.,physical_probe_output_RMS_V=metrics['carrier_RMS_exact_V']/50.,scope_display_Vpp_if_ratio_50=metrics['carrier_waveform_Vpp']),
                    alternate_500x=dict(physical_probe_output_Vpp=metrics['carrier_waveform_Vpp']/500.,scope_display_Vpp_if_ratio_500=metrics['carrier_waveform_Vpp'],scope_display_Vpp_if_menu_stays_50=metrics['carrier_waveform_Vpp']/10.)))
            if not metrics['Vpp_sampling_diagnostic']['passed']:diagnostic_failures.append(p['probe_id'])
            waveforms.append(small['carrier_excerpt_V']);envelopes.append(small['envelope_V']);ids.append(p['probe_id']);carrier_time=small['carrier_excerpt_time_s'];envelope_time=small['envelope_time_s']
        rows.append(row)
    calculated=int(np.count_nonzero(available));summary=dict(schema='task1-native-light-unloaded-probe-prediction-v2',estimator_id=ESTIMATOR_ID,
        status='calculated_unloaded_only_complete40'if calculated==40 else'partial_missing_native_same_layer_brackets',candidate_id=candidate_id,run_id=run_id,
        probe_count=40,requested_probe_count=40,calculated_probe_count=calculated,unavailable_probe_count=40-calculated,same_layer_extrapolated_probe_count=actual_extrapolated,strict_same_layer_bracket_available_probe_count=calculated-actual_extrapolated,
        frequencies_Hz=freq,probes=rows,source_recipe=SOURCE_PRODUCER,native_grid=dict(cell_count=prepared['cell_count'],XY_nodes=prepared['native_XY_nodes'],depth_planes=prepared['native_depth_planes']),
        coordinate_system=dict(surface_depth_mm=0.,positive_depth='+z into fixed phantom',horizontal_axes='phantom x/y',interfaces_mm=list(INTERFACES_MM),
            centre_pattern='Each depth5/10/15/20mm: centre and±5mm x/y; these centre offsets are distinct from fixed5mm tip spacing'),
        interpolation_policy=dict(XY='Bilinear actual physical coordinates, no XY extrapolation',Z='Exact plane or same-layer linear bracket; never cross a material interface',
            allow_same_layer_extrapolation=prepared['allow_same_layer_extrapolation'],maximum_nearest_spacings=1.,signed_tip_weights_and_boundary_distances_preserved=True,
            failure_policy='Unavailable row, never silently substitute nearest/cross-layer values',native_point_reconstruction_not_finite_tip_geometry=True),
        waveform_window=dict(duration_s=DURATION_S,primary_samples=SAMPLES,check_samples=CHECK_SAMPLES,
            common_period_2000_2010_Hz_s=.1,Vpp_definition='max-minus-min actual real sum over finite stated samples; bothN kept; continuum extrema not solved',
            RMS_definition='Exact distinct coherent-carrier sqrt(sum(abs(dphi_peak)^2)/2), checked against actual full-window waveform',
            spectrum_definition='Actual coherent real-waveform rFFT, peak2FFT/N, DC/Nyquist halfscaled; carrier+10Hz+largest other bin only',
            representative_points_per_probe=256,carrier_excerpt_points=128,carrier_excerpt_stride_native_samples=4,envelope_full_window_points=128,
            representative_scope='Carrier excerpt is short high-rate actual samples; envelope spans0.1s. Summary metrics use all32768/65536 samples, not the excerpts'),
        Vpp_sampling_diagnostic=dict(relative_delta_limit=VPP_RELATIVE_DELTA_LIMIT,failed_probe_ids=diagnostic_failures,all_calculated_pass=not diagnostic_failures,
            scope='Numerical waveform-sampling diagnostic only; does not clear prior spatial/contact/edge/SC gates'),
        instruments=instrument_metadata(),probe_loaded_prediction=False,experimental_validation=False,actual_switch_settings_verified=False,
        new_PDE_RHS=0,new_angular_evaluations=0,native_Q_loaded=False,candidate_adopted=False)
    arrays=dict(probe_differential_phasors_V_peak=phasors,nearest_native_differential_phasors_V_peak=nearest,probe_available=available,
        frequencies_Hz=np.asarray(freq,float),representative_probe_ids=np.asarray(ids),carrier_excerpt_time_s=np.asarray([]if carrier_time is None else carrier_time,float),
        representative_carrier_excerpt_V=np.asarray(waveforms,float).reshape(calculated,128),envelope_time_s=np.asarray([]if envelope_time is None else envelope_time,float),
        representative_envelope_V=np.asarray(envelopes,float).reshape(calculated,128))
    _check(guard,deadline_monotonic);return dict(summary=summary,arrays=arrays)


def evaluate(np,grid,phi_by_frequency,frequencies_Hz,*,allow_same_layer_extrapolation=False,candidate_id=None,run_id=None,guard=None,deadline_monotonic=None):
    """Convenience API; streaming prepare/sample_carrier/finish uses less RSS."""
    prepared=prepare(np,grid,allow_same_layer_extrapolation=allow_same_layer_extrapolation,guard=guard,deadline_monotonic=deadline_monotonic);samples=[]
    for frequency in frequencies_Hz:
        phi=phi_by_frequency[frequency]if frequency in phi_by_frequency else phi_by_frequency[str(frequency)]
        samples.append(sample_carrier(np,prepared,phi,frequency,guard=guard,deadline_monotonic=deadline_monotonic))
    return finish(np,prepared,samples,candidate_id=candidate_id,run_id=run_id,guard=guard,deadline_monotonic=deadline_monotonic)
