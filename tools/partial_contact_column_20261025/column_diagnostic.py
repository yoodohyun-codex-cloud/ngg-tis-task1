"""Finite partial-contact column mechanism test; ZERO phantom/native/CEM PDE.

No IO, masks, counts or numerical research work is evaluated on import.
The sole owner prepares/publishes this spec before invoking build under its
existing locks/resources. ΔV=1Vpeak is a2Vpp toy, not the actual1Vpp/50ohm case.
"""
from __future__ import annotations
import csv,hashlib,io,json,math,time
from pathlib import Path

ROOT=Path('/workspace/ngg-tis-task1')
COARSE=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run')
CASE='baseline-square15-human-sine2000-sc8-vs19uniform-bulk19-18-56-xy100'
CONFIG=COARSE/'configs'/(CASE+'.properties')
FINE=Path('/dev/shm/task1-layer-dtn-xy102-cem-20261025-run')
CONFIG_SHA='a20334ff9788323b065c89968cd18d764e813beb4017879bdc390f19a4db6445'
MATERIAL_SHA='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
CONTACT_SHA='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
COARSE_MASK_SHA='884d3bc2537bc88d87a82bffcd735a197c48afda02485573ec27b80469b688ca'
FINE_MASK_SHA='04ef856c91caac24557892a46d17447af71ee12d647dfa2fa01fa00af4c7e1c7'
FINE_MASK_RECEIPT_SHA='90fd7c33836314c2f4a56b7316df75e2ceb934faf033731bbc1793bb3dbcd3db'
FINE_COMMIT='d2456af62d0686e06555d9e6664ee5d3504d8c64'
FINE_SOURCE_COMMIT='6e5e4de75d9330a60e0eb1340497c9be8318b64f'
FINE_COMPARISON_SHA='29b0b4d505b770fb51e650385c03d03733b2808db5d517d9e6f0377e31165b7e'
EPS0=8.8541878128e-12
PLAN=dict(frequency_Hz=2000,SC_thickness_m=.0001,DeltaV_peak_V=1.,DeltaV_Vpp=2.,
 contact_impedance_scale_factors=[1.,1000.,100000.],masks=['COARSE_XY100','FINE_XY102'],
 toy_conditions=1,fixed_contact_scales=3,new_phantom_PDE=0,new_CEM_conditions=0,new_CEM_RHS=0,
 finite_timeout_seconds=60,CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,
 model_uniform='Each contacted pixel has one uniform tissue top potential and fullh² independent SC-column admittance; contact occupiesA=f*h²',
 model_area_resolved='Independent SCcolumn only under actualA, uniform bottomDirichlet; NO lateral spread; analytical comparison, NOT true3D reference',
 boundary='Each toy column has metal1Vpeak and SC-bottom0V; pad IDs index geometry only, no actualground/source topology/50ohm network',
 formula_uniform='I=h²*Y*f/(f+Y*zA)*DeltaV; J=Y*DeltaV/(f+Y*zA)',
 formula_area_resolved='I=A*Y/(1+Y*zA)*DeltaV; J=Y*DeltaV/(1+Y*zA)',
 fraction_roundoff_allowance=1e-10,area_relative_gate=1e-10,analytic_relative_gate=1e-10,
 original_contact_input_changed=False,model_correction_applied=False,candidate_adopted=False)

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pair(z):return dict(real=float(z.real),imaginary=float(z.imag))
def finite(z):return math.isfinite(complex(z).real)and math.isfinite(complex(z).imag)
def _read(path):
 p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Bounded regular metadata/mask input: '+str(p));return p.read_bytes()
