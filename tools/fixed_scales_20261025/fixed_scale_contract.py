"""Pure fixed range contract for an explicitly guarded cached GUI export.

Import performs no reads or calculations. build_contract() accepts already loaded
payloads; it never reads files, writes results, solves a PDE or changes amplitudes.
The global E limit deliberately covers several differently labelled quantities
with the same V/m numerical range. Signed plots use the corresponding +/- limit.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
from typing import Callable

import numpy as np


MAX_DESCRIPTOR_BYTES = 4*1024**2
MAX_DISPLAY_VALUES = 1000000
CASES = ('TIS', 'C1')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite_number(value, *, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value>0 if positive else value>=0)


def nice_upper(value):
    """Smallest 1/2/5*10**k upper bound, never rounded below the input."""
    require(finite_number(value), 'Finite nonnegative scale maximum required')
    if value == 0:
        return 1.0
    exponent = math.floor(math.log10(value))
    base = 10.0**exponent
    for multiplier in (1., 2., 5., 10.):
        result = multiplier*base
        if math.isfinite(result) and result >= value:
            return float(result)
    raise ValueError('Finite nice upper bound is not representable')


def _bytes(text, expected):
    require(isinstance(text, str) and 0<=expected<=MAX_DESCRIPTOR_BYTES and
            len(text)<=(expected+2)//3*4+4, 'Bounded declared display descriptor required')
    try:
        raw = base64.b64decode(text, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError('Invalid display base64') from error
    require(len(raw)==expected, 'Display shape and exact byte count differ')
    return raw


def _descriptor(value, count):
    require(isinstance(value, dict) and value.get('dtype')=='<f4' and
            isinstance(value.get('shape'),list) and len(value['shape'])==4 and
            all(type(n) is int and n>0 for n in value['shape']) and
            value['shape'][-2:]==[3,2] and math.prod(value['shape'])==count*6,
            'Exact native [v,u,xyz,re/im] Float32 descriptor required')
    raw = _bytes(value.get('data_base64'),count*6*4)
    return np.frombuffer(raw,dtype='<f4').reshape(count,3,2),hashlib.sha256(raw).hexdigest()


def _float16(text):
    require(isinstance(text,str) and len(text)<=MAX_DISPLAY_VALUES*3,
            'Bounded Float16 display required')
    try:
        raw=base64.b64decode(text,validate=True)
    except (ValueError,TypeError) as error:
        raise ValueError('Invalid Float16 base64') from error
    require(len(raw)%2==0 and 0<len(raw)<=MAX_DISPLAY_VALUES*2,'Bounded exact Float16 byte count required')
    result=np.frombuffer(raw,dtype='<f2').astype(np.float64)
    require(not np.isinf(result).any(),'Infinity is never a phantom-exterior marker')
    use=np.isfinite(result)
    require(use.any() and np.all(result[use]>=0),'Finite nonnegative physical display samples required')
    return result,hashlib.sha256(raw).hexdigest()


def _scale_maxima(analysis):
    modes=analysis.get('modes',{})
    require(isinstance(modes,dict) and modes,'Actual saved normalization modes required')
    values={case:[] for case in CASES};selections=[]
    for name,mode in modes.items():
        reference=mode.get('reference_amplitude_scale')
        require(finite_number(reference,positive=True),'Finite positive TIS amplitude required')
        values['TIS'].append(reference)
        matches=mode.get('matches',{})
        require(isinstance(matches,dict) and matches,'Actual C1 RMS matching choices required')
        for match,item in matches.items():
            scale=item.get('amplitude_scale',item.get('required_source_Vpp'))
            require(finite_number(scale,positive=True),'Finite positive C1 amplitude required')
            if 'required_source_Vpp' in item:
                require(finite_number(item['required_source_Vpp'],positive=True) and
                        math.isclose(scale,item['required_source_Vpp'],rel_tol=1e-12,abs_tol=1e-12),
                        'C1 one-Vpp unit amplitude and required source Vpp must agree')
            values['C1'].append(scale)
            selections.append(dict(mode=name,match=match,TIS=reference,C1=scale))
    return {case:float(max(items)) for case,items in values.items()},selections


def _axis(edges,name):
    require(isinstance(edges,list) and len(edges)>=2 and
            all(type(v)in(int,float)and math.isfinite(v)for v in edges)and
            all(b>a for a,b in zip(edges,edges[1:])), 'Increasing physical cell faces required: '+name)
    return [float(edges[0]),float(edges[-1])]


def build_contract(P: dict, base_payload: dict, guard: Callable[[], None]):
    """Compute immutable plot bounds once across every saved selection.

    Parent must call under the sole execution lock and its resource/budget guard.
    Native Float64 reconstruction evidence is inherited, not newly recomputed.
    Plane arrays are existing Float32 display phasors, not fresh native fields.
    """
    require(callable(guard),'The parent finite resource guard is required');guard()
    require(isinstance(P,dict)and isinstance(base_payload,dict)and
            P.get('schema')=='task1-native-field-shape-display-v1', 'Verified cached vector-display payload required')
    analysis=P.get('analysis');require(isinstance(analysis,dict)and analysis==base_payload.get('analysis'),
            'All stacked GUI layers must share exactly the same analysis')
    spatial=base_payload.get('spatial',{});require(isinstance(spatial,dict),'Actual spatial payload required')
    maxima,selections=_scale_maxima(analysis)
    planes=P.get('planes');require(isinstance(planes,list)and planes,'Actual saved native planes required')
    plane_ids=[];vector_evidence=[];evidence=[]
    upper=0.
    for plane in planes:
        guard();pid=plane.get('id');require(isinstance(pid,str)and pid not in plane_ids,'Unique named native planes required');plane_ids.append(pid)
        indices=np.asarray(plane.get('native_indices'))
        require(indices.ndim==1 and 0<len(indices)<=MAX_DISPLAY_VALUES and np.issubdtype(indices.dtype,np.integer)and
                np.all(indices>=-1),'Exact integer native cell indices and exterior=-1 required')
        inside=indices>=0;require(inside.any(),'An actual native cell must occur in every saved plane')
        for case in CASES:
            fields=plane.get('fields',{}).get(case,{})
            require(isinstance(fields,dict)and fields,'Actual coherent frequency fields required for '+case)
            triangle=np.zeros(len(indices),dtype=np.float64);descriptor_hashes={}
            for frequency,value in fields.items():
                guard();require(isinstance(frequency,str)and frequency.isdigit()and int(frequency)>0,'Positive explicit frequency required')
                packed,digest=_descriptor(value,len(indices))
                require(np.isfinite(packed[inside]).all(),'Every actual native complex component must be finite')
                # Binary NaN outside the phantom is allowed. Interior values are
                # bounded independently of carrier phase, direction and time.
                components=packed[inside].astype(np.float64)
                norm=np.sqrt(np.sum(components*components,axis=(1,2)))
                require(np.isfinite(norm).all(),'Finite complex vector norm required')
                triangle[inside]+=norm
                descriptor_hashes[frequency]=digest
            interior_indices=np.flatnonzero(inside)
            local=int(interior_indices[np.argmax(triangle[inside])]);raw_bound=float(triangle[local]);scaled=raw_bound*maxima[case]
            require(finite_number(scaled),'Finite scaled field bound required')
            row=dict(kind='phase_independent_complex_triangle_bound',case=case,plane_id=pid,
                     native_cell_index=int(indices[local]),raw_upper_V_m=raw_bound,
                     amplitude_scale=maxima[case],scaled_upper_V_m=scaled,
                     vector_descriptor_SHA256=descriptor_hashes)
            vector_evidence.append(row);upper=max(upper,scaled)
    # Existing RMS maps are Float16 displays. Include their rounded maxima as
    # well as authoritative Float64 volume statistics, without substituting one
    # precision class for the other.
    for case in CASES:
        guard();source=spatial.get(case,{});maps=source.get('RMS',{})
        require(isinstance(maps,dict)and isinstance(maps.get('xy'),list)and maps['xy'], 'All stored RMS slices required')
        for name,text in [(f'xy{i}',v)for i,v in enumerate(maps['xy'])]+[(axis,maps.get(axis))for axis in ('xz','yz')]:
            array,digest=_float16(text);raw_bound=float(np.nanmax(array));scaled=raw_bound*maxima[case]
            evidence.append(dict(kind='Float16_RMS_display_maximum',case=case,plane_id=name,raw_upper_V_m=raw_bound,
                                 amplitude_scale=maxima[case],scaled_upper_V_m=scaled,display_SHA256=digest))
            upper=max(upper,scaled)
        regions=spatial.get('regions',{}).get(case,{})
        require(isinstance(regions,dict)and isinstance(regions.get('total'),dict),'Authoritative whole-volume RMS statistics required')
        for region,stats in regions.items():
            raw_bound=stats.get('max');require(finite_number(raw_bound),'Finite Float64 regional RMS maximum required')
            scaled=raw_bound*maxima[case]
            evidence.append(dict(kind='saved_Float64_RMS_region_maximum',case=case,region=region,
                                 raw_upper_V_m=raw_bound,amplitude_scale=maxima[case],scaled_upper_V_m=scaled))
            upper=max(upper,scaled)
    e_limit=nice_upper(upper);require(e_limit>=upper,'Fixed E scale may not clip any declared bound')
    j_upper=0.;j_evidence=[]
    for case in CASES:
        guard();entry=spatial[case].get('contactJ');text=entry.get('values_b64')if isinstance(entry,dict)else entry
        values,digest=_float16(text);raw_bound=float(np.nanmax(values));scaled=raw_bound*maxima[case]
        j_upper=max(j_upper,scaled);j_evidence.append(dict(kind='Float16_contact_normal_J_RMS',case=case,
            raw_upper_A_m2=raw_bound,amplitude_scale=maxima[case],scaled_upper_A_m2=scaled,display_SHA256=digest))
    for name,mode in analysis['modes'].items():
        for case,match,burdens in [('TIS',None,mode.get('reference_burdens',{}))]+[
                ('C1',key,value.get('burdens',{}))for key,value in mode['matches'].items()]:
            for key in ('surface_J_RMS_max_A_m2','bulk_skin_J_vector_RMS_max_A_m2'):
                value=burdens.get(key);require(finite_number(value),'Saved finite current-density burden required')
                # These rows are ALREADY scaled in analysis; never scale twice.
                j_upper=max(j_upper,value);j_evidence.append(dict(kind='saved_scaled_J_RMS_maximum',case=case,
                    mode=name,match=match,metric=key,scaled_upper_A_m2=value))
    j_limit=nice_upper(j_upper);require(j_limit>=j_upper,'Fixed J scale may not clip any declared bound')
    grid=spatial.get('grid',{})
    coordinates=dict(x_mm=_axis(grid.get('x_edges_mm'),'x'),y_mm=_axis(grid.get('y_edges_mm'),'y'),
                     depth_z_mm=_axis(grid.get('z_faces_mm'),'depth z'))
    guard()
    return dict(schema='task1-fixed-scale-contract-v1',new_PDE=0,new_native_field_decode=0,
        immutable_after_build=True,automatic_rescaling=False,
        electric_field=dict(unit='V/m',lower_V_m=0.,upper_V_m=e_limit,
            signed_lower_V_m=-e_limit,signed_upper_V_m=e_limit,maximum_declared_upper_bound_V_m=upper,
            bound_kind='Maximum over every stored mode/match/case/plane; phase-independent complex triangle bound plus saved RMS display/volume maxima; rounded upwards to1/2/5 decade',
            members=['carrier_vector_RMS','total_vector_RMS','fixed_direction_two_tone_envelope_modulation',
                     'instantaneous_vector_magnitude','projected_instantaneous_waveform','analytic_envelope','RMS_and_AM_line_profiles'],
            scope='Instantaneous/envelope/directional bounds apply to the exported native slices; full-volume RMS maxima are separately included. No unsaved spatial field is claimed.',
            evidence=vector_evidence+evidence),
        current_density=dict(unit='A/m2',lower_A_m2=0.,upper_A_m2=j_limit,maximum_declared_upper_bound_A_m2=j_upper,
            members=['contact_normal_J_RMS','saved_skin_vector_J_RMS_maximum'],
            scope='RMS current density only; no bound on unsaved instantaneous current density is inferred',evidence=j_evidence),
        max_amplitude_by_case=maxima,selections=selections,plane_ids=plane_ids,
        coordinate_ranges_mm=coordinates,
        source=dict(reference_result_commit=P.get('reference_result_commit'),display_source_commit=P.get('display_source_commit'),
                    inherited_source_sha256=P.get('source_sha256',{}),
                    saved_regions_SHA256=hashlib.sha256(json.dumps(spatial['regions'],sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()),
        interpretation='Common numerical axes do not make RMS, modulation, instantaneous E or current density identical physical quantities. Labels, units and validation holds remain separate.',
        fixed_manual_zoom='No automatic or ROI-dependent zoom is defined. A future explicit manual zoom must preserve the locked full-range view and disclose clipping.')
