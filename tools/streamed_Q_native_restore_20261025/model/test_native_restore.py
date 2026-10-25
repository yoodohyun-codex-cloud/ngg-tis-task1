"""Prospective manufactured preconditions; no real native response or Q."""
import unittest
from unittest.mock import patch
from pathlib import Path
import native_restore as subject
import fine_solver
import streamed_real_q

class CachedRestorePreconditions(unittest.TestCase):
    def mask(self,areas=None,overlap=False):
        rows=['pad,i,j,area_m2'];areas=areas or [.000225]*4
        xy=[(0,0),(1,0),(0,1),(1,1)]
        if overlap:xy[1]=xy[0]
        for pad,((i,j),area)in enumerate(zip(xy,areas)):
            rows.append('%d,%d,%d,%.17e'%(pad,i,j,area))
        return ('\n'.join(rows)+'\n').encode()
    def test_manufactured_area_closure_is_verified_without_rescaling(self):
        import numpy as np
        ij=np.asarray([(0,0),(1,0),(0,1),(1,1)],np.int32)
        pads,cells,areas=subject.contacts(np,self.mask(),ij,.015)
        self.assertEqual(pads.tolist(),[0,1,2,3]);self.assertEqual(cells.tolist(),[0,1,2,3])
        self.assertTrue(np.all(areas==.000225))
    def test_overlap_or_non225_area_blocks_instead_of_repair(self):
        import numpy as np
        ij=np.asarray([(0,0),(1,0),(0,1),(1,1)],np.int32)
        with self.assertRaises(ValueError):subject.contacts(np,self.mask(overlap=True),ij,.015)
        with self.assertRaises(ValueError):subject.contacts(np,self.mask([.000224,.000225,.000225,.000225]),ij,.015)
    def test_missing_cached_response_cannot_call_solver_or_start_fallback(self):
        with patch.object(fine_solver,'solve',side_effect=AssertionError('No solve allowed'))as solver:
            with self.assertRaises(ValueError):
                subject.cached_gate(None,None,None,None,None,None,None,0,.015,None,lambda:None,None)
            solver.assert_not_called()
    def test_signed_power_comparison_retains_near_zero_floor_and_failure(self):
        self.assertTrue(subject.power_comparison(1.-2.j,1.-2.j,2e-7,1e-12)['passed'])
        near=subject.power_comparison(1e-20j,0j,2e-7,1e-12)
        self.assertTrue(near['passed']);self.assertEqual(near['relative_denominator_W'],1e-12)
        self.assertFalse(subject.power_comparison(1.001-2.j,1.-2.j,2e-7,1e-12)['passed'])
    def test_failed_operation_still_preserves_closed_operator_audit_without_native_IO(self):
        captured=[]
        class ManufacturedOperator:
            def __init__(self,*args,**kwargs):self.closed=False
            def __enter__(self):return self
            def __exit__(self,*args):self.closed=True
            def receipt(self):return dict(closed=self.closed,whole_Q_loaded=False,manufactured=True)
        def save(path,value):captured.append((path,value))
        context=dict(Q_manifest={},remote_Q_chunk_proofs=[],input_sha256={})
        with patch.object(streamed_real_q,'StreamedRealQ',ManufacturedOperator),patch.object(subject,'new',side_effect=save):
            with self.assertRaisesRegex(ValueError,'manufactured failure'):
                with subject.checked_operator(None,context,lambda:None,None,Path('/synthetic-output'),2000):
                    raise ValueError('manufactured failure')
        self.assertEqual(len(captured),1);self.assertTrue(captured[0][1]['closed'])
        self.assertEqual(captured[0][0].name,'B0-2000-streamed-Q-receipt.json')

if __name__=='__main__':unittest.main()