def properties(raw):return{k.strip():v.strip()for line in raw.decode().splitlines()if '='in line and not line.lstrip().startswith(('#','!'))for k,v in[line.split('=',1)]}
def check(guard,deadline):guard();require(deadline is None or time.monotonic()<deadline,'Finite60second column diagnostic deadline')
def _mask_definitions():
 cfg=properties(_read(CONFIG))
 return[dict(id='COARSE_XY100',path=cfg['mask.path'],SHA256=COARSE_MASK_SHA,nx=100,h_m=.0005),dict(id='FINE_XY102',path=str(FINE/'fine-mask.csv'),SHA256=FINE_MASK_SHA,nx=102,h_m=.05/102)]

def required_inputs():
 """Owner-only small metadata/mask reads; no actual fields/eigencache reads."""
 paths=[CONFIG,COARSE/'material-input.json',COARSE/'contact-receipt.json',FINE/'fine-mask.csv',FINE/'fine-mask-receipt.json',FINE/'spec.json',FINE/'comparison-summary.json',FINE/'reference-summary.json',FINE/'receipt.json',FINE/'result-publication/result-publication.json',FINE/'source-publication/result-publication.json']
 refs={str(p):sha(_read(p))for p in paths}
 require(refs[str(CONFIG)]==CONFIG_SHA and refs[str(COARSE/'material-input.json')]==MATERIAL_SHA and refs[str(COARSE/'contact-receipt.json')]==CONTACT_SHA,'Unchanged verified actual material/contact source inputs')
 require(refs[str(FINE/'fine-mask.csv')]==FINE_MASK_SHA and refs[str(FINE/'fine-mask-receipt.json')]==FINE_MASK_RECEIPT_SHA and refs[str(FINE/'comparison-summary.json')]==FINE_COMPARISON_SHA,'Exact published fine mask/failed comparison')
 for definition in _mask_definitions():require(sha(_read(definition['path']))==definition['SHA256'],'Exact previously published mask');refs[definition['path']]=definition['SHA256']
 pub=json.loads(_read(FINE/'result-publication/result-publication.json'));src=json.loads(_read(FINE/'source-publication/result-publication.json'))
 require(pub['status']=='published_readback_verified'and pub['commit']==FINE_COMMIT and src['status']=='published_readback_verified'and src['commit']==FINE_SOURCE_COMMIT,'Actual fine solve/source full publication prerequisites')
 for receipt,target,digest in((pub,'data-native/cloud-layer-dtn-xy102-cem-20261025/comparison-summary.json',FINE_COMPARISON_SHA),(src,'data-native/cloud-layer-dtn-xy102-cem-20261025/fine-mask.csv',FINE_MASK_SHA),(src,'data-native/cloud-layer-dtn-xy102-cem-20261025/fine-mask-receipt.json',FINE_MASK_RECEIPT_SHA)):
  row=receipt['files'][target];require(row['SHA256']==digest and row['readback_passed']is True,'Published complete-SHA evidence: '+target)
 return refs

def _load_mask(definition):
 raw=_read(definition['path']);require(sha(raw)==definition['SHA256'],'Immutable actual mask bytes');h2=definition['h_m']**2;rows=[];seen=set()
 for source in csv.DictReader(io.StringIO(raw.decode())):
  pad=int(source['pad']);i=int(source['i']);j=int(source['j']);area=float(source['area_m2']);fraction=area/h2
  require(pad in(0,1,2,3)and 0<=i<definition['nx']and 0<=j<definition['nx']and(i,j)not in seen,'Unique in-range canonical mask cell; disjoint pads');seen.add((i,j))
  require(math.isfinite(area)and area>0 and 0<fraction<=1+PLAN['fraction_roundoff_allowance'],'Positive actual area/fraction with declared floatroundoff allowance; zero contact has undefinedJ')
  rows.append(dict(pad=pad,i=i,j=j,area_m2=area,raw_fraction=fraction))
 stats=[]
 for pad in range(4):
  subset=[r for r in rows if r['pad']==pad];require(subset,'All four actual pads preserved');area=math.fsum(r['area_m2']for r in subset);footprint=len(subset)*h2;relative=abs(area-.000225)/.000225
  require(relative<=PLAN['area_relative_gate'],'225mm² actual pad area unchanged')
  fractions=[r['raw_fraction']for r in subset]
  stats.append(dict(pad=pad,patches=len(subset),actual_contact_area_m2=area,whole_contacted_pixel_footprint_m2=footprint,footprint_to_contact_area_ratio=footprint/area,
   min_raw_fraction=min(fractions),max_raw_fraction=max(fractions),full_cells_within_roundoff=sum(abs(f-1)<=PLAN['fraction_roundoff_allowance']for f in fractions),partial_cells=sum(f<1-PLAN['fraction_roundoff_allowance']for f in fractions),area_relative_error=relative))
 return rows,dict(id=definition['id'],path=definition['path'],SHA256=definition['SHA256'],h_m=definition['h_m'],nx=definition['nx'],patches=len(rows),pads=stats,
  raw_areas_preserved=True,fractions_clamped_or_rescaled=False,fraction_definition='f=actualA/float(h)^2; up to1e-10 above1 accepted as roundoff and reported unchanged',
  actual_contact_area_m2=math.fsum(r['area_m2']for r in rows),whole_contacted_pixel_footprint_m2=len(rows)*h2)

