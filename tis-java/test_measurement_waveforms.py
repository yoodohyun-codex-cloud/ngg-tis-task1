"""Analytic spectra and strict immutable-case joins; no PDE execution."""
from pathlib import Path
import copy
import hashlib
import math
import unittest

import numpy as np
import test_single_vs_tis as basis_fixture
from depth_probe_comparison import DEFAULT_POINTS
from single_vs_tis import (_entry, _electrical, build_comparison,
                           loaded_terminal_vpp_bounds, QUADRATIC)
from measurement_waveforms import (coherent_spectrum, signed_waveform,
    spectral_statistics, fundamental_envelope, build_measurement_waveforms)


class AnalyticWaveformTests(unittest.TestCase):
    def test_coincident_frequencies_sum_before_RMS_and_signed_wave(self):
        frequencies, values = coherent_spectrum([7, 7, 21], [1+2j, -1-2j, .4j])
        self.assertEqual(frequencies, [7, 21])
        self.assertEqual(values[0,0], 0)
        stats, _ = spectral_statistics([7,7,21], [1+2j,-1-2j,.4j], 'V')
        self.assertAlmostEqual(stats[0]['RMS'], .4/math.sqrt(2))
        np.testing.assert_allclose(signed_waveform([7,7,21], [1+2j,-1-2j,.4j], [0,.01])[:,0],
                                   -.4*np.sin(2*np.pi*21*np.array([0,.01])), atol=1e-15)

    def test_signed_asymmetric_extrema_are_not_twice_absolute_peak(self):
        stats, metadata = spectral_statistics([1,2], [1,.5], 'V')
        value = stats[0]
        self.assertAlmostEqual(value['RMS'], math.sqrt(.625))
        self.assertLessEqual(value['peak_to_peak_lower'], 2.25+1e-13)
        self.assertGreaterEqual(value['peak_to_peak_upper'], 2.25-1e-13)
        self.assertLess(value['peak_to_peak_upper'], 2*value['absolute_peak_lower'])
        self.assertLessEqual(value['signed_min_lower'], -.75)
        self.assertGreaterEqual(value['signed_min_upper'], -.75)
        self.assertLessEqual(value['signed_max_lower'], 1.5)
        self.assertGreaterEqual(value['signed_max_upper'], 1.5)
        self.assertEqual(metadata['minimal_repetition_period_s'], 1.)

    def test_exact_two_tone_envelope_keeps_phase_excludes_third(self):
        time = np.array([0.,.013,.037,.1])
        q0, q1, q3 = .3*np.exp(.71j), .2*np.exp(-.24j), 90-30j
        actual = fundamental_envelope([2000,2010,6000], [q0,q1,q3], [2000,2010], time)
        expected = q0*np.exp(2j*np.pi*2000*time)+q1*np.exp(2j*np.pi*2010*time)
        np.testing.assert_allclose(actual['signed_voltage_V'], expected.real)
        np.testing.assert_allclose(actual['analytic_envelope_V'], abs(expected))
        self.assertAlmostEqual(actual['analytic_min_V'], .1)
        self.assertAlmostEqual(actual['analytic_max_V'], .5)
        self.assertAlmostEqual(actual['modulation_width_V'], .4)
        single = fundamental_envelope([2000,6000], [q0,q3], [2000], time)
        np.testing.assert_allclose(single['analytic_envelope_V'], [.3]*len(time), atol=1e-15)
        self.assertEqual(single['modulation_width_V'], 0)
        self.assertTrue(single['single_carrier_TIS_zero'])


