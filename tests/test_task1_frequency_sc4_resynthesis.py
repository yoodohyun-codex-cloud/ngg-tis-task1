"""Synthetic SC4 identity/cutoff/dispatch/resource checks; no native data runs."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import task1_frequency_sc4_resynthesis as sc4


def item_fixture():
    condition = dict(id='baseline-square15-sc4-square_3h', waveform='square_3h',
        actual_fundamental_Hz=[3000, 3030], phase_deg=[0., 0.], source_Vpp_per_output=1.)
    return dict(summary=dict(id=sc4.SC4_CASE, mesh_metadata=dict(h_xy_mm=.625, sc_cells=4,
        bulk_layer_counts=[14, 14, 40], cells=361728, radius_mm=25., total_depth_mm=25.1,
        channels=2, frequencies_Hz=[3000, 3030, 9000, 9090])),
        case=dict(id=sc4.SC4_CASE, design_id='baseline-square15'),
        run=Path('/synthetic')/sc4.SOURCE_RUN, circuit=dict(n_pads=4, n_outputs=2),
        conditions=[condition], path=Path('/synthetic/SC4/summary.json'))


def cutoff_receipt():
    return dict(status='calculated_unadopted', source_provenance=dict(case_id='baseline-square15-xy80',
        run_id=sc4.SOURCE_RUN), actual_fundamental_Hz=[3000, 3030],
        shared_square_baseline_cutoffs_V_m={m:{r+'_'+s:float(10+i+j)
            for i, r in enumerate((sc4.volume.PRIMARY, sc4.volume.SLAB)) for j, s in enumerate(('mean', 'p10'))}
            for m in sc4.volume.METRICS})


class SC4IdentityTests(unittest.TestCase):
    def test_exact_sc4_identity_is_not_disguised_as_sc2(self):
        item = item_fixture()
        with mock.patch.object(sc4.volume, 'burdens', return_value=({}, [1., 1.])):
            self.assertIs(sc4.validate_sc4_identity(item), item)
        self.assertEqual(item['case']['id'], 'baseline-square15-sc4')
        self.assertEqual(item['summary']['mesh_metadata']['sc_cells'], 4)

    def test_sc2_wrong_grid_domain_or_extra_outputs_are_rejected(self):
        mutations = [('id', 'baseline-square15-xy80'), ('sc_cells', 2), ('h_xy_mm', .5),
            ('radius_mm', 30.), ('cells', 351680), ('channels', 4), ('frequencies_Hz', [3000, 3030])]
        for key, value in mutations:
            item = item_fixture()
            if key == 'id': item['summary']['id'] = value
            else: item['summary']['mesh_metadata'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                sc4.validate_sc4_identity(item)

    def test_source_path_rejects_other_sc4_label_at_arbitrary_location(self):
        with self.assertRaises(ValueError), mock.patch.object(sc4.view, 'load_case') as loader:
            sc4.source_item(Path('/fake/summary.json'))
        loader.assert_not_called()

    def test_refinement_rejects_impedance_geometry_or_circuit_changes(self):
        before = dict(config={'validation.sc_cells':'2', 'z.9000.re':'0.00004', 'pad.0.x_mm':'-10'},
            circuit={'n_outputs':2, 'return_topology':'common_GND'})
        after = copy.deepcopy(before); after['config']['validation.sc_cells'] = '4'
        self.assertTrue(sc4.refinement_contract(after, before)['geometry_contact_material_circuit_unchanged'])
        for key in ('z.9000.re', 'pad.0.x_mm'):
            bad = copy.deepcopy(after); bad['config'][key] = 'changed'
            with self.subTest(key=key), self.assertRaises(ValueError): sc4.refinement_contract(bad, before)
        bad = copy.deepcopy(after); bad['circuit']['n_outputs'] = 4
        with self.assertRaises(ValueError): sc4.refinement_contract(bad, before)

    def test_byte_identical_contact_mask_path_alias_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(sc4, 'ROOT', Path(temp)):
            first, second = Path(temp)/'SC2.csv', Path(temp)/'SC4.csv'
            data = b'pad,i,j,area_m2\n0,1,2,0.000225\n'
            first.write_bytes(data); second.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            before = dict(config={'validation.sc_cells':'2', 'mask.path':str(first), 'mask.sha256':digest}, circuit={})
            after = copy.deepcopy(before); after['config'].update({'validation.sc_cells':'4', 'mask.path':str(second)})
            receipt = sc4.refinement_contract(after, before)
            self.assertEqual(receipt['changed_config_fields'], ['mask.path', 'validation.sc_cells'])
            self.assertTrue(receipt['mask_path_alias']['both_bytes_verified'])
            second.write_bytes(data+b'1,3,4,0.000225\n')
            with self.assertRaisesRegex(ValueError, 'byte-identical'): sc4.refinement_contract(after, before)

    def test_contact_mask_different_digest_is_not_a_path_alias(self):
        before = dict(config={'validation.sc_cells':'2', 'mask.path':'/SC2.csv', 'mask.sha256':'one'}, circuit={})
        after = copy.deepcopy(before)
        after['config'].update({'validation.sc_cells':'4', 'mask.path':'/SC4.csv', 'mask.sha256':'two'})
        with self.assertRaisesRegex(ValueError, 'same declared byte digest'): sc4.refinement_contract(after, before)

    def test_sc2_square_cap_reference_reads_square_json_metrics_not_sine_candidate(self):
        item = item_fixture(); item['case']['id'] = item['summary']['id'] = 'baseline-square15-xy80'
        item['summary']['mesh_metadata']['sc_cells'] = 2
        item['conditions'][0]['id'] = 'original_SC2_square'
        burden = {'Jmax':12., 'power':.003}; current = [1.23, 1.24]
        with mock.patch.object(sc4.volume, 'burdens', return_value=(burden, current)) as reader, \
            mock.patch.object(sc4.view, 'sha', return_value='source_JSON_SHA'):
            reference = sc4.sc2_square_cap_reference(item)
        self.assertIs(reader.call_args.args[1], item['conditions'][0])
        self.assertEqual(reference['waveform'], 'square_3h')
        self.assertEqual(reference['id'], 'original_SC2_square')
        self.assertEqual(reference['burdens'], burden)
        self.assertEqual(reference['source_mesh_SC_cells'], 2)

    def test_cross_mesh_cutoffs_require_actual_sc2_provenance_and_are_copied(self):
        receipt = cutoff_receipt()
        result = sc4.fixed_sc2_cutoffs(receipt)
        result['maxTIS'][sc4.volume.PRIMARY+'_mean'] = -1
        self.assertGreater(receipt['shared_square_baseline_cutoffs_V_m']['maxTIS'][sc4.volume.PRIMARY+'_mean'], 0)
        for field, value in [('status', 'running'), ('actual_fundamental_Hz', [9000, 9090])]:
            bad = cutoff_receipt(); bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): sc4.fixed_sc2_cutoffs(bad)
        bad = cutoff_receipt(); bad['source_provenance']['case_id'] = sc4.SC4_CASE
        with self.assertRaises(ValueError): sc4.fixed_sc2_cutoffs(bad)

    def test_invalid_missing_cutoff_cannot_be_silently_replaced(self):
        for value in (0., -1., float('nan'), float('inf')):
            bad = cutoff_receipt(); bad['shared_square_baseline_cutoffs_V_m']['maxTIS'][sc4.volume.PRIMARY+'_mean'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): sc4.fixed_sc2_cutoffs(bad)
        bad = cutoff_receipt(); del bad['shared_square_baseline_cutoffs_V_m']['RMS']
        with self.assertRaises(ValueError): sc4.fixed_sc2_cutoffs(bad)


class SC4DispatchTests(unittest.TestCase):
    def test_genuine_sc4_basis_and_sc2_cutoffs_are_forwarded_without_module_patch(self):
        item = item_fixture(); grid = np.zeros(2)
        basis = dict(hashes={'real_SC4_basis': 'hash'}, grid=grid)
        cached = dict(condition=item['conditions'][0], item=item, grid=grid,
            arrays={m:np.array([1., 2.]) for m in sc4.volume.METRICS},
            regions={r:np.ones(2) for r in (sc4.volume.PRIMARY, sc4.volume.SLAB)})
        post = SimpleNamespace(_load_basis=mock.Mock(return_value=basis),
            _geometry=mock.Mock(return_value=({'genuine_SC4': True}, {'SC_cells': 4})))
        fixed = sc4.fixed_sc2_cutoffs(cutoff_receipt())
        plan = dict(native_input_sha256=basis['hashes'], conditions=[dict(x) for x in sc4.frequency.CONDITIONS],
            fixed_SC2_cutoffs_V_m=fixed, burden_reference_scope='SC4 references', holds=['held'],
            SC2_square_cap_reference=dict(id='SC2-square', burdens={'a':2.}, currents=[2., 2.],
                waveform='square_3h', actual_fundamental_Hz=[3000, 3030], source_mesh_SC_cells=2))
        before = copy.deepcopy(plan)
        calls = []
        def derive(*args):
            calls.append(args)
            self.assertIs(args[0], basis)
            self.assertEqual(args[3]['item']['case']['id'], 'baseline-square15-sc4')
            self.assertEqual(args[12], fixed)
            self.assertEqual(list(args[11]), [sc4.SC4_SQUARE_COHORT, sc4.SC2_SQUARE_COHORT])
            self.assertEqual(args[11][sc4.SC2_SQUARE_COHORT]['burdens'], {'a':2.})
            return dict(id=args[5]['id'], status='calculated_unadopted')
        with tempfile.TemporaryDirectory() as temp, \
            mock.patch.object(sc4, 'source_item', return_value=item), \
            mock.patch.object(sc4.volume, 'load_native', return_value=cached), \
            mock.patch.object(sc4.drive, 'import_frozen', return_value=(post, object(), object())) as importer, \
            mock.patch.object(sc4.volume, 'burdens', return_value=({'a':1.}, [1., 1.])), \
            mock.patch.object(sc4.frequency, 'derive', side_effect=derive), \
            mock.patch.object(sc4.signal, 'setitimer'), \
            mock.patch.object(sc4.view, 'sha', return_value='summarysha'):
            output = Path(temp)
            result = sc4.execute(plan, sc4.SC4_SUMMARY, output, float('inf'), mock.Mock())
            own = json.loads((output/'SC4-own-cutoff-reference.json').read_text())
        self.assertEqual(len(calls), 2)
        self.assertEqual([c[5]['actual_fundamental_Hz'] for c in calls], [[3000, 3030], [9000, 9090]])
        self.assertEqual(importer.call_args.args[0], item['run'])
        self.assertEqual(post._load_basis.call_args.args[0], item['run']/'bases'/sc4.SC4_CASE)
        self.assertEqual(plan, before)
        self.assertFalse(own['SC4_own_cutoffs_used_for_high_volume_comparison'])
        self.assertNotEqual(own['SC4_own_square_cutoffs_V_m'], fixed)
        self.assertEqual(result['source_mesh_SC_cells'], 4)
        self.assertEqual(result['comparison_cohorts'], [sc4.SC4_SQUARE_COHORT, sc4.SC2_SQUARE_COHORT, 'fresh_sine_3000_3030_caps'])
        self.assertEqual(result['SC2_square_cap_reference']['source_mesh_SC_cells'], 2)
        self.assertFalse(result['candidate_adopted'])

    def test_main_rejects_insufficient_budget_before_any_output_or_computation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'docs').mkdir()
            args = SimpleNamespace(output=root/'docs/cloud-next-sc4-test', plan=root/'plan.json', baseline_summary=root/'source.json')
            policy = SimpleNamespace(load_ledger=mock.Mock(return_value={'spent_seconds': 13400, 'limit_seconds': 13800}),
                remaining_seconds=mock.Mock(return_value=400))
            with mock.patch.object(sc4, 'ROOT', root), \
                mock.patch.object(sc4.argparse.ArgumentParser, 'parse_args', return_value=args), \
                mock.patch.object(sc4.frequency, 'policy_module', return_value=policy), \
                mock.patch.object(sc4, 'execute') as execute, \
                self.assertRaisesRegex(ValueError, '480s'):
                sc4.main()
            self.assertFalse(args.output.exists()); execute.assert_not_called()
            self.assertEqual(policy.load_ledger.return_value['spent_seconds'], 13400)

    def test_missing_ledger_is_not_recreated_or_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'docs').mkdir()
            args = SimpleNamespace(output=root/'docs/cloud-next-sc4-test', plan=root/'plan.json', baseline_summary=root/'source.json')
            policy = SimpleNamespace(load_ledger=mock.Mock(side_effect=FileNotFoundError('missing historical ledger')))
            with mock.patch.object(sc4, 'ROOT', root), \
                mock.patch.object(sc4.argparse.ArgumentParser, 'parse_args', return_value=args), \
                mock.patch.object(sc4.frequency, 'policy_module', return_value=policy), \
                self.assertRaises(FileNotFoundError):
                sc4.main()
            self.assertFalse(args.output.exists()); self.assertFalse((root/'runtime/task1-budget.json').exists())


if __name__ == '__main__':
    unittest.main()
