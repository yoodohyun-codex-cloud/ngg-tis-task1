"""Pure prospective READY-subset accounting; no I/O, imports or geometry work."""
IDS=('B0-square15-c10-diagonal','G1-square12-c10-diagonal','P24-peripheral-polyomino225','P23p5-peripheral-polyomino225','P12-square-c11p5-diagonal')
def prepared_counts(catalog):
 rows=catalog['candidates']
 if tuple(row['candidate_id']for row in rows)!=IDS:raise ValueError('Exact five requested cases required')
 for row in rows[:2]:
  if row['status']=='recipe_blocked'or row.get('reuse_first8_case_id')!=row['candidate_id']:raise ValueError('Both exact original control aliases are required')
 ready=[];blocked=[]
 for row in rows[2:]:
  if row['status']=='recipe_blocked':
   if not row.get('blocker')or row.get('mask_path')is not None:raise ValueError('Blocked recipe needs preserved reason and absent mask')
   blocked.append(dict(candidate_id=row['candidate_id'],blocker=row['blocker']))
  else:
   if row['status']!='source_recipe_geometry_ready_root_selection_pending':raise ValueError('Only explicitly ready new recipes may be selected')
   if row.get('reuse_first8_case_id')is not None or not row.get('mask_path')or not row.get('mask_sha256'):raise ValueError('Ready new geometry needs a frozen mask and no control alias')
   ready.append(row['candidate_id'])
 n=len(ready)
 return dict(schema='task1-peripheral-prospective-ready-subset-v1',requested_conditions=5,maximum_new_driven_RHS=6,
  ready_new_candidate_ids=ready,recipe_blockers=blocked,ready_new_geometries=n,expected_completed_conditions=2+n,
  expected_new_driven_RHS=2*n,expected_new_metric_evaluations=n,expected_control_alias_conditions=2,
  selected_before_source_publication=True,force_blocked_shape=False,permits_new_PDE=n>0)
