"""Guard-called native postprocessing for a four-layer assumption sensitivity.

Import does not read files or evaluate a field. The sole parent owns source/input
pins, execution locks, elapsed budget, memory/storage limits and all output. No
solver, plotting, installation, publication, cleanup or file write occurs here.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np

ROOT=Path('/workspace/ngg-tis-task1')
RUN_ID='cloud-mesh-c1-20261019T190000Z'
OLD_CASE='baseline-square15-xy80'
CASE='baseline-square15-sc-eps1100-xy80'
FREQUENCIES=(3000,3030,9000,9090)
FUNDAMENTALS=(3000,3030)
LAYERS=('sc','dermis','fat','muscle')
EPS0=8.8541878128e-12
NATIVE_GATES=dict(max_residual=2e-7,max_power_error=2e-7,max_current_error=2e-6,
    max_area_relative_error=1e-10,max_interface_normal_current_relative_error=2e-7)
DERIVED_J_RTOL=1e-10
DERIVED_J_ATOL=1e-10
PHI_E_RTOL=2e-8
PHI_E_ATOL=1e-8
MAX_FILE_BYTES=64*1024**2
MAX_RAW_BYTES=128*1024**2
MAX_DIRECTION_CHUNK=256


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def _metadata():
    path=ROOT/'data-native'/RUN_ID/'postprocess'/OLD_CASE/'summary.json'
    raw=path.read_bytes();require(len(raw)<4*1024**2,'Bounded original postprocess metadata')
    post=json.loads(raw)
    require(post['status']=='complete'and post['id']==OLD_CASE,'Completed canonical comparator required')
    for key,limit in NATIVE_GATES.items():require(0<=post['validation'][key]<=limit,'Canonical comparator native gate: '+key)
    square=next(c for c in post['conditions']if c['waveform']=='square_3h')
    require(square['actual_fundamental_Hz']==[3000,3030]and square['source_Vpp_per_output']==1 and square['phase_deg']==[0.,0.]and square['carrier_group']==[0,1],
        'Original high-Z1Vpp square3h phases/frequencies required')
    pins={str(path):sha(raw)}
    # These are source declarations; the caller hashes them before executing.
    for p,h in post['input_sha256'].items():
        if '/bases/'+OLD_CASE+'/'in p or p.endswith('/configs/'+OLD_CASE+'.properties'):pins[p]=h
    weights=path.parent/square['native_volume_archive']
    pins[str(weights)]=post['artifacts']['files'][square['native_volume_archive']]['SHA256']
    for name in('selectivity_postprocess.py','selectivity_volume.py','explore_tis.py','SelectivityShapeBasis.java','TisSweep.java'):
        p=ROOT/'tis-java'/name;pins[str(p)]=sha(p.read_bytes())
    return dict(post=post,square=square,summary_path=path,archive_path=weights),pins


def required_inputs():
    """Small metadata/source reads only; no native arrays or NPZ decode."""
    return _metadata()[1]


def coefficients():
    """Frozen square3h convention:0.5Vpeak basis and1Vpp total waveform."""
    a1=3/(2*math.sqrt(2));a3=1/(2*math.sqrt(2))
    return {3000:np.asarray([-1j*a1,0j]),3030:np.asarray([0j,-1j*a1]),
        9000:np.asarray([-1j*a3,0j]),9090:np.asarray([0j,-1j*a3])}


def _properties(raw):
    return {k.strip():v.strip()for line in raw.decode().splitlines()if line.strip()and not line.lstrip().startswith(('#','!'))and '='in line for k,v in[line.split('=',1)]}


def _gamma(config,f):
    return np.asarray([complex(float(config[n+'.sigma']),2*math.pi*f*EPS0*float(config[n+'.epsilon_r']))for n in LAYERS],np.complex128)


def weighted_statistics(values,weights,grid):
    """Inverse weighted ECDF; ties preserve original native cell index order."""
    values=np.asarray(values,float);weights=np.asarray(weights,float)
    require(values.shape==weights.shape==(len(grid),)and np.isfinite(values).all()and np.isfinite(weights).all()and np.all(weights>=0),
        'Finite same-grid scalar/volume weights required')
    cells=np.flatnonzero(weights>0);require(len(cells)>0,'Positive represented volume required')
    v=values[cells];w=weights[cells];order=np.argsort(v,kind='stable');sorted_cells=cells[order]
    cumulative=np.cumsum(w[order]);volume=float(cumulative[-1]);mean=float(v@w/volume)
    def location(index):
        return dict(native_cell_index=int(index),center_xyz_mm=grid[index,:3].tolist(),layer_index=int(grid[index,3]),layer=LAYERS[int(grid[index,3])])
    def quantile(q):
        j=min(int(np.searchsorted(cumulative,q*volume,side='left')),len(order)-1);index=int(sorted_cells[j])
        return dict(value=float(values[index]),cumulative_volume_m3=float(cumulative[j]),representative=location(index),
            representative_scope='First stable ascending weighted ECDF crossing; a quantile has no unique spatial coordinate')
    lo=float(v.min());hi=float(v.max());imin=int(cells[np.flatnonzero(v==lo)[0]]);imax=int(cells[np.flatnonzero(v==hi)[0]])
    return dict(min=lo,p10=quantile(.1)['value'],median=quantile(.5)['value'],p90=quantile(.9)['value'],p95=quantile(.95)['value'],
        max=hi,mean=mean,std=float(np.sqrt(((v-mean)**2)@w/volume)),energy_RMS=float(np.sqrt((v*v)@w/volume)),
        volume_m3=volume,cells=int(len(cells)),NaN_count=0,Inf_count=0,
        minimum_location=dict(**location(imin),tied_cell_count=int(np.count_nonzero(v==lo))),
        maximum_location=dict(**location(imax),tied_cell_count=int(np.count_nonzero(v==hi))),
        quantiles={name:quantile(q)for name,q in(('P10',.1),('median',.5),('P90',.9),('P95',.95))},
        weighted_quantile_definition='Stable ascending inverse weighted ECDF; first cumulative native volume reaching q*sum(volume); no spatial interpolation',
        extrema_scope='Cell-constant native-centre values at cells with positive represented volume; not a continuum maximum')


def _directions():
    # Exact same ordering as frozen explore_tis.directions(2048); source-pinned.
    out=[np.asarray(v,float)/np.linalg.norm(v)for v in itertools.product((-1,0,1),repeat=3)if any(v)]
    for i in range(2048):
        z=1-2*(i+.5)/2048;p=i*np.pi*(3-np.sqrt(5));r=np.sqrt(1-z*z);out.append([r*np.cos(p),r*np.sin(p),z])
    return np.asarray(out)


def _maximum_direction(a,b,guard,deadline):
    dirs=_directions();require(dirs.shape==(2074,3),'Exact frozen2074 direction order')
    result=np.zeros(len(a),float);winner=np.zeros(len(a),np.int32)
    for start in range(0,len(a),MAX_DIRECTION_CHUNK):
        guard()
        if deadline is not None and time.monotonic()>deadline-15:
            return None,None,dict(status='not_run_to_completion_budget',completed_cells=start,total_cells=len(a),scope='Partial angular results discarded; no maxTIS statistics reported')
        stop=min(start+MAX_DIRECTION_CHUNK,len(a));pa=np.abs(a[start:stop]@dirs.T);pb=np.abs(b[start:stop]@dirs.T)
        np.minimum(pa,pb,out=pa);ids=np.argmax(pa,axis=1);winner[start:stop]=ids;result[start:stop]=2*pa[np.arange(stop-start),ids]
    bound=2*np.minimum(np.linalg.norm(a,axis=1),np.linalg.norm(b,axis=1))
    require(np.all(result<=bound+1e-10*np.maximum(1,bound)),'Sampled direction maximum exceeds analytic upper bound')
    return result,winner,dict(status='complete',directions=2074,fibonacci_count=2048,chunk_cells=MAX_DIRECTION_CHUNK,
        metric='max sampled real unit n of2min(abs(n dot E3000),abs(n dot E3030))',scope='Finite sampled lower bound on continuous directional maximum; fundamental tones only')


def _geometry(grid,meta):
    n=len(grid);x,y,z=(np.unique(grid[:,k])for k in range(3));faces=np.asarray(meta['z_faces_mm'],float)
    require((len(x),len(y),len(z),n)==(80,80,70,351680)and len(faces)==71 and np.all(np.diff(faces)>0),
        'Exact canonical native lattice required')
    ix,iy,iz=(np.searchsorted(axis,grid[:,k])for k,axis in enumerate((x,y,z)))
    lookup=np.full((70,80,80),-1,np.int32);require(len(np.unique((iz*80+iy)*80+ix))==n,'Unique native positions')
    lookup[iz,iy,ix]=np.arange(n);require(np.array_equal(np.rint(grid[:,3]).astype(int),np.repeat(np.arange(4),[2,14,14,40])[iz]),'Layer IDs match fixed physical depth')
    require(np.allclose(z,(faces[:-1]+faces[1:])/2,rtol=0,atol=1e-9),'Native centre/face depths match')
    return dict(x=x,y=y,z=z,faces=faces,ix=ix,iy=iy,iz=iz,lookup=lookup,h=.000625,dz=np.diff(faces)*1e-3)


def reconstruct_native_field(phi,grid,geometry,gamma,contacts,metal,za):
    """Exact native half-face-flux ABI reconstruction; not independent accuracy."""
    lookup=geometry['lookup'];h=geometry['h'];iz=geometry['iz'];dz=geometry['dz'];layer=grid[:,3].astype(int)
    field=np.zeros((len(grid),3),np.complex128)
    for axis in range(3):
        if axis==0:aa,bb=lookup[:,:,:-1],lookup[:,:,1:]
        elif axis==1:aa,bb=lookup[:,:-1,:],lookup[:,1:,:]
        else:aa,bb=lookup[:-1,:,:],lookup[1:,:,:]
        good=(aa>=0)&(bb>=0);a=aa[good];b=bb[good]
        distance_a=(np.full(len(a),h)if axis<2 else dz[iz[a]])/2
        distance_b=(np.full(len(b),h)if axis<2 else dz[iz[b]])/2
        area=h*dz[iz[a]]if axis<2 else np.full(len(a),h*h)
        current=area/(distance_a/gamma[layer[a]]+distance_b/gamma[layer[b]])*(phi[a]-phi[b])
        field[a,axis]+=.5*current/(gamma[layer[a]]*area);field[b,axis]+=.5*current/(gamma[layer[b]]*area)
    for row in contacts:
        p=int(row['pad']);i=int(round((float(row['x_mm'])+25)/.625-.5));j=int(round((float(row['y_mm'])+25)/.625-.5));cell=int(lookup[0,j,i])
        require(cell>=0,'Actual top contact cell');voltage=metal[p]if p<2 else 0j
        current=float(row['area_m2'])/(za+dz[0]/(2*gamma[0]))*(phi[cell]-voltage)
        field[cell,2]-=.5*current/(gamma[0]*h*h)
    return field


def _comparison(actual,expected,rtol,atol,label):
    error=np.abs(actual-expected);limit=atol+rtol*np.abs(expected);passed=bool(np.all(error<=limit))
    require(passed,label+' computational consistency failed')
    return dict(status='passed',maximum_absolute_error=float(error.max(initial=0)),relative_tolerance=rtol,absolute_tolerance=atol,
        scope='Algebra/ABI consistency only; not independent discretization or physical material accuracy')


def actual_waveform_checks(spectra,grid,guard):
    """Actual native point-waveform normalization audit; no activation inference."""
    requests=[(0,0,z)for z in(5,10,15,20)]+[(x,y,17.5)for x,y in((-5,0),(5,0),(0,-5),(0,5))]
    indices=[]
    for xyz in requests:
        distance=np.sum((grid[:,:3]-np.asarray(xyz))**2,axis=1);indices.append(int(np.argmin(distance)))
    times=np.arange(8192,dtype=float)/8192*.1
    wave=np.zeros((len(times),len(indices),3));sampled={};energy=np.zeros((len(indices),3))
    for frequency,field in spectra.items():
        guard();value=field[indices];phase=np.exp(2j*math.pi*frequency*times)
        wave+=np.real(phase[:,None,None]*value[None,:,:]);energy+=abs(value)**2/2
        sampled[str(frequency)]=dict(real=value.real.tolist(),imaginary=value.imag.tolist())
    temporal=np.sqrt(np.mean(wave*wave,axis=0));analytic=np.sqrt(energy)
    rms_proof=_comparison(temporal,analytic,1e-10,1e-10,'Actual full four-frequency point waveform RMS')
    amplitude=[]
    for cell in indices:
        a,b=spectra[3000][cell],spectra[3030][cell]
        rows=[]
        for axis in range(3):
            aa,bb=a[axis],b[axis];aligned=(np.angle(aa)-np.angle(bb))%(2*math.pi)if abs(aa)and abs(bb)else 0.
            values=np.abs(aa+bb*np.exp(1j*np.asarray([aligned,aligned+math.pi])))
            actual=float(values.max()-values.min());expected=float(2*min(abs(aa),abs(bb)))
            require(abs(actual-expected)<=1e-10+1e-10*expected,'Actual complex scalar envelope max-min check')
            rows.append(dict(axis='xyz'[axis],analytic_modulation_V_m=expected,
                aligned_opposed_complex_envelope_range_V_m=actual,absolute_error_V_m=abs(actual-expected),status='passed'))
        amplitude.append(dict(native_cell_index=cell,center_xyz_mm=grid[cell,:3].tolist(),fundamental_fixed_direction_checks=rows))
    return dict(status='passed',scope='Actual new native point waveforms; separate from material/mesh validation',
        samples=8192,window_seconds=.1,time_endpoint_included=False,frequencies_Hz=list(FREQUENCIES),
        selection='Nearest actual native cell to requested centre depth5/10/15/20 and horizontalcross17.5mm; no field interpolation',
        requested_xyz_mm=[list(x)for x in requests],actual_xyz_mm=grid[indices,:3].tolist(),native_cell_indices=indices,
        complex_peak_spectra_V_m=sampled,full_four_frequency_RMS_check=rms_proof,
        fundamental_complex_envelope_checks=amplitude,
        harmonic_envelope_modulation='not_run; two-tone formula not applied to full four-frequency waveform',
        not_probe_voltage='These are local field samples, not5mm differential probe potential differences')


def build(run,guard,*,declared_sha256=None,deadline_monotonic=None,include_max_direction=True):
    """Read actual complete new native basis only when the sole parent calls.

    Return {summary: JSON-compatible dict, arrays: new derived Float64 arrays}.
    Parent decides how to persist arrays; no raw field duplication or writes here.
    """
    require(callable(guard),'Explicit parent resource guard');guard();run=Path(run).resolve();folder=run/'bases'/CASE
    require(run.name=='task1-all-layer-sensitivity-20261025-run'and folder.is_dir(),'Exact unique completed sensitivity run')
    old,old_pins=_metadata();used={};new_pins=dict(declared_sha256 or{})
    require(all(p not in new_pins or new_pins[p]==h for p,h in old_pins.items()),'Caller-pinned comparator/source metadata changed')
    def read(path):
        guard();p=Path(path);require(p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<=MAX_FILE_BYTES and
            (p.is_relative_to(folder)or p.is_relative_to(run/'configs')or str(p)in old_pins),'Declared bounded native/source file')
        raw=p.read_bytes();digest=sha(raw);expected=old_pins.get(str(p),new_pins.get(str(p)))
        require(expected is None or digest==expected,'Pinned input bytes changed: '+str(p));used[str(p)]=digest;return raw
    def js(path):return json.loads(read(path))
    def path(folder,name):
        values=[p for p in(folder/name,folder/(name+'.gz'))if p.is_file()];require(len(values)==1,'One actual native file required: '+name);return values[0]
    def decoded(path_,expected=None):
        raw=read(path_);limit=MAX_RAW_BYTES if expected is None else expected
        if Path(path_).suffix=='.gz':
            with gzip.GzipFile(fileobj=io.BytesIO(raw))as stream:raw=stream.read(limit+1)
        require(len(raw)<=limit and(expected is None or len(raw)==expected),'Exact finite native decoded size');guard();return raw
    def binary(folder_,name,shape):
        result=np.frombuffer(decoded(path(folder_,name),math.prod(shape)*16),dtype='<c16').reshape(shape)
        require(np.isfinite(result).all(),'Finite actual complex128 array');return result
    meta=js(folder/'mesh-metadata.json');validation=js(folder/'validation.json');read(folder/'BASIS_COMPLETE')
    require(meta['cells']==351680 and meta['channels']==2 and meta['h_xy_mm']==.625 and meta['sc_cells']==2 and meta['bulk_layer_counts']==[14,14,40]and
        meta['frequencies_Hz']==list(FREQUENCIES)and meta['phasor_convention']=='peak,+jomega_t'and meta['source_peak_V']==.5 and meta['source_resistance_ohm']==50,
        'Unchanged canonical geometry/circuit/peak phasor ABI')
    for key,limit in NATIVE_GATES.items():require(0<=validation[key]<=limit,'Original native gate failed: '+key)
    config=_properties(read(run/'configs'/(CASE+'.properties')))
    require([float(config[k+'.sigma'])for k in LAYERS]==[.0002,.2,.04,.3]and [float(config[k+'.epsilon_r'])for k in LAYERS]==[1100,10000,1000,100000],
        'Exact predeclared one-factor SC epsilon sensitivity; no hidden retuning')
    oldconfig=_properties(read(ROOT/'data-native'/RUN_ID/'configs'/(OLD_CASE+'.properties')))
    material=js(folder/'effective-materials.json')
    require(material['sigma_unit']=='S/m'and material['epsilon_r_unit']=='dimensionless'and material['gamma_unit']=='S/m'and
        material['epsilon0_F_m']==EPS0 and material['frequency_dependent_sigma_epsilon']is False and len(material['rows'])==4,
        'Actual material lookup audit and unit convention required')
    material_rows=[]
    for row in material['rows']:
        frequency=row['frequency_Hz'];require(frequency in FREQUENCIES and len(row['layers'])==4,'One actual frequency/layer table')
        expected=_gamma(config,frequency);previous=_gamma(oldconfig,frequency)
        for i,item in enumerate(row['layers']):
            require(item['name']==LAYERS[i]and item['sigma_S_m']==float(config[LAYERS[i]+'.sigma'])and
                item['epsilon_r']==float(config[LAYERS[i]+'.epsilon_r'])and item['measured']is False and
                math.isclose(item['gamma_real_S_m'],expected[i].real,rel_tol=1e-14,abs_tol=1e-18)and
                math.isclose(item['gamma_imag_S_m'],expected[i].imag,rel_tol=1e-14,abs_tol=1e-18),
                'Actual exporter gamma must equal config sigma+jomega epsilon0 epsilon_r')
            material_rows.append(dict(frequency_Hz=frequency,layer=LAYERS[i],old_sigma_S_m=float(oldconfig[LAYERS[i]+'.sigma']),
                new_sigma_S_m=item['sigma_S_m'],old_epsilon_r=float(oldconfig[LAYERS[i]+'.epsilon_r']),new_epsilon_r=item['epsilon_r'],
                actual_gamma_S_m=dict(real=float(expected[i].real),imaginary=float(expected[i].imag)),
                old_gamma_S_m=dict(real=float(previous[i].real),imaginary=float(previous[i].imag)),
                actual_Im_gamma_over_Re_gamma=float(expected[i].imag/expected[i].real),
                material_status='uncalibrated sensitivity assumption; not measured phantom data'))
    grid=np.loadtxt(io.BytesIO(decoded(path(folder,'grid.csv'))),delimiter=',',skiprows=1)
    require(grid.shape==(351680,5)and np.isfinite(grid).all(),'Native grid dimensions/finite data')
    oldfolder=ROOT/'data-native'/RUN_ID/'bases'/OLD_CASE
    oldgrid=np.loadtxt(io.BytesIO(decoded(path(oldfolder,'grid.csv'))),delimiter=',',skiprows=1)
    require(np.array_equal(grid,oldgrid),'Exact grid/order comparator; no remapping');del oldgrid
    geometry=_geometry(grid,meta);layer=grid[:,3].astype(int);coeff=coefficients()
    with np.load(io.BytesIO(read(old['archive_path'])),allow_pickle=False)as archive:
        weights={key:np.array(archive['region_'+key+'_m3'],copy=True)for key in('total','target','surface_0_5','subsurface_5_10','remaining','off_target')}
        old_rms=np.array(archive['RMS'],copy=True);old_max=np.array(archive['maxTIS'],copy=True)
    require(all(w.shape==(len(grid),)and np.isfinite(w).all()and np.all(w>=0)for w in weights.values()),'Exact original same-grid fractional region weights')
    require(np.allclose(weights['total'],geometry['h']**2*geometry['dz'][geometry['iz']],rtol=1e-12,atol=1e-24),'Original represented cell-volume ABI')
    require(np.allclose(weights['off_target'],weights['total']-weights['target'],rtol=1e-12,atol=1e-24),'Original target complement mask')
    spectra={};old_spectra={};jt_energy=np.zeros(len(grid));jc_energy=np.zeros(len(grid));phi_e={};derived_j={};interfaces={};electrical_rows=[]
    import whole_layer_interfaces as iface
    analytic=iface.analytic_validation();require(analytic['status']=='passed','Independent analytic helper validation')
    jcontact2=None;contactV2=None;currents2=np.zeros(2);losses=np.zeros(6);sourcepower=0.;old_energy=np.zeros(len(grid));jarea=None
    for f in FREQUENCIES:
        guard();c=coeff[f];gamma=_gamma(config,f);native=binary(folder,'field-'+str(f)+'.bin',(2,len(grid),3));field=np.einsum('c,cnj->nj',c,native)
        spectra[f]=field;del native
        for kind,material in(('Jtotal',gamma[layer,None]),('Jconduction',np.asarray([float(config[k+'.sigma'])for k in LAYERS])[layer,None])):
            native=binary(folder,kind+'-'+str(f)+'.bin',(2,len(grid),3));actual=np.einsum('c,cnj->nj',c,native);expected=material*field
            derived_j[str(f)+'_'+kind]=_comparison(actual,expected,DERIVED_J_RTOL,DERIVED_J_ATOL,kind)
            if kind=='Jtotal':jt_energy+=np.sum(abs(actual)**2,axis=1)/2
            else:jc_energy+=np.sum(abs(actual)**2,axis=1)/2
            del native,actual,expected
        phi=np.einsum('c,cn->n',c,binary(folder,'potential-'+str(f)+'.bin',(2,len(grid))))
        contacts=np.genfromtxt(io.BytesIO(read(folder/('contacts-'+str(f)+'.csv'))),delimiter=',',names=True)
        ncontacts=len(contacts);density=c@binary(folder,'density-'+str(f)+'.bin',(2,ncontacts));transfer=binary(folder,'source-'+str(f)+'.bin',(2,2));current=transfer@c
        loss_matrix=binary(folder,'loss-'+str(f)+'.bin',(6,2,2));loss=np.einsum('i,kij,j->k',c.conj(),loss_matrix,c)
        require(np.max(abs(loss.imag))<=1e-12 and np.all(loss.real>=-1e-12),'Driven real nonnegative loss quadratic forms')
        supplied=float(.25*np.vdot(c,current).real);require(supplied>0,'Positive actual supplied source power')
        area=contacts['area_m2'];pads=contacts['pad'].astype(int);balance=abs(np.sum(density*area))/max(float(np.sum(abs(density)*area)),1e-30)
        signal=np.asarray([np.sum(density[pads==i]*area[pads==i])for i in range(2)])
        current_error=float(np.max(abs(signal-current))/max(float(np.max(abs(current))),1e-30));power_error=abs(float(loss.real.sum())-supplied)/supplied
        require(max(balance,current_error)<=2e-6 and power_error<=2e-7,'Driven actual current/power conservation')
        metal=.5*c-50*current;za=complex(float(config[f'z.{f}.re']),float(config[f'z.{f}.im']))
        reconstructed=reconstruct_native_field(phi,grid,geometry,gamma,contacts,metal,za)
        phi_e[str(f)]=_comparison(field,reconstructed,PHI_E_RTOL,PHI_E_ATOL,'phi to native half-face E');del reconstructed
        interfaces[str(f)]=iface.interface_diagnostics(phi,grid,meta,gamma,guard)
        if jcontact2 is None:jcontact2=np.zeros(ncontacts);contactV2=np.zeros(ncontacts);jarea=np.array(area,copy=True)
        require(np.array_equal(jarea,area),'Frequency contact area/order match')
        jcontact2+=abs(density)**2/2;contactV2+=abs(density*za)**2/2;currents2+=abs(current)**2/2;losses+=loss.real;sourcepower+=supplied
        electrical_rows.append(dict(frequency_Hz=f,coefficients_real=c.real.tolist(),coefficients_imaginary=c.imag.tolist(),
            current_peak_A=dict(real=current.real.tolist(),imaginary=current.imag.tolist()),loaded_metal_peak_V=dict(real=metal.real.tolist(),imaginary=metal.imag.tolist()),
            source_power_W=supplied,layer_contact_resistor_loss_W=loss.real.tolist(),KCL_relative_error=float(balance),output_current_relative_error=current_error,power_relative_error=power_error))
        old_native=binary(oldfolder,'field-'+str(f)+'.bin',(2,len(grid),3));old_field=np.einsum('c,cnj->nj',c,old_native);old_spectra[f]=old_field;old_energy+=np.sum(abs(old_field)**2,axis=1)/2
        del phi,density,transfer,loss_matrix,old_native
    _comparison(np.sqrt(old_energy),old_rms,1e-10,1e-12,'Canonical square3h coefficient/comparator RMS')
    waveform_proof=actual_waveform_checks(spectra,grid,guard)
    total_rms=np.sqrt(sum(np.sum(abs(v)**2,axis=1)/2 for v in spectra.values()));fund_rms=np.sqrt(sum(np.sum(abs(spectra[f])**2,axis=1)/2 for f in FUNDAMENTALS))
    harmonic_rms=np.sqrt(sum(np.sum(abs(spectra[f])**2,axis=1)/2 for f in(9000,9090)))
    am=2*np.minimum(abs(spectra[3000]),abs(spectra[3030]));old_am=2*np.minimum(abs(old_spectra[3000]),abs(old_spectra[3030]))
    arrays=dict(total_E_RMS_V_m=total_rms,fundamental_E_RMS_V_m=fund_rms,harmonic_E_RMS_V_m=harmonic_rms,
        X_fundamental_TIS_V_m=am[:,0],Y_fundamental_TIS_V_m=am[:,1],Z_fundamental_TIS_V_m=am[:,2],
        total_Jtotal_RMS_A_m2=np.sqrt(jt_energy),total_Jconduction_RMS_A_m2=np.sqrt(jc_energy))
    for f in FREQUENCIES:arrays['carrier_'+str(f)+'_E_RMS_V_m']=np.sqrt(np.sum(abs(spectra[f])**2,axis=1)/2)
    if include_max_direction:
        maximum,winner,direction_proof=_maximum_direction(spectra[3000],spectra[3030],guard,deadline_monotonic)
        if maximum is not None:arrays.update(fundamental_maxTIS_2074_V_m=maximum,maxTIS_direction_index=winner)
    else:direction_proof=dict(status='not_run',reason='Caller excluded angular search; no maximum-direction result fabricated')
    regions={**{name:weights['total']*(layer==i)for i,name in enumerate(LAYERS)},**weights}
    statistics={};comparison={};scalar_names=[name for name in arrays if name!='maxTIS_direction_index']
    for region,w in regions.items():
        guard();statistics[region]={name:weighted_statistics(arrays[name],w,grid)for name in scalar_names}
        comparison[region]=dict(baseline_total_RMS=weighted_statistics(old_rms,w,grid),sensitivity_total_RMS=statistics[region]['total_E_RMS_V_m'],
            baseline_X_TIS=weighted_statistics(old_am[:,0],w,grid),baseline_Y_TIS=weighted_statistics(old_am[:,1],w,grid),baseline_Z_TIS=weighted_statistics(old_am[:,2],w,grid),
            baseline_cached_maxTIS_2074=weighted_statistics(old_max,w,grid))
    jrms=np.sqrt(jcontact2);order=np.argsort(jrms,kind='stable');j95=float(jrms[order[min(int(np.searchsorted(np.cumsum(jarea[order]),.95*jarea.sum(),side='left')),len(order)-1)]])
    skin=weights['total']*(layer<=1);jskin=weighted_statistics(arrays['total_Jtotal_RMS_A_m2'],skin,grid)
    electrical=dict(source_Vpp_per_output=1.,source_convention='high-Z1Vpp waveform before each50ohm; peak+jomega_t bases',
        source_current_RMS_by_output_mA=(np.sqrt(currents2)*1000).tolist(),source_power_W=sourcepower,
        layers_power_W={name:float(losses[i])for i,name in enumerate(LAYERS)},contact_power_W=float(losses[4]),source_resistor_power_W=float(losses[5]),
        contact_normal_J_RMS_max_A_m2=float(jrms.max()),contact_normal_J_RMS_P95_A_m2=j95,contact_voltage_RMS_max_V=float(np.sqrt(contactV2.max())),
        SC_plus_dermis_Jtotal_RMS_max_A_m2=jskin['max'],SC_plus_dermis_Jtotal_RMS_P95_A_m2=jskin['p95'],spectrum=electrical_rows)
    baseline_electrical=old['square']['metrics']
    matched_scales=dict(fixed_source_Vpp=1.,
        equal_total_source_real_power=math.sqrt(baseline_electrical['source_power_W']/sourcepower),
        equal_contact_normal_J_RMS_max=baseline_electrical['surface_J_RMS_max_A_m2']/electrical['contact_normal_J_RMS_max_A_m2'],
        equal_sum_of_output_RMS_currents_bookkeeping=float(np.sum(baseline_electrical['source_current_RMS_by_output_mA'])/np.sum(electrical['source_current_RMS_by_output_mA'])))
    normalized=[]
    for name,scale in matched_scales.items():
        normalized.append(dict(name=name,common_source_amplitude_scale=scale,source_Vpp_each=scale,
            target_mean_total_E_RMS_V_m=statistics['target']['total_E_RMS_V_m']['mean']*scale,
            target_P10_total_E_RMS_V_m=statistics['target']['total_E_RMS_V_m']['p10']*scale,
            target_mean_fundamental_maxTIS_V_m=statistics['target'].get('fundamental_maxTIS_2074_V_m',{}).get('mean',None)*scale if 'fundamental_maxTIS_2074_V_m'in statistics['target']else None,
            target_P10_fundamental_maxTIS_V_m=statistics['target'].get('fundamental_maxTIS_2074_V_m',{}).get('p10',None)*scale if 'fundamental_maxTIS_2074_V_m'in statistics['target']else None,
            contact_normal_J_RMS_max_A_m2=electrical['contact_normal_J_RMS_max_A_m2']*scale,
            contact_normal_J_RMS_P95_A_m2=j95*scale,contact_voltage_RMS_max_V=electrical['contact_voltage_RMS_max_V']*scale,
            source_power_W=sourcepower*scale*scale,SC_power_W=float(losses[0])*scale*scale,
            source_current_RMS_by_output_mA=(np.sqrt(currents2)*1000*scale).tolist(),
            interpretation='Each row matches only its named quantity. Sum of output RMS currents is bookkeeping, not net common-ground current. Equal Jmax is not a simultaneous multi-burden skin match or safety limit.'))
    summary=dict(schema='task1-whole-layer-assumption-sensitivity-post-v1',status='calculated_sensitivity_unadopted',case_id=CASE,
        actual_native_new_conditions=1,actual_native_new_RHS=8,new_PDE_in_postprocess=0,
        material_status='Uncalibrated four-layer hypotheses; only SCepsilon110000to1100; not a paper-material reproduction or experimental correction',
        coefficients={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in coeff.items()},
        native_gates=dict(status='passed',values=validation,thresholds=NATIVE_GATES),actual_material_lookup_audit=dict(status='passed_config_arithmetic_only',rows=material_rows,frequency_dispersion_status='sigma/epsilon constants; only omega term changes; no calibrated tissue dispersion fit'),derived_J_consistency=derived_j,
        phi_to_stored_E_consistency=phi_e,independent_interface_potential_gradient_diagnostics=interfaces,
        independent_analytic_layered_slab_and_affine=analytic,actual_native_waveform_checks=waveform_proof,maximum_direction_search=direction_proof,
        statistical_definition='Native cell-constant Float64 fields; original same-grid volume weights; stable inverse weighted ECDF; no value clipping or redistribution',
        coordinate_system='x/y horizontal mm; top surface z0; positive z is depth',
        model=dict(radius_mm=25,layers_mm=[.1,5,5,15],h_xy_mm=.625,layer_counts=[2,14,14,40],cells=len(grid),pads=4,outputs=2,return_topology='pad2and3commonGND',source_resistance_ohm=50),
        statistics=statistics,comparison_to_original_same_drive=comparison,electrical=electrical,baseline_cached_electrical_metrics=baseline_electrical,
        separate_linear_normalizations=normalized,input_sha256=used,
        comparator=dict(run_id=RUN_ID,case_id=OLD_CASE,status='existing_native_and_cached_maxTIS_reused; not a new comparator solve'),
        metric_separation=dict(carrier_RMS='per-frequency vector RMS',total_RMS='all four actual carrier/harmonic frequencies',
            fundamental_TIS='3000/3030 only; real fixed x/y/z projections with2min complex peak amplitudes',
            full_four_frequency_envelope_modulation='not_run; two-tone expression not extended to four-frequency waveform',
            max_direction='2074 finite sampled directions; not exact continuous maximum',
            Jtotal='conduction plus displacement gamma E',Jconduction='sigma E',raw_J_export='derived from same stored E, not independent physical verification'),
        validation_holds=dict(full_SC_XY_bulk_edge_convergence=False,independent_interface_accuracy_gated=False,experimental_validation=False,
            material_calibration=False,nominal_PBS_contact_as_skin_validated=False,existing_XY_surface_contact_failure_retained=True,
            independent_outer_wall_bottom_insulation_accuracy_validated=False,cylinder_staircase_sensitivity_validated=False,
            initial_2000_2010_condition_reproduced=False,current_f35_new_material_solve=False,activation_or_safety_validated=False))
    arrays.update({name+'_volume_weight_m3':w for name,w in regions.items()})
    guard();return dict(summary=summary,arrays=arrays)
