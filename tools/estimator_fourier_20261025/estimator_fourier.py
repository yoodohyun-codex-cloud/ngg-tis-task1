"""Ten manufactured SC4/SC8 estimator cases. No real phantom PDE or import IO."""
from __future__ import annotations
import hashlib,json,math,time
from pathlib import Path
import frozen_fourier_v1 as f

MMS=Path('/workspace/task1-interface-fourier-20261025-run-r2')
SC4=Path('/dev/shm/task1-sc4-2000-20261025-run')
MODES=[1,2,4,8,16]
GRIDS=[dict(id='D',h_mm=.5,sc_cells=4,bulk_counts=[18,18,56]),dict(id='E',h_mm=.5,sc_cells=8,bulk_counts=[18,18,56])]

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def _complex(obj):return complex(obj['real'],obj['imaginary'])

def required_inputs():
 """Owner-invoked source and small metadata hashes; never native field arrays."""
 refs=f.required_inputs()
 paths=[MMS/'summary.json',MMS/'computation-receipt.json',MMS/'source/fourier_benchmark.py',SC4/'postprocess/summary.json',SC4/'postprocess/artifact-sha256.json']
 for path in paths:
  require(path.is_file()and not path.is_symlink()and path.stat().st_size<8*1024**2,'Actual source/metadata required: '+str(path));refs[str(path)]=digest(path.read_bytes())
 source=Path(__file__).parent/'frozen_fourier_v1.py';require(source.read_bytes()==(MMS/'source/fourier_benchmark.py').read_bytes(),'Exact unchanged published MMS helper copy');refs[str(source)]=digest(source.read_bytes())
 artifact=json.loads((SC4/'postprocess/artifact-sha256.json').read_text());require(refs[str(SC4/'postprocess/summary.json')]==artifact['summary.json']['SHA256'],'Actual complete SC4 summary identity')
 return refs

def make_spec(material_receipt_bytes,config_bytes):
 spec=f.make_spec(material_receipt_bytes,config_bytes,optional_sc4=True)
 spec.update(schema='task1-fixed-order-SC4-SC8-manufactured-spec-v1',grids=[dict(g,bulk_counts=list(g['bulk_counts']))for g in GRIDS],modes=list(MODES),
  comparison='SC4 vs SC8 at unchanged XY0.5/bulk18,18,56; exactly2/2 and exactly3/3 one-sided fits are separate fixed-order series',
  real_field_bias_correction=False,new_real_native_PDE=0)
 return spec

def decompose(row,cos_rms):
 """Jup-Jlo=(Jup-Jtrue)-(Jlo-Jtrue); signed complex errors retained."""
 ju,jl,jt=(_complex(row[k])for k in('upper_J','lower_J','exact_J'));eu=ju-jt;el=jl-jt;c2=cos_rms*cos_rms
 a=abs(eu)**2*c2;b=abs(el)**2*c2;cross=-2*(eu*el.conjugate()).real*c2;jump=abs(ju-jl)**2*c2
 return dict(upper_SC_complex_error_A_m2=f.pair(eu),lower_VS_complex_error_A_m2=f.pair(el),upper_SC_spatial_RMS_error_A_m2=abs(eu)*cos_rms,lower_VS_spatial_RMS_error_A_m2=abs(el)*cos_rms,
  upper_squared_A2_m4=a,lower_squared_A2_m4=b,cross_term_signed_A2_m4=cross,jump_squared_A2_m4=jump,jump_identity_absolute_error_A2_m4=abs(jump-(a+b+cross)),
  larger_side_by_absolute_error='VS_lower'if abs(el)>abs(eu)else'SC_upper',
  interpretation='Complex side errors may reinforce or cancel. Decomposition is descriptive; no correction is applied to real native fields and no 5% criterion is changed.')

