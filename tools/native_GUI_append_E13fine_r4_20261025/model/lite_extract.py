"""Pure owner-called native display-plane extraction; NumPy is injected.

No file/source/data imports or reads, rendering, tests, process or scientific
work occurs on import. Owner must authenticate original arrays and metadata.
Quantitative statistics/normalizations/probes are supplied original records.
"""
import base64
import math
import time
from collections import defaultdict
from fractions import Fraction

INTERFACES_MM=(0.,.1,5.1,10.1,25.1)
XY_DEPTHS_MM=(15.,17.5,20.)
MAX_CELLS=800000
FLOAT16_ABSOLUTE_ERROR_BOUND=3.1e-8
FLOAT16_RELATIVE_ERROR_BOUND=5e-4
DISPLAY_ESTIMATOR='native-planes-same-layer-display-only-v1'


def require(ok,message):
    if not ok:raise ValueError(message)


def check(guard,deadline_monotonic):
    if guard is not None:guard()
    if deadline_monotonic is not None and time.monotonic()>=deadline_monotonic:
        raise TimeoutError('Finite native GUI display extraction incomplete')


def axis_edges(np,centres):
    """Uniform fixedD50 XY centres only, verified before edge reconstruction."""
    axis=np.asarray(centres,float);require(axis.ndim==1 and len(axis)>=2 and np.isfinite(axis).all(),'Finite native XY axis')
    h=float(axis[1]-axis[0]);require(h>0 and np.all(abs(np.diff(axis)-h)<=1e-9),'Uniform native XY spacing, no rounded geometry')
    edges=np.concatenate(([axis[0]-h/2.],axis+h/2.))
    require(abs(float(edges[0])+25.)<=1e-8 and abs(float(edges[-1])-25.)<=1e-8,'Actual centres must span fixed50mm XY faces')
    return edges


def native_layout(np,grid,z_faces_mm):
    g=np.asarray(grid);require(g.ndim==2 and g.shape[1]==5 and 0<len(g)<=MAX_CELLS and np.isfinite(g).all(),'Actual finite native N x5 physical grid below800k')
    zs,first,counts=np.unique(g[:,2],return_index=True,return_counts=True);nxy=int(counts[0]);nz=len(zs)
    require(np.all(counts==nxy)and np.array_equal(first,np.arange(nz)*nxy)and nxy*nz==len(g),'Z-major full ordered XY planes')
    rows=g.reshape(nz,nxy,5);xy=rows[0,:,:2];layers=rows[:,0,3].astype(int)
    require(np.array_equal(rows[:,:,0],np.broadcast_to(xy[:,0],(nz,nxy)))and np.array_equal(rows[:,:,1],np.broadcast_to(xy[:,1],(nz,nxy)))and np.array_equal(rows[:,:,2],np.broadcast_to(zs[:,None],(nz,nxy))),
            'Identical native physical XY order at every depth, no index remapping')
    require(np.array_equal(rows[:,:,3],np.broadcast_to(layers[:,None],(nz,nxy)))and np.array_equal(layers,np.searchsorted(INTERFACES_MM,zs,side='right')-1),'Fixed physical layer IDs at native depth samples')
    faces=np.asarray(z_faces_mm,float);require(faces.shape==(nz+1,)and np.isfinite(faces).all()and np.all(np.diff(faces)>0)and abs(float(faces[0]))<=1e-9 and abs(float(faces[-1])-25.1)<=1e-9,'Explicit original native z faces in mm, top0/bottom25.1')
    require(np.all((zs>faces[:-1])&(zs<faces[1:])),'Every native sample lies inside its original physical cell')
    require(all(np.any(abs(faces-bound)<=1e-9)for bound in INTERFACES_MM),'All fixed layer interfaces must be original native faces')
    xs=np.unique(xy[:,0]);ys=np.unique(xy[:,1]);ix=np.searchsorted(xs,xy[:,0]);iy=np.searchsorted(ys,xy[:,1]);require(len(np.unique(iy*len(xs)+ix))==nxy,'Unique native XY graph cells')
    lookup=np.full((len(ys),len(xs)),-1,np.int64);lookup[iy,ix]=np.arange(nxy)
    return dict(xs=xs,ys=ys,zs=zs,layers=layers,nxy=nxy,nz=nz,n=len(g),ix=ix,iy=iy,lookup=lookup,
        x_edges=axis_edges(np,xs),y_edges=axis_edges(np,ys),z_edges=faces)


