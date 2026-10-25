"""Independent potential-only one-sided interface diagnostics.

No research data, tests, files or numerical runs are accessed on import. The
registered parent calls these pure functions under its finite resource guard.
These diagnostics never use shared FVM face currents or stored electric fields.
They are explicitly not a grid-convergence or material-validation certificate.
"""
from __future__ import annotations
import math
import numpy as np

ABS_TOL=1e-10
REL_TOL=1e-10
DENOMINATOR_FLOOR=1e-12


def require(ok,message):
    if not ok:raise ValueError(message)


def lagrange_weights(nodes, at, derivative=0):
    """Value/first derivative weights, scaled before the tiny Vandermonde solve."""
    nodes=np.asarray(nodes,dtype=float)
    require(nodes.ndim==1 and len(nodes)in(2,3) and np.isfinite(nodes).all() and
            math.isfinite(at) and derivative in(0,1) and np.all(np.diff(nodes)>0),
            'Two/three distinct increasing finite nodes and derivative0/1 required')
    scale=float(np.max(abs(nodes-at)))
    require(scale>0,'Nonzero fit coordinate scale required')
    reduced=(nodes-at)/scale
    matrix=np.vstack([reduced**power for power in range(len(nodes))])
    require(np.linalg.cond(matrix)<1e12,'Ill-conditioned one-sided fit')
    target=np.zeros(len(nodes));target[derivative]=1. if derivative==0 else 1./scale
    return np.linalg.solve(matrix,target)


def _rms(value):
    value=np.asarray(value,complex)
    return float(np.sqrt(np.mean(abs(value)**2)))


def _comparison(upper,lower,xy_mm,z_mm,units):
    """Spatial complex-amplitude norms, not temporal RMS or an activation index."""
    upper,lower=np.asarray(upper,complex),np.asarray(lower,complex)
    require(upper.shape==lower.shape and upper.ndim==1 and np.isfinite(upper).all()and
            np.isfinite(lower).all(),'Finite same-sized complex face samples required')
    if not len(upper):return dict(status='not_run_no_samples',samples=0,units=units)
    error=upper-lower;denominator=max(_rms(upper),_rms(lower),DENOMINATOR_FLOOR)
    k=int(np.argmax(abs(error)))
    return dict(status='diagnostic_not_gated',samples=len(upper),units=units,
        upper_spatial_complex_RMS=_rms(upper),lower_spatial_complex_RMS=_rms(lower),
        difference_spatial_complex_RMS=_rms(error),normalized_L2=_rms(error)/denominator,
        denominator=denominator,denominator_floor=DENOMINATOR_FLOOR,
        maximum_absolute_difference=float(abs(error[k])),
        maximum_difference_xyz_mm=[float(xy_mm[k,0]),float(xy_mm[k,1]),float(z_mm)],
        complex_difference_at_maximum=dict(real=float(error[k].real),imaginary=float(error[k].imag)),
        norm_definition='sqrt(mean(abs(upper-lower)^2))/max(sqrt(mean(abs(upper)^2)),sqrt(mean(abs(lower)^2)),1e-12); equal-area native faces; no temporal sqrt(2) conversion')


def _tangent_stencils(xy_mm,h_mm):
    """Centered derivatives where available, explicit one-sided fallback at walls."""
    origin=np.min(xy_mm,axis=0)
    lattice=np.rint((xy_mm-origin)/h_mm).astype(int)
    require(np.allclose(origin+lattice*h_mm,xy_mm,rtol=0,atol=1e-8),
            'Regular native XY lattice required')
    lookup={tuple(ij):i for i,ij in enumerate(lattice)}
    outputs=[]
    for axis in(0,1):
        index=np.full((len(xy_mm),3),-1,dtype=int);weights=np.zeros((len(xy_mm),3))
        schemes=[]
        for k,key in enumerate(lattice):
            def point(offset):
                q=key.copy();q[axis]+=offset;return lookup.get(tuple(q),-1)
            if point(-1)>=0 and point(1)>=0:offsets=(-1,0,1);label='centered_three'
            elif point(1)>=0 and point(2)>=0:offsets=(0,1,2);label='forward_three'
            elif point(-1)>=0 and point(-2)>=0:offsets=(-2,-1,0);label='backward_three'
            elif point(1)>=0:offsets=(0,1);label='forward_two'
            elif point(-1)>=0:offsets=(-1,0);label='backward_two'
            else:schemes.append('unavailable');continue
            ids=[point(o)for o in offsets]
            for j,idx in enumerate(ids):index[k,j]=idx
            weights[k,:len(ids)]=lagrange_weights(np.asarray(offsets)*h_mm/1000.,0.,1)
            schemes.append(label)
        outputs.append((index,weights,schemes))
    return outputs