def build(spec,guard,deadline_monotonic=None):
 require(callable(guard),'Finite sole-owner guard');guard()
 require(spec['schema']=='task1-fixed-order-SC4-SC8-manufactured-spec-v1'and spec['modes']==MODES and spec['grids']==GRIDS,'Exactly ten fixed-grid manufactured cases')
 require(spec['material_receipt_sha256']==f.MATERIAL_SHA and spec['config_sha256']==f.COARSE_CONFIG_SHA and spec['thickness_m']==list(f.THICKNESS)and spec['period_m']==.05 and spec['independent_normal_current_QA_limit']==f.QA_LIMIT==.05,'Unchanged verified gamma inputs/domain/5%flag')
 gamma=[_complex(r['gamma_S_m'])for r in spec['material_rows']]
 require(len(gamma)==4 and all(f.finite(g)and g.real>0 and g.imag>0 for g in gamma),'Four finite passive scalar gamma values')
 for i,row in enumerate(spec['material_rows']):require(row['layer']==f.LAYERS[i]and f._close(gamma[i],complex(row['sigma_S_m'],2*math.pi*2000*f.EPS0*row['epsilon_r'])),'Actual material arithmetic')
 contracts=f.analytic_contracts(guard);rows=[];arrays={}
 for grid in spec['grids']:
  for mode in MODES:
   guard();require(deadline_monotonic is None or time.monotonic()<deadline_monotonic,'Finite manufactured deadline')
   faces,layers,zs=f.make_grid(grid['h_mm'],grid['sc_cells'],grid['bulk_counts']);dz=[b-a for a,b in zip(faces[:-1],faces[1:])];h=.0005;k=2*math.pi*mode/.05;kfd=2*math.sin(k*h/2)/h;nx=100
   cos_rms=math.sqrt(sum(math.cos(k*(-.025+(i+.5)*h))**2 for i in range(nx))/nx)
   v,j,state=f.exact_profile(k,gamma,f.THICKNESS,zs);vfd,jfd,statefd=f.exact_profile(kfd,gamma,f.THICKNESS,zs);fv=f.solve_fvm(kfd,gamma,faces,layers)
   fits={};decomposition={}
   for label,values,truth in(('exact_continuum_k',v,state),('exact_continuum_kfd',vfd,statefd),('FVM_reference_kfd',fv,statefd),('FVM_reference_physical_k',fv,state)):
    fits[label]={};decomposition[label]={}
    for order,points in(('common_two_point',2),('up_to_three_point',3)):
     result=f.fit_interfaces(values,zs,layers,gamma,f.THICKNESS,truth,points,cos_rms)
     require(all(r['upper_points']==r['lower_points']==points for r in result),'Identical declared one-sided fit order on SC4 and SC8')
     fits[label][order]=result;decomposition[label][order]=decompose(result[0],cos_rms)
   key=grid['id']+'_m'+str(mode)
   rows.append(dict(case_id=key,mesh=dict(grid),mode=mode,k_per_m=k,kfd_per_m=kfd,vertical_cells=len(zs),spatial_mean_cos_squared=cos_rms*cos_rms,
    lateral_symbol_only_profile_error=f._profile_error(vfd,v,dz,zs),vertical_FVM_vs_kfd_error=f._profile_error(fv,vfd,dz,zs),combined_FVM_vs_physical_k_error=f._profile_error(fv,v,dz,zs),
    FVM_checks=f.fvm_diagnostics(fv,kfd,gamma,faces,layers,statefd),independent_fit_diagnostics=fits,first_SC_interface_bias_decomposition=decomposition))
   arrays[key+'_z_mm']=[z*1000 for z in zs];arrays[key+'_layer']=layers
   for label,values in(('exact_k',v),('exact_kfd',vfd),('FVM_kfd',fv)):
    arrays[key+'_'+label+'_real_V']=[float(z.real)for z in values];arrays[key+'_'+label+'_imaginary_V']=[float(z.imag)for z in values]
 comparison=[]
 for mode in MODES:
  old=next(r for r in rows if r['case_id']=='D_m'+str(mode));new=next(r for r in rows if r['case_id']=='E_m'+str(mode))
  for label in old['independent_fit_diagnostics']:
   for order in('common_two_point','up_to_three_point'):
    a=old['independent_fit_diagnostics'][label][order][0];b=new['independent_fit_diagnostics'][label][order][0]
    comparison.append(dict(mode=mode,profile=label,fit_order=order,SC4=a,SC8=b,normalized_jump_change=b['normalized_L2']-a['normalized_L2'],absolute_RMS_jump_change_A_m2=b['jump_spatial_RMS_A_m2']-a['jump_spatial_RMS_A_m2'],same_upper_and_lower_fit_order=True))
 guard();return dict(summary=dict(schema='task1-fixed-order-estimator-fourier-result-v1',status='calculated_manufactured_only_unadopted',spec=spec,analytic_contracts=contracts,rows=rows,SC4_to_SC8_fixed_order_comparison=comparison,
  scope='Ten planar periodic manufactured cases only; no actual SC8 native run, cylinder/CEM/contact/50ohm source or TIS prediction',
  threshold=.05,criteria_relaxed=False,real_fields_bias_corrected=False,new_real_native_PDE=0,native_field_arrays_read=False,
  holds=dict(real_5percent_failures_retained=True,full_SC_XY_bulk_edge_contact_convergence=False,material_anatomic_or_experimental_calibration=False,candidate_adopted=False)),arrays=arrays)
