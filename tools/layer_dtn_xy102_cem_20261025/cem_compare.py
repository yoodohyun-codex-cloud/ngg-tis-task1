"""Physical-coordinate coarse/fine continuous-z CEM comparison; no import IO.

No cross-grid node-index subtraction, E export, TIS inference or native PDE.
Root alone calls this after preserving the new two-RHS reference outputs.
"""
from __future__ import annotations
import hashlib,io,json,math,time
from pathlib import Path
import numpy as np

COARSE=Path('/dev/shm/task1-layer-dtn-cem-20261025-run')
COARSE_COMMIT='e4c09902bf529b4111c006dd4b4fb6681ca81252'
LAYERS=('sc','dermis','fat','muscle')
EDGE_WIDTH_MM=.5
CONTACT_AREA_RELATIVE_LIMIT=1e-10
REVIEW_PERCENT=dict(contact_J_RMS_max_A_m2=5,contact_J_RMS_P95_A_m2=5,contact_drop_RMS_max_V=5,edge_J_RMS_max_A_m2=5,edge_J_RMS_P95_A_m2=5,
 source_power_W=2,contact_power_W=2,source_resistor_power_W=2,skin_power_W=2,edge_contact_power_W=2,sc_power_W=2,dermis_power_W=2,fat_power_W=2,muscle_power_W=2)


