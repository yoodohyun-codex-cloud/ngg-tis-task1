"""Verified cached native geometry consolidation: no PDE or angular reevaluation.

All numerical work is deferred to the sole root owner. Stored scalar fields
and actual complex potentials/vectors are read only after their publication
identities are authenticated. Same-ID verification variants remain explicit;
the first8 B0 is the immutable comparison reference. Local reported rows are
kept separately at fixed voltage, without invented native/electrical data.
"""
from __future__ import annotations
import copy,gc,json,math,time
from pathlib import Path
import consolidation_inputs
import frozen_design_analysis as view_math
import pixel_outline
import probe_prediction

SOURCE=Path('/dev/shm/task1-results-consolidation-20261025/source')
BASELINE='B0-square15-c10-diagonal'
MANDATORY=('MP8-vertical-strips','MP12-vertical-strips','MP16-subpad2x2')
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
SCALARS=('carrier_RMS','carrier0_RMS','carrier1_RMS','AM_x','AM_y','AM_z','AM_max2074','AM_direction_index','Jtotal_vector_RMS')

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(path):return view_math.sha_file(path)
def new_json(path,value):return view_math.new_json(path,value)
def check(guard,deadline):
 guard();require(deadline is None or time.monotonic()<deadline,'Finite cached consolidation deadline')
def _admission(value=None):
 if value is not None:return value
 return json.loads((SOURCE/'root-admission.json').read_bytes())
def _context(admission):return consolidation_inputs.make_spec(admission)

def required_inputs(root_admission=None):
 return dict(consolidation_inputs.required_inputs(_admission(root_admission)))

def make_spec(root_admission=None):
 admission=_admission(root_admission);context=_context(admission);candidates=context['canonical_candidates'];require(len(candidates)==15 and len({r['candidate_id']for r in candidates})==15,'Exactly fifteen distinct canonical native geometries')
 baseline=next(r for r in candidates if r['candidate_id']==BASELINE);b=baseline['record']['metrics']['regions'];B=b['target']['statistics']['maxTIS'];surface=b['surface_0_5']['statistics']['maxTIS'];off=b['off_target']['statistics']['maxTIS']
 return dict(schema='task1-native-results-consolidation-spec-v1',root_admission=admission,input_sha256=context['input_sha256'],expected_canonical_native_geometries=15,baseline_id=BASELINE,mandatory_compare_ids=list(MANDATORY),
  canonical_identities=[dict(candidate_id=r['candidate_id'],scalar_SHA256=r['scalar']['SHA256'],mask_SHA256=r['mask']['SHA256'],raw_SHA256_by_frequency={f:r['raw_by_frequency'][f]['SHA256']for f in('2000','2010')})for r in candidates],
  baseline_comparison=dict(target_AM_mean_V_m=B['mean'],target_AM_P10_V_m=B['p10'],target_to_surface_mean_ratio=B['mean']/surface['mean']if surface['mean']>0 else None,target_to_offtarget_mean_ratio=B['mean']/off['mean']if off['mean']>0 else None),
  rank_definition='For each of four separate normalizations: minimum of targetmean/B0mean, targetP10/B0P10, (targetmean/surfacemean)/(B0targetmean/B0surfacemean), (targetmean/offtargetmean)/(B0targetmean/B0offtargetmean). Display all ratios and absolute values. Primary provisional display order uses joint8 burden comparison, never candidate adoption.',
  zero_reference_policy='A missing/zero reference makes that ratio and min4 score unavailable; never insert an epsilon or zero-filled result',
  diagnostic_cutoffs=[dict(cutoff_id='B0-target-AM-mean',value_V_m=B['mean']),dict(cutoff_id='B0-offtarget-AM-P95',value_V_m=off['p95'])],cutoff_policy='Post-PDE baseline-relative numerical diagnostic values, fixed before this cached classification. No physiological activation or safety threshold.',
  common_grid_policy='Authenticate original bytes then compare decoded grid and every six original m3 ROI mask arrays exactly across each distinct grid archive; no coordinate index guessing or mask recomputation',
  alias_policy='Deduplicate exact candidateID+scalarSHA. SameID/differentSHA verification variants remain listed; compare stored scalar arrays without angular reevaluation, use earliest canonical record for display rather than overwrite any result.',
  probe_policy='Forty unloaded differential predictions per geometry, physical centre/depth/cross coordinates and5mm tip spacing distinct. Same-layer interpolation/extrapolation and nearest-point sensitivity disclosed; ETA5001/DSOX input loading not solved or validated.',
  local_policy='Reported LOCAL14/LOCAL16 rows are separate fixed-voltage metadata only; native fields, electrical files and burden-normalized comparisons pending unless independently supplied and authenticated. Not ranked alongside native geometries.',
  new_PDE_RHS=0,actual_new_angular_evaluations=0,candidate_adopted=False,Windows_saved_verified=False)

