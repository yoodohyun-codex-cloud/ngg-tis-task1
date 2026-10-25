"""Pure mixed-design accounting boundary; no input reads, geometry or arrays."""
def validate_mixed_summary(summary):
 expected=dict(completed_conditions=4,actual_new_driven_RHS=4,actual_new_metric_evaluations=2,actual_alias_conditions=2,new_eigen_solves=0)
 if summary.get('status')!='mixed_fourpad_screen_computed_unadopted':raise ValueError('Exact mixed-design result status required')
 for key,value in expected.items():
  if type(summary.get(key))is not int or summary[key]!=value:raise ValueError('Exact mixed-design counter '+key)
 return dict(passed=True,**expected)
