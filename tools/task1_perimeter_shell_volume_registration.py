"""Register completed square/perimeter native-face-union volumes only."""
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
NEW_RUN='cloud-perimeter-shell-20261021T185000Z'
CASE_ID='perimeter-shell225-notch-xy80'
PARENT_RUN='cloud-mesh-c1-20261019T190000Z'
PARENT_ID='baseline-square15-xy80'
CASE_TABLE=(inherited.CASE_TABLE[0],(NEW_RUN,CASE_ID))
SOURCES=('tools/task1_perimeter_shell_volume_registration.py','tests/test_task1_perimeter_shell_volume_registration.py',
    'tools/task1_perimeter_shell_registration.py','tests/test_task1_perimeter_shell_registration.py',*style.SOURCES)
ALLOWED_CONFIG_CHANGES={'mask.path','mask.sha256'}|{f'pad.{p}.{k}'for p in range(4)
    for k in ('shape','width_mm','height_mm','x_mm','y_mm')}
CENTROID=13.638237847222221
SIGNS=((-1,-1),(1,1),(1,-1),(-1,1))
RIM_RADIUS_SQUARED=623.828125
RIM_CLEARANCE=25.-math.sqrt(RIM_RADIUS_SQUARED)


def _committed_sources(root):
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();refs={}
    for name in dict.fromkeys(SOURCES):
        path=inherited._regular(root/name,root)
        inherited.require(subprocess.check_output(['git','show',commit+':'+name],cwd=root)==path.read_bytes(),
            'Commit consumed implementation/helpers/tests before registration: '+name)
        refs[str(path)]=inherited.sha(path)
    return commit,refs


def validate_shell_configs(parent,current,design):
    inherited.require(parent.keys()==current.keys()and all(parent[k]==current[k]for k in parent if k not in ALLOWED_CONFIG_CHANGES),
        'Only mask and honest pad-shape/bounding-box/centroid descriptors may change')
    for p,(sx,sy)in enumerate(SIGNS):
        prefix=f'pad.{p}.';pad=design['pads'][p]
        inherited.require(parent[prefix+'shape']=='rectangle'and current[prefix+'shape']=='masked_face_union'and
            float(parent[prefix+'width_mm'])==float(parent[prefix+'height_mm'])==15. and
            float(current[prefix+'width_mm'])==float(current[prefix+'height_mm'])==22.5 and
            float(parent[prefix+'rotation_deg'])==float(current[prefix+'rotation_deg'])==0. and
            math.isclose(float(current[prefix+'x_mm']),pad['center_mm'][0],rel_tol=0,abs_tol=1e-12)and
            math.isclose(float(current[prefix+'y_mm']),pad['center_mm'][1],rel_tol=0,abs_tol=1e-12)and
            math.isclose(float(current[prefix+'x_mm']),sx*CENTROID,rel_tol=0,abs_tol=1e-12)and
            math.isclose(float(current[prefix+'y_mm']),sy*CENTROID,rel_tol=0,abs_tol=1e-12),
            'Fixed native-face union descriptor, actual area-centroid and zero operative rotation required')
    inherited.require(parent['mask.sha256']!=current['mask.sha256'],'Shell union must have a distinct physical contact mask')


