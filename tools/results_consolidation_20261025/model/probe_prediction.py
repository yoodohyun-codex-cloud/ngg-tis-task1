"""Owner-called UNLOADED differential-potential prediction, no import IO/work.

Both supplied potential spectra must be actual 2000/2010 Hz peak phasors at
the same candidate/drive. The instrument model is metadata plus ideal gain
bookkeeping only: no probe-loaded PDE, bandwidth/load transfer or experiment
is asserted. NumPy is injected by the finite owner.
"""
INTERFACES_MM=(0.,.1,5.1,10.1,25.1)
DEPTHS_MM=(5.,10.,15.,20.)
CENTRES_XY_MM=((0.,0.),(5.,0.),(-5.,0.),(0.,5.),(0.,-5.))
TIP_SPACING_MM=5.
FREQUENCIES_HZ=(2000,2010)
SAMPLES=32768
DURATION_S=.1
COORDINATE_TOLERANCE_MM=1e-9


def _require(condition,message):
    if not condition:raise ValueError(message)


def _check(guard,deadline):
    import time
    guard()
    if deadline is not None and time.monotonic()>=deadline:
        raise TimeoutError('Unloaded probe prediction incomplete: deadline reached')


def _complex(value):
    value=complex(value)
    return dict(real=float(value.real),imaginary=float(value.imag))


def instrument_metadata():
    return dict(status='User-supplied specifications and ideal gain bookkeeping only; actual settings unconfirmed',
        probe=dict(model='ETA5001',bandwidth_Hz=15e6,
            differential_input=dict(resistance_ohm=8e6,capacitance_F=3.5e-12),
            each_input_to_ground=dict(resistance_ohm=4e6,capacitance_F=7e-12),attenuation_choices=[50,500]),
        oscilloscope=dict(model='Keysight DSOX1202A',input_resistance_ohm=1e6,input_resistance_tolerance_fraction=.02,
            input_capacitance_F=16e-12,input_capacitance_tolerance_F=3e-12,
            possible_body_bandwidths_Hz=[70e6,100e6,200e6],actual_body_option_verified=False),
        recommended_start=dict(probe_attenuation=50,scope_display_ratio=50,coupling='DC',
            scope_bandwidth_limit_Hz=20e6,external_50ohm_termination=False,actual_switch_menu_settings_verified=False),
        load_model_applied=False,probe_loaded_PDE_performed=False,
        scope_input_connected_directly_in_parallel_with_phantom=False,
        load_interpretation='ETA input specifications preserved as supplied; no input circuit assembled or R/C effects applied. Scope R/C belongs downstream of the active probe output.',
        scaling_definition='probe physical output=unloaded tip difference/physical attenuation; displayed voltage=probe output*selected scope display ratio',
        bandwidth_or_output_loading_transfer_applied=False,hardware_validation=False)


def _layout(np,grid):
    grid=np.asarray(grid,float)
    _require(grid.ndim==2 and grid.shape[1]==5 and len(grid)>0 and np.isfinite(grid).all(),
             'Finite grid N×5 x_mm,y_mm,z_mm,layer,volume_m3 required')
    xs=np.unique(grid[:,0]);ys=np.unique(grid[:,1]);zs,first=np.unique(grid[:,2],return_index=True)
    ix=np.searchsorted(xs,grid[:,0]);iy=np.searchsorted(ys,grid[:,1]);iz=np.searchsorted(zs,grid[:,2])
    layers=grid[first,3].astype(int)
    _require(np.array_equal(grid[:,3],layers[iz])and np.all((layers>=0)&(layers<4)),
             'Each centre-depth plane must have one exact physical layer ID')
    bounds=np.asarray(INTERFACES_MM)
    expected=np.searchsorted(bounds,zs,side='right')-1
    _require(np.all(zs>0)and np.all(zs<bounds[-1])and np.array_equal(layers,expected),
             'Layer IDs must follow fixed physical interfaces 0/.1/5.1/10.1/25.1 mm')
    linear=(iz*len(ys)+iy)*len(xs)+ix
    _require(len(np.unique(linear))==len(grid),'Unique physical native cells required')
    lookup=np.full((len(zs),len(ys),len(xs)),-1,np.int64);lookup[iz,iy,ix]=np.arange(len(grid))
    return dict(grid=grid,xs=xs,ys=ys,zs=zs,layers=layers,lookup=lookup)


