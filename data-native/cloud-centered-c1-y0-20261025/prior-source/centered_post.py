"""New genuine y=0 pair postprocessor; caller owns the sole finite run/guard.

Import performs no data reads or calculations. Frozen TIS/off-centre outputs
remain controls. New C1 fields and phi belong only to the new centred case.
"""
from __future__ import annotations
import base64
import copy
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import sys
import numpy as np

ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(SOURCE))
import task1_best1_pair_native as old
import centered_metrics as metrics
CASE_ID='centered-square15-C1-y0-xy80-f3000'
OLD_ID='baseline-square15-C1pair0-xy80'
OLD_HTML=Path('/dev/shm/task1-best1-pair-20261025/index.html')
MAX_BYTES=64*1024**2
PARENT_METRICS_SHA256='19b673746b313cf67bf1f5ea692389048ca865cffafedfb5e98b05f61f915d58'
require=old.require
LAYERS=('sc','dermis','fat','muscle')


def required_inputs():
    """Preparation reads only old JSON manifests and source/HTML byte hashes."""
    refs=old.required_inputs(ROOT)
    for p in (OLD_HTML,Path(__file__).resolve(),SOURCE/'centered_metrics.py',ROOT/'tools/task1_best1_pair_metrics.py',
              ROOT/'tis-java/selectivity_volume.py',ROOT/'tis-java/layered_probe_analysis.py'):
        refs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    return refs


def _complex_bytes(raw,shape):
    require(len(raw)==math.prod(shape)*16,'Exact little-endian complex128 dimensions; no trailing bytes')
    value=np.frombuffer(raw,dtype='<c16').reshape(shape)
    require(np.isfinite(value).all(),'Finite complex native basis required')
    return value


def _validate_centered_case(case):
    c=case['circuit']
    require(case['id']==CASE_ID and c['n_pads']==2 and c['n_outputs']==1 and c['n_return_nodes']==1 and
        c['pad_to_node']=={'0':'out0','1':'GND'} and c['source_peak_V']==.5 and c['source_resistance_ohm']==50,
        'New genuine one-output centred source/return pair required')
    pads=case['design']['pads'];require(len(pads)==2,'Exactly two physical square pads required')
    for i,x in enumerate((-10.,10.)):
        p=next(p for p in pads if p['pad']==i)
        expected=[[x-7.5,-7.5],[x+7.5,-7.5],[x+7.5,7.5],[x-7.5,7.5]]
        require(p['center_mm']==[x,0.] and p['width_mm']==p['height_mm']==15 and
            p.get('rotation_deg',0)==0 and np.array_equal(np.asarray(p['polygon_mm']),expected) and
            math.isclose(case['expected_pad_areas_m2'][i],225e-6,rel_tol=1e-12,abs_tol=1e-16),
            'Actual y=0 centred15mm squares/225mm2 including return required; old y=-10 is only a control')


