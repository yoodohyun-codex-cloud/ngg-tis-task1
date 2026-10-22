"""Synthetic lattice/resource/proc fixtures; no CLI, native arrays or worker."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_xy_native_resume_preflight as r


class XYNativeResumePreflightTest(unittest.TestCase):
    def test_fixed_integer_lattice_counts_and_fine_grid_exceeding_original_cap(self):
        for nx,xy,cells in ((40,1264,88480),(80,5024,351680),(120,11304,791280),(160,20108,1407560)):
            with self.subTest(nx=nx):
                result=r.grid_counts(nx)
                independent=sum(u*u+v*v<=nx*nx for u in range(1-nx,nx,2)for v in range(1-nx,nx,2))
                self.assertEqual(independent,xy)
                self.assertEqual(dict(nx=nx,xy_active_cells=xy,nz=70,cells=cells),result)
        fine=r.grid_counts(160)
        result=r.admission(10*1024**3,5000.,fine['cells'],nx=160)
        self.assertTrue(result['storage_pass']);self.assertTrue(result['time_pass'])
        self.assertFalse(result['cells_pass']);self.assertFalse(result['native_grid_supported'])
        self.assertFalse(result['resource_admission_passed'])
        self.assertIn('approved_800000_cell_cap_exceeded',result['blockers'])
        self.assertIn('frozen_Java_ValidationMesh_nx_above_120',result['blockers'])
        preferred=r.admission(10*1024**3,960.,791280)
        self.assertTrue(preferred['cells_pass']);self.assertTrue(preferred['native_grid_supported'])
        self.assertTrue(preferred['resource_admission_passed'])

    def test_grid_dimension_rejects_bool_noninteger_odd_nonpositive_values(self):
        for nx in(True,False,40.,'80',None,0,-2,1,41):
            with self.subTest(nx=nx),self.assertRaises((ValueError,TypeError)):r.grid_counts(nx)

    def test_storage_exact_boundary_and_one_byte_short_are_not_rounded(self):
        cells=351680;required=2*1024**3+cells*600+128*1024**2
        equal=r.admission(required,960.,cells,nx=80)
        short=r.admission(required-1,960.,cells,nx=80)
        self.assertEqual(required,equal['required_free_bytes']);self.assertEqual(required,short['required_free_bytes'])
        self.assertTrue(equal['storage_pass']);self.assertTrue(equal['time_pass']);self.assertTrue(equal['cells_pass'])
        self.assertTrue(equal['native_grid_supported']);self.assertTrue(equal['resource_admission_passed'])
        self.assertFalse(short['storage_pass']);self.assertFalse(short['resource_admission_passed'])

    def test_time_and_cell_limits_are_inclusive_and_do_not_admit_unsupported_native_grid(self):
        free=10*1024**3
        at=r.admission(free,960.,351680,nx=80);below=r.admission(free,959.999,351680,nx=80)
        self.assertTrue(at['time_pass']);self.assertFalse(below['time_pass']);self.assertFalse(below['resource_admission_passed'])
        self.assertTrue(r.admission(free,960.,800000,nx=120)['cells_pass'])
        self.assertFalse(r.admission(free,960.,800001,nx=120)['cells_pass'])
        unsupported=r.admission(free,960.,351680,nx=160)
        self.assertFalse(unsupported['native_grid_supported']);self.assertFalse(unsupported['resource_admission_passed'])

    def test_resource_counters_reject_bool_wrong_types_negative_and_nonfinite_values(self):
        valid=dict(free_bytes=10*1024**3,remaining_seconds=960.,cells=351680,nx=80)
        for key,value in [('free_bytes',True),('free_bytes',1.),('free_bytes',-1),('cells',True),('cells',351680.),
            ('cells',0),('cells',-1),('remaining_seconds',True),('remaining_seconds','960'),
            ('remaining_seconds',float('nan')),('remaining_seconds',float('inf')),('remaining_seconds',-1.),('nx',True)]:
            args={**valid,key:value}
            with self.subTest(key=key,value=value),self.assertRaises((ValueError,TypeError)):r.admission(**args)

    def test_process_identity_uses_start_ticks_and_handles_spaces_parentheses_missing_and_corrupt_stat(self):
        with tempfile.TemporaryDirectory()as td:
            proc=Path(td);pid=23145;ticks=7654321;folder=proc/str(pid);folder.mkdir();stat=folder/'stat'
            # Fields after comm start at3(state);18zeros are fields4..21.
            line=f'{pid} (synthetic worker (two words)) S '+' '.join(['0']*18+[str(ticks)]+['0']*4)+'\n'
            stat.write_text(line)
            self.assertTrue(r.live_process(pid,ticks,proc))
            self.assertFalse(r.live_process(pid,ticks+1,proc))
            self.assertFalse(r.live_process(pid+1,ticks,proc))
            stat.write_text(f'{pid} (truncated process) S 0\n')
            self.assertFalse(r.live_process(pid,ticks,proc))
            stat.write_text('malformed\n');self.assertFalse(r.live_process(pid,ticks,proc))
            stat.unlink();self.assertFalse(r.live_process(pid,ticks,proc))

    def test_matching_zombie_and_dead_states_are_not_live_but_running_state_is(self):
        with tempfile.TemporaryDirectory()as td:
            proc=Path(td);pid=23145;ticks=7654321;folder=proc/str(pid);folder.mkdir();stat=folder/'stat'
            for state,expected in [('R',True),('S',True),('Z',False),('X',False)]:
                stat.write_text(f'{pid} (same worker (identity)) {state} '+
                    ' '.join(['0']*18+[str(ticks)]+['0']*4)+'\n')
                with self.subTest(state=state):
                    self.assertIs(r.live_process(pid,ticks,proc),expected)


if __name__=='__main__':unittest.main()
