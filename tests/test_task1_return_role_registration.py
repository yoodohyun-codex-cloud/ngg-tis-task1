"""Synthetic role-remapping contract; root alone executes these pure tests."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
OLD_ID = 'asym-cross281p25-return168p75-xy80'
NEW_ID = 'return-cross281p25-signal168p75-xy80'
OLD_TO_NEW = {0: 2, 1: 3, 2: 0, 3: 1}
CENTRES = ((-10., -10.), (10., 10.), (10., -10.), (-10., 10.))
H = .625
FACE = (H / 1000.) ** 2


def synthetic_design():
    pads = []
    for index, (x, y) in enumerate(CENTRES):
        is_cross = index < 2
        width, height, area = (17.5, 17.5, 281.25) if is_cross else (15., 11.25, 168.75)
        if is_cross:
            a, b = 8.75, 6.25
            outline = [(-b, -a), (b, -a), (b, -b), (a, -b), (a, b), (b, b),
                       (b, a), (-b, a), (-b, b), (-a, b), (-a, -b), (-b, -b)]
        else:
            outline = [(-7.5, -5.625), (7.5, -5.625), (7.5, 5.625), (-7.5, 5.625)]
        pad = dict(pad=index, shape='cross' if is_cross else 'rectangle', center_mm=[x, y],
            width_mm=width, height_mm=height, rotation_deg=0., corner_radius_mm=0.,
            analytic_area_mm2=area, area_mm2=area, polygon_area_mm2=area,
            polygon_mm=[[x+u, y+v] for u, v in outline],
            role='signal' if is_cross else 'common_gnd_return',
            source_output=index if is_cross else None, indexed_pair=index % 2,
            custom_metadata={'original_pad': index, 'label': '합성 fixture'})
        if is_cross:
            pad.update(outer_length_mm=17.5, arm_width_mm=12.5,
                union_rectangles_mm=[dict(center_mm=[x, y], width_mm=17.5, height_mm=12.5),
                                     dict(center_mm=[x, y], width_mm=12.5, height_mm=17.5)])
        pads.append(pad)
    return dict(id=OLD_ID.removesuffix('-xy80'), total_pads=4, source_outputs=2,
        channels=2, phantom_diameter_mm=50, contact_plane_z_mm=0.,
        return_connection='all_return_pads_ideal_common_GND', pads=pads,
        xy_mm=[list(xy) for xy in CENTRES], physical_total_contact_area_mm2=900.,
        minimum_gap_mm=3.75, geometry_revision='synthetic-original-mixed',
        custom_metadata={'experiment': 'synthetic'})


def synthetic_rows():
    """Enumerate original full faces independently of the implementation."""
    rows = []
    for pad, (x, y) in enumerate(CENTRES):
        for j in range(80):
            for i in range(80):
                dx, dy = abs(-25+(i+.5)*H-x), abs(-25+(j+.5)*H-y)
                active = ((dx < 8.75 and dy < 6.25) or (dx < 6.25 and dy < 8.75)) \
                    if pad < 2 else (dx < 7.5 and dy < 5.625)
                if active:
                    rows.append((pad, i, j, FACE))
    return rows


def properties(data):
    return dict(line.split('=', 1) for line in data.decode('utf-8').splitlines()
                if line and not line.startswith(('#', '!')))


def synthetic_config(design, areas):
    values = dict(h_mm='0.625', channels='2', frequencies='3000,3030,9000,9090',
        **{'validation.sc_cells': '2', 'validation.max_cells': '800000',
           'bulk.counts': '14,14,40', 'mask.path': '/synthetic/original.csv',
           'mask.sha256': 'a'*64, 'sc.sigma': '0.0002', 'sc.epsilon_r': '110000',
           'dermis.sigma': '0.2', 'dermis.epsilon_r': '10000', 'fat.sigma': '0.04',
           'fat.epsilon_r': '1000', 'muscle.sigma': '0.3', 'muscle.epsilon_r': '100000',
           'synthetic.nonpad.sentinel': 'unchanged'})
    for frequency in (3000, 3030, 9000, 9090):
        values[f'z.{frequency}.re'] = '0.000044'
        values[f'z.{frequency}.im'] = '-0.000095'
    for pad in design['pads']:
        index = pad['pad']
        suffixes = {key: str(pad[key]) for key in
            ('shape', 'width_mm', 'height_mm', 'rotation_deg', 'analytic_area_mm2')}
        suffixes.update(x_mm=str(pad['center_mm'][0]), y_mm=str(pad['center_mm'][1]),
            represented_area_m2=format(areas[index], '.17g'), custom_suffix=f'original-{index}')
        if pad['shape'] == 'cross':
            suffixes['arm_width_mm'] = '12.5'
        values.update({f'pad.{index}.{suffix}': value for suffix, value in suffixes.items()})
    return ('# Synthetic complete metadata fixture\n'+''.join(f'{key}={value}\n'
        for key, value in values.items())).encode('utf-8')


class ReturnRoleRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT/'tools'))
        spec = importlib.util.spec_from_file_location('return_role_tested', ROOT/'tools/task1_return_role_registration.py')
        cls.registration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.registration)

    def setUp(self):
        self.design = synthetic_design()
        self.rows = synthetic_rows()
        self.old_areas = [math.fsum(a for pad, _, _, a in self.rows if pad == p) for p in range(4)]

    def test_exact_case_ID_and_pad_role_shape_position_permutation(self):
        r = self.registration
        design = r.remap_design(self.design)
        self.assertEqual(r.CASE_ID, NEW_ID)
        self.assertEqual(design['id'], NEW_ID.removesuffix('-xy80'))
        for old_index, new_index in OLD_TO_NEW.items():
            old, new = self.design['pads'][old_index], design['pads'][new_index]
            for key in ('shape', 'center_mm', 'width_mm', 'height_mm', 'polygon_mm',
                        'analytic_area_mm2', 'area_mm2', 'custom_metadata'):
                self.assertEqual(new[key], old[key])
            self.assertEqual(new['pad'], new_index)
            self.assertEqual(new['role'], 'signal' if new_index < 2 else 'common_gnd_return')
            self.assertEqual(new['source_output'], new_index if new_index < 2 else None)
        self.assertEqual((design['total_pads'], design['source_outputs']), (4, 2))
        self.assertEqual(design['return_connection'], 'all_return_pads_ideal_common_GND')
        self.assertEqual(design['xy_mm'], [pad['center_mm'] for pad in design['pads']])

    def test_design_reorder_is_a_deepcopy_and_preserves_physical_total_area(self):
        before = copy.deepcopy(self.design)
        design = self.registration.remap_design(self.design)
        self.assertEqual(self.design, before)
        self.assertEqual(sum(p['area_mm2'] for p in design['pads']), 900.)
        design['pads'][0]['polygon_mm'][0][0] = 999
        design['pads'][0]['custom_metadata']['label'] = 'changed'
        self.assertEqual(self.design, before)

    def test_same_2304_full_faces_union_and_physical_area_are_preserved(self):
        rows, areas, receipt = self.registration.relabel_mask(self.rows, self.design)
        self.assertEqual(len(rows), 2304)
        self.assertEqual({(i, j, a) for _, i, j, a in rows}, {(i, j, a) for _, i, j, a in self.rows})
        self.assertEqual(len({(i, j) for _, i, j, _ in rows}), 2304)
        self.assertTrue(all(a == FACE for _, _, _, a in rows))
        self.assertEqual([sum(pad == p for pad, _, _, _ in rows) for p in range(4)], [432, 432, 720, 720])
        for actual, expected in zip(areas, (168.75, 168.75, 281.25, 281.25)):
            self.assertAlmostEqual(actual*1e6, expected, places=10)
        self.assertAlmostEqual(math.fsum(areas)*1e6, 900., places=10)
        self.assertIsInstance(receipt, dict)

    def test_every_contact_face_only_changes_its_pad_label_without_input_mutation(self):
        before = copy.deepcopy((self.rows, self.design))
        rows, _, _ = self.registration.relabel_mask(self.rows, self.design)
        self.assertEqual(set(rows), {(OLD_TO_NEW[p], i, j, a) for p, i, j, a in self.rows})
        self.assertEqual((self.rows, self.design), before)

    def test_any_alternate_mapping_is_rejected(self):
        for mapping in ({0: 0, 1: 1, 2: 2, 3: 3}, {0: 2, 1: 2, 2: 0, 3: 1}, {0: 2, 1: 3, 2: 0}):
            with self.subTest(mapping=mapping):
                with self.assertRaises(ValueError):
                    self.registration.remap_design(self.design, mapping=mapping)
                with self.assertRaises(ValueError):
                    self.registration.relabel_mask(self.rows, self.design, mapping=mapping)

    def test_changed_source_roles_centres_area_or_geometry_are_rejected(self):
        for pad, key, value in ((0, 'role', 'common_gnd_return'), (1, 'source_output', 0),
                               (2, 'center_mm', [10., -9.375]), (0, 'rotation_deg', 90.),
                               (2, 'area_mm2', 225.), (0, 'arm_width_mm', 10.)):
            design = copy.deepcopy(self.design)
            design['pads'][pad][key] = value
            with self.subTest(pad=pad, key=key), self.assertRaises(ValueError):
                self.registration.remap_design(design)

    def test_mask_missing_duplicate_partial_relabelled_or_moved_faces_are_rejected(self):
        for variant in ('missing', 'duplicate', 'partial', 'wrong_pad', 'moved'):
            rows = list(self.rows)
            if variant == 'missing':
                rows.pop()
            elif variant == 'duplicate':
                rows[-1] = rows[0]
            else:
                p, i, j, a = rows[0]
                rows[0] = ((2, i, j, a) if variant == 'wrong_pad' else
                           (p, i, j, a/2) if variant == 'partial' else (p, 0, 0, a))
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                self.registration.relabel_mask(rows, self.design)

    def config_result(self):
        rows, areas, _ = self.registration.relabel_mask(self.rows, self.design)
        old = synthetic_config(self.design, self.old_areas)
        new_design = self.registration.remap_design(self.design)
        new, changes = self.registration.remap_config(old, Path('/synthetic/remapped.csv'), 'b'*64, areas, new_design)
        return old, new, changes, rows

    def test_all_pad_metadata_suffixes_move_and_nonpad_physics_is_identical(self):
        old, new, changes, _ = self.config_result()
        a, b = properties(old), properties(new)
        excluded = {'mask.path', 'mask.sha256'}
        self.assertEqual({k: v for k, v in a.items() if not k.startswith('pad.') and k not in excluded},
                         {k: v for k, v in b.items() if not k.startswith('pad.') and k not in excluded})
        for old_index, new_index in OLD_TO_NEW.items():
            prefix = f'pad.{old_index}.'
            expected = {key[len(prefix):]: value for key, value in a.items() if key.startswith(prefix)}
            new_prefix = f'pad.{new_index}.'
            actual = {key[len(new_prefix):]: value for key, value in b.items() if key.startswith(new_prefix)}
            self.assertEqual(actual, expected)
        self.assertEqual(b['mask.path'], '/synthetic/remapped.csv')
        self.assertEqual(b['mask.sha256'], 'b'*64)
        self.assertTrue(all(key.startswith('pad.') or key in excluded for key in changes))

    def test_rectangular_signal_pads_have_no_stale_cross_arm_width(self):
        _, new, _, _ = self.config_result()
        values = properties(new)
        for index in (0, 1):
            self.assertEqual(values[f'pad.{index}.shape'], 'rectangle')
            self.assertNotIn(f'pad.{index}.arm_width_mm', values)
            self.assertEqual(float(values[f'pad.{index}.width_mm']), 15.)
            self.assertEqual(float(values[f'pad.{index}.height_mm']), 11.25)
        for index in (2, 3):
            self.assertEqual(values[f'pad.{index}.shape'], 'cross')
            self.assertEqual(float(values[f'pad.{index}.arm_width_mm']), 12.5)

    def test_config_rejects_wrong_area_order_count_or_total(self):
        old = synthetic_config(self.design, self.old_areas)
        new_design = self.registration.remap_design(self.design)
        for areas in (self.old_areas, [168.75e-6]*3, [225.e-6]*4):
            with self.subTest(areas=areas), self.assertRaises(ValueError):
                self.registration.remap_config(old, Path('/synthetic/new.csv'), 'b'*64, areas, new_design)

    def test_remapped_labels_produce_a_distinct_operator_signature(self):
        old, new, _, rows = self.config_result()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            signatures = []
            for name, config, mask_rows in (('old', old, self.rows), ('new', new, rows)):
                config_path, mask_path = directory/(name+'.properties'), directory/(name+'.csv')
                config_path.write_bytes(config)
                mask_path.write_text('pad,i,j,area_m2\n'+''.join(f'{p},{i},{j},{a:.17g}\n' for p, i, j, a in mask_rows))
                signatures.append(self.registration.core.operator_signature(
                    dict(config_file=str(config_path), mask_file=str(mask_path), java_class='CloudShapeBasis')))
            self.assertNotEqual(*signatures)

    def decision_fixture(self, root):
        r = self.registration
        source = root/'data-native'/r.SOURCE_RUN
        source_paths = [source/'postprocess'/r.SOURCE_ID/'summary.json',
                        source/'configs'/(r.SOURCE_ID+'.properties'),
                        source/'masks'/(r.SOURCE_ID+'.csv')]
        for path, contents in zip(source_paths, ('{"status":"complete"}\n',
                                                 'h_mm=0.625\n', 'pad,i,j,area_m2\n')):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
        pins = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
        audit_path = root/'native-causal-audit.json'
        audit = dict(status='complete_diagnostic_only', inputs_unchanged=True,
                     inputs_sha256=copy.deepcopy(pins))
        audit_path.write_text(json.dumps(audit))
        decision = dict(schema='task1-return-role-decision-v1', status='preregistered_not_started',
            source_run_id=r.SOURCE_RUN, source_case_id=r.SOURCE_ID, chosen_case_id=r.CASE_ID,
            chosen_wiring_question='At unchanged physical patches, exchange source and common-GND roles?',
            adopted=False, native_audit=dict(path=str(audit_path),
                SHA256=hashlib.sha256(audit_path.read_bytes()).hexdigest()), inputs_sha256=pins)
        decision_path = root/'decision.json'
        decision_path.write_text(json.dumps(decision))
        return decision_path, decision, audit_path, audit, source_paths

    def test_decision_verifies_completed_causal_audit_and_source_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, decision, audit_path, _, source_paths = self.decision_fixture(root)
            with patch.object(self.registration.core, 'REPO', root):
                actual, pins = self.registration.verify_decision(path)
            self.assertEqual(actual, decision)
            for source in source_paths+[audit_path, path]:
                self.assertEqual(pins[str(source)], hashlib.sha256(source.read_bytes()).hexdigest())

    def test_decision_rejects_tampered_audit_or_missing_audit_source_mask_binding(self):
        for variant in ('tampered_bytes', 'missing_mask_binding'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, decision, audit_path, audit, source_paths = self.decision_fixture(root)
                if variant == 'tampered_bytes':
                    audit_path.write_text(audit_path.read_text()+' ')
                else:
                    audit['inputs_sha256'].pop(str(source_paths[2]))
                    audit_path.write_text(json.dumps(audit))
                    decision['native_audit']['SHA256'] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
                    path.write_text(json.dumps(decision))
                with patch.object(self.registration.core, 'REPO', root), self.assertRaises(ValueError):
                    self.registration.verify_decision(path)

    def test_ROI_only_selection_without_explicit_wiring_question_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, decision, _, _, _ = self.decision_fixture(root)
            decision.pop('chosen_wiring_question')
            decision['ROI_only_selection'] = True
            path.write_text(json.dumps(decision))
            with patch.object(self.registration.core, 'REPO', root), self.assertRaises(ValueError):
                self.registration.verify_decision(path)


if __name__ == '__main__':
    unittest.main()
