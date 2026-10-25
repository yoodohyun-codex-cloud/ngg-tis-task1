"""Pure physical contact-panel comparison; NumPy is supplied by the finite owner.

Import performs no IO, NumPy import, array construction or numerical work.
The fixed contact spans -0.0005 to +0.0005 metres. Inputs are piecewise-constant
complex PEAK normal current densities, not temporal RMS values. Quantities
integrated along this 2D contact are explicitly per unit out-of-plane width.
"""

CONTACT_LEFT_M=-.0005
CONTACT_RIGHT_M=.0005
ENDPOINT_TOLERANCE_M=1e-15
COVERAGE_TOLERANCE_M=1e-15
DENOMINATOR_FLOOR=1e-300


def _require(condition,message):
    if not condition:raise ValueError(message)


def _complex(value):
    value=complex(value)
    return dict(real=float(value.real),imaginary=float(value.imag))


def _partition(edges,q,np):
    edges=np.asarray(edges,dtype=float);q=np.asarray(q,dtype=complex)
    _require(edges.ndim==q.ndim==1 and len(edges)==len(q)+1 and len(q)>0 and
             np.isfinite(edges).all()and np.isfinite(q).all()and np.all(np.diff(edges)>0),
             'Finite increasing edges and one finite complex q per positive-width panel required')
    _require(abs(float(edges[0])-CONTACT_LEFT_M)<=ENDPOINT_TOLERANCE_M and
             abs(float(edges[-1])-CONTACT_RIGHT_M)<=ENDPOINT_TOLERANCE_M,
             'Both partitions must cover the entire fixed [-0.0005,+0.0005] m contact')
    # Endpoints within the declared input tolerance are snapped only to the
    # preregistered physical contact, never to the other partition's indices.
    edges=edges.copy();edges[0]=CONTACT_LEFT_M;edges[-1]=CONTACT_RIGHT_M
    _require(np.all(np.diff(edges)>0),'Endpoint canonicalization must retain positive panel widths')
    return edges,q,np.diff(edges)


def _weighted_quantile_magnitude(q,length,p,np):
    magnitude=np.abs(q);order=np.argsort(magnitude,kind='stable')
    cumulative=np.cumsum(length[order]);target=float(p*np.sum(length))
    index=min(int(np.searchsorted(cumulative,target,side='left')),len(order)-1)
    return float(magnitude[order[index]])


def _field_stats(q,length,zA,np):
    contact_length=float(np.sum(length));absolute_squared=np.abs(q)**2
    integral=float(np.sum(length*absolute_squared))
    _require(np.isfinite(integral),'Current-density squared integral must be finite')
    spatial_rms=float(np.sqrt(integral/contact_length));root_two=2.**.5
    integral_q=np.sum(length*q);nonconjugate=np.sum(length*q*q)
    power=.5*zA*integral
    j95=_weighted_quantile_magnitude(q,length,.95,np);panelmax=float(np.max(np.abs(q)))
    return dict(panel_count=len(q),contact_length_m=contact_length,
                spatial_complex_peak_RMS_A_m2=spatial_rms,
                spatial_temporal_RMS_A_m2=spatial_rms/root_two,
                length_weighted_J95_peak_A_m2=j95,length_weighted_J95_temporal_RMS_A_m2=j95/root_two,
                panel_max_peak_A_m2=panelmax,panel_max_temporal_RMS_A_m2=panelmax/root_two,
                integral_abs_q_squared_A2_m3=integral,
                integral_q_squared_NONCONJUGATE_A2_m3=_complex(nonconjugate),
                integral_q_peak_A_per_m=_complex(integral_q),
                complex_contact_power_per_width_VA_per_m=_complex(power),
                active_contact_power_per_width_W_per_m=float(power.real),
                reactive_contact_power_per_width_var_per_m=float(power.imag))


