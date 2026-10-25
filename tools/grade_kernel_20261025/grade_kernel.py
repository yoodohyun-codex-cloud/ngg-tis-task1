"""Independent periodic-log NtD operator verification and conditional edge batch.

No imports of NumPy, arrays, data reads or solves occur on import. The default
stage is full-period constant/Fourier manufactured verification. The partial
ideal equipotential patch is a separate root-admitted stage. This is a 2D slab
benchmark; zero actual 3D phantom cells/RHS and no spatial E reconstruction.
"""
from __future__ import annotations
import hashlib,json,math,time
from decimal import Decimal,localcontext
from pathlib import Path

SOURCE=Path('/dev/shm/task1-contact-graded-kernel-20261025/source')
HREF_SPEC=Path('/dev/shm/task1-contact-edge-surrogate-20261025-run/benchmark-spec.json')
HREF_SPEC_SHA256='3e8dfadadc9a3f39854e61b2aee6ba12c351464f9a5ef8995b5c2c6388f0ae8c'
EXPECTED_GAMMA=dict(real=5.959456590514033e-6,imaginary=2.5055522184188793e-5)
EXPECTED_Z=dict(real=5.5504758759767015e-5,imaginary=-1.2307933145190832e-4)
PAIRS=((128,32),(256,32),(512,8),(512,16),(512,32))
CONTRACTS=dict(linear_residual=1e-10,complex_symmetry=1e-10,constant_relative=1e-10,
 complex_power_balance=1e-10,passivity_relative=1e-12,MMS_panel_nonregression_absolute_allowance=1e-10)
DELTAS=dict(contact_current_complex_relative=.01,source_real_power_relative=.02,
 contact_J_RMS_P95_relative=.05,conditional_operator_slab_RMS_L2_relative=.01)
PLAN=dict(period_width_m=.002,thickness_m=.0001,partial_contact_endpoints_m=[-.0005,.0005],
 boundary_panels=[128,256,512],Gauss_orders=[8,16,32],unique_operator_cases=[list(v)for v in PAIRS],
 correction_positive_modes=64,pair_block=64,base_panels=128,base_edge_width_over_Robin_length=.25,
 nested_bisection_levels=[0,1,2],near_gap_over_max_width=2.,maximum_panel_width_over_period=.25,
 log_F_fallback_cancellation_condition=1e4,Decimal_precision=50,Decimal_check_precision=70,
 maximum_boundary_unknowns=512,actual_3D_cells=0,actual_3D_RHS=0,physical_cell_cap_unchanged=800000,
 CPU_limit=4,total_RSS_plus_ALL_task1_tmpfs_bytes=8000000000,root_admission_required=True,
 spatial_E_reconstruction=False,old_spatial_E_2percent_gate='not_applicable_not_passed')
MMS_MODES=(1,4)
OPERATOR_ACCURACY_GATE=dict(declared_before_first_execution=True,actual_outputs_observed_when_declared=False,finest_panels=512,finest_Gauss_order=32,MMS_forcings=['MMS-mode1','MMS-mode4'],projected_q_nonconstant_relative_L2_limit=.005,
 metric='sqrt(sum_i l_i*abs(q_num_i-exact_panel_average_q_i)^2) / sqrt(integral_period abs(q_exact-q0)^2 dx)',
 scope='Engineering operator-fixture accuracy only; not independent E/skin/physiological/safety validity')
MMS_COEFFICIENTS=dict(q0=dict(real=1.,imaginary=.2),qc=dict(real=.3,imaginary=-.1),qs=dict(real=.2,imaginary=.4))


def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def pair(v):v=complex(v);return dict(real=v.real,imaginary=v.imag)
def cv(v):return complex(v['real'],v['imaginary'])
def python_scalars(v):
 if v is None or type(v)in(bool,str,int):return v
 if type(v)is float:require(math.isfinite(v),'Nonfinite metadata rejected before open');return v
 if isinstance(v,dict):return{k:python_scalars(w)for k,w in v.items()}
 if isinstance(v,(tuple,list)):return[python_scalars(w)for w in v]
 if type(v).__name__=='ndarray':raise TypeError('Arrays require registered NPZ output')
 if getattr(v,'ndim',None)==0 and callable(getattr(v,'item',None)):
  x=v.item()
  if x is None or type(x)in(bool,str,int,float):return python_scalars(x)
 raise TypeError('Unsupported metadata type: '+type(v).__name__)
