"""Register three completed saved volumes for one rigid inward translation.

Import and metadata registration do not decode native grids, NPZ or PDE arrays.
The square remains the sole normalization baseline; the shell is the placement
control. Neither the source contour nor any original evidence is rewritten.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess

try:
    import task1_perimeter_shell_volume_registration as shell
except ModuleNotFoundError as error:
    if error.name!='task1_perimeter_shell_volume_registration':raise
    from tools import task1_perimeter_shell_volume_registration as shell

inherited=shell.inherited
ROOT=Path(__file__).resolve().parents[1]
NEW_RUN='cloud-perimeter-inward-20261021T194000Z'
CASE_ID='perimeter-shell225-inward0p625-xy80'
PARENT_RUN=shell.NEW_RUN
PARENT_ID=shell.CASE_ID
CASE_TABLE=(inherited.CASE_TABLE[0],(PARENT_RUN,PARENT_ID),(NEW_RUN,CASE_ID))
SOURCES=('tools/task1_perimeter_inward_volume_registration.py','tests/test_task1_perimeter_inward_volume_registration.py',
    'tools/task1_perimeter_inward_registration.py','tests/test_task1_perimeter_inward_registration.py',*shell.SOURCES)
TRANSLATIONS=((.625,.625),(-.625,-.625),(-.625,.625),(.625,-.625))
ALLOWED_CONFIG_CHANGES={'mask.path','mask.sha256'}|{f'pad.{p}.{key}'for p in range(4)for key in ('x_mm','y_mm')}
RIM_RADIUS_SQUARED=583.203125
RIM_CLEARANCE=25.-math.sqrt(RIM_RADIUS_SQUARED)


def _committed_sources(root):
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();refs={}
    for name in dict.fromkeys(SOURCES):
        path=inherited._regular(root/name,root)
        inherited.require(subprocess.check_output(['git','show',commit+':'+name],cwd=root)==path.read_bytes(),
            'Commit consumed implementation/helpers/tests before registration: '+name)
        refs[str(path)]=inherited.sha(path)
    return commit,refs


def validate_inward_configs(parent,current,design):
    inherited.require(parent.keys()==current.keys()and all(parent[k]==current[k]for k in parent if k not in ALLOWED_CONFIG_CHANGES),
        'Only native mask path/SHA and eight physical centroid coordinates may change')
    for p,(dx,dy)in enumerate(TRANSLATIONS):
        for axis,delta in (('x_mm',dx),('y_mm',dy)):
            key=f'pad.{p}.{axis}';index=0 if axis=='x_mm'else 1
            inherited.require(math.isclose(float(current[key]),float(parent[key])+delta,rel_tol=0,abs_tol=1e-12)and
                math.isclose(float(current[key]),design['pads'][p]['center_mm'][index],rel_tol=0,abs_tol=1e-12),
                'Exact0.625mm inward translation of every physical pad required')
    inherited.require(parent['mask.sha256']!=current['mask.sha256'],'Translated contact indices must have a distinct mask SHA')


def validate_inward_provenance(parent,current,proof):
    """Check exact registered metadata translations, without reconstructing masks."""
    for record in (current,current['design'],proof):
        inherited.require(record.get('geometry_kind')=='fixed_native_face_union'and record.get('native_full_face_contact')is True and
            record.get('physical_total_contact_area_mm2')==900. and record.get('minimum_physical_gap_mm')==2.5 and
            record.get('minimum_gap_XY_cells')==4 and record.get('maximum_physical_vertex_radius_squared_mm2')==RIM_RADIUS_SQUARED and
            math.isclose(record.get('rim_clearance_mm',-1),RIM_CLEARANCE,rel_tol=0,abs_tol=1e-12)and
            record.get('physical_geometry_frozen')is True and record.get('future_grid_reranking_allowed')is False and
            record.get('position_only_contrast')is True and record.get('translated_parent_outline')is True and
            record.get('placement_offset_per_coordinate_mm')==.625 and
            record.get('physical_translation_mm_by_pad')==[list(v)for v in TRANSLATIONS]and
            record.get('source_parent_case_id')==PARENT_ID,
            'Fixed parent outline, exact translation, areas/gaps and rim-clearance provenance required')
    for record in (current,current['design']):
        inherited.require(record.get('combined_geometry_and_placement')is False and record.get('new_geometry_shape_unchanged')is True and
            record.get('placement_and_gap_jointly_changed')is True and record.get('isolated_rim_effect_claimed')is False and
            record.get('isolated_shape_effect_claimed')is False,'Placement and gap change together; no isolated shape or rim effect claim')
    a,b=parent['design'],current['design']
    inherited.require(len(a.get('pads',[]))==len(b.get('pads',[]))==4 and b.get('minimum_gap_mm')==2.5,
        'Four fixed physical outlines and2.5mm minimum physical gap required')
    frozen=('pad','shape','geometry_primitive','width_mm','height_mm','rotation_deg','area_mm2','analytic_area_mm2',
        'polygon_area_mm2','dimension_fields_role','role','source_output','indexed_pair','native_face_h_mm',
        'native_face_lower_corner_origin_mm','native_face_count','physical_outline_frozen','smooth_annular_arc_claimed','convex_hull_used')
    for p,(old,new,(dx,dy))in enumerate(zip(a['pads'],b['pads'],TRANSLATIONS)):
        inherited.require(all(new.get(k)==old[k]for k in frozen if k in old),'Pad dimensions, contour semantics, area, identity or wiring changed')
        for key in ('center_mm','centroid_mm','bounding_box_center_mm'):
            if key in old:
                inherited.require(len(new.get(key,[]))==2 and all(math.isclose(v,u+d,rel_tol=0,abs_tol=1e-12)
                    for v,u,d in zip(new[key],old[key],(dx,dy))),'Physical centroid/bounding-box centre did not translate exactly')
        if 'bounding_box_mm'in old:
            inherited.require(new.get('bounding_box_mm')==[u+d for u,d in zip(old['bounding_box_mm'],(dx,dy,dx,dy))],
                'Physical bounding-box edges must translate rigidly')
        for key in ('polygon_mm','boundary_loops_mm'):
            if key in old:
                expected=([[x+dx,y+dy]for x,y in old[key]]if key=='polygon_mm'else
                    [[[x+dx,y+dy]for x,y in loop]for loop in old[key]])
                inherited.require(new.get(key)==expected,'Physical parent boundary loops changed beyond rigid translation')
        sx,sy=round(dx/.625),round(dy/.625)
        expected=sorted([[i+sx,j+sy]for i,j in old['native_face_indices']],key=lambda q:(q[1],q[0]))
        inherited.require(new.get('native_face_indices')==expected and len(expected)==576 and
            len({tuple(q)for q in expected})==576 and all(0<=i<80 and 0<=j<80 for i,j in expected),
            'Exactly576 original full faces per pad must shift by one native index without reranking')
        if 'union_rectangles_mm'in old:
            rectangles=copy.deepcopy(old['union_rectangles_mm'])
            for rectangle in rectangles:rectangle['center_mm']=[rectangle['center_mm'][0]+dx,rectangle['center_mm'][1]+dy]
            inherited.require(new.get('union_rectangles_mm')==rectangles,'Frozen physical face primitives must translate rigidly')
    inherited.require(proof.get('faces_per_pad')==[576]*4 and proof.get('contacts')==2304 and
        proof.get('components_per_pad')==[1]*4 and proof.get('holes_per_pad')==[0]*4 and
        proof.get('partial_faces')==0 and proof.get('clipping')is False and proof.get('renormalization')is False and
        len(proof.get('represented_pad_areas_m2',[]))==4 and all(math.isclose(a,.000225,rel_tol=1e-12,abs_tol=1e-16)
            for a in proof['represented_pad_areas_m2']),'Full native area, connectedness and no-hole/no-clipping proof required')


def make_preregistration(output,*,root=ROOT,decision_path,feedback_path):
    root,output=Path(root).resolve(),Path(output)
    inherited.require(output.is_absolute()and output==output.resolve()and output.is_relative_to(root/'docs')and
        output.name.endswith('-plan.json')and output.parent.is_dir()and not output.exists()and not output.is_symlink(),
        'New canonical docs -plan.json path required')
    commit,refs=_committed_sources(root);ledger=inherited.policy.load_ledger(root/'runtime/task1-budget.json')
    inherited.require(inherited.policy.effective_limit(ledger)==13800,'Validated13800s policy required')
    refs.update(inherited.policy.policy_refs(ledger));template=root/inherited.TEMPLATE;inherited._pin(template,refs,root)
    plan=copy.deepcopy(inherited.read(template))
    for path,digest in plan.get('frozen_definition_source_refs',{}).items():inherited._pin(Path(path),refs,root,digest)
    cases=[];pres=[];configs=[];originals=[]
    for index,(run,ident)in enumerate(CASE_TABLE):
        item,pre=inherited._case(root,run,ident,refs);original=next(c for c in pre['cases']if c['id']==ident)
        config=inherited._properties(Path(original['config_file']));shell._validate_family(item,pre,config,index)
        shell.style._validate_probe40(item,refs,root)
        cases.append(item);pres.append(pre);configs.append(config);originals.append(original)
    inherited.require(len({c['comparison_signature']for c in cases})==1,'All three grid/material/contact/ROI cohorts must match')
    proofs=[];proof_refs=[]
    for run,pre in ((PARENT_RUN,pres[1]),(NEW_RUN,pres[2])):
        path=root/'data-native'/run/'geometry-audit/perimeter-mask-proof.json'
        expected=pre['source_and_input_sha256'].get(str(path));inherited.require(isinstance(expected,str),'Registered geometry-proof SHA required')
        inherited._pin(path,refs,root,expected);proofs.append(inherited.read(path));proof_refs.append(dict(path=str(path),SHA256=expected))
    shell.validate_shell_provenance(originals[1],proofs[0]);shell.validate_shell_configs(configs[0],configs[1],originals[1]['design'])
    validate_inward_provenance(originals[1],originals[2],proofs[1]);validate_inward_configs(configs[1],configs[2],originals[2]['design'])
    decision_path,feedback_path=Path(decision_path),Path(feedback_path)
    decision_sha=inherited._pin(decision_path,refs,root);decision=inherited.read(decision_path)
    for name,digest in decision.get('input_sha256',{}).items():
        inherited.require(Path(name).suffix in ('.json','.md'),'Root decision evidence must remain metadata-only')
        inherited._pin(Path(name),refs,root,digest)
    selected=pres[-1].get('root_selection_decision',{})
    inherited.require(selected.get('path')==str(decision_path)and selected.get('SHA256')==decision_sha and
        decision.get('schema')=='task1-perimeter-inward-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and decision.get('case_id')==CASE_ID and
        decision.get('source_run_id')==PARENT_RUN and decision.get('source_case_id')==PARENT_ID and decision.get('new_PDE')==1 and
        decision.get('new_native_RHS')==8 and decision.get('independent_outputs')==2 and decision.get('physical_pads')==4 and
        decision.get('fixed_total_area_mm2')==900 and decision.get('placement_offset_per_coordinate_mm')==.625 and
        decision.get('candidate_adopted')is False and isinstance(decision.get('question'),str)and decision['question'].strip(),
        'Exact root-selected one-condition inward placement decision binding required')
    feedback=shell._feedback(feedback_path,refs,root)
    inherited.require(decision.get('feedback')==dict(path=str(feedback_path),SHA256=feedback['SHA256']),
        'Decision must bind the supplied explicit fresh feedback snapshot')
    optimization=pres[-1].get('optimization_context')
    inherited.require(isinstance(optimization,dict)and optimization.get('path')and optimization.get('SHA256'),
        'Completed source optimization context pin required')
    op=Path(optimization['path']);inherited._pin(op,refs,root,optimization['SHA256']);opt=inherited.read(op)
    inherited.require(optimization==decision.get('optimization_result')and
        decision.get('input_sha256',{}).get(str(op))==optimization['SHA256']and
        opt.get('schema')=='task1-perimeter-drive-optimization-v1'and opt.get('status')=='calculated_unadopted'and
        opt.get('inputs_unchanged')is True and opt.get('new_PDE')==0 and opt.get('candidate_adopted')is False and
        opt.get('global_optimum_claimed')is False and opt.get('source_geometry',{}).get('source_case_id')==PARENT_ID and
        opt.get('source_geometry',{}).get('source_run_id')==PARENT_RUN and
        not any(c.get('canonical_screen_all_passed')is True for c in opt.get('conditions',[])),
        'Source optimization must be terminal and unchanged; it is not a new optimization or adoption')
    history=pres[-1].get('source_feedback',{})
    if history.get('path'):inherited._pin(Path(history['path']),refs,root,history.get('SHA256'))
    baseline=cases[0]
    for case in cases:case.update(baseline_case_id=baseline['case_id'],baseline_summary_path=baseline['summary'],baseline_summary_sha256=baseline['summary_sha256'])
    plan.update(created_utc=datetime.now(timezone.utc).isoformat(),status='preregistered_not_executed',initial_case_count=3,cases=cases,
        baseline_case_id=baseline['case_id'],baseline_case_ids=[baseline['case_id']],baseline_summary_paths=[baseline['summary']],input_sha256=refs,
        purpose='Compare original square, cached fixed shell and the same shell translated0.625mm inward per coordinate',
        continuation_batch_kind='perimeter_inward_rigid_translation_cached_volume_audit',
        normalization_baseline_selection='Original nominalRs500 four-square only; cached shell is a placement control',
        new_feedback_context=dict(phase='perimeter_inward_rigid_placement',source=feedback,root_selection=dict(path=str(decision_path),SHA256=decision_sha),
            optimization_context=optimization,peer_specific_inward_geometry_endorsement_inferred=False,execution_owner='root',actual_volume_audit_started=False),
        geometry_comparison_contract=dict(kind='rigid_translation_of_frozen_native_face_union',physical_pad_counts=[4,4,4],independent_outputs_each=2,
            common_GND_return_nodes_each=1,physical_total_area_mm2=900.,native_faces_each_pad=576,area_mm2_each_pad=225.,
            geometry_proofs=proof_refs,physical_translation_mm_by_pad=[list(v)for v in TRANSLATIONS],placement_offset_per_coordinate_mm=.625,
            position_only_contrast=True,new_geometry_shape_unchanged=True,placement_and_gap_jointly_changed=True,
            isolated_rim_effect_claimed=False,isolated_shape_effect_claimed=False,minimum_gap_mm=2.5,minimum_gap_XY_cells=4,
            maximum_physical_vertex_radius_squared_mm2=RIM_RADIUS_SQUARED,rim_clearance_mm=RIM_CLEARANCE,
            physical_geometry_frozen=True,future_grid_reranking_allowed=False,partial_contact_faces=0,candidate_adopted=False,
            full_convergence_validated=False,convergence_hold='Rigid placement changes gap andrim clearance together; all XY/SC/bulk/edge/contact holds remain'),
        frozen_source_validation=dict(manifests=[c['frozen_source_manifest']for c in cases]),implementation_source_commit=commit,
        resource_policy_immutable_refs=inherited.policy.policy_refs(ledger))
    plan['resources'].update(cumulative_budget_limit_seconds=13800,observed_spent_seconds=ledger['spent_seconds'],observed_remaining_seconds=inherited.policy.remaining_seconds(ledger),
        native_scalar_cell_cache_sum=3*351680,conservative_cached_native_bytes_estimate=3*351680*256,
        estimated_cached_plus_overhead_bytes=3*351680*256+512*1024**2,nonbaseline_case_count=2)
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
