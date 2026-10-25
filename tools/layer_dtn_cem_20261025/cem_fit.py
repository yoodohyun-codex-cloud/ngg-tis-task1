"""Pure potential-fit and signed-error helpers for the finite owner's comparison.

Import performs no IO or numerical work. Inputs are supplied by the registered
owner. The reference is a conditional layered/XY-discrete model, not 3D truth.
No electric field is reconstructed or exported. All error decompositions are
diagnostic and do not change the independent 5% interface screening flag.
"""
from __future__ import annotations
import math
import numpy as np


DENOMINATOR_FLOOR=1e-12
INTERFACE_FLAG_LIMIT=.05


def require(condition,message):
    if not condition:raise ValueError(message)


def lagrange_weights(nodes,at,derivative=0):
    """Two/three-point value or first-derivative weights in caller's units."""
    nodes=np.asarray(nodes,float)
    require(nodes.ndim==1 and len(nodes)in(2,3)and np.isfinite(nodes).all()and
            math.isfinite(at)and derivative in(0,1)and np.all(np.diff(nodes)>0),
            'Two/three distinct increasing finite nodes are required')
    scale=float(np.max(abs(nodes-at)))
    require(scale>0,'Nonzero coordinate scale required')
    x=(nodes-at)/scale
    matrix=np.vstack([x**power for power in range(len(nodes))])
    require(np.linalg.cond(matrix)<1e12,'Ill-conditioned one-sided fit')
    target=np.zeros(len(nodes));target[derivative]=1. if derivative==0 else 1./scale
    return np.linalg.solve(matrix,target)


def prepare_layout(grid,meta):
    """Build native z/XY lookup once for optional reuse across basis/frequency fits."""
    grid=np.asarray(grid,float)
    require(grid.ndim==2 and grid.shape[1]==5 and len(grid)>0 and np.isfinite(grid).all(),
            'Finite native grid columns x_mm,y_mm,z_mm,layer,volume_m3 required')
    counts=np.asarray([meta['sc_cells']]+list(meta['bulk_layer_counts']),int)
    faces=np.asarray(meta['z_faces_mm'],float)
    require(counts.shape==(4,)and np.all(counts>=2)and len(faces)==int(counts.sum())+1 and
            np.isfinite(faces).all()and np.all(np.diff(faces)>0),
            'Four layers, at least two samples each, and actual z faces required')
    xy,ixy=np.unique(grid[:,:2],axis=0,return_inverse=True)
    z,iz=np.unique(grid[:,2],return_inverse=True)
    require(len(z)==int(counts.sum())and len(z)*len(xy)==len(grid),
            'Complete native z-times-XY columns required')
    require(np.allclose(z,(faces[:-1]+faces[1:])/2.,rtol=0,atol=1e-8),
            'Actual centre depths must match supplied native faces')
    expected=np.repeat(np.arange(4),counts)
    require(np.array_equal(grid[:,3],expected[iz]),'Layer IDs must exactly match actual z faces')
    linear=iz*len(xy)+ixy
    require(len(np.unique(linear))==len(grid),'Unique native grid cells required')
    lookup=np.full((len(z),len(xy)),-1,int);lookup[iz,ixy]=np.arange(len(grid))
    require(np.all(lookup>=0),'Missing native column cell')
    return dict(xy_mm=xy,z_mm=z,faces_mm=faces,layer_counts=counts,lookup=lookup,
                native_cell_count=len(grid),provenance='Caller-supplied grid and metadata only')