def validate_shell_provenance(case,proof):
    design=case['design']
    for record in (case,design):
        inherited.require(record.get('geometry_kind')=='fixed_native_face_union'and record.get('combined_geometry_and_placement')is True and
            record.get('isolated_shape_effect_claimed')is False and record.get('native_full_face_contact')is True and
            record.get('physical_total_contact_area_mm2')==900. and record.get('minimum_physical_gap_mm')==3.75 and
            record.get('minimum_gap_XY_cells')==6 and record.get('maximum_physical_vertex_radius_squared_mm2')==RIM_RADIUS_SQUARED and
            math.isclose(record.get('rim_clearance_mm',-1),RIM_CLEARANCE,rel_tol=0,abs_tol=1e-12),
            'Explicit fixed full-face union, combined geometry/placement and near-rim hold metadata required')
    inherited.require(design.get('minimum_gap_mm')==3.75 and len(design.get('pads',[]))==4,
        'Four physical shell pads and fixed3.75mm gap required')
    for p,(sx,sy)in enumerate(SIGNS):
        pad=design['pads'][p];faces=pad.get('native_face_indices',[]);loops=pad.get('boundary_loops_mm',[])
        inherited.require(pad.get('pad')==p and pad.get('shape')=='masked_face_union'and
            pad.get('geometry_primitive')=='fixed_union_of_native_full_face_rectangles'and pad.get('rotation_deg')==0 and
            pad.get('width_mm')==pad.get('height_mm')==22.5 and
            pad.get('bounding_box_center_mm')==[sx*13.125,sy*13.125]and
            len(pad.get('center_mm',[]))==2 and all(math.isclose(v,sgn*CENTROID,rel_tol=0,abs_tol=1e-12)
                for v,sgn in zip(pad['center_mm'],(sx,sy)))and
            all(pad.get(k)==225. for k in ('area_mm2','analytic_area_mm2','polygon_area_mm2'))and
            isinstance(pad.get('dimension_fields_role'),str)and bool(pad['dimension_fields_role'].strip()),
            'Honest face-union225mm2 area/centroid/bounding-box metadata required')
        inherited.require(len(faces)==576 and all(isinstance(q,list)and len(q)==2 and all(type(v)is int and 0<=v<80 for v in q)for q in faces)and
            len({tuple(q)for q in faces})==576 and faces==sorted(faces,key=lambda q:(q[1],q[0]))and
            isinstance(loops,list)and len(loops)==1 and isinstance(loops[0],list)and len(loops[0])>=4 and
            all(isinstance(q,list)and len(q)==2 and all(type(v)in(int,float)and math.isfinite(v)for v in q)for q in loops[0]),
            'Exactly576 unique full native faces and one explicit boundary loop required; no smooth arc inferred')
    inherited.require(proof.get('faces_per_pad')==[576]*4 and proof.get('components_per_pad')==[1]*4 and proof.get('holes_per_pad')==[0]*4 and
        proof.get('partial_faces')==0 and proof.get('clipping')is False and proof.get('renormalization')is False and
        proof.get('physical_total_contact_area_mm2')==900. and proof.get('minimum_physical_gap_mm')==3.75 and
        proof.get('minimum_gap_XY_cells')==6 and proof.get('maximum_physical_vertex_radius_squared_mm2')==RIM_RADIUS_SQUARED and
        math.isclose(proof.get('rim_clearance_mm',-1),RIM_CLEARANCE,rel_tol=0,abs_tol=1e-12),
        'Pinned native geometry proof must retain full-face counts, connectivity, no holes/clipping and near-rim boundary')