def _bracket(np,axis,value):
    nearest=int(np.argmin(abs(axis-value)))
    if abs(float(axis[nearest])-value)<=1e-9:return [nearest],[1.]
    high=int(np.searchsorted(axis,value,side='right'));require(0<high<len(axis),'Display interpolation cannot extrapolate native coordinates')
    low=high-1;f=(value-float(axis[low]))/(float(axis[high])-float(axis[low]));return [low,high],[1.-f,f]


def _z_bracket(np,layout,depth):
    layer=int(np.searchsorted(INTERFACES_MM,depth,side='right')-1);require(0<=layer<4 and INTERFACES_MM[layer]<depth<INTERFACES_MM[layer+1],'Display depth strictly inside one physical layer')
    eligible=np.flatnonzero(layout['layers']==layer);require(len(eligible)>0,'No same-layer native display samples')
    local,weights=_bracket(np,layout['zs'][eligible],depth);indices=[int(eligible[i])for i in local]
    require(all(int(layout['layers'][i])==layer for i in indices),'Never interpolate scalar display across a material interface')
    return indices,weights,dict(method='exact_native_plane'if len(indices)==1 else'same_layer_linear_display_interpolation',requested_depth_mm=float(depth),
        native_sample_depths_mm=[float(layout['zs'][i])for i in indices],signed_weights=[float(w)for w in weights],physical_layer=layer,
        physical_layer_bounds_mm=[INTERFACES_MM[layer],INTERFACES_MM[layer+1]],cross_layer_interpolation=False,quantitative_metrics_derived_from_display=False)


def plane_values(np,layout,field,orientation,depth_mm=None):
    """Native scalar values or signedE component, display reconstruction only."""
    raw=np.asarray(field);require(raw.shape==(layout['n'],)and np.isfinite(raw).all()and not np.iscomplexobj(raw),'Actual finite scalar or realE component at exact native grid order')
    values=raw.reshape(layout['nz'],layout['nxy']);nx=len(layout['xs']);ny=len(layout['ys'])
    if orientation=='XY':
        indices,weights,info=_z_bracket(np,layout,float(depth_mm));sample=np.zeros(layout['nxy'],float)
        for index,weight in zip(indices,weights):sample+=weight*values[index]
        out=np.full((ny,nx),np.nan);out[layout['iy'],layout['ix']]=sample
        return out,layout['x_edges'],layout['y_edges'],dict(orientation='XY',horizontal_axis='x_mm',vertical_axis='y_mm',**info)
    require(orientation in('XZ','YZ'),'Only native XY/XZ/YZ display planes')
    fixed=layout['ys']if orientation=='XZ'else layout['xs'];indices,weights=_bracket(np,fixed,0.);count=nx if orientation=='XZ'else ny
    out=np.zeros((layout['nz'],count),float);valid=np.ones(count,bool)
    for index,weight in zip(indices,weights):
        lookup=layout['lookup'][index,:]if orientation=='XZ'else layout['lookup'][:,index];present=lookup>=0;valid&=present
        if np.any(present):out[:,present]+=weight*values[:,lookup[present]]
    out[:,~valid]=np.nan
    edges=layout['x_edges']if orientation=='XZ'else layout['y_edges']
    return out,edges,layout['z_edges'],dict(orientation=orientation,horizontal_axis='x_mm'if orientation=='XZ'else'y_mm',vertical_axis='depth_mm',
        method='native_depth_samples_with_physical_horizontal_linear_display_interpolation',fixed_axis='y_mm'if orientation=='XZ'else'x_mm',requested_fixed_coordinate_mm=0.,
        native_fixed_sample_coordinates_mm=[float(fixed[i])for i in indices],signed_weights=[float(w)for w in weights],
        z_policy='Original cell-centre samples painted on original nonuniform physical z faces; no interpolation between layers',cross_layer_interpolation=False,quantitative_metrics_derived_from_display=False)