def four_ratios(mean,p10,surface_mean,off_mean,reference):
 require(all(math.isfinite(float(v))and v>=0 for v in(mean,p10,surface_mean,off_mean)),'Finite nonnegative absolute electrical proxies')
 ts=mean/surface_mean if surface_mean>0 else None;to=mean/off_mean if off_mean>0 else None
 def ratio(value,base):return value/base if value is not None and base is not None and base>0 else None
 ratios=dict(target_mean=ratio(mean,reference['target_AM_mean_V_m']),target_P10=ratio(p10,reference['target_AM_P10_V_m']),target_to_surface_mean=ratio(ts,reference['target_to_surface_mean_ratio']),target_to_offtarget_mean=ratio(to,reference['target_to_offtarget_mean_ratio']))
 return dict(four_ratios_to_B0=ratios,robust_minimum_four_ratio=min(ratios.values())if all(v is not None for v in ratios.values())else None,target_to_surface_mean_ratio=ts,target_to_offtarget_mean_ratio=to)

def comparison_row(normalized,reference):
 fields=normalized['absolute_ROI_fields_V_m'];t=fields['target']['maxTIS'];s=fields['surface_0_5']['maxTIS'];o=fields['off_target']['maxTIS'];m=four_ratios(t['mean'],t['p10'],s['mean'],o['mean'],reference)
 m.update(target_AM_mean_V_m=t['mean'],target_AM_P10_V_m=t['p10'],target_AM_max_V_m=t['max'],target_AM_std_V_m=t['std'],target_AM_CV=t['std']/t['mean']if t['mean']>0 else None,target_P10_mean=t['p10']/t['mean']if t['mean']>0 else None,surface_AM_mean_V_m=s['mean'],surface_AM_P95_V_m=s['p95'],surface_AM_max_V_m=s['max'],off_target_AM_mean_V_m=o['mean'],off_target_AM_P95_V_m=o['p95'],off_target_AM_P99_V_m=o['p99'],off_target_AM_max_V_m=o['max'],amplitude_scale=normalized['amplitude_scale'],electrical=copy.deepcopy(normalized['electrical']),limiting_constraints=copy.deepcopy(normalized.get('limiting_constraints',[])))
 return m

def _load(np,descriptor,keys,pins,guard,deadline,optional_keys=()):
 check(guard,deadline);path=Path(descriptor['path']);require(str(path)in pins and pins[str(path)]==descriptor['SHA256'],'Only deferred authenticated dataset input may be decoded');require(path.is_file()and path==path.resolve()and not path.is_symlink()and path.stat().st_size==descriptor['bytes']<=80*1024**2 and digest(path)==descriptor['SHA256'],'Exact published native archive bytes before decode')
 with np.load(path,allow_pickle=False)as saved:
  require(set(keys).issubset(saved.files),'Required stored native field unavailable; do not fabricate or recompute it');result={key:np.array(saved[key],copy=True)for key in list(keys)+[key for key in optional_keys if key in saved.files]}
 require(all(np.isfinite(v).all()for v in result.values()),'Finite stored numerical fields');return result

def _common_geometry(np,context,spec,guard,deadline):
 keys=['grid']+[key+'_volume_weight_m3'for key in REGIONS];optional=('ij','z_faces_m');common=_load(np,context['common_grid_ROI'],keys,spec['input_sha256'],guard,deadline,optional);grid=common['grid'];require(grid.shape==(793860,5),'Unchanged common physical native grid');proofs=[];seen={context['common_grid_ROI']['SHA256']}
 for descriptor in context['common_grids']:
  check(guard,deadline)
  if descriptor['SHA256']in seen:
   require(spec['input_sha256'].get(descriptor['path'])==descriptor['SHA256']and digest(descriptor['path'])==descriptor['SHA256'],'Same-SHA grid alias actual bytes before identity claim');proofs.append(dict(dataset_id=descriptor['dataset_id'],archive_SHA256=descriptor['SHA256'],status='exact_same_archive_bytes'));continue
  candidate=_load(np,descriptor,keys,spec['input_sha256'],guard,deadline,optional);shared_optional=[key for key in optional if key in candidate and key in common];checked=keys+shared_optional;require(all(np.array_equal(candidate[key],common[key])for key in checked),'Dataset body/ROI masks differ; no forced index comparison or silent remapping');proofs.append(dict(dataset_id=descriptor['dataset_id'],archive_SHA256=descriptor['SHA256'],status='all_native_grid_and_six_ROI_arrays_bit_identical',checked_keys=checked,optional_keys_missing=[key for key in optional if key not in candidate or key not in common]));seen.add(descriptor['SHA256']);del candidate
 weights={key:common[key+'_volume_weight_m3']for key in REGIONS};weights['surface_without_SC']=weights['surface_0_5']*(grid[:,3].astype(int)!=0);return grid,weights,proofs