def _validate_family(item,pre,config,index):
    case=next(c for c in pre['cases']if c['id']==item['case_id']);circuit=case['circuit']
    inherited.require(circuit.get('n_pads')==4 and circuit.get('n_outputs')==2 and circuit.get('n_return_nodes')==1 and
        circuit.get('pad_to_node')=={'0':'out0','1':'out1','2':'GND','3':'GND'}and circuit.get('source_resistance_ohm')==50 and
        circuit.get('source_peak_V')==.5 and circuit.get('source_Vpp_each')==1 and
        circuit.get('return_topology')=='all_return_pads_ideal_common_GND'and circuit.get('carrier_assignment_Hz')==[3000,3030]and
        circuit.get('inactive_source_at_other_frequencies','').replace(' ','')=='0Vthrough50ohm',
        'Four actual pads/two outputs/one commonGND/50ohm termination required')
    expected=[225.]*4
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
        peer_specific_perimeter_endorsement_inferred=False)


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
    inherited.require(len({c['comparison_signature']for c in cases})==1,'Both grid/material/contact/ROI cohorts must match')
    proof_path=root/'data-native'/NEW_RUN/'geometry-audit/perimeter-mask-proof.json'
    proof_sha=pres[-1]['source_and_input_sha256'].get(str(proof_path))
    inherited.require(isinstance(proof_sha,str),'Registered perimeter geometry-proof SHA required')
    inherited._pin(proof_path,refs,root,proof_sha);proof=inherited.read(proof_path)
    validate_shell_provenance(originals[1],proof)
    validate_shell_configs(configs[0],configs[1],originals[1]['design'])
    decision_path,feedback_path=Path(decision_path),Path(feedback_path)
    decision_sha=inherited._pin(decision_path,refs,root);decision=inherited.read(decision_path)
    for name,digest in decision.get('input_sha256',{}).items():
        inherited.require(Path(name).suffix in ('.json','.md'),'Root decision evidence must remain metadata-only')
        inherited._pin(Path(name),refs,root,digest)
    selected=pres[-1].get('root_selection_decision',{})
    inherited.require(selected.get('path')==str(decision_path)and selected.get('SHA256')==decision_sha and
        decision.get('schema')=='task1-perimeter-shell-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and
        decision.get('case_id')==CASE_ID and decision.get('source_run_id')==PARENT_RUN and decision.get('source_case_id')==PARENT_ID and
        decision.get('new_PDE')==1 and decision.get('new_native_RHS')==8 and
        decision.get('independent_outputs')==2 and decision.get('physical_pads')==4 and
        decision.get('fixed_total_area_mm2')==900 and decision.get('candidate_adopted')is False and
        isinstance(decision.get('question'),str)and decision['question'].strip(),'Exact root perimeter-shell decision binding required')
    feedback=_feedback(feedback_path,refs,root)
    inherited.require(decision.get('feedback')==dict(path=str(feedback_path),SHA256=feedback['SHA256']),
        'Decision must bind the supplied fresh feedback snapshot')
    history=pres[-1].get('source_feedback',{})
    if history.get('path'):inherited._pin(Path(history['path']),refs,root,history.get('SHA256'))
    baseline=cases[0]
    for case in cases:case.update(baseline_case_id=baseline['case_id'],baseline_summary_path=baseline['summary'],baseline_summary_sha256=baseline['summary_sha256'])
    plan.update(created_utc=datetime.now(timezone.utc).isoformat(),status='preregistered_not_executed',initial_case_count=2,cases=cases,
        baseline_case_id=baseline['case_id'],baseline_case_ids=[baseline['case_id']],baseline_summary_paths=[baseline['summary']],input_sha256=refs,
        purpose='Compare original square with fixed native-face-union perimeter geometry and placement',
        continuation_batch_kind='perimeter_shell_cached_volume_audit',
        normalization_baseline_selection='Original nominalRs500 four-square baseline only; new perimeter geometry is a comparison row',
        new_feedback_context=dict(phase='perimeter_shell_geometry_and_placement',source=feedback,inherited_source_feedback_context=history,
            original_S1_audit_schema_retained=True,root_selection=dict(path=str(decision_path),SHA256=decision_sha,question=decision['question']),
            peer_specific_perimeter_endorsement_inferred=False,execution_owner='root',actual_volume_audit_started=False),
        geometry_comparison_contract=dict(kind='fixed_native_face_union_geometry_and_placement_combined',physical_pad_counts=[4,4],
            independent_outputs_each=2,common_GND_return_nodes_each=1,physical_total_area_mm2=900.,area_mm2_each_pad=225.,
            geometry_proof=dict(path=str(proof_path),SHA256=proof_sha),native_faces_each_pad=576,partial_contact_faces=0,
            minimum_gap_mm=3.75,minimum_gap_XY_cells=6,maximum_physical_vertex_radius_squared_mm2=RIM_RADIUS_SQUARED,
            rim_clearance_mm=RIM_CLEARANCE,combined_geometry_and_placement=True,isolated_shape_effect_claimed=False,
            contour_definition='Fixed union of native full-face rectangles with one explicit boundary; no smooth arc or strict576outermost claim',
            construction_metadata=proof.get('construction'),
            convergence_hold='Near-rim clearance below0.024mm and native staircase contour require independent XY/SC/bulk/edge/contact sensitivity; no adoption',
            candidate_adopted=False,full_convergence_validated=False),
        frozen_source_validation=dict(scope='Inherited strict frozen-source and original terminal receipt validation without rewrites',
            manifests=[c['frozen_source_manifest']for c in cases]),implementation_source_commit=commit,resource_policy_immutable_refs=inherited.policy.policy_refs(ledger))
    plan['resources'].update(cumulative_budget_limit_seconds=13800,observed_spent_seconds=ledger['spent_seconds'],observed_remaining_seconds=inherited.policy.remaining_seconds(ledger),
        native_scalar_cell_cache_sum=2*351680,conservative_cached_native_bytes_estimate=2*351680*256,
        estimated_cached_plus_overhead_bytes=2*351680*256+512*1024**2,nonbaseline_case_count=1,
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
