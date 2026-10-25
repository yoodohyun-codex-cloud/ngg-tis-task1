"""Independent cached single-pair GUI completeness and topology accounting."""
import math
BASELINE='P23p5-peripheral-polyomino225'
PAIRS=('single-pair-square15-c12.5-y0','single-pair-square15-c15-y0')
MODES=('fixed_1Vpp','same_centre20mm_vector_RMS','same_target_volume_RMS')
def req(ok,message):
 if not ok:raise ValueError(message)
def positive(value):return type(value)in(int,float)and math.isfinite(value)and value>0
def same(actual,expected):
 return positive(actual)and positive(expected)and abs(actual-expected)<=1e-10+2e-7*abs(expected)
def validate_pair_gui_summary(summary):
 req(summary.get('status')=='cached_three_geometry_single_pair_GUI_prepared_unadopted','Actual complete cached companion-GUI status required')
 for key in('new_PDE_RHS','new_angular_evaluations'):req(type(summary.get(key))is int and summary[key]==0,'Exactly zero new PDE/angular work')
 for key in('Q_loaded','originals_overwritten','browser_validation_performed','candidate_adopted'):req(summary.get(key)is False,'No Q/overwrite/browser/adoption claims '+key)
 rows=summary.get('candidates');req(isinstance(rows,list)and tuple(r.get('candidate_id')for r in rows)==(BASELINE,)+PAIRS,'Actual P23 and two distinct corrected y0 single-pair geometries')
 req(summary.get('baseline_id')==BASELINE and tuple(summary.get('comparison_modes',()))==MODES,'Three separate fixedV/centreRMS/ROI-RMS comparisons')
 baseline=rows[0];ref=baseline['modes']['fixed_1Vpp'];matched=0
 for i,row in enumerate(rows):
  tis=i==0;req(row.get('is_TIS')is tis and row.get('physical_pads')==(4 if tis else 2)and row.get('independent_outputs')==(2 if tis else 1),'Physical pads versus connected output topology')
  req(row.get('contact_area_mm2')==(900. if tis else 450.)and row.get('frequencies_Hz')==([2000,2010]if tis else[2000]),'Actual areas and carrier counts, no extra single output')
  req(row.get('candidate_adopted')is False and tuple(row.get('modes',{}))==MODES,'Every geometry retains all three modes without adoption')
  proofs=row.get('regression_proofs');req(isinstance(proofs,list)and proofs and all(p.get('passed')is True for p in proofs),'Actual raw versus saved metric regression checks')
  fixed=row['modes']['fixed_1Vpp'];req(same(fixed['amplitude_scale'],1.)and same(fixed['required_source_high_impedance_Vpp'],1.),'Original fixed1Vpp data remains available')
  for name,mode in row['modes'].items():
   a=mode.get('amplitude_scale');req(positive(a)and same(mode.get('required_source_high_impedance_Vpp'),a),'Positive linear source-Vpp resynthesis at fixed1Vpp baseline')
   req(same(mode.get('centre_vector_RMS_V_m'),row['centre_vector_RMS_V_m']*a)and same(mode.get('target_volume_RMS_V_m'),row['target_volume_RMS_V_m']*a),'Distinct raw centre/ROI RMS scale consistently')
  if tis:continue
  req(row.get('single_carrier_10Hz_envelope_AM_V_m')==0.,'Single-frequency RMS cannot become two-tone10Hz AM')
  original=row.get('saved_single_pair_comparison',{});geometry=original.get('geometry',{});pads=geometry.get('pads',[])
  req(geometry.get('physical_pads')==2 and geometry.get('connected_sources')==1 and len(pads)==2 and all(p.get('center_mm',[None,None])[1]==0. for p in pads),'Corrected physical two-electrode geometry at y0 including return')
  req(same(row['modes'][MODES[1]]['centre_vector_RMS_V_m'],ref['centre_vector_RMS_V_m']),'Physical-centre20mm vector RMS matching criterion')
  req(same(row['modes'][MODES[2]]['target_volume_RMS_V_m'],ref['target_volume_RMS_V_m']),'Target-volume second-moment RMS matching criterion')
  matched+=2
 req(summary.get('grid_binding',{}).get('original_weights_changed')is False,'Original physical fractional ROI weights remain unchanged')
 return dict(passed=True,comparison_geometries=3,single_pair_geometries=2,distinct_matching_criteria=2,separate_single_pair_matches=matched,new_PDE_RHS=0,new_angular_evaluations=0,browser_validation_performed=False,candidate_adopted=False)