class JoinedMeasurementTests(unittest.TestCase):
    def setUp(self):
        fixture = basis_fixture.SingleVsTisTests(methodName='test_same_actual_rms_and_no1vpp_cap_and_single_zero_tis')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        for row in (fixture.tis, fixture.single):
            row['waveform'] = 'square_3h'
            row['phase_deg'] = [29.,-17.] if row['output_channels'] == 2 else [41.]
            folder = Path(fixture.paths[row['id']]['basis_dir'])
            config = folder/'config.properties'
            text = config.read_text()+f"channels={row['output_channels']}\nsize_mm=15\nh_mm=.625\n"
            frequencies = [2000,2010,6000,6030] if row['output_channels'] == 2 else [2000,6000]
            text += 'frequencies='+','.join(map(str,frequencies))+'\n'
            text += ''.join(f'pad.{i}.x_mm={x}\npad.{i}.y_mm={y}\n' for i,(x,y) in enumerate(row['xy_mm']))
            config.write_text(text)
            normalized = {key:value for key,value in row.items() if key not in (*QUADRATIC,'max_source_current_RMS_mA')}
            row.update(_electrical(normalized,folder)[0])
            fixture.paths[row['id']]['config_sha256'] = hashlib.sha256(config.read_bytes()).hexdigest()
        data = build_comparison([fixture.tis],[fixture.single],fixture.paths)
        self.tis, self.single = data['references'][0], data['single_controls'][0]
        self.pair = data['comparisons'][0]
        self.assertEqual(self.pair['status'], 'complete')
        self.native = {'tis_1Vpp':self.probe(self.tis,1.),
                       'single_at_match':self.probe(self.single,self.pair['match']['required_single_source_Vpp'])}

    @staticmethod
    def probe(entry, scale):
        row = entry['conditions']
        frequencies = [2000,2010,6000,6030] if row['output_channels'] == 2 else [2000,6000]
        # Deliberately independent nativephi data, not E_RMS times tipspacing.
        values = np.array([.003+.001j,.002-.001j,.0004-.0002j,.0003+.0001j][:len(frequencies)])*scale
        axes = {}
        for axis, factor in (('X',1.),('Y',-.7)):
            phasors = values*factor
            lo,hi,_ = loaded_terminal_vpp_bounds(frequencies,phasors[:,None])
            axes[axis] = dict(DEFAULT_POINTS[axis],spacing_mm=5.,
                RMS_V=float(np.sqrt(np.sum(abs(phasors)**2)/2)),Vpp_lower_V=float(lo[0]),Vpp_upper_V=float(hi[0]),
                spectrum=[dict(frequency_Hz=f,delta_potential_re_V=float(value.real),delta_potential_im_V=float(value.imag))
                          for f,value in zip(frequencies,phasors)])
        return dict(id=entry['id'],status='complete',probe_kind='depth_differential_potential',
            source_Vpp_per_output=scale,conditions=row,axes=axes,
            source_normalization='0.5Vpeak through50ohm; exp(+jwt); commonGND',
            verification=dict(potential_export_available=True,source_loss_verified=True,phi_E_consistency={'passed':True}))

    def build(self, **kwargs):
        return build_measurement_waveforms(self.tis,self.single,self.pair,self.fixture.paths,native_probes=self.native,**kwargs)

    def test_real_loaded_source_minus_50I_and_shared_phase_origin(self):
        report = self.build(max_plot_samples=257)
        self.assertEqual(report['status'],'complete')
        self.assertEqual(report['shared_time']['origin_s'],0.)
        self.assertEqual(report['shared_time']['common_period_s'],.1)
        self.assertFalse(report['shared_time']['plot_samples_define_extrema'])
        for role in report['roles'].values():
            for source,loaded,current in zip(role['source']['outputs'],role['loaded']['outputs'],role['loaded']['current_outputs']):
                for window in ('full_period_values','short_window_values'):
                    np.testing.assert_allclose(np.array(source[window])-50*np.array(current[window]),loaded[window],atol=1e-15)
                spec = source['spectrum']
                self.assertAlmostEqual(source['full_period_values'][0],sum(p['real'] for p in spec))
            self.assertEqual(len(role['native_probe']['axes']['X']['full_period_values']),257)
            self.assertFalse(role['native_probe']['axes']['X']['fundamental_full_period']['is_direction_maximized_field_TIS'])
        single = report['roles']['single_same_RMS']
        self.assertGreater(single['source_Vpp_per_output'],1.)
        self.assertEqual(single['field_direction_max_TIS']['value_V_m'],0.)
        self.assertEqual(single['native_probe']['axes']['X']['fundamental_full_period']['modulation_width_V'],0.)
        self.assertFalse(report['new_physical_validation_performed'])

    def test_plot_decimation_never_changes_certified_stats_and_short_window(self):
        coarse,fine = self.build(max_plot_samples=65),self.build(max_plot_samples=4097)
        a=coarse['roles']['tis_fixed_1Vpp']['native_probe']['axes']['X']
        b=fine['roles']['tis_fixed_1Vpp']['native_probe']['axes']['X']
        self.assertEqual(a['stats'],b['stats'])
        self.assertEqual(coarse['shared_time']['short_window_duration_s'],.002)
        self.assertEqual(fine['shared_time']['short_window_time_s'][0],0.)
        self.assertAlmostEqual(fine['shared_time']['short_window_time_s'][-1],.002)
        # The2ms signal is evaluated from original phasors at exact timestamps.
        expected=signed_waveform([p['frequency_Hz'] for p in b['spectrum']],
            [complex(p['real'],p['imag']) for p in b['spectrum']],fine['shared_time']['short_window_time_s'])[:,0]
        np.testing.assert_allclose(expected,b['short_window_values'])

    def test_wrong_config_hash_matrix_hash_case_or_native_points_rejected(self):
        with self.subTest('config hash'):
            paths=copy.deepcopy(self.fixture.paths);paths['tis']['config_sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'config hash'):
                build_measurement_waveforms(self.tis,self.single,self.pair,paths,native_probes=self.native)
        with self.subTest('matrix hash'):
            entry=copy.deepcopy(self.tis);entry['verification']['input_sha256']['source-2000.bin']='0'*64
            with self.assertRaisesRegex(ValueError,'matrix hash join'):
                build_measurement_waveforms(entry,self.single,self.pair,self.fixture.paths,native_probes=self.native)
        with self.subTest('wrong config despite valid hash'):
            config=Path(self.fixture.paths['tis']['config_path']);original=config.read_text()
            config.write_text(original.replace('channels=2','channels=1'))
            paths=copy.deepcopy(self.fixture.paths);paths['tis']['config_sha256']=hashlib.sha256(config.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'output count'):
                build_measurement_waveforms(self.tis,self.single,self.pair,paths,native_probes=self.native)
            config.write_text(original)
        with self.subTest('probe coordinates'):
            native=copy.deepcopy(self.native);native['tis_1Vpp']['axes']['X']['plus_mm']=[2.5,0,19.]
            with self.assertRaisesRegex(ValueError,'endpoint coordinates'):
                build_measurement_waveforms(self.tis,self.single,self.pair,self.fixture.paths,native_probes=native)
        with self.subTest('case identity'):
            pair=dict(self.pair,tis_id='other-case')
            with self.assertRaisesRegex(ValueError,'IDs do not join'):
                build_measurement_waveforms(self.tis,self.single,pair,self.fixture.paths,native_probes=self.native)

    def test_missing_native_phi_is_explicit_not_inferred_from_E(self):
        report=build_measurement_waveforms(self.tis,self.single,self.pair,self.fixture.paths,native_probes={})
        self.assertEqual(report['status'],'partial_native_unavailable')
        self.assertEqual(report['roles']['tis_fixed_1Vpp']['native_probe'],{'status':'unavailable','axes':{}})

    def test_nonfinite_RMS_or_amplitude_cannot_claim_equivalence(self):
        for value in (float('inf'), float('nan')):
            for kind in ('target', 'amplitude'):
                with self.subTest(value=value, kind=kind):
                    tis, pair = copy.deepcopy(self.tis), copy.deepcopy(self.pair)
                    if kind == 'target':
                        tis['metrics_at_1Vpp']['target20_total_E_RMS_V_m'] = value
                    else:
                        pair['match']['required_single_source_Vpp'] = value
                    with self.assertRaisesRegex(ValueError, 'Finite'):
                        build_measurement_waveforms(tis, self.single, pair, self.fixture.paths,
                                                    native_probes=self.native)


if __name__=='__main__':
    unittest.main()
