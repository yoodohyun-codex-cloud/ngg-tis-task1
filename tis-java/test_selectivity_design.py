"""Failure-before-PDE and byte preservation checks for the finite executor."""
import json
from pathlib import Path
import tempfile
import unittest
from selectivity_design import (check_fresh_run,check_publication,check_pins,check_stop,
                                ExperimentStop,sha,select_candidates,select_champion)

class ExecutionGuards(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.run=Path(self.tmp.name)
        for name in ('cases','bases','postprocess'):(self.run/name).mkdir()
        for name in ('summary.json','controller.json'):(self.run/name).write_text('{"status":"prepared"}\n')
        for name in ('manifest.json','preregistration.json'):(self.run/name).write_text('{}\n')
    def test_no_resume_over_partial_basis_or_case(self):
        for directory in ('cases','bases','postprocess'):
            p=self.run/directory/'partial-original';p.write_bytes(b'preserve\x00failed\n')
            with self.assertRaises(ValueError):check_fresh_run(self.run)
            self.assertEqual(p.read_bytes(),b'preserve\x00failed\n');p.unlink()
    def test_execution_attempt_without_summary_update_blocks_restart(self):
        p=self.run/'execution-attempt.json';p.write_text('{"pid":123}\n')
        with self.assertRaises(ValueError):check_fresh_run(self.run)
        self.assertEqual(p.read_text(),'{"pid":123}\n')
    def test_controller_history_and_failure_block_restart(self):
        (self.run/'controller.json').write_text('{"status":"running"}')
        with self.assertRaises(ValueError):check_fresh_run(self.run)
        (self.run/'controller.json').write_text('{"status":"prepared"}')
        (self.run/'failure.json').write_text('{}')
        with self.assertRaises(ValueError):check_fresh_run(self.run)
    def test_publication_requires_both_exact_namespaces(self):
        receipt=dict(status='published_verified',remote_ref_verified=True,commit_sha='a'*40,
          manifest_sha256=sha(self.run/'manifest.json'),preregistration_sha256=sha(self.run/'preregistration.json'))
        check_publication(self.run,receipt)
        for key in ('manifest_sha256','preregistration_sha256','commit_sha','status','remote_ref_verified'):
            bad=dict(receipt);bad[key]=False if key=='remote_ref_verified' else 'wrong'
            with self.assertRaises(ValueError):check_publication(self.run,bad)
    def test_input_mutation_is_not_refrozen(self):
        p=self.run/'input';p.write_bytes(b'old');pins={str(p):sha(p)};check_pins(pins)
        p.write_bytes(b'changed')
        with self.assertRaises(ValueError):check_pins(pins)
        self.assertEqual(p.read_bytes(),b'changed')
    def test_stop_and_hold_are_preserved(self):
        for marker in ('STOP','needs_attention','needs_physical_validation'):
            p=self.run/marker;p.write_text('user')
            with self.assertRaises(ExperimentStop):check_stop(self.run)
            self.assertEqual(p.read_text(),'user');p.unlink()
    def test_zero_field_does_not_win_on_absolute_objective(self):
        def r(p10,mean,ratio,j,power):return dict(selection_metrics=dict(roi_p10_TIS_V_m=p10,roi_mean_TIS_V_m=mean,target_superficial_p95_ratio=ratio,surface_J_RMS_max_A_m2=j,source_power_W=power))
        result={'strong-coarse':r(2,3,.1,4,1),'ratio-coarse':r(.01,.01,99,.01,.01),'baseline-square15-coarse':r(1,1,.1,1,1)}
        chosen=select_candidates(result,list(result));self.assertEqual(chosen[0],'strong')
        refined={'baseline-square15-xy80':r(1,1,.1,1,1),'strong-xy80':r(2,3,.1,4,1),'ratio-xy80':r(.01,.01,99,.01,.01)}
        self.assertEqual(select_champion(refined,chosen),'strong')
if __name__=='__main__':unittest.main()