def make_spec():
 cfgraw=_read(CONFIG);require(sha(cfgraw)==CONFIG_SHA,'Actual pinned material/contact config');cfg=properties(cfgraw)
 sigma=float(cfg['sc.sigma.2000']);epsilon=float(cfg['sc.epsilon_r.2000']);gamma=complex(sigma,2*math.pi*2000*EPS0*epsilon);z=complex(float(cfg['z.2000.re']),float(cfg['z.2000.im']))
 require(sigma>0 and epsilon>0 and finite(gamma)and z.real>0 and finite(z),'Source-verified passive actual gammaSC and zA')
 masks=[]
 for definition in _mask_definitions():rows,stats=_load_mask(definition);masks.append(stats)
 actualraw=_read(FINE/'comparison-summary.json');require(sha(actualraw)==FINE_COMPARISON_SHA,'Actual fixed failed fine comparison, no result-fitting');actual=json.loads(actualraw)
 before=actual['coarse_contact_binding']['basis'][0];after=actual['fine_contact_binding']['basis'][0]
 metrics=('contact_J_RMS_max_A_m2','edge_J_RMS_P95_A_m2','source_power_W','contact_power_W')
 observations={k:dict(coarse=before[k],fine=after[k],fine_to_coarse_ratio=after[k]/before[k])for k in metrics}
 return dict(schema='task1-partial-contact-column-spec-v1',plan=json.loads(json.dumps(PLAN)),masks=masks,
  config_sha256=CONFIG_SHA,material_receipt_sha256=MATERIAL_SHA,contact_receipt_sha256=CONTACT_SHA,
  gamma_SC_S_m=pair(gamma),sigma_SC_S_m=sigma,epsilon_SC_r=epsilon,Y_SC_column_S_m2=pair(gamma/PLAN['SC_thickness_m']),actual_zA_ohm_m2=pair(z),
  source_actual_reference_commit=FINE_COMMIT,actual_comparison_sha256=FINE_COMPARISON_SHA,actual_basis0_burden_context=observations,
  mechanism_hypothesis='A shared whole-pixel topDOF can draw SC current throughh² even when contactA=f*h² ispartial. Unit independent-column limit diagnoses possiblefootprintaliasing; no quantitative attribution of actual coupledCEM burden change.',
  actual_geometry_and_powers_not_replaced=True,lower_SC4_sampling_not_changed_by_this_diagnostic=True,actual_contact_scales_not_applied=True,
  no_fitted_parameters=True,old_failed_screens_preserved=True,physiological_or_safety_threshold=False)