def _tangent(values,stencil):
    indices,weights,schemes=stencil
    valid=indices[:,0]>=0;result=np.full(len(values),np.nan+1j*np.nan)
    safe=np.maximum(indices,0)
    result[valid]=-np.sum(values[safe[valid]]*weights[valid],axis=1)
    return result,valid


def _interface_diagnostics(phi,grid,meta,gamma,guard,maximum_fit_points,interior_radius_mm=None):
    """Return one-sided independent potential diagnostics for all three interfaces.

    phi is one coherently summed peak+jomega*t spectrum, complex[N]. grid is
    [x_mm,y_mm,z_mm,layer,volume_m3]. No raw E/J or FVM face-current is accepted.
    """
    require(maximum_fit_points in(2,3),'Only preregistered two/three-point fits are supported')
    guard();phi=np.asarray(phi,complex);grid=np.asarray(grid,float);gamma=np.asarray(gamma,complex)
    require(phi.ndim==1 and grid.shape==(len(phi),5) and len(phi)>0 and np.isfinite(phi).all()and
            np.isfinite(grid).all()and gamma.shape==(4,)and np.isfinite(gamma).all()and np.all(abs(gamma)>0),
            'Finite actual potential/grid and four nonzero complex admittivities required')
    counts=np.asarray([meta['sc_cells']]+list(meta['bulk_layer_counts']),int)
    faces=np.asarray(meta['z_faces_mm'],float);h=float(meta['h_xy_mm']);radius=float(meta.get('radius_mm',25.))
    require(counts.shape==(4,)and np.all(counts>=2)and len(faces)==counts.sum()+1 and
            np.isfinite(faces).all()and np.all(np.diff(faces)>0)and h>0 and radius>2*h,
            'Four layers with at least two cells and explicit physical faces required')
    xy,ixy=np.unique(grid[:,:2],axis=0,return_inverse=True)
    z,iz=np.unique(grid[:,2],return_inverse=True)
    require(len(z)==counts.sum()and len(z)*len(xy)==len(phi),'Complete native z-times-XY columns required')
    require(np.allclose(z,(faces[:-1]+faces[1:])/2,rtol=0,atol=1e-8),'Native centres must match actual faces')
    expected=np.repeat(np.arange(4),counts)
    require(np.array_equal(grid[:,3].astype(int),expected[iz]),'Actual layer IDs must match face metadata')
    linear=iz*len(xy)+ixy;require(len(np.unique(linear))==len(phi),'Unique native columns required')
    lookup=np.full((len(z),len(xy)),-1,int);lookup[iz,ixy]=np.arange(len(phi))
    require(np.all(lookup>=0),'Missing native column cells')
    potential=phi[lookup]
    stencils=_tangent_stencils(xy,h)
    native_interior_radius=radius-2*h
    selected_interior_radius=native_interior_radius if interior_radius_mm is None else float(interior_radius_mm)
    require(math.isfinite(selected_interior_radius)and 0<=selected_interior_radius<=radius,
            'Optional fixed physical interior radius must be finite and within the phantom radius')
    radial_distance=np.linalg.norm(xy,axis=1)
    scopes=dict(all=np.ones(len(xy),bool),interior=radial_distance<=selected_interior_radius,
                staircase_periphery=radial_distance>selected_interior_radius,
                native_interior=radial_distance<=native_interior_radius,
                native_staircase_periphery=radial_distance>native_interior_radius)
    if interior_radius_mm is not None:
        scopes.update(fixed_physical_interior=radial_distance<=selected_interior_radius,
                      fixed_physical_staircase_periphery=radial_distance>selected_interior_radius)
    stencil_counts_by_region={name:{axis:{scheme:int(sum(bool(mask[k])and value==scheme for k,value in enumerate(schemes)))
        for scheme in sorted(set(schemes))}for axis,(_,_,schemes)in zip(('x','y'),stencils)}for name,mask in scopes.items()}
    results=[];breaks=np.cumsum(counts)
    for layer,boundary in enumerate(breaks[:-1]):
        guard();face=float(faces[boundary]);first=0 if layer==0 else int(breaks[layer-1]);end=int(breaks[layer+1])
        upper=np.arange(max(first,int(boundary)-maximum_fit_points),int(boundary))
        lower=np.arange(int(boundary),min(end,int(boundary)+maximum_fit_points))
        upper_value=lagrange_weights(z[upper]/1000.,face/1000.,0)@potential[upper]
        lower_value=lagrange_weights(z[lower]/1000.,face/1000.,0)@potential[lower]
        upper_derivative=lagrange_weights(z[upper]/1000.,face/1000.,1)@potential[upper]
        lower_derivative=lagrange_weights(z[lower]/1000.,face/1000.,1)@potential[lower]
        j_upper=-gamma[layer]*upper_derivative;j_lower=-gamma[layer+1]*lower_derivative
        upper_t=[_tangent(upper_value,stencil)for stencil in stencils]
        lower_t=[_tangent(lower_value,stencil)for stencil in stencils]
        rows={}
        for name,mask in scopes.items():
            row=dict(face_columns=int(mask.sum()),potential_jump=_comparison(upper_value[mask],lower_value[mask],xy[mask],face,'V'),
                total_normal_current=_comparison(j_upper[mask],j_lower[mask],xy[mask],face,'A/m2'),tangential_E={})
            for axis,(up,lo)in enumerate(zip(upper_t,lower_t)):
                a,valid_a=up;b,valid_b=lo;use=mask&valid_a&valid_b
                row['tangential_E']['xy'[axis]]=_comparison(a[use],b[use],xy[use],face,'V/m')
                row['tangential_E']['xy'[axis]]['unavailable_stencil_columns']=int((mask&~(valid_a&valid_b)).sum())
            rows[name]=row
        results.append(dict(interface_depth_mm=face,upper_layer=layer,lower_layer=layer+1,
            upper_fit_points=len(upper),lower_fit_points=len(lower),upper_degree=len(upper)-1,lower_degree=len(lower)-1,
            upper_sample_depths_mm=z[upper].tolist(),lower_sample_depths_mm=z[lower].tolist(),regions=rows))
    return dict(schema='task1-independent-potential-interface-diagnostic-v3',status='diagnostic_not_gated',
        maximum_fit_points_per_side=maximum_fit_points,sc_cells=int(counts[0]),layer_counts=counts.tolist(),
        comparison_scope=('Common exactly-two-nearest-potential-point one-sided fits on BOTH sides of all three interfaces; comparable between SC2, SC4 and SC8 without changing fit order'
                          if maximum_fit_points==2 else
                          ('Up to three nearest potential points per side; SC2 upper first-interface side remains linear; different orders must not be treated as like-for-like'if counts[0]==2 else'Up to three nearest potential points per side; this SC4/SC8 mesh has three SC samples available; compare against the same fit order and retain common-two-point mode')),
        method='One-sided potential-only polynomial extrapolation to each interface; independent of shared-FVM face flux and stored E',
        phi_convention='Peak complex potential; +jomega*t; potential derivatives use metres',
        normal_quantity='total Jnormal=-gamma*dphi/dz, including displacement; not conduction-only sigma*E',
        tangential_quantity='-d(phi_face)/dx and -d(phi_face)/dy from each independent side',
        spatial_norm_is_not_temporal_RMS=True,small_denominator_floor=DENOMINATOR_FLOOR,
        h_xy_mm=h,phantom_radius_mm=radius,interior_radius_mm=selected_interior_radius,
        interior_radius_is_fixed_physical=interior_radius_mm is not None,
        native_interior_radius_mm=native_interior_radius,
        interior_definition=('r <= explicit interior_radius_mm' if interior_radius_mm is not None else 'r <= radius-2*h'),
        periphery_definition=('r > explicit interior_radius_mm; no side/bottom boundary accuracy inferred' if interior_radius_mm is not None else
                              'r > radius-2*h; no side/bottom boundary accuracy inferred'),
        native_region_definition='native_interior: r <= radius-2*h; native_staircase_periphery: r > radius-2*h',
        comparison_region_warning='Changing h changes the native periphery width. Use the same explicit physical interior_radius_mm for like-region mesh comparisons; a changed region is not convergence.',
        region_face_columns={name:int(mask.sum())for name,mask in scopes.items()},
        tangent_stencil_counts={axis:{s:schemes.count(s)for s in sorted(set(schemes))}for axis,(_,_,schemes)in zip(('x','y'),stencils)},
        tangent_stencil_counts_by_region=stencil_counts_by_region,
        all_columns_reported=True,interfaces=results,
        limitations=[('Common two-point mode is linear on both sides of every interface, including SC4/SC8' if maximum_fit_points==2 else
                      'SC2 has two potential samples and uses a linear SC fit' if counts[0]==2 else
                      'This SC4/SC8 mesh uses three nearest samples and a quadratic SC fit; retain common-two-point mode separately for comparison'),
                    'One-sided differences are finite-grid diagnostics; no predeclared accuracy gate or convergence proof',
                    'No outer-wall insulation, electrode-edge, contact-physics or material calibration proof is inferred'])