def normal_fits(phi_native_order,grid,meta,gamma,points,guard=lambda:None,layout=None):
    """Independent one-sided potential fits, returning small face-array products.

    points=2 fixes exactly two nearest samples on both sides. points=3 means
    the historical up-to-three-point rule; a two-cell SC side remains linear.
    Actual side counts are always returned. Derivatives use metres; phi is
    complex peak +j*omega*t and J=-gamma*dphi/dz includes displacement current.
    No shared FVM current or native E is accepted.
    """
    require(points in(2,3),'points must be the registered maximum 2 or 3')
    guard();phi=np.asarray(phi_native_order,complex);gamma=np.asarray(gamma,complex)
    require(phi.ndim==1 and np.isfinite(phi).all()and gamma.shape==(4,)and
            np.isfinite(gamma).all()and np.all(abs(gamma)>0),
            'Finite potential and four nonzero finite complex admittivities required')
    if layout is None:layout=prepare_layout(grid,meta)
    require(len(phi)==layout['native_cell_count'],'Potential must match prepared native layout')
    counts=np.asarray([meta['sc_cells']]+list(meta['bulk_layer_counts']),int)
    require(np.array_equal(counts,layout['layer_counts'])and
            np.array_equal(np.asarray(meta['z_faces_mm'],float),layout['faces_mm']),
            'Prepared layout must have the same explicit layer/faces metadata')
    z=layout['z_mm'];faces=layout['faces_mm'];potential=phi[layout['lookup']]
    ends=np.cumsum(counts);depths=[];upper_j=[];lower_j=[];upper_phi=[];lower_phi=[]
    upper_points=[];lower_points=[];upper_depths=[];lower_depths=[]
    for layer,boundary in enumerate(ends[:-1]):
        guard();boundary=int(boundary);first=0 if layer==0 else int(ends[layer-1]);last=int(ends[layer+1])
        upper=np.arange(max(first,boundary-points),boundary)
        lower=np.arange(boundary,min(last,boundary+points));face=float(faces[boundary])
        a=lagrange_weights(z[upper]/1000.,face/1000.,0)@potential[upper]
        b=lagrange_weights(z[lower]/1000.,face/1000.,0)@potential[lower]
        aj=-gamma[layer]*(lagrange_weights(z[upper]/1000.,face/1000.,1)@potential[upper])
        bj=-gamma[layer+1]*(lagrange_weights(z[lower]/1000.,face/1000.,1)@potential[lower])
        depths.append(face);upper_phi.append(a);lower_phi.append(b);upper_j.append(aj);lower_j.append(bj)
        upper_points.append(len(upper));lower_points.append(len(lower))
        upper_depths.append(z[upper].tolist());lower_depths.append(z[lower].tolist())
    return dict(status='diagnostic_not_gated',xy_mm=layout['xy_mm'],interface_depths_mm=np.asarray(depths),
                upper_J=np.asarray(upper_j),lower_J=np.asarray(lower_j),
                upper_phi=np.asarray(upper_phi),lower_phi=np.asarray(lower_phi),
                upper_points=upper_points,lower_points=lower_points,
                upper_sample_depths_mm=upper_depths,lower_sample_depths_mm=lower_depths,
                maximum_fit_points=points,phi_convention='peak complex +jomega*t',
                current_definition='total J=-gamma*dphi/dz, derivative in metres',
                reference_scope='Potential-only fit; no E or shared-face current used')


def scopes(xy_mm,h_mm,radius_mm=25.,fixed_interior_radius_mm=23.75):
    """Internal masks: fixed physical comparison region plus actual-grid regions."""
    xy=np.asarray(xy_mm,float)
    require(xy.ndim==2 and xy.shape[1]==2 and np.isfinite(xy).all()and
            math.isfinite(h_mm)and h_mm>0 and math.isfinite(radius_mm)and radius_mm>2*h_mm and
            math.isfinite(fixed_interior_radius_mm)and 0<=fixed_interior_radius_mm<=radius_mm,
            'Finite XY grid, positive spacing/radius and valid fixed radius required')
    r=np.linalg.norm(xy,axis=1);fixed=r<=fixed_interior_radius_mm;native=r<=radius_mm-2*h_mm
    return dict(all=np.ones(len(xy),bool),interior=fixed,staircase_periphery=~fixed,
                fixed_physical_interior=fixed,fixed_physical_staircase_periphery=~fixed,
                native_interior=native,native_staircase_periphery=~native)


def _rms(values):return float(np.sqrt(np.mean(abs(values)**2)))


def _complex(value):return dict(real=float(complex(value).real),imaginary=float(complex(value).imag))


def _mask(scope,n):
    mask=np.asarray(scope)
    require(mask.dtype==np.dtype(bool)and mask.shape==(n,),'Explicit boolean XY scope mask required')
    return mask


