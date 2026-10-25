"""Conditional HREF-MIX coefficient-transfer SC-slab/contact benchmark.

Import performs no I/O, array construction, NumPy import or scientific work.
Only the actual2000Hz CEM SC/contact coefficients are transferred. The periodic slab
and ideal equipotential patch remain a separate benchmark, not the four-pad model.
The root may admit execution only after the preceding finite-volume results
have been validated; source preparation does not admit numerical execution.
"""
from __future__ import annotations
import hashlib,io,json,math,time
from pathlib import Path

SOURCE=Path('/dev/shm/task1-contact-edge-surrogate-20261025/source')
ORIGINAL_SPEC=Path('/dev/shm/task1-layer-dtn-xy102-cem-20261025-run/spec.json')
ORIGINAL_SPEC_SHA256='98840b84c321ea57ff255fec56e565277765cafda3c2aa84a96ebc28931e556c'
ORIGINAL_BEM=Path('/dev/shm/task1-contact-edge-equipotential-20261025/source/contact_edge_equipotential.py')
FROZEN_BEM=SOURCE/'frozen_contact_edge_equipotential.py'
FROZEN_BEM_SHA256='5c84ed110897959bbf3336d7c0e3042fc10c7c1f3d5500512be25c6e10b1a61a'
EXPECTED_GAMMA=dict(real=5.959456590514033e-6,imaginary=2.5055522184188793e-5)
EXPECTED_CONTACT=dict(real=5.5504758759767015e-5,imaginary=-1.2307933145190832e-4)
CASE_PAIRS=((64,4096),(128,4096),(256,1024),(256,2048),(256,4096))
DELTA_LIMITS=dict(contact_current_complex_relative=.01,source_real_power_relative=.02,
 contact_J_RMS_P95_relative=.05,slab_E_L2_RMS_relative=.01,same_grid_vector_field_relative_L2=.02)
CONTRACTS=dict(linear_residual=1e-10,complex_symmetry=1e-10,complex_power_balance=1e-10,
 analytic_relative=1e-10,analytic_absolute=1e-10,passivity_relative=1e-12)
PLAN=dict(period_width_m=.002,SC_thickness_m=.0001,contact_endpoints_m=[-.0005,.0005],
 transferred_gamma_S_m=dict(EXPECTED_GAMMA),transferred_contact_ohm_m2=dict(EXPECTED_CONTACT),
 equipotential_contact_peak_V=dict(real=1.,imaginary=0.),bottom_peak_V=0.,
 panel_counts=[64,128,256],positive_harmonic_cutoffs=[1024,2048,4096],unique_cases=[list(v)for v in CASE_PAIRS],
 panel_axis=dict(panels=[64,128,256],fixed_positive_harmonics=4096),
 harmonic_axis=dict(positive_harmonics=[1024,2048,4096],fixed_panels=256),
 field_x_midpoints=512,field_z_midpoints=128,surface_x_midpoints=1024,
 spectral_block_modes=64,reconstruction_depth_block=8,max_all_physical_evaluation_samples=800000,
 surrogate_slab_conditions=5,surrogate_slab_RHS=5,analytic_contract_extra_slab_RHS=1,root_admission_required=True,new_actual_phantom_PDE=0,new_actual_four_pad_CEM_RHS=0)


def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pair(v):v=complex(v);return dict(real=v.real,imaginary=v.imag)
def complex_value(v):return complex(v['real'],v['imaginary'])
def python_scalars(value):
 """Lossless JSON metadata normalization; never implicitly exports arrays."""
 if value is None or type(value)in(bool,str,int):return value
 if type(value)is float:
  require(math.isfinite(value),'Nonfinite metadata rejected before file open');return value
 if isinstance(value,dict):return{key:python_scalars(item)for key,item in value.items()}
 if isinstance(value,(list,tuple)):return[python_scalars(item)for item in value]
 if type(value).__name__=='ndarray':raise TypeError('Metadata arrays require explicit registered export, not implicit JSON conversion')
 if getattr(value,'ndim',None)==0 and callable(getattr(value,'item',None)):
  scalar=value.item()
  if scalar is None or type(scalar)in(bool,str,int,float):return python_scalars(scalar)
  raise TypeError('Unsupported scientific scalar payload: '+type(scalar).__name__)
 raise TypeError('Unsupported scientific metadata type: '+type(value).__name__)
