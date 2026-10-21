"""Pure rectangle/mask geometry diagnostics; no solver or research imports.

Whole-cell support is a conservative numerical footprint. Shared tissue DOFs
do not imply merged physical metal pads or a verified electrical short.
"""
from __future__ import annotations

import csv
import itertools
import math
from pathlib import Path


def _require(ok,message):
    if not ok:raise ValueError(message)


def masks_from_csv(path):
    with Path(path).open(newline='') as stream:
        reader=csv.DictReader(stream)
        _require(reader.fieldnames == ['pad','i','j','area_m2'],'Exact native contact-mask CSV columns required')
        rows=[]
        for row in reader:
            _require(None not in row and all(row[k] is not None for k in reader.fieldnames),'Malformed mask CSV row')
            rows.append((int(row['pad']),int(row['i']),int(row['j']),float(row['area_m2'])))
    return rows


def _bbox_gap(a,b):
    dx=max(a[0]-b[1],b[0]-a[1]);dy=max(a[2]-b[3],b[2]-a[3])
    signed=(-min(-dx,-dy) if dx<0 and dy<0 else math.hypot(max(dx,0),max(dy,0)))
    return signed,[dx,dy]


def _intersection(pad,i,j,h):
    x,y=-25+(i+.5)*h,-25+(j+.5)*h
    dx=max(0.,min(x+h/2,pad['x_mm']+pad['width_mm']/2)-max(x-h/2,pad['x_mm']-pad['width_mm']/2))
    dy=max(0.,min(y+h/2,pad['y_mm']+pad['height_mm']/2)-max(y-h/2,pad['y_mm']-pad['height_mm']/2))
    return dx*dy*1e-6


def _centre_distance(a,b,h):
    def extents(points):
        xs=[x for x,_ in points];ys=[y for _,y in points]
        return min(xs),max(xs),min(ys),max(ys)
    aa,bb=extents(a),extents(b)
    cartesian=lambda points,box:len(points) == (box[1]-box[0]+1)*(box[3]-box[2]+1)
    if cartesian(a,aa) and cartesian(b,bb):
        return h*math.hypot(max(aa[0]-bb[1],bb[0]-aa[1],0),max(aa[2]-bb[3],bb[2]-aa[3],0))
    return h*math.sqrt(min((i-k)**2+(j-l)**2 for i,j in a for k,l in b))


