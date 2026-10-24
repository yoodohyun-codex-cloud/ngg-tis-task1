"""Synthetic-only centred C1 tests; no native inputs or research execution."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parent
ROOT = Path('/workspace/ngg-tis-task1')
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(ROOT / 'tools'))
SPEC = importlib.util.spec_from_file_location('synthetic_centered_post', SOURCE / 'centered_post.py')
POST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POST)


def centered_case():
    pads = []
    for i, x in enumerate((-10., 10.)):
        pads.append(dict(pad=i, center_mm=[x, 0.], width_mm=15., height_mm=15., rotation_deg=0.,
                         polygon_mm=[[x-7.5, -7.5], [x+7.5, -7.5], [x+7.5, 7.5], [x-7.5, 7.5]]))
    return dict(id='centered-square15-C1-y0-xy80-f3000',
                circuit=dict(n_pads=2, n_outputs=1, n_return_nodes=1, source_peak_V=.5,
                             source_resistance_ohm=50, pad_to_node={'0': 'out0', '1': 'GND'}),
                design=dict(pads=pads), expected_pad_areas_m2=[225e-6, 225e-6])


def unit_arrays():
    field = np.array([[3+4j, 0, 0], [0, 6j, 8], [0, 0, 12], [1+2j, 2-1j, 0]], dtype=complex)
    current = -.002j
    area = np.array([1e-8, 2.99e-6, 2.5e-6, 2.5e-6])
    pads = np.array([0, 0, 1, 1])
    # Each pad has cancelling real components; integrate complex J before abs/RMS.
    density = np.array([( .001-.001j)/area[0], (-.001-.001j)/area[1],
                        (-.0005+.001j)/area[2], (.0005+.001j)/area[3]])
    loss = np.array([2e-6, 1.1e-4, 9e-5, 1.88e-4, 1e-5, 1e-4], dtype=complex)
    za_real = loss[4].real / np.sum(abs(density)**2 * area / 2)
    za = za_real * (1-2j)
    layers = np.arange(4)
    gamma = np.array([2+0j, .5+.5j, 1.5+.2j, 3+.2j])
    # Consistent independent field-volume loss for each tissue layer.
    total = loss[:4].real / (gamma.real * np.sum(abs(field)**2, axis=1) / 2)
    return [field, current, density, pads, area, loss, za, layers, total, gamma]


class CenteredPostTests(unittest.TestCase):
    def test_metrics_bytes_only_change_the_genuine_case_literal(self):
        original = (ROOT / 'tools/task1_best1_pair_metrics.py').read_bytes()
        derived = (SOURCE / 'centered_metrics.py').read_bytes()
        old = b'baseline-square15-C1pair0-xy80'
        new = b'centered-square15-C1-y0-xy80-f3000'
        self.assertEqual(original.count(old), 1)
        self.assertEqual(derived, original.replace(old, new))
        self.assertEqual(derived.count(new), 1)
        self.assertNotIn(old, derived)

    def test_centered_case_requires_actual_two_y_zero_squares_and_one_output(self):
        good = centered_case()
        before = copy.deepcopy(good)
        self.assertIsNone(POST._validate_centered_case(good))
        self.assertEqual(good, before)
        for mutation in ('old_id', 'old_y', 'four_pads', 'two_outputs', 'area', 'polygon', 'resistor', 'node'):
            case = centered_case()
            if mutation == 'old_id': case['id'] = 'baseline-square15-C1pair0-xy80'
            elif mutation == 'old_y':
                for p in case['design']['pads']:
                    p['center_mm'][1] = -10.
                    for vertex in p['polygon_mm']: vertex[1] -= 10.
            elif mutation == 'four_pads': case['circuit']['n_pads'] = 4
            elif mutation == 'two_outputs': case['circuit']['n_outputs'] = 2
            elif mutation == 'area': case['expected_pad_areas_m2'][1] = 224e-6
            elif mutation == 'polygon': case['design']['pads'][1]['polygon_mm'][0][0] += .625
            elif mutation == 'resistor': case['circuit']['source_resistance_ohm'] = 0
            else: case['circuit']['pad_to_node']['1'] = 'out1'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                POST._validate_centered_case(case)

    def test_all_seventeen_burdens_coherent_kcl_weighted_p95_and_no_extra_loss_half(self):
        args = unit_arrays()
        before = [x.copy() if isinstance(x, np.ndarray) else x for x in args]
        actual = POST._unit_burdens(*args)
        field, current, density, pads, area, loss, za, layers, total, gamma = args
        jrms = abs(density) / math.sqrt(2)
        erms = np.sqrt(np.sum(abs(field)**2, axis=1) / 2)
        jskin = abs(gamma[:2]) * erms[:2]
        expected = dict(source_current_RMS_mA=math.sqrt(2), source_current_peak_mA=2.,
            contact_J_RMS_max_A_m2=jrms[0], contact_J_RMS_p95_A_m2=jrms[1],
            contact_voltage_RMS_max_V=jrms[0]*abs(za), bulk_skin_J_RMS_max_A_m2=jskin[0],
            bulk_skin_J_RMS_p95_A_m2=jskin[1], SC_power_W=2e-6, dermis_power_W=1.1e-4,
            skin_SC_plus_dermis_power_W=1.12e-4, fat_power_W=9e-5, muscle_power_W=1.88e-4,
            contact_power_W=1e-5, tissue_contact_power_W=.0004, source_resistor_power_W=.0001,
            source_power_W=.0005, loaded_metal_Vpp=.8)
        self.assertEqual(set(actual), set(expected))
        self.assertEqual(len(actual), 17)
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertTrue(math.isclose(actual[key], value, rel_tol=1e-12, abs_tol=1e-15), (key, actual[key], value))
        for new, old in zip(args, before):
            if isinstance(new, np.ndarray): np.testing.assert_array_equal(new, old)
            else: self.assertEqual(new, old)
        # Coherent patch integral differs from integrating nonnegative patch RMS.
        self.assertAlmostEqual(abs(np.sum(density[pads == 0]*area[pads == 0])), abs(current))
        self.assertGreater(np.sum(abs(density[pads == 0])*area[pads == 0]), abs(current))
        self.assertAlmostEqual(np.sum(jrms**2*za.real*area), actual['contact_power_W'])
        np.testing.assert_allclose(gamma.real*np.sum(abs(field)**2, axis=1)*total/2, loss[:4].real, rtol=1e-12)
        self.assertAlmostEqual(actual['source_power_W'], actual['tissue_contact_power_W']+actual['source_resistor_power_W'])
        self.assertEqual(actual['SC_power_W'], loss[0].real)
        self.assertNotEqual(actual['SC_power_W'], .5*loss[0].real)
        for mutation in ('pad_kcl', 'source_loss', 'nonfinite', 'layer'):
            broken = unit_arrays()
            if mutation == 'pad_kcl': broken[2][0] += 10000j
            elif mutation == 'source_loss': broken[5] *= .5
            elif mutation == 'nonfinite': broken[0][0, 0] = np.nan+0j
            else: broken[7][0] = 4
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                POST._unit_burdens(*broken)

    def test_complex128_little_endian_shape_order_exact_bytes_and_finite_guards(self):
        expected = np.array([[[1+2j, -3+4j, 5-6j], [7-8j, -9-10j, 11+12j]]], dtype='<c16')
        raw = expected.tobytes(order='C')
        actual = POST._complex_bytes(raw, (1, 2, 3))
        self.assertEqual(actual.shape, (1, 2, 3))
        np.testing.assert_array_equal(actual, expected)
        for broken, shape in ((raw+b'\x00', (1, 2, 3)), (raw[:-1], (1, 2, 3)),
                              (raw, (2, 2, 3)), (np.array([complex(1, float('nan'))], dtype='<c16').tobytes(), (1,)),
                              (np.array([complex(float('inf'), 0)], dtype='<c16').tobytes(), (1,))):
            with self.subTest(shape=shape, size=len(broken)), self.assertRaises(ValueError):
                POST._complex_bytes(broken, shape)


if __name__ == '__main__':
    unittest.main()
