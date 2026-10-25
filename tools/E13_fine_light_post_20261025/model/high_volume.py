"""Thresholded cached scalar volumes; no field/metric reconstruction or IO.

Numerical cutoffs are fixed by the caller from original coarse101 B0.  They
classify the stored piecewise-constant sampled modulation field and are not
physiological thresholds or convergence/adoption gates.
"""
import math,time

def require(ok,message):
    if not ok:raise ValueError(message)

def check(guard,deadline):
    guard()
    if deadline is not None and time.monotonic()>=deadline:
        raise TimeoutError('Finite cached high-volume postprocessing deadline')

def threshold_summary(np,grid,values,weights,cutoff,amplitude_scale=1.,*,
                      guard=lambda:None,deadline_monotonic=None,chunk=65536):
    """One weighted threshold subset, without changing cached arrays.

    Extents refer to native cell centres with positive ROI intersection weight;
    they are not an isosurface or a resolved boundary of the high-field volume.
    At most sixteen tied hotspot centres are exported, with the full tie count.
    """
    require(grid.ndim==2 and grid.shape[1]==5 and values.shape==weights.shape==(len(grid),),
            'Same authenticated flat grid/scalar/fractional-volume ABI')
    require(type(chunk)is int and 0<chunk<=65536,'Finite bounded reduction chunk')
    require(math.isfinite(float(cutoff))and cutoff>0 and
            math.isfinite(float(amplitude_scale))and amplitude_scale>=0,
            'Positive fixed numerical cutoff and nonnegative finite amplitude scale')
    total=volume=0.;positive=selected=ties=0;peak=None;peak_sites=[]
    lower=upper=None;layer_volume={};moments=[0.,0.,0.]
    for start in range(0,len(grid),chunk):
        check(guard,deadline_monotonic);stop=min(start+chunk,len(grid))
        v=values[start:stop];w=weights[start:stop];g=grid[start:stop]
        require(np.isfinite(v).all()and np.isfinite(w).all()and np.isfinite(g).all()
                and np.all(v>=0)and np.all(w>=0),'Finite nonnegative cached scalar/ROI weights')
        in_roi=w>0;positive+=int(np.count_nonzero(in_roi));total+=float(w.sum())
        # Multiplication inside this bounded chunk implements the documented
        # IEEE predicate directly, including exact threshold ties.
        scaled=v*amplitude_scale
        require(np.isfinite(scaled).all(),'Finite scaled cached scalar in bounded chunk')
        use=in_roi&(scaled>=cutoff)
        count=int(np.count_nonzero(use));selected+=count
        if not count:continue
        xyzd=g[use,:3];wu=w[use];vu=scaled[use];layer=g[use,3]
        added=float(wu.sum());volume+=added
        lo=xyzd.min(axis=0);hi=xyzd.max(axis=0)
        lower=lo.tolist()if lower is None else [min(lower[k],float(lo[k]))for k in range(3)]
        upper=hi.tolist()if upper is None else [max(upper[k],float(hi[k]))for k in range(3)]
        for k in range(3):moments[k]+=float(np.sum(xyzd[:,k]*wu))
        for ident in np.unique(layer):
            key=str(int(ident));layer_volume[key]=layer_volume.get(key,0.)+float(wu[layer==ident].sum())
        local=float(vu.max())
        if peak is None or local>peak:peak=local;ties=0;peak_sites=[]
        if local==peak:
            indexes=np.flatnonzero(use&(scaled==peak));ties+=len(indexes)
            for offset in indexes[:max(0,16-len(peak_sites))]:
                index=start+int(offset);row=grid[index]
                peak_sites.append(dict(native_cell_index=index,x_mm=float(row[0]),
                    y_mm=float(row[1]),depth_mm=float(row[2]),layer_index=int(row[3]),
                    ROI_intersection_volume_m3=float(weights[index])))
    check(guard,deadline_monotonic)
    return dict(status='complete_cached_scalar_threshold_diagnostic',cutoff_V_m=float(cutoff),
        amplitude_scale=float(amplitude_scale),threshold_evaluation='Within bounded chunk: stored_scalar * amplitude_scale >= cutoff',
        ROI_volume_m3=total,high_modulation_volume_m3=volume,
        high_modulation_volume_fraction=volume/total if total>0 else None,
        native_positive_ROI_weight_cells=positive,native_threshold_subset_cells=selected,
        volume_weighting='Published fractional physical ROI-intersection weights; sampled native scalar treated constant within its cell',
        high_subset_native_centre_bounds_mm=dict(minimum=lower,maximum=upper),
        weighted_native_centre_mm=[v/volume for v in moments]if volume>0 else None,
        layer_high_modulation_volume_m3=layer_volume,
        high_subset_maximum_V_m=float(peak)if peak is not None else None,
        hotspot_centres=peak_sites,hotspot_tie_count=ties,hotspot_coordinates_limit=16,
        spatial_extent_scope='Native centre extent only, not an isosurface or proof of depth selectivity',
        threshold_rule='Scaled cached scalar >= fixed cutoff, and ROI weight > 0',
        physiological_threshold=False,safety_limit=False,numerical_gate=False,
        cached_scalar_modified=False,old_statistics_recomputed=False,new_angular_evaluations=0)
