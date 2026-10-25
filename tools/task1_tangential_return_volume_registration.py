"""Register completed original-square/asymmetric/tangential-return volumes only."""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

try:
    import task1_adjacent_source_volume_registration as style
except ModuleNotFoundError as error:
    if error.name!='task1_adjacent_source_volume_registration':raise
    from tools import task1_adjacent_source_volume_registration as style
inherited=style.inherited
ROOT=Path(__file__).resolve().parents[1]
NEW_RUN='cloud-tangential-return-20261021T183000Z'
CASE_ID='asym-return-tangent4p375-xy80'
PARENT_RUN='cloud-asymmetric-20261021T051000Z'
PARENT_ID='asym-cross281p25-return168p75-xy80'
CASE_TABLE=(inherited.CASE_TABLE[0],(PARENT_RUN,PARENT_ID),(NEW_RUN,CASE_ID))
SOURCES=('tools/task1_tangential_return_volume_registration.py','tests/test_task1_tangential_return_volume_registration.py',
    'tools/task1_tangential_return_registration.py','tests/test_task1_tangential_return_registration.py',*style.SOURCES)
ALLOWED_CONFIG_CHANGES={'mask.path','mask.sha256','pad.2.x_mm','pad.2.y_mm','pad.3.x_mm','pad.3.y_mm'}
SHIFTS={'2':[4.375,4.375],'3':[-4.375,-4.375]}
INDEX_SHIFTS={'2':[7,7],'3':[-7,-7]}
PARENT_CENTRES={'2':[10.,-10.],'3':[-10.,10.]}
NEW_CENTRES={'2':[14.375,-5.625],'3':[-14.375,5.625]}


def _committed_sources(root):
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();refs={}
    for name in dict.fromkeys(SOURCES):
        path=inherited._regular(root/name,root)
        inherited.require(subprocess.check_output(['git','show',commit+':'+name],cwd=root)==path.read_bytes(),
            'Commit consumed implementation/helpers/tests before registration: '+name)
        refs[str(path)]=inherited.sha(path)
    return commit,refs


def validate_translation_configs(parent,current):
    inherited.require(parent.keys()==current.keys()and all(parent[k]==current[k]for k in parent if k not in ALLOWED_CONFIG_CHANGES),
        'Only GNDpad2/3 coordinates plus portable mask identity may change')
    for p in ('2','3'):
        inherited.require([float(parent[f'pad.{p}.{axis}_mm'])for axis in ('x','y')]==PARENT_CENTRES[p]and
            [float(current[f'pad.{p}.{axis}_mm'])for axis in ('x','y')]==NEW_CENTRES[p]and
            float(parent[f'pad.{p}.rotation_deg'])==float(current[f'pad.{p}.rotation_deg'])==0. and
            float(parent[f'pad.{p}.width_mm'])==float(current[f'pad.{p}.width_mm'])==15. and
            float(parent[f'pad.{p}.height_mm'])==float(current[f'pad.{p}.height_mm'])==11.25,
            'Exact unrotated return translation with unchanged intrinsic dimensions required')
    inherited.require(parent['mask.sha256']!=current['mask.sha256'],'Translation must have a distinct contact-mask identity')