def _unit_burdens(field,current,density,pads,area,loss,za,layers,total,gamma):
    """Native one-frequency peak complex phasors; loss is c†Lc, no extra half."""
    field=np.asarray(field,complex);density=np.asarray(density,complex);pads=np.asarray(pads)
    area=np.asarray(area,float);loss=np.asarray(loss,complex);layers=np.asarray(layers);total=np.asarray(total,float);gamma=np.asarray(gamma,complex)
    erms=old.pure_sine_rms(field)
    require(density.shape==pads.shape==area.shape and density.ndim==1 and set(pads)=={0,1} and
        np.isfinite(density).all() and np.isfinite(area).all() and np.all(area>0) and loss.shape==(6,) and
        np.isfinite(loss).all() and np.max(abs(loss.imag))<1e-12 and np.all(loss.real>=-1e-12) and
        layers.shape==total.shape==erms.shape and np.isfinite(total).all() and np.all(total>0) and
        np.equal(layers,np.rint(layers)).all() and np.all((layers>=0)&(layers<=3)) and gamma.shape==(4,) and
        np.isfinite(gamma).all() and math.isfinite(current.real+current.imag),'Finite native one-output field/current/contact/loss ABI required')
    current_scale=max(abs(current),1e-30);supplied=.25*(1j*current).real
    require(supplied>0 and abs(np.sum(density*area))/max(float(np.sum(abs(density)*area)),1e-30)<=2e-6 and
        abs(np.sum(density[pads==0]*area[pads==0])-current)<=2e-6*current_scale and
        abs(np.sum(density[pads==1]*area[pads==1])+current)<=2e-6*current_scale and
        abs(loss.real.sum()-supplied)<=2e-7*abs(supplied),'Actual C1 full-pad KCL/source/loss conservation failed')
    jrms=abs(density)/math.sqrt(2);skin=layers<=1;jskin=abs(gamma[layers.astype(int)])*erms
    def p95(v,w):
        order=np.argsort(v,kind='stable');j=min(int(np.searchsorted(np.cumsum(w[order]),.95*w.sum(),side='left')),len(v)-1)
        return float(v[order[j]])
    require(np.any(skin),'Actual SC+dermis cells required')
    return dict(source_current_RMS_mA=float(abs(current)/math.sqrt(2)*1000),source_current_peak_mA=float(abs(current)*1000),
        contact_J_RMS_max_A_m2=float(jrms.max()),contact_J_RMS_p95_A_m2=p95(jrms,area),
        contact_voltage_RMS_max_V=float((abs(density*za)/math.sqrt(2)).max()),
        bulk_skin_J_RMS_max_A_m2=float(jskin[skin].max()),bulk_skin_J_RMS_p95_A_m2=p95(jskin[skin],total[skin]),
        SC_power_W=float(loss[0].real),dermis_power_W=float(loss[1].real),skin_SC_plus_dermis_power_W=float(loss[0].real+loss[1].real),
        fat_power_W=float(loss[2].real),muscle_power_W=float(loss[3].real),contact_power_W=float(loss[4].real),
        tissue_contact_power_W=float(loss[:5].real.sum()),source_resistor_power_W=float(loss[5].real),source_power_W=float(supplied),
        loaded_metal_Vpp=float(2*abs(-.5j-50*current)))


def _properties(raw):
    return {k.strip():v.strip()for line in raw.decode().splitlines()if line.strip()and not line.lstrip().startswith('#')for k,v in[line.split('=',1)]}


def _hotspot(values,weights,grid):
    use=np.flatnonzero(weights>0);index=int(use[np.argmax(values[use])]);layer=int(grid[index,3])
    return dict(value_V_m=float(values[index]),native_cell_index=index,center_xyz_mm=grid[index,:3].tolist(),layer_index=layer,layer=LAYERS[layer],
        scope='Native cell centre with positive region overlap; a layer-boundary maximum is not deep focus')


