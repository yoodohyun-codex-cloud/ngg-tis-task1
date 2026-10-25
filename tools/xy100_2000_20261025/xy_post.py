"""Single-carrier XY refinement diagnostic. Import performs no data read/solve."""
from __future__ import annotations
import gzip,hashlib,io,json,math
from pathlib import Path
import numpy as np
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-xy100-2000-20261025/source')
RUN=Path('/workspace/task1-xy100-2000-20261025-run-r2')
CASE='baseline-square15-human-sine2000-xy100'
COARSE=Path('/workspace/task1-experiment-2000-2010-20261025-run')
COARSE_CASE='baseline-square15-human-sine2000-2010-xy80'
LAYERS=('sc','dermis','fat','muscle');EPS0=8.8541878128e-12;FREQUENCY=2000
GATES=dict(max_residual=2e-7,max_power_error=2e-7,max_current_error=2e-6,max_area_relative_error=1e-10,max_interface_normal_current_relative_error=2e-7)
QA_LIMIT=.05
MATERIAL_SHA='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
CONTACT_SHA='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
ADJACENCY_PERCENT={
 'target.E_carrier_RMS.mean':1,'target.E_carrier_RMS.p10':1,
 'contact_normal_J_RMS_max_A_m2':5,'contact_normal_J_RMS_P95_A_m2':5,'contact_voltage_RMS_max_V':5,
 'source_power_W':2,'contact_power_W':2,'source_resistor_power_W':2,'SC_power_W':2,'skin_power_W':2,
 'dermis_power_W':2,'fat_power_W':2,'muscle_power_W':2,
}

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def _properties(raw):return {k.strip():v.strip()for line in raw.decode().splitlines()if '='in line and not line.lstrip().startswith(('#','!'))for k,v in[line.split('=',1)]}
def required_inputs():
 """Small completed-coarse metadata and immutable source pins only."""
 refs={}
 for name in('native-sha256.json','postprocess/summary.json','postprocess/artifact-sha256.json'):
  p=COARSE/name;r=p.read_bytes();require(len(r)<4*1024**2,'Bounded completed coarse metadata');refs[str(p)]=sha(r)
 manifest=json.loads((COARSE/'native-sha256.json').read_bytes());refs.update(manifest['files'])
 artifacts=json.loads((COARSE/'postprocess/artifact-sha256.json').read_bytes())
 summaryraw=(COARSE/'postprocess/summary.json').read_bytes();require(sha(summaryraw)==artifacts['summary.json']['SHA256'],'Actual coarse summary identity')
 require(json.loads(summaryraw)['actual_new_RHS']==4,'Existing two-frequency run completed')
 for name in('material-input.json','contact-receipt.json'):
  config=_properties((COARSE/'configs'/(COARSE_CASE+'.properties')).read_bytes());label='material'if name.startswith('material')else'contact'
  refs[str(COARSE/name)]=config[label+'.input_sha256']
 for name in('selectivity_volume.py','explore_tis.py'):
  p=ROOT/'tis-java'/name;refs[str(p)]=sha(p.read_bytes())
 return refs

def numerical_qa(proof):
 rows=[]
 for face in proof['interfaces']:
  for region,r in face['regions'].items():
   value=r['total_normal_current'].get('normalized_L2')
   rows.append(dict(interface_depth_mm=face['interface_depth_mm'],region=region,normalized_L2=value,limit=QA_LIMIT,passed=value is not None and value<=QA_LIMIT))
 return dict(status='all_numerical_flags_pass'if all(r['passed']for r in rows)else'numerical_flags_failed',rows=rows,
  interpretation='Predeclared 5% independent-gradient screening flag only; not physical accuracy, activation or safety. Flag failure never suppresses result export or changes the criterion.')