def column_model(area,h2,Y,z,DeltaV=1.,model='uniform_pixel'):
 """One synthetic independent SC column; all phasors peak,+jwt; VI*/2."""
 require(area>0 and h2>0 and 0<area/h2<=1+PLAN['fraction_roundoff_allowance']and finite(Y)and Y.real>0 and finite(z)and z.real>=0 and finite(DeltaV),'Finite passive contacted column; f0 not admissible forJ')
 f=area/h2
 if model=='uniform_pixel':B=h2;current=h2*Y*f*DeltaV/(f+Y*z)
 elif model=='area_resolved':B=area;current=area*Y*DeltaV/(1+Y*z)
 else:raise ValueError('Unknown predeclared column model')
 J=current/area;Vt=current/(B*Y);Vc=J*z;Ssource=.5*DeltaV*current.conjugate();SSC=.5*B*Y.conjugate()*abs(Vt)**2;Scontact=.5*z*abs(current)**2/area
 require(all(finite(v)for v in(current,J,Vt,Vc,Ssource,SSC,Scontact)),'Finite synthetic phasors/powers')
 voltage_error=abs(Vt+Vc-DeltaV)/max(abs(DeltaV),1e-12);power_error=abs(Ssource-SSC-Scontact)/max(abs(Ssource),abs(SSC+Scontact),1e-12)
 require(voltage_error<=PLAN['analytic_relative_gate']and power_error<=PLAN['analytic_relative_gate'],'Independent column series voltage/complex-power identity')
 require(SSC.real>=-1e-20 and Scontact.real>=-1e-20,'Signed passive real losses retained withoutabs/clamp')
 return dict(I=current,J=J,Vt=Vt,Vc=Vc,Ssource=Ssource,SSC=SSC,Scontact=Scontact,relative_voltage_error=voltage_error,relative_complex_power_error=power_error)

def weighted_quantile(values,weights,q):
 rows=sorted(zip(values,weights),key=lambda x:x[0]);threshold=q*math.fsum(weights);at=0.
 for value,weight in rows:
  at+=weight
  if at>=threshold:return value
 return rows[-1][0]

def _summarize(results,areas):
 source=sum((r['Ssource']for r in results),0j);sc=sum((r['SSC']for r in results),0j);contact=sum((r['Scontact']for r in results),0j);J=[abs(r['J'])/math.sqrt(2)for r in results];drop=[abs(r['Vc'])/math.sqrt(2)for r in results]
 return dict(total_complex_current_peak_A=pair(sum((r['I']for r in results),0j)),contact_J_RMS_max_A_m2=max(J),contact_J_RMS_area_P95_A_m2=weighted_quantile(J,areas,.95),contact_drop_RMS_max_V=max(drop),
  source_complex_power_W=pair(source),SC_complex_power_W=pair(sc),contact_complex_power_W=pair(contact),source_real_power_W=source.real,SC_real_power_W=sc.real,contact_real_power_W=contact.real,
  maximum_relative_voltage_identity_error=max(r['relative_voltage_error']for r in results),maximum_relative_complex_power_identity_error=max(r['relative_complex_power_error']for r in results),
  total_complex_power_identity_error=abs(source-sc-contact)/max(abs(source),abs(sc+contact),1e-12),power_definition='Signed complexVI*/2; real loss notabs-clipped; RMS=peak/sqrt2')

