"""Fifteen predeclared VS estimator/operator MMS cases, never a native solve.

No I/O, material evaluation or geometry computation occurs on import. Owner
make_spec pins actual faces and equivalent native counts before owner build.
"""
from __future__ import annotations
import hashlib,json,math,time
from pathlib import Path
import frozen_fourier_v1 as f

PRIOR=Path('/workspace/task1-estimator-fourier-20261025-run')
SC8=Path('/dev/shm/task1-sc8-2000-20261025-run')
SOURCE_ORIGINAL=Path('/dev/shm/task1-estimator-fourier-20261025/source')
MODES=[1,2,4,8,16]
GRIDS=[dict(id='U18',h_mm=.5,sc_cells=8,bulk_counts=[18,18,56],VS_grading='uniform'),
       dict(id='U19',h_mm=.5,sc_cells=8,bulk_counts=[19,18,56],VS_grading='uniform'),
       dict(id='G18',h_mm=.5,sc_cells=8,bulk_counts=[18,18,56],VS_grading='symmetric_geometric',width_ratio=1.15)]
SCREEN=dict(nonregression_relative_allowance=.01,meaningful_error_reduction_fraction=.10,
    relative_error_floor_allowance=1e-10,
    unchanged_independent_normal_current_QA=.05,automatic_native_admission=False,
    frozen_native_mesh_supports_U19_or_G18=False,
    interpretation='Predeclared engineering review screens only, not physical tolerance, activation or safety. No candidate ranking/automatic native solve.')

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def cx(obj):return complex(obj['real'],obj['imaginary'])

def required_inputs():
 """Deferred small metadata/source hashes, called only by root after SC8."""
 refs=f.required_inputs()
 paths=[PRIOR/'spec.json',PRIOR/'summary.json',PRIOR/'computation-receipt.json',
        SC8/'execute-receipt.json',SC8/'postprocess/summary.json',SC8/'postprocess/artifact-sha256.json',
        SOURCE_ORIGINAL/'estimator_fourier.py',SOURCE_ORIGINAL/'frozen_fourier_v1.py']
 for path in paths:
  require(path.is_file()and not path.is_symlink()and path.stat().st_size<8*1024**2,'Completed immutable source/metadata required: '+str(path));refs[str(path)]=digest(path.read_bytes())
 require((Path(__file__).parent/'frozen_fourier_v1.py').read_bytes()==(SOURCE_ORIGINAL/'frozen_fourier_v1.py').read_bytes(),'Unchanged published Fourier helper')
 receipt=json.loads((SC8/'execute-receipt.json').read_bytes());require(receipt['new_native_conditions_completed']==1 and receipt['new_native_RHS_completed']==2,'Actual SC8 native completion before this MMS study')
 artifact=json.loads((SC8/'postprocess/artifact-sha256.json').read_bytes());require(refs[str(SC8/'postprocess/summary.json')]==artifact['summary.json']['SHA256'],'Actual complete SC8 summary identity')
 refs[str(Path(__file__).parent/'frozen_fourier_v1.py')]=digest((Path(__file__).parent/'frozen_fourier_v1.py').read_bytes())
 return refs

def make_grid(grid):
 counts=[grid['sc_cells']]+grid['bulk_counts'];require(grid in GRIDS and counts[0]==8,'Only fixed SC8 candidate grids')
 if grid['VS_grading']=='uniform':return f.make_grid(grid['h_mm'],grid['sc_cells'],grid['bulk_counts'])
 faces=[0.];layers=[]
 for material,(thickness,count)in enumerate(zip(f.THICKNESS,counts)):
  top=faces[-1]
  weights=[grid['width_ratio']**min(j,count-1-j)for j in range(count)]if material==1 else[1.]*count
  total=sum(weights);cumulative=0.
  for j,weight in enumerate(weights):
   cumulative+=weight;faces.append(top+thickness*(cumulative/total if j+1<count else 1.));layers.append(material)
 zs=[(a+b)/2 for a,b in zip(faces[:-1],faces[1:])]
 require(all(b>a for a,b in zip(faces[:-1],faces[1:])),'Positive graded cells')
 return faces,layers,zs