def validate_translation_provenance(parent,current):
    design=current['design'];old=parent['design']
    inherited.require(current.get('translation_only_contrast')is True and current.get('applied_physical_rotation_deg')==0 and
        current.get('operative_config_rotation_deg')==0 and design.get('physical_rotation_deg')==0,
        'Translation-only physical and operative rotation0 provenance required')
    for record in (current,design):
        inherited.require(record.get('return_shift_grid_indices')==INDEX_SHIFTS and record.get('return_shift_mm')==SHIFTS and
            record.get('moved_physical_pad_ids')==[2,3],
            'Exact seven-face return translations and physical shifts required')
    inherited.require(all(design['pads'][p]==old['pads'][p]for p in (0,1)),
        'Source pad0/1 identities and polygons must remain byte-value identical')
    for p in (2,3):
        before,after=old['pads'][p],design['pads'][p];key=str(p);shift=SHIFTS[key]
        inherited.require(before.get('pad')==after.get('pad')==p and before.get('role')==after.get('role')=='common_gnd_return'and
            before.get('source_output')is None and after.get('source_output')is None and
            before.get('center_mm')==PARENT_CENTRES[key]and after.get('center_mm')==NEW_CENTRES[key],
            'Moved pads retain physicalGND identities without exchange')
        inherited.require(all(after.get(k)==v for k,v in before.items()if k not in ('center_mm','polygon_mm')),
            'Return shape, dimensions, rotation, area and node metadata must remain unchanged')
        inherited.require(set(after)-set(before)<={'applied_translation_mm','applied_physical_rotation_deg'}and
            after.get('applied_translation_mm')==shift and after.get('applied_physical_rotation_deg')==0,
            'Only explicit zero-rotation translation provenance may be added to moved pads')
        polygon=before.get('polygon_mm',[])
        inherited.require(len(polygon)==4 and after.get('polygon_mm')==[[x+shift[0],y+shift[1]]for x,y in polygon],
            'Return polygon must be an exact translation with no clipping or rotation')
    inherited.require(design.get('minimum_gap_mm')==1.25 and design.get('minimum_gap_XY_cells')==2 and
        design.get('physical_total_contact_area_mm2')==900.,
        'Fixed900mm2 area and preregistered1.25mm two-cell gap must remain explicit')


def _validate_family(item,pre,config,index):
    case=next(c for c in pre['cases']if c['id']==item['case_id']);circuit=case['circuit']
    inherited.require(circuit.get('n_pads')==4 and circuit.get('n_outputs')==2 and circuit.get('n_return_nodes')==1 and
        circuit.get('pad_to_node')=={'0':'out0','1':'out1','2':'GND','3':'GND'}and circuit.get('source_resistance_ohm')==50 and
        circuit.get('source_peak_V')==.5 and circuit.get('source_Vpp_each')==1 and
        circuit.get('return_topology')=='all_return_pads_ideal_common_GND'and circuit.get('carrier_assignment_Hz')==[3000,3030]and
        circuit.get('inactive_source_at_other_frequencies','').replace(' ','')=='0Vthrough50ohm',
        'Four actual pads/two outputs/one commonGND/50ohm termination required')
    expected=[225.]*4 if index==0 else[281.25,281.25,168.75,168.75]
    areas=case.get('expected_pad_areas_m2',[])
    inherited.require(len(areas)==4 and all(math.isclose(a,b*1e-6,rel_tol=1e-12,abs_tol=1e-16)for a,b in zip(areas,expected))and
        case.get('source_coating_nm')==10 and case.get('source_Rs_fit_window_Hz')==500,'Fixed nominalRs500 per-pad allocation required')
    inherited.require(float(config['h_mm'])==.625 and config['validation.sc_cells']=='2'and config['bulk.counts']=='14,14,40'and
        config['channels']=='2'and config['frequencies']=='3000,3030,9000,9090','Same native grid and square3h spectrum required')
    return case


def _feedback(path,refs,root):
    digest=inherited._pin(path,refs,root);obj=inherited.read(path)
    inherited.require(obj.get('schema')=='task1-queue-feedback-v1'and obj.get('status')=='read_only_feedback_checked'and
        obj.get('error')is None and obj.get('public_GitHub_only')is True and obj.get('messages_sent')==0 and obj.get('new_PDE')==0,
        'Actual successful read-only public feedback snapshot required')
    incoming=[]
    for receipt in obj.get('receipts',[]):
        if receipt.get('pull')!=2 or receipt.get('kind')!='comments':continue
        for row in receipt.get('evidence',[]):
            if row.get('author')!='yoodohyun-codex-cloud':continue
            body=row.get('body');inherited.require(isinstance(body,str)and hashlib.sha256(body.encode()).hexdigest()==row.get('body_sha256'),
                'Public peer body SHA mismatch')
            incoming.append(dict(id=row['id'],body_SHA256=row['body_sha256'],url=row.get('html_url')))
    inherited.require({6320375305,6321929825}<={row['id']for row in incoming},'Current peer feedback including6321929825 required')
    return dict(path=str(path),SHA256=digest,observed_utc=obj['observed_utc'],incoming_sources=incoming,
        peer_specific_tangential_endorsement_inferred=False)