def interface_diagnostics(phi,grid,meta,gamma,guard=lambda:None,interior_radius_mm=None):
    """Independent up-to-three-point diagnostic, with optional fixed physical mask.

    Default interior/periphery use radius-2*h as before. An explicit physical
    radius selects those existing region names while native_* regions retain
    the grid-dependent masks. Fixed and native regions are both reported.
    """
    return _interface_diagnostics(phi,grid,meta,gamma,guard,3,interior_radius_mm)


def common_two_point_diagnostics(phi,grid,meta,gamma,guard=lambda:None,interior_radius_mm=None):
    """Exactly two nearest potential points on BOTH sides, at every interface.

    This fixes fit order for a like-for-like SC2/SC4 finite-grid diagnostic.
    It does not assert two-level or complete convergence and remains not gated.
    """
    return _interface_diagnostics(phi,grid,meta,gamma,guard,2,interior_radius_mm)


diagnostics=interface_diagnostics


def _historical_analytic_validation():
    """Independent synthetic layered slab and affine potential checks, no PDE/data."""
    boundaries=np.asarray([0.,.1,5.1,10.1,25.1])/1000.
    counts=np.asarray([2,3,3,4]);gamma=np.asarray([.002+.01j,.2+.002j,.04+.0002j,.3+.02j])
    faces=np.concatenate([np.linspace(boundaries[k],boundaries[k+1],counts[k]+1)[:-1]for k in range(4)]+[boundaries[-1:]])
    centres=(faces[:-1]+faces[1:])/2;layers=np.repeat(np.arange(4),counts)
    current=1./np.sum(np.diff(boundaries)/gamma)
    phi=np.empty(len(centres),complex)
    for k,(z,l)in enumerate(zip(centres,layers)):
        integral=np.sum(np.diff(boundaries)[:l]/gamma[:l])+(z-boundaries[l])/gamma[l]
        phi[k]=1-current*integral
    rows=[]
    for l,stop in enumerate(np.cumsum(counts)[:-1]):
        face=boundaries[l+1];start=0 if l==0 else np.cumsum(counts)[l-1];end=np.cumsum(counts)[l+1]
        a=np.arange(max(start,stop-3),stop);b=np.arange(stop,min(end,stop+3))
        exact_phi=1-current*np.sum(np.diff(boundaries)[:l+1]/gamma[:l+1])
        for side,indices,material in(('upper',a,l),('lower',b,l+1)):
            face_phi=lagrange_weights(centres[indices],face,0)@phi[indices]
            estimated_j=-gamma[material]*(lagrange_weights(centres[indices],face,1)@phi[indices])
            ep=abs(face_phi-exact_phi);ej=abs(estimated_j-current)
            require(ep<=ABS_TOL+REL_TOL*abs(exact_phi)and ej<=ABS_TOL+REL_TOL*abs(current),'Synthetic layered slab extrapolation failed')
            rows.append(dict(interface_m=float(face),side=side,points=len(indices),potential_error_V=float(ep),total_current_error_A_m2=float(ej),passed=True))
    axis=(np.arange(4)-1.5)*.625;xx,yy=np.meshgrid(axis,axis,indexing='xy');xy=np.column_stack((xx.ravel(),yy.ravel()))
    a=.3+.2j;b=-.4+.1j;potential=a*xy[:,0]/1000.+b*xy[:,1]/1000.+.7
    stencils=_tangent_stencils(xy,.625);affine=[]
    for label,coefficient,stencil in zip(('x','y'),(a,b),stencils):
        values,valid=_tangent(potential,stencil);error=float(np.max(abs(values[valid]+coefficient)))
        require(valid.all()and error<=ABS_TOL+REL_TOL*abs(coefficient),'Synthetic complex affine tangential gradient failed')
        affine.append(dict(axis=label,samples=int(valid.sum()),maximum_error_V_m=error,passed=True))
    return dict(schema='task1-independent-interface-analytic-validation-v1',status='passed',passed=True,
        scope='Synthetic complex layered-slab and homogeneous affine potential only; not an actual phantom solve',
        absolute_tolerance=ABS_TOL,relative_tolerance=REL_TOL,layered_slab=rows,affine_tangent=affine,
        new_PDE=0,native_data_read=False,full_convergence_validated=False)