def postprocess(runpath,case,guard):
    """Read new centred basis only when the root calls under its shared guard."""
    _validate_centered_case(case);runpath=Path(runpath).resolve();folder=runpath/'bases'/CASE_ID
    used={};pinned=case.get('input_sha256',{})
    def read(path,expected=None):
        guard();p=Path(path).resolve();require(p.is_file()and not p.is_symlink()and p.stat().st_size<=MAX_BYTES and
            (p.is_relative_to(ROOT)or p.is_relative_to(runpath)or p==OLD_HTML or p.is_relative_to(SOURCE)), 'Bounded declared native/source input required')
        raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest();expected=expected or pinned.get(str(p))
        require(expected is None or h==expected,'Input SHA changed: '+str(p));used[str(p)]=h;guard();return raw
    def js(path,expected=None):return json.loads(read(path,expected))
    def path(name):
        found=[p for p in(folder/name,folder/(name+'.gz'))if p.is_file()];require(len(found)==1,'Exactly one new native file required: '+name);return found[0]
    def decoded(p,limit):
        raw=read(p)
        if Path(p).suffix=='.gz':
            with gzip.GzipFile(fileobj=io.BytesIO(raw))as stream:raw=stream.read(limit+1)
        require(len(raw)<=limit,'Decoded native input exceeds exact bound');return raw
    def binary(name,shape):return _complex_bytes(decoded(path(name),math.prod(shape)*16),shape)
    def grid(p):return np.loadtxt(io.BytesIO(decoded(p,MAX_BYTES)),delimiter=',',skiprows=1)
    meta=js(path('mesh-metadata.json'));validation=js(path('validation.json'));read(path('BASIS_COMPLETE'))
    require(meta['channels']==validation['channels']==1 and meta['frequencies_Hz']==[3000] and meta['cells']==351680 and
        meta['h_xy_mm']==.625 and meta['sc_cells']==2 and meta['bulk_layer_counts']==[14,14,40] and
        meta['source_peak_V']==.5 and meta['source_resistance_ohm']==50 and meta['phasor_convention']=='peak,+jomega_t' and
        meta.get('exporter_kind')=='centered_pair_native' and meta.get('exporter_class')=='CenteredPairBasis' and
        meta.get('numerical_base_class')=='SelectivityShapeBasis' and meta.get('radius_mm')==25 and meta.get('total_depth_mm')==25.1 and
        meta.get('field_reconstruction')=='half_face_flux; top contact term averaged over full cell face h^2', 'Transparent unchanged-FVM single-frequency centred native ABI required')
    for key,limit in old.contact.NATIVE_GATES.items():require(0<=validation[key]<=limit,'Original native gate failed: '+key)
    config_raw=read(case['config_file'],case['config_sha256']);config=_properties(config_raw)
    require(meta['config_sha256']==case['config_sha256'],'New exporter/config identity differs')
    top5=js(ROOT/old.TOP5_PLAN);row=next(r for r in top5['catalog']['selected_layouts']if r['condition_id']==old.F35_ID)
    reference=js(row['condition_source']['path'],row['condition_source']['SHA256'])
    tconfig=_properties(read(row['native_config']['path'],row['native_config']['SHA256']))
    require(all(tconfig.get(k)==v for k,v in config.items()if k.startswith('z.')or k.endswith(('.sigma','.epsilon_r'))), 'Unchanged nominal PBS specific-Z/tissue properties required')
    html=read(OLD_HTML).decode();match=re.search(r'<script\s+id=["\']packed["\'][^>]*>([^<]+)</script>',html)
    require(match is not None,'Source-bound original GUI packed payload required')
    packed=base64.b64decode(match.group(1).strip(),validate=True)
    with gzip.GzipFile(fileobj=io.BytesIO(packed))as stream:payload_raw=stream.read(16*1024**2+1)
    require(len(payload_raw)<=16*1024**2,'Bounded old packed payload required');control=json.loads(payload_raw)
    oldanalysis,oldspatial=control['analysis'],control['spatial']
    require(oldanalysis['reference']['candidate_id']==old.F35_ID and oldanalysis['single_pair']['case_id']==OLD_ID,
        'Original f35/y=-10 GUI control identity required')
    cg=grid(path('grid.csv'));tg=grid(row['grid']['path'])
    require(cg.shape==(351680,5)and np.array_equal(cg,tg),'New C1 and immutable f35 grid/order must be exactly identical')
    require(hashlib.sha256(Path(row['grid']['path']).read_bytes()).hexdigest()==row['grid']['SHA256'],'Existing TIS grid SHA changed')
    axes=old.display.axes_and_indices(cg,meta)
    with np.load(io.BytesIO(read(row['scalar_archive']['path'],row['scalar_archive']['SHA256'])),allow_pickle=False)as archive:
        ta={k:np.array(archive[k],copy=True)for k in('RMS','region_target_m3','region_surface_0_5_m3','region_total_m3')}
    require(all(v.shape==(351680,)and v.dtype==np.dtype('<f8')and np.isfinite(v).all()and np.all(v>=0)for v in ta.values()),'Actual Float64 TIS scalar and fractional masks required')
    # Independently regenerate the same native fractional weights from new metadata.
    def module(name):
        p=ROOT/'tis-java'/(name+'.py');read(p);spec=importlib.util.spec_from_file_location('centered_'+name,p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
    structured=np.empty(len(cg),dtype=[(k,'<f8')for k in('x_mm','y_mm','z_mm','layer','volume_m3')])
    for i,k in enumerate(structured.dtype.names):structured[k]=cg[:,i]
    scalar=module('selectivity_volume');vm=dict(h_xy_mm=.625,radius_mm=25,z_faces_mm=meta['z_faces_mm'],layer_counts=[2,14,14,40],geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001)
    regenerated,weightproof=scalar.native_region_weights(structured,vm)
    for name,original in(('target','region_target_m3'),('surface_0_5','region_surface_0_5_m3'),('total','region_total_m3')):
        require(np.array_equal(regenerated[name],ta[original]),'New native fractional weights differ from exact cached TIS: '+name)
    target,surface,total=(ta[k]for k in('region_target_m3','region_surface_0_5_m3','region_total_m3'))
    require(np.all(total>0)and np.all(target<=total)and np.all(surface<=total),'Valid positive native region volumes required')
    weights=dict(zip(old.REGIONS,(target,surface,total-target,total)))
    native_field=binary('field-3000.bin',(1,len(cg),3));field=-1j*native_field[0];crms=old.pure_sine_rms(field);trms=ta['RMS']
    centre=float(old.pure_sine_rms(old._sample_complex(field,cg)[None,:])[0])
    cstats={r:dict(old.weighted_stats(crms,w),hotspot=_hotspot(crms,w,cg))for r,w in weights.items()}
    for r,w in weights.items():
        ts=old.weighted_stats(trms,w)
        for key in('mean','p10','p95','max','std','volume_m3'):
            require(math.isclose(ts[key],oldspatial['regions']['TIS'][r][key],rel_tol=1e-10,abs_tol=1e-25 if key=='volume_m3' else 1e-12),'Immutable TIS statistics changed')
    contacts=np.genfromtxt(io.BytesIO(read(path('contacts-3000.csv'))),delimiter=',',names=True)
    pads,x,y,area=(contacts[k].astype(int if k=='pad'else float)for k in('pad','x_mm','y_mm','area_m2'))
    density=-1j*binary('density-3000.bin',(1,len(area)))[0];transfer=binary('source-3000.bin',(1,1))[0,0];current=-1j*transfer
    loss=binary('loss-3000.bin',(6,1,1))[:,0,0];za=complex(float(config['z.3000.re']),float(config['z.3000.im']))
    gamma=np.asarray([complex(float(config[k+'.sigma']),2*math.pi*3000*old.EPS0*float(config[k+'.epsilon_r']))for k in LAYERS])
    burdens=_unit_burdens(field,current,density,pads,area,loss,za,cg[:,3],total,gamma)
    maskrows=csv.DictReader(io.StringIO(read(case['mask_file'],case['mask_sha256']).decode()))
    mask={(int(r['pad']),int(r['i']),int(r['j'])):float(r['area_m2'])for r in maskrows}
    actual={(int(p),round((xx+25)/.625-.5),round((yy+25)/.625-.5)):float(a)for p,xx,yy,a in zip(pads,x,y,area)}
    require(len(actual)==len(area)and actual.keys()==mask.keys()and all(math.isclose(a,mask[k],rel_tol=1e-12,abs_tol=1e-24)for k,a in actual.items()),'New native contacts do not match centred physical mask')
    cdisplay,jprecision=old._contact_display(pads,x,y,area,abs(density)/math.sqrt(2),case,axes)
    require(all(math.isclose(p['x_mm'],xx,abs_tol=1e-10)and abs(p['y_mm'])<=1e-10 for p,xx in zip(cdisplay['pad_centres'],(-10.,10.))), 'Actual contact centroids are not centred y=0')
    cdisplay['RMS'],rprecision=old._planes(crms,axes)
    potential=binary('potential-3000.bin',(1,len(cg)));probe_module=module('layered_probe_analysis')
    geometry=dict(coordinate_system=dict(unit='mm',surface_z_mm=0.,depth_axis='+z'),radius_mm=25.,layers=[dict(l)for l in probe_module.DEFAULT_LAYERS],z_faces_mm=meta['z_faces_mm'],field_reconstruction=probe_module.FIELD_RECONSTRUCTION,
        basis_normalization=dict(source_peak_V=.5,source_Vpp=1.,source_resistance_ohm=50.,phasor_exponent='+jomega_t'),gamma_S_m={3000:{i:v for i,v in enumerate(gamma)}})
    digest=lambda obj:hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    probe=probe_module.evaluate_layered_probe(structured,{3000:potential},{3000:native_field},geometry,{3000:np.array([-1j])},
        provenance=dict(source_run_id=runpath.name,source_condition_id=CASE_ID+'-3000Hz-sine',source_candidate_id=CASE_ID,input_sha256=digest(used),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),result_sha256=digest(validation)),fundamental_frequencies_Hz=[3000],tip_gap_mm=5.,plus_pitch_mm=5.,depths_mm=(5.,10.,15.,20.))
    require(probe['status']=='complete'and probe['numerical_checks']['all_passed']and len(probe['measurements'])==40,'New nativephi/E forty-probe validation failed')
    for p in probe['measurements']:p.pop('time_plot',None)
    unit=dict(case_id=CASE_ID,source_run_id=runpath.name,circuit=copy.deepcopy(case['circuit']),physical_pad_centres_mm=[[-10,0],[10,0]],waveform='pure sine',frequency_Hz=3000,raw_source_Vpp=1.,raw_centre20_E_RMS_V_m=centre,raw_ROI_energy_RMS_V_m=cstats[old.REGIONS[0]]['energy_RMS_V_m'],raw_burdens=burdens,
        represented_pad_contact_areas_m2=[float(area[pads==p].sum())for p in(0,1)],unloaded_probe_reference=dict(status='computed_from_new_native_phi',in_memory_result='postprocess.probe40',case_id=CASE_ID,probe_count=40,tip_gap_mm=5.,instrument_loading_validated=False))
    metal=-.5j-50*current
    electrical=dict(source_current_spectrum=[dict(frequency_Hz=3000,real_A=[float(current.real)],imaginary_A=[float(current.imag)])],loaded_metal_voltage_spectrum=[dict(frequency_Hz=3000,real_V=[float(metal.real)],imaginary_V=[float(metal.imag)])],source_power_W=burdens['source_power_W'],source_resistor_power_W=burdens['source_resistor_power_W'],source_current_RMS_by_output_mA=[burdens['source_current_RMS_mA']])
    publication=js(runpath/'source-publication.json')
    require(publication.get('status')=='published_readback_verified'and isinstance(publication.get('commit'),str)and
        re.fullmatch('[0-9a-f]{40}',publication['commit']) is not None,'Actual new source publication/readback receipt required')
    unit['source_commit']=publication['commit']
    analysis=metrics.build_comparison(reference,unit,electrical,probe)
    analysis.update(new_PDE=1,new_native_RHS=1)
    analysis['single_pair']['source_commit']=publication['commit']
    analysis['geometry_comparison'].update(C1_centres_mm=[[-10,0],[10,0]],old_offcenter_control_centres_mm=[[-10,-10],[10,-10]])
    shape={name:{criterion:old.scalar_shape_comparison(trms,crms,target,mode['reference_amplitude_scale'],matched['amplitude_scale'])for criterion,matched in mode['matches'].items()}for name,mode in analysis['modes'].items()}
    cglobal=_hotspot(crms,total,cg);tglobal=copy.deepcopy(reference['normalizations']['raw_1Vpp']['regions']['total']['RMS']['hotspot']);tglobal['value_V_m']=float(trms.max())
    j=abs(density)/math.sqrt(2);ji=int(np.argmax(j));skin=np.flatnonzero(cg[:,3]<=1);jbulk=abs(gamma[cg[:,3].astype(int)])*crms;bi=int(skin[np.argmax(jbulk[skin])])
    spatial=dict(grid=copy.deepcopy(oldspatial['grid']),TIS=copy.deepcopy(oldspatial['TIS']),C1=cdisplay,regions=dict(TIS=copy.deepcopy(oldspatial['regions']['TIS']),C1=cstats),shape_comparison=shape,
        proofs=dict(exact_grid_and_fractional_masks=True,native_weight_regeneration=weightproof,TIS_maps_reused_byte_unchanged=True,C1_NPZ_RMS_used=False,C1_only_active_frequency_Hz=3000,C1_raw_burdens=burdens,new_PDE=1,new_native_RHS=1,
            raw_RMS_global_max=dict(C1=cglobal,TIS=tglobal),contact_Jmax=dict(C1=dict(value_A_m2=float(j[ji]),center_xyz_mm=[float(x[ji]),float(y[ji]),0.],pad=int(pads[ji]))),
            bulk_skin_Jmax=dict(C1=dict(value_A_m2=float(jbulk[bi]),center_xyz_mm=cg[bi,:3].tolist(),layer_index=int(cg[bi,3]),layer=LAYERS[int(cg[bi,3])],native_cell_index=bi)),
            display_precision=dict(C1_RMS=rprecision,C1_contact=jprecision),same_rounded_two_pad_case_available=False,
            coordinate_system='x,y horizontal mm; z=0 top and +z depth; C1centres(-10,0),(10,0); originaly=-10 pair is a separate control',held='High SC/interface maxima are not deep focus; no waveform/vector/activation/safety equivalence or instrument loading validation'))
    oldunit=oldanalysis['single_pair'];oldcache=js(ROOT/old.C1_CACHE)['single_stimulation']
    require(oldcache['case_id']==OLD_ID and oldcache['raw_source_Vpp']==1. and oldcache['frequency_Hz']==3000,'Genuine old off-centred unit must remain a separate source-bound control')
    off=dict(schema='task1-centered-versus-offcenter-control-v1',old_case_id=OLD_ID,new_case_id=CASE_ID,old_centres_mm=[[-10,-10],[10,-10]],new_centres_mm=[[-10,0],[10,0]],reference_candidate_id=old.F35_ID,
        raw_unit=dict(old=dict(centre20_E_RMS_V_m=oldunit['unit_centre20_E_RMS_V_m'],ROI_energy_RMS_V_m=oldunit['unit_ROI_energy_RMS_V_m'],burdens=copy.deepcopy(oldcache['raw_burdens'])),new=dict(centre20_E_RMS_V_m=centre,ROI_energy_RMS_V_m=unit['raw_ROI_energy_RMS_V_m'],burdens=burdens)),modes={},regions=dict(old=copy.deepcopy(oldspatial['regions']['C1']),new=cstats),holds=['Only C1 pair yposition changes; f35 reference/weights/source amplitudes remain unchanged','Old full C1 scalar was not decoded; new-versus-old whole-volume L2 is not inferred from display planes'])
    for name,mode in analysis['modes'].items():
        off['modes'][name]={}
        for criterion,new in mode['matches'].items():
            before=oldanalysis['modes'][name]['matches'][criterion]
            compact=lambda m,sh:dict(required_source_Vpp=m['required_source_Vpp'],source_current_RMS_mA=m['source_current_RMS_mA'],burdens=copy.deepcopy(m['burdens']),shape_comparison=copy.deepcopy(sh))
            changes=lambda a,b:None if b==0 else a/b-1
            off['modes'][name][criterion]=dict(old=compact(before,oldspatial['shape_comparison'][name][criterion]),new=compact(new,shape[name][criterion]),relative_change=dict(required_source_Vpp=changes(new['required_source_Vpp'],before['required_source_Vpp']),source_current_RMS_mA=changes(new['source_current_RMS_mA'],before['source_current_RMS_mA']),burdens={k:changes(new['burdens'][k],before['burdens'][k])for k in new['burdens']}))
    # Source derivation is exactly one case-ID literal substitution, physics unchanged.
    original=read(ROOT/'tools/task1_best1_pair_metrics.py');derived=read(SOURCE/'centered_metrics.py')
    require(hashlib.sha256(original).hexdigest()==PARENT_METRICS_SHA256 and original.count(OLD_ID.encode())==1 and derived==original.replace(OLD_ID.encode(),CASE_ID.encode()), 'Centred metrics may only change the genuine C1 case-ID literal of the exact frozen parent')
    sourceproof=dict(parent_metrics_SHA256=hashlib.sha256(original).hexdigest(),derived_metrics_SHA256=hashlib.sha256(derived).hexdigest(),only_change='C1 case ID literal',new_case_id=CASE_ID)
    for name,h in list(used.items()):guard();require(hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,'Consumed input changed during centredpost: '+name)
    proofs=dict(input_sha256=used,inputs_unchanged=True,native_five_gates=validation,original_gate_limits=old.contact.NATIVE_GATES,source_derivation=sourceproof,
        source_commit=publication['commit'],TIS_display_unchanged=spatial['TIS']==oldspatial['TIS'],new_PDE=1,new_native_RHS=1,probe40_computed_from_new_phi=True,instrument_loading_validated=False)
    spatial['proofs'].update(input_sha256=copy.deepcopy(used),inputs_unchanged=True,source_derivation=sourceproof)
    guard();return dict(analysis=analysis,spatial=spatial,unit=unit,offcenter_comparison=off,proofs=proofs,probe40=probe,single_electrical_metrics=electrical)
