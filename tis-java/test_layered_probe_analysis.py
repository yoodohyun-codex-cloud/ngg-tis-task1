"""Analytic layered-potential tests only: no PDE, Java, cache or GUI writes."""
import copy
import math
import unittest

import numpy as np

from layered_probe_analysis import (DEFAULT_LAYERS, FIELD_RECONSTRUCTION,
    LayeredPotentialSampler, ProbeDataMissing, SamplingLimits, coherent_spectrum,
    evaluate_layered_probe, probe_layout, waveform_statistics)


class LayeredProbeTests(unittest.TestCase):
    def setUp(self):
        faces = [0.]
        for layer, count in zip(DEFAULT_LAYERS, (4, 14, 14, 40)):
            faces.extend(np.linspace(layer['z_min_mm'], layer['z_max_mm'], count+1)[1:])
        z = (np.asarray(faces[:-1])+faces[1:])/2
        self.grid = np.array([(x, y, depth,
            next(layer['id'] for layer in DEFAULT_LAYERS
                 if layer['z_min_mm'] < depth < layer['z_max_mm']))
            for depth in z for y in np.arange(-10, 10.1, 2.5)
            for x in np.arange(-10, 10.1, 2.5)],
            dtype=[('x_mm', float), ('y_mm', float), ('z_mm', float), ('layer', int)])
        self.geometry = dict(coordinate_system=dict(unit='mm', surface_z_mm=0., depth_axis='+z'),
            radius_mm=25., layers=copy.deepcopy(DEFAULT_LAYERS), z_faces_mm=faces,
            field_reconstruction=FIELD_RECONSTRUCTION,
            basis_normalization=dict(source_peak_V=.5, source_Vpp=1., source_resistance_ohm=50.,
                                     phasor_exponent='+jomega_t'))
        self.gamma = {0: .0002+.012j, 1: .2+.001j, 2: .04+.0001j, 3: .3+.01j}
        self.provenance = dict(source_run_id='synthetic-only', source_condition_id='analytic-layered',
            source_candidate_id='synthetic-phase', input_sha256='1'*64, code_sha256='2'*64,
            result_sha256='3'*64)

    def analytic_potential(self, xyz, gradients, normal_flux):
        xyz = np.asarray(xyz)
        integral = np.zeros(len(xyz), complex)
        for layer in DEFAULT_LAYERS:
            length = np.maximum(0., np.minimum(xyz[:, 2], layer['z_max_mm'])-layer['z_min_mm'])
            integral += length/1000/self.gamma[layer['id']]
        return (.23+.017j + np.asarray(gradients) @ (xyz[:, :2]/1000).T -
                np.asarray(normal_flux)[:, None]*integral)

    def analytic_arrays(self, gradients=((1+2j, 3-.5j), (-.2+.1j, .4+1j)), normal_flux=(.03+.02j, -.01j)):
        phi = self.analytic_potential(np.stack([self.grid[n] for n in ('x_mm', 'y_mm', 'z_mm')], axis=1), gradients, normal_flux)
        field = np.empty((*phi.shape, 3), complex)
        field[..., :2] = -np.asarray(gradients)[:, None, :]
        field[..., 2] = np.asarray(normal_flux)[:, None]/np.array([self.gamma[int(l)] for l in self.grid['layer']])[None, :]
        return phi, field

    def evaluate(self, phi=None, field=None, geometry=None):
        if phi is None:
            phi, field = self.analytic_arrays()
        geometry = copy.deepcopy(geometry or self.geometry)
        geometry['gamma_S_m'] = {3000: self.gamma, 3030: self.gamma, 9000: self.gamma}
        return evaluate_layered_probe(self.grid, {f: phi for f in (3000, 3030, 9000)},
            {f: field for f in (3000, 3030, 9000)}, geometry,
            {3000: np.array([-1j, 0]), 3030: np.array([0, np.exp(.3j)]),
             9000: np.array([-.1j*np.exp(.6j), 0])},
            provenance=self.provenance, fundamental_frequencies_Hz=[3000, 3030])

    def test_exact_40_endpoint_coordinates_and_distinct_pitch_gap(self):
        layout = probe_layout()
        self.assertEqual(len(layout), 40)
        self.assertEqual(len({row['id'] for row in layout}), 40)
        d5 = next(r for r in layout if r['id'] == 'd5-x_plus-X')
        self.assertEqual(d5['centre_mm'], [5, 0, 5])
        self.assertEqual(d5['plus_mm'], [7.5, 0, 5])
        self.assertEqual(d5['minus_mm'], [2.5, 0, 5])
        alternate = probe_layout(plus_pitch_mm=6, tip_gap_mm=5)
        row = next(r for r in alternate if r['id'] == 'd20-y_minus-Y')
        self.assertEqual(row['centre_mm'], [0, -6, 20])
        self.assertEqual(row['plus_mm'], [0, -3.5, 20])
        self.assertEqual(row['minus_mm'], [0, -8.5, 20])
        for row in alternate:
            self.assertAlmostEqual(np.linalg.norm(np.array(row['plus_mm'])-row['minus_mm']), 5)

    def test_series_impedance_interpolation_near_dermis_and_fat_boundary(self):
        phi, field = self.analytic_arrays()
        sampler = LayeredPotentialSampler(self.grid, self.geometry)
        for point, touched in [([1.25, -.75, 5.], [1, 2]), ([1.25, -.75, 10.], [2, 3]),
                               ([0, 0, 15], [3]), ([0, 0, 20], [3]), ([0, 0, 5.1], [1, 2])]:
            stencil = sampler.stencil(point, self.gamma)
            self.assertEqual(stencil['layer_ids'], touched)
            actual = sampler.interpolate(phi, stencil)
            expected = self.analytic_potential([point], ((1+2j, 3-.5j), (-.2+.1j, .4+1j)), (.03+.02j, -.01j))[:, 0]
            np.testing.assert_allclose(actual, expected, atol=2e-15)
        nodes = set()
        for row in probe_layout():
            for end in ('plus_mm', 'minus_mm'):
                nodes.update(sampler.stencil(row[end], self.gamma)['indices'])
        gate = sampler.phi_e_consistency(phi, field, nodes, self.gamma)
        self.assertTrue(gate['passed'])
        self.assertEqual(set(gate['checked_cells_by_layer']), {'1', '2', '3'})
        self.assertGreater(gate['interface_adjacent_cell_count'], 0)
        # A generic z-linear cross-layer interpolation does not reproduce phi.
        p = np.array([0., 0., 5.])
        hi = np.searchsorted(sampler.axes[2], 5.)
        loz, hiz = sampler.axes[2][hi-1:hi+1]
        ends = self.analytic_potential([[0, 0, loz], [0, 0, hiz]], ((1, 1), (1, 1)), (.03, .03))
        generic = ends[:, 0] + (ends[:, 1]-ends[:, 0])*(5-loz)/(hiz-loz)
        exact = self.analytic_potential([p], ((1, 1), (1, 1)), (.03, .03))[:, 0]
        self.assertGreater(float(np.max(abs(generic-exact))), 1e-7)

    def test_all_40_layered_waveforms_preserve_spectrum_phase_and_instrument_planes(self):
        result = self.evaluate()
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['counts']['complete'], 40)
        self.assertTrue(result['numerical_checks']['all_passed'])
        self.assertFalse(result['new_PDE_executed'])
        self.assertTrue(result['unloaded_prediction'])
        x = next(row for row in result['measurements'] if row['id'] == 'd20-centre-X')
        expected = [.005*(1+2j)*-1j, .005*(-.2+.1j)*np.exp(.3j),
                    .005*(1+2j)*-.1j*np.exp(.6j)]
        np.testing.assert_allclose([complex(s['real_V'], s['imaginary_V']) for s in x['spectrum']], expected, atol=2e-15)
        self.assertAlmostEqual(x['RMS_V'], np.linalg.norm(expected)/math.sqrt(2), places=13)
        self.assertAlmostEqual(x['common_period']['period_s'], 1/30)
        for instrument in x['nominal_instrument']:
            self.assertAlmostEqual(instrument['BNC_Vpp_lower_V']*instrument['attenuation'], x['Vpp_lower_V'])
            self.assertEqual(instrument['displayed_Vpp_lower_V'], x['Vpp_lower_V'])
            self.assertEqual(instrument['scope_probe_factor'], instrument['attenuation'])
        self.assertEqual(result['shared_plot_axes']['time_ms'], [0, 2])
        self.assertIsNotNone(result['shared_plot_axes']['voltage_V'])
        self.assertEqual(result['coordinate_system']['surface_z_mm'], 0)
        self.assertEqual(result['measurements'][0]['tissue_at_probe_depth']['layer_names'], ['dermis'])
        d10 = next(row for row in result['measurements'] if row['id'] == 'd10-centre-X')
        self.assertEqual(d10['tissue_at_probe_depth']['layer_names'], ['fat'])
        self.assertEqual(result['drive_coefficients'][0]['imaginary_by_basis_channel'], [-1, 0])

    def test_independent_sc_refinement_and_actual_xy_grid_are_not_assumed(self):
        # The common bulk-z grid remains fixed while SC cell counts change.
        for count in (2, 4, 8):
            faces = list(np.linspace(0, .1, count+1))
            for layer, n in zip(DEFAULT_LAYERS[1:], (14, 14, 40)):
                faces.extend(np.linspace(layer['z_min_mm'], layer['z_max_mm'], n+1)[1:])
            z = (np.asarray(faces[:-1])+faces[1:])/2
            # Independently refined, nonuniform local XY samples are explicit.
            xy = [-10, -8, -6, -4, -2, 0, 1, 3, 5, 7, 10]
            grid = np.array([(x, y, depth,
                next(l['id'] for l in DEFAULT_LAYERS if l['z_min_mm'] < depth < l['z_max_mm']))
                for depth in z for y in xy for x in xy], dtype=self.grid.dtype)
            geometry = copy.deepcopy(self.geometry)
            geometry['z_faces_mm'] = faces
            sampler = LayeredPotentialSampler(grid, geometry)
            phi = self.analytic_potential(np.stack([grid[n] for n in ('x_mm', 'y_mm', 'z_mm')], axis=1),
                                          ((1, 2),), (.03,))
            for depth in (5, 10, 15, 20):
                point = [2.5, -.75, depth]
                actual = sampler.interpolate(phi, sampler.stencil(point, self.gamma))
                expected = self.analytic_potential([point], ((1, 2),), (.03,))[:, 0]
                np.testing.assert_allclose(actual, expected, atol=2e-15)

    def test_same_frequency_coherent_sum_before_rms_and_full_period_asymmetry(self):
        frequencies, values = coherent_spectrum([3000, 3000, 3030], [1+2j, -1-2j, 2j])
        self.assertEqual(frequencies, [3000, 3030])
        self.assertEqual(values[0], 0)
        stats = waveform_statistics([1, 2], np.array([1, .5]), [1, 2])
        self.assertLessEqual(stats['Vpp_lower_V'], 2.25+1e-12)
        self.assertGreaterEqual(stats['Vpp_upper_V'], 2.25-1e-12)
        self.assertLess(stats['Vpp_upper_V'], 2*stats['sampled_max_V'])
        self.assertAlmostEqual(stats['fundamental_fixed_axis_envelope']['variation_range_V'], 1)
        self.assertAlmostEqual(stats['fundamental_fixed_axis_envelope']['modulation_index'], .5)
        single = waveform_statistics([3000], [1j], [3000])
        self.assertEqual(single['fundamental_fixed_axis_envelope']['variation_range_V'], 0)
        self.assertEqual(single['fundamental_fixed_axis_envelope']['modulation_index'], 0)
        phase = waveform_statistics([1, 2], np.array([1, .5j]), [1, 2])
        self.assertNotAlmostEqual(phase['Vpp_lower_V'], stats['Vpp_lower_V'], places=3)

    def test_missing_metadata_wrong_tissue_and_nan_are_not_bypassed(self):
        geometry = copy.deepcopy(self.geometry)
        del geometry['z_faces_mm']
        with self.assertRaises(ProbeDataMissing):
            LayeredPotentialSampler(self.grid, geometry)
        bad = self.grid.copy()
        bad['layer'][bad['z_mm'] == np.unique(bad['z_mm'])[10]] = 2
        with self.assertRaisesRegex(ValueError, 'tissue label'):
            LayeredPotentialSampler(bad, self.geometry)
        sampler = LayeredPotentialSampler(self.grid, self.geometry)
        with self.assertRaises(ProbeDataMissing):
            sampler.stencil([0, 0, 5], {})
        with self.assertRaises(ProbeDataMissing):
            sampler.stencil([0, 0, 25.099], self.gamma)
        with self.assertRaises(ProbeDataMissing):
            sampler.stencil([24, 24, 20], self.gamma)
        phi, field = self.analytic_arrays()
        phi[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            self.evaluate(phi, field)

    def test_algebraic_failure_is_reported_per_probe_not_silently_discarded(self):
        phi, field = self.analytic_arrays()
        field[..., 0] += .01
        result = self.evaluate(phi, field)
        self.assertEqual(result['status'], 'validation_failed')
        self.assertEqual(result['counts']['validation_failed'], 40)
        self.assertEqual(len(result['measurements']), 40)
        self.assertTrue(all('RMS_V' not in row for row in result['measurements']))

    def test_explicit_period_and_plot_caps_and_no_frequency_rounding(self):
        with self.assertRaises(ProbeDataMissing):
            waveform_statistics([3000, 3001], [1, 1], [3000, 3001],
                                SamplingLimits(max_statistics_samples=1024))
        with self.assertRaises(ProbeDataMissing):
            waveform_statistics([3000.1], [1], [3000])
        with self.assertRaises(ValueError):
            waveform_statistics([3000], [1], [3000], SamplingLimits(plot_duration_s=.003))
        with self.assertRaises(ValueError):
            waveform_statistics([3000], [1], [3010])


if __name__ == '__main__':
    unittest.main()