def encoded(v):return(json.dumps(python_scalars(v),ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def new_json(p,v):
 raw=encoded(v)
 with Path(p).open('xb')as stream:stream.write(raw)
def check(guard,deadline):
 guard();require(deadline is None or time.monotonic()<deadline,'Finite graded-kernel deadline')
def _metadata(path):
 p=Path(path);require(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size<=8*1024**2,'Canonical bounded metadata');return p.read_bytes()
def _href():
 raw=_metadata(HREF_SPEC);require(sha(raw)==HREF_SPEC_SHA256,'Exact original HREF coefficient specification');v=json.loads(raw)
 require(v['coefficient_transfer']['frequency_Hz']==2000 and v['plan']['transferred_gamma_S_m']==EXPECTED_GAMMA and v['plan']['transferred_contact_ohm_m2']==EXPECTED_Z,'Unchanged2000Hz HREF-MIX SC/contact')
 require(v['plan']['period_width_m']==.002 and v['plan']['SC_thickness_m']==.0001 and v['plan']['contact_endpoints_m']==[-.0005,.0005],'Same benchmark physical geometry');return v

def _contact_admission():
 path=SOURCE/'root-graded-admission.json';raw=_metadata(path);obj=json.loads(raw)
 require(obj['schema']=='task1-graded-kernel-contact-admission-v1'and obj['status']=='admitted_after_operator_verification'and obj['root_review_positive']is True and obj['candidate_adopted']is False,'Explicit root-only partial-contact admission')
 require(isinstance(obj['verification_public_commit'],str)and len(obj['verification_public_commit'])==40 and all(c in'0123456789abcdef'for c in obj['verification_public_commit']),'Actual published verification commit')
 summary=Path(obj['verification_summary_path']);receipt=Path(obj['verification_receipt_path'])
 require(sha(_metadata(summary))==obj['verification_summary_SHA256']and sha(_metadata(receipt))==obj['verification_receipt_SHA256'],'Pinned actual verification summary/receipt')
 result=json.loads(_metadata(summary));record=json.loads(_metadata(receipt))
 require(result['schema']=='task1-graded-log-kernel-result-v1'and result['stage']=='verification'and result['verification_passed']is True and record['verification_passed']is True and result['operator_accuracy_passed']is True and record['operator_accuracy_passed']is True and result['operator_accuracy_gate_before_first_execution']==OPERATOR_ACCURACY_GATE and record['operator_accuracy_gate_before_first_execution']==OPERATOR_ACCURACY_GATE and record['schema']=='task1-graded-log-kernel-computation-receipt-v1'and record['stage']=='verification'and record['source_method_SHA256']==file_sha(__file__),'Actual completed positive operator verification; no automatic partial solve')
 require(isinstance(obj.get('MMS_error_review_basis'),str)and bool(obj['MMS_error_review_basis'].strip()),'Root records actual MMS error review before partial-stage admission')
 return obj,{str(path):sha(raw),str(summary):obj['verification_summary_SHA256'],str(receipt):obj['verification_receipt_SHA256']}

def required_inputs(stage='verification'):
 _href();refs={str(HREF_SPEC):HREF_SPEC_SHA256,str(Path(__file__).resolve()):file_sha(__file__)}
 if stage=='graded_contacts':_,more=_contact_admission();refs.update(more)
 else:require(stage=='verification','Two explicit finite stages only')
 return refs

def make_spec(stage='verification'):
 original=_href();require(stage in('verification','graded_contacts'),'Explicit supported stage');admission=None
 if stage=='graded_contacts':admission,_=_contact_admission()
 return dict(schema='task1-graded-log-kernel-spec-v1',stage=stage,plan=json.loads(json.dumps(PLAN)),contracts=dict(CONTRACTS),diagnostic_limits=dict(DELTAS),operator_accuracy_gate_before_first_execution=json.loads(json.dumps(OPERATOR_ACCURACY_GATE)),
  material=dict(gamma_S_m=dict(EXPECTED_GAMMA),zA_ohm_m2=dict(EXPECTED_Z),frequency_Hz=2000,HREF_spec_SHA256=HREF_SPEC_SHA256,original_CEM_spec_SHA256=original['coefficient_transfer']['original_CEM_spec_sha256'],scope=original['material_provenance']),
  voltage_peak_V=dict(real=1.,imaginary=0.),MMS_modes=list(MMS_MODES),MMS_coefficients=json.loads(json.dumps(MMS_COEFFICIENTS)),partial_contact_admission=admission,
  forcing='Entire period prescribed U(x): constant or analytic non-equipotential Fourier MMS ONLY'if stage=='verification'else'Ideal1Vpeak patch, zero flux on top outside exact patch; entire bottom0V',
  registered_synthetic_RHS=15 if stage=='verification'else 5,
  kernel='gamma*K=t/L-log(2|sin(pi*s/L)|)/pi-(2/pi)sum cos(2pi*n*s/L)/(n(exp(4pi*n*t/L)+1))',
  quadrature_scope='Total quadrature operations and peak temporary nodes are separate from boundary panels and actual3D physical cells; no800kcap reinterpretation',
  energy_scope='q^H G q/|gamma|^2 is conditional quadrature-operator bulk energy, not independent spatial field validation; previous spatial E2percent gate N/A',
  source_scope='Separate2D transferred-surrogate slab; no actual4pad/50ohm/human anatomy/skin-contact/activation/safety validation',originals_preserved=True,candidate_adopted=False)


def correction_tail_bound(L,t,N=64):
 a=4*math.pi*t/L
 return (2/math.pi)*math.exp(-a*(N+1))/((N+1)*(-math.expm1(-a)))

def log_F(u):
 return 0. if u==0 else .5*u*u*math.log(abs(u))-.75*u*u

def _decimal_log_rectangle(a,b,c,d,L,shift,precision):
 with localcontext()as context:
  context.prec=precision;A,B,C,D,LL=(Decimal.from_float(float(v))for v in(a,b,c,d,L));C+=Decimal(shift)*LL;D+=Decimal(shift)*LL
  def F(v):return Decimal(0)if v==0 else v*v*abs(v).ln()/2-Decimal(3)*v*v/4
  value=LL*LL*(F((B-C)/LL)-F((A-C)/LL)-F((B-D)/LL)+F((A-D)/LL))
  return float(value)

def log_rectangle(a,b,c,d,L,shift=0,counters=None):
 """Exact log integral; precision fallback evaluates the identical expression."""
 cc=c+shift*L;dd=d+shift*L
 terms=[log_F((b-cc)/L),-log_F((a-cc)/L),-log_F((b-dd)/L),log_F((a-dd)/L)]
 summed=math.fsum(terms);condition=sum(abs(v)for v in terms)/max(abs(summed),1e-300)
 if shift!=0 or condition>PLAN['log_F_fallback_cancellation_condition']:
  if counters is not None:counters['Decimal_F_fallback_pairs']+=1
  return _decimal_log_rectangle(a,b,c,d,L,shift,PLAN['Decimal_precision'])
 return L*L*summed

def base_graded_edges(width,Robin_length):
 """Symmetric geometric base, subsequently bisected without moving old nodes."""
 M=PLAN['base_panels']//2;minimum=Robin_length*PLAN['base_edge_width_over_Robin_length'];half=width/2
 require(width>0 and minimum>0 and M*minimum<half,'Resolvable positive graded contact')
 def total(eta):return minimum*math.fsum(math.exp(j*eta)for j in range(M))
 lo=0.;hi=1.
 while total(hi)<half:hi*=2;require(hi<8,'Bounded geometric grading ratio')
 for _ in range(100):
  middle=(lo+hi)/2
  if total(middle)<half:lo=middle
  else:hi=middle
 eta=(lo+hi)/2;left=[-half];position=-half
 for j in range(M-1):position+=minimum*math.exp(j*eta);left.append(position)
 left.append(0.);edges=left+[-v for v in reversed(left[:-1])]
 require(len(edges)==129 and all(b>a for a,b in zip(edges[:-1],edges[1:])),'Exact symmetric positive128-panel base')
 return edges,dict(base_minimum_requested_m=minimum,base_log_geometric_ratio=eta,base_centre_closure_m=half-total(eta),physical_width_m=width)

def graded_edges(np,P,width,Robin_length):
 require(P in(128,256,512),'Registered nested panel levels only');values,proof=base_graded_edges(width,Robin_length)
 while len(values)-1<P:
  refined=[]
  for a,b in zip(values[:-1],values[1:]):refined.extend((a,(a+b)/2))
  values=refined+[values[-1]]
 edges=np.asarray(values,float);lengths=np.diff(edges);require(np.all(lengths>0)and edges[0]==-width/2 and edges[-1]==width/2 and np.array_equal(edges,-edges[::-1]),'Unmoved physical endpoints and exact mirror refinement')
 proof.update(panels=P,minimum_width_m=float(lengths.min()),maximum_width_m=float(lengths.max()),total_width_m=float(lengths.sum()),nested=True)
 return edges,proof


def assemble_geometry(np,edges,L,t,q,guard,deadline):
 """No row-sum repair, no symmetrization, no eigenvalue clipping."""
 require(q in(8,16,32),'Preregistered Gauss orders only');lengths=np.diff(edges);centres=(edges[:-1]+edges[1:])/2;P=len(lengths)
 require(P<=512 and np.all(lengths>0)and float(lengths.max())<=L/4,'Panel count/nearest periodic-image restriction')
 nodes,weights=np.polynomial.legendre.leggauss(q);w2=weights[:,None]*weights[None,:]
 logarithm=np.empty((P,P),float);counts=dict(total_panel_pairs=P*P,near_pairs=0,far_pairs=0,Decimal_F_fallback_pairs=0,total_Gauss_pair_node_evaluations=0,peak_temporary_pair_node_count=0)
 # Compute both directions independently so the symmetry test is informative.
 for first in range(0,P*P,PLAN['pair_block']):
  check(guard,deadline);flat=np.arange(first,min(P*P,first+PLAN['pair_block']));i=flat//P;j=flat%P
  shifts=np.rint((centres[i]-centres[j])/L).astype(int);delta=centres[i]-centres[j]-shifts*L
  samples=delta[:,None,None]+lengths[i,None,None]*nodes[None,:,None]/2-lengths[j,None,None]*nodes[None,None,:]/2
  require(np.max(abs(samples))<L,'Only the nearest logarithmic singular image can occur')
  gap=np.maximum(0.,abs(delta)-(lengths[i]+lengths[j])/2);near=gap<=PLAN['near_gap_over_max_width']*np.maximum(lengths[i],lengths[j])
  result=np.empty(len(flat),float)
  if np.any(near):
   smooth=-np.log(2*math.pi*np.sinc(samples[near]/L))/math.pi
   result[near]=lengths[i[near]]*lengths[j[near]]/4*np.sum(smooth*w2,axis=(1,2))
   for position in np.flatnonzero(near):
    result[position]-=log_rectangle(float(edges[i[position]]),float(edges[i[position]+1]),float(edges[j[position]]),float(edges[j[position]+1]),L,int(shifts[position]),counts)/math.pi
  if np.any(~near):
   regular=-np.log(2*np.abs(np.sin(math.pi*samples[~near]/L)))/math.pi
   result[~near]=lengths[i[~near]]*lengths[j[~near]]/4*np.sum(regular*w2,axis=(1,2))
  logarithm[i,j]=result;counts['near_pairs']+=int(near.sum());counts['far_pairs']+=int((~near).sum());counts['total_Gauss_pair_node_evaluations']+=len(flat)*q*q;counts['peak_temporary_pair_node_count']=max(counts['peak_temporary_pair_node_count'],int(samples.size))
 N=PLAN['correction_positive_modes'];n=np.arange(1,N+1);k=2*math.pi*n/L;a=4*math.pi*t/L
 weight=np.exp(-a*n)/(n*(1+np.exp(-a*n)));panel=lengths[:,None]*np.sinc(lengths[:,None]*k[None,:]/(2*math.pi));C=panel*np.cos(centres[:,None]*k);S=panel*np.sin(centres[:,None]*k)
 correction=-(2/math.pi)*((C*weight)@C.T+(S*weight)@S.T)
 G=logarithm+t/L*np.outer(lengths,lengths)+correction
 require(np.isfinite(G).all(),'Finite independent geometric kernel matrix')
 root=np.sqrt(lengths);scaled=G/root[:,None]/root[None,:];symmetry=float(np.linalg.norm(G-G.T)/max(float(np.linalg.norm(G)),1e-300));eigen=np.linalg.eigvalsh(scaled)
 psd_scale=max(float(abs(eigen).max()),1e-300);PSD=bool(float(eigen.min())>=-CONTRACTS['passivity_relative']*psd_scale)
 tail=correction_tail_bound(L,t,N)
 proof=dict(**counts,relative_real_symmetry=symmetry,symmetry_passed=symmetry<=CONTRACTS['complex_symmetry'],scaled_G_smallest_eigenvalue_m=float(eigen.min()),scaled_G_largest_eigenvalue_m=float(eigen.max()),PSD_passed=PSD,eigenvalues_clipped=False,
  correction_modes=N,uniform_kernel_tail_bound=tail,maximum_entry_tail_bound_m2=float(lengths.max()**2*tail),constant_and_correction_added_once=True,
  matrix_entries=P*P,boundary_unknowns=P,actual_3D_cells=0,quadrature_operations_are_not_physical_cells=True,physical_cell_cap_unchanged=800000)
 return G,proof


def _forcing(np,kind,edges,L,t,gamma,zA):
 lengths=np.diff(edges);centres=(edges[:-1]+edges[1:])/2
 require(edges[0]==-L/2 and edges[-1]==L/2,'Manufactured/constant verification requires FULL PERIOD contact')
 if kind=='constant':
  q0=1./(zA+t/gamma);coeff=np.asarray([q0],complex);modes=np.asarray([0]);rhs=lengths.astype(complex)
  metadata=dict(name=kind,equipotential=True,top_peak_V=pair(1.),analytic_q_peak_A_m2=pair(q0),full_period=True)
 else:
  m=int(kind.removeprefix('MMS-mode'));q0=cv(MMS_COEFFICIENTS['q0']);qc=cv(MMS_COEFFICIENTS['qc']);qs=cv(MMS_COEFFICIENTS['qs'])
  coeff=np.asarray([q0,(qc-1j*qs)/2,(qc+1j*qs)/2],complex);modes=np.asarray([0,m,-m]);k=2*math.pi*m/L;T=math.tanh(k*t)/(gamma*k)
  U=coeff*np.asarray([zA+t/gamma,zA+T,zA+T])
  phase=np.exp(2j*math.pi*centres[:,None]*modes[None,:]/L);sinc=np.sinc(lengths[:,None]*modes[None,:]/L);rhs=lengths*((phase*sinc)@U)
  metadata=dict(name=kind,equipotential=False,manufactured_non_equipotential_forcing_only=True,mode=m,full_period=True,coefficients=MMS_COEFFICIENTS,
   formula='U=(zA+t/gamma)q0+(zA+Tm)(qc*cos(km*x)+qs*sin(km*x)); no nonzero flux outside a partial patch is used')
 phase=np.exp(2j*math.pi*centres[:,None]*modes[None,:]/L);sinc=np.sinc(lengths[:,None]*modes[None,:]/L)
 mean=(phase*sinc)@coeff
 # Independent exact Fourier moments, not kernel quadrature.
 second=np.zeros(len(lengths),complex)
 for i,n in enumerate(modes):
  for j,m in enumerate(modes):second+=coeff[i]*np.conj(coeff[j])*lengths*np.sinc((n-m)*lengths/L)*np.exp(2j*math.pi*(n-m)*centres/L)
 require(np.max(abs(second.imag))<=1e-12*max(float(np.max(abs(second.real))),1e-300),'Real exact manufactured second moment')
 total=float(second.real.sum());variance=second.real-lengths*abs(mean)**2
 bound=128*np.finfo(float).eps*(abs(second.real)+lengths*abs(mean)**2)
 require(np.all(variance>=-bound),'Only bounded roundoff may affect exact projection variance')
 variance=np.maximum(variance,0.)
 weights=np.asarray([t if n==0 else math.tanh(abs(2*math.pi*n/L)*t)/abs(2*math.pi*n/L)for n in modes])
 exact_bulk=.5*L/gamma*float(np.sum(weights*abs(coeff)**2))
 nonconstant_total=float(L*np.sum(abs(coeff[modes!=0])**2))
 metadata.update(exact_continuous_q_squared_integral_A2_per_m3=total,exact_nonconstant_q_squared_integral_A2_per_m3=nonconstant_total,exact_bulk_complex_power_W_per_m=pair(exact_bulk),projection_variance_roundoff_bound_applied=True,projection_variance_roundoff_clipped_panels=int(np.count_nonzero(second.real-lengths*abs(mean)**2<0)))
 return rhs,mean,variance,total,metadata


def _weighted95(np,values,lengths):
 order=np.argsort(values,kind='stable');index=min(int(np.searchsorted(np.cumsum(lengths[order]),.95*lengths.sum(),side='left')),len(order)-1)
 return float(values[order[index]])


def solve_case(np,spec,P,order,guard,deadline):
 check(guard,deadline);started=time.monotonic();stage=spec['stage'];L=PLAN['period_width_m'];t=PLAN['thickness_m'];gamma=cv(EXPECTED_GAMMA);zA=cv(EXPECTED_Z);width=L if stage=='verification'else .001
 edges,mesh=graded_edges(np,P,width,abs(gamma*zA));lengths=np.diff(edges);root=np.sqrt(lengths)
 G,kernel=assemble_geometry(np,edges,L,t,order,guard,deadline);scaled=G/root[:,None]/root[None,:];alpha=gamma*zA
 M=scaled.astype(np.complex128)+alpha*np.eye(P);A=G/gamma+zA*np.diag(lengths)
 names=['constant']+['MMS-mode%d'%m for m in MMS_MODES]if stage=='verification'else['equipotential_partial']
 force_data=[]
 for name in names:
  if stage=='verification':force_data.append(_forcing(np,name,edges,L,t,gamma,zA))
  else:force_data.append((lengths.astype(complex),None,None,None,dict(name=name,equipotential=True,top_peak_V=pair(1.),full_period=False,top_outside_patch_flux=0.)))
 RHS=np.column_stack([item[0]for item in force_data]);check(guard,deadline);u=np.linalg.solve(M,gamma*RHS/root[:,None]);q=u/root[:,None]
 require(np.isfinite(q).all(),'Finite graded-kernel solutions')
 rows=[];all_pass=kernel['symmetry_passed']and kernel['PSD_passed'];eigen=np.linalg.eigvalsh(scaled);singular=abs(eigen+alpha)
 condition=float(singular.max()/max(float(singular.min()),1e-300));tail=correction_tail_bound(L,t,PLAN['correction_positive_modes'])
 row_sum=G.sum(axis=1);row_relative=float(np.max(abs(row_sum-t*lengths)/(t*lengths)))if stage=='verification'else None
 if stage=='verification':all_pass=all_pass and row_relative<=CONTRACTS['constant_relative']
 for column,(rhs,truth,variance,total,forcing)in enumerate(force_data):
  check(guard,deadline);value=q[:,column];physical=A@value;res=float(np.linalg.norm(physical-rhs)/max(float(np.linalg.norm(rhs)),1e-300));scaled_res=float(np.linalg.norm(M@u[:,column]-gamma*rhs/root)/max(float(np.linalg.norm(gamma*rhs/root)),1e-300))
  current=complex(lengths@value);source=.5*complex(np.vdot(value,rhs));contact=.5*zA*float(lengths@(abs(value)**2));geometric=complex(np.vdot(value,G@value));bulk=.5*geometric/gamma
  power=abs(source-contact-bulk)/max(abs(source),1e-300);real_energy_pass=abs(geometric.imag)<=CONTRACTS['complex_power_balance']*max(abs(geometric),1e-300)and geometric.real>=0
  passive=source.real>0 and contact.real>=-CONTRACTS['passivity_relative']*abs(source)and bulk.real>=-CONTRACTS['passivity_relative']*abs(source)
  passed=res<=CONTRACTS['linear_residual']and scaled_res<=CONTRACTS['linear_residual']and power<=CONTRACTS['complex_power_balance']and real_energy_pass and passive
  jrms=abs(value)/math.sqrt(2);peak=int(np.argmax(jrms));data=dict(forcing=forcing,algebraic_relative_residual=res,normalized_basis_relative_residual=scaled_res,complex_power_relative_error=power,
   real_geometric_energy_relative_imaginary=abs(geometric.imag)/max(abs(geometric),1e-300),geometric_energy_peak=pair(geometric),source_complex_power_W_per_m=pair(source),contact_complex_power_W_per_m=pair(contact),bulk_complex_power_W_per_m=pair(bulk),
   bulk_energy_scope='Conditional quadrature-operator q^H*G*q only; not independent spatial E validation',conditional_operator_slab_RMS_L2_V_m=math.sqrt(geometric.real/(2*L*t*abs(gamma)**2))if real_energy_pass else None,
   contact_current_peak_A_per_m=pair(current),contact_J_RMS_P95_A_m2=_weighted95(np,jrms,lengths),contact_J_RMS_mean_A_m2=float(jrms@lengths/width),contact_J_RMS_max_panel_A_m2=float(jrms[peak]),maximum_panel_width_m=float(lengths[peak]),
   maximum_panel_edge_distance_m=float(min((edges[peak]+edges[peak+1])/2+width/2,width/2-(edges[peak]+edges[peak+1])/2)),peak_scope='Native panel average and sample dependent; no continuum edge maximum',physical_contact_edge_present=stage=='graded_contacts',contracts_passed=bool(passed),passive_real_powers=bool(passive))
  if stage=='verification':
   error_mean=float(np.sum(lengths*abs(value-truth)**2));error_total=error_mean+float(variance.sum());trueL2=math.sqrt(error_total/max(total,1e-300));projection=math.sqrt(float(variance.sum())/max(total,1e-300));meanL2=math.sqrt(error_mean/max(total,1e-300))
   nonconstant=forcing['exact_nonconstant_q_squared_integral_A2_per_m3'];projected_nonconstant=math.sqrt(error_mean/nonconstant)if nonconstant>0 else None
   data.update(projected_q_nonconstant_relative_L2=projected_nonconstant,true_continuous_q_relative_L2=trueL2,exact_panel_mean_q_relative_L2=meanL2,projection_variance_relative_L2=projection,exact_bulk_power_relative_error=abs(bulk-cv(forcing['exact_bulk_complex_power_W_per_m']))/max(abs(cv(forcing['exact_bulk_complex_power_W_per_m'])),1e-300))
   if forcing['name']=='constant':
    expected=cv(forcing['analytic_q_peak_A_m2']);constant=float(np.max(abs(value-expected))/max(abs(expected),1e-300));data.update(constant_q_max_relative_error=constant,constant_q_passed=constant<=CONTRACTS['constant_relative']);passed=passed and constant<=CONTRACTS['constant_relative'];data['contracts_passed']=bool(passed)
  all_pass=all_pass and passed;rows.append(data)
 arrays=dict(panel_edges_m=edges,panel_lengths_m=lengths,G_geometric_m2=G,q_panel_peak_A_m2=q,RHS_integrated_V_m=RHS,forcing_panel_mean_peak_V=RHS/lengths[:,None])
 if stage=='verification':arrays['exact_panel_mean_q_peak_A_m2']=np.column_stack([item[1]for item in force_data])
 metadata=dict(case_id='%s-P%d-Q%d'%(stage,P,order),stage=stage,panels=P,Gauss_order=order,mesh=mesh,kernel=kernel,forcing_rows=rows,all_algebraic_analytic_contracts_pass=bool(all_pass),
  fullperiod_kernel_row_sum_max_relative_error=row_relative,fullperiod_row_sum_expected='G*1=t*panel_length; never repaired'if stage=='verification'else'not_applicable_partial_contact',
  normalized_operator_condition_estimate=condition,condition_scope='Eigenvalue shift of real symmetric length-normalized G; conditional on the separately tested symmetry',scaled_operator_correction_tail_norm_bound_m=tail*width,
  synthetic_RHS_completed=len(names),actual_3D_cells=0,actual_3D_RHS=0,physical_cell_cap_unchanged=800000,spatial_E_reconstructed=False,old_spatial_E_2percent_gate='not_applicable_not_passed',wall_seconds=time.monotonic()-started,candidate_adopted=False)
 return dict(metadata=metadata,arrays=arrays)


def adjacent_case(old,new,axis):
 rows=[]
 for a,b in zip(old['metadata']['forcing_rows'],new['metadata']['forcing_rows']):
  require(a['forcing']['name']==b['forcing']['name'],'Same explicit forcing across an adjacent comparison')
  quantities=(('contact_current_complex_relative',cv(a['contact_current_peak_A_per_m']),cv(b['contact_current_peak_A_per_m'])),
   ('source_real_power_relative',a['source_complex_power_W_per_m']['real'],b['source_complex_power_W_per_m']['real']),
   ('contact_J_RMS_P95_relative',a['contact_J_RMS_P95_A_m2'],b['contact_J_RMS_P95_A_m2']),
   ('conditional_operator_slab_RMS_L2_relative',a['conditional_operator_slab_RMS_L2_V_m'],b['conditional_operator_slab_RMS_L2_V_m']))
  for name,x,y in quantities:
   error=None if x is None or y is None else float(abs(x-y)/max(abs(y),1e-300))
   rows.append(dict(forcing=b['forcing']['name'],metric=name,relative_difference=error,limit=DELTAS[name],passed=error is not None and error<=DELTAS[name]))
 return dict(axis=axis,coarse_case=old['metadata']['case_id'],fine_case=new['metadata']['case_id'],rows=rows,all_flags_pass=all(row['passed']for row in rows),
  interpretation='Finite panel/quadrature diagnostic changes, nonaborting; no continuum or safety inference. Conditional operator energy is not a spatial E field test.',old_spatial_E_2percent_gate='not_applicable_not_passed')


def _MMS_panel_review(cases):
 rows=[]
 for coarse,fine in(((128,32),(256,32)),((256,32),(512,32))):
  for name in('MMS-mode1','MMS-mode4'):
   a=next(row for row in cases[coarse]['metadata']['forcing_rows']if row['forcing']['name']==name);b=next(row for row in cases[fine]['metadata']['forcing_rows']if row['forcing']['name']==name)
   old=a['true_continuous_q_relative_L2'];new=b['true_continuous_q_relative_L2'];limit=CONTRACTS['MMS_panel_nonregression_absolute_allowance']
   rows.append(dict(coarse_case=cases[coarse]['metadata']['case_id'],fine_case=cases[fine]['metadata']['case_id'],forcing=name,coarse_true_q_L2=old,fine_true_q_L2=new,absolute_allowance=limit,passed=new<=old+limit))
 return dict(rows=rows,all_passed=all(row['passed']for row in rows),scope='Independent exact manufactured flux; full-period top U is non-equipotential ONLY in MMS. Projection variance is retained; no convergence order is forced.')


def operator_accuracy_review(cases):
 """Predeclared finest fixture acceptance, normalized without the DC part."""
 fine=cases[OPERATOR_ACCURACY_GATE['finest_panels'],OPERATOR_ACCURACY_GATE['finest_Gauss_order']]['metadata'];rows=[]
 for name in OPERATOR_ACCURACY_GATE['MMS_forcings']:
  value=next(row for row in fine['forcing_rows']if row['forcing']['name']==name)
  error=value['projected_q_nonconstant_relative_L2'];limit=OPERATOR_ACCURACY_GATE['projected_q_nonconstant_relative_L2_limit']
  rows.append(dict(case_id=fine['case_id'],forcing=name,projected_q_nonconstant_relative_L2=error,limit=limit,passed=error is not None and math.isfinite(error)and error<=limit,
   true_continuous_q_relative_L2=value['true_continuous_q_relative_L2'],projection_variance_relative_L2=value['projection_variance_relative_L2']))
 return dict(rows=rows,all_passed=all(row['passed']for row in rows),gate=OPERATOR_ACCURACY_GATE,interpretation='Predeclared before any graded-kernel numerical outputs; operator fixture only, never a safety or spatial E-field gate')


def edge_maximum_review(cases):
 axes={}
 for name,keys in(('panel_at_Q32',((128,32),(256,32),(512,32))),('quadrature_at_P512',((512,8),(512,16),(512,32)))):
  records=[]
  for key in keys:
   meta=cases[key]['metadata'];value=meta['forcing_rows'][0]
   records.append(dict(case_id=meta['case_id'],J_RMS_max_panel_A_m2=value['contact_J_RMS_max_panel_A_m2'],maximum_panel_width_m=value['maximum_panel_width_m'],distance_to_edge_m=value['maximum_panel_edge_distance_m']))
  axes[name]=dict(rows=records,adjacent_increases=[records[i+1]['J_RMS_max_panel_A_m2']>records[i]['J_RMS_max_panel_A_m2']for i in range(len(records)-1)])
 return dict(axes=axes,edge_continuum_Jmax_converged=False,interpretation='Native panel values and increases remain visible; smaller cells or stable integrals/J95 do not prove a continuum maximum or human skin burden.')


def build(spec,guard,deadline_monotonic=None,output_dir=None):
 """One finite root-owned stage, exclusive case snapshots and exact resume."""
 stage=spec['stage'];require(spec==make_spec(stage)and callable(guard),'Exact reviewed stage/method/coefficient specification');check(guard,deadline_monotonic)
 inputs=required_inputs(stage);out=Path(output_dir)
 require(out.is_absolute()and out.parent==Path('/dev/shm')and out.name.startswith('task1-contact-graded-kernel-')and out.is_dir()and not out.is_symlink()and out==out.resolve(),'Owner-created distinct canonical stage directory')
 import numpy as np
 specraw=encoded(spec);specsha=sha(specraw);methodsha=file_sha(__file__);saved=out/'benchmark-spec.json'
 if saved.exists():require(saved.read_bytes()==specraw,'Immutable specification differs; preserve old run')
 else:
  with saved.open('xb')as stream:stream.write(specraw)
 casedir=out/'cases';progress=out/'progress';casedir.mkdir(exist_ok=True);progress.mkdir(exist_ok=True)
 cases={};completed=[];new_rhs=0;reused_rhs=0
 for P,order in PAIRS:
  check(guard,deadline_monotonic)
  for path,digest in inputs.items():require(file_sha(path)==digest,'Frozen stage input/source changed')
  cid='%s-P%d-Q%d'%(stage,P,order);metadata=casedir/(cid+'.json');arrays=casedir/(cid+'.npz');marker=progress/(cid+'.json')
  if metadata.exists():
   info=json.loads(metadata.read_bytes());require(info['spec_SHA256']==specsha and info['source_method_SHA256']==methodsha and info['case_id']==cid and file_sha(arrays)==info['arrays_SHA256'],'Exact completed case for resume')
   # Comparisons use saved scalar metadata. No completed solution/matrix is decoded.
   result=dict(metadata=info,arrays={});reused_rhs+=info['synthetic_RHS_completed']
  else:
   require(not arrays.exists()and not marker.exists(),'Partial output preserved; explicit recovery/new run required')
   result=solve_case(np,spec,P,order,guard,deadline_monotonic);new_rhs+=result['metadata']['synthetic_RHS_completed']
   with arrays.open('xb')as stream:np.savez_compressed(stream,**result['arrays'])
   result['metadata'].update(spec_SHA256=specsha,source_method_SHA256=methodsha,arrays_SHA256=file_sha(arrays));new_json(metadata,result['metadata'])
   result['arrays']={}
  record=dict(case_id=cid,metadata_SHA256=file_sha(metadata),arrays_SHA256=file_sha(arrays),synthetic_RHS_completed=result['metadata']['synthetic_RHS_completed'],spec_SHA256=specsha,source_method_SHA256=methodsha,complete=True)
  if marker.exists():require(json.loads(marker.read_bytes())==record,'Preserved completed-case checkpoint differs')
  else:new_json(marker,record)
  completed.append(record);index=dict(schema='task1-graded-kernel-resume-index-v1',stage=stage,spec_SHA256=specsha,source_method_SHA256=methodsha,completed=list(completed),remaining=['%s-P%d-Q%d'%(stage,p,q)for p,q in PAIRS if(p,q)not in cases and(p,q)!=(P,order)],no_completed_solve_repeated=True)
  snapshot=out/('resume-index-%02d.json'%len(completed))
  if snapshot.exists():require(json.loads(snapshot.read_bytes())==index,'Preserved resume snapshot differs')
  else:new_json(snapshot,index)
  temporary=out/('resume-index-%d.new'%time.time_ns());new_json(temporary,index);temporary.replace(out/'resume-index.json');cases[P,order]=result
 checks=[adjacent_case(cases[128,32],cases[256,32],'panel_at_Q32'),adjacent_case(cases[256,32],cases[512,32],'panel_at_Q32'),adjacent_case(cases[512,8],cases[512,16],'quadrature_at_P512'),adjacent_case(cases[512,16],cases[512,32],'quadrature_at_P512')]
 contracts=all(value['metadata']['all_algebraic_analytic_contracts_pass']for value in cases.values());delta=all(row['all_flags_pass']for row in checks);MMS=_MMS_panel_review(cases)if stage=='verification'else None;accuracy=operator_accuracy_review(cases)if stage=='verification'else None
 verified=bool(contracts and delta and MMS['all_passed']and accuracy['all_passed'])if stage=='verification'else False
 total_rhs=sum(value['metadata']['synthetic_RHS_completed']for value in cases.values());require(total_rhs==spec['registered_synthetic_RHS'],'Exact finite registered RHS count')
 summary=dict(schema='task1-graded-log-kernel-result-v1',status='computed_verification_passed'if verified else'computed_with_diagnostic_holds'if stage=='verification'else'graded_contact_cases_computed_unadopted',stage=stage,spec=spec,
  verification_passed=verified,operator_accuracy_passed=bool(accuracy['all_passed'])if accuracy is not None else False,operator_accuracy_gate_before_first_execution=spec['operator_accuracy_gate_before_first_execution'],operator_accuracy_review=accuracy,all_algebraic_analytic_contracts_passed=bool(contracts),all_delta_flags_passed=bool(delta),MMS_true_error_review=MMS,cases={value['metadata']['case_id']:value['metadata']for value in cases.values()},adjacent_diagnostics=checks,
  edge_maximum_review=edge_maximum_review(cases)if stage=='graded_contacts'else None,total_synthetic_RHS_completed=total_rhs,actual_new_synthetic_RHS_this_call=new_rhs,synthetic_RHS_reused=reused_rhs,
  source_method_SHA256=methodsha,input_SHA256=inputs,resume_index_SHA256=file_sha(out/'resume-index.json'),actual_3D_cells=0,actual_3D_RHS=0,physical_cell_cap_unchanged=800000,
  boundary_unknowns_max=512,quadrature_operations_total=sum(value['metadata']['kernel']['total_Gauss_pair_node_evaluations']for value in cases.values()),peak_temporary_pair_node_count=max(value['metadata']['kernel']['peak_temporary_pair_node_count']for value in cases.values()),quadrature_nodes_are_not_physical_mesh_cells=True,
  spatial_E_reconstructed=False,old_spatial_E_2percent_gate='not_applicable_not_passed',bulk_energy_scope='Conditional G-quadrature operator energy, not independent physical field validation',
  holds=dict(edge_continuum_Jmax_converged=False,actual_four_pad_model_validated=False,human_or_skin_contact_validated=False,experimental_activation_or_safety_validated=False,candidate_adopted=False),
  next_step='Root reviews actual published verification before explicitly admitting any partial-contact stage'if stage=='verification'else'Root reviews graded/quad errors and peak growth; no automatic3D correction or physical candidate adoption')
 receipt=dict(schema='task1-graded-log-kernel-computation-receipt-v1',status=summary['status'],stage=stage,verification_passed=verified,operator_accuracy_passed=bool(accuracy['all_passed'])if accuracy is not None else False,operator_accuracy_gate_before_first_execution=spec['operator_accuracy_gate_before_first_execution'],source_method_SHA256=methodsha,spec_SHA256=specsha,total_synthetic_RHS_completed=total_rhs,actual_new_synthetic_RHS_this_call=new_rhs,synthetic_RHS_reused=reused_rhs,actual_3D_cells=0,actual_3D_RHS=0,resume_index_SHA256=summary['resume_index_SHA256'])
 receiptpath=out/'computation-receipt.json'
 if receiptpath.exists():
  prior=json.loads(receiptpath.read_bytes());require(prior['spec_SHA256']==specsha and prior['source_method_SHA256']==methodsha and prior['total_synthetic_RHS_completed']==total_rhs and prior['verification_passed']==verified,'Preserve completed computation receipt')
 else:new_json(receiptpath,receipt)
 check(guard,deadline_monotonic);return dict(summary=python_scalars(summary),arrays={})