def adjacent_checks(old,new):
 rows=[]
 def check(name,before,after,tol,unit):
  relative=abs(after-before)/max(abs(before),1e-30)
  rows.append(dict(metric=name,coarse=before,fine=after,absolute_difference=abs(after-before),relative_difference=relative,limit=tol,units=unit,passed=relative<=tol))
 for k in('mean','p10'):check('target.E_carrier_RMS.'+k,old['statistics']['target']['E_carrier_RMS_V_m'][k],new['statistics']['target']['E_carrier_RMS_V_m'][k],.01,'V/m')
 for k in('contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2'):check(k,old['electrical'][k],new['electrical'][k],.05,'A/m2')
 check('contact_voltage_RMS_max_V',old['electrical']['contact_voltage_RMS_max_V'],new['electrical']['contact_voltage_RMS_max_V'],.05,'V')
 for k in('source_power_W','contact_power_W','source_resistor_power_W','SC_power_W','skin_power_W'):check(k,old['electrical'][k],new['electrical'][k],.02,'W')
 for n in LAYERS[1:]:check(n+'_power_W',old['electrical']['layers_power_W'][n],new['electrical']['layers_power_W'][n],.02,'W')
 require({r['metric']:r['limit']*100 for r in rows}==ADJACENCY_PERCENT,'Exact preregistered adjacency metric names and thresholds')
 return dict(all_passed=all(r['passed']for r in rows),rows=rows,full_convergence_validated=False,
  interpretation='XY0.625→0.5 one-carrier adjacency only; 1% target mean/P10,5% contact Jmax/J95/contact voltage,2% individual powers. Independent 5% screening is separate; any failure prevents adoption.')

def independent_comparison(coarse,fine):
 rows=[]
 for key in('common_two_point','nearest_up_to_three_point'):
  old=coarse[key];new=fine[key]
  for oldface in old['interfaces']:
   newface=next(f for f in new['interfaces']if math.isclose(f['interface_depth_mm'],oldface['interface_depth_mm'],rel_tol=0,abs_tol=1e-9))
   for scope in('all','interior','staircase_periphery'):
    a=oldface['regions'][scope]['total_normal_current']['normalized_L2'];b=newface['regions'][scope]['total_normal_current']['normalized_L2']
    rows.append(dict(order=key,interface_depth_mm=oldface['interface_depth_mm'],scope=scope,coarse_normalized_L2=a,fine_normalized_L2=b,absolute_change=b-a,
     numerical_limit=QA_LIMIT,coarse_passed=a<=QA_LIMIT,fine_passed=b<=QA_LIMIT,comparison_interior_radius_mm=23.75))
 return dict(rows=rows,region_definition='Same physical all /r<=23.75mm /r>23.75mm at both XY meshes; no comparison against changing native24mm fine cutoff',physical_accuracy_claim=False)

