"""Pure fixed-reference high-modulation volume bookkeeping, not activation thresholds."""
import numpy as np

def build(summary,new_values,baseline_values,weights,grid,guard):
    reference=float(summary['comparison_to_original_same_drive']['target']['baseline_cached_maxTIS_2074']['mean'])
    if not np.isfinite(reference)or reference<=0:raise ValueError('Positive frozen baseline reference required')
    rows=[]
    for normalization in summary['separate_linear_normalizations']:
        guard();factor=float(normalization['common_source_amplitude_scale'])
        for multiple in(.5,1.,2.):
            cutoff=reference*multiple
            for region,w in weights.items():
                w=np.asarray(w,float)
                if w.shape!=(len(grid),)or not np.isfinite(w).all()or np.any(w<0):raise ValueError('Finite original same-grid volume weights')
                total=float(np.sum(w,dtype=np.float64))
                for model,values,scale in(('legacy_baseline',baseline_values,1.),('human_reference_surrogate',new_values,factor)):
                    values=np.asarray(values,float)
                    if values.shape!=(len(grid),)or not np.isfinite(values).all():raise ValueError('Finite lossless directional modulation scalar')
                    selected=(w>0)&(values*scale>=cutoff);volume=float(np.sum(w[selected],dtype=np.float64));ids=np.flatnonzero(selected)
                    if not 0<=volume<=total*(1+1e-12):raise ValueError('High-modulation volume domain')
                    rows.append(dict(normalization=normalization['name'],model=model,region=region,source_amplitude_scale=scale,
                        reference_multiple=multiple,cutoff_V_m=cutoff,volume_above_mm3=volume*1e9,fraction_of_region=volume/total,
                        native_cells_above=int(len(ids)),native_center_bbox_xyz_mm=None if not len(ids)else dict(min=grid[ids,:3].min(axis=0).tolist(),max=grid[ids,:3].max(axis=0).tolist())))
    return dict(schema='task1-high-modulation-numerical-volume-audit-v1',metric='fundamental_maxTIS_2074_V_m; finite sampled directions',
        numerical_reference='Original canonical baseline target ROI volume-weighted mean at high-Z1Vpp; frozen shared reference across models and normalizations',
        reference_V_m=reference,reference_multiples=[.5,1.,2.],thresholds_are_physiological=False,activation_thresholds_validated=False,
        spatial_scope='Cell-constant Float64 values and original represented-volume ROI masks; bbox is selected native cell centres, not continuum boundary',
        field_values_changed=False,new_PDE=0,rows=rows)
