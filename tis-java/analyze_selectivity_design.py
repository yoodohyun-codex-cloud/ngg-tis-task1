"""Metadata/scalar-only final analysis of the finite fixed-phantom design run.

Reads already complete case summaries and stored native scalar/volume weights.
No E/phi interpolation, waveform reconstruction, solver, or old registry body
processing. Relative high-TIS volume cutoffs are preregistered electrical map
comparators, never physiological thresholds. Original JSON remains SI.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,math,os,time
import numpy as np

ROOT=Path(__file__).resolve().parent
CONVERGENCE_PERCENT=dict(target20_modulation_V_m=1,target20_total_E_RMS_V_m=1,
 roi_mean_TIS_V_m=1,roi_p10_TIS_V_m=1,roi_mean_RMS_V_m=1,target_superficial_p95_ratio=1,
 surface_J_RMS_max_A_m2=5,surface_J_RMS_p95_A_m2=5,contact_voltage_RMS_max_V=5,
 SC_power_W=2,contact_power_W=2,source_power_W=2)
WAVE_FUND={'square_3h':1.,'sine':1/1.0606601717798212,'triangle_3h':.9/1.0606601717798212}

def read(p):return json.loads(Path(p).read_text())
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def ratio(a,b):return a/b if b!=0 else None
def delta(a,b):return 100*(b/a-1) if a!=0 else (0 if b==0 else None)
def square(result):return next(c for c in result['conditions'] if c['waveform']=='square_3h')
def values(c):
 e=c['metrics'];v=c['volume_metrics'];t=v['regions']['target']['statistics'];r=v['ratios']['maxTIS']['surface_0_5']
 return {**{k:e[k] for k in CONVERGENCE_PERCENT if k in e},'roi_mean_TIS_V_m':t['maxTIS']['mean'],'roi_p10_TIS_V_m':t['maxTIS']['p10'],
  'roi_mean_RMS_V_m':t['RMS']['mean'],'target_superficial_p95_ratio':r['target_mean_over_off_p95']}
def scales(e,b):
 for k in ('surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2','contact_voltage_RMS_max_V','SC_power_W','contact_power_W','source_power_W'):
  if not math.isfinite(e[k]) or not math.isfinite(b[k]) or e[k]<=0 or b[k]<=0:raise ValueError('Nonpositive/nonfinite normalization metric:'+k)
 linear={k:b[k]/e[k] for k in ('surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2','contact_voltage_RMS_max_V')}
 quadratic={k:math.sqrt(b[k]/e[k]) for k in ('SC_power_W','contact_power_W')}
 exact_power=math.sqrt(b['source_power_W']/e['source_power_W'])
 burden=min(1.,*linear.values(),*quadratic.values());power=min(1.,exact_power)
 active=min({**linear,**quadratic,'output_1Vpp':1},key={**linear,**quadratic,'output_1Vpp':1}.get)
 return dict(raw_1Vpp=1.,equal_power_exact_unclipped=exact_power,power_cap_1Vpp=power,
             skin_contact_cap_1Vpp=burden,joint_power_skin_cap_1Vpp=min(burden,power)),dict(linear_constraints=linear,
             quadratic_constraints=quadratic,skin_limiting_metric=active,exact_power_within_source_1Vpp=exact_power<=1)
def pareto(rows):
 out=[]
 for i,a in enumerate(rows):
  va=[a['roi_P10_TIS_V_cm'],a['roi_mean_TIS_V_cm'],a['target_mean_over_surface_P95'],-a['Jmax_mA_cm2'],-a['source_power_uW']]
  dominated=False
  for j,b in enumerate(rows):
   if i==j:continue
   vb=[b['roi_P10_TIS_V_cm'],b['roi_mean_TIS_V_cm'],b['target_mean_over_surface_P95'],-b['Jmax_mA_cm2'],-b['source_power_uW']]
   if all(x>=y for x,y in zip(vb,va)) and any(x>y for x,y in zip(vb,va)):dominated=True;break
  if not dominated:out.append(a['condition_id'])
 return out

def main(run):
 started=time.monotonic();run=Path(run).resolve();state=read(run/'summary.json');reg=read(run/'preregistration.json')
 if state['status']=='running':raise ValueError('Do not analyze a mutable executing run')
 if (run/'analysis.json').exists():
  old=read(run/'analysis.json')
  if old['source_summary_sha256']==digest(run/'summary.json') and old['analyzer_sha256']==digest(__file__):
   print('unchanged analysis reused');return
  raise FileExistsError('Use a new immutable analysis version for changed source/code')
 loaded={};source_pins={str(run/'summary.json'):digest(run/'summary.json'),str(run/'preregistration.json'):digest(run/'preregistration.json')}
 for item in state['cases']:
  p=Path(item['postprocess']['path']);actual=digest(p)
  if actual!=item['postprocess']['sha256']:raise ValueError('Completed case summary hash changed')
  data=read(p)
  if data['status']!='complete':raise ValueError('Do not promote incomplete source')
  case=read(run/'cases'/f"{item['id']}.json")
  loaded[item['id']]=dict(data=data,case=case,path=p);source_pins[str(p)]=actual
 baseline={x['case']['mesh_id']:x for x in loaded.values() if x['case']['design_id']=='baseline-square15' and x['case']['channels']==2}
 # The original final-grid reference is a read-only source result, not a new PDE.
 if 'reference-best1-final' in loaded:baseline['original_xy120']=loaded['reference-best1-final']
 bare_files={'xy80':'baseline-leader','xy100':'xy100-leader','sc4':'sc4-leader','original_xy120':'xy120-leader'}
 bare={};basepath=ROOT/'runs/leader-validation-3k-20261019T030136Z/cases'
 for mesh,ident in bare_files.items():
  p=basepath/(ident+'.json')
  if p.exists():
   c=read(p)
   if c.get('status')=='complete':bare[mesh]=(c,p);source_pins[str(p)]=digest(p)
 rows=[];norms=[];high=[];warnings=[];candidate_20point=[]
 for ident,entry in loaded.items():
  case,data=entry['case'],entry['data']
  if case['channels']!=2:continue
  mesh=case['mesh_id'];ref=baseline.get(mesh)
  if ref is None:warnings.append(dict(case_id=ident,status='normalization_held',reason='Exact same-mesh coated baseline absent'));continue
  by_wave={c['waveform']:c for c in ref['data']['conditions']}
  for c in data['conditions']:
   wave=c['waveform'];e=c['metrics'];b=by_wave[wave]['metrics'];v=c['volume_metrics'];t=v['regions']['target']['statistics']
   factors,receipt=scales(e,b);native=entry['path'].parent/c['native_volume_archive']
   source_pins[str(native)]=digest(native)
   with np.load(native,allow_pickle=False) as archive:
    native_tis=archive['maxTIS']*WAVE_FUND[wave];native_fixed=archive['fixedTIS']*WAVE_FUND[wave]
    weights={r:archive['region_'+r+'_m3'] for r in ('off_target','surface_0_5','subsurface_5_10','remaining')}
   bt=by_wave[wave]['volume_metrics']['regions']['target']['statistics']['maxTIS']
   thresholds={'baseline_ROI_P10':bt['p10'],'half_baseline_ROI_mean':.5*bt['mean']}
   compare=[('latest_coated_same_mesh',name,a,receipt) for name,a in factors.items()]
   if mesh in bare:
    bare_case,bpath=bare[mesh];bb=next(z for z in bare_case['metrics'] if z['waveform']==wave)
    # Validate mesh/geometry identity from published bare diagnostic metadata.
    if bare_case.get('h_xy_mm')==case['h_xy_mm'] and bare_case.get('sc_cells')==case['sc_cells']:
     sf,sr=scales(e,bb)
     compare.extend(('original_bare_1k_same_mesh',name,a,{**sr,'bare_source_case':str(bpath),'bare_source_case_sha256':source_pins[str(bpath)]}) for name,a in sf.items() if name in ('skin_contact_cap_1Vpp','power_cap_1Vpp','joint_power_skin_cap_1Vpp'))
   for reference,name,a,detail in compare:
    value={
     'condition_id':c['id'],'case_id':ident,'design_id':case['design_id'],'mesh_id':mesh,'waveform':wave,
     'reference':reference,'normalization':name,'source_Vpp_each':a,'within_original_1Vpp_output_cap':a<=1,
     'h_xy_mm':case['h_xy_mm'],'SC_cells':case['sc_cells'],'bulk_counts':','.join(map(str,case['bulk_counts'])),
     'roi_mean_TIS_V_cm':t['maxTIS']['mean']*a*.01,'roi_P10_TIS_V_cm':t['maxTIS']['p10']*a*.01,
     'roi_mean_fixed_TIS_V_cm':t['fixedTIS']['mean']*a*.01,'roi_P10_fixed_TIS_V_cm':t['fixedTIS']['p10']*a*.01,
     'roi_mean_E_RMS_V_cm':t['RMS']['mean']*a*.01,
     'central20_TIS_V_cm':e['target20_modulation_V_m']*a*.01,'central20_E_RMS_V_cm':e['target20_total_E_RMS_V_m']*a*.01,
     'Jmax_mA_cm2':e['surface_J_RMS_max_A_m2']*a*.1,'J95_area_weighted_mA_cm2':e['surface_J_RMS_p95_A_m2']*a*.1,
     'contact_voltage_RMS_mV':e['contact_voltage_RMS_max_V']*a*1000,
     'SC_power_uW':e['SC_power_W']*a*a*1e6,'contact_power_uW':e['contact_power_W']*a*a*1e6,'source_power_uW':e['source_power_W']*a*a*1e6,
     'target_mean_over_surface_P95':v['ratios']['maxTIS']['surface_0_5']['target_mean_over_off_p95'],
     'target_P10_over_surface_P95':v['ratios']['maxTIS']['surface_0_5']['target_p10_over_off_p95'],
     'target_mean_over_all_off_P95':v['ratios']['maxTIS']['off_target']['target_mean_over_off_p95']}
    for r,label in [('surface_0_5','surface_0_5'),('subsurface_5_10','subsurface_5_10'),('remaining','remaining'),('off_target','all_off')]:
     stats=v['regions'][r]['statistics']
     for metric,mkey in [('TIS','maxTIS'),('fixed_TIS','fixedTIS'),('E_RMS','RMS')]:
      value[f'{label}_P95_{metric}_V_cm']=stats[mkey]['p95']*a*.01;value[f'{label}_max_{metric}_V_cm']=stats[mkey]['max']*a*.01
    for threshold,cutoff in thresholds.items():
     for field,arr in [('maxTIS',native_tis),('fixedTIS',native_fixed)]:
      for region,w in weights.items():
       volume=float(w[arr*a>=cutoff].sum())
       high.append(dict(condition_id=c['id'],case_id=ident,normalization=name,reference=reference,
        field=field,region=region,threshold_name=threshold,threshold_V_m=cutoff,volume_mm3=volume*1e9,
        fraction=volume/float(w.sum()),baseline_case_id=ref['case']['id'],baseline_result_sha256=source_pins[str(ref['path'])],
        threshold_interpretation='predeclared relative map comparator; not activation or safety threshold'))
       if region=='off_target' and field=='maxTIS':value['off_high_volume_'+threshold+'_mm3']=volume*1e9
    rows.append(value);norms.append(dict(condition_id=c['id'],normalization=name,reference=reference,scale=a,details=detail,
      linear_fields_current_voltage_scale=a,quadratic_power_scale=a*a,baseline_same_wave_case_id=ref['case']['id']))
  candidate_20point.append(dict(case_id=ident,original_Best1_comparison_scope='Current source exact original_xy120 shown separately; candidate comparisons use same-mesh rerun baseline'))
 # Pair-specific convergence; no global final/continuous convergence claim.
 convergence=[]
 for entry in loaded.values():
  c=entry['case']
  if c['channels']!=2 or c['mesh_id'] not in ('xy100','sc4','bulk'):continue
  before=loaded.get(c['design_id']+'-xy80')
  if before is None:continue
  for wave in ('square_3h','sine','triangle_3h'):
   old=values(next(z for z in before['data']['conditions'] if z['waveform']==wave));new=values(next(z for z in entry['data']['conditions'] if z['waveform']==wave))
   changes={k:dict(before=old[k],after=new[k],relative_change_percent=delta(old[k],new[k]),limit_percent=l,
              passed=delta(old[k],new[k]) is not None and abs(delta(old[k],new[k]))<=l) for k,l in CONVERGENCE_PERCENT.items()}
   convergence.append(dict(design_id=c['design_id'],axis=c['mesh_id'],waveform=wave,before_case=before['case']['id'],after_case=c['id'],
    changes=changes,registered_pair_passed=all(z['passed'] for z in changes.values()),
    full_continuum_convergence_certified=False,independent_surface_or_whole3D_final_validation='held beyond this limited adjacent pair'))
 # Controls are physically separate two-pad solves at exact same h/.625 material and shape.
 controls=[]
 for entry in loaded.values():
  cc=entry['case']
  if cc['channels']!=1:continue
  tis=loaded.get(cc['design_id']+'-xy80')
  if tis is None:continue
  for control in entry['data']['conditions']:
   target=next(z for z in tis['data']['conditions'] if z['waveform']==control['waveform'])
   ce,te=control['metrics'],target['metrics']
   cr=control['volume_metrics']['regions']['target']['statistics']['RMS']['mean'];tr=target['volume_metrics']['regions']['target']['statistics']['RMS']['mean']
   for match,ct,tt in [('central20_total_E_RMS',ce['target20_total_E_RMS_V_m'],te['target20_total_E_RMS_V_m']),('ROI_mean_total_E_RMS',cr,tr)]:
    if ct==0:controls.append(dict(control_id=control['id'],status='held_zero_transfer',match=match));continue
    a=tt/ct
    burden={k:dict(single_at_matching=ce[k]*(a*a if k.endswith('_W') else a),TIS_at_1Vpp=te[k],ratio_single_over_TIS=ratio(ce[k]*(a*a if k.endswith('_W') else a),te[k])) for k in ('surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2','contact_voltage_RMS_max_V','SC_power_W','contact_power_W','source_power_W')}
    controls.append(dict(status='electrical_comparison_complete_convergence_held',control_id=control['id'],TIS_id=target['id'],indexed_pair=cc['indexed_pair'],
     actual_single_carrier_Hz=control['actual_fundamental_Hz'],match=match,required_source_Vpp=a,source_ohm=50,single_two_carrier_TIS=0,
     linear_scaling_verified=all(z['passed'] for q in entry['data']['actual_transfer_amplitude_scaling_checks'] for z in q['checks'].values()),quadratic_power_scaling_verified=all(z['passed'] for q in entry['data']['actual_transfer_amplitude_scaling_checks'] for z in q['checks'].values()),actual_transfer_amplitude_scaling_checks=entry['data']['actual_transfer_amplitude_scaling_checks'],burden=burden,
     limitation='High amplitude is small-signal contact engineering extrapolation; neither equal activation nor instrument compliance proven'))
 pareto_groups={}
 for mesh in sorted({r['mesh_id'] for r in rows}):
  for norm in ('raw_1Vpp','power_cap_1Vpp','skin_contact_cap_1Vpp','joint_power_skin_cap_1Vpp'):
   r=[x for x in rows if x['mesh_id']==mesh and x['waveform']=='square_3h' and x['normalization']==norm and x['reference']=='latest_coated_same_mesh']
   if r:pareto_groups[mesh+'/'+norm]=pareto(r)
 nominal=[]
 for row in rows:
  if row['waveform']!='square_3h' or row['reference']!='latest_coated_same_mesh' or row['design_id']=='baseline-square15':continue
  base=next((r for r in rows if r['design_id']=='baseline-square15' and r['mesh_id']==row['mesh_id'] and r['normalization']==row['normalization'] and r['reference']==row['reference'] and r['waveform']==row['waveform']),None)
  if base:
   nominal.append(dict(condition_id=row['condition_id'],mesh_id=row['mesh_id'],normalization=row['normalization'],
    ROI_mean_gain_percent=delta(base['roi_mean_TIS_V_cm'],row['roi_mean_TIS_V_cm']),ROI_P10_gain_percent=delta(base['roi_P10_TIS_V_cm'],row['roi_P10_TIS_V_cm']),
    surface_selectivity_gain_percent=delta(base['target_mean_over_surface_P95'],row['target_mean_over_surface_P95']),
    simultaneous_nominal_absolute_and_surface_ratio_improvement=all(row[k]>base[k] for k in ('roi_mean_TIS_V_cm','roi_P10_TIS_V_cm','target_mean_over_surface_P95')),
    clinically_or_continuum_validated=False))
 conclusions={
  'Q1':dict(question='고정 팬텀에서15–20mm 절대 TIS와선택성을동시에개선했는가?',nominal_simultaneous_cases=[x for x in nominal if x['simultaneous_nominal_absolute_and_surface_ratio_improvement']],
    limitation='Finite design pool; native FVM/direction sampled electrical metrics. Coarse improvements require same-mesh refinement and independent current-density/contact/geometry checks.'),
  'Q2':dict(question='같은 피부 부담과전력에서도유지되는가?',comparisons=[x for x in nominal if x['normalization'] in ('skin_contact_cap_1Vpp','power_cap_1Vpp','joint_power_skin_cap_1Vpp')],
    references='Same-wave same-mesh current-coated design baseline; exact existing bare1k burden/power caps separately where available. Coated baseline is never relabelled bare.'),
  'Q3':dict(question='모서리·격자·조직경계효과에의존하지않는가?',registered_convergence_rows=len(convergence),pair_failures=[x for x in convergence if not x['registered_pair_passed']],
    continuum_independence_demonstrated=False,limitation='Adjacent XY/SC/bulk tests and native phi-E/operator conservation are separate; insulating bottom and staircase cylinder remain part of physical phantom model.'),
  'Q4':dict(question='기존 Best1보다얻고잃은것은?',same_mesh_deltas=nominal,
    reference_original_case='reference-best1-final',limitation='Original nominal centre leader is retained. New ROI P10/mean/surface P95/high-volume/J/power tradeoffs are separate and no physiological efficacy/safety claim follows.')}
 if 'reference-best1-final' in loaded:
  old=read(ROOT/'runs/rs-window-tis-validation-20261019T135413Z/cases/coat010-f0500-minusRs.json');new=loaded['reference-best1-final']['data']
  reproduction=[]
  for c in new['conditions']:
   o=next(r for r in old['metrics'] if r['waveform']==c['waveform'])
   for k in ('target20_modulation_V_m','target20_total_E_RMS_V_m','surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2','contact_voltage_RMS_max_V','SC_power_W','contact_power_W','source_power_W'):
    rel=abs(c['metrics'][k]/o[k]-1) if o[k] else abs(c['metrics'][k]);reproduction.append(dict(waveform=c['waveform'],metric=k,relative_error=rel,passed=rel<=2e-7))
  if not all(r['passed'] for r in reproduction):raise ValueError('Original Best1 scalar reproduction failed')
 else:reproduction=[]
 out=dict(schema='fixed-phantom-selectivity-analysis-v1',status='complete_existing_results_analysis',created_utc=datetime.now(timezone.utc).isoformat(),
  source_run_id=run.name,source_run_status=state['status'],source_summary_sha256=digest(run/'summary.json'),analyzer_sha256=digest(__file__),
  source_inputs_sha256=source_pins,nominal_reference_not_global_optimum=True,original_best1_reproduction=reproduction,
  completed_ledger_cases=len(loaded),new_PDE_conditions=state['new_PDE_jobs'],normalizations=norms,rows_cm=rows,
  relative_high_modulation_volume=high,convergence=convergence,pareto=pareto_groups,controls=controls,conclusions=conclusions,
  representative_case_ids=['baseline-square15-xy80',*[d+'-xy80' for d in state.get('selected_coarse',[])]],
  source_version_scope='New finite results only; original registry row bodies and old GUI pointers untouched',
  holds=['No neural/muscle/diaphragm activation or safety proof.','New coating/Rs/contact/3D continuous validation held.',
   'Physical insulating side/bottom fixed; target15–20 is5.1–10.1mm above bottom.','Display phi-gradient maps differ from native-cell volume metrics.'],
  warnings=warnings,new_PDE=0,new_original_row_body_processing=0,wall_seconds=time.monotonic()-started)
 for p,v in source_pins.items():
  if digest(p)!=v:raise ValueError('Source changed during final scalar analysis')
 with (run/'analysis-rows-cm.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['case_id']);w.writeheader();w.writerows(rows)
 (run/'analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 print(json.dumps(dict(status=out['status'],rows=len(rows),controls=len(controls),convergence=len(convergence),nominal_both=len(conclusions['Q1']['nominal_simultaneous_cases']),new_PDE=0)))

if __name__=='__main__':
 os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();main(a.run)