def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pair(v):return dict(real=float(complex(v).real),imaginary=float(complex(v).imag))
def _small(p):
 p=Path(p);require(p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Bounded actual metadata/source');return p.read_bytes()


def required_inputs():
 """Deferred metadata/proof/hash declarations; no old/new field or Q decoding."""
 import layer_dtn_cem as model
 refs=model.required_inputs();publication=COARSE/'result-publication/result-publication.json';raw=_small(publication);pub=json.loads(raw)
 require(pub['status']=='published_readback_verified'and pub['commit']==COARSE_COMMIT,'Actual fully published coarse CEM reference');refs[str(publication)]=sha(raw)
 for name in('reference-summary.json','reference-arrays.npz','comparison-summary.json'):
  p=COARSE/name;matches=[v for key,v in pub['files'].items()if key.endswith('/'+name)and v.get('readback_passed')is True]
  require(matches and len(set(v['SHA256']for v in matches))==1,'Unambiguous direct coarse immutable full-SHA proof: '+name);refs[str(p)]=matches[0]['SHA256']
  if p.suffix=='.json':require(sha(_small(p))==refs[str(p)],'Actual coarse metadata unchanged')
 coarse=json.loads(_small(COARSE/'reference-summary.json'));face=Path(coarse['spec']['z_faces_path']);require(sha(_small(face))==coarse['spec']['z_faces_sha256'],'Actual coarse evaluation-face receipt');refs[str(face)]=coarse['spec']['z_faces_sha256']
 for name in('cem_compare.py','physical_projector.py','cem_fit.py'):
  p=Path(__file__).parent/name;refs[str(p)]=sha(_small(p))
 return refs


def _rectangle_area(a,b):
 return max(0.,min(a[1],b[1])-max(a[0],b[0]))*max(0.,min(a[3],b[3])-max(a[2],b[2]))*1e-6

def weighted_stats(values,weights):
 v=np.asarray(values,float);w=np.asarray(weights,float);require(v.shape==w.shape and v.ndim==1 and np.isfinite(v).all()and np.isfinite(w).all()and np.all(w>=0)and w.sum()>0,'Finite scalar quadrature');use=w>0;v=v[use];w=w[use];order=np.argsort(v,kind='stable');cum=np.cumsum(w[order]);total=float(cum[-1]);mean=float(w@v/total)
 def q(p):return float(v[order[min(int(np.searchsorted(cum,p*total,side='left')),len(v)-1)]])
 return dict(min=float(v.min()),p10=q(.1),median=q(.5),p95=q(.95),max=float(v.max()),mean=mean,std=float(np.sqrt(w@((v-mean)**2)/total)),energy_RMS=float(np.sqrt(w@(v*v)/total)),represented_measure=total,quantile='inverse weighted ECDF, no value clipping')


def contact_metrics(arrays,h_mm,pad_rectangles,z_specific):
 """Bind actual fractional contact areas and fixed physical0.5mm pad-edge ring."""
 xy=np.asarray(arrays['contact_xy_mm'],float);area=np.asarray(arrays['contact_area_m2'],float);pads=np.asarray(arrays['contact_pad']);index=np.asarray(arrays['contact_xy_index'],int);graph=np.asarray(arrays['xy_mm'],float)
 require(xy.shape==(len(area),2)and pads.shape==area.shape and np.all(area>0)and np.isfinite(area).all()and np.array_equal(xy,graph[index]),'Exact actual contact-node/area ABI')
 ij=np.rint((xy+25)/h_mm-.5).astype(int);require(np.all(abs((-25+(ij+.5)*h_mm)-xy)<=1e-9),'Canonical physical contact centres')
 ring=np.zeros(len(area));padproof=[]
 for i,((ix,iy),p)in enumerate(zip(ij,pads)):
  require(int(p)==p and str(int(p))in pad_rectangles,'Four declared physical pads');box=(-25+ix*h_mm,-25+(ix+1)*h_mm,-25+iy*h_mm,-25+(iy+1)*h_mm);pad=pad_rectangles[str(int(p))]
  expected=_rectangle_area(box,pad);require(expected>0 and abs(area[i]-expected)/expected<=CONTACT_AREA_RELATIVE_LIMIT,'Exact physical pad/cell clipping, no old indices or area renormalization')
  inside=(pad[0]+EDGE_WIDTH_MM,pad[1]-EDGE_WIDTH_MM,pad[2]+EDGE_WIDTH_MM,pad[3]-EDGE_WIDTH_MM);ring[i]=max(0.,expected-_rectangle_area(box,inside))
 for p in range(4):
  pad=pad_rectangles[str(p)];expected=(pad[1]-pad[0])*(pad[3]-pad[2])*1e-6;represented=float(area[pads==p].sum());edge=float(ring[pads==p].sum());true_edge=expected-(pad[1]-pad[0]-2*EDGE_WIDTH_MM)*(pad[3]-pad[2]-2*EDGE_WIDTH_MM)*1e-6
  require(abs(expected-.000225)<=1e-16 and abs(represented-expected)/expected<=CONTACT_AREA_RELATIVE_LIMIT and abs(edge-true_edge)/true_edge<=CONTACT_AREA_RELATIVE_LIMIT,'Same225mm2 pads and same physical edge strip')
  padproof.append(dict(pad=p,analytic_area_m2=expected,actual_area_m2=represented,edge_area_m2=edge,relative_area_error=abs(represented-expected)/expected))
 result=[];I=np.asarray(arrays['source_current']);drop=np.asarray(arrays['contact_drop']);J=np.asarray(arrays['contact_normal_J']);layer=np.asarray(arrays['layer_complex_power']);ideal=np.asarray(arrays['source_ideal_voltage'])
 require(I.shape==ideal.shape==(2,2)and np.array_equal(ideal,.5*np.eye(2))and J.shape==drop.shape==(2,len(area))and layer.shape==(2,4),'Actual shared basis/output/contact/power ABI')
 require(all(np.isfinite(a).all()for a in(I,J,drop,layer))and np.all(abs(drop-z_specific*J)<=1e-12+2e-7*abs(drop)),'Finite same physical contact condition')
 for basis in(0,1):
  jrms=abs(J[basis])/math.sqrt(2);contact=weighted_stats(jrms,area);edge=weighted_stats(jrms,ring);sourceP=float(.5*np.vdot(I[basis],ideal[basis]).real)
  e=dict(source_power_W=sourceP,output_RMS_current_A=(abs(I[basis])/math.sqrt(2)).tolist(),sum_output_RMS_current_A_bookkeeping=float(abs(I[basis]).sum()/math.sqrt(2)),
   contact_J_RMS_max_A_m2=contact['max'],contact_J_RMS_P95_A_m2=contact['p95'],contact_drop_RMS_max_V=float(abs(drop[basis]).max()/math.sqrt(2)),edge_J_RMS_max_A_m2=edge['max'],edge_J_RMS_P95_A_m2=edge['p95'],
   contact_power_W=float(.5*np.sum(drop[basis]*np.conj(J[basis])*area).real),edge_contact_power_W=float(.5*z_specific.real*np.sum(abs(J[basis])**2*ring)),source_resistor_power_W=float(25*np.sum(abs(I[basis])**2)),skin_power_W=float(layer[basis,:2].real.sum()))
  e.update({name+'_power_W':float(layer[basis,i].real)for i,name in enumerate(LAYERS)});result.append(e)
 return dict(pad_area_proof=padproof,edge_width_mm=EDGE_WIDTH_MM,relative_area_limit=CONTACT_AREA_RELATIVE_LIMIT,basis=result,scope='Contact-normal carrierRMS and real time-average losses; no tissue vectorJ or safety inference')


def _layout_flags(arrays,faces_m,counts,h_mm,gamma,guard):
 """Sampled-potential flags on their own physical sampling grid, never deltas."""
 import cem_fit as fit
 xy=np.asarray(arrays['xy_mm']);z=np.asarray(arrays['z_eval_mm']);phi=np.asarray(arrays['phi_ref']);nxy=len(xy);faces=np.asarray(faces_m)*1000;counts=np.asarray(counts,int);zs=(faces[:-1]+faces[1:])/2
 require(phi.shape==(2,len(z)*nxy)and np.allclose(z,zs,rtol=0,atol=1e-9)and len(z)==counts.sum(),'Actual potential evaluation grid')
 order=np.lexsort((xy[:,1],xy[:,0]));layout=dict(xy_mm=xy[order],z_mm=z,faces_mm=faces,layer_counts=counts,lookup=np.arange(len(z)*nxy).reshape(len(z),nxy)[:,order],native_cell_count=phi.shape[1])
 meta=dict(sc_cells=int(counts[0]),bulk_layer_counts=counts[1:].tolist(),z_faces_mm=faces.tolist(),h_xy_mm=h_mm,radius_mm=25.)
 scopes=fit.scopes(layout['xy_mm'],h_mm);rows=[]
 for basis in(0,1):
  for points in(2,3):
   guard();value=fit.normal_fits(phi[basis],None,meta,gamma,points,guard,layout=layout)
   for interface,depth in enumerate(value['interface_depths_mm']):
    for scope in('all','interior','staircase_periphery','native_interior','native_staircase_periphery'):
     rows.append(dict(basis=basis,points_per_side=points,interface_depth_mm=float(depth),scope=scope,upper_sample_depths_mm=value['upper_sample_depths_mm'][interface],lower_sample_depths_mm=value['lower_sample_depths_mm'][interface],jump=fit.interface_norms(value['upper_J'][interface],value['lower_J'][interface],layout['xy_mm'],float(depth),scopes[scope])))
 return dict(rows=rows,warning='FineSC4/97-plane sampling differs from coarseSC8/101. No like-sample jump delta or XY convergence conclusion is computed. Old original flags remain separate.')


def roi_potential_comparison(coarse,fine,coarsefaces,finefaces,links,guard):
 """Common physical disk/z quadrature only on matching muscle target planes."""
 import physical_projector as project
 area=project.analyticdisk_rect_area(links['rectangle_mm'],5.);use=area>0;ci=links['coarse_index'][use];fi=links['fine_index'][use];area=area[use]
 require(area.sum()>0,'Positive common target disk');cf=np.asarray(coarsefaces);ff=np.asarray(finefaces);cz=np.asarray(coarse['z_eval_mm'])*1e-3;fz=np.asarray(fine['z_eval_mm'])*1e-3
 C=np.asarray(coarse['phi_ref']).reshape(2,len(cz),len(coarse['xy_mm']));F=np.asarray(fine['phi_ref']).reshape(2,len(fz),len(fine['xy_mm']))
 matches=[]
 for j in range(len(fz)):
  overlap=max(0.,min(ff[j+1],.020)-max(ff[j],.015))
  if overlap<=0:continue
  candidates=[i for i in range(len(cz))if abs(cf[i]-ff[j])<=1e-12 and abs(cf[i+1]-ff[j+1])<=1e-12 and abs(cz[i]-fz[j])<=1e-12]
  require(len(candidates)==1,'Target depths differ; separate cached coarse modal reconstruction is required before a pointwise volume comparison')
  matches.append((candidates[0],j,overlap))
 require(matches,'Common physical target planes');weights=np.concatenate([area*d for _,_,d in matches]);volume=float(weights.sum());analytic=math.pi*.005**2*.005
 require(abs(volume-analytic)/analytic<=1e-10,'Analytic common r5/depth15–20mm volume; no mask renormalization')
 rows=[]
 for basis in(0,1):
  guard();a=np.concatenate([C[basis,i,ci]for i,_,_ in matches]);b=np.concatenate([F[basis,j,fi]for _,j,_ in matches]);total=float(weights.sum());error=np.sqrt(float(weights@(abs(b-a)**2)/total));den=max(float(np.sqrt(weights@(abs(a)**2)/total)),1e-12)
  rows.append(dict(basis=basis,coarse_potential_carrier_RMS_V=weighted_stats(abs(a)/math.sqrt(2),weights),fine_potential_carrier_RMS_V=weighted_stats(abs(b)/math.sqrt(2),weights),
   coarse_complex_mean_V=pair(np.sum(weights*a)/total),fine_complex_mean_V=pair(np.sum(weights*b)/total),pairwise_cellconstant_potential_L2_V=float(error),relative_L2_coarse_denominator=float(error/den),denominator_V=den,phase_or_gauge_fitted=False))
 return dict(rows=rows,represented_volume_m3=volume,analytic_volume_m3=analytic,target_plane_pairs=[dict(coarse_plane=i,fine_plane=j,z_overlap_m=d)for i,j,d in matches],
  quadrature='Version2 analytic centred-disk/rectangle intersections times exact depth overlap; both fields represented cellconstant at matching physical muscle centres. Previous128² masks/results remain unchanged.',
  no_global_SC_phi_comparison=True,coarse97_reconstruction_performed=False,why_no_coarse_Q_reload='Only target muscle56 planes are compared and already match physically; SC4vsSC8 sample differences lie outside thisROI.',
  interpretation='Potential statistics are not electric-field/TIS convergence; no reference E is exported.')


def build(fine_result,spec,guard,deadline_monotonic=None):
 import layer_dtn_cem as model
 import physical_projector as project
 require(callable(guard),'Finite root guard');guard();quality=fine_result['summary'];fine=fine_result['arrays']
 require(quality['spec']==spec and quality['physical_gates_passed']is True and quality['cache_reuse']['complete_before_after_SHA_verified']is True and spec['coarse_reference_commit']==COARSE_COMMIT,'Successful new fine CEM and actual coarse identity')
 require(spec['plan']['XY_nodes']==8184 and spec['plan']['evaluation_layer_counts']==[4,19,18,56]and spec['plan']['evaluation_cells']==793848 and spec['old_independent_QA_limit']==.05,'Frozen fine graph/evaluation/QA')
 pins=required_inputs();used={}
 def check():
  guard();require(deadline_monotonic is None or time.monotonic()<deadline_monotonic,'Finite physical cross-grid comparison deadline')
 def read(path):
  check();p=Path(path);require(str(p)in pins and p.is_file()and not p.is_symlink()and p.stat().st_size<=128*1024**2,'Only exact pinned metadata/array input');raw=p.read_bytes();require(sha(raw)==pins[str(p)],'Actual input bytes changed');used[str(p)]=pins[str(p)];return raw
 def js(p):return json.loads(read(p))
 coarsequality=js(spec['coarse_reference_summary_path']);require(coarsequality['physical_gates_passed']is True and coarsequality['cache_reuse']['complete_before_after_SHA_verified']is True,'Actual successful coarse CEM')
 with np.load(io.BytesIO(read(spec['coarse_reference_arrays_path'])),allow_pickle=False)as archive:coarse={key:np.array(archive[key],copy=True)for key in archive.files}
 oldspec=coarsequality['spec'];require(oldspec['material_rows']==spec['material_rows']and oldspec['contact_specific_impedance_ohm_m2']==spec['contact_specific_impedance_ohm_m2']and oldspec['plan']['source_resistance_ohm']==spec['plan']['source_resistance_ohm']==50,'Same material/contact/circuit, not a parameter change')
 coarseface=Path(oldspec['z_faces_path']);coarsefaces=js(coarseface)['z_faces_m'];finefaces=js(spec['z_faces_path'])['z_faces_m'];oldcomparison=js(COARSE/'comparison-summary.json')
 cxy=np.asarray(coarse['xy_mm']);fxy=np.asarray(fine['xy_mm']);require(cxy.shape==(7860,2)and fxy.shape==(8184,2),'Explicit different XY coordinate arrays')
 for data,nz,nxy in((coarse,101,7860),(fine,97,8184)):
  require(np.asarray(data['phi_ref']).shape==(2,nz*nxy)and np.asarray(data['interface_J']).shape==(2,3,nxy)and np.asarray(data['phi_ref']).dtype==np.dtype('complex128')and np.asarray(data['interface_J']).dtype==np.dtype('complex128')and np.isfinite(data['phi_ref']).all()and np.isfinite(data['interface_J']).all(),'Finite complex128 samephysical reference field ABIs')
  require(np.asarray(data['layer_eval']).shape==(nz,)and np.equal(data['layer_eval'],np.rint(data['layer_eval'])).all(),'Explicit integral evaluation-layer IDs')
 links=project.build_overlap(cxy,.5,fxy,50/102,check);inner=project.analyticdisk_rect_area(links['rectangle_mm'],23.75);density=np.minimum(1.,np.maximum(0.,inner/links['area_m2']))
 scopes={'common_staircase_intersection':None,'physical_r_le23_75':density,'physical_r_gt23_75':1-density};interface=[]
 for basis in(0,1):
  for iface,depth in enumerate((.1,5.1,10.1)):
   check()
   for name,w in scopes.items():interface.append(dict(basis=basis,interface_depth_mm=depth,scope=name,units='A/m2',norm_scope='Spatial complex peak-amplitude current on physical overlap, not temporal RMS',comparison=project.compare_piecewise(np.asarray(coarse['interface_J'])[basis,iface],np.asarray(fine['interface_J'])[basis,iface],links,w)))
 za=complex(spec['contact_specific_impedance_ohm_m2']['real'],spec['contact_specific_impedance_ohm_m2']['imaginary']);rectangles=spec['pad_rectangles_mm'];contactC=contact_metrics(coarse,.5,rectangles,za);contactF=contact_metrics(fine,50/102,rectangles,za)
 circuits=[];reviews=[]
 for basis in(0,1):
  c=contactC['basis'][basis];f=contactF['basis'][basis];rows=[]
  for key,percent in REVIEW_PERCENT.items():
   before=c[key];after=f[key];floor=1e-12;relative=abs(after-before)/max(abs(before),floor);units='W'if key.endswith('_W')else'V'if key.endswith('_V')else'A/m2';rows.append(dict(metric=key,units=units,coarse=before,fine=after,absolute_difference=abs(after-before),relative_difference=relative,percent_limit=percent,passed=relative<=percent/100,denominator_floor=floor,denominator_floor_units=units))
  circuits.append(dict(basis=basis,coarse=c,fine=f,output_current_difference_complex_peak_A=[pair(a-b)for a,b in zip(np.asarray(fine['source_current'])[basis],np.asarray(coarse['source_current'])[basis])]))
  reviews.append(dict(basis=basis,rows=rows,all_available_electrical_screens_passed=all(r['passed']for r in rows),target_E_mean_P10='not_evaluated_reference_E_not_exported',automatic_adoption=False))
 gamma=np.asarray([complex(r['gamma_S_m']['real'],r['gamma_S_m']['imaginary'])for r in spec['material_rows']]);fineflags=_layout_flags(fine,finefaces,[4,19,18,56],50/102,gamma,check)
 legacy=[{k:r[k]for k in('basis','points_per_side','interface_depth_mm','scope','upper_sample_depths_mm','lower_sample_depths_mm','native_original_jump','reference_sampled_jump')}for r in oldcomparison['sampled_interface_estimator_comparison']]
 potential=roi_potential_comparison(coarse,fine,coarsefaces,finefaces,links,check)
 check();return dict(summary=dict(schema='task1-physical-XY100-XY102-CEM-comparison-v1',status='calculated_crossgrid_diagnostic_unadopted',fine_spec=spec,coarse_reference_commit=COARSE_COMMIT,
  provenance=dict(input_sha256=used),physical_overlap=links['summary'],interface_J_physical_common_area=interface,target_potential=potential,coarse_contact_binding=contactC,fine_contact_binding=contactF,circuit_and_burdens=circuits,
  predeclared_available_electrical_screens=reviews,review_percent=REVIEW_PERCENT,edge_strip_width_mm=EDGE_WIDTH_MM,coarse_original_native_and_reference_5percent_flags=legacy,fine_reference_sampled_5percent_flags=fineflags,
  old_failed_QA_flags_retained=True,criteria_relaxed=False,no_indexwise_node_delta=True,coarse_or_fine_common_offset_fit=False,
  interpretation='Interface values compared as piecewiseconstant physical square-cell fields on exact overlap; primary pairwiseL2 retains variation, secondary fine-to-coarse averaging can hide it. Unmatched boundaryarea is separate. Different staircases and physical contact discretization remain part of XY sensitivity.',
  holds=dict(full_SC_XY_bulk_edge_contact_convergence=False,material_anatomic_experimental_safety_validation=False,candidate_adopted=False,reference_E_not_exported=True,TIS_not_defined_one_carrier=True),new_PDE_in_comparison=0),
  arrays=dict(overlap_coarse_index=links['coarse_index'],overlap_fine_index=links['fine_index'],overlap_area_m2=links['area_m2'],overlap_rectangles_mm=links['rectangle_mm']))