def geometry_receipt(grid):
 faces,layers,zs=make_grid(grid);dz=[b-a for a,b in zip(faces[:-1],faces[1:])];nxy=0;h=.0005
 for j in range(100):
  for i in range(100):
   x=-.025+(i+.5)*h;y=-.025+(j+.5)*h
   if x*x+y*y<.025*.025:nxy+=1
 equivalent=nxy*len(zs);require(equivalent<=800000,'Candidate exceeds unchanged real-equivalent native800000cells')
 vs=[d for d,l in zip(dz,layers)if l==1];boundaries=[0];at=0
 for count in[grid['sc_cells']]+grid['bulk_counts']:at+=count;boundaries.append(at)
 require(all(abs(faces[index]-sum(f.THICKNESS[:layer]))<=1e-14 for layer,index in enumerate(boundaries)),'Exact unchanged physical layer boundaries')
 return dict(faces_m=faces,layer_ids=layers,centres_m=zs,VS_widths_m=vs,VS_min_dz_m=min(vs),VS_max_dz_m=max(vs),
    VS_thickness_m=sum(vs),vertical_cells=len(zs),XY_columns=nxy,real_equivalent_native_cells=equivalent,
    face_table_sha256=digest(json.dumps(faces,separators=(',',':'),allow_nan=False).encode()),
    actual_native_geometry_implemented=False,scope='Planar periodic manufactured mesh only; not a cylinder/CEM simulation')

def make_spec(material_receipt_bytes,config_bytes):
 spec=f.make_spec(material_receipt_bytes,config_bytes)
 spec.update(schema='task1-fixed-SC8-VS-estimator-spec-v1',grids=[dict(g,bulk_counts=list(g['bulk_counts']))for g in GRIDS],modes=list(MODES),
    geometry={g['id']:geometry_receipt(g)for g in GRIDS},case_count=15,review_screens=dict(SCREEN),
    comparison='FixedSC8/XY0.5, VS18uniform versus VS19uniform versus VS18symmetricr1.15; fixed2/2 and3/3 fits',
    scope='Manufactured planar periodic diagnostic only; exact faces/counts frozen before build; no native admission or bias correction',
    new_real_native_PDE=0,real_field_bias_correction=False)
 return spec

def discrete_admittance_profile(kfd,gamma,faces,layers):
 """Independent network reduction, not the Thomas elimination implementation."""
 dz=[b-a for a,b in zip(faces[:-1],faces[1:])];n=len(dz)
 edges=[1/(dz[i]/(2*gamma[layers[i]])+dz[i+1]/(2*gamma[layers[i+1]]))for i in range(n-1)]
 effective=[0j]*n;effective[-1]=gamma[layers[-1]]*dz[-1]*kfd*kfd
 for i in range(n-2,-1,-1):effective[i]=gamma[layers[i]]*dz[i]*kfd*kfd+edges[i]*effective[i+1]/(edges[i]+effective[i+1])
 top=2*gamma[layers[0]]/dz[0];values=[top/(top+effective[0])]
 for i,g in enumerate(edges):values.append(values[-1]*g/(g+effective[i+1]))
 require(all(f.finite(v)for v in values),'Finite independently reduced discrete profile')
 return values

def discrete_interface_states(values,gamma,faces,layers):
 """Algebraic discrete-network reference; NOT exact continuum/PDE truth."""
 dz=[b-a for a,b in zip(faces[:-1],faces[1:])];states=[(1+0j,2*gamma[layers[0]]/dz[0]*(1-values[0]))]
 for i in range(len(values)-1):
  if layers[i]==layers[i+1]:continue
  flux=(values[i]-values[i+1])/(dz[i]/(2*gamma[layers[i]])+dz[i+1]/(2*gamma[layers[i+1]]))
  voltage=values[i]-flux*dz[i]/(2*gamma[layers[i]]);states.append((voltage,flux))
 states.append((values[-1],0j));require(len(states)==5,'Four-layer discrete interface states')
 return states

def error_components(fitted_fv,fitted_exact,discrete_truth,continuum_truth,cos_rms):
 out={}
 for side in('upper','lower'):
  jf=cx(fitted_fv[side+'_J']);je=cx(fitted_exact[side+'_J']);jd=discrete_truth[1];jc=continuum_truth[1]
  estimator_vs_discrete=jf-jd;discrete_vs_continuum=jd-jc;total=jf-jc;exact_sample_bias=je-jc;profile_error_through_fit=jf-je
  out[side]=dict(FVM_fit_minus_discrete_flux=f.pair(estimator_vs_discrete),discrete_flux_minus_continuum_kfd=f.pair(discrete_vs_continuum),
   FVM_fit_minus_continuum_kfd=f.pair(total),exact_continuum_sample_fit_bias=f.pair(exact_sample_bias),FVM_profile_error_through_fit=f.pair(profile_error_through_fit),
   identity_error_A_m2=abs(total-estimator_vs_discrete-discrete_vs_continuum),second_identity_error_A_m2=abs(total-exact_sample_bias-profile_error_through_fit),
   estimator_vs_discrete_spatial_RMS_A_m2=abs(estimator_vs_discrete)*cos_rms,exact_sample_bias_spatial_RMS_A_m2=abs(exact_sample_bias)*cos_rms,
   FVM_fit_total_spatial_RMS_A_m2=abs(total)*cos_rms,cross_term_signed_A2_m4=2*(estimator_vs_discrete*discrete_vs_continuum.conjugate()).real*cos_rms*cos_rms)
 return out

