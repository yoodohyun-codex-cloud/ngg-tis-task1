"""Deferred certified ellipse/square intersections using exact scalar intervals.

No file reads, scientific imports, geometry or numerical work occur on import.
The caller supplies authenticated physical centres and graph indices. All
integration uses Fraction interval arithmetic, directed dyadic rounding, exact
integer square-root brackets and a bounded alternating atan series. No libm
trigonometric accuracy assumption or two-resolution error estimate is used.
"""
import math
import operator
import time
from fractions import Fraction as F

BITS=160
SERIES_TERMS=80
MAX_SEGMENTS=24
MAX_CONTACT_CANDIDATE_CELLS=10000
PI_DECIMAL='3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679'


def require(ok,message):
    if not ok:raise ValueError(message)


def _f(value):
    require(type(value) is not bool,'Boolean is not a physical coordinate')
    if isinstance(value,F):return value
    if isinstance(value,float):
        require(math.isfinite(value),'Finite physical coordinate');return F.from_float(value)
    return F(value)


def _check(guard,deadline):
    guard()
    if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite ellipse contact certificate incomplete')


def _down(value):
    value=_f(value);scale=1<<BITS
    return F((value.numerator*scale)//value.denominator,scale)


def _up(value):return -_down(-_f(value))


class Interval:
    """Exact enclosure with explicit outward dyadic rounding after every op."""
    def __init__(self,lo,hi=None):
        lo=_f(lo);hi=lo if hi is None else _f(hi)
        require(lo<=hi,'Ordered exact interval');self.lo=_down(lo);self.hi=_up(hi)
    def __add__(self,other):
        other=_i(other);return Interval(self.lo+other.lo,self.hi+other.hi)
    __radd__=__add__
    def __neg__(self):return Interval(-self.hi,-self.lo)
    def __sub__(self,other):return self+-_i(other)
    def __rsub__(self,other):return _i(other)+-self
    def __mul__(self,other):
        other=_i(other);v=[a*b for a in (self.lo,self.hi) for b in (other.lo,other.hi)]
        return Interval(min(v),max(v))
    __rmul__=__mul__
    def __truediv__(self,other):
        other=_i(other);require(not(other.lo<=0<=other.hi),'Interval division through zero')
        return self*Interval(1/other.hi,1/other.lo)
    def __rtruediv__(self,other):return _i(other)/self


def _i(value):return value if isinstance(value,Interval) else Interval(value)


def _sqrt_point(value):
    value=_f(value);require(value>=0,'Nonnegative exact square root')
    scale=1<<BITS;q=(value.numerator*(scale*scale))//value.denominator
    low=F(math.isqrt(q),scale)
    return Interval(low,low if low*low==value else low+F(1,scale))


def _sqrt(value):
    value=_i(value);require(value.lo>=0,'Nonnegative square-root interval')
    return Interval(_sqrt_point(value.lo).lo,_sqrt_point(value.hi).hi)


def _pi():
    # The displayed decimal is a truncation of pi, so one last-decimal unit
    # gives a strict mathematical bracket. Original physical area is 225mm2.
    digits=len(PI_DECIMAL.split('.')[1]);low=F(PI_DECIMAL)
    return Interval(low,low+F(1,10**digits))


def _atan_small(value,guard,deadline):
    value=_f(value);require(0<=value<=F(1,2),'Bounded atan range reduction')
    x=Interval(value);square=x*x;power=x;total=Interval(0)
    for n in range(SERIES_TERMS):
        if n%16==0:_check(guard,deadline)
        term=power/(2*n+1);total=total+term if n%2==0 else total-term;power=power*square
    # Alternating remainder <= next omitted term; interval roundoff is already
    # included in total and power. Symmetric bound is deliberately conservative.
    remainder=power.hi/F(2*SERIES_TERMS+1)
    return total+Interval(-remainder,remainder)


def _atan_point(value,guard,deadline):
    value=_f(value)
    if value<0:return -_atan_point(-value,guard,deadline)
    if value>1:return _pi()/2-_atan_point(1/value,guard,deadline)
    if value==1:return _pi()/4
    # atan(x)=2 atan(x/(1+sqrt(1+x^2))); reduced x <= sqrt(2)-1 < 1/2.
    reduced=Interval(value)/(1+_sqrt(1+Interval(value)*value))
    require(0<=reduced.lo<=reduced.hi<=F(1,2),'Certified bounded atan reduction')
    return 2*Interval(_atan_small(reduced.lo,guard,deadline).lo,_atan_small(reduced.hi,guard,deadline).hi)


def _asin_point(value,guard,deadline):
    value=_f(value);require(-1<=value<=1,'asin physical domain')
    if value<0:return -_asin_point(-value,guard,deadline)
    if value==1:return _pi()/2
    reduced=Interval(value)/(1+_sqrt(Interval(1)-Interval(value)*value))
    return 2*Interval(_atan_point(reduced.lo,guard,deadline).lo,_atan_point(reduced.hi,guard,deadline).hi)


def _asin(value,guard,deadline):
    value=_i(value);require(-1<=value.lo<=value.hi<=1,'Enclosed asin physical domain')
    return Interval(_asin_point(value.lo,guard,deadline).lo,_asin_point(value.hi,guard,deadline).hi)


def _float_lower(value):
    value=_f(value);answer=float(value)
    return math.nextafter(answer,-math.inf) if F.from_float(answer)>value else answer


def _float_upper(value):
    value=_f(value);answer=float(value)
    return math.nextafter(answer,math.inf) if F.from_float(answer)<value else answer


def _json_interval(value):
    value=_i(value);return dict(lower=_float_lower(value.lo),upper=_float_upper(value.hi))


def _rational(value):
    value=_f(value);return dict(numerator=value.numerator,denominator=value.denominator)


def _coefficients(cx,cy,a,b,orientation):
    if orientation=='axis_x':return 1/(a*a),F(0),1/(b*b)
    if orientation=='axis_y':return 1/(b*b),F(0),1/(a*a)
    require(orientation=='tangential' and cx*cx+cy*cy>0,'Tangential nonzero physical centre')
    r2=cx*cx+cy*cy
    return ((cy*cy/(a*a)+cx*cx/(b*b))/r2,
            cx*cy*(1/(b*b)-1/(a*a))/r2,
            (cx*cx/(a*a)+cy*cy/(b*b))/r2)


def make_ellipse(cx_mm,cy_mm,semimajor_mm=13,area_mm2=225,orientation='tangential'):
    """Internal scalar shape; its analytic centroid is exactly the supplied centre."""
    cx,cy,a,area=map(_f,(cx_mm,cy_mm,semimajor_mm,area_mm2))
    require(a>0 and area>0,'Positive analytic ellipse dimensions')
    pi=_pi();b=Interval(area)/(pi*a);require(0<b.lo<=b.hi<a,'Radial semiminor less than tangential semimajor')
    middle=(b.lo+b.hi)/2;A,B,C=_coefficients(cx,cy,a,middle,orientation);det=A*C-B*B
    require(A>0 and C>0 and det>0,'Positive definite exact conic')
    outer_A,outer_B,outer_C=_coefficients(cx,cy,a,b.hi,orientation)
    outer_det=outer_A*outer_C-outer_B*outer_B
    return dict(cx=cx,cy=cy,a=a,b=b,b_middle=middle,area=area,orientation=orientation,
                A=A,B=B,C=C,rx=_sqrt(Interval(C/det)),ry=_sqrt(Interval(A/det)),
                physical_support_rx=_sqrt(Interval(outer_C/outer_det)),
                physical_support_ry=_sqrt(Interval(outer_A/outer_det)))


def _quadratic(shape,x,y,b):
    A,B,C=_coefficients(shape['cx'],shape['cy'],shape['a'],b,shape['orientation'])
    dx=x-shape['cx'];dy=y-shape['cy'];return A*dx*dx+2*B*dx*dy+C*dy*dy


def _minimum_quadratic(shape,rectangle,b):
    x0,x1,y0,y1=rectangle;cx,cy=shape['cx'],shape['cy'];A,B,C=_coefficients(cx,cy,shape['a'],b,shape['orientation'])
    clamp=lambda v,lo,hi:max(lo,min(hi,v))
    points=[(x,y) for x in (x0,x1) for y in (y0,y1)]
    if x0<=cx<=x1 and y0<=cy<=y1:points.append((cx,cy))
    for x in (x0,x1):points.append((x,clamp(cy-B*(x-cx)/C,y0,y1)))
    for y in (y0,y1):points.append((clamp(cx-B*(y-cy)/A,x0,x1),y))
    return min(_quadratic(shape,x,y,b) for x,y in points)


def _height_bounds(shape,x):
    dx=Interval(x-shape['cx']);m=Interval(-shape['B']/shape['C'])
    rad=1-dx*dx/(shape['rx']*shape['rx'])
    require(rad.hi>=0,'Inner horizontal integration domain')
    half=_sqrt(1/Interval(shape['C']))*_sqrt(Interval(max(F(0),rad.lo),max(F(0),rad.hi)))
    middle=shape['cy']+m*dx
    return middle-half,middle+half


def _root_bands(shape,y,lo,hi):
    dy=Interval(y-shape['cy']);ry=shape['ry'];rad=1-dy*dy/(ry*ry)
    if rad.hi<0:return []
    amplitude=_sqrt(1/Interval(shape['A']))*_sqrt(Interval(max(F(0),rad.lo),max(F(0),rad.hi)))
    middle=shape['cx']+Interval(-shape['B']/shape['A'])*dy;result=[]
    for root in (middle-amplitude,middle+amplitude):
        left=max(lo,root.lo);right=min(hi,root.hi)
        if left<=right:result.append((left,right))
    return result


def _primitive(shape,x,guard,deadline):
    u=Interval(x-shape['cx'])/shape['rx']
    # Inner extent construction proves the true u is in[-1,1]. Intersecting
    # the interval with that proven domain improves only an existing enclosure.
    u=Interval(max(F(-1),u.lo),min(F(1),u.hi))
    rad=1-u*u;root=_sqrt(Interval(max(F(0),rad.lo),max(F(0),rad.hi)))
    return u*root+_asin(u,guard,deadline)


def _integrate_segment(shape,lo,hi,y0,y1,guard,deadline):
    if hi<=lo:return Interval(0),False
    lower,upper=_height_bounds(shape,(lo+hi)/2)
    if upper.hi<=y0 or lower.lo>=y1:return Interval(0),False
    if upper.lo>=y1:top=(Interval(y1),Interval(0),Interval(0));top_mid=Interval(y1)
    elif upper.hi<=y1:top=(Interval(shape['cy']),Interval(-shape['B']/shape['C']),_sqrt(1/Interval(shape['C'])));top_mid=upper
    else:return Interval(0,(hi-lo)*(y1-y0)),True
    if lower.hi<=y0:bottom=(Interval(y0),Interval(0),Interval(0));bottom_mid=Interval(y0)
    elif lower.lo>=y0:bottom=(Interval(shape['cy']),Interval(-shape['B']/shape['C']),-_sqrt(1/Interval(shape['C'])));bottom_mid=lower
    else:return Interval(0,(hi-lo)*(y1-y0)),True
    if top_mid.hi<=bottom_mid.lo:return Interval(0),False
    if top_mid.lo<bottom_mid.hi:return Interval(0,(hi-lo)*(y1-y0)),True
    alpha,beta,chi=(a-b for a,b in zip(top,bottom));dx0=lo-shape['cx'];dx1=hi-shape['cx']
    value=alpha*(hi-lo)+beta*((dx1*dx1-dx0*dx0)/2)
    if chi.lo!=0 or chi.hi!=0:value=value+chi*shape['rx']/2*(_primitive(shape,hi,guard,deadline)-_primitive(shape,lo,guard,deadline))
    return Interval(max(F(0),value.lo),min((hi-lo)*(y1-y0),max(F(0),value.hi))),False


def ellipse_rectangle_area(shape,rectangle_mm,guard=lambda:None,deadline=None):
    """Certified mathematical area interval in mm2, no sampled area rescaling."""
    _check(guard,deadline);rectangle=tuple(map(_f,rectangle_mm));require(len(rectangle)==4,'Rectangle[x0,x1,y0,y1]')
    x0,x1,y0,y1=rectangle;require(x0<=x1 and y0<=y1,'Ordered physical rectangle')
    full=(x1-x0)*(y1-y0)
    if full==0:return dict(interval=Interval(0),method='zero_rectangle',segments=0,ambiguous_segments=0)
    if all(_quadratic(shape,x,y,shape['b'].lo)<=1 for x in (x0,x1) for y in (y0,y1)):
        return dict(interval=Interval(full),method='whole_square_proved_inside',segments=0,ambiguous_segments=0)
    if _minimum_quadratic(shape,rectangle,shape['b'].hi)>1:
        return dict(interval=Interval(0),method='whole_square_proved_outside',segments=0,ambiguous_segments=0)
    cx=shape['cx'];rx=shape['rx'];lo=max(x0,cx-rx.lo);hi=min(x1,cx+rx.lo)
    outer_lo=max(x0,cx-rx.hi);outer_hi=min(x1,cx+rx.hi)
    unknown=max(F(0),outer_hi-outer_lo)-max(F(0),hi-lo)
    if hi<=lo:return dict(interval=Interval(0,max(F(0),outer_hi-outer_lo)*(y1-y0)),method='bounded_extent_strip',segments=0,ambiguous_segments=1)
    bands=sorted(_root_bands(shape,y0,lo,hi)+_root_bands(shape,y1,lo,hi));merged=[]
    for a,b in bands:
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:merged.append((a,b))
    segments=[];last=lo
    for a,b in merged:
        if a>last:segments.append((last,a))
        unknown+=b-a;last=max(last,b)
    if last<hi:segments.append((last,hi))
    require(len(segments)<=MAX_SEGMENTS,'Fixed maximum clipped-conic integration segments')
    area=Interval(0);ambiguous=0
    for a,b in segments:
        value,uncertain=_integrate_segment(shape,a,b,y0,y1,guard,deadline);area=area+value;ambiguous+=int(uncertain)
    # The true semiminor uses mathematical pi. It lies between nested ellipses;
    # their entire symmetric-difference area bounds the change in any cell.
    parameter_error=_pi().hi*shape['a']*(shape['b'].hi-shape['b'].lo)
    upper_extra=max(F(0),unknown)*(y1-y0)+parameter_error
    result=Interval(max(F(0),area.lo-parameter_error),min(full,area.hi+upper_extra))
    return dict(interval=result,method='analytic_conic_primitive_with_outward_interval_certificate',
                segments=len(segments),ambiguous_segments=ambiguous,
                excluded_root_extent_strip_area_bound_mm2=upper_extra)


def _perimeter(shape,guard,deadline):
    a=shape['a'];e2=1-shape['b']*shape['b']/(a*a);require(0<=e2.lo<=e2.hi<1,'Bounded ellipse perimeter series')
    power=Interval(1);total=Interval(0)
    for n in range(1,SERIES_TERMS+1):
        if n%16==0:_check(guard,deadline)
        power=power*e2;coefficient=F(math.comb(2*n,n),1<<(2*n))**2/F(2*n-1);total=total+power*coefficient
    n=SERIES_TERMS+1;coefficient=F(math.comb(2*n,n),1<<(2*n))**2/F(2*n-1)
    tail=(power*e2*coefficient)/(1-e2)
    return 2*_pi()*a*(1-total-Interval(0,tail.hi))


def _shapes(centres_mm):
    require(len(centres_mm)==4,'Exactly four original physical pad centres')
    shapes=[make_ellipse(*centre) for centre in centres_mm]
    expected=((-1,-1),(1,1),(1,-1),(-1,1))
    for shape,signs in zip(shapes,expected):
        require(tuple(1 if shape[k]>0 else -1 if shape[k]<0 else 0 for k in ('cx','cy'))==signs,
                'Preserve physical pads0/1 source and2/3 common-GND quadrants')
    return shapes


def preflight(centres_mm,guard=lambda:None,deadline=None):
    """Block on circle/quadrant failure; never resize or adjust a supplied centre."""
    rows=[]
    for pad,shape in enumerate(_shapes(centres_mm)):
        _check(guard,deadline);a=shape['a'];b=shape['b'];r2=shape['cx']**2+shape['cy']**2
        # Global unconstrained maximum of the concave quadratic in cos(t)
        # bounds the actual maximum, including endpoint cases.
        maximum2=Interval(r2+a*a)+r2*b*b/(a*a-b*b);rmax=_sqrt(maximum2)
        margin_x=abs(shape['cx'])-shape['physical_support_rx'].hi;margin_y=abs(shape['cy'])-shape['physical_support_ry'].hi
        require(rmax.hi<25 and margin_x>0 and margin_y>0,
                'Ellipse must fit strictly inside D50 and its whole original quadrant; BLOCK without resize')
        rows.append(dict(physical_pad_id=pad,analytic_centroid_mm=[float(shape['cx']),float(shape['cy'])],
            analytic_centroid_exact=[_rational(shape['cx']),_rational(shape['cy'])],
            analytic_area_mm2=225.,tangential_semimajor_mm=13.,radial_semiminor_mm=_json_interval(b),
            maximum_radius_upper_bound_mm=_float_upper(rmax.hi),
            quadrant_axis_margins_mm=[_float_lower(margin_x),_float_lower(margin_y)],
            perimeter_mm_interval=_json_interval(_perimeter(shape,guard,deadline))))
    return dict(schema='task1-centroid-tangential-ellipse-preflight-v1',passed=True,pads=rows,
                no_overlap_proof='Four whole supports lie strictly within distinct original quadrants',
                no_resize=True,no_centre_adjustment=True,physical_pads=4,independent_outputs=2,
                node_mapping=['out0','out1','GND','GND'],source_resistance_ohm_each=50.,
                analytic_area_total_mm2=900.,geometry_and_area_are_not_field_or_contact_convergence=True)


def contact_patches(centres_mm,ij,h_mm=.5,guard=lambda:None,deadline=None):
    """Return canonical pad/j/i fractional patches and rigorous area receipts."""
    _check(guard,deadline);h=_f(h_mm);require(h==F(1,2),'Unchanged .5mm XY100 graph')
    proof=preflight(centres_mm,guard,deadline);shapes=_shapes(centres_mm);nodes=set()
    for pair in ij:
        require(len(pair)==2,'Actual injected graph ij pair');i,j=(operator.index(v) for v in pair)
        require(type(pair[0])is not bool and type(pair[1])is not bool and 0<=i<100 and 0<=j<100,'Exact graph index bounds')
        x=-25+(F(i)+F(1,2))*h;y=-25+(F(j)+F(1,2))*h
        require(x*x+y*y<625 and (i,j)not in nodes,'Unique actual centre-inside-D50 graph nodes');nodes.add((i,j))
    rows=[];pad_receipts=[];candidate_cells=0;face_m2=h*h/F(1000000)
    for pad,shape in enumerate(shapes):
        xs=(shape['cx']-shape['physical_support_rx'].hi,shape['cx']+shape['physical_support_rx'].hi)
        ys=(shape['cy']-shape['physical_support_ry'].hi,shape['cy']+shape['physical_support_ry'].hi)
        imin=max(0,int((xs[0]+25)//h));imax=min(99,int((xs[1]+25)//h))
        jmin=max(0,int((ys[0]+25)//h));jmax=min(99,int((ys[1]+25)//h))
        total=Interval(0);nominal=F(0);error=F(0);moment_x=F(0);moment_y=F(0);partial=0;omitted=F(0);pad_rows=[]
        for j in range(jmin,jmax+1):
            for i in range(imin,imax+1):
                candidate_cells+=1;require(candidate_cells<=MAX_CONTACT_CANDIDATE_CELLS,'Finite prospective contact-certificate work bound')
                _check(guard,deadline);x0=-25+i*h;y0=-25+j*h
                calculation=ellipse_rectangle_area(shape,(x0,x0+h,y0,y0+h),guard,deadline);area=calculation['interval']/1000000;total=total+area
                if area.hi==0:continue
                require((i,j)in nodes,'Every potentially positive certified physical patch must map to the actual injected graph; no support trimming')
                require(area.lo>0,
                        'Unresolved potentially positive ellipse contact support: pad='+str(pad)+
                        ',i='+str(i)+',j='+str(j)+',certified_area_interval_m2='+str(_json_interval(area))+
                        '; BLOCK without omission, f_min threshold or rescale; area error cannot bound contact peaks')
                value=float((area.lo+area.hi)/2);represented=F.from_float(value)
                require(0<value<=float(face_m2)*(1+1e-12),'Finite once-rounded fractional physical area')
                cell_error=max(abs(represented-area.lo),abs(represented-area.hi));error+=cell_error;nominal+=represented
                x=x0+h/2;y=y0+h/2;moment_x+=represented*x;moment_y+=represented*y
                is_partial=calculation['method']!='whole_square_proved_inside';partial+=int(is_partial)
                row=dict(pad=pad,i=i,j=j,area_m2=value,area_interval_m2=_json_interval(area),
                         fraction_of_face=value/float(face_m2),partial_contact=is_partial,
                         absolute_area_error_bound_m2=_float_upper(cell_error),certificate_method=calculation['method'])
                pad_rows.append(row);rows.append(row)
        expected=F(225,1000000);serialized_sum=math.fsum(row['area_m2'] for row in pad_rows)
        summation_error=abs(F.from_float(serialized_sum)-nominal);error+=summation_error
        require(total.lo<=expected<=total.hi,'Exact analytic225mm2 lies within sum of certified cell intersections')
        require(nominal>0 and (abs(F.from_float(serialized_sum)-expected)+error)/expected<=F(1,10**10),
                'Certified physical area plus float export must satisfy unchanged1e-10 pad gate; BLOCK without rescale')
        node_centre=(moment_x/nominal,moment_y/nominal)
        pad_receipts.append(dict(physical_pad_id=pad,patches=len(pad_rows),partial_patch_count=partial,
            minimum_positive_fraction=min(row['fraction_of_face'] for row in pad_rows),
            analytic_area_mm2=225.,represented_float_area_m2=serialized_sum,
            certified_total_intersection_area_m2=_json_interval(total),
            summed_absolute_area_error_bound_m2=_float_upper(error),
            omitted_unresolved_area_upper_bound_m2=_float_upper(omitted),
            certified_relative_area_gate=1e-10,certified_relative_area_error_bound=_float_upper((abs(F.from_float(serialized_sum)-expected)+error)/expected),
            analytic_centroid_exact=[_rational(shape['cx']),_rational(shape['cy'])],
            analytic_centroid_mm=[float(shape['cx']),float(shape['cy'])],
            node_area_weighted_centroid_mm=[float(v) for v in node_centre],
            node_minus_analytic_centroid_mm=[float(node_centre[0]-shape['cx']),float(node_centre[1]-shape['cy'])],
            node_centroid_is_not_analytic_area_centroid=True,
            first_moment_integration='Not run; analytic centroid follows exact ellipse symmetry, lumped-node centroid is separately reported'))
    receipt=dict(schema='task1-certified-centroid-ellipse-contact-v1',passed=True,preflight=proof,pads=pad_receipts,
        physical_pads=4,independent_outputs=2,physical_area_total_mm2=900.,h_mm=.5,
        canonical_patch_order='pad ascending, then j ascending, then i ascending',candidate_cells_examined=candidate_cells,
        certificate=dict(method='Analytic clipped-conic primitive with exact Fraction interval arithmetic',
            directed_dyadic_precision_bits=BITS,atan_and_perimeter_series_terms=SERIES_TERMS,
            maximum_segments_per_cell=MAX_SEGMENTS,maximum_candidate_cells=MAX_CONTACT_CANDIDATE_CELLS,
            sqrt='Exact integer-isqrt lower/upper brackets',trigonometry='Bounded alternating atan series and exact range identities; no libm trig calls',
            root_and_extent_uncertainty='Excluded strips charged by full cell height times certified strip width',
            pi='Fixed known decimal truncation plus one last-decimal unit',
            float_export='Each area rounded once; exact Fraction.from_float comparison and summed rounding bounds',
            two_resolution_difference_used_as_certificate=False),
        actual_graph_hash_identity_must_be_authenticated_by_caller=True,
        injected_graph_coordinates_and_all_potential_positive_patch_coverage_checked=True,
        actual_graph_hash_identity_authenticated_here=False,area_rescaled=False,forced_contact_cell_count=False,
        unresolved_potential_positive_support_omitted=False,
        analytic_centres_adjusted=False,physical_first_moments_numerically_integrated=False,
        partial_contact_model_uncertainty_preserved=True,full_convergence_or_adoption=False)
    return dict(patches=rows,receipt=receipt)