def build(run,guard,*,declared_sha256=None,deadline_monotonic=None,include_max_direction=False):
 from xy_math import native_geometry,reconstruct_native_field,weighted_statistics
 import xy100_interfaces as iface
 from selectivity_volume import native_region_weights
 run=Path(run).resolve();require(run==RUN and callable(guard),'Exact sole-owner run');guard();pins=required_inputs();provided=dict(declared_sha256 or{});used={}
 require(all(k not in provided or provided[k]==h for k,h in pins.items()),'Coarse comparator pins unchanged')
 def read(p):
  guard();p=Path(p);require(p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<=64*1024**2 and(p.is_relative_to(run)or str(p)in pins),'Bounded actual declared file')
  r=p.read_bytes();h=sha(r);require(h==pins.get(str(p),provided.get(str(p),h)),'Actual source/native SHA mismatch');used[str(p)]=h;return r
 def js(p):return json.loads(read(p))
 def path(folder,name):
  ps=[p for p in(folder/name,folder/(name+'.gz'))if p.is_file()];require(len(ps)==1,'One actual file '+name);return ps[0]
 def decoded(p):
  r=read(p)
  if p.suffix=='.gz':
   with gzip.GzipFile(fileobj=io.BytesIO(r))as f:r=f.read(128*1024**2+1)
  require(len(r)<=128*1024**2,'Bounded native decode');return r
 def binary(folder,name,shape):
  r=decoded(path(folder,name));require(len(r)==math.prod(shape)*16,'Exact native little-endian complex128 length');a=np.frombuffer(r,dtype='<c16').reshape(shape);require(np.isfinite(a).all(),'Finite raw complex arrays');return a
 coarse_summary=js(COARSE/'postprocess/summary.json');old_independent=coarse_summary['independent_interface_diagnostics']['2000'];analytic=iface.analytic_validation();require(analytic['passed'],'Fixed1e-10 analytic complex slab and affine contracts')
 scenarios={};new_arrays={};new_independent=None;selfconsistency=None;material_audit=None;material_receipt=None;contact_receipt=None;waveproof=None
 for tag,base,case,expected_h in(('XY100',run,CASE,.5),('XY80',COARSE,COARSE_CASE,.625)):
  guard();folder=base/'bases'/case;meta=js(folder/'mesh-metadata.json');validation=js(folder/'validation.json');read(folder/'BASIS_COMPLETE')
  require(meta['h_xy_mm']==expected_h and meta['sc_cells']==2 and meta['bulk_layer_counts']==[14,14,40]and meta['channels']==2 and meta['source_resistance_ohm']==50 and meta['source_peak_V']==.5 and meta['phasor_convention']=='peak,+jomega_t'and 2000 in meta['frequencies_Hz'],'Exact preserved circuit/layers/phasor and requested XY')
  if base==run:require(meta['frequencies_Hz']==[2000],'Exactly one new carrier; no hidden 2010 solve')
  for k,limit in GATES.items():require(0<=validation[k]<=limit,'Original native gate '+k)
  grid=np.loadtxt(io.BytesIO(decoded(path(folder,'grid.csv'))),delimiter=',',skiprows=1);n=len(grid);require(grid.shape==(n,5)and n==meta['cells']and n<=800000,'Owner-pinned finite native cell count')
  layer=grid[:,3].astype(int);geometry=native_geometry(grid,meta)
  cfg=_properties(read(base/'configs'/(case+'.properties')))
  sigma=np.asarray([float(cfg[k+'.sigma.2000'])for k in LAYERS]);epsilon=np.asarray([float(cfg[k+'.epsilon_r.2000'])for k in LAYERS]);gamma=sigma+2j*math.pi*2000*EPS0*epsilon
  require(np.isfinite(gamma).all()and np.all(sigma>0)and np.all(epsilon>0),'Finite positive actual per-frequency material')
  if base==run:
   oldcfg=_properties(read(COARSE/'configs'/(COARSE_CASE+'.properties')))
   require(int(cfg['validation.expected_cells'])==n,'Owner-preregistered expected native cell count')
   require(all(cfg[k+'.'+t+'.2000']==oldcfg[k+'.'+t+'.2000']for k in LAYERS for t in('sigma','epsilon_r')),'No material reevaluation or model changes')
   require(all(cfg['z.2000.'+t]==oldcfg['z.2000.'+t]for t in('re','im')),'No contact reevaluation')
   for label,name in(('material','material-input.json'),('contact','contact-receipt.json')):
    receipt=run/name;require(Path(cfg[label+'.input_path'])==receipt,'Exact run-local receipt path');provided[str(receipt)]=cfg[label+'.input_sha256']
    require(cfg[label+'.input_sha256']==oldcfg[label+'.input_sha256']==(MATERIAL_SHA if label=='material'else CONTACT_SHA),'Exact unchanged registered receipt SHA')
   material_receipt=js(run/'material-input.json');contact_receipt=js(run/'contact-receipt.json')
   lookup=js(folder/'effective-materials.json');row=next(r for r in lookup['rows']if r['frequency_Hz']==2000)
   require(len(lookup['rows'])==1 and lookup['epsilon0_F_m']==EPS0 and lookup['sigma_unit']=='S/m'and lookup['epsilon_r_unit']=='dimensionless'and lookup['gamma_unit']=='S/m','Actual one-carrier exporter lookup units')
   for i,item in enumerate(row['layers']):require(item['name']==LAYERS[i]and item['sigma_S_m']==sigma[i]and item['epsilon_r']==epsilon[i]and item['measured']is False and math.isclose(item['gamma_real_S_m'],gamma[i].real,rel_tol=1e-14,abs_tol=1e-18)and math.isclose(item['gamma_imag_S_m'],gamma[i].imag,rel_tol=1e-14,abs_tol=1e-18),'Actual material gamma audit')
   material_audit=dict(status='passed_config_arithmetic_only',rows=row['layers'])
  declared=dict(meta,radius_mm=25,layer_counts=[2,14,14,40],geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001)
  weights,roi_receipt=native_region_weights({k:grid[:,i]for i,k in enumerate(('x_mm','y_mm','z_mm','layer','volume_m3'))},declared,deadline_monotonic=deadline_monotonic)
  regions={**{k:weights['total']*(layer==i)for i,k in enumerate(LAYERS)},**weights,'surface_without_SC':weights['surface_0_5']*(layer!=0)}
  E=binary(folder,'field-2000.bin',(2,n,3))[0];rms=np.linalg.norm(E,axis=1)/math.sqrt(2);jt=np.linalg.norm(gamma[layer,None]*E,axis=1)/math.sqrt(2);jc=np.linalg.norm(sigma[layer,None]*E,axis=1)/math.sqrt(2)
  contacts=np.genfromtxt(io.BytesIO(read(folder/'contacts-2000.csv')),delimiter=',',names=True);area=contacts['area_m2'];pads=contacts['pad'].astype(int);density=binary(folder,'density-2000.bin',(2,len(contacts)))[0]
  c=np.asarray([1.,0.],complex);current=binary(folder,'source-2000.bin',(2,2))@c;loss=np.einsum('i,kij,j->k',c.conj(),binary(folder,'loss-2000.bin',(6,2,2)),c);power=float(.25*np.vdot(c,current).real)
  require(power>0 and np.max(abs(loss.imag))<=1e-12 and np.all(loss.real>=-1e-12)and abs(loss.real.sum()-power)<=2e-7*power,'Driven native real-power gate')
  balance=abs(np.sum(density*area))/max(float(np.sum(abs(density)*area)),1e-30);active=np.asarray([np.sum(density[pads==i]*area[pads==i])for i in range(2)]);cerr=float(np.max(abs(active-current))/max(float(abs(current).max()),1e-30));require(max(balance,cerr)<=2e-6,'Driven current/KCL gate')
  za=complex(float(cfg['z.2000.re']),float(cfg['z.2000.im']));jrms=abs(density)/math.sqrt(2);order=np.argsort(jrms,kind='stable');j95=float(jrms[order[min(int(np.searchsorted(np.cumsum(area[order]),.95*area.sum(),side='left')),len(order)-1)]])
  jskin=weighted_statistics(jt,weights['total']*(layer<=1),grid)
  electrical=dict(source_Vpp_each_active=1.,output_RMS_current_A=(abs(current)/math.sqrt(2)).tolist(),sum_output_current_RMS_A_bookkeeping=float(abs(current).sum()/math.sqrt(2)),source_power_W=power,
   layers_power_W={k:float(loss.real[i])for i,k in enumerate(LAYERS)},SC_power_W=float(loss.real[0]),skin_power_W=float(loss.real[:2].sum()),contact_power_W=float(loss.real[4]),source_resistor_power_W=float(loss.real[5]),
   contact_normal_J_RMS_max_A_m2=float(jrms.max()),contact_normal_J_RMS_P95_A_m2=j95,contact_voltage_RMS_max_V=float(abs(density*za).max()/math.sqrt(2)),skin_vector_J_RMS_max_A_m2=jskin['max'],skin_vector_J_RMS_P95_A_m2=jskin['p95'])
  scalars=dict(E_carrier_RMS_V_m=rms,Jtotal_carrier_RMS_A_m2=jt,Jconduction_carrier_RMS_A_m2=jc)
  statistics={r:{k:weighted_statistics(v,w,grid)for k,v in scalars.items()}for r,w in regions.items()}
  if base==run:
   phi=binary(folder,'potential-2000.bin',(2,n))[0];metal=.5*c-50*current;reconstructed=reconstruct_native_field(phi,grid,geometry,gamma,contacts,metal,za);error=abs(E-reconstructed)
   selfconsistency=dict(passed=bool(np.all(error<=1e-8+2e-8*abs(reconstructed))),maximum_absolute_difference_V_m=float(error.max()),rtol=2e-8,atol=1e-8,scope='Shared native half-face algebra/ABI only; not independent accuracy')
   common=iface.common_two_point_diagnostics(phi,grid,meta,gamma,guard);three=iface.interface_diagnostics(phi,grid,meta,gamma,guard)
   fixedcommon=iface.common_two_point_diagnostics(phi,grid,meta,gamma,guard,interior_radius_mm=23.75);fixedthree=iface.interface_diagnostics(phi,grid,meta,gamma,guard,interior_radius_mm=23.75)
   new_independent=dict(native_grid_masks=dict(common_two_point=common,nearest_up_to_three_point=three,common_QA=numerical_qa(common),up_to_three_QA=numerical_qa(three)),
    fixed_coarse_physical_masks=dict(common_two_point=fixedcommon,nearest_up_to_three_point=fixedthree,common_QA=numerical_qa(fixedcommon),up_to_three_QA=numerical_qa(fixedthree)),
    mask_note='Default r<=25-2h changes interior23.75→24mm. Fixed23.75mm diagnostics are also reported so periphery comparisons preserve the physical region.')
   cell=int(np.argmin(np.sum((grid[:,:3]-np.asarray([0,0,20]))**2,axis=1)));t=np.arange(8192)/8192/2000;wave=np.real(np.exp(2j*math.pi*2000*t)[:,None]*E[cell]);actual=np.sqrt(np.mean(wave**2,axis=0));expected=abs(E[cell])/math.sqrt(2)
   waveproof=dict(native_cell_index=cell,actual_xyz_mm=grid[cell,:3].tolist(),temporal_RMS=actual.tolist(),analytic_RMS=expected.tolist(),passed=bool(np.all(abs(actual-expected)<=1e-10+1e-10*expected)),scope='One actual carrier waveform, no TIS modulation')
   new_arrays={**scalars,**{k+'_volume_weight_m3':w for k,w in regions.items()}}
  scenarios[tag]=dict(h_xy_mm=expected_h,grid_cells=n,physical_ROI_receipt=roi_receipt,statistics=statistics,electrical=electrical,native_validation=validation,
   current_KCL_relative_error=float(balance),output_current_relative_error=cerr,source_peak_current_A=dict(real=current.real.tolist(),imaginary=current.imag.tolist()),
   drive='2000Hz c=[1,0]: output0 high-Z1Vpp, output1 ideal0V behind50Ω; four pads/two outputs with common-ground pads2and3. This is not a one-pair/two-pad stimulus.')
 fine=scenarios['XY100'];coarse=scenarios['XY80'];a=fine['electrical'];b=coarse['electrical'];linear=('contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V','skin_vector_J_RMS_max_A_m2','skin_vector_J_RMS_P95_A_m2')
 caps={k:b[k]/max(a[k],1e-30)for k in linear};caps.update({k:math.sqrt(b[k]/max(a[k],1e-30))for k in('SC_power_W','skin_power_W','contact_power_W')})
 scales=dict(same_Vpp=1.,same_sum_output_RMS_current_bookkeeping=b['sum_output_current_RMS_A_bookkeeping']/a['sum_output_current_RMS_A_bookkeeping'],same_source_real_power=math.sqrt(b['source_power_W']/a['source_power_W']),joint_eight_comparator_burden_caps=min(caps.values()))
 normalized=[]
 for name,s in scales.items():
  target=fine['statistics']['target']['E_carrier_RMS_V_m'];normalized.append(dict(name=name,amplitude_scale=s,source_Vpp_active=s,target_mean_carrier_RMS_V_m=target['mean']*s,target_P10_carrier_RMS_V_m=target['p10']*s,
   electrical={**{k:(v*s*s if k.endswith('_power_W')or k=='source_power_W'else v*s)for k,v in a.items()if isinstance(v,(int,float))and k!='source_Vpp_each_active'},'layers_power_W':{k:v*s*s for k,v in a['layers_power_W'].items()},'output_RMS_current_A':[v*s for v in a['output_RMS_current_A']]},active_joint_cap=min(caps,key=caps.get)if name.startswith('joint')else None))
 summary=dict(schema='task1-xy100-single2000-diagnostic-post-v1',status='calculated_diagnostic_unadopted',case_id=CASE,run_id=run.name,actual_new_native_conditions=1,actual_new_RHS=2,
  frequency_Hz=2000,scenarios=scenarios,adjacent_XY_checks=adjacent_checks(coarse,fine),independent_interface_diagnostics=dict(coarse_reused=old_independent,fine=new_independent),
  predeclared_independent_screening=dict(normalized_L2_limit=QA_LIMIT,physical_accuracy_claim=False,activation_or_safety_threshold=False,failures_preserved=True),
  independent_same_physical_region_comparison=independent_comparison(old_independent,new_independent['fixed_coarse_physical_masks']),
  phi_to_stored_E_selfconsistency=selfconsistency,independent_analytic_validation=analytic,actual_native_waveform_check=waveproof,actual_material_audit=material_audit,material_receipt=material_receipt,contact_receipt=contact_receipt,
  normalizations=normalized,joint_comparator_burden_scales=caps,normalization_interpretation='Different comparisons. Sum of output RMS currents is bookkeeping, not net common-ground current. Joint eight caps derive only from the coarse comparator; not human safety limits.',
  metric_separation='Single carrier E RMS and Jtotal/Jconduction RMS only. No second frequency was solved; no TIS modulation, beat or directional AM is computed or inferred.',
  coordinate_system='Top z0,+z depth; x/y horizontal mm; D50 and0.1/5/5/15mm layers fixed; ROI r<=5mm,z15–20; original128-square fractional boundary algorithm, no cell-count ROI or analytic-volume renormalization',
  validation_holds=dict(full_SC_XY_bulk_edge_contact_convergence=False,experimental_validation=False,material_or_anatomic_calibration=False,old_XY_surface_contact_failure_retained=True,candidate_adopted=False,independent_QA_pass_does_not_prove_accuracy=True),input_sha256=used)
 guard();return dict(summary=summary,arrays=new_arrays)
