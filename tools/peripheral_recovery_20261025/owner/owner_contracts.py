"""Pure recovery accounting boundary; no input reads, geometry or arrays."""
def validate_recovery_summary(summary):
 expected=dict(completed_conditions=4,actual_new_driven_RHS=2,actual_reused_saved_RHS=2,
  actual_new_metric_evaluations=2,actual_alias_conditions=2,new_P23_RHS=0,new_P12_RHS=2,new_eigen_solves=0)
 if summary.get('status')!='peripheral_recovery_computed_without_P23_PDE_repeat':raise ValueError('Exact memory-separated recovery result status required')
 for key,value in expected.items():
  if type(summary.get(key))is not int or summary[key]!=value:raise ValueError('Exact recovery counter '+key)
 if [row['candidate_id']for row in summary.get('recipe_blockers',[])]!=['P24-peripheral-polyomino225']:raise ValueError('Original P24 geometry blocker must remain preserved')
 return dict(passed=True,**expected)