def _electrodes(entry,pins):
 descriptor=entry['mask'];path=Path(descriptor['path']);require(path.is_absolute()and path==path.resolve()and pins.get(str(path))==descriptor['SHA256']and path.is_file()and not path.is_symlink()and path.stat().st_size==descriptor['bytes']<8_000_000 and digest(path)==descriptor['SHA256'],'Authenticated actual physical mask CSV')
 return pixel_outline.electrodes(path.read_bytes(),entry['padmetadata'],.5)

def _variant_proofs(np,context,pins,guard,deadline):
 canonical={row['candidate_id']:row for row in context['canonical_candidates']};proofs=[]
 for identity in context['identity_variants']:
  variant=identity['record'];check(guard,deadline);cid=variant['candidate_id'];original=canonical[cid];a=_load(np,original['scalar'],SCALARS,pins,guard,deadline);b=_load(np,variant['scalar'],SCALARS,pins,guard,deadline);require(all(a[key].shape==b[key].shape for key in SCALARS),'Same-ID scalar variant changed dimensions; no implicit alias');differences={key:dict(array_equal=bool(np.array_equal(a[key],b[key])),maximum_absolute_difference=float(np.max(abs(a[key]-b[key]))))for key in SCALARS};proofs.append(dict(candidate_id=cid,canonical_scalar_SHA256=original['scalar']['SHA256'],variant_scalar_SHA256=variant['scalar']['SHA256'],all_scalar_arrays_identical=all(v['array_equal']for v in differences.values()),differences=differences,display_policy='Earliest canonical published record; variant retained explicitly, no overwrite or extra geometry count',variant_provenance=variant['provenance']));del a,b
 return proofs

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(spec==make_spec(spec['root_admission'])and callable(guard),'Exact deferred root-admitted consolidated inputs/ranking definition');check(guard,deadline_monotonic);context=_context(spec['root_admission']);out=Path(output_dir);require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink()and out.parent==Path('/dev/shm'),'Unique root-created analysis output')
 import numpy as np
 grid,weights,grid_proofs=_common_geometry(np,context,spec,guard,deadline_monotonic);variant_proofs=_variant_proofs(np,context,spec['input_sha256'],guard,deadline_monotonic);new_json(out/'common-grid-identity-proof.json',grid_proofs);new_json(out/'control-identity-variant-proof.json',variant_proofs);new_json(out/'diagnostic-cutoffs.json',dict(policy=spec['cutoff_policy'],cutoffs=spec['diagnostic_cutoffs']));rows=[];view_candidates={};shared_max=0.;cdir=out/'candidates';cdir.mkdir(exist_ok=True)
 for entry in context['canonical_candidates']:
  check(guard,deadline_monotonic);cid=entry['candidate_id'];record=entry['record'];scalar=_load(np,entry['scalar'],['AM_max2074','carrier_RMS'],spec['input_sha256'],guard,deadline_monotonic);require(all(v.shape==(len(grid),)for v in scalar.values()),'Same native scalar ordering');phi=[];E=[]
  for frequency in('2000','2010'):
   data=_load(np,entry['raw_by_frequency'][frequency],['phi_peak_V','E_peak_V_m'],spec['input_sha256'],guard,deadline_monotonic);require(data['phi_peak_V'].shape==(len(grid),)and data['E_peak_V_m'].shape==(len(grid),3),'Full actual carrier potential/vector ABI');phi.append(data['phi_peak_V']);E.append(data['E_peak_V_m'])
  electrodes=_electrodes(entry,spec['input_sha256']);count=len(electrodes);require(count==record['metrics']['pads']and record['metrics']['independent_outputs']==2,'Actual physical pad count distinct from exactly two outputs');metrics={};scales={};classified={}
  for mode in MODES:
   normalized=record['normalizations']['comparisons'][mode];require(normalized['status']=='calculated_global_amplitude_rescaling','Existing complete distinct normalization required');metrics[mode]=comparison_row(normalized,spec['baseline_comparison']);scale=float(normalized['amplitude_scale']);scales[mode]=scale;scaled=scalar['AM_max2074']*scale;shared_max=max(shared_max,float(np.max(scaled)),float(np.max(scalar['carrier_RMS']))*scale);classified[mode]={cutoff['cutoff_id']:{region:view_math.high_volume(np,scaled,weights[region],grid,cutoff['value_V_m'])for region in('target','surface_0_5','surface_without_SC','off_target','total')}for cutoff in spec['diagnostic_cutoffs']}
  probe=probe_prediction.build(np,grid,phi[0],phi[1],guard,deadline_monotonic);new_json(cdir/(cid+'-probe.json'),probe['summary'])
  with(cdir/(cid+'-probe-arrays.npz')).open('xb')as f:np.savez_compressed(f,**probe['arrays'])
  row=dict(candidate_id=cid,physical_pad_count=count,independent_outputs=2,electrodes=electrodes,metrics=metrics,score_burden_matched_min4=metrics['joint_eight_surface_contact_burden_caps']['robust_minimum_four_ratio'],high_modulation_volumes=classified,global_hotspot_fixed1Vpp=copy.deepcopy(record['metrics']['regions']['total']['statistics']['maxTIS']),probe_prediction=probe['summary'],provenance=entry['provenance'],source_run_id=entry['provenance'].get('source_run_id'),source_result_commit=entry['provenance'].get('result_commit'),source_scalar_SHA256=entry['scalar']['SHA256'],source_mask_SHA256=entry['mask']['SHA256'],source_raw_SHA256_by_frequency={key:value['SHA256']for key,value in entry['raw_by_frequency'].items()},holds=copy.deepcopy(record.get('holds',record['metrics']['holds'])),candidate_adopted=False)
  row['holds'].update(global_SC_hotspot_not_cleared=True,full_numerical_convergence=False,experimental_validation=False,candidate_adopted=False);rows.append(row);view_candidates[cid]=view_math._views(np,grid,scalar,E[0],E[1],electrodes,scales,guard,deadline_monotonic);new_json(cdir/(cid+'-consolidated.json'),row);new_json(out/('checkpoint-%02d.json'%len(rows)),dict(status='cached_native_geometry_consolidated',candidate_id=cid,completed_native_geometries=len(rows),new_PDE_RHS=0,actual_new_angular_evaluations=0));del scalar,phi,E,data,probe;gc.collect()
 def key(row):
  score=row['score_burden_matched_min4'];m=row['metrics']['joint_eight_surface_contact_burden_caps'];return (-(score if score is not None else -math.inf),-m['target_AM_P10_V_m'],-m['target_AM_mean_V_m'],row['candidate_id'])
 ranked=sorted(rows,key=key)
 for i,row in enumerate(ranked,1):row['provisional_rank']=i if row['score_burden_matched_min4']is not None else None
 top=[row['candidate_id']for row in ranked if row['provisional_rank']is not None][:5];display=list(dict.fromkeys(top+[BASELINE]+list(MANDATORY)));local=copy.deepcopy(context['reported_local_candidates'])
 for row in local:row.update(native_comparison_class='reported_local_fixed_voltage_only',eligible_for_native_ranking=False,electrical_and_burden_normalization_status='pending_files_unless_explicitly_verified',new_native_values_inferred=False)
 aliases=[dict(candidate_id=a['candidate_id'],identity_key=a['identity_key'],canonical_dataset=a['canonical_dataset'],alias_dataset=a['alias_dataset'],scalar=a['record']['scalar'],provenance=a['record']['provenance'])for a in context['aliases']]
 summary=dict(schema='task1-native-results-consolidation-v1',status='fifteen_native_geometries_cached_gui_probe_analysis_complete',spec=spec,baseline_id=BASELINE,mandatory_compare_ids=list(MANDATORY),candidates=rows,canonical_native_geometries=len(rows),provisional_top5=top,display_candidates_with_baseline=display,reported_local_candidates=local,rank_definition=spec['rank_definition'],diagnostic_cutoffs=spec['diagnostic_cutoffs'],high_volume_cutoff_policy=spec['cutoff_policy'],common_grid_identity_proofs=grid_proofs,identity_variants=variant_proofs,exact_aliases=aliases,dataset_provenance=context['datasets'],roi_definitions=context['ROI_receipt'],power_topology=dict(independent_outputs=2,source_resistance_ohm=50,return_topology='Common grounded returns, activeout0@2000/activeout1@2010; otheridealoutput0Vthrough50ohm',physical_pad_counts_compared=[4,8,12,16]),new_PDE_RHS=0,actual_new_angular_evaluations=0,no_original_phi_E_or_scalar_overwrite=True,candidate_adopted=False,Windows_saved_verified=False)
 views=dict(schema='task1-consolidated-native-views-v1',baseline_id=BASELINE,fixed_ranges=dict(xy_mm=[-25,25],depth_mm=[0,25.1],field_V_m=[0,shared_max]),candidates=view_candidates,raw_fields_clipped=False,all_native_normalizations_share_color_and_axes_by_default=True);new_json(out/'views.json',views);check(guard,deadline_monotonic);return dict(summary=summary,arrays={},views=views)
