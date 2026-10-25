"""Scalar-only geometry/resource feasibility; no eigen, CEM or PDE execution.

Import performs no I/O, graph construction, mask counts or scientific imports.
Only the root invokes build under its existing locks and finite resource guards.
"""
from __future__ import annotations
import hashlib,json,math,time
from fractions import Fraction
from pathlib import Path

BASE=Path('/dev/shm/task1-layer-dtn-xy102-20261025-run')
BASE_COMMIT='ea11fdd9198a7e0c82d91d87f594a5063087486a'
BASE_SUMMARY_SHA='33e6585e3ff2c797a8fb3cb42040d252dfe5da1aa848aa3817feb2747b538cd4'
SOURCES=(Path('/dev/shm/task1-layer-dtn-xy102-cem-20261025/source/layer_dtn_cem.py'),Path('/dev/shm/task1-layer-dtn-xy102-20261025/source/layer_dtn_backend.py'))
PLAN=dict(base_uniform_nx=102,physical_diameter_m=.05,physical_layer_thickness_m=[.0001,.005,.005,.015],
 pad_centres_mm=[[-10,-10],[10,10],[10,-10],[-10,10]],pad_width_mm=15.,pad_height_mm=15.,pad_area_m2=.000225,
 geometry_methods=['move_nearest_faces','union_faces'],
 evaluation_options=[dict(id='moved_faces_keep97',geometry='move_nearest_faces',layer_samples=[4,19,18,56],planes=97),
  dict(id='union_faces_keep97',geometry='union_faces',layer_samples=[4,19,18,56],planes=97),
  dict(id='union_faces_explicit90',geometry='union_faces',layer_samples=[4,18,18,50],planes=90)],
 physical_evaluation_cell_cap=800000,CPU_limit=4,total_RSS_plus_all_owned_tmpfs_limit_bytes=8000000000,
 root_scalar_preflight_timeout_seconds=60,future_numerical_child_timeout_seconds=600,
 real_Q_cache_chunk_max_bytes=32*1024**2,no_automatic_method_or_sampling_selection=True,
 new_eigen_runs=0,new_CEM_conditions=0,new_CEM_RHS=0,new_actual_phantom_PDE=0)
VALIDATION_GATES=dict(weighted_null_relative=1e-12,full_contact_analytic_relative=1e-10,
 uniform_limit_operator_relative=1e-12,eigen_residual_spectral_relative=1e-11,
 selected_orthogonality_absolute=2e-10,real_transform_relative=2e-10,
 CEM_loaded_current_residual=2e-7,CEM_KCL=2e-6,CEM_complex_power=2e-7,CEM_reciprocity=2e-7,
 existing_independent_potential_gradient_screen=.05)

def require(ok,message):
 if not ok:raise ValueError(message)
