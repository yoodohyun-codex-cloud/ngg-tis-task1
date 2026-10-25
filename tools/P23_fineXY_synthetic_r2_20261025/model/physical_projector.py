"""Conservative whole-square-cell overlaps and explicit physical-area norms.

Pure functions only: no IO, native data, tests or numerical work on import.
The represented domain is the union of the supplied WHOLE square cells, not a
smooth circle. Cell indices from two grids are never equated. Rectangle order is
[xmin,xmax,ymin,ymax] in mm; physical integration areas are in m^2.
"""
from __future__ import annotations
import math
import numpy as np


DOMAIN_SIDE_MM=50.
DOMAIN_MIN_MM=-25.
COORDINATE_TOLERANCE_MM=1e-8
OVERLAP_WIDTH_TOLERANCE_MM=1e-11
AREA_TOLERANCE_M2=1e-18
DENOMINATOR_FLOOR=1e-12


def require(condition,message):
    if not condition:raise ValueError(message)


def _canonical_cells(xy_mm,h_mm):
    xy=np.asarray(xy_mm,float)
    require(xy.ndim==2 and xy.shape[1]==2 and np.isfinite(xy).all()and
            math.isfinite(h_mm)and h_mm>0,'Finite XY centres and positive spacing required')
    n=int(round(DOMAIN_SIDE_MM/h_mm))
    require(n>0 and abs(n*h_mm-DOMAIN_SIDE_MM)<=COORDINATE_TOLERANCE_MM,
            'Spacing must divide the canonical 50 mm square')
    ij=np.rint((xy-DOMAIN_MIN_MM)/h_mm-.5).astype(np.int64)
    reconstructed=DOMAIN_MIN_MM+(ij+.5)*h_mm
    require(np.all(abs(reconstructed-xy)<=COORDINATE_TOLERANCE_MM)and
            np.all(ij>=0)and np.all(ij<n),'Centres must lie on -25+(i+.5)*h canonical axes')
    require(len(np.unique(ij,axis=0))==len(ij),'Duplicate canonical cells are not allowed')
    return xy,ij,n


def _coverage_summary(coverage,full_cell_area):
    missing=np.maximum(full_cell_area-coverage,0.)
    require(np.all(coverage<=full_cell_area+AREA_TOLERANCE_M2),'Overlap coverage exceeds whole-cell area')
    return dict(domain_area_m2=float(len(coverage)*full_cell_area),
                common_covered_area_m2=float(np.sum(coverage)),
                unmatched_area_m2=float(np.sum(missing)),
                cells_with_unmatched_area=int(np.sum(missing>AREA_TOLERANCE_M2)),
                cells_without_overlap=int(np.sum(coverage<=AREA_TOLERANCE_M2)),
                partially_covered_cells=int(np.sum((coverage>AREA_TOLERANCE_M2)&(missing>AREA_TOLERANCE_M2))),
                fully_covered_cells=int(np.sum(missing<=AREA_TOLERANCE_M2)),
                maximum_overcoverage_m2=float(max(0.,np.max(coverage-full_cell_area)))if len(coverage)else 0.)


