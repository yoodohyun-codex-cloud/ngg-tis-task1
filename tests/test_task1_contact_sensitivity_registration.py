"""Synthetic interface-impedance tests; no research imports or preparation."""
import copy
import contextlib
import io
import math
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_contact_sensitivity_registration as r


def profile():
    points=[]
    for i in range(30):
        frequency=10**(2+3*i/29)
        t=math.log10(frequency/100)
        points.append(dict(frequency_Hz=frequency,Z_real_ohm=500-20*t,Z_imag_ohm=-300+10*t))
    return dict(measurement_area_m2=1e-4,points=points)


def fit(rs=25.):
    return dict(status='complete',selected_fit=dict(Rs_ohm=rs),selected_subtraction_passive=True)


def config(rows):
    text=('sc.sigma=0.0002\nsc.epsilon_r=110000\ndermis.sigma=0.2\n'
        'h_mm=0.5\nchannels=2\nfrequencies=3000,3030,9000,9090\n'
        'validation.sc_cells=8\nbulk.counts=18,18,56\n'
        'mask.path=/tmp/original-mask.csv\nmask.sha256='+'a'*64+'\n')
    for row in rows:
        f=row['frequency_Hz']
        text+=f'z.{f}.re={row["area_real_ohm_m2"]:.17g}\nz.{f}.im={row["area_imag_ohm_m2"]:.17g}\n'
    for pad,(x,y) in enumerate(((-10,-10),(10,10),(10,-10),(-10,10))):
        text+=(f'pad.{pad}.shape=rectangle\npad.{pad}.x_mm={x}\npad.{pad}.y_mm={y}\n'
            f'pad.{pad}.width_mm=15\npad.{pad}.height_mm=15\npad.{pad}.rotation_deg=0\n'
            f'pad.{pad}.analytic_area_mm2=225\npad.{pad}.represented_area_m2=0.000225\n')
    return text


