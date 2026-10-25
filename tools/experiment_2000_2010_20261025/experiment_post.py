"""Guard-owned minimum 2k/2010 sine analysis. No import-time IO or native work."""
from __future__ import annotations
import csv,gzip,hashlib,io,json,math,time
from pathlib import Path
import numpy as np
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-experiment-2000-2010-20261025/source')
RUN=Path('/workspace/task1-experiment-2000-2010-20261025-run')
CASE='baseline-square15-human-sine2000-2010-xy80'
HUMAN=Path('/dev/shm/task1-human-tissue-20261025-run')
HCASE='baseline-square15-human-reference-xy80'
LEGACY=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z'
LCASE='baseline-square15-xy80'
LAYERS=('sc','dermis','fat','muscle')
A1=3/(2*math.sqrt(2));EPS0=8.8541878128e-12
GATES=dict(max_residual=2e-7,max_power_error=2e-7,max_current_error=2e-6,max_area_relative_error=1e-10,max_interface_normal_current_relative_error=2e-7)
QA_LIMIT=.05

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def required_inputs():
 """Read only small metadata and frozen source, no native arrays or NPZ."""
 refs={}
 for run,case in((HUMAN,HCASE),(LEGACY,LCASE)):
  summarypath=run/('postprocess/summary.json'if run==HUMAN else 'postprocess/'+case+'/summary.json')
  raw=summarypath.read_bytes();require(len(raw)<4*1024**2,'Bounded completed comparator metadata');s=json.loads(raw);refs[str(summarypath)]=sha(raw)
  if run==HUMAN:
   m=run/'native-sha256.json';r=m.read_bytes();refs[str(m)]=sha(r);refs.update(json.loads(r)['files'])
   artifactpath=run/'postprocess/artifact-sha256.json';r=artifactpath.read_bytes();refs[str(artifactpath)]=sha(r);a=json.loads(r)
   refs[str(run/'postprocess/scalars.npz')]=a['scalars.npz']['SHA256']
  else:
   refs.update({p:h for p,h in s['input_sha256'].items()if '/bases/'+case+'/'in p or p.endswith('/configs/'+case+'.properties')})
   square=next(c for c in s['conditions']if c['waveform']=='square_3h');refs[str(summarypath.parent/square['native_volume_archive'])]=s['artifacts']['files'][square['native_volume_archive']]['SHA256']
 for name in('human_post.py','human_interfaces.py'):
  p=Path('/dev/shm/task1-human-tissue-20261025/source')/name;refs[str(p)]=sha(p.read_bytes())
 return refs

def _properties(raw):return {k.strip():v.strip()for line in raw.decode().splitlines()if '='in line and not line.lstrip().startswith(('#','!'))for k,v in[line.split('=',1)]}
def _gamma(config,f):
 return np.asarray([complex(float(config.get(n+'.sigma.'+str(f),config.get(n+'.sigma','nan'))),2*math.pi*f*EPS0*float(config.get(n+'.epsilon_r.'+str(f),config.get(n+'.epsilon_r','nan'))))for n in LAYERS])
def _sigma(config,f):return np.asarray([float(config.get(n+'.sigma.'+str(f),config.get(n+'.sigma','nan')))for n in LAYERS])
def _stat(v,w,grid):
 from experiment_math import weighted_statistics
 return weighted_statistics(v,w,grid)

def _qa(proof):
 rows=[]
 for face in proof['interfaces']:
  for region,r in face['regions'].items():
   value=r['total_normal_current'].get('normalized_L2')
   rows.append(dict(interface_depth_mm=face['interface_depth_mm'],region=region,normalized_L2=value,predeclared_numerical_limit=QA_LIMIT,passed=value is not None and value<=QA_LIMIT))
 return dict(status='all_numerical_flags_pass'if all(r['passed']for r in rows)else'numerical_flags_failed',rows=rows,
  scope='Proposed 5% independent gradient consistency QA; no physical accuracy, activation or safety threshold. Failure does not suppress raw results or alter criteria.')

