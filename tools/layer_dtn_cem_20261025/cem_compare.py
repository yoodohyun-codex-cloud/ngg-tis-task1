"""Conditional continuous-z CEM versus actual cached U19 native comparison.

No import-time data IO/solver. No reference E or TIS is created. Root alone
invokes this after the separately admitted one-condition/two-RHS reference solve.
"""
from __future__ import annotations
import gzip,hashlib,io,json,math,time
from pathlib import Path
import numpy as np

RUN=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run')
CASE='baseline-square15-human-sine2000-sc8-vs19uniform-bulk19-18-56-xy100'
PHASE1_COMMIT='815327e978ec5e3976ba9a462510d6faac6f318a'
NATIVE_COMMIT='cebb04aa2074e848e34ffd7aede4bc0476aa16c6'
GATES=dict(max_residual=2e-7,max_power_error=2e-7,max_current_error=2e-6,max_area_relative_error=1e-10,max_interface_normal_current_relative_error=2e-7)
LAYERS=('sc','dermis','fat','muscle')


def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pair(v):return dict(real=float(complex(v).real),imaginary=float(complex(v).imag))
def _bounded(p):
 p=Path(p);require(p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Bounded metadata/source');return p.read_bytes()


def required_inputs():
 """Root-invoked metadata/hash declarations; no native field or Q decoding."""
 import layer_dtn_cem as model
 refs=model.required_inputs()
 pubpath=RUN/'result-publication.json';sourcepath=RUN/'source-publication.json';pubraw=_bounded(pubpath);sourceraw=_bounded(sourcepath);pub=json.loads(pubraw);source=json.loads(sourceraw)
 require(pub['status']=='published_readback_verified'and pub['commit']==NATIVE_COMMIT and source['status']=='published_readback_verified','Actual complete native/source publications')
 require(any(name.endswith('/source-publication.json')and v.get('SHA256')==sha(sourceraw)and v.get('readback_passed')is True for name,v in pub['files'].items()),'Exact source publication authenticated by native result readback')
 refs[str(pubpath)]=sha(pubraw);refs[str(sourcepath)]=sha(sourceraw)
 manifestpath=RUN/'native-sha256.json';raw=_bounded(manifestpath);manifest=json.loads(raw);refs[str(manifestpath)]=sha(raw)
 for name,digest in manifest['files'].items():
  p=Path(name);require(p.is_relative_to(RUN),'Exact native comparator paths');relative=p.relative_to(RUN).as_posix();documents=[pub]if relative.startswith('bases/')else[pub,source]
  require(any(key.endswith('/'+relative)and v.get('SHA256')==digest and v.get('readback_passed')is True for document in documents for key,v in document['files'].items()),'Direct immutable native/config proof: '+relative);refs[name]=digest
 for name in('postprocess/summary.json','postprocess/artifact-sha256.json'):
  p=RUN/name;refs[str(p)]=sha(_bounded(p))
 artifact=json.loads(_bounded(RUN/'postprocess/artifact-sha256.json'));require(refs[str(RUN/'postprocess/summary.json')]==artifact['summary.json']['SHA256'],'Actual preserved native summary')
 for name in('cem_compare.py','cem_math.py','cem_fit.py'):
  p=Path(__file__).parent/name;refs[str(p)]=sha(_bounded(p))
 return refs


def coordinate_map(native_grid,reference_xy,reference_z,reference_layers):
 """Native-cell→reference z-major/explicitXY order; no spatial interpolation."""
 grid=np.asarray(native_grid,float);xy=np.asarray(reference_xy,float);z=np.asarray(reference_z,float);raw_layers=np.asarray(reference_layers)
 require(np.isfinite(raw_layers).all()and np.equal(raw_layers,np.rint(raw_layers)).all(),'Integral actual reference evaluation-layer IDs');layers=raw_layers.astype(int)
 require(grid.ndim==2 and grid.shape[1]==5 and xy.ndim==2 and xy.shape[1]==2 and z.ndim==1 and layers.shape==z.shape and np.isfinite(grid).all()and np.isfinite(xy).all()and np.isfinite(z).all(),'Finite explicit coordinate ABI')
 require(len(z)*len(xy)==len(grid)and np.all(np.diff(z)>0),'Complete reference z×XY Cartesian evaluation')
 table={tuple(row):i for i,row in enumerate(xy)};require(len(table)==len(xy),'Unique reference XY graph nodes')
 unique_z=np.unique(grid[:,2]);require(len(unique_z)==len(z)and np.allclose(unique_z,z,rtol=0,atol=1e-9),'Same physical evaluation centres, absolute tolerance1e-9mm')
 zi=np.searchsorted(unique_z,grid[:,2]);xi=np.asarray([table.get((x,y),-1)for x,y in grid[:,:2]],int)
 require(np.all(xi>=0)and np.array_equal(grid[:,3].astype(int),layers[zi]),'Exact native/reference XY and layer mapping')
 out=zi*len(xy)+xi;require(len(np.unique(out))==len(grid),'Bijective native/reference cell map');return out


def complex_error(actual,reference,weights,coordinates,units):
 """Secondary reference-normalized diagnostic; never an automatic accuracy gate."""
 a=np.asarray(actual,complex);b=np.asarray(reference,complex);w=np.asarray(weights,float);coords=np.asarray(coordinates,float)
 require(a.ndim==b.ndim==1 and a.shape==b.shape==w.shape and coords.shape[0]==len(a)and np.isfinite(a).all()and np.isfinite(b).all()and np.isfinite(w).all()and np.all(w>=0),'Finite weighted same-coordinate complex values')
 selected=np.flatnonzero(w>0);require(len(selected)>0,'Positive represented measure');total=float(w.sum());error=a-b
 na=math.sqrt(float(w@(abs(a)**2)/total));nb=math.sqrt(float(w@(abs(b)**2)/total));absolute=math.sqrt(float(w@(abs(error)**2)/total));den=max(nb,1e-12);i=int(selected[np.argmax(abs(error[selected]))])
 return dict(status='secondary_diagnostic_not_gated',units=units,native_or_estimate_spatial_complex_RMS=na,conditional_reference_spatial_complex_RMS=nb,absolute_difference_spatial_complex_RMS=absolute,
  normalized_L2_reference_denominator=absolute/den,denominator=den,denominator_floor=1e-12,denominator_floor_used=nb<1e-12,
  maximum_native_sample_absolute_difference=float(abs(error[i])),maximum_location=coords[i].tolist(),difference_complex_mean=pair(np.sum(w*error)/total),
  phase_or_gauge_fitted=False,norm='Weighted complex peak amplitudes; temporal RMS is separately /sqrt(2); reference normalized, distinct from upper/lower jump denominator')


def shared_flux(phi,layout,gamma):
 """Downward harmonic native FVM face current per area, not stored E."""
 potential=np.asarray(phi)[layout['lookup']];faces=layout['faces_mm'];dz=np.diff(faces)*1e-3;breaks=np.cumsum(layout['layer_counts']);rows=[]
 for layer,boundary in enumerate(breaks[:-1]):
  denominator=dz[boundary-1]/(2*gamma[layer])+dz[boundary]/(2*gamma[layer+1]);rows.append((potential[boundary-1]-potential[boundary])/denominator)
 return np.asarray(rows)


def _scalar_error(a,b,units):
 return dict(native=float(a),conditional_reference=float(b),units=units,signed_difference=float(a-b),absolute_difference=float(abs(a-b)),relative_difference=float(abs(a-b)/max(abs(b),1e-12)),denominator_floor=1e-12,status='secondary_diagnostic_not_gated')


def build(refarrays,spec,guard,deadline_monotonic=None,*,reference_summary=None):
 """Accept full reference {summary,arrays}, or arrays plus reference_summary.

 Every data read/array computation occurs only inside this root-invoked call.
 """
 import layer_dtn_cem as model
 import cem_fit as fit
 from cem_math import native_geometry
 from selectivity_volume import native_region_weights
 require(callable(guard),'Explicit finite root guard');guard()
 if isinstance(refarrays,dict)and'arrays'in refarrays and'summary'in refarrays:reference_summary=refarrays['summary'];refarrays=refarrays['arrays']
 require(reference_summary is not None and reference_summary['spec']==spec and reference_summary['physical_gates_passed']is True,'Successful actual reference solve/immutable specification required')
 require(reference_summary['cache_reuse']['complete_before_after_SHA_verified']is True and reference_summary['cache_reuse']['manifest_sha256']==spec['cache_manifest_sha256']and spec['phase1_commit']==PHASE1_COMMIT and spec['native_comparator_commit']==NATIVE_COMMIT,'Actual SHA-verified phase1 cache reuse before/after reference solve')
 require(spec['schema']=='task1-layer-dtn-cem-reference-spec-v1'and spec['old_independent_QA_limit']==.05 and spec['old_failed_QA_preserved']is True,'Unchanged reference/5% scope')
 pins=required_inputs();used={}
 def check():
  guard();require(deadline_monotonic is None or time.monotonic()<deadline_monotonic,'Finite CEM comparison deadline')
 def read(path):
  check();p=Path(path);require(str(p)in pins and p.is_file()and not p.is_symlink()and p.stat().st_size<=80*1024**2,'Only pinned bounded comparison inputs');raw=p.read_bytes();require(sha(raw)==pins[str(p)],'Native/source bytes changed');used[str(p)]=pins[str(p)];return raw
 def js(p):return json.loads(read(p))
 def decoded(path):
  raw=read(path)
  if Path(path).suffix=='.gz':
   with gzip.GzipFile(fileobj=io.BytesIO(raw))as stream:raw=stream.read(128*1024**2+1)
  require(len(raw)<=128*1024**2,'Bounded actual native decode');return raw
 def binary(path,shape):
  raw=decoded(path);require(len(raw)==math.prod(shape)*16,'Exact native complex128LE size');a=np.frombuffer(raw,dtype='<c16').reshape(shape);require(np.isfinite(a).all(),'Finite native complex values');return a
 paths=spec['native_paths'];meta=js(paths['mesh_metadata']);validation=js(paths['validation'])
 require(meta['frequencies_Hz']==[2000]and meta['channels']==2 and meta['sc_cells']==8 and meta['bulk_layer_counts']==[19,18,56]and meta['h_xy_mm']==.5 and meta['source_peak_V']==.5 and meta['source_resistance_ohm']==50 and meta['phasor_convention']=='peak,+jomega_t','Actual unchanged U19 native model/circuit/peak-phasor convention')
 for key,limit in GATES.items():require(0<=validation[key]<=limit,'Original native algebra gate '+key)
 require(meta['pad_to_node']=={'0':'out0','1':'out1','2':'GND','3':'GND'}and meta['inactive_output_at_each_basis_frequency']=='0V through50ohm','Actual native common-return termination')
 require(spec['phi_ref_native_grid_sha256']==pins[paths['grid_compressed']]==reference_summary['reference_array_ABI']['phi_ref_native_grid_sha256'],'Exact reference evaluation-grid input SHA')
 grid=np.loadtxt(io.BytesIO(decoded(paths['grid_compressed'])),delimiter=',',skiprows=1);n=len(grid);require(grid.shape==(n,5)and n==meta['cells']==793860,'Exact793860 native evaluation cells');native_geometry(grid,meta)
 native_phi=binary(paths['potential'],(2,n));ref_phi=np.asarray(refarrays['phi_ref']);xy_ref=np.asarray(refarrays['xy_mm']);z_ref=np.asarray(refarrays['z_eval_mm']);layers_ref=np.asarray(refarrays['layer_eval'])
 require(ref_phi.shape==(2,n)and ref_phi.dtype==np.dtype('complex128')and np.isfinite(ref_phi).all(),'Finite complex128 peak reference potential ABI')
 native_to_ref=coordinate_map(grid,xy_ref,z_ref,layers_ref);reference_phi=ref_phi[:,native_to_ref]
 gamma=np.asarray([complex(r['gamma_S_m']['real'],r['gamma_S_m']['imaginary'])for r in spec['material_rows']]);require(gamma.shape==(4,)and np.isfinite(gamma).all()and np.all(gamma.real>0),'Finite declared reference/native gamma')
 layout=fit.prepare_layout(grid,meta);xy=layout['xy_mm'];nxy=len(xy);xy_index={tuple(row):i for i,row in enumerate(xy_ref)};ref_order=np.asarray([xy_index[tuple(row)]for row in xy],int)
 ref_j=np.asarray(refarrays['interface_J']);require(ref_j.shape==(2,3,nxy)and ref_j.dtype==np.dtype('complex128')and np.isfinite(ref_j).all(),'Analytic complex128 downward reference interface-J ABI')
 jtruth=ref_j[:,:,ref_order];scopes=fit.scopes(xy,.5);scope_keys=('all','interior','staircase_periphery','native_interior','native_staircase_periphery')
 weights,roi_receipt=native_region_weights({k:grid[:,i]for i,k in enumerate(('x_mm','y_mm','z_mm','layer','volume_m3'))},dict(meta,radius_mm=25,layer_counts=[8,19,18,56],geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001),deadline_monotonic=deadline_monotonic)
 regions={**{name:weights['total']*(grid[:,3]==i)for i,name in enumerate(LAYERS)},**weights,'surface_without_SC':weights['surface_0_5']*(grid[:,3]!=0)}
 potential_rows=[];interface_rows=[];fit_rows=[];new_arrays={}
 for basis in(0,1):
  check();potential_rows.append(dict(basis=basis,regions={region:complex_error(native_phi[basis],reference_phi[basis],w,grid[:,:3],'V')for region,w in regions.items()}))
  nj=shared_flux(native_phi[basis],layout,gamma);rj_sample=shared_flux(reference_phi[basis],layout,gamma)
  for iface,depth in enumerate((.1,5.1,10.1)):
   coordinates=np.column_stack((xy,np.full(nxy,depth)))
   for scope in scope_keys:
    mask=scopes[scope];w=mask.astype(float)
    interface_rows.append(dict(basis=basis,interface_depth_mm=depth,scope=scope,
     native_shared_FVM_vs_reference_J=complex_error(nj[iface],jtruth[basis,iface],w,coordinates,'A/m2'),
     reference_sampled_FVM_operator_vs_reference_J=complex_error(rj_sample[iface],jtruth[basis,iface],w,coordinates,'A/m2'),
     shared_face_decomposition=fit.signed_decomposition(nj[iface],rj_sample[iface],jtruth[basis,iface],mask,component_names=('native_minus_reference_through_shared_face_operator','reference_sampled_shared_face_operator_bias'))))
  for points in(2,3):
   check();nativefit=fit.normal_fits(native_phi[basis],grid,meta,gamma,points,guard,layout=layout);referencefit=fit.normal_fits(reference_phi[basis],grid,meta,gamma,points,guard,layout=layout)
   require(nativefit['upper_points']==nativefit['lower_points']==referencefit['upper_points']==referencefit['lower_points']==[points]*3,'Exact same registered2/2or3/3stencils')
   for iface,depth in enumerate(nativefit['interface_depths_mm']):
    for scope in scope_keys:
     mask=scopes[scope];row=dict(basis=basis,points_per_side=points,interface_depth_mm=float(depth),scope=scope,
      native_original_jump=fit.interface_norms(nativefit['upper_J'][iface],nativefit['lower_J'][iface],xy,float(depth),mask),
      reference_sampled_jump=fit.interface_norms(referencefit['upper_J'][iface],referencefit['lower_J'][iface],xy,float(depth),mask),
      upper_sample_depths_mm=nativefit['upper_sample_depths_mm'][iface],lower_sample_depths_mm=nativefit['lower_sample_depths_mm'][iface],side_errors={})
     for side in('upper','lower'):
      N=nativefit[side+'_J'][iface];R=referencefit[side+'_J'][iface];T=jtruth[basis,iface]
      row['side_errors'][side]=dict(
       solution_and_sample_estimator_bias=fit.signed_decomposition(N,R,T,mask,component_names=('native_minus_reference_solution_through_same_estimator','reference_sampled_estimator_bias')),
       native_flux_and_estimator_split=fit.signed_decomposition(N,nj[iface],T,mask,component_names=('native_estimator_minus_native_shared_FVM_flux','native_shared_FVM_flux_minus_reference_J')))
     fit_rows.append(row)
  new_arrays['basis'+str(basis)+'_native_shared_FVM_J_real_A_m2']=nj.real;new_arrays['basis'+str(basis)+'_native_shared_FVM_J_imaginary_A_m2']=nj.imag
 # Circuit/contact/power comparison uses declared basis,output and contact order.
 transfer=binary(paths['source'],(2,2));loss=binary(paths['loss'],(6,2,2));contacts=np.genfromtxt(io.BytesIO(read(paths['contacts'])),delimiter=',',names=True);density=binary(paths['density'],(2,len(contacts)));area=contacts['area_m2'];pads=contacts['pad'].astype(int)
 require(np.array_equal(refarrays['contact_pad'],pads)and np.array_equal(refarrays['contact_area_m2'],area)and np.array_equal(refarrays['contact_xy_mm'],np.column_stack((contacts['x_mm'],contacts['y_mm']))),'Same canonical physical contact order/coordinates/area')
 Iref=np.asarray(refarrays['source_current']);metalref=np.asarray(refarrays['metal']);ideal=np.asarray(refarrays['source_ideal_voltage']);referencecontact=np.asarray(refarrays['contact_normal_J']);reference_drop=np.asarray(refarrays['contact_drop']);reference_layers=np.asarray(refarrays['layer_complex_power'])
 require(Iref.shape==metalref.shape==ideal.shape==(2,2)and np.array_equal(ideal,.5*np.eye(2))and referencecontact.shape==reference_drop.shape==density.shape and reference_layers.shape==(2,4),'Reference circuit/contact/loss basis-first ABI')
 require(all(np.isfinite(a).all()for a in(Iref,metalref,referencecontact,reference_drop,reference_layers)),'Finite reference electrical arrays')
 require(np.all(abs(metalref-(ideal-50*Iref))<=1e-12+2e-7*abs(metalref)),'Same reference loaded50ohm source equation')
 zspecific=complex(spec['contact_specific_impedance_ohm_m2']['real'],spec['contact_specific_impedance_ohm_m2']['imaginary']);require(np.all(abs(reference_drop-zspecific*referencecontact)<=1e-12+2e-7*abs(reference_drop)),'Reference physical-top contact equation')
 circuit=[]
 for basis in(0,1):
  current=transfer[:,basis];native_metal=ideal[basis]-50*current;native_loss=loss[:,basis,basis];require(np.max(abs(native_loss.imag))<=1e-12,'Native real quadratic loss diagonals')
  sourceP=float(.25*current[basis].real);refP=float(.5*np.vdot(Iref[basis],ideal[basis]).real);refContact=float(.5*np.sum(reference_drop[basis]*np.conj(referencecontact[basis])*area).real);refR=float(25*np.sum(abs(Iref[basis])**2))
  currentcoords=np.column_stack((np.arange(2),np.zeros(2)));contactcoords=np.column_stack((contacts['x_mm'],contacts['y_mm'],np.zeros(len(contacts))))
  circuit.append(dict(basis=basis,source_current=complex_error(current,Iref[basis],np.ones(2),currentcoords,'A'),metal_voltage=complex_error(native_metal,metalref[basis],np.ones(2),currentcoords,'V'),
   contact_normal_J=complex_error(density[basis],referencecontact[basis],area,contactcoords,'A/m2'),contact_drop=complex_error(zspecific*density[basis],reference_drop[basis],area,contactcoords,'V'),
   source_real_power=_scalar_error(sourceP,refP,'W'),contact_real_loss=_scalar_error(float(native_loss[4].real),refContact,'W'),source_resistor_loss=_scalar_error(float(native_loss[5].real),refR,'W'),
   layer_real_loss={name:_scalar_error(float(native_loss[i].real),float(reference_layers[basis,i].real),'W')for i,name in enumerate(LAYERS)},
   conditional_reference_layer_complex_power=[pair(v)for v in reference_layers[basis]],conditional_reference_power_balance_W=float(reference_layers[basis].real.sum()+refContact+refR-refP)))
 failed_native=sum(row['native_original_jump']['screening_flag_5pct']is True for row in fit_rows);failed_reference_sample=sum(row['reference_sampled_jump']['screening_flag_5pct']is True for row in fit_rows)
 check();return dict(summary=dict(schema='task1-layer-DtN-CEM-native-comparison-v1',status='calculated_conditional_reference_diagnostics_unadopted',reference_spec=spec,reference_solve_summary=reference_summary,
  provenance=dict(input_sha256=used,phase1_commit=PHASE1_COMMIT,native_commit=NATIVE_COMMIT,cache_before_after_sha_verified=True),native_gates=dict(values=validation,limits=GATES),
  coordinate_map=dict(native_cells=n,XY_nodes=nxy,mapping='Explicit z_eval/xy_mm bijection to exact native-cell order; no interpolation or common offset/phase fit',z_match_absolute_tolerance_mm=1e-9),ROI_geometry=roi_receipt,
  potential_native_vs_reference=potential_rows,native_FVM_interface_flux_vs_reference=interface_rows,sampled_interface_estimator_comparison=fit_rows,circuit_contact_power=circuit,
  original_5percent_flags=dict(limit=.05,native_flagged_rows=failed_native,reference_exactz_sampled_flagged_rows=failed_reference_sample,flags_not_relaxed=True,scope='Bothbasis×2orders×3interfaces×fixed/native regions; reference sampling may itself flag despite exact continuous-z continuity'),
  reference_meaning='Continuous-z layered CEM conditional on the exact fixed staircase XY graph, eigensystem and iterative-solver tolerances. No true smooth3D continuum/anatomic/skin-contact/safety inference.',
  boundary_meaning='Reference uses physical-top CEM g=A/z with whole analytic SC; native includes SC-centre half-cell approximation. Their solution difference includes vertical/boundary discretization, not a changed physical source topology.',
  field_ABI=dict(reference_phi='peakcomplex potential atnativecentres',reference_J='analyticdownward interfacecurrent',reference_E='not_computed_or_exported',native_stored_E='not_read_or_conflated',TIS='not_defined_onecarrier'),
  holds=dict(old_independent_5percent_flags_retained=True,full_SC_XY_bulk_edge_contact_convergence=False,material_anatomic_or_experimental_validation=False,candidate_adopted=False,secondary_reference_error_not_automatic_adoption=True),new_PDE_in_comparison=0),arrays=new_arrays)
