"""Metadata-only registration of cached square and fixed rounded face unions.

No native field, grid or scalar array is decoded during registration. The
original square is the sole burden-normalization baseline. The staircase
outline has a larger perimeter than the square; no smooth-circle or isolated
edge-effect interpretation is attached to this two-geometry comparison.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import importlib
import json
import math
from pathlib import Path
import subprocess
from unittest import mock

try:
    import task1_perimeter_shell_volume_registration as shell
except ModuleNotFoundError as error:
    if error.name!='task1_perimeter_shell_volume_registration':raise
    from tools import task1_perimeter_shell_volume_registration as shell

inherited=shell.inherited
ROOT=Path(__file__).resolve().parents[1]
NEW_RUN='cloud-rounded-fullface-20261021T200000Z'
CASE_ID='rounded-fullface225-xy80'
PARENT_RUN='cloud-mesh-c1-20261019T190000Z'
PARENT_ID='baseline-square15-xy80'
CASE_TABLE=((PARENT_RUN,PARENT_ID),(NEW_RUN,CASE_ID))
SOURCES=('tools/task1_rounded_fullface_volume_registration.py','tests/test_task1_rounded_fullface_volume_registration.py',
    'tools/task1_rounded_fullface_registration.py','tests/test_task1_rounded_fullface_registration.py',*shell.SOURCES)
ALLOWED_CONFIG_CHANGES={'mask.path','mask.sha256'}|{f'pad.{p}.{key}'for p in range(4)for key in ('shape','width_mm','height_mm')}
CENTRES=((-10.,-10.),(10.,10.),(10.,-10.),(-10.,10.))
GEOMETRY_REVISION='rounded-fullface225-odd-r2le730-v1'
RIM_RADIUS_SQUARED=528.90625
RIM_CLEARANCE=25.-math.sqrt(RIM_RADIUS_SQUARED)


def _committed_sources(root):
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();refs={}
    for name in dict.fromkeys(SOURCES):
        path=inherited._regular(root/name,root)
        inherited.require(subprocess.check_output(['git','show',commit+':'+name],cwd=root)==path.read_bytes(),
            'Commit consumed implementation/helpers/tests before registration: '+name)
        refs[str(path)]=inherited.sha(path)
    return commit,refs


def expected_native_faces(pad):
    cx,cy=CENTRES[pad];ix,iy=round((cx+25)/.625),round((cy+25)/.625)
    return [[i,j]for j in range(80)for i in range(80)if (2*(i-ix)+1)**2+(2*(j-iy)+1)**2<=730]


def validate_rounded_configs(parent,current,design):
    inherited.require(parent.keys()==current.keys()and all(parent[k]==current[k]for k in parent if k not in ALLOWED_CONFIG_CHANGES),
        'Only contact mask and honest shape/bounding-box dimensions may change; centres, area and physics stay fixed')
    for p,centre in enumerate(CENTRES):
        prefix=f'pad.{p}.';pad=design['pads'][p]
        inherited.require(parent[prefix+'shape']=='rectangle'and current[prefix+'shape']=='masked_face_union'and
            float(parent[prefix+'width_mm'])==float(parent[prefix+'height_mm'])==15. and
            float(current[prefix+'width_mm'])==float(current[prefix+'height_mm'])==17.5 and
            float(current[prefix+'rotation_deg'])==0. and pad['center_mm']==list(centre)and
            [float(current[prefix+'x_mm']),float(current[prefix+'y_mm'])]==list(centre),
            'Fixed rounded full-face union descriptors and original centres required')
    inherited.require(parent['mask.sha256']!=current['mask.sha256'],'Rounded contour requires a distinct contact mask SHA')


def validate_rounded_provenance(case,proof):
    design=case['design']
    for record in (case,design,proof):
        inherited.require(record.get('geometry_kind')=='fixed_native_face_union'and record.get('geometry_revision')==GEOMETRY_REVISION and
            record.get('native_full_face_contact')is True and record.get('physical_total_contact_area_mm2')==900. and
            record.get('minimum_physical_gap_mm')==2.5 and record.get('minimum_gap_XY_cells')==4 and
            record.get('maximum_physical_vertex_radius_squared_mm2')==RIM_RADIUS_SQUARED and
            math.isclose(record.get('rim_clearance_mm',-1),RIM_CLEARANCE,rel_tol=0,abs_tol=1e-12)and
            record.get('physical_geometry_frozen')is True and record.get('future_grid_reranking_allowed')is False and
            record.get('shape_only_contrast')is True and record.get('centres_unchanged')is True and record.get('area_unchanged')is True and
            record.get('smooth_circle_claimed')is False and record.get('perimeter_reduction_claimed')is False and
            record.get('isolated_edge_effect_claimed')is False and record.get('physical_outline_perimeter_mm_per_pad')==70. and
            record.get('source_square_perimeter_mm_per_pad')==60. and record.get('strict_radial_prefix_face_count')==560 and
            record.get('cutoff_tie_face_count')==16 and record.get('all_cutoff_ties_included')is True and
            record.get('cutoff_local_odd_radius_squared')==730,
            'Fixed rounded union, unchanged centres/area, complete cutoff ties and honest70mm staircase perimeter required')
    inherited.require(len(design.get('pads',[]))==4 and design.get('minimum_gap_mm')==2.5,'Four fixed225mm2 pads and2.5mm gap required')
    for p,centre in enumerate(CENTRES):
        pad=design['pads'][p];loops=pad.get('boundary_loops_mm',[])
        inherited.require(pad.get('pad')==p and pad.get('shape')=='masked_face_union'and
            pad.get('geometry_primitive')=='fixed_union_of_native_full_face_rectangles'and
            pad.get('width_mm')==pad.get('height_mm')==17.5 and pad.get('rotation_deg')==0 and
            pad.get('center_mm')==list(centre)and pad.get('bounding_box_center_mm')==list(centre)and
            all(pad.get(k)==225. for k in ('area_mm2','analytic_area_mm2','polygon_area_mm2'))and
            pad.get('role')==('signal'if p<2 else'common_gnd_return')and pad.get('source_output')==(p if p<2 else None)and
            pad.get('native_face_indices')==expected_native_faces(p)and isinstance(loops,list)and len(loops)==1 and len(loops[0])>=4 and
            all(isinstance(q,list)and len(q)==2 and all(type(v)in(int,float)and math.isfinite(v)for v in q)for q in loops[0]),
            'Exact centred radial576-face set, physical identity/wiring,225mm2 area and one explicit finite boundary required')
    inherited.require(proof.get('faces_per_pad')==[576]*4 and proof.get('components_per_pad')==[1]*4 and
        proof.get('holes_per_pad')==[0]*4 and proof.get('partial_faces')==0 and proof.get('contacts')==2304 and
        proof.get('clipping')is False and proof.get('renormalization')is False and
        len(proof.get('represented_pad_areas_m2',[]))==4 and all(math.isclose(a,.000225,rel_tol=1e-12,abs_tol=1e-16)
            for a in proof['represented_pad_areas_m2']),
        'Pinned native proof must preserve full-face area, connectivity and no holes, clipping or renormalization')


def _context(decision_path,feedback_path,root):
    try:geometry=importlib.import_module('task1_rounded_fullface_registration')
    except ModuleNotFoundError as error:
        if error.name!='task1_rounded_fullface_registration':raise
        geometry=importlib.import_module('tools.task1_rounded_fullface_registration')
    with mock.patch.object(geometry.core,'REPO',root):
        return geometry.verify_context(decision_path,feedback_path)


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
        config=inherited._properties(Path(original['config_file']));shell._validate_family(item,pre,config,index)
        shell.style._validate_probe40(item,refs,root)
        cases.append(item);pres.append(pre);configs.append(config);originals.append(original)
    inherited.require(len({c['comparison_signature']for c in cases})==1,'Both grid/material/contact/ROI cohorts must match')
    proof_path=root/'data-native'/NEW_RUN/'geometry-audit/rounded-mask-proof.json'
    proof_sha=pres[-1]['source_and_input_sha256'].get(str(proof_path));inherited.require(isinstance(proof_sha,str),'Registered rounded geometry-proof SHA required')
    inherited._pin(proof_path,refs,root,proof_sha);proof=inherited.read(proof_path)
    validate_rounded_provenance(originals[1],proof);validate_rounded_configs(configs[0],configs[1],originals[1]['design'])
    decision_path,feedback_path=Path(decision_path),Path(feedback_path)
    decision_sha=inherited._pin(decision_path,refs,root)
    decision_ref,feedback,context_pins=_context(decision_path,feedback_path,root)
    decision=inherited.read(decision_path)
    inherited.require(decision_ref.get('path')==str(decision_path)and decision_ref.get('SHA256')==decision_sha,
        'Main conditional selection receipt must bind the identical root decision')
    for path,digest in context_pins.items():
        inherited.require(Path(path).suffix in ('.json','.md'),'Conditional selection evidence must remain metadata-only')
        inherited._pin(Path(path),refs,root,digest)
    inherited._pin(feedback_path,refs,root,feedback.get('SHA256')or feedback.get('sha256'))
    selected=pres[-1].get('root_selection_decision',{})
    inherited.require(selected.get('path')==str(decision_path)and selected.get('SHA256')==decision_sha and
        decision.get('schema')=='task1-rounded-fullface-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and decision.get('case_id')==CASE_ID and
        decision.get('source_run_id')==PARENT_RUN and decision.get('source_case_id')==PARENT_ID and
        decision.get('new_PDE')==1 and decision.get('new_native_RHS')==8 and decision.get('physical_pads')==4 and
        decision.get('independent_outputs')==2 and decision.get('fixed_total_area_mm2')==900 and decision.get('candidate_adopted')is False,
        'Exact conditional root-selected rounded-shape decision binding required')
    baseline=cases[0]
    for case in cases:case.update(baseline_case_id=baseline['case_id'],baseline_summary_path=baseline['summary'],baseline_summary_sha256=baseline['summary_sha256'])
    plan.update(created_utc=datetime.now(timezone.utc).isoformat(),status='preregistered_not_executed',initial_case_count=2,cases=cases,
        baseline_case_id=baseline['case_id'],baseline_case_ids=[baseline['case_id']],baseline_summary_paths=[baseline['summary']],input_sha256=refs,
        purpose='Compare square and fixed rounded576-face contact at identical centres, area, circuit, grid and material/contact model',
        continuation_batch_kind='rounded_fullface_fixed_shape_cached_volume_audit',
        normalization_baseline_selection='Original nominalRs500 four-square only; rounded face union is a comparison row',
        new_feedback_context=dict(phase='rounded_fullface_shape',source=feedback,root_selection=dict(path=str(decision_path),SHA256=decision_sha),
            inward_volume=decision['inward_volume'],inward_screen=decision['inward_screen'],peer_specific_rounded_geometry_endorsement_inferred=False,
            execution_owner='root',actual_volume_audit_started=False),
        geometry_comparison_contract=dict(kind='fixed_native_face_union_shape_contrast',physical_pad_counts=[4,4],independent_outputs_each=2,
            common_GND_return_nodes_each=1,physical_total_area_mm2=900.,area_mm2_each_pad=225.,native_faces_each_pad=576,partial_contact_faces=0,
            geometry_proof=dict(path=str(proof_path),SHA256=proof_sha),geometry_revision=GEOMETRY_REVISION,shape_only_contrast=True,
            centres_unchanged=True,area_unchanged=True,minimum_gap_mm=2.5,minimum_gap_XY_cells=4,
            maximum_physical_vertex_radius_squared_mm2=RIM_RADIUS_SQUARED,rim_clearance_mm=RIM_CLEARANCE,
            rounded_physical_perimeter_mm_each=70.,square_physical_perimeter_mm_each=60.,smooth_circle_claimed=False,
            perimeter_reduction_claimed=False,isolated_edge_effect_claimed=False,physical_geometry_frozen=True,
            future_grid_reranking_allowed=False,strict_radial_prefix_face_count=560,cutoff_tie_face_count=16,all_cutoff_ties_included=True,
            candidate_adopted=False,full_convergence_validated=False,
            convergence_hold='Native staircase shape retains XY/SC/bulk/edge/contact holds; same-area shape change does not isolate an edge mechanism'),
        frozen_source_validation=dict(manifests=[c['frozen_source_manifest']for c in cases]),implementation_source_commit=commit,
        resource_policy_immutable_refs=inherited.policy.policy_refs(ledger))
    plan['resources'].update(cumulative_budget_limit_seconds=13800,observed_spent_seconds=ledger['spent_seconds'],
        observed_remaining_seconds=inherited.policy.remaining_seconds(ledger),native_scalar_cell_cache_sum=2*351680,
        conservative_cached_native_bytes_estimate=2*351680*256,estimated_cached_plus_overhead_bytes=2*351680*256+512*1024**2,nonbaseline_case_count=1)
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