def build_overlap(coarse_xy_mm,coarse_h_mm,fine_xy_mm,fine_h_mm,guard=lambda:None):
    """Sparse exact rectangle intersections, with disclosed floating tolerances.

    No centre interpolation/index matching is used. Both input domains are
    whole-square staircase unions. Input row order is preserved in link indices.
    """
    guard();coarse,cij,_=_canonical_cells(coarse_xy_mm,coarse_h_mm)
    fine,fij,nfine=_canonical_cells(fine_xy_mm,fine_h_mm)
    lookup={tuple(int(v)for v in key):index for index,key in enumerate(fij)}
    ci=[];fi=[];areas=[];rectangles=[]
    for c,key in enumerate(cij):
        if c%128==0:guard()
        x0=DOMAIN_MIN_MM+int(key[0])*coarse_h_mm;x1=x0+coarse_h_mm
        y0=DOMAIN_MIN_MM+int(key[1])*coarse_h_mm;y1=y0+coarse_h_mm
        # One extra candidate on each edge makes roundoff at aligned boundaries
        # harmless; zero-width contacts are explicitly excluded below.
        ilo=max(0,int(math.floor((x0-DOMAIN_MIN_MM)/fine_h_mm))-1)
        ihi=min(nfine-1,int(math.floor((x1-DOMAIN_MIN_MM)/fine_h_mm))+1)
        jlo=max(0,int(math.floor((y0-DOMAIN_MIN_MM)/fine_h_mm))-1)
        jhi=min(nfine-1,int(math.floor((y1-DOMAIN_MIN_MM)/fine_h_mm))+1)
        for i in range(ilo,ihi+1):
            fx0=DOMAIN_MIN_MM+i*fine_h_mm;fx1=fx0+fine_h_mm
            a=max(x0,fx0);b=min(x1,fx1)
            if b-a<=OVERLAP_WIDTH_TOLERANCE_MM:continue
            for j in range(jlo,jhi+1):
                f=lookup.get((i,j))
                if f is None:continue
                fy0=DOMAIN_MIN_MM+j*fine_h_mm;fy1=fy0+fine_h_mm
                d=max(y0,fy0);e=min(y1,fy1)
                if e-d<=OVERLAP_WIDTH_TOLERANCE_MM:continue
                ci.append(c);fi.append(f);areas.append((b-a)*(e-d)*1e-6)
                rectangles.append((a,b,d,e))
    guard();ci=np.asarray(ci,np.int64);fi=np.asarray(fi,np.int64);area=np.asarray(areas,float)
    rectangles=np.asarray(rectangles,float).reshape((-1,4))
    cc=np.bincount(ci,weights=area,minlength=len(coarse));fc=np.bincount(fi,weights=area,minlength=len(fine))
    common=float(np.sum(area))
    summary=dict(schema='task1-whole-square-overlap-v1',domain_representation='Union of whole canonical square cells; not a smooth disk',
                 coordinate_axes='x,y in mm; canonical centre=-25+(index+.5)*h; 50 mm square',
                 rectangle_bounds_order=['xmin','xmax','ymin','ymax'],area_units='m2',
                 coarse_cells=len(coarse),fine_cells=len(fine),overlap_links=len(area),
                 coarse_h_mm=float(coarse_h_mm),fine_h_mm=float(fine_h_mm),common_area_m2=common,
                 coarse=_coverage_summary(cc,coarse_h_mm**2*1e-6),
                 fine=_coverage_summary(fc,fine_h_mm**2*1e-6),
                 coordinate_tolerance_mm=COORDINATE_TOLERANCE_MM,
                 excluded_zero_width_tolerance_mm=OVERLAP_WIDTH_TOLERANCE_MM,
                 coverage_roundoff_tolerance_m2=AREA_TOLERANCE_M2)
    return dict(coarse_index=ci,fine_index=fi,area_m2=area,rectangle_mm=rectangles,
                coarse_coverage_area_m2=cc,fine_coverage_area_m2=fc,summary=summary)