def interface_norms(up,lo,xy,depth,scope):
    """JSON-safe spatial complex-amplitude jump and unchanged 5% screening flag."""
    up=np.asarray(up,complex);lo=np.asarray(lo,complex);xy=np.asarray(xy,float)
    require(up.ndim==1 and up.shape==lo.shape and xy.shape==(len(up),2)and
            np.isfinite(up).all()and np.isfinite(lo).all()and np.isfinite(xy).all()and math.isfinite(depth),
            'Finite same-sized face samples, XY positions and depth required')
    mask=_mask(scope,len(up));indices=np.flatnonzero(mask)
    if not len(indices):return dict(status='not_run_no_samples',samples=0,screening_flag_5pct=None)
    a=up[mask];b=lo[mask];difference=a-b;ur=_rms(a);lr=_rms(b)
    denominator=max(ur,lr,DENOMINATOR_FLOOR);numerator=_rms(difference);index=int(np.argmax(abs(difference)))
    return dict(status='diagnostic_only',samples=len(indices),units='A/m2',
                upper_spatial_complex_RMS=ur,lower_spatial_complex_RMS=lr,
                difference_spatial_complex_RMS=numerator,normalized_L2=numerator/denominator,
                denominator=denominator,denominator_floor=DENOMINATOR_FLOOR,
                denominator_floor_used=max(ur,lr)<DENOMINATOR_FLOOR,
                maximum_absolute_difference=float(abs(difference[index])),
                maximum_difference_xyz_mm=[float(xy[indices[index],0]),float(xy[indices[index],1]),float(depth)],
                complex_difference_at_maximum=_complex(difference[index]),
                screening_flag_5pct=numerator/denominator>INTERFACE_FLAG_LIMIT,
                screening_limit=INTERFACE_FLAG_LIMIT,
                screening_definition='Diagnostic flag only; not physical, biological or full convergence validation',
                norm_definition='spatial sqrt(mean(abs(complex peak samples)^2)); equal-area faces; no temporal sqrt(2) conversion')


def _error_stats(values,denominator,indices):
    index=int(np.argmax(abs(values)));absolute_rms=_rms(values)
    return dict(absolute_RMS=absolute_rms,normalized_RMS=absolute_rms/denominator,
                complex_mean=_complex(np.mean(values)),maximum_absolute_value=float(abs(values[index])),
                maximum_native_XY_index=int(indices[index]),complex_value_at_maximum=_complex(values[index]))


def signed_decomposition(native_fit,intermediate,reference,mask,
                         component_names=('solution_through_estimator','reference_sample_fit_bias')):
    """JSON-safe signed components; input arrays have shape(nXY,) or(nfaces,nXY).

    c1=native_fit-intermediate, c2=intermediate-reference,
    total=native_fit-reference=c1+c2. Both components share the exact same
    reference RMS denominator. The cross term may be negative (cancellation).
    Default intermediate is the reference-potential fit; another use is native
    shared FVM flux with custom labels. These are conditional reference errors,
    not errors against 3D truth, and no acceptance gate is applied here.
    """
    n=np.asarray(native_fit,complex);i=np.asarray(intermediate,complex);r=np.asarray(reference,complex)
    require(n.shape==i.shape==r.shape and n.ndim in(1,2)and np.isfinite(n).all()and
            np.isfinite(i).all()and np.isfinite(r).all(),'Finite same-shaped one/two-dimensional complex arrays required')
    require(len(component_names)==2 and all(isinstance(v,str)and v for v in component_names)and
            component_names[0]!=component_names[1],'Two distinct nonempty component names required')
    scope=_mask(mask,n.shape[-1]);indices=np.flatnonzero(scope)
    if not len(indices):return dict(status='not_run_no_samples',samples_per_face=0,component_names=list(component_names))
    if n.ndim==1:n=n[None,:];i=i[None,:];r=r[None,:]
    rows=[]
    for face,(nv,iv,rv)in enumerate(zip(n[:,scope],i[:,scope],r[:,scope])):
        c1=nv-iv;c2=iv-rv;total=nv-rv;reference_rms=_rms(rv)
        denominator=max(reference_rms,DENOMINATOR_FLOOR)
        cross=float(2.*np.real(np.mean(c1*np.conjugate(c2))))
        norm_closure=float(np.mean(abs(total)**2)-np.mean(abs(c1)**2)-np.mean(abs(c2)**2)-cross)
        rows.append(dict(face_index=face,samples=len(indices),reference_spatial_complex_RMS=reference_rms,
                         denominator=denominator,denominator_floor=DENOMINATOR_FLOOR,
                         denominator_floor_used=reference_rms<DENOMINATOR_FLOOR,
                         components={component_names[0]:_error_stats(c1,denominator,indices),
                                     component_names[1]:_error_stats(c2,denominator,indices)},
                         total=_error_stats(total,denominator,indices),
                         cross_term_2Re_mean_c1_conj_c2=cross,
                         squared_RMS_identity_closure=norm_closure,
                         maximum_absolute_vector_identity_closure=float(np.max(abs(total-c1-c2)))))
    return dict(schema='task1-cem-signed-decomposition-v1',status='diagnostic_not_gated',
                units='A/m2',cross_term_units='A^2/m4',component_names=list(component_names),
                identity='native-reference=(native-intermediate)+(intermediate-reference)',
                reference_scope='Conditional continuous-z layered/XY-discrete reference; not 3D physical truth',
                spatial_complex_norm_is_not_temporal_RMS=True,faces=rows)