def _axis_stencil(np,axis,coordinate):
    nearest=int(np.argmin(abs(axis-coordinate)))
    if abs(float(axis[nearest])-coordinate)<=COORDINATE_TOLERANCE_MM:return [nearest],[1.]
    high=int(np.searchsorted(axis,coordinate,side='right'))
    _require(0<high<len(axis),'Tip lies outside native XY interpolation range; extrapolation is forbidden')
    low=high-1;fraction=(coordinate-float(axis[low]))/(float(axis[high])-float(axis[low]))
    return [low,high],[1.-fraction,fraction]


def _z_stencil(np,layout,depth):
    bounds=np.asarray(INTERFACES_MM);layer=int(np.searchsorted(bounds,depth,side='right')-1)
    _require(0<=layer<4 and bounds[layer]<=depth<=bounds[layer+1],'Depth must lie within a physical layer')
    indices=np.flatnonzero(layout['layers']==layer);z=layout['zs'][indices]
    _require(len(indices)>=2,'Two same-layer centre depths required for probe prediction')
    nearest=int(np.argmin(abs(z-depth)));nearest_global=int(indices[nearest])
    if abs(float(z[nearest])-depth)<=COORDINATE_TOLERANCE_MM:
        return [nearest_global],[1.],dict(layer=layer,method='exact_native_depth_plane',
            sample_depths_mm=[float(z[nearest])],extrapolation_distance_mm=0.,
            extrapolation_distance_over_sample_spacing=0.,native_depth_exact=True),nearest_global
    high=int(np.searchsorted(z,depth,side='right'))
    if high==0:local=[0,1];method='same_layer_one_sided_linear_extrapolation'
    elif high==len(z):local=[len(z)-2,len(z)-1];method='same_layer_one_sided_linear_extrapolation'
    else:local=[high-1,high];method='same_layer_linear_interpolation'
    za,zb=(float(z[k])for k in local);spacing=zb-za;fraction=(depth-za)/spacing
    distance=max(za-depth,depth-zb,0.)
    _require(distance<=spacing+COORDINATE_TOLERANCE_MM,
             'Required same-layer extrapolation exceeds one nearest sample spacing')
    info=dict(layer=layer,physical_layer_bounds_mm=[float(bounds[layer]),float(bounds[layer+1])],method=method,
              sample_depths_mm=[za,zb],interpolation_weights=[1.-fraction,fraction],
              extrapolation_distance_mm=distance,extrapolation_distance_over_sample_spacing=distance/spacing,
              native_depth_exact=False,uncertainty='Linear potential reconstruction only; curvature error unbounded by this calculation')
    return [int(indices[k])for k in local],[1.-fraction,fraction],info,nearest_global


def sample_tip(np,layout,phi0,phi1,xyz_mm):
    """Pure interpolated and same-layer nearest samples, exposed for source tests."""
    x,y,z=(float(v)for v in xyz_mm)
    xi,xw=_axis_stencil(np,layout['xs'],x);yi,yw=_axis_stencil(np,layout['ys'],y)
    zi,zw,zinfo,nearest_z=_z_stencil(np,layout,z)
    result=np.zeros(2,np.complex128)
    for kz,wz in zip(zi,zw):
        for ky,wy in zip(yi,yw):
            for kx,wx in zip(xi,xw):
                cell=int(layout['lookup'][kz,ky,kx]);_require(cell>=0,'A required bilinear tip corner is outside the represented native domain')
                result+=wz*wy*wx*np.asarray([phi0[cell],phi1[cell]])
    # Ties select the smaller sorted coordinate; nearest depth remains inside
    # the exact same physical layer as interpolation/extrapolation.
    nx=int(np.argmin(abs(layout['xs']-x)));ny=int(np.argmin(abs(layout['ys']-y)))
    nearest_cell=int(layout['lookup'][nearest_z,ny,nx]);_require(nearest_cell>=0,'Nearest physical tip cell is missing')
    nearest=np.asarray([phi0[nearest_cell],phi1[nearest_cell]],np.complex128)
    actual=layout['grid'][nearest_cell,:3]
    info=dict(requested_tip_xyz_mm=[x,y,z],XY_method='bilinear physical-coordinate weights; no XY extrapolation',
              x_sample_coordinates_mm=[float(layout['xs'][i])for i in xi],x_weights=[float(v)for v in xw],
              y_sample_coordinates_mm=[float(layout['ys'][i])for i in yi],y_weights=[float(v)for v in yw],
              Z=zinfo,nearest_native_cell_index=nearest_cell,nearest_native_xyz_mm=[float(v)for v in actual],
              nearest_distance_mm=float(np.linalg.norm(actual-np.asarray([x,y,z]))),
              nearest_tie_policy='smaller sorted coordinate; nearest same-layer depth')
    return result,nearest,info