def encoded(value):return(json.dumps(value,allow_nan=False,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def check(guard,deadline):guard();require(deadline is None or time.monotonic()<deadline,'Finite scalar preflight deadline')
def _read(path):
 p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Bounded regular source/metadata input');return p.read_bytes()
def required_inputs():
 refs={str(p):sha(_read(p))for p in SOURCES}
 summary_raw=_read(BASE/'summary.json');require(sha(summary_raw)==BASE_SUMMARY_SHA,'Actual existing XY102 graph metadata identity')
 pub=json.loads(_read(BASE/'result-publication/result-publication.json'));proof=pub['files']['data-native/cloud-layer-dtn-xy102-20261025/summary.json']
 require(pub['status']=='published_readback_verified'and pub['commit']==BASE_COMMIT and proof['SHA256']==BASE_SUMMARY_SHA and proof['readback_passed']is True,'Existing baseline graph metadata fully published')
 summary=json.loads(summary_raw);require(summary['graph']['nodes']==8184 and summary['graph']['h_m']==.05/102,'Actual baseline counts from metadata only, no old graph rerun')
 refs[str(BASE/'summary.json')]=BASE_SUMMARY_SHA;refs[str(BASE/'result-publication/result-publication.json')]=sha(_read(BASE/'result-publication/result-publication.json'))
 return refs

def make_spec():
 return dict(schema='task1-contact-conforming-scalar-preflight-spec-v1',plan=json.loads(json.dumps(PLAN)),proposed_validation_gates=dict(VALIDATION_GATES),
  baseline_geometry_metadata=dict(commit=BASE_COMMIT,summary_SHA256=BASE_SUMMARY_SHA,XY_nodes=8184,h_m=.05/102),
  insertion_face_coordinates_m=[-.0175,-.0025,.0025,.0175],
  physical_geometry='Same50mm body/four-layer thickness/pad polygons; new Cartesian staircase and local spacing are numerical geometry changes and must be compared on physical overlap.',
  material_and_contact='No material/gamma/contact data evaluated here. Future admission must pin unchanged owner-selected latest verified material/contact/frequency inputs; no invented constants or inherited experimental validation.',
  mass_operator='M_i=dx_i*dy_i; K_ij=-shared_face_length/centre_distance, diagonal=sum conductances; A=M^(-1/2) K M^(-1/2)',
  modal_operator='I_tissue=M^(1/2) Q diag(Y) Q^T M^(1/2) phi; Q real Euclidean-orthonormal, zeroq=sqrt(M)/sqrt(sumM)',
  reconstruction='b=Q^T sqrt(M) phi_top; phi(z)=M^(-1/2) Q diag(F(z)) b; integratedJ(z)=sqrt(M) Q diag(Junit(z)) b',
  contacts='Conforming full physical cell faces only, G=actual_area/zA with noSC halfcell; pad0/1 two outputs each50ohm, pad2/3 common0V, inactive output0V behind50ohm.',
  zero_mode='Actual insulated bottom givesY(0)=0; a grounded-bottom full-contact analytic validation is separately labelled synthetic and must not change actual boundary conditions.',
  cell_semantics='Unique physical evaluation samples=Nxy*selected_planes <=800000; densebasis entries are disclosed storage, not cells. Streaming/chunking cannot bypass total evaluation cap.',
  resource_semantics='No resource admission from approximate historic4.4GB tmpfs. Root supplies fresh aggregate task-tmpfs/other-owned-RSS snapshot; theoretical passing estimate is not a runtime guarantee.',
  required_before_actual_four_pad=['nonuniform constant/mass/null and uniform-grid reduction checks','separate grounded-full-contact analytic current/power check','controlled Fourier/MMS operator consistency/refinement with nonuniform waves NOT assumed eigenmodes','weighted eigen residual/orthogonality and transforms','fresh resource/cell/sampling admission and source publication'],
  no_old_graph_recomputation=True,no_actual_solver_admission=True,no_criteria_relaxation=True,candidate_adopted=False)

def axis_faces(method,nx=102):
 require(method in PLAN['geometry_methods']and nx==102,'Only declared new geometry methods')
 radius=Fraction(1,40);h=Fraction(1,20*nx);original=[-radius+i*h for i in range(nx+1)];fixed=[Fraction(-7,400),Fraction(-1,400),Fraction(1,400),Fraction(7,400)]
 shifts=[]
 if method=='union_faces':faces=sorted(set(original+fixed))
 else:
  faces=list(original);used=set()
  for target in fixed:
   index=min(range(1,nx),key=lambda k:(abs(original[k]-target),k));require(index not in used,'Nearest-face relocation collision');used.add(index)
   require(abs(original[index]-target)<=h/2,'Declared nearest existing face displacement bound')
   shifts.append(dict(index=index,original_m=float(original[index]),new_m=float(target),shift_m=float(target-original[index])));faces[index]=target
 require(faces[0]==-radius and faces[-1]==radius and all(a<b for a,b in zip(faces[:-1],faces[1:]))and all(v in faces for v in fixed),'Positive exact face intervals; fixed body bounds and all physical pad edges')
 if method=='move_nearest_faces':require(len(faces)==nx+1,'Relocation retains102 cells across')
 return faces,shifts

def resource_estimate(nodes,edges,snapshot=None):
 B=nodes*nodes*8;workspace=512*1024**2;vectors=256*1024**2;sparse_vectors=(nodes+2*edges)*64
 # Intentionally conservative coexistence: input, returnedQ, possible backend
 # inputcopy, localQcache, workspace and vectors plus all historic task memory.
 incremental=4*B+workspace+vectors+sparse_vectors
 base=dict(real_dense_input_bytes=B,real_returned_Q_bytes=B,possible_real_backend_copy_bytes=B,new_local_Q_cache_bytes=B,
  workspace_allowance_bytes=workspace,vector_library_allowance_bytes=vectors,sparse_scalar_allowance_bytes=sparse_vectors,conservative_incremental_bytes=incremental,
  eigenmatrix_entries=nodes*nodes,max_cache_chunk_bytes=PLAN['real_Q_cache_chunk_max_bytes'],cache_chunks=(B+PLAN['real_Q_cache_chunk_max_bytes']-1)//PLAN['real_Q_cache_chunk_max_bytes'],
  peak_estimate_not_measured=True,no_complex_dense_Q_or_K=True)
 if snapshot is None:return dict(**base,status='blocked_pending_fresh_owner_memory_snapshot',budget_estimate_within_limit=None,actual_worker_admitted=False)
 require(set(snapshot)>=set(('owned_tmpfs_bytes','other_owned_RSS_bytes'))and all(type(snapshot[k])is int and snapshot[k]>=0 for k in('owned_tmpfs_bytes','other_owned_RSS_bytes')),'Fresh integer owner memory snapshot')
 projected=snapshot['owned_tmpfs_bytes']+snapshot['other_owned_RSS_bytes']+incremental;limit=PLAN['total_RSS_plus_all_owned_tmpfs_limit_bytes']
 return dict(**base,status='theoretical_budget_estimate_passes_runtime_gate_pending'if projected<=limit else'blocked_conservative_memory_estimate',snapshot=snapshot,projected_RSS_plus_all_owned_tmpfs_bytes=projected,
  approved_limit_bytes=limit,budget_estimate_within_limit=projected<=limit,actual_worker_admitted=False)

def _geometry(method,guard,deadline):
 faces,shifts=axis_faces(method);width=[b-a for a,b in zip(faces[:-1],faces[1:])];centres=[(a+b)/2 for a,b in zip(faces[:-1],faces[1:])];radius=Fraction(1,40)
 nodes=[];lookup={}
 for j,y in enumerate(centres):
  if j%8==0:check(guard,deadline)
  for i,x in enumerate(centres):
   if x*x+y*y<radius*radius:lookup[i,j]=len(nodes);nodes.append((i,j,x,y,width[i]*width[j]))
 require(nodes,'Nonempty proposed D50 staircase');neighbors=[[]for _ in nodes];degree=[0]*len(nodes);edge=[];Kdiag=[0.]*len(nodes)
 for p,(i,j,x,y,area)in enumerate(nodes):
  if p%512==0:check(guard,deadline)
  for key,face,distance in(((i+1,j),width[j],(width[i]+width[i+1])/2 if i+1<len(width)else None),((i,j+1),width[i],(width[j]+width[j+1])/2 if j+1<len(width)else None)):
   if key in lookup:
    q=lookup[key];w=float(face/distance);require(w>0,'Positive shared-face stiffness');edge.append((p,q,w));Kdiag[p]+=w;Kdiag[q]+=w;degree[p]+=1;degree[q]+=1;neighbors[p].append(q);neighbors[q].append(p)
 seen={0};todo=[0]
 while todo:
  for q in neighbors[todo.pop()]:
   if q not in seen:seen.add(q);todo.append(q)
 require(len(seen)==len(nodes),'Connected nonuniform graph, one constant nullmode candidate')
 mass=[float(n[4])for n in nodes];roots=[math.sqrt(m)for m in mass];total_mass=math.fsum(mass);qzero=[v/math.sqrt(total_mass)for v in roots]
 diagonal=[v/m for v,m in zip(Kdiag,mass)];off=[0.]*len(nodes);action=[a*q for a,q in zip(diagonal,qzero)]
 for p,q,w in edge:
  a=w/(roots[p]*roots[q]);off[p]+=a;off[q]+=a;action[p]-=a*qzero[q];action[q]-=a*qzero[p]
 bound=max(d+o for d,o in zip(diagonal,off));nullrelative=max(abs(v)for v in action)/max(bound*max(qzero),1e-300)
 rects=[(Fraction(-7,400),Fraction(-1,400),Fraction(-7,400),Fraction(-1,400)),(Fraction(1,400),Fraction(7,400),Fraction(1,400),Fraction(7,400)),(Fraction(1,400),Fraction(7,400),Fraction(-7,400),Fraction(-1,400)),(Fraction(-7,400),Fraction(-1,400),Fraction(1,400),Fraction(7,400))]
 pads=[];pad_of_node={}
 for pad,(xl,xu,yl,yu)in enumerate(rects):
  total=Fraction(0);count=0
  require(all(x*x+y*y<radius*radius for x in(xl,xu)for y in(yl,yu)),'Entire physical square pad strictly inside D50 circle')
  for p,(i,j,x,y,area)in enumerate(nodes):
   ox=max(Fraction(0),min(faces[i+1],xu)-max(faces[i],xl));oy=max(Fraction(0),min(faces[j+1],yu)-max(faces[j],yl));contact=ox*oy
   if contact:
    require(contact==area and p not in pad_of_node,'Contact-conforming fullcell face and disjoint pad masks; no partial scaling')
    pad_of_node[p]=pad;total+=contact;count+=1
  require(total==Fraction(9,40000),'Exact225mm² physical pad area')
  pads.append(dict(pad=pad,full_contact_faces=count,exact_area_numerator=total.numerator,exact_area_denominator=total.denominator,area_m2=float(total),all_contact_fractions_exactly_one=True))
 geometry=dict(method=method,cells_across=len(width),XY_nodes=len(nodes),undirected_edges=len(edge),connected_components=1,source_node_order='j then i over exact rational center-inside circle',
  moved_faces=shifts,minimum_dx_m=float(min(width)),maximum_dx_m=float(max(width)),maximum_abs_face_shift_m=max((abs(v['shift_m'])for v in shifts),default=0.),
  represented_staircase_area_m2=total_mass,physical_circle_area_m2=math.pi*.025**2,baseline_verified_uniform_area_m2=8184*(.05/102)**2,
  represented_area_difference_from_verified_uniform_m2=total_mass-8184*(.05/102)**2,mass_min_m2=min(mass),mass_max_m2=max(mass),degree_min=min(degree),degree_max=max(degree),
  A_Gershgorin_upper_bound_per_m2=bound,weighted_zero_scalar_relative_residual=nullrelative,weighted_zero_scalar_gate=VALIDATION_GATES['weighted_null_relative'],weighted_zero_scalar_passed=nullrelative<=VALIDATION_GATES['weighted_null_relative'],
  zero_vector='sqrt(M)/sqrt(sumM), NOT a constant Euclidean vector',pad_area_proofs=pads,full_face_contacts=True,
  geometry_table_SHA256=sha(encoded(dict(axis_numerators=[v.numerator for v in faces],axis_denominators=[v.denominator for v in faces],ij=[[n[0],n[1]]for n in nodes],mass_m2=mass,edges=edge))),
  unchanged_body_and_physical_pads=True,staircase_projection_required=True,new_eigen_or_CEM_runs=0)
 arrays=dict(axis_faces_m=[float(v)for v in faces],ix=[n[0]for n in nodes],iy=[n[1]for n in nodes],mass_m2=mass,edge_p=[e[0]for e in edge],edge_q=[e[1]for e in edge],edge_stiffness=[e[2]for e in edge])
 return geometry,arrays

def build(spec,guard,deadline_monotonic=None,memory_snapshot=None):
 require(spec==make_spec()and callable(guard),'Immutable scalar-only proposal and root guard');check(guard,deadline_monotonic);required_inputs();geometries={};arrays={}
 for method in PLAN['geometry_methods']:
  geometry,table=_geometry(method,guard,deadline_monotonic);geometries[method]=geometry
  for key,value in table.items():arrays[method+'_'+key]=value
 options=[]
 for option in PLAN['evaluation_options']:
  geometry=geometries[option['geometry']];n=geometry['XY_nodes'];planes=option['planes'];cells=n*planes;cap=cells<=PLAN['physical_evaluation_cell_cap'];resources=resource_estimate(n,geometry['undirected_edges'],memory_snapshot)
  options.append(dict(**option,XY_nodes=n,physical_evaluation_cells=cells,maximum=800000,physical_evaluation_cap_passed=cap,
   sampling_changed=planes!=97,resources=resources,status='blocked_physical_evaluation_cap'if not cap else'pending_validation_and_explicit_owner_selection',
   no_like_sampled_fit_or_E_TIS_convergence_claim=True,actual_eigen_or_CEM_admitted=False))
 check(guard,deadline_monotonic)
 return dict(summary=dict(schema='task1-contact-conforming-scalar-preflight-result-v1',status='geometry_resource_options_only_unadmitted',spec=spec,geometries=geometries,evaluation_options=options,
  actual_new_eigen_runs=0,actual_new_CEM_conditions=0,actual_new_CEM_RHS=0,actual_old_uniform_graph_runs=0,automatic_option_selected=None,
  holds=dict(nonuniform_operator_MMS_required=True,weighted_eigen_validation_required=True,fullcontact_nonzero_current_validation_required=True,fresh_resource_snapshot_required=memory_snapshot is None,
   no_criteria_relaxation=True,no_silent_sampling_change=True,actual_material_circuit_contact_changes=False,candidate_adopted=False,full_convergence=False,experimental_validation=False)),arrays=arrays)
