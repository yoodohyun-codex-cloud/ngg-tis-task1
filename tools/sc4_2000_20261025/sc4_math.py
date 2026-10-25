from __future__ import annotations
import math
import numpy as np
LAYERS=("sc","dermis","fat","muscle")
def require(ok,message):
 if not ok:raise ValueError(message)
def weighted_statistics(values,weights,grid):
    """Inverse weighted ECDF; ties preserve original native cell index order."""
    values=np.asarray(values,float);weights=np.asarray(weights,float)
    require(values.shape==weights.shape==(len(grid),)and np.isfinite(values).all()and np.isfinite(weights).all()and np.all(weights>=0),
        'Finite same-grid scalar/volume weights required')
    cells=np.flatnonzero(weights>0);require(len(cells)>0,'Positive represented volume required')
    v=values[cells];w=weights[cells];order=np.argsort(v,kind='stable');sorted_cells=cells[order]
    cumulative=np.cumsum(w[order]);volume=float(cumulative[-1]);mean=float(v@w/volume)
    def location(index):
        return dict(native_cell_index=int(index),center_xyz_mm=grid[index,:3].tolist(),layer_index=int(grid[index,3]),layer=LAYERS[int(grid[index,3])])
    def quantile(q):
        j=min(int(np.searchsorted(cumulative,q*volume,side='left')),len(order)-1);index=int(sorted_cells[j])
        return dict(value=float(values[index]),cumulative_volume_m3=float(cumulative[j]),representative=location(index),
            representative_scope='First stable ascending weighted ECDF crossing; a quantile has no unique spatial coordinate')
    lo=float(v.min());hi=float(v.max());imin=int(cells[np.flatnonzero(v==lo)[0]]);imax=int(cells[np.flatnonzero(v==hi)[0]])
    return dict(min=lo,p10=quantile(.1)['value'],median=quantile(.5)['value'],p90=quantile(.9)['value'],p95=quantile(.95)['value'],
        max=hi,mean=mean,std=float(np.sqrt(((v-mean)**2)@w/volume)),energy_RMS=float(np.sqrt((v*v)@w/volume)),
        volume_m3=volume,cells=int(len(cells)),NaN_count=0,Inf_count=0,
        minimum_location=dict(**location(imin),tied_cell_count=int(np.count_nonzero(v==lo))),
        maximum_location=dict(**location(imax),tied_cell_count=int(np.count_nonzero(v==hi))),
        quantiles={name:quantile(q)for name,q in(('P10',.1),('median',.5),('P90',.9),('P95',.95))},
        weighted_quantile_definition='Stable ascending inverse weighted ECDF; first cumulative native volume reaching q*sum(volume); no spatial interpolation',
        extrema_scope='Cell-constant native-centre values at cells with positive represented volume; not a continuum maximum')

def reconstruct_native_field(phi,grid,geometry,gamma,contacts,metal,za):
    """Exact native half-face-flux ABI reconstruction; not independent accuracy."""
    lookup=geometry['lookup'];h=geometry['h'];iz=geometry['iz'];dz=geometry['dz'];layer=grid[:,3].astype(int)
    field=np.zeros((len(grid),3),np.complex128)
    for axis in range(3):
        if axis==0:aa,bb=lookup[:,:,:-1],lookup[:,:,1:]
        elif axis==1:aa,bb=lookup[:,:-1,:],lookup[:,1:,:]
        else:aa,bb=lookup[:-1,:,:],lookup[1:,:,:]
        good=(aa>=0)&(bb>=0);a=aa[good];b=bb[good]
        distance_a=(np.full(len(a),h)if axis<2 else dz[iz[a]])/2
        distance_b=(np.full(len(b),h)if axis<2 else dz[iz[b]])/2
        area=h*dz[iz[a]]if axis<2 else np.full(len(a),h*h)
        current=area/(distance_a/gamma[layer[a]]+distance_b/gamma[layer[b]])*(phi[a]-phi[b])
        field[a,axis]+=.5*current/(gamma[layer[a]]*area);field[b,axis]+=.5*current/(gamma[layer[b]]*area)
    for row in contacts:
        p=int(row['pad']);i=int(round((float(row['x_mm'])+25)/geometry['h_mm']-.5));j=int(round((float(row['y_mm'])+25)/geometry['h_mm']-.5));cell=int(lookup[0,j,i])
        require(cell>=0,'Actual top contact cell');voltage=metal[p]if p<2 else 0j
        current=float(row['area_m2'])/(za+dz[0]/(2*gamma[0]))*(phi[cell]-voltage)
        field[cell,2]-=.5*current/(gamma[0]*h*h)
    return field