def compare_piecewise(coarsevalues,finevalues,links,weights=None):
    """JSON-safe pairwise and projected-average norms on the same common area.

    Each input is one scalar complex piecewise-constant field per cell. Optional
    weights are DIMENSIONLESS nonnegative integration densities per link;
    weights=ROI_intersection_area_m2/links['area_m2'] integrates an exact ROI.
    Pairwise L2 is primary: fine variation lost by coarse-cell averaging remains
    in that norm. No automatic pass/fail gate or temporal sqrt(2) is applied.
    """
    coarse=np.asarray(coarsevalues,complex);fine=np.asarray(finevalues,complex)
    ci=np.asarray(links['coarse_index'],np.int64);fi=np.asarray(links['fine_index'],np.int64)
    area=np.asarray(links['area_m2'],float)
    require(coarse.ndim==fine.ndim==1 and np.isfinite(coarse).all()and np.isfinite(fine).all()and
            ci.shape==fi.shape==area.shape and area.ndim==1 and np.isfinite(area).all()and np.all(area>0),
            'Finite scalar fields and positive finite overlap-link areas required')
    require(np.all(ci>=0)and np.all(ci<len(coarse))and np.all(fi>=0)and np.all(fi<len(fine)),
            'Overlap indices must address the supplied fields')
    density=np.ones(len(area))if weights is None else np.asarray(weights,float)
    require(density.shape==area.shape and np.isfinite(density).all()and np.all(density>=0),
            'Optional weights must be one finite nonnegative dimensionless density per link')
    w=area*density;total=float(np.sum(w))
    if total<=0:return dict(status='not_run_no_common_weighted_area',weighted_area_m2=total,
                            automatic_gate_applied=False)
    a=coarse[ci];b=fine[fi];difference=a-b
    coarse_rms=float(np.sqrt(np.sum(w*abs(a)**2)/total))
    fine_rms=float(np.sqrt(np.sum(w*abs(b)**2)/total));denominator=max(coarse_rms,DENOMINATOR_FLOOR)
    pair_squared=float(np.sum(w*abs(difference)**2)/total)
    coverage=np.bincount(ci,weights=w,minlength=len(coarse));use=coverage>0
    fine_integral=np.bincount(ci,weights=w*b.real,minlength=len(coarse))+1j*np.bincount(ci,weights=w*b.imag,minlength=len(coarse))
    average=np.zeros(len(coarse),complex);average[use]=fine_integral[use]/coverage[use]
    projected_squared=float(np.sum(coverage[use]*abs(coarse[use]-average[use])**2)/total)
    difference_mean=np.sum(w*difference)/total
    return dict(schema='task1-physical-piecewise-common-area-comparison-v1',status='diagnostic_not_gated',
                reference='Coarse field on the common represented whole-square area; not physical truth',
                weighted_area_m2=total,common_unweighted_area_m2=float(np.sum(area)),
                contributing_links=int(np.sum(w>0)),contributing_coarse_cells=int(np.sum(use)),
                coarse_spatial_complex_RMS=coarse_rms,fine_spatial_complex_RMS=fine_rms,
                denominator=denominator,denominator_floor=DENOMINATOR_FLOOR,
                denominator_floor_used=coarse_rms<DENOMINATOR_FLOOR,
                pairwise_primary=dict(absolute_L2=math.sqrt(max(0.,pair_squared)),normalized_L2=math.sqrt(max(0.,pair_squared))/denominator,
                                      squared_L2=pair_squared),
                projected_coarse_average_secondary=dict(absolute_L2=math.sqrt(max(0.,projected_squared)),
                    normalized_L2=math.sqrt(max(0.,projected_squared))/denominator,squared_L2=projected_squared),
                within_coarse_fine_variation_squared=pair_squared-projected_squared,
                complex_difference_mean=dict(real=float(difference_mean.real),imaginary=float(difference_mean.imag)),
                norm_definition='sqrt(sum(area_m2*density*abs(complex difference)^2)/sum(area_m2*density)); spatial peak-amplitude norm, no temporal sqrt(2)',
                projection_warning='Averaging fine values within each covered coarse cell can hide fine variation; pairwise norm is primary',
                automatic_gate_applied=False)


def _quadrant_prefix(a,b,radius):
    a=min(abs(a),radius);b=min(abs(b),radius)
    if a<=0 or b<=0:return 0.
    x0=math.sqrt(max(0.,radius*radius-b*b));cut=min(a,x0)
    area=b*cut
    if a>x0:
        def primitive(x):
            x=min(max(x,0.),radius)
            return .5*(x*math.sqrt(max(0.,radius*radius-x*x))+radius*radius*math.asin(x/radius))
        area+=primitive(a)-primitive(x0)
    return area


def _disk_rect_area_mm2(bounds,radius):
    x0,x1,y0,y1=(float(v)for v in bounds)
    require(x0<=x1 and y0<=y1,'Ordered rectangle bounds required')
    if x0==x1 or y0==y1:return 0.
    def prefix(x,y):
        if x==0 or y==0:return 0.
        return (1. if x*y>0 else -1.)*_quadrant_prefix(x,y,radius)
    area=prefix(x1,y1)-prefix(x0,y1)-prefix(x1,y0)+prefix(x0,y0)
    rectangle=(x1-x0)*(y1-y0);tolerance=1e-12*max(1.,radius*radius,rectangle)
    require(-tolerance<=area<=rectangle+tolerance,'Analytic disk intersection outside rectangle area bounds')
    return min(rectangle,max(0.,area))


def analyticdisk_rect_area(bounds,radius_mm=5.):
    """Exact analytic centred-disk/rectangle intersection area in m^2.

    bounds is [xmin,xmax,ymin,ymax] mm or an (N,4) array. A single rectangle
    returns float; multiple rectangles return a float array. Signed quadrant
    prefix inclusion-exclusion handles rectangles crossing either axis.
    This is a new explicit analytic ROI weighting, not a rewrite of old masks.
    """
    rectangles=np.asarray(bounds,float)
    require(math.isfinite(radius_mm)and radius_mm>0 and np.isfinite(rectangles).all()and
            (rectangles.shape==(4,)or(rectangles.ndim==2 and rectangles.shape[1]==4)),
            'Finite rectangle bounds and positive finite disk radius required')
    if rectangles.ndim==1:return _disk_rect_area_mm2(rectangles,radius_mm)*1e-6
    return np.asarray([_disk_rect_area_mm2(row,radius_mm)*1e-6 for row in rectangles],float)