def encoded_plane(np,values,h_edges,v_edges,metadata,quantity,unit):
    values=np.asarray(values);valid=np.isfinite(values);require(values.ndim==2 and values.shape==(len(v_edges)-1,len(h_edges)-1),'Display matrix/actual physical edges ABI')
    finite=values[valid];require(not len(finite)or np.all(abs(finite)<=65504.),'DisplayFloat16 would overflow; preserve values and stop, never clip raw data')
    packed=np.zeros(values.shape,dtype='<f2');packed[valid]=finite.astype('<f2');restored=packed[valid].astype(float)
    require(not len(finite)or np.all(abs(restored-finite)<=FLOAT16_ABSOLUTE_ERROR_BOUND+FLOAT16_RELATIVE_ERROR_BOUND*abs(finite)),'Explicit raw display-pixel quantization bound')
    return dict(orientation=metadata['orientation'],horizontal_axis=metadata['horizontal_axis'],vertical_axis=metadata['vertical_axis'],
        h_edges_mm=[float(x)for x in h_edges],v_edges_mm=[float(x)for x in v_edges],shape=list(values.shape),
        values_b64_float16LE=base64.b64encode(packed.tobytes(order='C')).decode('ascii'),valid_mask_b64_u8=base64.b64encode(valid.astype('u1').tobytes(order='C')).decode('ascii'),
        quantity=quantity,unit=unit,display_only=True,sampling_metadata=metadata,
        quantization=dict(dtype='IEEE754Float16LE',maximum_raw_abs_error=float(np.max(abs(restored-finite)))if len(finite)else 0.,
            raw_absolute_bound=FLOAT16_ABSOLUTE_ERROR_BOUND,raw_relative_bound=FLOAT16_RELATIVE_ERROR_BOUND,
            scaling_caveat='For displayed amplitude scaleA, the raw absolute bound is multiplied by abs(A); source statistics remain originalFloat64 and are not recomputed from pixels',
            original_fields_clipped_or_overwritten=False,not_a_scientific_convergence_gate=True))


def _arrows(np,layout,E,orientation,depth_mm=None,stride=8):
    components=(0,1)if orientation=='XY'else(0,2)if orientation=='XZ'else(1,2)
    u,he,ve,meta=plane_values(np,layout,E[:,components[0]].real,orientation,depth_mm);v,_,_,_=plane_values(np,layout,E[:,components[1]].real,orientation,depth_mm)
    hs=layout['xs']if orientation!='YZ'else layout['ys'];vs=layout['ys']if orientation=='XY'else layout['zs'];rows=[]
    for j in range(0,len(vs),stride):
        for i in range(0,len(hs),stride):
            if np.isfinite(u[j,i])and np.isfinite(v[j,i]):rows.append(dict(h_mm=float(hs[i]),v_mm=float(vs[j]),u_V_m=float(u[j,i]),v_V_m=float(v[j,i])))
    return rows


