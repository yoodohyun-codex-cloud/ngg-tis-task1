"""Copied signed two-carrier circuit bookkeeping; numerics injected by Root."""
import math
LAYERS=('sc','dermis','fat','muscle')
def require(ok,message):
 if not ok:raise ValueError(message)
def complex_value(v):return complex(v['real'],v['imaginary'])if isinstance(v,dict)else complex(v)
def complex_pair(v):return dict(real=float(complex(v).real),imaginary=float(complex(v).imag))
def synthesize(np,raws,proofs):
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


