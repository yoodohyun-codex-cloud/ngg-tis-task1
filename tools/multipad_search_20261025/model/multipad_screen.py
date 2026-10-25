"""Proposed grouped physical-pad screen using exactly two source output nodes.

No I/O, NumPy import, cached arrays or numerical work occurs on import. The sole
registered root owner calls build. Original reference/native outputs are read
only. Full fields are streamed per driven RHS; candidates are never adopted by
this screening module and old convergence failures remain held.
"""
from __future__ import annotations
import csv,hashlib,io,json,math,sys,time
from pathlib import Path
import frozen_coarse_cem as base
import provisional_field

SOURCE=Path('/dev/shm/task1-multipad-extension-20261025/source')
CATALOG_SOURCE=SOURCE
RUN=Path('/dev/shm/task1-multipad-extension-20261025-run')
REFERENCE=Path('/dev/shm/task1-layer-dtn-cem-20261025-run')
REFERENCE_COMMIT='e4c09902bf529b4111c006dd4b4fb6681ca81252'
REFERENCE_PUBLICATION_SHA='d9eb06ea685eea8b00e89336d8394e34f994ef4672c453fa0844ff9aa1a8826a'
REFERENCE_SUMMARY_SHA='bfe77b2968dc65255f8fcee276166d11508428cb4e68278332a4ab21929bea63'
REFERENCE_ARRAYS_SHA='58fd401921747455816a81f4f30580db12d33e3fd721c427ea53564e50f8ec3d'
LAYERS=('sc','dermis','fat','muscle')
EXPECTED_IDS=('B0-square15-c10-diagonal','MP8-vertical-strips','MP12-vertical-strips','MP16-subpad2x2')
H=.0005;NXY=7860;COUNTS=(8,19,18,56);FREQUENCIES=(2000,2010);THICKNESS=(.0001,.005,.005,.015)
MAX_FILE=80*1024**2

def require(ok,message):
 if not ok:raise ValueError(message)