def synthetic_layered_slab(sc_cells,h_xy_mm=.625):
    """Small synthetic complex slab for caller-owned analytic checks only."""
    require(sc_cells in(2,4,8),'Synthetic slab supports the registered SC2/SC4/SC8 levels')
    require(math.isfinite(h_xy_mm)and h_xy_mm>0,'Positive synthetic XY spacing required')
    boundaries_mm=np.asarray([0.,.1,5.1,10.1,25.1])
    boundaries=boundaries_mm/1000.;counts=np.asarray([sc_cells,3,3,4])
    gamma=np.asarray([.002+.01j,.2+.002j,.04+.0002j,.3+.02j])
    faces=np.concatenate([np.linspace(boundaries_mm[k],boundaries_mm[k+1],counts[k]+1)[:-1]for k in range(4)]+[boundaries_mm[-1:]])
    centres=(faces[:-1]+faces[1:])/2.;layers=np.repeat(np.arange(4),counts)
    current=1./np.sum(np.diff(boundaries)/gamma)
    potential_z=np.empty(len(centres),complex)
    for k,(z_mm,l)in enumerate(zip(centres,layers)):
        integral=np.sum(np.diff(boundaries)[:l]/gamma[:l])+(z_mm/1000.-boundaries[l])/gamma[l]
        potential_z[k]=1-current*integral
    axis=(np.arange(4)-1.5)*h_xy_mm;xx,yy=np.meshgrid(axis,axis,indexing='xy');xy=np.column_stack((xx.ravel(),yy.ravel()))
    a=.3+.2j;b=-.4+.1j
    tangent=a*xy[:,0]/1000.+b*xy[:,1]/1000.
    phi=(potential_z[:,None]+tangent[None,:]).reshape(-1)
    grid=np.empty((len(phi),5),float)
    grid[:,0]=np.tile(xy[:,0],len(centres));grid[:,1]=np.tile(xy[:,1],len(centres))
    grid[:,2]=np.repeat(centres,len(xy));grid[:,3]=np.repeat(layers,len(xy))
    grid[:,4]=np.repeat(h_xy_mm**2*np.diff(faces)*1e-9,len(xy))
    meta=dict(sc_cells=sc_cells,bulk_layer_counts=[3,3,4],z_faces_mm=faces.tolist(),h_xy_mm=h_xy_mm,radius_mm=25.)
    return dict(phi=phi,grid=grid,meta=meta,gamma=gamma,current=current,
                potential_z=potential_z,centres_m=centres/1000.,boundaries_m=boundaries,
                counts=counts,tangential_coefficients=(a,b))


