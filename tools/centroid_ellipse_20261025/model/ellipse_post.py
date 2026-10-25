"""One new two-carrier metric case plus two immutable published aliases.

No I/O, scientific imports, arrays or work on import. Root calls after the raw
Q frame returned JSON metadata and GC completed. No control field/angular work.
"""
import copy,gc,json,math,time
from pathlib import Path
import ellipse_electrical
import screen_metrics
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
SCALARS=('AM_max2074','carrier_RMS','Jtotal_vector_RMS','AM_direction_index')
def require(ok,message):
 if not ok:raise ValueError(message)
def check(guard,deadline):
 guard()
 if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite ellipse metric stage deadline')
def new(path,value):
 with Path(path).open('xb')as stream:stream.write((json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode())
def vector4(normalized):
 fields=normalized['absolute_ROI_fields_V_m'];t=fields['target']['maxTIS'];s=fields['surface_0_5']['maxTIS'];o=fields['off_target']['maxTIS']
 return dict(target_mean=float(t['mean']),target_P10=float(t['p10']),target_to_surface_mean=float(t['mean'])/float(s['mean'])if s['mean']>0 else None,target_to_offtarget_mean=float(t['mean'])/float(o['mean'])if o['mean']>0 else None)
def score(value,baseline):
 ratios={key:value[key]/baseline[key]if value[key]is not None and baseline[key]is not None and baseline[key]>0 else None for key in baseline}
 losses={key:bool(value[key]<baseline[key])for key in('target_mean','target_P10')}
 return dict(objectives=value,four_ratios_to_B0=ratios,robust_minimum_four_ratio=min(ratios.values())if all(v is not None for v in ratios.values())else None,absolute_target_losses=losses,ratio_only_improvement_with_absolute_loss=bool(any(losses.values())and any(value[k]is not None and baseline[k]is not None and value[k]>baseline[k]for k in('target_to_surface_mean','target_to_offtarget_mean'))))
def pareto(vectors):
 result={}
 for ident,value in vectors.items():
  if any(v is None for v in value.values()):result[ident]=dict(status='not_ranked_missing_objective');continue
  dominated=[]
  for other,alternative in vectors.items():
   if other==ident or any(v is None for v in alternative.values()):continue
   if all(alternative[k]>=value[k]for k in value)and any(alternative[k]>value[k]for k in value):dominated.append(other)
  result[ident]=dict(status='provisional_nondominated'if not dominated else'provisional_dominated',dominated_by=dominated,scope='Strict scalar four-objective comparison; numerical/contact uncertainty is unresolved, not candidate adoption')
 return result
def high_volume(np,values,weights,cutoff):
 use=(weights>0)&(values>=cutoff);total=float(weights.sum());volume=float(weights[use].sum())
 return dict(cutoff_V_m=float(cutoff),volume_m3=volume,volume_fraction=volume/total if total>0 else None,cutoff_scope='Original B0-relative numerical diagnostic fixed before this candidate PDE; not physiological activation/safety',native_positive_weight_cells=int(use.sum()))
def partial_contact_diagnostics(np,grid,raws):
 areas=raws[0]['contact_area_m2'];pads=raws[0]['contact_pad'];cells=raws[0]['contact_xy_index'];fractions=areas/(.0005**2)
 j=np.sqrt((abs(raws[0]['contact_normal_J_peak_A_m2'])**2+abs(raws[1]['contact_normal_J_peak_A_m2'])**2)/2.);v=np.sqrt((abs(raws[0]['contact_drop_peak_V'])**2+abs(raws[1]['contact_drop_peak_V'])**2)/2.)
 def site(index):
  return dict(contact_row=int(index),physical_pad=int(pads[index]),surface_xy_mm=[float(x)for x in grid[int(cells[index]),:2]],physical_depth_mm=0.,actual_area_m2=float(areas[index]),fraction_of_full_surface_face=float(fractions[index]),contact_normal_J_RMS_A_m2=float(j[index]),contact_drop_RMS_V=float(v[index]),is_partial_cell_with_float_tolerance=bool(fractions[index]<1.-1e-12))
 perpad=[]
 for pad in range(4):
  use=np.flatnonzero(pads==pad);jmax=int(use[np.argmax(j[use])]);vmax=int(use[np.argmax(v[use])]);perpad.append(dict(physical_pad=pad,minimum_positive_fraction=float(fractions[use].min()),partial_cell_count=int(np.sum(fractions[use]<1.-1e-12)),contact_rows=len(use),Jmax_site=site(jmax),contact_voltage_max_site=site(vmax)))
 return dict(schema='task1-fractional-contact-peak-diagnostic-v1',minimum_positive_fraction=float(fractions.min()),partial_cell_count=int(np.sum(fractions<1.-1e-12)),maximum_J_RMS_site=site(int(np.argmax(j))),maximum_contact_voltage_RMS_site=site(int(np.argmax(v))),pads=perpad,partial_classification_float_tolerance=1e-12,source_of_fractions='Actual certified physical patch area divided by unchanged .5mm-square face area; no pruning or renormalization',contact_model='Each physical partial patch uses its containing surface-node potential; unresolved subcell edge variation remains held',no_correction_factor_applied=True,minimum_fraction_used_as_cutoff=False,Jmax_is_not_bounded_by_area_sum_error=True,physiological_or_safety_inference=False)
def build(np,spec,raw,guard,deadline,out):
 import ellipse_screen as model
 context=spec['inputs'];out=Path(out);check(guard,deadline)
 require(raw['new_RHS']==2 and set(raw['raw_by_frequency'])=={'2000','2010'},'Exactly two actual new ellipse RHS, no control repetition')
 keys=['grid']+[name+'_volume_weight_m3'for name in REGIONS];common=model.load(np,context['common_grid_ROI'],keys,context['input_sha256'],guard,deadline);grid=common['grid'];require(grid.shape==(793860,5),'Exact unchanged coarse101/XY100 common native grid');weights={name:common[name+'_volume_weight_m3']for name in REGIONS};rows=[];proofs=[]
 rawkeys=['E_peak_V_m','contact_normal_J_peak_A_m2','contact_drop_peak_V','contact_pad','contact_xy_index','contact_area_m2','source_current_peak_A','metal_peak_V','layer_complex_power_W']
 for frequency in('2000','2010'):
  entry=raw['raw_by_frequency'][frequency];proof=entry['proof'];require(proof['passed']is True and proof['physical_gates']['passed']is True and proof['actual_new_RHS']==1 and proof['frequency_Hz']==int(frequency),'Fresh unrelaxed source/circuit proof per actual carrier')
  pins={entry['raw']['path']:entry['raw']['SHA256']};data=model.load(np,entry['raw'],rawkeys,pins,guard,deadline);require(data['E_peak_V_m'].shape==(len(grid),3),'Same complex peak E field ordering');rows.append(data);proofs.append(proof)
 electrical,spectral=ellipse_electrical.synthesize(np,rows,proofs);contact_diagnostics=partial_contact_diagnostics(np,grid,rows);new(out/'fractional-contact-peak-diagnostic.json',contact_diagnostics);gamma=[np.asarray([model.cv(v)for v in context['catalog']['gamma_by_frequency'][f]])for f in('2000','2010')]
 metric=screen_metrics.evaluate(np,grid,weights,rows[0]['E_peak_V_m'],rows[1]['E_peak_V_m'],gamma[0],gamma[1],electrical,guard,deadline);del rows;gc.collect()
 baseline=context['controls']['B0']['record'];normalizations=screen_metrics.normalize(metric['summary'],baseline['metrics']);require(normalizations['status']=='complete','Four separate original-B0 normalizations available')
 scalar=model.archive(np,out/(spec['candidate_id']+'-scalars.npz'),**{key:metric['arrays'][key]for key in SCALARS});cutoffs=spec['diagnostic_cutoffs'];high={mode:{cutoff['cutoff_id']:{region:high_volume(np,metric['arrays']['AM_max2074']*normalizations['comparisons'][mode]['amplitude_scale'],weights[region],cutoff['value_V_m'])for region in('total','target','surface_0_5','off_target')}for cutoff in cutoffs}for mode in MODES}
 record=dict(candidate_id=spec['candidate_id'],geometry=dict(definition=spec['geometry'],preflight_and_contact=raw['geometry_receipt'],centroid_source=raw['centroid_proof'],physical_pad_count=4,independent_outputs=2,body_changed=False),metrics=metric['summary'],normalizations=normalizations,source_physics_proofs=proofs,per_frequency_signed_circuit=spectral,fractional_contact_diagnostics=contact_diagnostics,scalar_arrays=scalar,scalar_saved_names=list(SCALARS),raw_by_frequency=raw['raw_by_frequency'],high_modulation_volumes=high,provisional_field_version=spec['field_version'],candidate_adopted=False,control_alias=False)
 records=[]
 for name in('B0','P23'):
  control=context['controls'][name];alias=copy.deepcopy(control['record']);alias.update(control_alias=True,alias_source_scalar=control['scalar'],alias_source_raw_by_frequency=control['raw_by_frequency'],alias_provenance=control['provenance'],new_PDE_RHS=0,new_angular_metric_evaluations=0,candidate_adopted=False);records.append(alias);new(out/(alias['candidate_id']+'-immutable-control-alias.json'),dict(candidate_id=alias['candidate_id'],scalar=control['scalar'],raw_by_frequency=control['raw_by_frequency'],source_provenance=control['provenance'],no_control_field_or_angular_recalculation=True))
 records.append(record);scores={};paretos={}
 for mode in MODES:
  basevector=vector4(baseline['normalizations']['comparisons'][mode]);vectors={row['candidate_id']:vector4(row['normalizations']['comparisons'][mode])for row in records};scores[mode]={ident:score(v,basevector)for ident,v in vectors.items()};paretos[mode]=pareto(vectors)
 for row in records:row['provisional_four_objective_scores']={mode:scores[mode][row['candidate_id']]for mode in MODES};row['provisional_pareto']={mode:paretos[mode][row['candidate_id']]for mode in MODES}
 new(out/(spec['candidate_id']+'-summary.json'),record);new(out/'four-objective-comparison.json',dict(scores=scores,pareto=paretos,not_convergence_or_adoption=True))
 summary=dict(schema='task1-centroid-tangent-ellipse-result-v1',status='single_centroid_area_matched_ellipse_screen_computed_unadopted',spec=spec,candidates=records,completed_conditions=3,actual_new_driven_RHS=2,actual_new_angular_metric_evaluations=1,actual_immutable_control_aliases=2,actual_control_RHS_repeated=0,actual_control_angular_metrics_repeated=0,new_eigen_solves=0,Q_resident_during_metrics=False,originals_overwritten=False,candidate_adopted=False,prior_actual_fine_outcome=context['fine_review'],ROI_receipt=context['ROI_receipt'],geometry_question='Same physical225mm2 area/actual P23 centroid, tangential smoothellipse versus originalpolyomino; fractional node contact and perimeter uncertainty remain confounds',comparison_definition='Fixed voltage/current-bookkeeping/power/joint8 separate; absolute targetmean/P10 and both ratios shown, min4/Pareto provisional only',four_objective_scores=scores,provisional_pareto=paretos,holds=dict(old_signals_raw_failures_GUI_preserved=True,old_13_of_14_XY_contact_failures_preserved=True,fractional_contact_and_edge_peak_uncertainty=True,full_convergence=False,experimental_validation=False,physiological_activation_or_safety_claim=False,candidate_adopted=False),new_native_phi_probe_predictions=dict(status='not_run',reason='Potential archives saved; update only after candidate result review'),Windows_saved_verified=False)
 check(guard,deadline);return dict(summary=summary,arrays={})
