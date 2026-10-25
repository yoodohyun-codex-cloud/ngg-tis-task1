"""Pure completeness accounting for cached consolidation; no scientific reads."""
def validate_consolidation_summary(summary):
 expected=dict(canonical_native_geometries=15,new_PDE_RHS=0,actual_new_angular_evaluations=0)
 if summary.get('status')!='fifteen_native_geometries_cached_gui_probe_analysis_complete':raise ValueError('Complete cached-consolidation status required')
 for key,value in expected.items():
  if type(summary.get(key))is not int or summary[key]!=value:raise ValueError('Exact cached-consolidation counter '+key)
 rows=summary.get('candidates')
 if not isinstance(rows,list)or len(rows)!=15 or len({row.get('candidate_id')for row in rows})!=15:raise ValueError('Fifteen distinct canonical native geometries required')
 probe_count=0
 for row in rows:
  probe=row.get('probe_prediction',{})
  if probe.get('status')!='calculated_unloaded_only' or type(probe.get('probe_count'))is not int or probe['probe_count']!=40 or len(probe.get('probes',[]))!=40:raise ValueError('Forty complete unloaded probes per native geometry required')
  if row.get('candidate_adopted')is not False:raise ValueError('Cached comparison cannot adopt a candidate')
  probe_count+=probe['probe_count']
 ids={row['candidate_id']for row in rows}
 top=summary.get('provisional_top5')
 if not isinstance(top,list)or len(top)!=5 or len(set(top))!=5 or not set(top).issubset(ids):raise ValueError('Five distinct provisional native candidates required')
 if summary.get('baseline_id')not in ids or not set(summary.get('mandatory_compare_ids',[])).issubset(ids):raise ValueError('Baseline and mandatory native pad-count references required')
 for row in summary.get('reported_local_candidates',[]):
  if row.get('eligible_for_native_ranking')is not False:raise ValueError('Unverified local reported data cannot enter the native ranking')
 if summary.get('candidate_adopted')is not False or summary.get('no_original_phi_E_or_scalar_overwrite')is not True:raise ValueError('Preserve originals and withhold candidate adoption')
 return dict(passed=True,**expected,unloaded_probe_count=probe_count,probes_per_geometry=40)