def encoded(obj):return (json.dumps(python_scalars(obj),ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def new_json(path,obj):
 raw=encoded(obj) # Normalize/encode completely before creating immutable output.
 with Path(path).open('xb')as stream:stream.write(raw)

def file_sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def check(guard,deadline):
 guard();require(deadline is None or time.monotonic()<deadline,'Finite conditional surrogate-contact benchmark deadline')
def _pinned_source_spec(raw=None):
 """Owner-only bounded metadata read or pure supplied-byte verification."""
 if raw is None:
  require(ORIGINAL_SPEC.is_file()and ORIGINAL_SPEC==ORIGINAL_SPEC.resolve()and not ORIGINAL_SPEC.is_symlink()and ORIGINAL_SPEC.stat().st_size<=2*1024**2,'Bounded canonical original CEM specification')
  raw=ORIGINAL_SPEC.read_bytes()
 require(isinstance(raw,bytes)and len(raw)<=2*1024**2 and sha(raw)==ORIGINAL_SPEC_SHA256,'Exact original XY102 CEM specification SHA; no source substitution')
 obj=json.loads(raw)
 require(obj['schema']=='task1-layer-dtn-xy102-cem-reference-spec-v1'and obj['plan']['frequency_Hz']==2000 and obj['plan']['layers_m'][0]==.0001,'Original2000Hz SC coefficient source and0.1mm thickness')
 require(obj['material_receipt_sha256']=='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'and obj['contact_receipt_sha256']=='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b','Original HREF-MIX/contact receipt provenance')
 rows=[row for row in obj['material_rows']if row['layer']=='sc'];require(len(rows)==1,'Unique SC row, never whole-skin/other-layer duplication')
 row=rows[0];gamma=dict(row['gamma_S_m']);contact=dict(obj['contact_specific_impedance_ohm_m2'])
 require(gamma==EXPECTED_GAMMA and contact==EXPECTED_CONTACT and row['sigma_S_m']==gamma['real']and row['epsilon_r']>0,'Exact already-evaluated SC gamma and contact zA; no refit/recalculation')
 return obj,row,gamma,contact

def required_inputs():
 """Only source/metadata pins; never reads previous fields, arrays or Q cache."""
 _pinned_source_spec()
 for p in(ORIGINAL_BEM,FROZEN_BEM):require(p.is_file()and not p.is_symlink()and file_sha(p)==FROZEN_BEM_SHA256,'Byte-identical published synthetic BEM method source')
 p=Path(__file__).resolve()
 return {str(ORIGINAL_SPEC):ORIGINAL_SPEC_SHA256,str(ORIGINAL_BEM):FROZEN_BEM_SHA256,str(FROZEN_BEM):FROZEN_BEM_SHA256,str(p):file_sha(p)}

def make_spec(source_spec_bytes=None):
 original,row,gamma,contact=_pinned_source_spec(source_spec_bytes);plan=json.loads(json.dumps(PLAN))
 plan['transferred_gamma_S_m']=gamma;plan['transferred_contact_ohm_m2']=contact
 beta=abs(complex_value(gamma)*complex_value(contact))/plan['SC_thickness_m']
 return dict(schema='task1-surrogate-equipotential-contact-slab-spec-v1',plan=plan,
  diagnostic_delta_limits=dict(DELTA_LIMITS),algebraic_contracts=dict(CONTRACTS),
  coefficient_transfer=dict(original_CEM_spec_sha256=ORIGINAL_SPEC_SHA256,frozen_synthetic_BEM_source_sha256=FROZEN_BEM_SHA256,frequency_Hz=2000,SC_source_row=row,
   gamma_unit='S/m',zA_unit='ohm m^2',contact_specific_impedance_ohm_m2=contact,material_receipt_sha256=original['material_receipt_sha256'],contact_receipt_sha256=original['contact_receipt_sha256'],
   operation='Exact complex coefficient copy at2000Hz; no new measurement, Rs subtraction, area scaling, material evaluation or empirical correction',
   beta_dimensionless=beta,beta_definition='abs(zA*gamma)/SC_thickness',edge_resolution_warning='Small beta makes the contact edge difficult; unchanged diagnostic flags and increasing panel Jmax must be retained'),
  admission_policy='Conditional source only: root executes after actual finite-volume benchmark results are validated; no automatic admission',
  coordinate_system=dict(x='periodic horizontal coordinate in metres, -L/2 <= x < L/2',z='depth from physical SC top,0<=z<=t',out_of_plane='unit length; I in A/m and complex power in W/m'),
  phasor='peak complex exp(+j omega t); transferred coefficients evaluated at2000Hz',
  circuit='one ideal1Vpeak equipotential patch and grounded entire bottom; insulated top outside patch and periodic sides; actual four-pad/50ohm source topology is not transferred',
  material_provenance='HREF-MIX declared surrogate SC and PBS-derived uncertain contact coefficients from the actual CEM input; not direct human thoracoabdominal measurements or validated skin contact',
  series='finite symmetric +/-n Fourier truncation; separately evaluated positive and negative complex coefficients, never assume conjugate symmetry',
  power='Ssource=.5 V conj(I); Scontact=.5 zA integral|q|^2; Sbulk=.5 integral phi_top conj(q); all per unit out-of-plane length',
  field='analytic x/z derivatives of finite Fourier potential; E_RMS=sqrt((abs(Ex)^2+abs(Ez)^2)/2)',
  interpretation='Separate periodic slab comparison of transferred coefficients; finite panel/harmonic diagnostics, no exact continuum truth, actual four-pad solution, anatomical/skin-contact/physiological/safety validation',
  original_results_preserved=True,candidate_adopted=False)

def stable_kernel(k,z,t):
 """Scalar sinh/cosh and cosh/cosh ratios without high-k overflow."""
 require(k>=0 and t>0 and 0<=z<=t,'Nonnegative modal k and physical depth')
 if k==0:return t-z,1.
 base=math.exp(-k*z);tail=math.exp(-2*k*(t-z));den=1+math.exp(-2*k*t)
 return base*(-math.expm1(-2*k*(t-z)))/(k*den),base*(1+tail)/den

def full_contact_analytic(gamma,zA,L,t,V):
 require(gamma.real>0 and zA.real>0 and L>0 and t>0,'Passive transferred-coefficient full contact')
 q=V/(zA+t/gamma);I=L*q;contact=.5*zA*L*abs(q)**2;bulk=.5*(t/gamma)*L*abs(q)**2;source=.5*V*I.conjugate()
 return dict(q=q,I=I,Ssource=source,Scontact=contact,Sbulk=bulk)

def _assemble(np,edges,H,L,t,gamma,zA,V,guard,deadline):
 """Integrated Galerkin matrix; +/- terms equal factor2*cos, no missing mode."""
 lengths=np.diff(edges);centres=(edges[:-1]+edges[1:])/2;p=len(lengths)
 require(p>0 and H>0 and np.all(lengths>0),'Positive exactly endpoint-aligned panels')
 bulk=(t/gamma/L)*np.outer(lengths,lengths).astype(np.complex128)
 for first in range(1,H+1,PLAN['spectral_block_modes']):
  check(guard,deadline);n=np.arange(first,min(H+1,first+PLAN['spectral_block_modes']));k=2*math.pi*n/L
  B=lengths[:,None]*np.sinc(lengths[:,None]*k[None,:]/(2*math.pi))*np.exp(1j*centres[:,None]*k[None,:])
  T=np.tanh(k*t)/(gamma*k)
  bulk+=((B*T)@B.conj().T+(B.conj()*T)@B.T)/L
 A=bulk+np.diag(zA*lengths);rhs=V*lengths
 symmetry=float(np.linalg.norm(A-A.T)/max(float(np.linalg.norm(A)),1e-300))
 require(symmetry<=CONTRACTS['complex_symmetry'],'Complex symmetric Galerkin reciprocity contract')
 q=np.linalg.solve(A,rhs);residual=float(np.linalg.norm(A@q-rhs)/max(float(np.linalg.norm(rhs)),1e-300))
 require(np.isfinite(q).all()and residual<=CONTRACTS['linear_residual'],'Finite solved surrogate Galerkin residual')
 return q,lengths,centres,dict(relative_linear_residual=residual,relative_complex_symmetry=symmetry,complex_symmetric_not_Hermitian=True)

def _coefficients(np,q,lengths,centres,H,L,guard,deadline):
 plus=np.empty(H,np.complex128);minus=np.empty(H,np.complex128)
 for first in range(0,H,PLAN['spectral_block_modes']):
  check(guard,deadline);last=min(H,first+PLAN['spectral_block_modes']);k=2*math.pi*np.arange(first+1,last+1)/L
  B=lengths[:,None]*np.sinc(lengths[:,None]*k[None,:]/(2*math.pi))*np.exp(1j*centres[:,None]*k[None,:])
  plus[first:last]=B.conj().T@q/L;minus[first:last]=B.T@q/L
 return complex(lengths@q/L),plus,minus

def _reconstruct(np,q0,plus,minus,x,z,L,t,gamma,guard,deadline):
 """Blocked finite-series potential and signed analytic field components."""
 phi=np.broadcast_to(q0*(t-z[:,None])/gamma,(len(z),len(x))).astype(np.complex128).copy()
 Ex=np.zeros_like(phi);Ez=np.full_like(phi,q0/gamma)
 for first in range(0,len(plus),PLAN['spectral_block_modes']):
  check(guard,deadline);last=min(len(plus),first+PLAN['spectral_block_modes']);k=2*math.pi*np.arange(first+1,last+1)/L
  positive=np.exp(1j*k[:,None]*x[None,:]);negative=positive.conj();den=1+np.exp(-2*k*t)
  for zi in range(0,len(z),PLAN['reconstruction_depth_block']):
   check(guard,deadline);stop=min(len(z),zi+PLAN['reconstruction_depth_block']);depth=z[zi:stop,None]
   decay=np.exp(-depth*k[None,:]);tail=np.exp(-2*(t-depth)*k[None,:])
   ph=decay*(-np.expm1(-2*(t-depth)*k[None,:]))/(gamma*k[None,:]*den[None,:]);normal=decay*(1+tail)/(gamma*den[None,:])
   pp=ph*plus[None,first:last];pm=ph*minus[None,first:last]
   phi[zi:stop]+=pp@positive+pm@negative
   Ex[zi:stop]+=(-1j*k[None,:]*pp)@positive+(1j*k[None,:]*pm)@negative
   Ez[zi:stop]+=(normal*plus[None,first:last])@positive+(normal*minus[None,first:last])@negative
 return phi,Ex,Ez

def _weighted_p95(np,values,lengths):
 order=np.argsort(values,kind='stable');j=min(int(np.searchsorted(np.cumsum(lengths[order]),.95*lengths.sum(),side='left')),len(order)-1)
 return float(values[order[j]])

def analytic_validation(np,guard=lambda:None,deadline=None,spec=None):
 """Full-period1D contract explicitly uses the transferred case coefficients."""
 spec=make_spec()if spec is None else spec;require(spec==make_spec(),'Exact transferred-coefficient analytic validation specification');plan=spec['plan']
 L=plan['period_width_m'];t=plan['SC_thickness_m'];gamma=complex_value(plan['transferred_gamma_S_m']);zA=complex_value(plan['transferred_contact_ohm_m2']);V=complex_value(plan['equipotential_contact_peak_V'])
 truth=full_contact_analytic(gamma,zA,L,t,V);edges=np.linspace(-L/2,L/2,5)
 q,lengths,centres,solve=_assemble(np,edges,32,L,t,gamma,zA,V,guard,deadline)
 q0,plus,minus=_coefficients(np,q,lengths,centres,32,L,guard,deadline)
 x=np.asarray([-L/3,0.,L/3]);z=np.asarray([0.,t/2,t]);phi,Ex,Ez=_reconstruct(np,q0,plus,minus,x,z,L,t,gamma,guard,deadline)
 expected_phi=np.broadcast_to(truth['q']*(t-z[:,None])/gamma,phi.shape)
 rows=dict(q=float(np.max(abs(q-truth['q']))),potential=float(np.max(abs(phi-expected_phi))),horizontal_E=float(np.max(abs(Ex))),vertical_E=float(np.max(abs(Ez-truth['q']/gamma))))
 for name,error in rows.items():
  scale=abs(truth['q'])if name=='q'else abs(truth['q']/gamma)if name.endswith('_E')else max(1.,float(np.max(abs(expected_phi))))
  require(error<=CONTRACTS['analytic_absolute']+CONTRACTS['analytic_relative']*scale,'Full-contact closed-form '+name)
 power_error=abs(truth['Ssource']-truth['Scontact']-truth['Sbulk'])/max(abs(truth['Ssource']),1e-300)
 require(power_error<=CONTRACTS['complex_power_balance'],'Independent signed complex source/contact/bulk power contract')
 return dict(passed=True,scope='Full-period ideal equipotential contact; independent 1D analytic contract, not the partial-contact continuum solution',errors=rows,complex_power_relative_error=power_error,solve=solve,transferred_gamma_S_m=pair(gamma),transferred_zA_ohm_m2=pair(zA),source_CEM_spec_sha256=ORIGINAL_SPEC_SHA256,periodic_slab_only=True,new_actual_phantom_PDE=0)

def _case(np,P,H,spec,guard,deadline):
 check(guard,deadline);start=time.monotonic();plan=spec['plan'];L=plan['period_width_m'];t=plan['SC_thickness_m'];gamma=complex_value(plan['transferred_gamma_S_m']);zA=complex_value(plan['transferred_contact_ohm_m2']);V=complex_value(plan['equipotential_contact_peak_V']);a,b=plan['contact_endpoints_m']
 edges=np.linspace(a,b,P+1);q,lengths,centres,solve=_assemble(np,edges,H,L,t,gamma,zA,V,guard,deadline)
 q0,plus,minus=_coefficients(np,q,lengths,centres,H,L,guard,deadline);k=2*math.pi*np.arange(1,H+1)/L
 I=complex(q@lengths);source=.5*V*I.conjugate();contact=.5*zA*float(lengths@(abs(q)**2))
 energy_coefficient=t*abs(q0)**2+float(np.sum(np.tanh(k*t)/k*(abs(plus)**2+abs(minus)**2)))
 bulk=.5*L/gamma*energy_coefficient;energy_peak_area=L/abs(gamma)**2*energy_coefficient
 balance=abs(source-contact-bulk)/max(abs(source),1e-300)
 require(balance<=CONTRACTS['complex_power_balance'],'Finite-series signed complex power balance')
 require(source.real>0 and contact.real>=-CONTRACTS['passivity_relative']*abs(source)and bulk.real>=-CONTRACTS['passivity_relative']*abs(source),'Transferred-coefficient passive real power')
 x=-L/2+(np.arange(plan['field_x_midpoints'])+.5)*L/plan['field_x_midpoints'];z=(np.arange(plan['field_z_midpoints'])+.5)*t/plan['field_z_midpoints']
 phi,Ex,Ez=_reconstruct(np,q0,plus,minus,x,z,L,t,gamma,guard,deadline);rms=np.sqrt((abs(Ex)**2+abs(Ez)**2)/2)
 volume_l2=math.sqrt(energy_peak_area/(2*L*t));grid_l2=float(np.sqrt(np.mean(rms*rms)));jrms=abs(q)/math.sqrt(2)
 sx=-L/2+(np.arange(plan['surface_x_midpoints'])+.5)*L/plan['surface_x_midpoints'];surface_phi,surface_Ex,surface_Ez=_reconstruct(np,q0,plus,minus,sx,np.asarray([0.]),L,t,gamma,guard,deadline)
 native_q=np.zeros(len(sx),np.complex128);inside=(sx>=a)&(sx<b);indices=np.searchsorted(edges,sx[inside],side='right')-1;native_q[inside]=q[indices];truncated_q=gamma*surface_Ez[0]
 robin=surface_phi[0,inside]+zA*native_q[inside]-V;gap=~inside
 arrays=dict(panel_edges_m=edges,panel_centres_m=centres,panel_lengths_m=lengths,q_panel_peak_A_m2=q,q_panel_RMS_A_m2=jrms,q_mode0_peak_A_m2=np.asarray(q0),q_mode_positive_peak_A_m2=plus,q_mode_negative_peak_A_m2=minus,
  x_m=x,z_m=z,phi_peak_V=phi,Ex_peak_V_m=Ex,Ez_peak_V_m=Ez,E_carrier_RMS_V_m=rms,surface_x_m=sx,surface_phi_peak_V=surface_phi[0],surface_q_native_panel_peak_A_m2=native_q,surface_q_Fourier_partial_peak_A_m2=truncated_q)
 require(all(np.isfinite(v).all()for v in arrays.values()),'All exported surrogate-slab arrays finite')
 metadata=dict(case_id='P%d-H%d'%(P,H),panels=P,positive_harmonics=H,total_signed_modes=2*H+1,physical_contact_endpoints_m=[float(edges[0]),float(edges[-1])],
  solved_contracts=dict(**solve,signed_complex_power_relative_error=balance),contact_current_peak_A_per_m=pair(I),source_complex_power_W_per_m=pair(source),contact_complex_power_W_per_m=pair(contact),bulk_complex_power_W_per_m=pair(bulk),
  contact_q_native_panel=dict(complex_length_weighted_mean_peak_A_m2=pair(I/(b-a)),RMS_length_weighted_mean_A_m2=float(jrms@lengths/lengths.sum()),RMS_P95_A_m2=_weighted_p95(np,jrms,lengths),RMS_max_panel_A_m2=float(jrms.max()),maximum_scope='Maximum panel-constant approximation; sampling/panel dependent, not the continuum edge maximum'),
  slab_field=dict(volume_L2_carrier_RMS_V_m=volume_l2,volume_definition='Entire periodic slab L*t per unit out-of-plane length; not an actual phantom target ROI',finite_series_integral_peak_E_squared_V2=energy_peak_area,field_grid_L2_carrier_RMS_V_m=grid_l2,field_grid_vs_Parseval_relative_difference=abs(grid_l2-volume_l2)/max(volume_l2,1e-300),mean_sampled_carrier_RMS_V_m=float(rms.mean()),max_sampled_carrier_RMS_V_m=float(rms.max()),maximum_scope='Fixed physical midpoint samples; not a continuum maximum'),
  surface_Fourier_projection=dict(contact_sampled_Robin_relative_RMS=float(np.sqrt(np.mean(abs(robin)**2))/max(abs(V),1e-300)),gap_truncated_normal_flux_RMS_A_m2=float(np.sqrt(np.mean(abs(truncated_q[gap])**2))/math.sqrt(2)),native_gap_flux_prescribed_zero=True,interpretation='Native piecewise-constant panel q is zero outside the exact contact. Finite Fourier surface flux has truncation/Gibbs leakage; this is not separately solved insulation failure or validated edge Jmax'),
  evaluated_physical_points=int(len(x)*len(z)+len(sx)),array_shapes={key:list(value.shape)for key,value in arrays.items()},wall_seconds=time.monotonic()-start,new_actual_phantom_PDE=0,new_actual_four_pad_CEM_RHS=0,candidate_adopted=False)
 return dict(metadata=metadata,arrays=arrays)

def _adjacent(np,old,new,axis):
 a=old['metadata'];b=new['metadata'];rows=[]
 def add(name,value,limit):rows.append(dict(metric=name,relative_difference=float(value),limit=limit,passed=bool(value<=limit)))
 ai=complex_value(a['contact_current_peak_A_per_m']);bi=complex_value(b['contact_current_peak_A_per_m'])
 add('contact_current_complex_relative',abs(ai-bi)/max(abs(bi),1e-300),DELTA_LIMITS['contact_current_complex_relative'])
 for key,av,bv in(('source_real_power_relative',a['source_complex_power_W_per_m']['real'],b['source_complex_power_W_per_m']['real']),('contact_J_RMS_P95_relative',a['contact_q_native_panel']['RMS_P95_A_m2'],b['contact_q_native_panel']['RMS_P95_A_m2']),('slab_E_L2_RMS_relative',a['slab_field']['volume_L2_carrier_RMS_V_m'],b['slab_field']['volume_L2_carrier_RMS_V_m'])):add(key,abs(av-bv)/max(abs(bv),1e-300),DELTA_LIMITS[key])
 aa=old['arrays'];bb=new['arrays'];require(np.array_equal(aa['x_m'],bb['x_m'])and np.array_equal(aa['z_m'],bb['z_m']),'Same physical field samples for adjacent diagnostics')
 numerator=float(np.sum(abs(aa['Ex_peak_V_m']-bb['Ex_peak_V_m'])**2+abs(aa['Ez_peak_V_m']-bb['Ez_peak_V_m'])**2));denominator=float(np.sum(abs(bb['Ex_peak_V_m'])**2+abs(bb['Ez_peak_V_m'])**2))
 add('same_grid_vector_field_relative_L2',math.sqrt(numerator/max(denominator,1e-300)),DELTA_LIMITS['same_grid_vector_field_relative_L2'])
 return dict(axis=axis,coarse_case=a['case_id'],fine_case=b['case_id'],rows=rows,all_diagnostic_flags_pass=all(row['passed']for row in rows),
  interpretation='Predeclared finite-panel or finite-harmonic numerical changes only; flags never suppress results and do not establish continuum truth, actual skin validity, activation or safety')

def edge_maximum_diagnostics(cases):
 """Native-panel extrema are retained separately from J95/delta flags."""
 axes={}
 for label,pairs in(('panel_at_H4096',((64,4096),(128,4096),(256,4096))),('harmonic_at_P256',((256,1024),(256,2048),(256,4096)))):
  rows=[dict(case_id=cases[pair]['metadata']['case_id'],RMS_max_panel_A_m2=cases[pair]['metadata']['contact_q_native_panel']['RMS_max_panel_A_m2'])for pair in pairs]
  axes[label]=dict(rows=rows,adjacent_increases=[rows[i+1]['RMS_max_panel_A_m2']>rows[i]['RMS_max_panel_A_m2']for i in range(len(rows)-1)])
 return dict(axes=axes,edge_continuum_Jmax_converged=False,not_an_asymptotic_convergence_test=True,
  interpretation='Preserve every native panel maximum and any increase. Passing integral/J95/slab-field delta flags never establishes the continuum edge maximum or human skin burden.')

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 """Root-only conditional five-case transferred-coefficient batch; exclusive per-case outputs and resume index."""
 require(spec==make_spec()and callable(guard),'Exact transferred-coefficient method and explicit root guard')
 check(guard,deadline_monotonic);out=Path(output_dir)
 require(out.is_absolute()and out.parent==Path('/dev/shm')and out.name.startswith('task1-contact-edge-surrogate-')and out.is_dir()and not out.is_symlink()and out==out.resolve(),'Owner-created canonical surrogate benchmark output')
 import numpy as np
 physical_count=len(CASE_PAIRS)*(PLAN['field_x_midpoints']*PLAN['field_z_midpoints']+PLAN['surface_x_midpoints'])
 require(physical_count<PLAN['max_all_physical_evaluation_samples'],'Total fixed physical evaluation count below800000')
 spec_raw=encoded(spec);spec_sha=sha(spec_raw);method_sha=file_sha(Path(__file__).resolve());spec_path=out/'benchmark-spec.json'
 if spec_path.exists():require(spec_path.read_bytes()==spec_raw,'Preserve exact registered transferred-coefficient specification')
 else:
  with spec_path.open('xb')as stream:stream.write(spec_raw)
 cases_dir=out/'cases';progress=out/'progress';cases_dir.mkdir(exist_ok=True);progress.mkdir(exist_ok=True)
 pinned_inputs=required_inputs();analytic=analytic_validation(np,guard,deadline_monotonic,spec);cases={};completed=[];new_partial_RHS=0;reused_cases=0
 for P,H in CASE_PAIRS:
  check(guard,deadline_monotonic);require(file_sha(Path(__file__).resolve())==method_sha,'Frozen benchmark method source changed');cid='P%d-H%d'%(P,H);meta_path=cases_dir/(cid+'.json');array_path=cases_dir/(cid+'.npz');marker=progress/(cid+'.json')
  if meta_path.exists():
   meta=json.loads(meta_path.read_bytes());require(meta['spec_sha256']==spec_sha and meta['method_sha256']==method_sha and meta['case_id']==cid and meta['arrays_SHA256']==file_sha(array_path),'Completed same-case metadata/array identity for resume')
   with np.load(array_path,allow_pickle=False)as saved:arrays={key:saved[key]for key in saved.files}
   result=dict(metadata=meta,arrays=arrays);reused_cases+=1
  else:
   require(not array_path.exists()and not marker.exists(),'Preserve partial case output; root recovery/new run required')
   result=_case(np,P,H,spec,guard,deadline_monotonic);new_partial_RHS+=1
   with array_path.open('xb')as stream:np.savez_compressed(stream,**result['arrays'])
   result['metadata'].update(spec_sha256=spec_sha,method_sha256=method_sha,arrays_SHA256=file_sha(array_path));new_json(meta_path,result['metadata'])
  record=dict(case_id=cid,metadata_SHA256=file_sha(meta_path),arrays_SHA256=file_sha(array_path),spec_sha256=spec_sha,method_sha256=method_sha,complete=True)
  if marker.exists():require(json.loads(marker.read_bytes())==record,'Immutable completed-case checkpoint mismatch')
  else:new_json(marker,record)
  completed.append(record);index=dict(schema='task1-surrogate-contact-edge-resume-index-v1',spec_sha256=spec_sha,method_sha256=method_sha,completed=list(completed),remaining=['P%d-H%d'%v for v in CASE_PAIRS if 'P%d-H%d'%v not in{row['case_id']for row in completed}],no_completed_case_recomputed=True)
  snapshot=out/('resume-index-%02d.json'%len(completed))
  if snapshot.exists():require(json.loads(snapshot.read_bytes())==index,'Preserved resume snapshot mismatch')
  else:new_json(snapshot,index)
  temp=out/('resume-index-%d.new'%time.time_ns());new_json(temp,index);temp.replace(out/'resume-index.json');cases[P,H]=result
 checks=[_adjacent(np,cases[64,4096],cases[128,4096],'panel_at_H4096'),_adjacent(np,cases[128,4096],cases[256,4096],'panel_at_H4096'),_adjacent(np,cases[256,1024],cases[256,2048],'harmonic_at_P256'),_adjacent(np,cases[256,2048],cases[256,4096],'harmonic_at_P256')]
 summary=dict(schema='task1-surrogate-equipotential-contact-slab-result-v1',status='five_finite_Galerkin_cases_calculated_diagnostic_unadopted',spec=spec,analytic_contract=analytic,cases={value['metadata']['case_id']:value['metadata']for value in cases.values()},adjacent_diagnostics=checks,edge_maximum_diagnostics=edge_maximum_diagnostics(cases),all_diagnostic_flags_pass=all(row['all_diagnostic_flags_pass']for row in checks),
  completed_unique_cases=len(cases),surrogate_slab_RHS=5,actual_new_surrogate_slab_RHS_this_call=new_partial_RHS,completed_partial_cases_reused=reused_cases,analytic_contract_extra_slab_RHS=1,analytic_contract_RHS_this_call=1,method_sha256=method_sha,input_sha256=pinned_inputs,coefficient_transfer=spec['coefficient_transfer'],total_fixed_physical_evaluation_samples=physical_count,source_voltage_peak_V=1.,source_voltage_Vpp=2.,current_unit='A/m out-of-plane',complex_power_unit='W/m out-of-plane',new_actual_phantom_PDE=0,new_actual_four_pad_CEM_RHS=0,
  limitations=['Partial contact reference remains finite in both panel and harmonic discretization','Full-contact1D analytic contract is not an independent solution of the partial-contact problem','Panel Jmax and finite Fourier surface flux are separate approximations','Fixed-grid visualization can have quadrature error; Parseval slab norm refers only to the finite series','Transferred HREF-MIX coefficients do not transfer actual4pad source/circuit, human anatomy, validated skin contact, TIS, activation, safety or experimental verification'],candidate_adopted=False,resume_index_sha256=file_sha(out/'resume-index.json'))
 check(guard,deadline_monotonic);return dict(summary=summary,arrays={})