def build(np,grid,phi0,phi1,guard=lambda:None,deadline=None):
    """Return 40 unloaded probe summaries and compact spectra/waveform arrays."""
    _check(guard,deadline);layout=_layout(np,grid)
    p0=np.asarray(phi0,np.complex128);p1=np.asarray(phi1,np.complex128)
    _require(p0.shape==p1.shape==(len(layout['grid']),)and np.isfinite(p0).all()and np.isfinite(p1).all(),
             'Actual matched 2000/2010 complex peak potential arrays required')
    t=np.arange(SAMPLES,dtype=float)*(DURATION_S/SAMPLES)
    e0=np.exp(2j*np.pi*2000.*t);e1=np.exp(2j*np.pi*2010.*t);beat=np.exp(2j*np.pi*10.*t)
    rows=[];phasors=[];nearest_phasors=[];waveforms=[];waveform_ids=[]
    for depth in DEPTHS_MM:
        for cx,cy in CENTRES_XY_MM:
            for axis in('x','y'):
                _check(guard,deadline);probe_id='d%g_cx%g_cy%g_%s'%(depth,cx,cy,axis)
                dx=TIP_SPACING_MM/2. if axis=='x'else 0.;dy=TIP_SPACING_MM/2. if axis=='y'else 0.
                negative=[cx-dx,cy-dy,depth];positive=[cx+dx,cy+dy,depth]
                neg,near_neg,neginfo=sample_tip(np,layout,p0,p1,negative)
                pos,near_pos,posinfo=sample_tip(np,layout,p0,p1,positive)
                delta=pos-neg;nearest_delta=near_pos-near_neg;a,b=delta
                waveform=np.real(a*e0+b*e1);rms=float(np.sqrt(np.mean(waveform**2)))
                analytic_rms=float(np.sqrt((abs(a)**2+abs(b)**2)/2.));vpp=float(np.max(waveform)-np.min(waveform))
                envelope=np.abs(a+b*beat);am=2.*min(abs(a),abs(b))
                spectrum=np.fft.rfft(waveform)*(2./SAMPLES);k0=200;k1=201
                spectral=np.asarray([spectrum[k0],spectrum[k1]])
                _require(np.all(abs(spectral-delta)<=1e-10+1e-10*abs(delta))and
                         abs(rms-analytic_rms)<=1e-10+1e-10*analytic_rms,
                         'Probe waveform RMS/coherent DFT phasor check failed')
                other=np.abs(spectrum);other[k0]=0.;other[k1]=0.;other_index=int(np.argmax(other))
                difference=nearest_delta-delta
                row=dict(probe_id=probe_id,centre_xyz_mm=[cx,cy,depth],differential_axis=axis,
                    tip_spacing_mm=TIP_SPACING_MM,negative_tip_xyz_mm=negative,positive_tip_xyz_mm=positive,
                    polarity='phi(positive tip)-phi(negative tip)',negative_tip_sampling=neginfo,positive_tip_sampling=posinfo,
                    unloaded=dict(carrier_waveform_Vpp=vpp,carrier_RMS_V=rms,carrier_RMS_formula_V=analytic_rms,
                        envelope_AM_exact_V_peak=float(am),envelope_AM_sampled_V_peak=float(envelope.max()-envelope.min()),
                        envelope_max_exact_V=float(abs(a)+abs(b)),envelope_min_exact_V=float(abs(abs(a)-abs(b))),
                        envelope_difference_frequency_Hz=10.,carrier_phasors_V_peak=[_complex(v)for v in delta],
                        spectrum_coherent_DFT_phasors_V_peak=[_complex(v)for v in spectral],
                        maximum_other_DFT_peak_V=float(other[other_index]),maximum_other_DFT_frequency_Hz=other_index/DURATION_S),
                    nearest_point_sensitivity=dict(nearest_native_differential_phasors_V_peak=[_complex(v)for v in nearest_delta],
                        nearest_minus_interpolated_complex_V_peak=[_complex(v)for v in difference],
                        absolute_difference_V_peak=[float(v)for v in abs(difference)],
                        relative_complex_difference=[float(v)for v in abs(difference)/np.maximum(abs(delta),1e-12)],
                        denominator_floor_V=1e-12,scope='Sampling sensitivity only; not a validated interpolation-error bound'),
                    ideal_gain_only_unloaded=dict(
                        nominal_50x=dict(physical_probe_output_Vpp=vpp/50.,physical_probe_output_RMS_V=rms/50.,scope_display_Vpp_if_ratio_50=vpp),
                        alternate_500x=dict(physical_probe_output_Vpp=vpp/500.,physical_probe_output_RMS_V=rms/500.,
                            scope_display_Vpp_if_ratio_500=vpp,scope_display_Vpp_if_menu_stays_50=vpp/10.)))
                if cx==cy==0. and depth in(5.,20.)and axis=='x':
                    waveforms.append(waveform.copy());waveform_ids.append(probe_id)
                rows.append(row);phasors.append(delta);nearest_phasors.append(nearest_delta)
    _check(guard,deadline);_require(len(rows)==40,'Complete 40-probe contract required')
    summary=dict(schema='task1-unloaded-cross-probe-prediction-v1',status='calculated_unloaded_only',probes=rows,
        probe_count=40,frequencies_Hz=list(FREQUENCIES_HZ),source_basis='2000Hz output0 and2010Hz output1; caller-supplied actual 1Vpp high-Z solutions',
        coordinate_system=dict(surface_depth_mm=0.,positive_depth='+z into phantom',horizontal_axes='phantom x/y',
            centre_pattern='Centre plus ±5 mm on x and y at each depth; centre offsets are distinct from 5 mm tip spacing'),
        waveform_window=dict(duration_s=DURATION_S,samples=SAMPLES,sample_rate_Hz=SAMPLES/DURATION_S,
            Vpp_definition='max(real summed carrier waveform)-min over the finite stated samples; sub-sample extrema are not solved',
            spectrum_definition='Coherent real-waveform DFT, peak phasor 2*FFT/N at2000/2010Hz; remaining-bin maximum retained',
            modulation_definition='2min(abs(delta_phi_2000),abs(delta_phi_2010)); envelope depth, not a physical 10Hz voltage spectral component'),
        representative_waveform_probe_ids=waveform_ids,instruments=instrument_metadata(),
        interpolation_scope='Physical bilinear XY plus same-layer linear Z; within-layer one-sided extrapolation explicitly labelled and limited to one nearest spacing',
        probe_loaded_prediction=False,experimental_validation=False,actual_switch_settings_verified=False,
        candidate_adopted=False,old_data_preserved=True)
    arrays=dict(probe_differential_phasors_V_peak=np.asarray(phasors,np.complex128),
        nearest_native_differential_phasors_V_peak=np.asarray(nearest_phasors,np.complex128),
        frequencies_Hz=np.asarray(FREQUENCIES_HZ,int),representative_time_s=t,
        representative_waveforms_V=np.asarray(waveforms,float))
    return dict(summary=summary,arrays=arrays)
