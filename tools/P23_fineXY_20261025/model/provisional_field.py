"""Pure derived-field adapter; NumPy is injected by the registered finite owner.

No imports, IO, arrays, solver/cache reads or numerical work occur on import.
This hybrid reconstruction has EXACTLY the old native lateral half-face
stencil, and a separately declared analytic continuous-z normal component.
It does not reproduce the old native vertical half-face/contact averaging ABI,
certify full E accuracy, clear 5% failures or adopt a candidate.
"""

VERSION='native-lateral-half-face-v1+analytic-z-DtN-v1'


def _require(condition,message):
    if not condition:raise ValueError(message)


def provenance():
    return dict(derived_field_version=VERSION,phasor_convention='complex peak +jomega*t',
                field_units='V/m',positive_z='downward from physical top',
                lateral_source='SelectivityShapeBasis.java ShapeNet.field/edgeCurrent; same archive ExploreBasis.edgeCurrent sign',
                lateral_definition='Each existing +x/+y edge (a,b) contributes (phi_a-phi_b)/(2*h) to BOTH incident cells in its oriented component',
                missing_neighbor_rule='No edge means zero face contribution; wall cells retain half contribution, never a full one-sided derivative',
                normal_definition='Ez=analytic_downward_J/gamma_at_same_plane; J=-gamma*dphi/dz',
                old_vertical_field_ABI_reproduced=False,full_E_accuracy_validated=False,
                old_5percent_failures_preserved=True,candidate_adopted=False,
                conditional_scope='Continuous z conditional on the registered discrete XY graph and inherited material/contact/circuit assumptions')


def _edges(np,ij):
    raw=np.asarray(ij)
    _require(raw.ndim==2 and raw.shape[1]==2 and len(raw)>0 and np.isfinite(raw).all(),
             'Finite nonempty ij array shape(nXY,2) required')
    integer=raw.astype(np.int64)
    _require(np.array_equal(raw,integer)and np.all(integer>=0)and
             len(np.unique(integer,axis=0))==len(integer),'Unique nonnegative integer XY coordinates required')
    lookup={(int(i),int(j)):p for p,(i,j)in enumerate(integer)}
    result=[]
    for axis in(0,1):
        links=[]
        for p,(i,j)in enumerate(integer):
            target=(int(i)+1,int(j))if axis==0 else(int(i),int(j)+1)
            q=lookup.get(target)
            if q is not None:links.append((p,q))
        result.append(np.asarray(links,np.int64).reshape((-1,2)))
    return result


def _lateral_with_edges(np,phi,edges,h_m,guard):
    result=np.zeros(phi.shape+(2,),np.complex128)
    for axis,pairs in enumerate(edges):
        guard()
        if not len(pairs):continue
        a=pairs[:,0];b=pairs[:,1]
        contribution=(phi[...,a]-phi[...,b])/(2.*h_m)
        # Each a/b occurs at most once separately for a fixed +axis edge set.
        # The two assignments intentionally accumulate at shared incident cells.
        result[...,a,axis]+=contribution
        result[...,b,axis]+=contribution
    return result


def lateral_field(np,phi,ij,h_m,guard=lambda:None):
    """Return complex Ex/Ey shape(...,nXY,2) from phi shape(...,nXY).

    XY ordering is defined only by supplied ij rows, not array index arithmetic.
    For an interior cell, Ex=(phi_left-phi_right)/(2*h); at a missing wall face
    the corresponding HALF-face contribution is zero. Gamma and dz cancel for
    these same-layer lateral edges only. No additional drive-amplitude factor
    or temporal RMS conversion is applied.
    """
    guard();phi=np.asarray(phi,np.complex128)
    _require(phi.ndim>=1 and phi.shape[-1]==len(ij)and np.isfinite(phi).all()and
             np.isfinite(h_m)and h_m>0,'Finite complex phi(...,nXY) and positive h in metres required')
    return _lateral_with_edges(np,phi,_edges(np,ij),h_m,guard)


def assemble_E(np,phi,Jdown,gamma_by_plane,ij,h_m,guard=lambda:None,depth_block=8,out=None):
    """Return derived E shape(...,nz,nXY,3), optionally using caller storage.

    phi/Jdown shape(...,nz,nXY) must refer to the exact same XY ordering, physical
    centre depths, basis, frequency and drive. gamma_by_plane is the complex
    S/m admittivity at each of those nz centre planes. The caller supplies the
    analytic downward J reconstructed from the SAME modal coefficients and
    kernel. Stored interface-only J cannot replace centre-plane J.

    depth_block bounds lateral temporary arrays; output still stores three
    components unless out is a caller-controlled writable complex array/memmap.
    Units and field/version metadata are returned separately by provenance().
    """
    guard();phi=np.asarray(phi,np.complex128);Jdown=np.asarray(Jdown,np.complex128)
    gamma=np.asarray(gamma_by_plane,np.complex128)
    _require(phi.ndim>=2 and phi.shape==Jdown.shape and phi.shape[-1]==len(ij)and
             phi.shape[-2]>0 and gamma.shape==(phi.shape[-2],)and
             np.isfinite(phi).all()and np.isfinite(Jdown).all()and np.isfinite(gamma).all()and
             np.all(abs(gamma)>0)and np.isfinite(h_m)and h_m>0,
             'Matched finite centre-plane phi/Jdown, nonzero gamma per plane and positive h required')
    _require(isinstance(depth_block,int)and depth_block>0,'Positive finite depth block required')
    shape=phi.shape+(3,)
    if out is None:out=np.empty(shape,np.complex128)
    else:
        _require(out.shape==shape and np.issubdtype(out.dtype,np.complexfloating)and out.flags.writeable,
                 'Caller output must be writable complex storage of exact E shape')
    edges=_edges(np,ij)
    for first in range(0,phi.shape[-2],depth_block):
        guard();last=min(phi.shape[-2],first+depth_block)
        out[...,first:last,:,:2]=_lateral_with_edges(np,phi[...,first:last,:],edges,h_m,guard)
        out[...,first:last,:,2]=Jdown[...,first:last,:]/gamma[first:last,None]
    guard()
    return out