def pair(v):return base.pair(v)
def cv(v):return complex(v['real'],v['imaginary'])
def digest(path):return base._hash_file(path)
def read_json(path,expected=None):
 p=Path(path);require(p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Bounded canonical JSON metadata');raw=p.read_bytes();require(expected is None or hashlib.sha256(raw).hexdigest()==expected,'Metadata SHA mismatch: '+str(p));return json.loads(raw)
def encoded(value):return (json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def new_json(path,value):
 raw=encoded(value)
 with Path(path).open('xb')as f:f.write(raw)
def check(guard,deadline):base.check(guard,deadline)
def archive(np,path,**arrays):
 with Path(path).open('xb')as f:np.savez_compressed(f,**arrays)
 require(Path(path).stat().st_size<MAX_FILE,'Preserved raw archive exceeds preregistered80MiB publication bound')
 return dict(path=str(path),bytes=Path(path).stat().st_size,SHA256=digest(path))

def _catalog(spec=None):
 if spec is not None:return spec
 sys.path.insert(0,str(CATALOG_SOURCE))
 import multipad_catalog
 return multipad_catalog.make_spec(RUN)

def _reference_proof():
 pub=read_json(REFERENCE/'result-publication/result-publication.json',REFERENCE_PUBLICATION_SHA)
 require(pub['status']=='published_readback_verified'and pub['commit']==REFERENCE_COMMIT,'Actual coarse reference publication')
 for name,sha in(('reference-summary.json',REFERENCE_SUMMARY_SHA),('reference-arrays.npz',REFERENCE_ARRAYS_SHA)):
  proof=pub['files']['data-native/cloud-layer-dtn-cem-20261025/'+name];require(proof['SHA256']==sha and proof['readback_passed']is True,'Direct original coarse-CEM readback proof')
 summary=read_json(REFERENCE/'reference-summary.json',REFERENCE_SUMMARY_SHA);require(summary['physical_gates_passed']is True and summary['actual_new_CEM_RHS']==2,'Previously completed compatible reference')
 return pub,summary

def _admission(value=None):
 if value is not None:return value
 path=SOURCE/'root-admission.json'
 return read_json(path)if path.is_file()else None

def _first8_metadata(admission):
 require(admission is not None and admission.get('schema')=='task1-grouped-multipad-root-admission-v1'and admission.get('status')=='selected_finite_multipad_screen'and admission.get('root_selected')is True,'Separate positive root finite selection after actual first8 results is required')
 require(admission.get('maximum_new_RHS')==8 and admission.get('physical_pad_counts')==[4,8,12,16]and admission.get('independent_outputs')==2 and admission.get('candidate_adopted')is False,'Exact finite grouped-family scope; no pad/output conflation')
 run=Path(admission['first8_run']);pubpath=run/'result-publication/result-publication.json';pub=read_json(pubpath,admission['first8_publication_sha256']);require(pub['status']=='published_readback_verified'and pub['commit']==admission['first8_result_commit']and len(pub['commit'])==40,'Actual completed first8 publication root decision identity')
 def proof(path,expected=None):
  relative=Path(path).relative_to(run).as_posix();matches=[row for target,row in pub['files'].items()if target.endswith('/'+relative)];require(len(matches)==1 and matches[0]['readback_passed']is True,'Exactly one actual first8 direct readback proof');row=matches[0];require(expected is None or row['SHA256']==expected,'First8 original SHA conflict');return row['SHA256']
 summarypath=run/'summary.json';summary=read_json(summarypath,proof(summarypath));require(summary['status']=='provisional_eight_layout_screen_computed_unadopted'and summary['completed_candidates']==8,'First8 actually completed; not merely a prepared owner')
 baseline=next(row for row in summary['candidates']if row['candidate_id']==EXPECTED_IDS[0]);refs={str(pubpath):admission['first8_publication_sha256'],str(summarypath):proof(summarypath)}
 for f in FREQUENCIES:
  raw=summary['raw_artifacts'][EXPECTED_IDS[0]+'-'+str(f)];refs[raw['path']]=proof(raw['path'],raw['SHA256'])
 return summary,baseline,refs

def required_inputs(catalog_spec=None,root_admission=None):
 """Deferred metadata-only inventory: raw/cache SHA references are not decoded."""
 catalog=_catalog(catalog_spec);phase,manifest=base._phase1_metadata();_reference_proof();refs=dict(catalog['input_pins'])
 refs.update({str(base.PHASE1/'summary.json'):base.PHASE1_SUMMARY_SHA,str(base.PHASE1/'arrays.npz'):base.PHASE1_ARRAYS_SHA,str(base.PHASE1/'eigen-cache/manifest.json'):base.CACHE_MANIFEST_SHA,
  str(REFERENCE/'result-publication/result-publication.json'):REFERENCE_PUBLICATION_SHA,str(REFERENCE/'reference-summary.json'):REFERENCE_SUMMARY_SHA,str(REFERENCE/'reference-arrays.npz'):REFERENCE_ARRAYS_SHA})
 for chunk in manifest['chunks']:refs[chunk['path']]=chunk['SHA256']
 for p in(SOURCE/'frozen_coarse_cem.py',SOURCE/'frozen_layer_dtn_backend.py',SOURCE/'frozen_fourier_v1.py',Path('/workspace/ngg-tis-task1/tis-java/selectivity_volume.py'),Path('/workspace/ngg-tis-task1/tis-java/explore_tis.py'),Path('/workspace/ngg-tis-task1/tis-java/explore_inputs.py')):refs[str(p)]=digest(p)
 admission=_admission(root_admission)
 if admission is not None:
  _,_,first8refs=_first8_metadata(admission);refs.update(first8refs)
  path=SOURCE/'root-admission.json'
  if path.is_file():refs[str(path)]=digest(path)
 return refs

def make_spec(catalog_spec=None,root_admission=None):
 catalog=_catalog(catalog_spec);admission=_admission(root_admission);require(catalog['frequencies']==[2000,2010]and len(catalog['candidates'])==4,'Exactly four proposed area-matched pad-count recipes')
 require(tuple(row['candidate_id']for row in catalog['candidates'])==EXPECTED_IDS,'Fixed baseline and candidate IDs/order')
 for f,output in((2000,0),(2010,1)):
  require(catalog['drives'][str(f)]['output']==output and catalog['drives'][str(f)]['source_peak_V']==.5 and len(catalog['gamma_by_frequency'][str(f)])==4,'Original one-active-output sine drives; .5Vpeak before50ohm')
 for index,(candidate,count)in enumerate(zip(catalog['candidates'],(4,8,12,16))):
  require(candidate['baseline']is(index==0),'Exactly B0 is the reused baseline; never an unannounced fresh control solve')
  require(candidate['physical_pad_count']==count and candidate['independent_outputs']==2 and len(candidate['physical_pad_to_node'])==count and set(candidate['physical_pad_to_node'])=={-1,0,1},'Physical pads map explicitly to exactly two outputnodes and commonGND')
 return dict(schema='task1-proposed-grouped-multipad-screen-spec-v1',catalog=catalog,root_admission=admission,input_sha256=required_inputs(catalog,admission),frequencies_Hz=[2000,2010],maximum_new_driven_RHS=8,expected_new_driven_RHS_with_verified_B0_reuse=6,
  planned_reuse='B0 both carriers reuse actual first8 phi_surface/metal only after root-selected direct SHA/readback proof, identical physical contact mapping/material/circuit/hybridfield ABI. Fresh residual/current/power checks still run. Missing or incompatible B0 reuse is a blocker, not an automatic PDE rerun.',
  grid=dict(h_m=H,nx=100,nxy=NXY,layer_counts=list(COUNTS),cells=NXY*sum(COUNTS),physical_layers_m=list(THICKNESS),radius_mm=25.),
  geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001,
  solver=dict(base.GMRES),physical_gates=dict(base.LIMITS),provisional_field=provisional_field.provenance(),
  source_convention='Exactly two outputnodes, each with one50ohm resistor BEFOREfanout. Physical pads explicitly map to output0/output1/commonGND. Active source1Vpp high-Z=.5Vpeak; other ideal output0V/50ohm; no equal branch-current assumption.',
  power_convention='Layer powers from analytic modal boundary flux and source/contact/50ohm powers; NEVER replaced by cell-centred reconstructed|E|² sums',
  maximum_file_bytes=MAX_FILE,new_eigen_solves=0,new_native_FVM_RHS=0,candidate_adopted=False,source_only_unadmitted=admission is None,
  holds=dict(old_5percent_interface_failures_preserved=True,old_XY_contact_burden_failures_preserved=True,full_SC_XY_bulk_edge_contact_convergence=False,material_contact_hardware_or_experiment_validated=False,provisional_screen_only=True))

def _mask(np,candidate,ij):
 path=Path(candidate['mask_path']);require(digest(path)==candidate['mask_sha256'],'Actual immutable candidate mask bytes');lookup={(int(i),int(j)):p for p,(i,j)in enumerate(ij)};pads=[];cells=[];areas=[]
 for row in csv.DictReader(io.StringIO(path.read_text())):
  p=int(row['pad']);key=(int(row['i']),int(row['j']));area=float(row['area_m2']);require(0<=p<candidate['physical_pad_count']and key in lookup and area==H*H,'Canonical full-face physical pad area, not a fraction or electrical output number');pads.append(p);cells.append(lookup[key]);areas.append(area)
 pads=np.asarray(pads,np.int32);cells=np.asarray(cells,np.int32);areas=np.asarray(areas,float);require(len(areas)>0 and len(set(zip(pads.tolist(),cells.tolist())))==len(areas),'Unique pad/cell contact records')
 covered=np.bincount(cells,weights=areas,minlength=NXY);require(float(covered.max())<=H*H*(1+1e-10),'Disjoint electrode contact faces')
 for p in range(candidate['physical_pad_count']):
  definition=next(r for r in candidate['pads']if r['pad']==p);area=float(areas[pads==p].sum());expected=definition['analytic_area_m2'];require(expected>0 and abs(area-expected)/expected<=1e-10,'Candidate-specific analytic contact area; no old225mm2 assumption')
 return pads,cells,areas

def grouped_contact_state(np,phi,metal,pads,cells,areas,physical_pad_to_node,z_specific):
 """Exact fanout contact state; one potential/node, currents solved per patch."""
 raw_mapping=np.asarray(physical_pad_to_node);mapping=raw_mapping.astype(np.int32);require(np.array_equal(raw_mapping,mapping),'Electrical node mapping must be exact integers, never rounded');pads=np.asarray(pads,np.int32);cells=np.asarray(cells,np.int32);areas=np.asarray(areas,float)
 require(mapping.ndim==1 and len(mapping)>0 and set(mapping.tolist())=={-1,0,1}and pads.shape==cells.shape==areas.shape and np.all((pads>=0)&(pads<len(mapping)))and len(metal)==2,'Explicit physical-pad/node map and exactly two metal variables')
 nodes=mapping[pads];vp=np.zeros(len(pads),np.complex128)
 for node in(0,1):vp[nodes==node]=metal[node]
 q=areas/z_specific*(phi[cells]-vp);qsum=np.zeros(len(phi),np.complex128);np.add.at(qsum,cells,q)
 qphysical=np.asarray([q[pads==p].sum()for p in range(len(mapping))]);qnode=np.asarray([q[nodes==node].sum()for node in(0,1,-1)])
 return dict(metal_contact_voltage=vp,outward_patch_current=q,surface_outward_current=qsum,outward_current_by_physical_pad=qphysical,outward_current_by_node=qnode,contact_node=nodes)

def _profiles(np,Q,eigen,gamma,zs,guard,deadline):
 Y=np.empty(NXY,np.complex128);unitV=np.empty((NXY,5),np.complex128);unitJ=np.empty_like(unitV);factorV=np.empty((NXY,len(zs)),np.complex128);factorJ=np.empty_like(factorV);faces=[0.]
 for t in THICKNESS:faces.append(faces[-1]+t)
 for k,value in enumerate(eigen):
  if k%256==0:check(guard,deadline)
  wave=math.sqrt(float(value));Y[k]=base.kernel.modal_admittance(wave,gamma,THICKNESS);unitV[k],unitJ[k]=base.kernel.stable_profile(wave,gamma,THICKNESS,faces);factorV[k],factorJ[k]=base.kernel.stable_profile(wave,gamma,THICKNESS,zs)
 require(Y[0]==0j and all(np.isfinite(a).all()for a in(Y,unitV,unitJ,factorV,factorJ)),'Finite analytic modal profiles and insulated constant mode')
 diagonal=np.zeros(NXY,np.complex128)
 for first in range(0,NXY,128):
  check(guard,deadline);last=min(NXY,first+128);squared=Q[:,first:last]**2;diagonal+=H*H*(squared@Y[first:last].real+1j*(squared@Y[first:last].imag))
 return dict(Y=Y,unitV=unitV,unitJ=unitJ,V=factorV,J=factorJ,diagonal=diagonal,gamma=np.asarray(gamma,np.complex128))

def _solve(np,Q,profile,pads,cells,areas,physical_pad_to_node,za,output,guard,deadline,cached=None):
 from scipy.sparse.linalg import LinearOperator,gmres
 n=NXY;R=50.;g=areas/za;node_map=np.asarray(physical_pad_to_node,np.int32);nodes=node_map[pads];metalg=np.asarray([g[nodes==node].sum()for node in(0,1)]);gsum=np.bincount(cells,weights=g.real,minlength=n)+1j*np.bincount(cells,weights=g.imag,minlength=n);diagonal=np.r_[profile['diagonal']+gsum,metalg+1/R];require(np.all(abs(diagonal)>1e-30),'Nonzero grouped-CEM preconditioner; exactly one resistor per output beforefanout')
 def tissue(phi):return H*H*base._real_complex_transform(np,Q,profile['Y']*base._real_complex_transform(np,Q,phi,True))
 def split(x):
  phi=x[:n];metal=x[n:];state=grouped_contact_state(np,phi,metal,pads,cells,areas,physical_pad_to_node,za);return phi,metal,state['metal_contact_voltage'],state['outward_patch_current'],state['surface_outward_current'],state['outward_current_by_physical_pad'],state['outward_current_by_node']
 calls=0
 def action(x):
  nonlocal calls
  calls+=1;check(guard,deadline);phi,metal,vp,q,qsum,qpad,qnode=split(x);return np.r_[tissue(phi)+qsum,metal/R-qnode[:2]]
 rhs=np.zeros(n+2,np.complex128);rhs[n+output]=.5/R;history=[];start=time.monotonic()
 if cached is None:
  A=LinearOperator((n+2,n+2),matvec=action,dtype=np.complex128);M=LinearOperator((n+2,n+2),matvec=lambda x:x/diagonal,dtype=np.complex128)
  def callback(v):history.append(float(v));check(guard,deadline)
  x,info=gmres(A,rhs,M=M,rtol=base.GMRES['rtol'],atol=base.GMRES['atol'],restart=base.GMRES['restart'],maxiter=base.GMRES['max_outer_iterations'],callback=callback,callback_type='pr_norm')
 else:x=np.r_[cached['phi_surface'],cached['metal']];info=0
 phi,metal,vp,q,qsum,qpad,qnode=split(x);ideal=np.zeros(2,np.complex128);ideal[output]=.5;Isource=(ideal-metal)/R;tissue_current=tissue(phi);coeff=base._real_complex_transform(np,Q,phi,True)
 Slayer=.5*H*H*np.sum(abs(coeff[:,None])**2*(profile['unitV'][:,:-1]*profile['unitJ'][:,:-1].conj()-profile['unitV'][:,1:]*profile['unitJ'][:,1:].conj()),axis=0)
 Ssource=.5*np.sum(ideal*Isource.conj());Scontact=.5*np.sum((vp-phi[cells])*(-q).conj());Presistor=.5*R*float(np.sum(abs(Isource)**2));Ssum=Slayer.sum()+Scontact+Presistor;scale=max(float(np.linalg.norm(tissue_current)),float(np.linalg.norm(qsum)),float(np.linalg.norm(Isource)),1e-12)
 errors=dict(relative_algebraic_residual=float(np.linalg.norm(np.r_[tissue_current+qsum,metal/R-qnode[:2]]-rhs)/np.linalg.norm(rhs)),relative_loaded_current_residual=float(np.linalg.norm(np.r_[tissue_current+qsum,Isource+qnode[:2]])/scale),relative_all_pad_KCL=float(abs(qpad.sum())/max(float(np.sum(abs(qpad))),1e-12)),relative_output_pad_current=float(np.max(abs(Isource+qnode[:2])/np.maximum(np.maximum(abs(Isource),abs(qnode[:2])),1e-12))),relative_complex_power_error=float(abs(Ssource-Ssum)/max(abs(Ssource),abs(Ssum),1e-12)))
 gates=base.screen_errors(errors);powers=[complex(v)for v in Slayer]+[complex(Scontact),complex(Presistor)];allowance=1e-14+1e-12*max(abs(v)for v in powers);passive=all(v.real>=-allowance for v in powers)
 proof=dict(driven_output=output,source_peak_V=.5,source_high_impedance_Vpp=1.,physical_pad_count=len(physical_pad_to_node),independent_outputs=2,physical_pad_to_node=list(physical_pad_to_node),output_resistors=2,resistor_connection='one50ohm peroutput BEFORE fanout',reused_published_baseline_surface=cached is not None,actual_new_RHS=int(cached is None),gmres_info=int(info),iterations=len(history),history=history,wall_seconds=time.monotonic()-start,matvec_count=calls,physical_gates=gates,passivity_passed=bool(passive),passed=bool(info==0 and gates['passed']and passive),source_complex_power_W=pair(Ssource),layer_complex_power_W=[pair(v)for v in Slayer],contact_complex_power_W=pair(Scontact),source_resistor_power_W=Presistor,source_current_peak_A=[pair(v)for v in Isource],outward_current_by_physical_pad_A=[pair(v)for v in qpad],outward_current_by_node_A={str(node):pair(qnode[index])for index,node in enumerate((0,1,-1))},equal_branch_current_assumed=False,two_basis_reciprocity='not_run_one_driven_RHS_at_each_frequency; prior baseline two-basis reciprocity preserved')
 return dict(phi_surface=phi,metal=metal,source_current=Isource,coeff=coeff,contact_current=-q,contact_J=-q/areas,contact_drop=vp-phi[cells],inward_current_by_physical_pad=-qpad,inward_current_by_node=-qnode,layer_power=Slayer,source_power=Ssource,contact_power=Scontact,resistor_power=Presistor,proof=proof)

def _fields(np,Q,profile,solution,ij,layerids,guard,deadline):
 phi=np.empty((len(layerids),NXY),np.complex128);E=np.empty((len(layerids),NXY,3),np.complex128);coeff=solution['coeff'];gamma=profile['gamma'][layerids]
 for first in range(0,len(layerids),8):
  check(guard,deadline);last=min(len(layerids),first+8);v=base._real_complex_transform(np,Q,coeff[:,None]*profile['V'][:,first:last]).T;j=base._real_complex_transform(np,Q,coeff[:,None]*profile['J'][:,first:last]).T
  phi[first:last]=v;E[first:last,:,:2]=provisional_field.lateral_field(np,v,ij,H,guard);E[first:last,:,2]=j/gamma[first:last,None]
 interface=base._real_complex_transform(np,Q,coeff[:,None]*profile['unitJ'][:,1:4]).T
 require(np.isfinite(phi).all()and np.isfinite(E).all()and np.isfinite(interface).all(),'All streamed provisional phi/E/interfaceJ finite')
 return phi.reshape(-1),E.reshape((-1,3)),interface

def _cached_baseline(np,Q,candidate,pads,cells,areas,catalog,frequency,admission,guard,deadline):
 if not candidate['baseline']:return None
 check(guard,deadline);summary,baseline,refs=_first8_metadata(admission);old=summary['spec'];oldcatalog=old['catalog'];key=str(frequency)
 require(oldcatalog['gamma_by_frequency'][key]==catalog['gamma_by_frequency'][key]and oldcatalog['z_by_frequency'][key]==catalog['z_by_frequency'][key]and old['provisional_field']['derived_field_version']==provisional_field.VERSION,'Exact carrier-specific baseline material/contact/reconstruction ABI, never a cross-frequency copy')
 raw=summary['raw_artifacts'][EXPECTED_IDS[0]+'-'+key];path=Path(raw['path']);require(digest(path)==refs[str(path)]==raw['SHA256'],'Actual selected first8 raw SHA before baseline reuse')
 with np.load(path,allow_pickle=False)as saved:
  require({'phi_surface_peak_V','metal_peak_V','contact_pad','contact_xy_index','contact_area_m2'}.issubset(saved.files),'Baseline raw ABI unavailable; exact blocker instead of automatic fresh solve')
  require(np.array_equal(saved['contact_pad'],pads)and np.array_equal(saved['contact_xy_index'],cells)and np.array_equal(saved['contact_area_m2'],areas),'Cached B0 exactly matches physical contact cells/order/areas')
  phi=np.array(saved['phi_surface_peak_V'],copy=True);metal=np.array(saved['metal_peak_V'],copy=True);require(phi.shape==(NXY,)and metal.shape==(2,)and np.isfinite(phi).all()and np.isfinite(metal).all(),'Finite original driven surface and exactly two metal outputs')
 return dict(phi_surface=phi,metal=metal)

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(spec==make_spec(spec['catalog'],spec['root_admission'])and callable(guard),'Exact proposed grouped-family specification');_first8_metadata(spec['root_admission']);check(guard,deadline_monotonic);out=Path(output_dir or RUN)
 require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink()and out.parent==Path('/dev/shm'),'Canonical unique owner-created output')
 import numpy as np
 import screen_metrics
 sys.path.insert(0,'/workspace/ngg-tis-task1/tis-java')
 from selectivity_volume import native_region_weights
 phase,manifest=base._phase1_metadata();Q,cacheproof=base._load_cache(np,manifest,guard,deadline_monotonic);phasepath=base.PHASE1/'arrays.npz';require(digest(phasepath)==base.PHASE1_ARRAYS_SHA,'Exact published eigen/graph arrays')
 with np.load(phasepath,allow_pickle=False)as saved:eigen=np.array(saved['eigenvalues_per_m2'],copy=True);xy=np.array(saved['XY_m'],copy=True);ij=np.array(saved['ij'],copy=True)
 require(eigen.shape==(NXY,)and xy.shape==ij.shape==(NXY,2),'Same coarse eigen/XY graph ABI');require(hashlib.sha256(xy.astype('<f8',copy=False).tobytes()).hexdigest()==phase['graph']['XY_float64_le_SHA256']and hashlib.sha256(ij.astype('<i4',copy=False).tobytes()).hexdigest()==phase['graph']['ij_int32_le_SHA256'],'Exact graph row order')
 faces,layerlist,zlist=base.kernel.f.make_grid(.5,8,[19,18,56]);faces=np.asarray(faces,float);zs=np.asarray(zlist,float);layerids=np.repeat(np.arange(4),COUNTS);require(len(zs)==101 and len(layerids)*NXY==793860,'Fixed physical101-plane evaluation grid')
 grid=np.column_stack((np.tile(xy[:,0]*1000,len(zs)),np.tile(xy[:,1]*1000,len(zs)),np.repeat(zs*1000,NXY),np.repeat(layerids,NXY),np.repeat(H*H*np.diff(faces),NXY)))
 weights,roi=native_region_weights({key:grid[:,i]for i,key in enumerate(('x_mm','y_mm','z_mm','layer','volume_m3'))},dict(h_xy_mm=.5,radius_mm=25,z_faces_mm=faces*1000,layer_counts=list(COUNTS),geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001),deadline_monotonic=deadline_monotonic)
 archive(np,out/'common-grid-and-ROI.npz',grid=grid,ij=ij,z_faces_m=faces,**{key+'_volume_weight_m3':value for key,value in weights.items()});new_json(out/'ROI-receipt.json',roi)
 catalog=spec['catalog'];profiles={}
 for f in FREQUENCIES:profiles[f]=_profiles(np,Q,eigen,[cv(v)for v in catalog['gamma_by_frequency'][str(f)]],zs,guard,deadline_monotonic)
 records=[];actual_RHS=0;baseline_summary=None;artifacts={};rawdir=out/'rhs';rawdir.mkdir(exist_ok=True);cdir=out/'candidates';cdir.mkdir(exist_ok=True)
 for candidate in catalog['candidates']:
  check(guard,deadline_monotonic);cid=candidate['candidate_id'];pads,cells,areas=_mask(np,candidate,ij);mapping=candidate['physical_pad_to_node'];fields=[];proofs=[];losses=np.zeros(4);current2=np.zeros(2);physical_current2=np.zeros(candidate['physical_pad_count']);node_current2=np.zeros(3);pad_contact_power=np.zeros(candidate['physical_pad_count']);j2=np.zeros(len(areas));drop2=np.zeros(len(areas));sourceP=contactP=resistorP=0.
  for f,output in((2000,0),(2010,1)):
   check(guard,deadline_monotonic);za=cv(catalog['z_by_frequency'][str(f)]);cached=_cached_baseline(np,Q,candidate,pads,cells,areas,catalog,f,spec['root_admission'],guard,deadline_monotonic);solution=_solve(np,Q,profiles[f],pads,cells,areas,mapping,za,output,guard,deadline_monotonic,cached)
   proof=solution['proof'];proof.update(candidate_id=cid,frequency_Hz=f);new_json(rawdir/(cid+'-'+str(f)+'-solve-proof.json'),proof)
   archive(np,rawdir/(cid+'-'+str(f)+'-surface-state.npz'),phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],modal_surface_coeff=solution['coeff'],contact_current_peak_A=solution['contact_current'])
   require(proof['passed'],'Physical CEM gate failed; preserved surface iterate/proof, no criteria relaxation')
   actual_RHS+=proof['actual_new_RHS'];require(actual_RHS<=8,'Maximum separately selected grouped-family RHS');phi,E,interface=_fields(np,Q,profiles[f],solution,ij,layerids,guard,deadline_monotonic)
   raw=archive(np,rawdir/(cid+'-'+str(f)+'-raw.npz'),phi_peak_V=phi,E_peak_V_m=E,interface_downward_J_peak_A_m2=interface,modal_surface_coeff=solution['coeff'],phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],contact_current_peak_A=solution['contact_current'],contact_normal_J_peak_A_m2=solution['contact_J'],contact_drop_peak_V=solution['contact_drop'],contact_pad=pads,physical_pad_to_node=np.asarray(mapping,np.int32),contact_electrical_node=np.asarray(mapping,np.int32)[pads],contact_xy_index=cells,contact_area_m2=areas,inward_current_by_physical_pad_peak_A=solution['inward_current_by_physical_pad'],inward_current_by_node_0_1_GND_peak_A=solution['inward_current_by_node'],layer_complex_power_W=solution['layer_power']);artifacts[cid+'-'+str(f)]=raw;fields.append(E);proofs.append(proof)
   losses+=solution['layer_power'].real;sourceP+=float(solution['source_power'].real);contactP+=float(solution['contact_power'].real);resistorP+=solution['resistor_power'];current2+=abs(solution['source_current'])**2/2;physical_current2+=abs(solution['inward_current_by_physical_pad'])**2/2;node_current2+=abs(solution['inward_current_by_node'])**2/2;j2+=abs(solution['contact_J'])**2/2;drop2+=abs(solution['contact_drop'])**2/2
   for physical in range(candidate['physical_pad_count']):
    select=pads==physical;pad_contact_power[physical]+=.5*za.real*float(np.sum(areas[select]*abs(solution['contact_J'][select])**2))
   new_json(out/('checkpoint-'+cid+'-'+str(f)+'.json'),dict(status='driven_RHS_raw_complete',candidate_id=cid,frequency_Hz=f,actual_new_RHS=proof['actual_new_RHS'],completed_new_RHS=actual_RHS,raw=raw,field_version=provisional_field.VERSION,candidate_adopted=False));del phi,interface,solution
  j=np.sqrt(j2);order=np.argsort(j,kind='stable');index=min(int(np.searchsorted(np.cumsum(areas[order]),.95*float(areas.sum()),side='left')),len(order)-1)
  electrical=dict(source_Vpp_each=1.,source_current_RMS_by_output_A=np.sqrt(current2).tolist(),sum_output_current_RMS_A_bookkeeping=float(np.sqrt(current2).sum()),source_power_W=sourceP,layers_power_W={name:float(losses[i])for i,name in enumerate(LAYERS)},SC_power_W=float(losses[0]),skin_power_W=float(losses[:2].sum()),contact_power_W=contactP,source_resistor_power_W=resistorP,contact_normal_J_RMS_max_A_m2=float(j.max()),contact_normal_J_RMS_P95_A_m2=float(j[order[index]]),contact_voltage_RMS_max_V=float(np.sqrt(drop2.max())))
  per_pad=[]
  for physical in range(candidate['physical_pad_count']):
   selected=pads==physical;v=j[selected];w=areas[selected];order_pad=np.argsort(v,kind='stable');position=min(int(np.searchsorted(np.cumsum(w[order_pad]),.95*float(w.sum()),side='left')),len(v)-1)
   per_pad.append(dict(physical_pad_id=physical,electrical_node=mapping[physical],area_m2=float(w.sum()),current_RMS_A=float(np.sqrt(physical_current2[physical])),contact_J_RMS_max_A_m2=float(v.max()),contact_J_RMS_P95_A_m2=float(v[order_pad[position]]),contact_voltage_RMS_max_V=float(np.sqrt(drop2[selected].max())),contact_real_power_W=float(pad_contact_power[physical]),equal_current_sharing_assumed=False))
  result=screen_metrics.evaluate(np,grid,weights,fields[0],fields[1],np.asarray([cv(v)for v in catalog['gamma_by_frequency']['2000']]),np.asarray([cv(v)for v in catalog['gamma_by_frequency']['2010']]),electrical,guard,deadline_monotonic)
  result['summary']['pads']=candidate['physical_pad_count'];result['summary']['independent_outputs']=2;result['summary']['return_topology']='Physicalpad-to-node mapping explicit; two metal outputs with one50ohm each BEFOREfanout; allnode-1pads hardcommon0V; no equalbranchcurrent assumption'
  record=dict(candidate_id=cid,geometry=candidate,physical_pad_count=candidate['physical_pad_count'],independent_outputs=2,physical_pad_to_node=mapping,per_physical_pad_electrical=per_pad,current_RMS_by_node_0_1_GND_A=np.sqrt(node_current2).tolist(),output_resistors=2,source_physics_proofs=proofs,metrics=result['summary'],provisional_field=provisional_field.provenance(),adopted=False)
  if baseline_summary is None:require(candidate['baseline']is True and cid==EXPECTED_IDS[0],'Baseline must be first');baseline_summary=result['summary']
  record['normalizations']=screen_metrics.normalize(result['summary'],baseline_summary);record['scalar_arrays']=archive(np,cdir/(cid+'-scalars.npz'),**result['arrays']);new_json(cdir/(cid+'-summary.json'),record);records.append(record)
  new_json(out/('checkpoint-'+cid+'-metrics.json'),dict(status='candidate_provisional_metrics_complete',candidate_id=cid,complete_candidates=len(records),actual_new_RHS=actual_RHS));del fields,result
 for row in cacheproof:check(guard,deadline_monotonic);require(digest(row['path'])==row['SHA256'],'Full Q cache SHA again after batch');row['after_passed']=True
 check(guard,deadline_monotonic)
 summary=dict(schema='task1-provisional-grouped-multipad-screen-result-v1',status='provisional_four_recipe_multipad_screen_computed_unadopted',spec=spec,candidates=records,completed_candidates=len(records),actual_new_driven_RHS=actual_RHS,actual_reused_baseline_RHS=8-actual_RHS,physical_pad_counts=[4,8,12,16],independent_outputs=2,output_resistors=2,new_eigen_solves=0,new_native_FVM_RHS=0,raw_artifacts=artifacts,ROI_receipt=roi,cache_reuse=dict(no_new_eigen=True,manifest_SHA256=base.CACHE_MANIFEST_SHA,complete_before_after_SHA_verified=True),holds=spec['holds'],candidate_adopted=False,Windows_saved_verified=False,next_step='Review area-matched segmentation patterns and changed coverage/centroids/gaps; do not attribute differences solely to padcount or increase electricaloutputs. Preserve all original uncertainty and convergence failures.')
 return dict(summary=summary,arrays={})