def build(spec,guard,deadline_monotonic=None):
 require(callable(guard),'Sole-owner finite guard');check(guard,deadline_monotonic);require(spec==make_spec(),'Exactly preregistered two actual masks and three fixed toy scales')
 start=time.monotonic();Y=complex(spec['Y_SC_column_S_m2']['real'],spec['Y_SC_column_S_m2']['imaginary']);z0=complex(spec['actual_zA_ohm_m2']['real'],spec['actual_zA_ohm_m2']['imaginary']);rows=[];arrays={};limits=[]
 # Independent exact limiting contracts, separate from actual observed burdens.
 a=.25;h2=1.;probe=.3+.2j
 one=column_model(h2,h2,Y,z0);reference=column_model(h2,h2,Y,z0,model='area_resolved');require(all(abs(one[k]-reference[k])<=1e-12+1e-10*abs(reference[k])for k in('I','J','Vc','Ssource','SSC','Scontact')),'f1 exact agreement')
 zero=column_model(a,h2,Y,0j);resolved=column_model(a,h2,Y,0j,model='area_resolved');require(abs(zero['I']-h2*Y)<=1e-12+1e-10*abs(Y)and abs(resolved['I']-a*Y)<=1e-12+1e-10*abs(Y),'z0 footprint current limit')
 limits.append(dict(fraction=a,zA=pair(0j),uniform_I=pair(zero['I']),resolved_I=pair(resolved['I']),uniform_to_resolved_J_magnitude_ratio=abs(zero['J'])/abs(resolved['J']),expected_ratio=1/a,
  interpretation='With contactz0, wholepixel currentapproachesh²Y independentactualA, whilearea-resolvedcurrentapproachesAY. Toy only, notactual3D correction.'))
 for definition in _mask_definitions():
  patches,geometry=_load_mask(definition);areas=[p['area_m2']for p in patches];prefix=definition['id'];h2=definition['h_m']**2
  for key in('pad','i','j','area_m2','raw_fraction'):arrays[prefix+'_'+key]=[p[key]for p in patches]
  for scale in PLAN['contact_impedance_scale_factors']:
   check(guard,deadline_monotonic);z=scale*z0;models={}
   for model in('uniform_pixel','area_resolved'):
    result=[]
    for index,patch in enumerate(patches):
     if index%128==0:check(guard,deadline_monotonic)
     result.append(column_model(patch['area_m2'],h2,Y,z,PLAN['DeltaV_peak_V'],model))
    models[model]=_summarize(result,areas)
    key=prefix+'_z'+format(scale,'.0f')+'_'+model
    for field in('I','J','Vt','Vc','Ssource','SSC','Scontact'):
     arrays[key+'_'+field+'_real']=[r[field].real for r in result];arrays[key+'_'+field+'_imaginary']=[r[field].imag for r in result]
    ratios=[]
    if model=='uniform_pixel':uniform_result=result
    else:
     ratios=[abs(u['J'])/max(abs(r['J']),1e-300)for u,r in zip(uniform_result,result)]
     models['ratio_max_per_patch_J_magnitude']=max(ratios);models['ratio_area_P95_per_patch_J_magnitude']=weighted_quantile(ratios,areas,.95);models['ratio_min_per_patch_J_magnitude']=min(ratios)
   rows.append(dict(mask=prefix,zA_scale=scale,synthetic_zA_ohm_m2=pair(z),actual_contact_input_modified=False,geometry=geometry,models=models,
    interpretation='Predeclared toycontactscale only; no refit or change toactual coupledphantom/contact/outputs. Area-column forbidslateralspread and isnottrue3D truth.'))
 check(guard,deadline_monotonic)
 return dict(summary=dict(schema='task1-partial-contact-column-result-v1',status='calculated_mechanism_MMS_only_no_model_change',spec=spec,rows=rows,limiting_contracts=limits,
  invariants=dict(f_equals_one_models_agree=True,zero_contact_impedance_footprint_limit_checked=True,finite_signed_complex_power_identity_passed=True,areas_or_fractions_rescaled=False,z_scales_fitted=False),
  new_phantom_PDE=0,new_CEM_conditions=0,new_CEM_RHS=0,wall_seconds=time.monotonic()-start,
  interpretation='IndependentSCcolumns with prescribedunitvoltage test possible partialcontact/wholepixelDOF mechanism. They do notreproduceactual2RHS, lateralspread, bulkcoupling,50ohm sources orTIS; no correctionfactor orburdenprediction isapplied.',
  holds=dict(actual_fine_CEM_screens_still_failed=True,old_5percent_flags_preserved=True,source_and_contact_originals_unchanged=True,candidate_adopted=False,full_convergence=False,experimental_validation=False,Windows_saved_verified=False)),arrays=arrays)
