"""Cached actual U19 source-basis/topology audit. No import-time data IO.

Two 2000 Hz native RHS already exist. This module performs no new PDE and no
TIS/physiology/safety inference. The finite root owner controls all reads/output.
"""
from __future__ import annotations
import gzip,hashlib,io,json,math,time
from pathlib import Path
import numpy as np

RUN=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run')
CASE='baseline-square15-human-sine2000-sc8-vs19uniform-bulk19-18-56-xy100'
ROOT=Path('/workspace/ngg-tis-task1')
LAYERS=('sc','dermis','fat','muscle');EPS0=8.8541878128e-12
GATES=dict(max_residual=2e-7,max_power_error=2e-7,max_current_error=2e-6,max_area_relative_error=1e-10,max_interface_normal_current_relative_error=2e-7)
SOURCE0_RTOL=1e-10;SOURCE0_ATOL=1e-12
MAX_STORED=80*1024**2;MAX_DECODED=128*1024**2
PAD_REFLECTION={0:1,1:0,2:3,3:2}


def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def _properties(raw):return {k.strip():v.strip()for line in raw.decode().splitlines()if '='in line and not line.lstrip().startswith(('#','!'))for k,v in[line.split('=',1)]}
def _bounded(path):
 p=Path(path);require(p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Bounded actual metadata/source file');return p.read_bytes()


def required_inputs():
 """Owner-only deferred metadata/source hashes; raw native SHA declared, not read."""
 refs={};metadata={}
 for name in('native-sha256.json','postprocess/summary.json','postprocess/artifact-sha256.json','result-publication.json','source-publication.json','persist-receipt.json'):
  p=RUN/name;r=_bounded(p);refs[str(p)]=sha(r);metadata[name]=json.loads(r)
 summary=metadata['postprocess/summary.json'];artifact=metadata['postprocess/artifact-sha256.json'];manifest=metadata['native-sha256.json'];publication=metadata['result-publication.json']
 require(summary['case_id']==CASE and summary['frequency_Hz']==2000 and summary['actual_new_RHS']==2 and summary['actual_new_native_conditions']==1 and'U19'in summary['scenarios'],'Actual complete U19 two-basis one-carrier comparator')
 require(refs[str(RUN/'postprocess/summary.json')]==artifact['summary.json']['SHA256'],'Actual source0 summary SHA')
 require(manifest['native_conditions_completed']==1 and manifest['native_RHS_completed']==2,'Actual completed native bases')
 require(publication['status']=='published_readback_verified'and isinstance(publication['commit'],str)and len(publication['commit'])==40,'Full immutable U19 publication prerequisite')
 sourcepub=metadata['source-publication.json'];require(sourcepub['status']=='published_readback_verified','Published immutable source prerequisite')
 sourcepub_sha=refs[str(RUN/'source-publication.json')]
 require(any(name.endswith('/source-publication.json')and item.get('SHA256')==sourcepub_sha and item.get('readback_passed')is True for name,item in publication['files'].items()),'Authenticate exact source-publication document through current result readback')
 def published_proof(p,digest):
  relative=p.relative_to(RUN).as_posix();documents=[publication]if relative.startswith('bases/')else[publication,sourcepub]
  matches=[v for document in documents for name,v in document['files'].items()if name.endswith('/'+relative)and v.get('SHA256')==digest and v.get('readback_passed')is True]
  require(matches,'Direct per-file authenticated U19 readback proof required: '+relative);return matches[0]
 proof={}
 for path,digest in manifest['files'].items():
  p=Path(path);require(p.is_relative_to(RUN),'Only exact U19 native/config paths');relative=p.relative_to(RUN).as_posix()
  refs[path]=digest;proof[path]=published_proof(p,digest)
 published_proof(RUN/'postprocess/summary.json',refs[str(RUN/'postprocess/summary.json')])
 cfgpath=RUN/'configs'/(CASE+'.properties');raw=_bounded(cfgpath);require(sha(raw)==refs[str(cfgpath)],'Pinned published actual U19 config');cfg=_properties(raw)
 for label,name in(('material','material-input.json'),('contact','contact-receipt.json')):
  p=RUN/name;r=_bounded(p);require(sha(r)==cfg[label+'.input_sha256'],'Actual unchanged receipt SHA');refs[str(p)]=sha(r);published_proof(p,sha(r))
 faces=Path(cfg['mesh.z_faces_path']);r=_bounded(faces);require(faces==RUN/'z-faces.json'and sha(r)==cfg['mesh.z_faces_sha256'],'Exact actual face receipt');refs[str(faces)]=sha(r);published_proof(faces,sha(r))
 mask=Path(cfg['mask.path']);r=_bounded(mask);require(mask==RUN/'masks'/(CASE+'.csv')and sha(r)==cfg['mask.sha256'],'Exact actual electrode mask');refs[str(mask)]=sha(r);published_proof(mask,sha(r))
 for name in('selectivity_volume.py','explore_tis.py'):
  p=ROOT/'tis-java'/name;refs[str(p)]=sha(_bounded(p))
 p=Path(__file__).parent/'basis_math.py';refs[str(p)]=sha(_bounded(p))
 return refs


def make_spec():
 """Owner calls before field opening and persists this finite audit specification."""
 refs=required_inputs();publication=json.loads(_bounded(RUN/'result-publication.json'))
 return dict(schema='task1-U19-cached-basis-audit-spec-v1',case_id=CASE,frequency_Hz=2000,input_sha256=refs,publication_commit=publication['commit'],source_coefficients=[[1,0],[0,1]],
  source0_summary_check=dict(relative_tolerance=SOURCE0_RTOL,absolute_tolerance=SOURCE0_ATOL),
  native_thresholds=dict(GATES),symmetry='Attempt Y-reflection and separately predeclared180degreeXYrotation only after exact mask/area/full-grid proof; otherwise not_applicable; no phase or gauge fitting',
  interpretation='Separate existing source1/source0 carrier RMS and burdens; both other outputs ideal0V behind50ohm;4pads/2outputs/commonreturn; no new PDE or TIS')


def contact_reflection_proof(contacts,transformation='y_reflection'):
 """Prove exact top-contact geometry under y→-y,pads0↔1,2↔3, or decline."""
 require(transformation in('y_reflection','xy_rotation180'),'Declared coordinate transformation only');sx=1 if transformation=='y_reflection'else-1
 lookup={};areas={i:0. for i in range(4)}
 for i,row in enumerate(contacts):
  p=int(row['pad']);x=float(row['x_mm']);y=float(row['y_mm']);a=float(row['area_m2'])
  require(p in PAD_REFLECTION and all(math.isfinite(v)for v in(x,y,a))and a>0,'Finite positive four-pad contact cells')
  key=(p,x,y)
  if key in lookup:return dict(status='not_applicable',reason='Duplicate pad/XY contact entries prevent exact one-to-one geometry proof'),None
  lookup[key]=(i,a);areas[p]+=a
 if set(int(r['pad'])for r in contacts)!=set(PAD_REFLECTION):return dict(status='not_applicable',reason='Actual contact table lacks the declared four pads'),None
 permutation=[]
 for row in contacts:
  key=(PAD_REFLECTION[int(row['pad'])],sx*float(row['x_mm']),-float(row['y_mm']));target=lookup.get(key)
  if target is None:return dict(status='not_applicable',reason='Pad mask is not invariant under required y-reflection/pad exchange',unmatched=dict(pad=int(row['pad']),x_mm=float(row['x_mm']),y_mm=float(row['y_mm']))),None
  if target[1]!=float(row['area_m2']):return dict(status='not_applicable',reason='Reflected contact area differs; exact physical mask equivalence not proved'),None
  permutation.append(target[0])
 require(len(set(permutation))==len(contacts),'Bijective contact permutation')
 return dict(status='exact_'+transformation+'_pad_mask_proved',transformation=transformation,contacts=len(contacts),pad_mapping={str(k):v for k,v in PAD_REFLECTION.items()},area_by_pad_m2={str(k):v for k,v in areas.items()},
  scope='Exact matching native contact XY coordinates and areal weights, not an inferred electrode design'),np.asarray(permutation,int)


def grid_y_permutation(grid,geometry,transformation='y_reflection'):
 require(transformation in('y_reflection','xy_rotation180'),'Declared coordinate transformation only');sx=1 if transformation=='y_reflection'else-1
 y=geometry['y'];require(np.array_equal(y,-y[::-1]),'Exact symmetric native y axis')
 ix=geometry['ix']if sx==1 else len(geometry['x'])-1-geometry['ix'];p=geometry['lookup'][geometry['iz'],len(y)-1-geometry['iy'],ix]
 require(np.all(p>=0)and len(np.unique(p))==len(grid),'Complete bijective native reflection')
 require(np.array_equal(grid[p,0],sx*grid[:,0])and np.array_equal(grid[p,1],-grid[:,1])and np.array_equal(grid[p,2:],grid[:,2:]),'Declared transform preserves physical z,layer,volume and exactly maps x/y')
 return p


def mask_contact_binding(mask,contacts,h_mm):
 """Mask schema is pad,i,j,area_m2; fourth column is never a fraction."""
 declared={};actual={}
 for row in mask:
  i=float(row['i']);j=float(row['j']);p=int(row['pad']);a=float(row['area_m2'])
  require(i==int(i)and j==int(j)and 0<=i<100 and 0<=j<100 and a>0 and math.isfinite(a),'Valid actual indexed-area mask')
  key=(p,-25+(i+.5)*h_mm,-25+(j+.5)*h_mm)
  if key in declared:return dict(status='geometry_mismatch',reason='Duplicate canonical mask location')
  declared[key]=a
 for row in contacts:
  key=(int(row['pad']),float(row['x_mm']),float(row['y_mm']))
  if key in actual:return dict(status='geometry_mismatch',reason='Duplicate native contact location')
  actual[key]=float(row['area_m2'])
 return dict(status='exact_mask_native_contact_geometry_match'if declared==actual else'geometry_mismatch',schema='pad,i,j,area_m2; absolute area, not fraction',mask_entries=len(declared),native_contacts=len(actual),typed_float_area_identity=declared==actual)


def weighted_quantile(values,weights,q):
 v=np.asarray(values,float);w=np.asarray(weights,float);require(v.ndim==1 and v.shape==w.shape and np.isfinite(v).all()and np.isfinite(w).all()and np.all(w>=0)and w.sum()>0 and 0<=q<=1,'Finite positive weighted-quantile input')
 ids=np.argsort(v,kind='stable');at=min(int(np.searchsorted(np.cumsum(w[ids]),q*w.sum(),side='left')),len(ids)-1);return float(v[ids[at]])


def conservation(coefficients,transfer,loss_forms,density,areas,pads):
 c=np.asarray(coefficients,complex);current=transfer@c;j=c@density;loss=np.einsum('i,kij,j->k',c.conj(),loss_forms,c)
 supplied=float(.25*np.vdot(c,current).real);den=max(float(np.max(abs(current))),1e-30);integral=np.asarray([np.sum(j[pads==i]*areas[pads==i])for i in range(2)])
 kcl=float(abs(np.sum(j*areas))/max(float(np.sum(abs(j)*areas)),1e-30));cerr=float(np.max(abs(integral-current))/den);p_error=abs(float(loss.real.sum())-supplied)/max(abs(supplied),1e-30)
 passed=bool(np.max(abs(loss.imag))<=1e-12 and np.all(loss.real>=-1e-12)and supplied>0 and kcl<=GATES['max_current_error']and cerr<=GATES['max_current_error']and p_error<=GATES['max_power_error'])
 return dict(passed=passed,coefficients=dict(real=c.real.tolist(),imaginary=c.imag.tolist()),source_power_W=supplied,losses_W=loss.real.tolist(),loss_imaginary_absmax_W=float(abs(loss.imag).max()),
  contact_KCL_relative=kcl,output_current_relative=cerr,power_relative=p_error,output_peak_current_A=dict(real=current.real.tolist(),imaginary=current.imag.tolist())),current,j,loss.real


def parity_diagnostic(a,b,weights,grid,quantity,units):
 """Volume-weighted complex-amplitude differences, no threshold or fitted offset."""
 a=np.asarray(a);b=np.asarray(b);require(a.shape==b.shape and a.shape[0]==len(grid)and np.isfinite(a).all()and np.isfinite(b).all(),'Finite same-grid parity arrays')
 if a.ndim==1:a=a[:,None];b=b[:,None]
 w=np.asarray(weights);square=np.sum(abs(a-b)**2,axis=1);volume=float(w.sum());difference=math.sqrt(float(w@square/volume));na=math.sqrt(float(w@np.sum(abs(a)**2,axis=1)/volume));nb=math.sqrt(float(w@np.sum(abs(b)**2,axis=1)/volume));den=max(na,nb,1e-12);point=np.sqrt(square);i=int(np.argmax(point))
 return dict(status='calculated_diagnostic_not_gated',quantity=quantity,units=units,absolute_volume_weighted_RMS_difference=difference,source0_complex_amplitude_norm=na,reflected_source1_complex_amplitude_norm=nb,normalized_L2=difference/den,denominator=den,denominator_floor=1e-12,
  maximum_native_vector_absolute_difference=float(point[i]),maximum_location_xyz_mm=grid[i,:3].tolist(),phase_or_gauge_fitted=False,scope='Spatial volume-weighted peak-phasor norms, not temporal RMS or continuum accuracy')


def build(guard,deadline_monotonic=None,*,spec=None):
 """Root only; read hash-pinned cached actual native fields, no new solve/writes."""
 from basis_math import native_geometry,weighted_statistics
 from selectivity_volume import native_region_weights
 require(callable(guard),'Explicit finite sole-owner guard');guard();spec=make_spec()if spec is None else spec
 require(spec['schema']=='task1-U19-cached-basis-audit-spec-v1'and spec['case_id']==CASE and spec['frequency_Hz']==2000 and spec['source_coefficients']==[[1,0],[0,1]]and spec['native_thresholds']==GATES,'Exact frozen audit spec')
 pins=spec['input_sha256'];used={}
 def check():
  guard();require(deadline_monotonic is None or time.monotonic()<deadline_monotonic,'Finite cached-audit deadline')
 def read(path):
  check();p=Path(path);require(str(p)in pins and p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<=MAX_STORED,'Only exact bounded pinned files')
  raw=p.read_bytes();require(sha(raw)==pins[str(p)],'Actual input bytes changed');used[str(p)]=pins[str(p)];return raw
 def js(p):return json.loads(read(p))
 folder=RUN/'bases'/CASE
 def path(name):
  ps=[p for p in(folder/name,folder/(name+'.gz'))if str(p)in pins and p.is_file()];require(len(ps)==1,'One actual published native file '+name);return ps[0]
 def decoded(p):
  raw=read(p)
  if p.suffix=='.gz':
   with gzip.GzipFile(fileobj=io.BytesIO(raw))as stream:raw=stream.read(MAX_DECODED+1)
  require(len(raw)<=MAX_DECODED,'Bounded native decode');return raw
 def binary(name,shape):
  raw=decoded(path(name));require(len(raw)==math.prod(shape)*16,'Exact complex128LE native shape');a=np.frombuffer(raw,dtype='<c16').reshape(shape);require(np.isfinite(a).all(),'Finite actual complex native values');return a
 meta=js(folder/'mesh-metadata.json');validation=js(folder/'validation.json');read(folder/'BASIS_COMPLETE')
 require(meta['frequencies_Hz']==[2000]and meta['channels']==2 and meta['sc_cells']==8 and meta['bulk_layer_counts']==[19,18,56]and meta['h_xy_mm']==.5 and meta['source_peak_V']==.5 and meta['source_resistance_ohm']==50 and meta['phasor_convention']=='peak,+jomega_t','Exact existing U19 ABI/source condition')
 require(meta['pad_to_node']=={'0':'out0','1':'out1','2':'GND','3':'GND'}and meta['inactive_output_at_each_basis_frequency']=='0V through50ohm','Actual four-pad/two-output/commonreturn topology')
 for key,limit in GATES.items():require(0<=validation[key]<=limit,'Original native gate '+key)
 grid=np.loadtxt(io.BytesIO(decoded(path('grid.csv'))),delimiter=',',skiprows=1);n=len(grid);require(grid.shape==(n,5)and n==meta['cells']and n<=800000,'Exact finite native grid');geometry=native_geometry(grid,meta);layer=grid[:,3].astype(int)
 cfg=_properties(read(RUN/'configs'/(CASE+'.properties')));sigma=np.asarray([float(cfg[k+'.sigma.2000'])for k in LAYERS]);epsilon=np.asarray([float(cfg[k+'.epsilon_r.2000'])for k in LAYERS]);gamma=sigma+2j*math.pi*2000*EPS0*epsilon
 require(np.isfinite(gamma).all()and np.all(sigma>0)and np.all(epsilon>0),'Actual positive material lookup')
 material=js(folder/'effective-materials.json');lookup=next(r['layers']for r in material['rows']if r['frequency_Hz']==2000)
 for i,row in enumerate(lookup):require(row['name']==LAYERS[i]and row['sigma_S_m']==sigma[i]and row['epsilon_r']==epsilon[i]and math.isclose(row['gamma_real_S_m'],gamma[i].real,rel_tol=1e-14,abs_tol=1e-18)and math.isclose(row['gamma_imag_S_m'],gamma[i].imag,rel_tol=1e-14,abs_tol=1e-18),'Actual gamma/config arithmetic')
 weights,roi_receipt=native_region_weights({k:grid[:,i]for i,k in enumerate(('x_mm','y_mm','z_mm','layer','volume_m3'))},dict(meta,radius_mm=25,layer_counts=[8,19,18,56],geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001),deadline_monotonic=deadline_monotonic)
 regions={**{name:weights['total']*(layer==i)for i,name in enumerate(LAYERS)},**weights,'surface_without_SC':weights['surface_0_5']*(layer!=0)}
 fields=binary('field-2000.bin',(2,n,3));potentials=binary('potential-2000.bin',(2,n));transfer=binary('source-2000.bin',(2,2));loss_forms=binary('loss-2000.bin',(6,2,2))
 contacts=np.genfromtxt(io.BytesIO(read(folder/'contacts-2000.csv')),delimiter=',',names=True);area=contacts['area_m2'];pads=contacts['pad'].astype(int);density=binary('density-2000.bin',(2,len(contacts)));za=complex(float(cfg['z.2000.re']),float(cfg['z.2000.im']))
 mask=np.genfromtxt(io.BytesIO(read(Path(cfg['mask.path']))),delimiter=',',names=True);require(mask.dtype.names==('pad','i','j','area_m2'),'Actual indexed-area mask schema; no fractional-area interpretation')
 binding=mask_contact_binding(mask,contacts,meta['h_xy_mm'])
 parent=js(RUN/'postprocess/summary.json')['scenarios']['U19'];scenarios={};arrays={};conservation_rows=[]
 for basis in(0,1):
  check();c=np.zeros(2);c[basis]=1;proof,current,j,loss=conservation(c,transfer,loss_forms,density,area,pads);conservation_rows.append(proof)
  E=fields[basis];rms=np.linalg.norm(E,axis=1)/math.sqrt(2);jrms=np.linalg.norm(gamma[layer,None]*E,axis=1)/math.sqrt(2);skin=weighted_statistics(jrms,weights['total']*(layer<=1),grid);contact=abs(j)/math.sqrt(2)
  stats={name:weighted_statistics(rms,w,grid)for name,w in regions.items()}
  electrical=dict(source_power_W=proof['source_power_W'],source_Vpp_each_active=1.,output_RMS_current_A=(abs(current)/math.sqrt(2)).tolist(),sum_output_current_RMS_A_bookkeeping=float(abs(current).sum()/math.sqrt(2)),
   layers_power_W={name:float(loss[i])for i,name in enumerate(LAYERS)},SC_power_W=float(loss[0]),skin_power_W=float(loss[:2].sum()),contact_power_W=float(loss[4]),source_resistor_power_W=float(loss[5]),
   skin_vector_J_RMS_max_A_m2=skin['max'],skin_vector_J_RMS_P95_A_m2=skin['p95'],contact_normal_J_RMS_max_A_m2=float(contact.max()),contact_normal_J_RMS_P95_A_m2=weighted_quantile(contact,area,.95),contact_voltage_RMS_max_V=float(abs(j*za).max()/math.sqrt(2)))
  scenarios['source'+str(basis)]=dict(frequency_Hz=2000,active_output=basis,source_coefficients=c.tolist(),native_RHS_reused=True,statistics=stats,electrical=electrical,conservation=proof,
   definition='Existing actual source basis; other output ideal0V through50ohm. Four pads/twooutputs/commonreturn; not a one-electrode-pair model.')
  arrays['source'+str(basis)+'_E_carrier_RMS_V_m']=rms
  if basis==1:arrays['source1_Jtotal_carrier_RMS_A_m2']=jrms
 # These are algebraic same-frequency superpositions, not new protocols/PDE/TIS.
 for c in([1,1],[1,1j]):
  proof,_,_,_=conservation(c,transfer,loss_forms,density,area,pads);proof['scope']='Same-frequency algebraic energy/KCL cross-term check; no new PDE, TIS or proposed hardware protocol';conservation_rows.append(proof)
 audit=[]
 def compare(name,a,b):
  passed=abs(a-b)<=SOURCE0_ATOL+SOURCE0_RTOL*abs(b);audit.append(dict(metric=name,recomputed=float(a),preserved_source0_summary=float(b),absolute_difference=float(abs(a-b)),rtol=SOURCE0_RTOL,atol=SOURCE0_ATOL,passed=bool(passed)))
 for region,values in scenarios['source0']['statistics'].items():
  for key in('mean','p10','energy_RMS'):compare(region+'.E_carrier_RMS.'+key,values[key],parent['statistics'][region]['E_carrier_RMS_V_m'][key])
 for key,value in scenarios['source0']['electrical'].items():
  if isinstance(value,(int,float)):compare(key,value,parent['electrical'][key])
  elif key=='layers_power_W':
   for name,v in value.items():compare(name+'_power_W',v,parent['electrical'][key][name])
  elif key=='output_RMS_current_A':
   for i,v in enumerate(value):compare('output'+str(i)+'_RMS_current_A',v,parent['electrical'][key][i])
 symmetries={}
 for transformation,sx in(('y_reflection',1.),('xy_rotation180',-1.)):
  reflection,contact_perm=contact_reflection_proof(contacts,transformation);symmetry=dict(mask_proof=reflection,status='not_applicable')
  if binding['status']!='exact_mask_native_contact_geometry_match':
   symmetry.update(reason='Canonical mask/native contact binding failed; no geometric symmetry inferred')
  elif contact_perm is not None:
   try:permutation=grid_y_permutation(grid,geometry,transformation)
   except ValueError as error:symmetry.update(reason=str(error))
   else:
    reflected_E=fields[1,permutation]*np.asarray([sx,-1.,1.]);symmetry=dict(status='calculated_diagnostic_not_gated',mask_proof=reflection,
     field_parity=parity_diagnostic(fields[0],reflected_E,weights['total'],grid,'E0 versus transformed E1; vector parity('+str(sx)+',-1,+1)','V/m'),
     potential_parity=parity_diagnostic(potentials[0],potentials[1,permutation],weights['total'],grid,'phi0(x,y,z) versus phi1('+str(sx)+'*x,-y,z)','V'),
     contact_density_max_absolute_difference_A_m2=float(abs(density[0]-density[1,contact_perm]).max()),
     output_current_swap_max_absolute_difference_A=float(abs(transfer[:,0]-transfer[[1,0],1]).max()),
     source_power_difference_W=scenarios['source1']['electrical']['source_power_W']-scenarios['source0']['electrical']['source_power_W'],
     interpretation='Exact geometrical/network symmetry hypothesis with direct same-phase,common-GND complex fields; no offset/phase/gauge fit and no inference of physical validation.')
  symmetries[transformation]=symmetry
 overall=all(r['passed']for r in conservation_rows)and all(r['passed']for r in audit)and binding['status']=='exact_mask_native_contact_geometry_match'
 check();return dict(summary=dict(schema='task1-U19-actual-cached-basis-audit-v1',status='calculated_cached_audit'if overall else'calculated_cached_audit_failed_checks_preserved',spec=spec,source0_summary_audit=audit,all_conservation_and_source0_checks_passed=overall,scenarios=scenarios,
  algebraic_same_frequency_checks=conservation_rows,canonical_mask_contact_binding=binding,reflection=symmetries['y_reflection'],rotation180=symmetries['xy_rotation180'],reciprocity_diagnostic=dict(offdiagonal_transfer_current_absolute_difference_A=float(abs(transfer[0,1]-transfer[1,0])),status='diagnostic_not_gated'),
  ROI_geometry=roi_receipt,actual_material_lookup=material,raw_format='complex128LE,peak+jomega_t; E(2,N,3),phi(2,N),source(2,2),loss(6,2,2),density(2,Ncontacts)',input_sha256=used,
  experimental_or_safety_validation=False,material_or_anatomic_calibration=False,candidate_adopted=False,new_PDE=0,new_TIS_modulation='not_defined_one_carrier',native_interface_5percent_holds_unchanged=True,
  interpretation='Source1 is a separately reported cached basis at2000Hz. Equal field/RMS or exact numerical symmetry does not imply equal physiological activation/safety. Native field J is derived gamma E; native quadratic/face losses are not falsely equated to integral of averaged stored E.'),arrays=arrays)
