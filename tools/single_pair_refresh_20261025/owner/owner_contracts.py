"""Pure single-pair accounting boundary; no input reads or numerical work."""
import math
IDS=('single-pair-square15-c12.5-y0','single-pair-square15-c15-y0')
MATCHES=('same_centre20mm_vector_RMS','same_target_volume_RMS')
def require(ok,message):
 if not ok:raise ValueError(message)
def validate_single_pair_summary(summary):
 require(summary.get('status')=='calculated_provisional_single_pair_comparison_unadopted','Exact completed single-pair model status')
 require(type(summary.get('actual_new_driven_RHS'))is int and summary['actual_new_driven_RHS']==2 and type(summary.get('new_eigen_solves'))is int and summary['new_eigen_solves']==0,'Exactly two new physical RHS, no eigen work')
 require(summary.get('existing_PDE_repeated')is False and summary.get('TIS_angular_computation_performed')is False and summary.get('Q_resident_during_metrics')is False and summary.get('candidate_adopted')is False,'No oldPDE/angular repeat/Q-resident metrics/adoption')
 require(summary.get('selected_TIS_reference',{}).get('candidate_id')=='P23p5-peripheral-polyomino225','Actual selected provisional P23 reference only')
 rows=summary.get('candidates',[]);require(tuple(r['candidate_id']for r in rows)==IDS,'Exactly two prospectively declared centred-y0 geometries')
 for row in rows:
  g=row['geometry'];require(g['physical_pads']==2 and g['connected_sources']==1 and len(g['pads'])==2 and all(p['center_mm'][1]==0 for p in g['pads']),'Two physical pads/one connected output centredy0')
  require(type(row.get('actual_new_driven_RHS'))is int and row['actual_new_driven_RHS']==1,'One new single-carrier RHS per geometry')
  proof=row['source_physics_proof'];topology=proof['physical_topology'];require(proof['passed']is True and topology['passed']is True and topology['connected_sources']==1 and topology['no_logical1_or3_contact_patches']is True,'Unchanged physical gates and unattacheddummy topology must pass')
  require(row.get('single_carrier_envelope_AM_10Hz_V_m')==0 and row.get('carrier_RMS_is_not_TIS_modulation')is True,'Single-frequency RMS is never TIS modulation')
  matches=row['separate_RMS_matches_to_selected_TIS'];require(tuple(matches)==MATCHES,'Distinct centre and volume RMS matching conditions')
  for result in matches.values():
   v=result['required_source_high_impedance_Vpp'];require(type(v)in(int,float)and math.isfinite(v)and v>0 and result['equal_RMS_does_not_imply_equal_TIS_modulation_or_activation']is True,'Positive independently matched Vpp and no activation equivalence claim')
 boundaries=summary.get('Q_release_boundaries',[]);require(tuple(r['candidate_id']for r in boundaries)==IDS and all(r['raw_frame_returned']is True and r['Q_passed_to_metrics']is False for r in boundaries),'Both raw frames exited before metrics')
 return dict(passed=True,completed_conditions=2,actual_new_driven_RHS=2,physical_pads_per_condition=2,connected_sources_per_condition=1,new_eigen_solves=0,new_angular_evaluations=0,GUI_generated=False)