def envelope(rows,grid_id):
 cases=[r for r in rows if r['grid']['id']==grid_id];bias={}
 for order in('common_two_point','three_point'):
  bias[order]=max(r['fits']['exact_continuum_kfd'][order][0]['lower_error_relative']for r in cases)
 return dict(SC_conservative_flux_vs_continuum_kfd_max_relative=max(r['FVM_vs_continuum_kfd']['shared_interface_flux_errors'][0]['relative_error']for r in cases),
  all_interface_flux_vs_continuum_kfd_max_relative=max(q['relative_error']for r in cases for q in r['FVM_vs_continuum_kfd']['shared_interface_flux_errors']),
  VS_profile_vs_continuum_kfd_max_relative=max(r['VS_FVM_profile_vs_continuum_kfd']['relative_L2']for r in cases),
  physical_k_profile_max_relative=max(r['combined_FVM_vs_physical_k']['relative_L2']for r in cases),
  exact_sample_lowerVS_bias_max_relative=bias)

def build(spec,guard,deadline_monotonic=None):
 require(callable(guard),'Finite sole-owner guard');guard()
 require(spec['schema']=='task1-fixed-SC8-VS-estimator-spec-v1'and spec['grids']==GRIDS and spec['modes']==MODES and spec['case_count']==15 and spec['review_screens']==SCREEN,'Exactly15 frozen candidate/mode cases and review metrics')
 require(spec['material_receipt_sha256']==f.MATERIAL_SHA and spec['config_sha256']==f.COARSE_CONFIG_SHA and spec['thickness_m']==list(f.THICKNESS)and spec['period_m']==.05 and spec['independent_normal_current_QA_limit']==.05,'Unchanged material/domain/5percent screen')
 gamma=[cx(r['gamma_S_m'])for r in spec['material_rows']]
 for i,row in enumerate(spec['material_rows']):require(row['layer']==f.LAYERS[i]and f._close(gamma[i],complex(row['sigma_S_m'],2*math.pi*2000*f.EPS0*row['epsilon_r'])),'Actual unchanged gamma arithmetic')
 contracts=f.analytic_contracts(guard);rows=[];arrays={}
 for grid in GRIDS:
  geometry=geometry_receipt(grid);require(spec['geometry'][grid['id']]==geometry,'Preregistered exact face/width/count table changed')
  faces=geometry['faces_m'];layers=geometry['layer_ids'];zs=geometry['centres_m'];dz=[b-a for a,b in zip(faces[:-1],faces[1:])]
  if grid['id']=='U18':require((faces,layers,zs)==f.make_grid(.5,8,[18,18,56]),'Exact preserved uniformSC8 baseline')
  for mode in MODES:
   guard();require(deadline_monotonic is None or time.monotonic()<deadline_monotonic,'Finite manufactured deadline')
   k=2*math.pi*mode/.05;h=.0005;kfd=2*math.sin(k*h/2)/h;cos_rms=math.sqrt(sum(math.cos(k*(-.025+(i+.5)*h))**2 for i in range(100))/100)
   v,_,truth=f.exact_profile(k,gamma,f.THICKNESS,zs);vfd,_,truthfd=f.exact_profile(kfd,gamma,f.THICKNESS,zs);fv=f.solve_fvm(kfd,gamma,faces,layers)
   independent=discrete_admittance_profile(kfd,gamma,faces,layers);algebra_error=max(abs(a-b)for a,b in zip(fv,independent));require(all(f._close(a,b)for a,b in zip(fv,independent)),'Independent discrete network/Thomas algebra crosscheck')
   discrete=discrete_interface_states(fv,gamma,faces,layers);fits={};components={}
   for label,values,reference in(('exact_continuum_k',v,truth),('exact_continuum_kfd',vfd,truthfd),('FVM_against_continuum_kfd',fv,truthfd),('FVM_against_physical_k',fv,truth),('FVM_against_discrete_network',fv,discrete)):
    fits[label]={}
    for order,points in(('common_two_point',2),('three_point',3)):
     result=f.fit_interfaces(values,zs,layers,gamma,f.THICKNESS,reference,points,cos_rms);require(all(r['upper_points']==r['lower_points']==points for r in result),'Fixed same order on both sides in every candidate');fits[label][order]=result
   for order in('common_two_point','three_point'):components[order]=error_components(fits['FVM_against_continuum_kfd'][order][0],fits['exact_continuum_kfd'][order][0],discrete[1],truthfd[1],cos_rms)
   diagnostics=f.fvm_diagnostics(fv,kfd,gamma,faces,layers,truthfd)
   require(diagnostics['relative_algebraic_residual']<=1e-10 and diagnostics['complex_energy_relative_error']<=1e-10,'Fixed manufactured algebra/energy contracts')
   vs=[i for i,l in enumerate(layers)if l==1]
   key=grid['id']+'_m'+str(mode)
   rows.append(dict(case_id=key,grid=dict(grid),mode=mode,k_per_m=k,kfd_per_m=kfd,geometry=geometry,
    discrete_Thomas_vs_admittance_max_absolute_V=algebra_error,FVM_vs_continuum_kfd=diagnostics,
    VS_FVM_profile_vs_continuum_kfd=f._profile_error([fv[i]for i in vs],[vfd[i]for i in vs],[dz[i]for i in vs],[zs[i]for i in vs]),
    vertical_FVM_vs_continuum_kfd=f._profile_error(fv,vfd,dz,zs),lateral_symbol_continuum_kfd_vs_k=f._profile_error(vfd,v,dz,zs),combined_FVM_vs_physical_k=f._profile_error(fv,v,dz,zs),
    fits=fits,SC_VS_signed_error_components=components,discrete_interface_reference=[dict(V=f.pair(a),J=f.pair(b))for a,b in discrete],
    reference_labels=dict(discrete='Algebraically solved discrete-network reference only; not true continuum/PDE error',vertical='Analytic continuum at kfd',physical='Analytic continuum at physicalk',fit_bias='One-sided fit on exact analytic continuum samples')))
   arrays[key+'_z_mm']=[z*1000 for z in zs];arrays[key+'_layer']=layers
   for label,values in(('exact_k',v),('exact_kfd',vfd),('FVM_kfd',fv)):
    arrays[key+'_'+label+'_real_V']=[z.real for z in values];arrays[key+'_'+label+'_imaginary_V']=[z.imag for z in values]
 baseline=envelope(rows,'U18');reviews=[]
 for grid in GRIDS[1:]:
  candidate=envelope(rows,grid['id']);keys=('SC_conservative_flux_vs_continuum_kfd_max_relative','all_interface_flux_vs_continuum_kfd_max_relative','VS_profile_vs_continuum_kfd_max_relative','physical_k_profile_max_relative')
  nonregression=all(candidate[key]<=baseline[key]*(1+SCREEN['nonregression_relative_allowance'])+SCREEN['relative_error_floor_allowance'] for key in keys)
  physical_gain=any(baseline[key]>SCREEN['relative_error_floor_allowance']and candidate[key]<=baseline[key]*(1-SCREEN['meaningful_error_reduction_fraction'])for key in keys[:3])
  bias_gain=all(baseline['exact_sample_lowerVS_bias_max_relative'][order]>SCREEN['relative_error_floor_allowance']and candidate['exact_sample_lowerVS_bias_max_relative'][order]<=baseline['exact_sample_lowerVS_bias_max_relative'][order]*(1-SCREEN['meaningful_error_reduction_fraction'])for order in('common_two_point','three_point'))
  reviews.append(dict(candidate=grid['id'],baseline_metrics=baseline,candidate_metrics=candidate,true_continuum_error_nonregression=nonregression,
   physical_error_improvement_review=nonregression and physical_gain,estimator_localization_only_review=nonregression and bias_gain,
   pure_fit_bias_improves_both_fixed_orders=bias_gain,automatic_native_admission=False,requires_root_review=True,
   native_implementation_blocker='Frozen native ValidationMesh supports neither VS19 nor gradedVS18. A separately published/validated mesh adapter is needed before any real native followup.',
   nonregression_scope='Worst envelopes over all declared modes/interfaces; full per-mode/interface rows are retained, so this is not a pointwise monotonicity guarantee',
   interpretation='A screening flag improvement alone never proves improved PDE accuracy; no winner chosen and no real fields corrected'))
 guard();return dict(summary=dict(schema='task1-SC8-VS-estimator-manufactured-result-v1',status='calculated_manufactured_only_unadopted',spec=spec,analytic_contracts=contracts,rows=rows,predeclared_native_review=reviews,
  no_automatic_candidate_selection=True,independent_5percent_criterion_unchanged=True,real_fields_bias_corrected=False,new_real_native_PDE=0,native_field_arrays_read=False,
  scope='15 planar periodic top-Dirichlet manufactured cases only, not cylinder/CEM/electrodes/50ohm hardware or real-phantom validation',
  holds=dict(full_SC_XY_bulk_edge_contact_convergence=False,candidate_adopted=False,material_anatomic_experimental_or_safety_validation=False,real_5percent_flags_retained=True)),arrays=arrays)