def compare(edges_a,q_a,edges_b,q_b,zA,np,guard=lambda:None):
    """Return {summary: JSON-safe scalar norms, arrays: physical overlap arrays}.

    Primary L2 integrates |qA-qB|^2 on exact physical interval intersections;
    averaging B onto A is secondary and may hide variation. The common relative
    denominator is max(spatial complex peak RMS qA, RMS qB, 1e-300 A/m^2).
    zA is one finite passive contact area impedance in ohm*m^2. Complex contact
    power per unit width is 0.5*zA*integral(|q|^2 dl); q^2 without conjugation is
    disclosed separately and is never used in norms or contact power.
    """
    guard();a,qa,wa=_partition(edges_a,q_a,np);b,qb,wb=_partition(edges_b,q_b,np)
    zA=complex(zA)
    _require(np.isfinite(zA)and zA.real>=0,'Finite passive scalar contact zA in ohm*m2 required')
    ai=[];bi=[];left=[];right=[];length=[];i=j=0
    while i<len(qa)and j<len(qb):
        if (i+j)%128==0:guard()
        lo=max(float(a[i]),float(b[j]));hi=min(float(a[i+1]),float(b[j+1]))
        if hi>lo:
            ai.append(i);bi.append(j);left.append(lo);right.append(hi);length.append(hi-lo)
        ar=float(a[i+1]);br=float(b[j+1])
        if ar<=br:i+=1
        if br<=ar:j+=1
    guard();ai=np.asarray(ai,dtype=np.int64);bi=np.asarray(bi,dtype=np.int64)
    length=np.asarray(length,dtype=float);left=np.asarray(left,float);right=np.asarray(right,float)
    coverage_a=np.bincount(ai,weights=length,minlength=len(qa))
    coverage_b=np.bincount(bi,weights=length,minlength=len(qb))
    contact_length=CONTACT_RIGHT_M-CONTACT_LEFT_M
    _require(len(length)>0 and abs(float(np.sum(length))-contact_length)<=COVERAGE_TOLERANCE_M and
             np.all(abs(coverage_a-wa)<=COVERAGE_TOLERANCE_M)and
             np.all(abs(coverage_b-wb)<=COVERAGE_TOLERANCE_M),
             'Physical overlap must cover every old/new panel and the full contact')
    difference=qa[ai]-qb[bi]
    integral_difference=float(np.sum(length*np.abs(difference)**2))
    _require(np.isfinite(integral_difference),'Difference squared integral must be finite')
    primary_squared=integral_difference/contact_length
    fine_integral=np.bincount(ai,weights=length*qb[bi].real,minlength=len(qa))+1j*np.bincount(ai,weights=length*qb[bi].imag,minlength=len(qa))
    qb_average_on_a=fine_integral/coverage_a
    secondary_squared=float(np.sum(coverage_a*np.abs(qa-qb_average_on_a)**2)/contact_length)
    within_a_squared=float(np.sum(length*np.abs(qb[bi]-qb_average_on_a[ai])**2)/contact_length)
    stats_a=_field_stats(qa,wa,zA,np);stats_b=_field_stats(qb,wb,zA,np)
    rms_a=stats_a['spatial_complex_peak_RMS_A_m2'];rms_b=stats_b['spatial_complex_peak_RMS_A_m2']
    denominator=max(rms_a,rms_b,DENOMINATOR_FLOOR);primary=float(np.sqrt(primary_squared))
    secondary=float(np.sqrt(secondary_squared));root_two=2.**.5
    delta_integral=stats_b['integral_abs_q_squared_A2_m3']-stats_a['integral_abs_q_squared_A2_m3']
    delta_power=.5*zA*delta_integral
    summary=dict(schema='task1-contact-physical-panel-overlap-v1',status='diagnostic_not_gated',
                 contact_bounds_m=[CONTACT_LEFT_M,CONTACT_RIGHT_M],contact_length_m=contact_length,
                 overlap_length_m=float(np.sum(length)),overlap_links=len(length),
                 endpoint_tolerance_m=ENDPOINT_TOLERANCE_M,coverage_tolerance_m=COVERAGE_TOLERANCE_M,
                 endpoint_policy='Validate both physical endpoints, then canonicalize them to the fixed contact within tolerance',
                 a=stats_a,b=stats_b,contact_zA_ohm_m2=_complex(zA),
                 denominator_A_m2=denominator,denominator_floor_A_m2=DENOMINATOR_FLOOR,
                 denominator_floor_used=max(rms_a,rms_b)<DENOMINATOR_FLOOR,
                 primary_pairwise=dict(absolute_spatial_peak_L2_A_m2=primary,
                     absolute_temporal_RMS_difference_A_m2=primary/root_two,
                     normalized_L2=primary/denominator,integral_abs_difference_squared_A2_m3=integral_difference),
                 secondary_B_averaged_on_A=dict(absolute_spatial_peak_L2_A_m2=secondary,
                     absolute_temporal_RMS_difference_A_m2=secondary/root_two,
                     normalized_L2=secondary/denominator,
                     covered_fraction_A_min=float(np.min(coverage_a/wa)),covered_fraction_A_max=float(np.max(coverage_a/wa)),
                     covered_fraction_B_min=float(np.min(coverage_b/wb)),covered_fraction_B_max=float(np.max(coverage_b/wb))),
                 within_A_B_variation_squared_A2_m4=within_a_squared,
                 projection_Pythagorean_closure_A2_m4=primary_squared-secondary_squared-within_a_squared,
                 B_minus_A_integral_abs_q_squared_A2_m3=delta_integral,
                 B_minus_A_complex_contact_power_per_width_VA_per_m=_complex(delta_power),
                 B_minus_A_active_contact_power_per_width_W_per_m=float(delta_power.real),
                 quantile_definition='Length-weighted empirical magnitude quantile: smallest value whose cumulative contact length reaches 95%; no interpolation',
                 power_definition='Peak phasors: complex S per unit out-of-plane width =0.5*zA*integral(abs(q)^2 dl); active power=real(S)',
                 current_definition='Caller-supplied complex peak normal current density; temporal RMS magnitudes divide by sqrt(2)',
                 projection_warning='Averaging can hide panel-scale variation; physical pairwise comparison is primary',
                 automatic_gate_applied=False)
    # Stable compact owner ABI; descriptive keys above retain explicit units.
    summary['primary']=dict(relative_L2=primary/denominator,
                            absolute_spatial_peak_L2_A_m2=primary,
                            absolute_temporal_RMS_difference_A_m2=primary/root_two,
                            integral_abs_difference_squared_A2_m3=integral_difference)
    summary['secondary']=dict(relative_L2=secondary/denominator,
                              absolute_spatial_peak_L2_A_m2=secondary,
                              absolute_temporal_RMS_difference_A_m2=secondary/root_two,
                              definition='B length-averaged onto covered old panels; secondary only')
    arrays=dict(old_idx=ai,new_idx=bi,length=length,length_m=length,left_m=left,right_m=right,
                old_coverage_length_m=coverage_a,new_coverage_length_m=coverage_b,
                old_covered_fraction=coverage_a/wa,new_covered_fraction=coverage_b/wb,
                B_averaged_on_A=qb_average_on_a,complex_pairwise_difference_peak_A_m2=difference)
    return dict(summary=summary,arrays=arrays)
