"""Pure accounting for one explicitly hypothetical floating-P23 comparison."""
FLOATING='P23p5-peripheral-polyomino225__hypothetical-floating-pairs02-13'

def require(ok,message):
 if not ok:raise ValueError(message)
def validate_summary(s):
 require(s.get('status')=='hypothetical_floating_P23_comparison_computed_unadopted','Exact complete hypothetical-field status')
 for key,value in dict(actual_new_driven_RHS=2,actual_new_metric_evaluations=1,immutable_common_control_aliases=2,completed_conditions=3,new_common_return_RHS=0,new_B0_RHS=0,new_eigen_solves=0).items():require(type(s.get(key))is int and s[key]==value,'Exact prospective work count '+key)
 require(s.get('actual_hardware_wiring_claimed')is False and s.get('physical_mask_changed')is False and s.get('candidate_adopted')is False and s.get('common_return_and_hypothetical_floating_separately_named')is True,'Hypothesis only, no default hardware/geometry change or adoption')
 require(s['spec']['physical_pairs']==[[0,2],[1,3]]and s['spec']['frequency_output_assignment']==[[2000,0],[2010,1]],'Preserve physical source frequency assignment and explicit independent pairs')
 rows=s['candidates'];require(len(rows)==3 and rows[-1]['candidate_id']==FLOATING,'Two common controls and one distinct hypothetical condition')
 for row in rows[:2]:require(row['actual_new_RHS']==0 and row['actual_new_metric_evaluations']==0 and row['no_field_reconstruction']is True and row['no_angular_recalculation']is True,'Cached common-return controls are never repeated')
 new=rows[-1];require(new['actual_new_RHS']==2 and new['actual_new_metric_evaluations']==1 and new['Q_or_profiles_or_solver_resident_during_metrics']is False and new['actual_hardware_wiring_claimed']is False,'Two physical RHS, one post-Q metric evaluation')
 require(len(new['source_physics_proofs'])==2,'Actual two frequency-specific physics proofs')
 for p,output in zip(new['source_physics_proofs'],(0,1)):
  require(p['passed']is True and p['pair_pad_indices']==[[0,2],[1,3]]and p['driven_output']==output and p['source_output_order_preserved']is True,'Physical paired source proofs must pass unchanged gates')
 return dict(passed=True,new_floating_RHS=2,new_angular_metrics=1,common_control_aliases=2,new_common_return_RHS=0,new_eigen_solves=0,actual_hardware_wiring_changed=False)