def audit_mask_geometry(rows,case):
    """Return geometry/area/shared-DOF facts without modifying input rows."""
    n=case['n_pads'];h=case['h_xy_mm'];face=(h/1000)**2
    _require(n in (4,8,12,16) and h in (.625,1.25) and case['n_outputs'] == 2 and
        case['n_return_nodes'] == 1,'Registered4/8/12/16-pad,2-output,commonGND coarse/fine geometry required')
    pads=case['pads'];nodes=case['pad_node_ids'];m=n//4
    _require(len(pads) == n and nodes == [0]*m+[1]*m+[-1]*(2*m),'Explicit physical-pad/node parent groups required')
    expected=case['expected_pad_areas_m2']
    _require(len(expected) == n and all(math.isfinite(a) and a>0 for a in expected),'Positive explicit physical pad areas required')
    analytic=[]
    for p,pad in enumerate(pads):
        _require(pad['pad_id'] == p and pad['parent_group'] == p//m and pad['node'] == nodes[p] and
            pad['shape'] == 'rectangle' and pad['rotation_deg'] == 0 and pad.get('attachment') == 'top_z0' and
            all(type(pad[k]) in (int,float) and math.isfinite(pad[k]) for k in ('x_mm','y_mm','width_mm','height_mm','area_mm2')) and
            min(pad['width_mm'],pad['height_mm'])>0,'Finite axis-aligned top rectangle/node definitions required')
        x,y,w,t=(pad[k] for k in ('x_mm','y_mm','width_mm','height_mm'))
        _require(abs(pad['area_mm2']/(w*t)-1) <= 1e-10 and abs(expected[p]/(w*t*1e-6)-1) <= 1e-10,
            'Analytic/registered physical rectangle area differs')
        box=[x-w/2,x+w/2,y-t/2,y+t/2]
        _require(all(xx*xx+yy*yy < 625 for xx in box[:2] for yy in box[2:]),'Physical rectangle outside fixedD50')
        analytic.append(box)
    by_pad=[{} for _ in pads];by_face={};ratios=[]
    for row in rows:
        _require(len(row) == 4,'Four columns required per mask row')
        p,i,j,area=row
        _require(all(type(v) is int for v in (p,i,j)) and 0<=p<n and 0<=i<round(50/h) and 0<=j<round(50/h) and
            type(area) in (int,float) and math.isfinite(area) and 0<area<=face*(1+1e-10) and
            (i,j) not in by_pad[p] and (-25+(i+.5)*h)**2+(-25+(j+.5)*h)**2<625,
            'Invalid/duplicate physical contact patch or outside native face')
        exact=_intersection(pads[p],i,j,h)
        _require(exact>0 and abs(area/exact-1)<=1e-10,'Stored patch differs from exact physical rectangle intersection')
        by_pad[p][i,j]=area;by_face.setdefault((i,j),[]).append((p,area));ratios.append(area/face)
    _require(all(by_pad),'Every physical pad requires represented contact patches')
    _require(all(math.fsum(a for _,a in patches)<=face*(1+1e-10) for patches in by_face.values()),
        'Sum of physical patches exceeds one native tissue top-face area')
    per_pad=[];supports=[]
    for p,patches in enumerate(by_pad):
        is_=[i for i,_ in patches];js=[j for _,j in patches]
        support=[-25+min(is_)*h,-25+(max(is_)+1)*h,-25+min(js)*h,-25+(max(js)+1)*h]
        supports.append(support);observed=math.fsum(patches.values());area=math.prod((pads[p]['width_mm'],pads[p]['height_mm']))
        omitted=[];positive=0
        box=analytic[p]
        for j in range(max(0,math.floor((box[2]+25)/h)),min(round(50/h),math.ceil((box[3]+25)/h))):
            for i in range(max(0,math.floor((box[0]+25)/h)),min(round(50/h),math.ceil((box[1]+25)/h))):
                intersection=_intersection(pads[p],i,j,h)
                if intersection>0:
                    positive+=1
                    if (i,j) not in patches:omitted.append(intersection)
        error=observed/(area*1e-6)-1
        per_pad.append(dict(pad_id=p,parent_group=pads[p]['parent_group'],node=nodes[p],analytic_area_mm2=area,
            represented_area_m2=observed,expected_area_m2=expected[p],represented_vs_analytic_relative_error=error,
            area_gate_passed=abs(error)<=1e-10,contact_cells=len(patches),support_bbox_mm=support,
            analytic_bbox_mm=analytic[p],partial_face_count=sum(abs(a/face-1)>4*math.ulp(1.) for a in patches.values()),
            minimum_fragment_area_m2=min(patches.values()),minimum_fragment_fraction=min(patches.values())/face,
            reconstructed_positive_intersection_count=positive,omitted_positive_intersection_count=len(omitted),
            omitted_positive_intersection_area_m2=math.fsum(omitted),area_values_modified=False))
    pairwise=[];same=[];different=[]
    for p,q in itertools.combinations(range(n),2):
        ag,axis=_bbox_gap(analytic[p],analytic[q]);sg,saxis=_bbox_gap(supports[p],supports[q])
        shared=len(set(by_pad[p]).intersection(by_pad[q]))
        if shared:(same if nodes[p] == nodes[q] else different).append([p,q])
        pairwise.append(dict(pad_a=p,pad_b=q,node_a=nodes[p],node_b=nodes[q],same_electrical_node=nodes[p] == nodes[q],
            analytic_gap_mm=max(ag,0.),analytic_signed_axis_gap_mm=axis,physical_bbox_overlap=ag<0,
            represented_support_signed_bbox_gap_mm=sg,support_signed_axis_gap_mm=saxis,
            contact_cell_centre_min_distance_mm=_centre_distance(by_pad[p],by_pad[q],h),shared_top_face_count=shared))
    parents=[]
    for group in range(4):
        members=per_pad[group*m:(group+1)*m]
        parents.append(dict(parent_group=group,node=nodes[group*m],
            analytic_area_mm2=math.fsum(p['analytic_area_mm2'] for p in members),
            represented_area_m2=math.fsum(p['represented_area_m2'] for p in members),
            expected_area_m2=math.fsum(p['expected_area_m2'] for p in members)))
    shared=[dict(i=i,j=j,x_mm=-25+(i+.5)*h,y_mm=-25+(j+.5)*h,
        pad_ids=[p for p,_ in patches],node_ids=[nodes[p] for p,_ in patches],
        represented_area_m2=math.fsum(a for _,a in patches)) for (i,j),patches in sorted(by_face.items()) if len(patches)>1]
    return dict(schema='task1-grouped-mask-gap-geometry-v1',status='computed_geometry_only',h_xy_mm=h,
        physical_pad_count=n,n_outputs=2,n_return_nodes=1,pad_node_ids=list(nodes),
        pads=per_pad,parents=parents,pairwise=pairwise,
        analytical_minimum_gap_mm=min(p['analytic_gap_mm'] for p in pairwise),
        analytical_minimum_gap_in_cells=min(p['analytic_gap_mm'] for p in pairwise)/h,
        minimum_represented_support_signed_bbox_gap_mm=min(p['represented_support_signed_bbox_gap_mm'] for p in pairwise),
        minimum_contact_cell_centre_distance_mm=min(p['contact_cell_centre_min_distance_mm'] for p in pairwise),
        shared_tissue_top_faces=dict(count=len(shared),physical_pad_pairs_same_node=len(same),
            physical_pad_pairs_different_nodes=len(different),same_node_pairs=same,different_node_pairs=different,faces=shared),
        represented_total_area_m2=math.fsum(p['represented_area_m2'] for p in per_pad),
        analytic_total_area_mm2=math.fsum(p['analytic_area_mm2'] for p in per_pad),
        expected_total_area_m2=math.fsum(expected),contact_patch_count=len(rows),
        fragment_fraction_counts={str(cutoff):sum(r<cutoff for r in ratios) for cutoff in (1e-6,1e-3,.01,.1)},
        all_pad_native_area_gates_passed=all(p['area_gate_passed'] for p in per_pad),
        input_rows_modified=False,area_renormalization=False,physical_electrode_merging_assumed=False,
        numerical_convergence_validated=False,experimental_validation=False,
        definitions=dict(analytic_gap='Euclidean distance between physical axis-aligned rectangles; mm',
            represented_support_gap='Signed minimum separation of entire contacted-cell bounding boxes; negative means overlap, zero includes touch; conservative numerical footprint, not physical gap',
            centre_distance='Minimum XY distance between actual contacted native-cell centres; zero for a shared tissue top DOF',
            shared_tissue_DOF='Distinct physical metal pads retain separate contact edges; shared tissue node is not a claim of a metal short',
            fragments='Stored positive overlaps are retained verbatim; omitted positive intersections are separately counted; numeric bins are not safety limits'))