def make_preregistration(output,*,root=ROOT,decision_path,feedback_path):
    root,output=Path(root).resolve(),Path(output)
    inherited.require(output.is_absolute()and output==output.resolve()and output.is_relative_to(root/'docs')and
        output.name.endswith('-plan.json')and output.parent.is_dir()and not output.exists()and not output.is_symlink(),
        'New canonical docs -plan.json path required')
    commit,refs=_committed_sources(root);ledger=inherited.policy.load_ledger(root/'runtime/task1-budget.json')
    inherited.require(inherited.policy.effective_limit(ledger)==13800,'Validated13800s policy required');refs.update(inherited.policy.policy_refs(ledger))
    template=root/inherited.TEMPLATE;inherited._pin(template,refs,root);plan=copy.deepcopy(inherited.read(template))
    for path,digest in plan.get('frozen_definition_source_refs',{}).items():inherited._pin(Path(path),refs,root,digest)
    cases=[];pres=[];configs=[];originals=[]
    for index,(run,ident)in enumerate(CASE_TABLE):
        item,pre=inherited._case(root,run,ident,refs);original=next(c for c in pre['cases']if c['id']==ident)
        config=inherited._properties(Path(original['config_file']));_validate_family(item,pre,config,index)
        style._validate_probe40(item,refs,root)
        cases.append(item);pres.append(pre);configs.append(config);originals.append(original)
    inherited.require(len({c['comparison_signature']for c in cases})==1,'All three grid/material/contact/ROI cohorts must match')
    validate_translation_configs(configs[1],configs[2])
    validate_translation_provenance(originals[1],originals[2])
    decision_path,feedback_path=Path(decision_path),Path(feedback_path)
    decision_sha=inherited._pin(decision_path,refs,root);decision=inherited.read(decision_path)
    for name,digest in decision.get('input_sha256',{}).items():
        inherited.require(Path(name).suffix in ('.json','.md'),'Root decision evidence must remain metadata-only')
        inherited._pin(Path(name),refs,root,digest)
    selected=pres[-1].get('root_selection_decision',{})
    inherited.require(selected.get('path')==str(decision_path)and selected.get('SHA256')==decision_sha and
        decision.get('schema')=='task1-tangential-return-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and
        decision.get('case_id')==CASE_ID and decision.get('source_run_id')==PARENT_RUN and decision.get('source_case_id')==PARENT_ID and
        decision.get('return_shift_grid_indices')==INDEX_SHIFTS and decision.get('return_shift_mm')==SHIFTS and
        decision.get('new_centres_mm')==NEW_CENTRES and decision.get('physical_rotation_deg')==0 and
        decision.get('unchanged_physical_pads')==[0,1]and decision.get('moved_physical_pads')==[2,3]and
        decision.get('new_PDE')==1 and decision.get('new_native_RHS')==8 and
        decision.get('independent_outputs')==2 and decision.get('physical_pads')==4 and
        decision.get('fixed_total_area_mm2')==900 and decision.get('expected_minimum_gap_mm')==1.25 and
        decision.get('expected_minimum_gap_XY_cells')==2 and decision.get('candidate_adopted')is False and
        isinstance(decision.get('question'),str)and decision['question'].strip(),'Exact root tangential-return decision binding required')
    feedback=_feedback(feedback_path,refs,root)
    inherited.require(decision.get('feedback')==dict(path=str(feedback_path),SHA256=feedback['SHA256']),
        'Decision must bind the supplied fresh feedback snapshot')
    history=pres[-1].get('source_feedback',{})
    if history.get('path'):inherited._pin(Path(history['path']),refs,root,history.get('SHA256'))
    baseline=cases[0]
    for case in cases:case.update(baseline_case_id=baseline['case_id'],baseline_summary_path=baseline['summary'],baseline_summary_sha256=baseline['summary_sha256'])
    plan.update(created_utc=datetime.now(timezone.utc).isoformat(),status='preregistered_not_executed',initial_case_count=3,cases=cases,
        baseline_case_id=baseline['case_id'],baseline_case_ids=[baseline['case_id']],baseline_summary_paths=[baseline['summary']],input_sha256=refs,
        purpose='Compare original square, cached unrotated asymmetric parent and two tangentially translated GND returns',
        continuation_batch_kind='tangential_return_cached_volume_audit',
        normalization_baseline_selection='Original nominalRs500 four-square baseline only; asymmetric parent remains a comparison control',
        new_feedback_context=dict(phase='tangential_return_translation',source=feedback,inherited_source_feedback_context=history,
            original_S1_audit_schema_retained=True,root_selection=dict(path=str(decision_path),SHA256=decision_sha,question=decision['question']),
            peer_specific_tangential_endorsement_inferred=False,execution_owner='root',actual_volume_audit_started=False),
        geometry_comparison_contract=dict(kind='two_commonGND_return_tangential_translations_from_unrotated_asymmetric_parent',physical_pad_counts=[4]*3,
            independent_outputs_each=2,common_GND_return_nodes_each=1,translated_physical_pad_ids=[2,3],physical_rotation_deg=0,
            return_shift_grid_indices=INDEX_SHIFTS,return_shift_mm=SHIFTS,parent_centres_mm=PARENT_CENTRES,new_centres_mm=NEW_CENTRES,
            unchanged_physical_pad_ids=[0,1],physical_total_area_mm2=900.,minimum_gap_mm=1.25,minimum_gap_XY_cells=2,
            gap_resolution_status='Two XY cells only; SC/XY/bulk/edge/contact convergence and adoption remain held',
            fixed_drive='Original phase0/0 square3h four spectral lines; dose normalization remains separate in five modes',
            candidate_adopted=False,full_convergence_validated=False),
        frozen_source_validation=dict(scope='Inherited strict frozen-source and original terminal receipt validation without rewrites',
            manifests=[c['frozen_source_manifest']for c in cases]),implementation_source_commit=commit,resource_policy_immutable_refs=inherited.policy.policy_refs(ledger))
    plan['resources'].update(cumulative_budget_limit_seconds=13800,observed_spent_seconds=ledger['spent_seconds'],observed_remaining_seconds=inherited.policy.remaining_seconds(ledger),
        native_scalar_cell_cache_sum=3*351680,conservative_cached_native_bytes_estimate=3*351680*256,
        estimated_cached_plus_overhead_bytes=3*351680*256+512*1024**2,nonbaseline_case_count=2,
        budget_policy='Validated approved13800s policy; charge actual audit time; no automatic expansion')
    argv=['python',str(root/'tools/task1_volume_selectivity.py'),'--preregistration',str(output),'--baseline-summary',baseline['summary']]
    for case in cases:argv+=['--summary',case['summary']]
    plan['resume_command_argv']=argv+['--output',str(output.with_name(output.stem.removesuffix('-plan')+'.json'))]
    plan['metadata_registration_scope'].update(native_E_phi_array_reads=False,native_grid_array_reads=False,volume_NPZ_decode_or_byte_read=False,new_ROI_or_normalization_calculation=False)
    final_commit,final_sources=_committed_sources(root)
    inherited.require(final_commit==commit and all(refs.get(p)==digest for p,digest in final_sources.items()),'Committed implementation changed')
    for path,digest in refs.items():
        if Path(path).name not in ('volume.npz','grid.csv','grid.csv.gz'):inherited.require(inherited.sha(path)==digest,'Consumed metadata changed: '+path)
    with output.open('x')as stream:json.dump(plan,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','decision','feedback'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();plan=make_preregistration(args.output,decision_path=args.decision,feedback_path=args.feedback)
    print(json.dumps(dict(status=plan['status'],case_ids=[c['case_id']for c in plan['cases']],actual_audit_started=False,resume_command_argv=plan['resume_command_argv'])))

if __name__=='__main__':main()