def native_geometry(grid,meta):
 """Validate physical faces/counts without assuming a fixed bulk cell count.

 This builds native lookup geometry only. Region integration separately uses
 the frozen 128-square fractional-overlap algorithm on each actual grid.
 """
 grid=np.asarray(grid,float)
 require(grid.ndim==2 and grid.shape[1]==5 and 0<len(grid)<=800000 and np.isfinite(grid).all(),'Bounded finite native geometry')
 h_mm=float(meta['h_xy_mm']);radius=float(meta.get('radius_mm',25.));h=h_mm*1e-3
 raw_counts=np.asarray([meta['sc_cells']]+list(meta['bulk_layer_counts']),float)
 require(radius==25 and math.isfinite(h_mm)and h_mm>0 and raw_counts.shape==(4,)and np.isfinite(raw_counts).all()and np.all(raw_counts>=2)and np.equal(raw_counts,np.rint(raw_counts)).all(),'Fixed radius and four integral layer counts >=2')
 counts=raw_counts.astype(int);nx=round(2*radius/h_mm);nz=int(counts.sum())
 require(nx>=2 and math.isclose(nx*h_mm,2*radius,rel_tol=0,abs_tol=1e-9),'XY spacing must tile fixed diameter')
 x,y,z=(np.unique(grid[:,k])for k in range(3));faces=np.asarray(meta['z_faces_mm'],float)
 require(len(x)==len(y)==nx and len(z)==nz and len(faces)==nz+1 and np.isfinite(faces).all()and np.all(np.diff(faces)>0),'Dynamic native XY/Z/count/face agreement')
 require(np.allclose(faces[np.r_[0,np.cumsum(counts)]],[0,.1,5.1,10.1,25.1],rtol=0,atol=1e-9),'Preserved physical tissue boundaries')
 axis=-radius+(np.arange(nx)+.5)*h_mm;require(np.array_equal(x,axis)and np.array_equal(y,axis),'Exact native XY coordinates')
 ix,iy,iz=(np.searchsorted(a,grid[:,k])for k,a in enumerate((x,y,z)))
 require(np.allclose(z,(faces[:-1]+faces[1:])/2,rtol=0,atol=1e-9)and np.array_equal(grid[:,3].astype(int),np.repeat(np.arange(4),counts)[iz]),'Physical centre/face/layer agreement')
 linear=(iz*nx+iy)*nx+ix
 require(len(np.unique(linear))==len(grid),'Unique native cell indices')
 lookup=np.full((nz,nx,nx),-1,np.int32);lookup[iz,iy,ix]=np.arange(len(grid))
 require(np.array_equal(lookup>=0,np.broadcast_to(lookup[0]>=0,lookup.shape)),'Complete repeated XY columns on every bulk plane')
 expected_volume=h*h*np.diff(faces)[iz]*1e-3
 require(np.allclose(grid[:,4],expected_volume,rtol=2e-10,atol=1e-20),'Actual h squared dz volumes')
 return dict(x=x,y=y,z=z,faces=faces,ix=ix,iy=iy,iz=iz,lookup=lookup,h=h,dz=np.diff(faces)*1e-3,h_mm=h_mm,layer_counts=counts.tolist())
