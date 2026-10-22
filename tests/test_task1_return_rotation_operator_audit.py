"""Small synthetic contact responses only; never real E/phi/grid/NPZ or a PDE."""
import copy
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import task1_return_rotation_operator_audit as audit


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.contacts = np.array([(p,a) for p in range(4) for a in (.25,.75)], dtype=[('pad','f8'),('area_m2','f8')])
        self.rank2 = np.array([[3.,2.],[1.,4.],[-3.,-1.],[-1.,-5.]], complex)

    def diagnose(self, r, f=3000):
        d = np.repeat(r.T,2,axis=1)
        d[0,::2] += 3j; d[0,1::2] -= 1j
        return audit.response_diagnostics(d,self.contacts,r[:2],[1.]*4,f)

    def test_actual_complex_area_integration_preserves_matrix_orientation(self):
        r = self.rank2.copy(); r[2] += [1j,2j]; r[0] -= [1j,2j]
        result = self.diagnose(r)
        actual = np.asarray(result['physical_pad_response_peak_real_A'])+1j*np.asarray(result['physical_pad_response_peak_imaginary_A'])
        np.testing.assert_allclose(actual,r,rtol=0,atol=1e-15)
        self.assertEqual(result['return_rank_at_native_resolution'],2)
        self.assertLessEqual(result['signal_source_relative_error'],2e-6)
        self.assertLessEqual(result['full_pad_KCL_relative_error'],2e-6)
        self.assertFalse(result['drive_weights_constructed'])

    def test_identical_return_rows_rank1_is_a_valid_observed_result(self):
        r = np.array([[3.,2.],[1.,2.],[-2.,-2.],[-2.,-2.]],complex)
        result = self.diagnose(r)
        self.assertEqual(result['return_rank_at_native_resolution'],1)
        self.assertEqual(result['status'],'measured_operator_rank_deficient_at_native_resolution')
        self.assertTrue(result['rank_deficiency_is_valid_result'])
        self.assertTrue(result['return_rows_equal_within_native_resolution'])
        self.assertIsNone(result['return_condition_number_at_native_resolution'])
        self.assertFalse(result['physical_symmetry_inferred_from_rank'])
        json.dumps(result,allow_nan=False)

    def test_zero_return_response_rank0_and_unresolved_weak_singular_value(self):
        r = np.array([[1.,2.],[-1.,-2.],[0.,0.],[0.,0.]],complex)
        result = self.diagnose(r)
        self.assertEqual(result['return_rank_at_native_resolution'],0)
        self.assertEqual(result['return_weakest_over_strongest'],0.)
        self.assertIsNone(result['return_condition_number_raw'])
        self.assertFalse(result['future_q_denominator']['resolved'])
        near = np.array([[3.,2.],[1.,2.+1e-7],[-2.,-2.],[-2.,-2.-1e-7]],complex)
        result = self.diagnose(near)
        self.assertLess(result['return_weakest_over_strongest'],2e-6)
        self.assertEqual(result['return_rank_at_native_resolution'],1)
        json.dumps(result,allow_nan=False)

    def test_frequency_specific_future_denominators_are_only_measured_not_inverted(self):
        for f,row,col in [(3000,2,1),(3030,3,0)]:
            result = self.diagnose(self.rank2,f)
            den = result['future_q_denominator']
            self.assertEqual((den['row'],den['column']),(row,col))
            self.assertEqual(den['absolute_A'],abs(self.rank2[row,col]))
            self.assertNotIn('q0',result); self.assertNotIn('q1',result)
            self.assertFalse(result['local_J_cancellation_inferred'])
            self.assertEqual(result['common_GND_nodes'],1)

    def test_rank1_does_not_require_equal_return_rows(self):
        r = np.array([[3.,3.],[3.,3.],[-2.,-2.],[-4.,-4.]],complex)
        result = self.diagnose(r)
        self.assertEqual(result['return_rank_at_native_resolution'],1)
        self.assertFalse(result['return_rows_equal_within_native_resolution'])

    def test_invalid_areas_ids_density_shape_source_or_kcl_fail(self):
        d = np.repeat(self.rank2.T,2,axis=1)
        for key,value in [('area_m2',0.),('area_m2',float('nan')),('pad',4.),('pad',.5)]:
            c = self.contacts.copy(); c[key][0] = value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                audit.response_diagnostics(d,c,self.rank2[:2],[1.]*4,3000)
        for density,source in [(d.T,self.rank2[:2]),(d,np.zeros((1,2))),
                               (np.full(d.shape,np.nan),self.rank2[:2]),(d,self.rank2[:2]+1.)]:
            with self.assertRaises(ValueError): audit.response_diagnostics(density,self.contacts,source,[1.]*4,3000)
        broken = self.rank2.copy(); broken[2,0] += .01
        with self.assertRaisesRegex(ValueError,'KCL'): self.diagnose(broken)
        with self.assertRaisesRegex(ValueError,'patch areas'):
            audit.response_diagnostics(d,self.contacts,self.rank2[:2],[2.]*4,3000)


class SmallFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_complex_native_little_endian_shape_and_gzip_bounded_decoder(self):
        a = np.array([[1+2j,3-4j],[5+.25j,-6j]],dtype='<c16')
        for suffix in ('.bin','.bin.gz'):
            p = self.root/('source-3000'+suffix)
            p.write_bytes(gzip.compress(a.tobytes()) if suffix.endswith('.gz') else a.tobytes())
            np.testing.assert_array_equal(audit.complex_array(p,(2,2)),a)
        p = self.root/'bad.bin'
        for raw in (a.tobytes()[:-1],a.tobytes()+b'x',np.full((2,2),np.inf+0j,dtype='<c16').tobytes()):
            p.write_bytes(raw)
            with self.assertRaises(ValueError): audit.complex_array(p,(2,2))

    def test_contact_csv_keeps_actual_order_and_rejects_extra_or_nonfinite_columns(self):
        p = self.root/'contacts-3000.csv'
        p.write_text('pad,x_mm,y_mm,area_m2\n2,1,2,.0001\n0,3,4,.0002\n')
        c = audit.load_contacts(p)
        self.assertEqual(c['pad'].tolist(),[2.,0.]); self.assertEqual(c['area_m2'].tolist(),[.0001,.0002])
        for data in ('pad,x_mm,y_mm,area_m2\n0,0,0,1,extra\n','pad,x_mm,y_mm,area_m2\n0,0,0,nan\n','pad,area_m2\n0,1\n'):
            p.write_text(data)
            with self.assertRaises(ValueError): audit.load_contacts(p)

    def make_source(self):
        declared = audit.SOURCE_CASES[0]; run = self.root/'data-native'/declared['run_id']; ident = declared['case_id']
        for part in ('cases','configs','masks','postprocess/'+ident,'bases/'+ident): (run/part).mkdir(parents=True,exist_ok=True)
        config = run/'configs/config.properties'
        centres = [[-10,-10],[10,10],[10,-10],[-10,10]]
        text = 'sc.sigma=0.0002\n'
        for i,(x,y) in enumerate(centres): text += f'pad.{i}.x_mm={x}\npad.{i}.y_mm={y}\npad.{i}.represented_area_m2=.000225\n'
        config.write_text(text); mask = run/'masks/mask.csv'; mask.write_text('pad,i,j,area_m2\n')
        circ = dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},source_resistance_ohm=50)
        case = dict(id=ident,config_file=str(config),config_sha256=audit.core.sha(config),mask_file=str(mask),mask_sha256=audit.core.sha(mask),circuit=circ,expected_pad_areas_m2=[.000225]*4)
        prepath = run/'preregistration.json'; audit.core.write(prepath,dict(status='prepared',source_commit='a'*40,cases=[case]))
        post = run/'postprocess'/ident/'summary.json'; audit.core.write(post,dict(status='complete',id=ident,input_sha256={'DO_NOT_OPEN_E': 'unconsumed provenance only'}))
        basis = run/'bases'/ident; (basis/'BASIS_COMPLETE').write_bytes(b'')
        audit.core.write(basis/'validation.json',dict(channels=2,cells=351680,**{k:0. for k in audit.core.GATES}))
        audit.core.write(basis/'mesh-metadata.json',dict(exporter_class='SelectivityShapeBasis',source_peak_V=.5,source_resistance_ohm=50,
            phasor_convention='peak,+jomega_t',channels=2,h_xy_mm=.625,sc_cells=2,bulk_layer_counts=[14,14,40],
            frequencies_Hz=[3000,3030,9000,9090],radius_mm=25,total_depth_mm=25.1,tissue_boundaries_mm=[0,.1,5.1,10.1,25.1],config_sha256=case['config_sha256']))
        for f in (3000,3030):
            for kind,suffix in [('density','bin'),('source','bin'),('contacts','csv')]: (basis/f'{kind}-{f}.{suffix}').write_bytes(b'small fixture bytes')
        (basis/'field-3000.bin').write_bytes(b'never open this field')
        files = {p.name:dict(sha256=audit.core.sha(p)) for p in basis.iterdir()}
        audit.core.write(run/'cases'/(ident+'.json'),dict(status='complete',config_sha256=case['config_sha256'],postprocess_path=str(post),postprocess_sha256=audit.core.sha(post),native_files=files))
        audit.core.write(run/'summary.json',dict(status='complete',registration_sha256=audit.core.sha(prepath)))
        return declared,run,basis

    def test_inventory_only_hashes_declared_small_files_not_E_phi_grid_or_NPZ(self):
        declared,run,basis = self.make_source(); seen = []; original = audit.core.sha
        def checked(p):
            p = Path(p); seen.append(p.name)
            self.assertFalse(p.name.startswith(('field-','potential-','grid.')) or p.suffix == '.npz')
            return original(p)
        with mock.patch.object(audit,'ROOT',self.root),mock.patch.object(audit.core,'sha',side_effect=checked):
            refs = {}; result = audit.source_metadata(declared,refs)
        self.assertFalse(result['raw_E_phi_grid_volume_files_opened'])
        self.assertEqual(set(result['native_small_arrays']),{'3000','3030'})
        self.assertEqual(len([n for n in refs if Path(n).name.startswith(('density-','source-','contacts-'))]),6)
        self.assertTrue(refs); self.assertNotIn('field-3000.bin',seen)

    def test_incomplete_terminal_or_small_native_hash_drift_blocks_inventory(self):
        declared,run,basis = self.make_source()
        with mock.patch.object(audit,'ROOT',self.root):
            terminal = audit.core.read(run/'summary.json'); terminal['status']='running'; audit.core.write(run/'summary.json',terminal)
            with self.assertRaisesRegex(ValueError,'completed source'): audit.source_metadata(declared,{})
            terminal['status']='complete'; audit.core.write(run/'summary.json',terminal)
            (basis/'density-3000.bin').write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError,'Pinned small source'): audit.source_metadata(declared,{})

    def test_execution_failure_preserves_receipt_and_appends_elapsed_time_without_reset(self):
        (self.root/'docs').mkdir(); (self.root/'runtime').mkdir()
        out = self.root/'docs/new-audit'; plan = self.root/'docs/plan.json'; plan.write_text('{}')
        ledger_path = self.root/'runtime/task1-budget.json'
        ledger = dict(limit_seconds=13800,spent_seconds=123.,runs=[dict(stage='prior',seconds=123.)])
        audit.core.write(ledger_path,ledger)
        argv = ['operator-audit','--preregistration',str(plan),'--output',str(out)]
        with mock.patch.object(audit,'ROOT',self.root),mock.patch.object(sys,'argv',argv), \
             mock.patch.object(audit.os,'sched_setaffinity'), \
             mock.patch.object(audit.policy,'load_ledger',return_value=copy.deepcopy(ledger)), \
             mock.patch.object(audit.policy,'remaining_seconds',return_value=100), \
             mock.patch.object(audit,'verify_plan',side_effect=ValueError('synthetic plan drift')), \
             mock.patch.object(audit,'execute') as execute:
            with self.assertRaisesRegex(ValueError,'synthetic plan drift'): audit.main()
            execute.assert_not_called()
        result = audit.core.read(out/'failure.json'); after = audit.core.read(ledger_path)
        self.assertTrue(result['partial_evidence_preserved']); self.assertFalse(result['automatic_retry'])
        self.assertEqual(after['runs'][0],ledger['runs'][0]); self.assertGreater(after['spent_seconds'],123.)
        self.assertEqual(after['runs'][-1]['status'],'failed_preserved')
        self.assertEqual(audit.core.read(out/'heartbeat.json')['status'],'failed_preserved')
        self.assertTrue((out/'checkpoint-001-verify_plan.json').exists())


if __name__ == '__main__': unittest.main()