def _slab_fit_validation(sc_cells,maximum_fit_points,h_xy_mm=.625):
    slab=synthetic_layered_slab(sc_cells,h_xy_mm=h_xy_mm)
    result=_interface_diagnostics(slab['phi'],slab['grid'],slab['meta'],slab['gamma'],lambda:None,maximum_fit_points)
    gamma,current=slab['gamma'],slab['current'];counts=slab['counts'];centres=slab['centres_m']
    phi_z=slab['potential_z'];boundaries=slab['boundaries_m'];rows=[]
    for l,stop in enumerate(np.cumsum(counts)[:-1]):
        face=boundaries[l+1];start=0 if l==0 else int(np.cumsum(counts)[l-1]);end=int(np.cumsum(counts)[l+1])
        upper=np.arange(max(start,int(stop)-maximum_fit_points),int(stop))
        lower=np.arange(int(stop),min(end,int(stop)+maximum_fit_points))
        exact_phi=1-current*np.sum(np.diff(boundaries)[:l+1]/gamma[:l+1])
        for side,indices,material in(('upper',upper,l),('lower',lower,l+1)):
            observed_phi=lagrange_weights(centres[indices],face,0)@phi_z[indices]
            observed_current=-gamma[material]*(lagrange_weights(centres[indices],face,1)@phi_z[indices])
            ep=float(abs(observed_phi-exact_phi));ej=float(abs(observed_current-current))
            require(ep<=ABS_TOL+REL_TOL*abs(exact_phi)and ej<=ABS_TOL+REL_TOL*abs(current),
                    'SC2/SC4/SC8 synthetic one-sided slab reference failed')
            rows.append(dict(interface_m=float(face),side=side,points=len(indices),potential_error_V=ep,
                             total_current_error_A_m2=ej,passed=True))
        face_result=result['interfaces'][l]['regions']['all']
        require(face_result['potential_jump']['maximum_absolute_difference']<=ABS_TOL+REL_TOL,
                'Synthetic continuous face potential diagnostic failed')
        require(face_result['total_normal_current']['maximum_absolute_difference']<=ABS_TOL+REL_TOL*abs(current),
                'Synthetic common complex normal current diagnostic failed')
        for axis,coefficient in zip(('x','y'),slab['tangential_coefficients']):
            require(face_result['tangential_E'][axis]['maximum_absolute_difference']<=ABS_TOL+REL_TOL*abs(coefficient),
                    'Synthetic side-independent affine tangent diagnostic failed')
    if maximum_fit_points==2:
        require(all(row['upper_fit_points']==row['lower_fit_points']==2 for row in result['interfaces']),
                'Common comparison must use exactly two points on both sides')
    else:
        require(result['interfaces'][0]['upper_fit_points']==3,'SC4/SC8 quadratic diagnostic needs three SC points')
    return dict(sc_cells=sc_cells,maximum_fit_points_per_side=maximum_fit_points,h_xy_mm=h_xy_mm,status='passed',
                analytical_reference='Continuous layered complex impedance plus a common affine tangential potential',
                face_fit_checks=rows,diagnostic_status=result['status'],
                stencil_points=[dict(depth_mm=i['interface_depth_mm'],upper=i['upper_fit_points'],lower=i['lower_fit_points'])for i in result['interfaces']],
                common_two_point_comparison=maximum_fit_points==2,passed=True)