def extract_case(np,grid,z_faces_mm,scalars,*,E_peak_2000=None,contact_J=None,pad_outlines=None,guard=None,deadline_monotonic=None):
    """Extract five native/display planes per stored AM/RMS; no ROI reductions.

    contact_J is optional already-stored native RMS map {values,valid_mask,
    physical_contact_fraction?}, eachshape(ny,nx). No J is inferred from E.
    pad_outlines must be actual authenticated physical geometry, not a bbox.
    """
    check(guard,deadline_monotonic);layout=native_layout(np,grid,z_faces_mm);require(set(('AM_max2074','carrier_RMS')).issubset(scalars),'Actual stored native AM2074 and carrierRMS required; no angular/scalar reconstruction')
    E=None if E_peak_2000 is None else np.asarray(E_peak_2000)
    if E is not None:require(E.shape==(layout['n'],3)and np.iscomplexobj(E)and np.isfinite(E).all(),'Actual one2000Hz native complex peakE only; no field reconstruction')
    planes={};requests=[('xy15','XY',15.),('xy17p5','XY',17.5),('xy20','XY',20.),('xz','XZ',None),('yz','YZ',None)]
    arrows={}
    if E is not None:
        for key,orientation,depth in requests:
            check(guard,deadline_monotonic);arrows[key]=_arrows(np,layout,E,orientation,depth)
    for quantity in('AM_max2074','carrier_RMS'):
        require(np.asarray(scalars[quantity]).shape==(layout['n'],)and np.all(np.asarray(scalars[quantity])>=0),'Actual nonnegative stored scalar field')
        planes[quantity]={}
        for key,orientation,depth in requests:
            check(guard,deadline_monotonic);values,he,ve,meta=plane_values(np,layout,scalars[quantity],orientation,depth)
            item=encoded_plane(np,values,he,ve,meta,quantity,'V/m')
            if key in arrows:item.update(arrows=arrows[key],arrow_frequency_Hz=2000,arrow_phase_rad=0.,arrow_label='Re(E_peak) at2000Hz,phase0; carrier arrows, never AM vectors')
            planes[quantity][key]=item
    if contact_J is None:planes['contact_J']=dict(status='unavailable',reason='No stored native contact normalJ RMS map supplied; skin/bulkJ is not derived from E')
    else:
        values=np.asarray(contact_J['values']);mask=np.asarray(contact_J['valid_mask'],bool)
        require(values.shape==mask.shape==(len(layout['ys']),len(layout['xs']))and np.all(np.isfinite(values[mask]))and np.all(values[mask]>=0),'Actual stored native contact normal RMS map and exactXY validity mask')
        meta=dict(orientation='XY',horizontal_axis='x_mm',vertical_axis='y_mm',method='stored_native_contact_face_RMS_map',depth_mm=0.,
            physical_scope='Native patch value coloured on its XY face; physical footprints/holes/partial patches are separate authenticated overlays',not_bulk_skin_vector_J=True,
            cross_layer_interpolation=False,quantitative_metrics_derived_from_display=False)
        item=encoded_plane(np,np.where(mask,values,np.nan),layout['x_edges'],layout['y_edges'],meta,'contact_normal_J_RMS','A/m2')
        if 'physical_contact_fraction'in contact_J:
            fraction=np.asarray(contact_J['physical_contact_fraction']);require(fraction.shape==mask.shape and np.all(np.isfinite(fraction))and np.all((fraction>=0)&(fraction<=1+1e-10)),'Actual partial-contact face fractions, no inferred square areas')
            item['physical_contact_fraction_b64_float16LE']=base64.b64encode(fraction.astype('<f2').tobytes()).decode('ascii');item['partial_contact_cell_count']=int(np.count_nonzero(mask&(fraction<1-1e-10)))
        planes['contact_J']=dict(status='stored_native_map',xy=item)
    check(guard,deadline_monotonic)
    return dict(estimator_id=DISPLAY_ESTIMATOR,planes=planes,pad_outlines=[]if pad_outlines is None else pad_outlines,
        missing_pad_outlines=pad_outlines is None,grid=dict(native_cells=layout['n'],XY_nodes=layout['nxy'],depth_planes=layout['nz'],
            XY_faces_x=len(layout['x_edges'])-1,XY_faces_y=len(layout['y_edges'])-1,physical_top_depth_mm=0.,positive_depth='+zdown',layer_interfaces_mm=list(INTERFACES_MM)),
        quantitative_statistics_recomputed=False,source_field_or_original_GUI_modified=False,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,
        axes_policy='Every plane retains native physical edges; only same-layer requestedXYdisplay interpolation. Common renderer/manual ranges persist without candidate/variable autoscaling.')


