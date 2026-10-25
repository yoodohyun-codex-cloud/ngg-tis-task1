"""Record finite native-batch resource admission; never starts a solver."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import time
import task1_bounded_continuation as q
import task1_resource_policy as policy
ROOT=Path(__file__).resolve().parents[1]
RAW_BOUND_BYTES=361728*600
POST_RESERVE_BYTES=128*1024**2
BUDGET_RESERVE_SECONDS=1320

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output
    q.require(out.is_absolute()and out==out.resolve()and out.is_relative_to(ROOT/'docs')and not out.exists()and out.parent.is_dir(),'Unique canonical docs output required')
    with q.dual_lock(ROOT/'.task1-loop.lock'),q.dual_lock(ROOT/'.task1-execution.lock'):
        started=time.monotonic();budget=policy.load_ledger();remaining=policy.remaining_seconds(budget)
        free=shutil.disk_usage(ROOT).free;required=2*q.GIB+RAW_BOUND_BYTES+POST_RESERVE_BYTES;reasons=[]
        if free<required:reasons.append('disk_reserve_for_next_fine_native_and_postprocessing')
        if remaining<BUDGET_RESERVE_SECONDS:reasons.append('remaining_approved_time')
        controls=[]
        for name in ('cloud-rounded-sc4-20261021T204000Z','cloud-rounded-contact-20261021T210000Z'):
            c=q.read(ROOT/'data-native'/name/'controller.json');controls.append(dict(run_id=name,status=c['status'],last_pid=c.get('pid'),last_startticks=c.get('proc_start_ticks'),live=q.live(c['pid'],c['proc_start_ticks'])))
        if any(c['live']for c in controls):reasons.append('recorded_native_process_still_live')
        value=dict(schema='task1-next-fine-native-admission-v1',status='blocked_for_next_fine_native_batch'if reasons else'resources_available_registration_still_required',observed_utc=q.now(),blockers=reasons,
            source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),numerical_worker_started=False,prior_native_controllers=controls,
            filesystem=dict(free_bytes=free,reserve_bytes=2*q.GIB,next_SC4_basis_cells=361728,conservative_native_bound_bytes=RAW_BOUND_BYTES,postprocessing_reserve_bytes=POST_RESERVE_BYTES,required_free_bytes=required,deficit_bytes=max(0,required-free),original_or_failure_data_deleted=False,full_raw_persistent_backup_verified=False),
            budget=dict(approved_limit_seconds=policy.effective_limit(budget),remaining_seconds_before_check=remaining,next_finite_batch_reserve_seconds=BUDGET_RESERVE_SECONDS,expanded=False),
            next_scientific_question='Keep the physical rounded polygon, top-only geometry, original SC2 caps and true source topology fixed; select next XY/bulk/edge or contact diagnostic after resources permit. No coarse-grid reranking to bypass a fine-grid storage gate.',
            resume_condition='Both locks free; at least required_free_bytes available without deleting original/failure evidence; remaining approved time>=1320s; new uniquely preregistered finite batch and current feedback review. This check alone does not register or execute a PDE.',
            next_inspection_command='python tools/task1_native_resume_preflight.py --output '+str(out.with_name(out.stem+'-next.json')),
            current_completed_evidence=['docs/cloud-rounded-contact-sensitivity-20261021T210000Z/summary.json','docs/cloud-rounded-single-pair-20261021T212000Z/summary.json','docs/cloud-rounded-contact-native-maps-20261021T211000Z-v2/summary.json'],new_PDE=0,candidate_adopted=False)
        elapsed=time.monotonic()-started;budget['spent_seconds']+=elapsed;budget['runs'].append(dict(run_id=out.stem,stage='next_fine_native_resource_preflight',seconds=elapsed,status=value['status'],finished_utc=q.now()));q.write(ROOT/'runtime/task1-budget.json',budget);value['budget']['remaining_seconds_after_check']=policy.remaining_seconds(budget);q.write(out,value);print(json.dumps(dict(status=value['status'],blockers=reasons,deficit_bytes=value['filesystem']['deficit_bytes'],remaining_seconds=policy.remaining_seconds(budget))))
if __name__=='__main__':main()