def _affine_validation(h_xy_mm):
    """Independent expected complex affine gradients at one caller-selected XY spacing."""
    axis=(np.arange(4)-1.5)*h_xy_mm
    xx,yy=np.meshgrid(axis,axis,indexing='xy');xy=np.column_stack((xx.ravel(),yy.ravel()))
    a=.3+.2j;b=-.4+.1j;potential=.7+a*xy[:,0]/1000.+b*xy[:,1]/1000.
    rows=[]
    for label,coefficient,stencil in zip(('x','y'),(a,b),_tangent_stencils(xy,h_xy_mm)):
        observed,valid=_tangent(potential,stencil)
        error=float(np.max(abs(observed[valid]+coefficient)))
        require(valid.all()and error<=ABS_TOL+REL_TOL*abs(coefficient),
                'Generic-XY synthetic affine tangential gradient failed')
        rows.append(dict(axis=label,samples=int(valid.sum()),maximum_error_V_m=error,passed=True))
    return dict(h_xy_mm=h_xy_mm,status='passed',affine_tangent=rows,passed=True)


def analytic_validation():
    """Synthetic SC2/SC4/SC8 complex-slab/affine checks at .5 and .625 mm XY."""
    legacy=_historical_analytic_validation()
    scenarios=[_slab_fit_validation(sc_cells,points,h_xy_mm=h)for h in(.5,.625)for sc_cells,points in((2,2),(4,2),(4,3),(8,2),(8,3))]
    return dict(schema='task1-generic-xy-interface-analytic-validation-v1',status='passed',passed=True,
        scope='Synthetic complex layered slab/affine checks only; no native field or numerical PDE',
        absolute_tolerance=ABS_TOL,relative_tolerance=REL_TOL,
        common_order_definition='Exactly two nearest potential points on BOTH sides of all interfaces for SC2, SC4 and SC8',
        original_three_point_diagnostic_separate=True,legacy_analytic_reference=legacy,scenarios=scenarios,
        affine_checks=[_affine_validation(h)for h in(.5,.625)],
        new_PDE=0,native_data_read=False,full_convergence_validated=False)