def rectangle_union_outline(rectangles,pad_id,node,*,declared_area_mm2=None):
    """Exact rectilinear boundary segments; holes remain unfilled geometry.

    Supply actual published rational rectangle bounds[xmin,xmax,ymin,ymax].
    This function never turns fractional area into an invented square patch.
    Curved/nonrectilinear footprints must instead come from original polygons.
    """
    require(0<len(rectangles)<=20000,'Bounded actual physical patch rectangles')
    def F(v):return v if isinstance(v,Fraction)else Fraction(str(v))
    rects=[];lines=defaultdict(lambda:defaultdict(Fraction));xevents=defaultdict(list);area=Fraction(0)
    for row in rectangles:
        require(len(row)==4,'Actual rectangle bounds required');a,b,c,d=map(F,row);require(a<b and c<d,'Positive physical patch width/height')
        require(all(x*x+y*y<=625 for x in(a,b)for y in(c,d)),'Every physical patch corner lies inside fixedD50')
        rects.append((a,b,c,d));area+=(b-a)*(d-c);xevents[a].append((c,d,1));xevents[b].append((c,d,-1))
        for orientation,fixed,lo,hi,sign in(('h',c,a,b,1),('h',d,a,b,-1),('v',a,c,d,-1),('v',b,c,d,1)):
            lines[(orientation,fixed)][lo]+=sign;lines[(orientation,fixed)][hi]-=sign
    # Independent positive-area overlap rejection; no geometric repair.
    active=defaultdict(int);union_area=Fraction(0);xs=sorted(xevents)
    for position,x in enumerate(xs):
        for c,d,change in xevents[x]:active[(c,d)]+=change
        if position+1==len(xs):break
        yevents=defaultdict(int)
        for(c,d),count in active.items():
            if count:yevents[c]+=count;yevents[d]-=count
        ys=sorted(yevents);coverage=0;height=Fraction(0)
        for j,y in enumerate(ys[:-1]):
            coverage+=yevents[y];require(0<=coverage<=1,'Actual physical rectangles overlap; no area rescaling or union repair')
            if coverage:height+=ys[j+1]-y
        union_area+=(xs[position+1]-x)*height
    require(area==union_area,'Exact physical rectangle partition, no overlaps')
    if declared_area_mm2 is not None:require(area==F(declared_area_mm2),'Actual rational footprint area must equal published declared area; no scale correction')
    segments=[]
    for(orientation,fixed),events in sorted(lines.items()):
        points=sorted(events);coverage=0
        for j,start in enumerate(points[:-1]):
            coverage+=events[start];require(abs(coverage)<=1,'Ambiguous or overlapping rectilinear native boundary')
            if not coverage:continue
            end=points[j+1];u,v=(start,end)if coverage>0 else(end,start)
            segments.append([[float(u),float(fixed)],[float(v),float(fixed)]]if orientation=='h'else[[float(fixed),float(u)],[float(fixed),float(v)]])
    return dict(pad_id=pad_id,node=node,patch_rectangles_mm=[[float(v)for v in row]for row in rects],boundary_segments_xy_mm=segments,
        area_mm2=float(area),exact_area_mm2=dict(numerator=area.numerator,denominator=area.denominator),
        physical_geometry_source='Caller-authenticated original rectangle union; rational boundary cancellation only',holes_preserved_by_boundary_segments=True,
        bbox_or_area_inferred_patch=False,geometric_area_rescaled=False,not_a_new_electrode_design=True)