class ContactSensitivityTests(unittest.TestCase):
    def setUp(self):
        self.profile=profile();self.fit=fit()

    def test_log_frequency_interpolates_real_and_imaginary_raw_components(self):
        points=[dict(frequency_Hz=1000.,Z_real_ohm=100.,Z_imag_ohm=-50.),
                dict(frequency_Hz=10000.,Z_real_ohm=200.,Z_imag_ohm=-150.)]
        z=r.interpolate_raw_complex(points,math.sqrt(1000*10000))
        self.assertAlmostEqual(150.,z.real,places=12)
        self.assertAlmostEqual(-100.,z.imag,places=12)
        self.assertEqual(complex(100.,-50.),r.interpolate_raw_complex(points,1000.))
        for f in (0.,999.,10001.,math.nan):
            with self.assertRaises(ValueError):r.interpolate_raw_complex(points,f)

    def test_rs_is_subtracted_once_before_single_measured_area_normalization(self):
        rows=r.derive_contact_rows(self.profile,self.fit)
        self.assertEqual((3000,3030,9000,9090),tuple(row['frequency_Hz'] for row in rows))
        for row in rows:
            t=math.log10(row['frequency_Hz']/100)
            self.assertAlmostEqual((500-20*t-25)*1e-4,row['area_real_ohm_m2'],places=14)
            self.assertAlmostEqual((-300+10*t)*1e-4,row['area_imag_ohm_m2'],places=14)
        other=r.derive_contact_rows(self.profile,fit(40.))
        for a,b in zip(rows,other):
            self.assertAlmostEqual(15e-4,a['area_real_ohm_m2']-b['area_real_ohm_m2'],places=14)
            self.assertEqual(a['area_imag_ohm_m2'],b['area_imag_ohm_m2'])

    def test_nonpassive_nonfinite_or_mismatched_measurement_area_is_rejected(self):
        for area in (0.,1e-3,math.nan):
            p=copy.deepcopy(self.profile);p['measurement_area_m2']=area
            with self.assertRaises(ValueError):r.derive_contact_rows(p,self.fit)
        with self.assertRaises(ValueError):r.derive_contact_rows(self.profile,fit(600.))
        invalid=fit();invalid['selected_subtraction_passive']=False
        with self.assertRaises(ValueError):r.derive_contact_rows(self.profile,invalid)
        for field in ('Z_real_ohm','Z_imag_ohm'):
            p=copy.deepcopy(self.profile);p['points'][10][field]=math.nan
            with self.assertRaises(ValueError):r.derive_contact_rows(p,self.fit)

    def test_raw_frequency_order_and_coverage_are_required(self):
        for points in (list(reversed(self.profile['points'])),
                       [self.profile['points'][0],self.profile['points'][0]],
                       self.profile['points'][:2]):
            p=copy.deepcopy(self.profile);p['points']=points
            with self.assertRaises(ValueError):r.derive_contact_rows(p,self.fit)

    def test_stale_presubtracted_legacy_carriers_never_feed_actual_carrier_values(self):
        expected=r.derive_contact_rows(self.profile,self.fit)
        stale=copy.deepcopy(self.profile)
        stale['carriers']=[dict(frequency_Hz=2000,area_real_ohm_m2=-1000.,area_imag_ohm_m2=1000.),
                           dict(frequency_Hz=3000,area_real_ohm_m2=777.,area_imag_ohm_m2=888.)]
        self.assertEqual(expected,r.derive_contact_rows(stale,self.fit))
        self.assertTrue(r.verify_nominal_contact(stale,self.fit,config(expected)))

    def test_nominal_verifier_requires_actual_raw_rs500_contact_equality(self):
        rows=r.derive_contact_rows(self.profile,self.fit);text=config(rows)
        self.assertTrue(r.verify_nominal_contact(self.profile,self.fit,text))
        stale=text.replace('z.3000.re='+format(rows[0]['area_real_ohm_m2'],'.17g'),'z.3000.re=0.12345')
        with self.assertRaises(ValueError):r.verify_nominal_contact(self.profile,self.fit,stale)

    def test_transform_preserves_geometry_wiring_mask_hash_and_all_noncontact_fields(self):
        nominal=r.derive_contact_rows(self.profile,self.fit)
        varied=r.derive_contact_rows(self.profile,fit(40.))
        original=config(nominal)
        changed=r.transform_config(original,Path('/tmp/new-mask.csv'),varied)
        self.assertIsInstance(changed,bytes)
        a,b=r.parse_properties(original),r.parse_properties(changed)
        allowed={'mask.path'}|{f'z.{f}.{part}'for f in (3000,3030,9000,9090)for part in ('re','im')}
        self.assertEqual(set(a),set(b))
        self.assertEqual({k:v for k,v in a.items()if k not in allowed},
                         {k:v for k,v in b.items()if k not in allowed})
        self.assertEqual('/tmp/new-mask.csv',b['mask.path'])
        for pad in range(4):
            self.assertEqual('0.000225',b[f'pad.{pad}.represented_area_m2'])
        for row in varied:
            self.assertEqual(row['area_real_ohm_m2'],float(b[f'z.{row["frequency_Hz"]}.re']))
            self.assertEqual(row['area_imag_ohm_m2'],float(b[f'z.{row["frequency_Hz"]}.im']))

    def test_batch_has_exactly_two_cases_and_preserves_explicit_remaining_budget_floor(self):
        self.assertEqual(2,len(r.CASE_IDS));self.assertEqual(2,len(set(r.CASE_IDS)))
        self.assertEqual(1380,r.MIN_REMAINING_SECONDS)

    def test_cli_freezes_successful_preparation_exactly_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run=root/'new-run'
            fake=types.SimpleNamespace(freeze_sources=mock.Mock())
            with mock.patch.object(r,'ROOT',root), mock.patch.object(r,'prepare_contact_sensitivity',
                    return_value={'status':'prepared'}) as prepare, \
                    mock.patch.dict(sys.modules,{'task1_cloud_batch':fake}), \
                    mock.patch.object(sys,'argv',['sensitivity','--prepare','--output',str(run)]), \
                    contextlib.redirect_stdout(io.StringIO()):
                r.main()
            prepare.assert_called_once_with(run)
            fake.freeze_sources.assert_called_once_with(run.resolve())

    def test_cli_never_freezes_failed_preparation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            fake=types.SimpleNamespace(freeze_sources=mock.Mock())
            with mock.patch.object(r,'ROOT',root), mock.patch.object(r,'prepare_contact_sensitivity',
                    side_effect=ValueError('synthetic preparation failure')), \
                    mock.patch.dict(sys.modules,{'task1_cloud_batch':fake}), \
                    mock.patch.object(sys,'argv',['sensitivity','--prepare','--output',str(root/'new-run')]):
                with self.assertRaisesRegex(ValueError,'synthetic preparation failure'):
                    r.main()
            fake.freeze_sources.assert_not_called()


if __name__=='__main__':
    unittest.main()