def build(run,guard,*,declared_sha256=None,deadline_monotonic=None,include_max_direction=True):
 from experiment_math import _geometry,reconstruct_native_field,_maximum_direction
 import experiment_interfaces as iface
 run=Path(run).resolve();require(run==RUN and callable(guard),'Exact finite-owner run and guard');guard()
 pins=required_inputs();supplied=dict(declared_sha256 or{});used={}
 require(all(k not in supplied or supplied[k]==h for k,h in pins.items()),'Pinned comparator metadata unchanged')
 def read(path):
  guard();p=Path(path);require(p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<=64*1024**2 and(p.is_relative_to(run)or str(p)in pins),'Bounded actual declared file')
  raw=p.read_bytes();digest=sha(raw);require(digest==pins.get(str(p),supplied.get(str(p),digest)),'Native/source SHA mismatch');used[str(p)]=digest;return raw
 def js(p):return json.loads(read(p))
 def path(folder,name):
  ps=[p for p in(folder/name,folder/(name+'.gz'))if p.is_file()];require(len(ps)==1,'One actual file '+name);return ps[0]
 def decoded(p):
  r=read(p)
  if p.suffix=='.gz':
   with gzip.GzipFile(fileobj=io.BytesIO(r))as f:r=f.read(128*1024**2+1)
  require(len(r)<=128*1024**2,'Bounded native decode');return r
 def binary(folder,name,shape):
  r=decoded(path(folder,name));require(len(r)==math.prod(shape)*16,'Native exact complex128 length');a=np.frombuffer(r,dtype='<c16').reshape(shape);require(np.isfinite(a).all(),'Finite complex native array');return a
 folder=run/'bases'/CASE;meta=js(folder/'mesh-metadata.json');validation=js(folder/'validation.json');read(folder/'BASIS_COMPLETE')
 require(meta['cells']==351680 and meta['sc_cells']==2 and meta['h_xy_mm']==.625 and meta['frequencies_Hz']==[2000,2010]and meta['channels']==2,'Exact two-frequency SC2 mesh')
 for k,limit in GATES.items():require(0<=validation[k]<=limit,'Original native gate '+k)
 newconfig=_properties(read(run/'configs'/(CASE+'.properties')))
 for label in('material','contact'):
  receipt=run/(label+'-receipt.json'if label=='contact'else'material-input.json')
  require(Path(newconfig[label+'.input_path'])==receipt,'Exact run-local '+label+' receipt')
  supplied[str(receipt)]=newconfig[label+'.input_sha256']
 material_receipt=js(run/'material-input.json');contact_receipt=js(run/'contact-receipt.json')
 material_export=js(folder/'effective-materials.json')
 require(material_export['sigma_unit']=='S/m'and material_export['epsilon_r_unit']=='dimensionless'and material_export['gamma_unit']=='S/m'and
  material_export['epsilon0_F_m']==EPS0 and material_export['frequency_dependent_sigma_epsilon']is True and sorted(r['frequency_Hz']for r in material_export['rows'])==[2000,2010],'Actual two-frequency material lookup units and coverage')
 grid=np.loadtxt(io.BytesIO(decoded(path(folder,'grid.csv'))),delimiter=',',skiprows=1);require(grid.shape==(351680,5),'Exact grid');layer=grid[:,3].astype(int);geometry=_geometry(grid,meta)
 with np.load(io.BytesIO(read(HUMAN/'postprocess/scalars.npz')),allow_pickle=False)as a:
  weights={k:np.array(a[k+'_volume_weight_m3'],copy=True)for k in('total','target','surface_0_5','subsurface_5_10','remaining','off_target')};human_max=np.array(a['fundamental_maxTIS_2074_V_m'],copy=True)/A1
 oldsummary=js(LEGACY/'postprocess'/LCASE/'summary.json');square=next(c for c in oldsummary['conditions']if c['waveform']=='square_3h')
 with np.load(io.BytesIO(read(LEGACY/'postprocess'/LCASE/square['native_volume_archive'])),allow_pickle=False)as a:
  legacy_max=np.array(a['maxTIS'],copy=True)/A1
  for k,w in weights.items():require(np.array_equal(w,a['region_'+k+'_m3']),'Identical physical ROI masks across cached comparators')
 regions={**{n:weights['total']*(layer==i)for i,n in enumerate(LAYERS)},**weights,'surface_without_SC':weights['surface_0_5']*(layer!=0)}
 scenarios={};outarrays={};independent={};native_phi_consistency={};actual_material_rows=[];waveform_check=None
 analytic=iface.analytic_validation();require(analytic['passed'],'Predeclared 1e-10 analytic layered-slab/affine validation')
 for tag,base,case,freqs,cachedmax in(('human_2000_2010_sine',run,CASE,(2000,2010),None),('human_3000_3030_sine',HUMAN,HCASE,(3000,3030),human_max),('legacy_3000_3030_sine',LEGACY,LCASE,(3000,3030),legacy_max)):
  guard();basis=base/'bases'/case;config=_properties(read(base/'configs'/(case+'.properties')))
  if base!=run:
   oldgrid=np.loadtxt(io.BytesIO(decoded(path(basis,'grid.csv'))),delimiter=',',skiprows=1);require(np.array_equal(grid,oldgrid),'Exact comparator grid; no mapping');del oldgrid
  energy=np.zeros(len(grid));jenergy=np.zeros(len(grid));fields=[];density2=None;contactv2=None;currents2=np.zeros(2);losses=np.zeros(6);power=0.;spectral=[];area=None
  for channel,f in enumerate(freqs):
   guard();c=np.zeros(2,complex);c[channel]=1;gamma=_gamma(config,f);sigma=_sigma(config,f);require(np.isfinite(gamma).all()and np.all(gamma.real>0)and np.all(gamma.imag>0),'Actual finite positive material lookup')
   E=binary(basis,'field-'+str(f)+'.bin',(2,len(grid),3))[channel];fields.append(E);energy+=np.sum(abs(E)**2,axis=1)/2;jenergy+=np.sum(abs(gamma[layer,None]*E)**2,axis=1)/2
   contacts=np.genfromtxt(io.BytesIO(read(basis/('contacts-'+str(f)+'.csv'))),delimiter=',',names=True);area_=contacts['area_m2'];pads=contacts['pad'].astype(int)
   density=binary(basis,'density-'+str(f)+'.bin',(2,len(contacts)))[channel];current=binary(basis,'source-'+str(f)+'.bin',(2,2))@c;loss=np.einsum('i,kij,j->k',c.conj(),binary(basis,'loss-'+str(f)+'.bin',(6,2,2)),c)
   require(np.max(abs(loss.imag))<=1e-12 and np.all(loss.real>=-1e-12),'Real nonnegative actual native losses');p=float(.25*np.vdot(c,current).real);require(p>0 and abs(loss.real.sum()-p)<=2e-7*p,'Original driven power gate')
   balance=abs(np.sum(density*area_))/max(float(np.sum(abs(density)*area_)),1e-30);signal=np.asarray([np.sum(density[pads==i]*area_[pads==i])for i in range(2)]);cerr=float(np.max(abs(signal-current))/max(float(abs(current).max()),1e-30));require(max(balance,cerr)<=2e-6,'Original driven current gate')
   za=complex(float(config['z.'+str(f)+'.re']),float(config['z.'+str(f)+'.im']))
   if density2 is None:density2=np.zeros(len(contacts));contactv2=np.zeros(len(contacts));area=area_
   require(np.array_equal(area,area_),'Identical contact ordering/area');density2+=abs(density)**2/2;contactv2+=abs(density*za)**2/2;currents2+=abs(current)**2/2;losses+=loss.real;power+=p
   spectral.append(dict(frequency_Hz=f,source_basis_coefficients_real=c.real.tolist(),source_current_peak_A=dict(real=current.real.tolist(),imaginary=current.imag.tolist()),source_power_W=p,losses_W=loss.real.tolist(),KCL_relative_error=float(balance),current_relative_error=cerr))
   if base==run:
    exported=next(r['layers']for r in material_export['rows']if r['frequency_Hz']==f)
    require(len(exported)==4,'All four actual exporter layers')
    for i,item in enumerate(exported):
     require(item['name']==LAYERS[i]and item['sigma_S_m']==sigma[i]and item['epsilon_r']==float(config[LAYERS[i]+'.epsilon_r.'+str(f)])and item['measured']is False and
      math.isclose(item['gamma_real_S_m'],gamma[i].real,rel_tol=1e-14,abs_tol=1e-18)and math.isclose(item['gamma_imag_S_m'],gamma[i].imag,rel_tol=1e-14,abs_tol=1e-18),'Actual sigma/epsilon/gamma exporter arithmetic audit')
    phi=binary(basis,'potential-'+str(f)+'.bin',(2,len(grid)))[channel];metal=.5*c-50*current;reconstructed=reconstruct_native_field(phi,grid,geometry,gamma,contacts,metal,za);error=abs(E-reconstructed)
    native_phi_consistency[str(f)]=dict(passed=bool(np.all(error<=1e-8+2e-8*abs(reconstructed))),maximum_absolute_error_V_m=float(error.max()),scope='Same native half-face flux ABI/algebra only; not independent accuracy')
    common=iface.common_two_point_diagnostics(phi,grid,meta,gamma,guard);quadratic=iface.interface_diagnostics(phi,grid,meta,gamma,guard)
    independent[str(f)]=dict(common_two_point=common,nearest_up_to_three_point=quadratic,common_numerical_QA=_qa(common),up_to_three_point_numerical_QA=_qa(quadratic))
    actual_material_rows.extend(dict(frequency_Hz=f,layer=n,sigma_S_m=float(sigma[i]),epsilon_r=float(gamma[i].imag/(2*math.pi*f*EPS0)),gamma_S_m=dict(real=float(gamma[i].real),imaginary=float(gamma[i].imag)))for i,n in enumerate(LAYERS))
  rms=np.sqrt(energy)
  if base==run:
   cell=int(np.argmin(np.sum((grid[:,:3]-np.asarray([0,0,20]))**2,axis=1)));t=np.arange(8192)/8192*.1
   waveform=sum(np.real(np.exp(2j*math.pi*f*t)[:,None]*v[cell][None,:])for f,v in zip(freqs,fields));numerical=np.sqrt(np.mean(waveform**2,axis=0));analytic_rms=np.sqrt(sum(abs(v[cell])**2/2 for v in fields))
   waveform_check=dict(native_cell_index=cell,actual_xyz_mm=grid[cell,:3].tolist(),samples=8192,window_seconds=.1,temporal_RMS_V_m=numerical.tolist(),analytic_RMS_V_m=analytic_rms.tolist(),passed=bool(np.all(abs(numerical-analytic_rms)<=1e-10+1e-10*analytic_rms)),scope='Actual native two-frequency local field waveform; not differential probe voltage or hardware validation')
  if cachedmax is None:
   if include_max_direction:maximum,winner,maxproof=_maximum_direction(fields[0],fields[1],guard,deadline_monotonic)
   else:maximum=None;maxproof=dict(status='not_run_caller_excluded')
  else:maximum=cachedmax;maxproof=dict(status='reused_exact_coefficient_scaling',factor=1/A1,scope='Cached square3h fundamental2074 max divided by a1; no redundant angular calculation; full RMS recomposed sine-only')
  jvolume=np.sqrt(jenergy);skinweights=weights['total']*(layer<=1);jskin=_stat(jvolume,skinweights,grid);jrms=np.sqrt(density2);order=np.argsort(jrms,kind='stable');j95=float(jrms[order[min(int(np.searchsorted(np.cumsum(area[order]),.95*area.sum(),side='left')),len(order)-1)]])
  electrical=dict(source_Vpp_each=1.,source_current_RMS_by_output_A=np.sqrt(currents2).tolist(),sum_output_current_RMS_A_bookkeeping=float(np.sqrt(currents2).sum()),source_power_W=power,
   layers_power_W={n:float(losses[i])for i,n in enumerate(LAYERS)},SC_power_W=float(losses[0]),skin_power_W=float(losses[:2].sum()),contact_power_W=float(losses[4]),source_resistor_power_W=float(losses[5]),
   contact_normal_J_RMS_max_A_m2=float(jrms.max()),contact_normal_J_RMS_P95_A_m2=j95,contact_voltage_RMS_max_V=float(np.sqrt(contactv2.max())),skin_vector_J_RMS_max_A_m2=jskin['max'],skin_vector_J_RMS_P95_A_m2=jskin['p95'])
  stats={r:dict(total_E_RMS_V_m=_stat(rms,w,grid),**({'fundamental_maxTIS_2074_V_m':_stat(maximum,w,grid)}if maximum is not None else{}))for r,w in regions.items()}
  scenarios[tag]=dict(frequencies_Hz=list(freqs),waveform='two-tone sine',coefficient_convention='c=[1,0] and[0,1],0.5Vpeak basis→1Vpp each; RMS and two-tone directional amplitude metrics are invariant to common per-tone phase rotations; reference waveform phase is not claimed identical',statistics=stats,electrical=electrical,spectrum=spectral,maximum_direction_search=maxproof)
  if base==run:
   outarrays.update(total_E_RMS_V_m=rms,total_Jtotal_RMS_A_m2=jvolume)
   if maximum is not None:outarrays['fundamental_maxTIS_2074_V_m']=maximum
   for axis in range(3):outarrays['xyz'[axis]+'_TIS_V_m']=2*np.minimum(abs(fields[0][:,axis]),abs(fields[1][:,axis]))
  del fields
 new=scenarios['human_2000_2010_sine'];normalizations={}
 burdens=('contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V','skin_vector_J_RMS_max_A_m2','skin_vector_J_RMS_P95_A_m2')
 for tag,ref in scenarios.items():
  if ref is new:continue
  a=new['electrical'];b=ref['electrical'];caps={k:b[k]/max(a[k],1e-30)for k in burdens};caps.update({k:math.sqrt(b[k]/max(a[k],1e-30))for k in('SC_power_W','skin_power_W','contact_power_W')})
  scales=dict(same_Vpp=1.,same_sum_output_RMS_current_bookkeeping=b['sum_output_current_RMS_A_bookkeeping']/a['sum_output_current_RMS_A_bookkeeping'],same_source_real_power=math.sqrt(b['source_power_W']/a['source_power_W']),joint_eight_numerical_burden_caps=min(caps.values()))
  rows=[]
  for name,s in scales.items():
   target=new['statistics']['target'];am=target.get('fundamental_maxTIS_2074_V_m',{})
   rows.append(dict(name=name,amplitude_scale=s,source_Vpp_each=s,target_AM_mean_V_m=am.get('mean',0)*s if am else None,target_AM_P10_V_m=am.get('p10',0)*s if am else None,target_RMS_mean_V_m=target['total_E_RMS_V_m']['mean']*s,
    electrical={**{k:(v*s*s if k.endswith('_power_W')or k=='source_power_W'else v*s)for k,v in a.items()if isinstance(v,(int,float))and k!='source_Vpp_each'},
     'layers_power_W':{k:v*s*s for k,v in a['layers_power_W'].items()},'source_current_RMS_by_output_A':[v*s for v in a['source_current_RMS_by_output_A']]},active_joint_cap=min(caps,key=caps.get)if name=='joint_eight_numerical_burden_caps'else None))
  normalizations[tag]=dict(rows=rows,joint_cap_scales=caps,interpretation='Comparator-derived numerical electrical burden caps, not human limits. Equal current/power/joint burden are distinct comparisons; sum RMS output currents is bookkeeping, not net common-ground current.')
 analytic_SC=[]
 cfg=_properties(read(run/'configs'/(CASE+'.properties')))
 for f in(2000,2010):
  gamma=_gamma(cfg,f)[0];z14=14e-6/gamma;z100=100e-6/gamma;analytic_SC.append(dict(frequency_Hz=f,Zarea_14um_ohm_m2=dict(real=z14.real,imaginary=z14.imag),Zarea_100um_ohm_m2=dict(real=z100.real,imaginary=z100.imag),ratio=.14,scope='Analytic bulk Zarea=t/gamma only; no new geometry, circuit rebalance, contact calibration or PDE'))
 summary=dict(schema='task1-minimum-sine-frequency-comparison-v1',status='calculated_unadopted',case_id=CASE,run_id=run.name,actual_new_native_conditions=1,actual_new_RHS=4,native_gates=dict(values=validation,thresholds=GATES),
  scenarios=scenarios,normalizations=normalizations,actual_material_lookup=actual_material_rows,material_receipt=material_receipt,contact_receipt=contact_receipt,actual_native_waveform_check=waveform_check,independent_interface_diagnostics=independent,phi_to_stored_E_consistency=native_phi_consistency,analytic_validation=analytic,SC_14_vs_100_um_analytic=analytic_SC,
  reference_3k_interface_diagnostics=dict(human_reused={k:v for k,v in js(HUMAN/'postprocess/summary.json')['independent_interface_potential_gradient_diagnostics'].items()if k in('3000','3030')},legacy='Existing canonical diagnostics retained; no old phi re-evaluation'),
  model=dict(radius_mm=25,layers_mm=[.1,5,5,15],pads=4,outputs=2,return_topology='pad2and3 commonGND',source_resistance_ohm=50,grid_cells=len(grid),sc_cells=2),
  coordinate_system='Surface z=0,+z depth; x/y horizontal mm',ROI='Original same-grid fractional r<=5,z15–20; surface0–5; surface_without_SC excludes SC; exact mask weights reused',
  metric_separation='Two sine tones only. Carrier RMS and fundamental directional modulation distinct; no neural activation or safety inference. Native probe Vpp not newly evaluated.',
  validation_holds=dict(full_SC_XY_bulk_edge_contact_convergence=False,experimental_validation=False,material_calibration=False,thoracoabdominal_specificity=False,old_XY_surface_contact_failure_retained=True,new_best_candidate_adopted=False),input_sha256=used)
 outarrays.update({k+'_volume_weight_m3':v for k,v in regions.items()});guard();return dict(summary=summary,arrays=outarrays)
