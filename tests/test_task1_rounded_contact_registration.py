"""Synthetic complex-contact uncertainty contracts; no native arrays or PDE."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_rounded_contact_registration as r
import task1_rounded_fullface_registration as rounded
import task1_rounded_sc4_registration as sc4


class RoundedContactRegistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline=next(d for d in json.loads((rounded.core.HIST/'inputs/designs.json').read_text())
            if d['id']=='baseline-square15')
        cls.design,cls.rows,cls.areas,_=rounded.rounded_design(baseline)
        cls.mask=rounded._mask_bytes(cls.rows);cls.mask_sha=hashlib.sha256(cls.mask).hexdigest()
        cls.source=dict(rounded.COMMON,id=sc4.CASE_ID,design=cls.design,expected_pad_areas_m2=cls.areas,
            mask_sha256=cls.mask_sha,h_xy_mm=.625,sc_cells=4,bulk_counts=[14,14,40],channels=2,cells=361728,
            frequencies_Hz=[3000,3030,9000,9090],
            circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
                source_resistance_ohm=50,source_peak_V=.5))
        data=(rounded.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        data,_=rounded.changed_rounded_config(data,cls.design,Path('/tmp/nominal-rounded.csv'),cls.mask_sha)
        cls.config,_=sc4.changed_sc4_config(data,Path('/tmp/nominal-rounded-SC4.csv'))

    def test_both_complex_parts_receive_exact_factor_with_no_Rs_or_area_change(self):
        before=rounded._properties(self.config);zkeys={f'z.{f}.{p}'for f in(3000,3030,9000,9090)for p in('re','im')}
        for factor in(.5,2.):
            with self.subTest(factor=factor):
                after_bytes,changes=r.changed_contact_config(self.config,Path('/tmp/contact-copy.csv'),factor)
                after=rounded._properties(after_bytes)
                self.assertEqual(zkeys|{'mask.path'},set(changes));self.assertEqual(set(before),set(after))
                self.assertEqual({k:v for k,v in before.items()if k not in changes},{k:v for k,v in after.items()if k not in changes})
                self.assertEqual(before['mask.sha256'],after['mask.sha256'])
                for key in zkeys:
                    self.assertTrue(math.isclose(float(after[key]),float(before[key])*factor,rel_tol=1e-14,abs_tol=1e-16))
                for key in before:
                    if key.startswith('pad.')or key in('h_mm','validation.sc_cells','bulk.counts','channels','frequencies'):
                        self.assertEqual(before[key],after[key])

    def test_unregistered_scale_nonpassive_real_or_nonfinite_imaginary_is_rejected(self):
        for scale in(0.,1.,-0.5,3.,float('nan'),float('inf'),True):
            with self.subTest(scale=scale),self.assertRaises(ValueError):
                r.changed_contact_config(self.config,Path('/tmp/new.csv'),scale)
        properties=rounded._properties(self.config)
        for key,value in [('z.3000.re','0'),('z.3030.re','-0.0001'),('z.9000.re','nan'),('z.9090.im','inf')]:
            bad=rounded._changed_config(self.config,{key:value})
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                r.changed_contact_config(bad,Path('/tmp/new.csv'),.5)
        self.assertTrue(all(float(properties[f'z.{f}.re'])>0 for f in(3000,3030,9000,9090)))

    def test_source_grid_and_two_output_four_frequency_scope_cannot_change(self):
        for key,value in [('h_mm','0.5'),('validation.sc_cells','2'),('bulk.counts','18,18,56'),
            ('channels','4'),('frequencies','3000,3030')]:
            bad=rounded._changed_config(self.config,{key:value})
            with self.subTest(key=key),self.assertRaises(ValueError):r.changed_contact_config(bad,Path('/tmp/new.csv'),2.)
        self.assertEqual('4',rounded._properties(self.config)['validation.sc_cells'])

    def test_nominal_source_reuses_exact_SC4_mask_and_frozen_physical_outline(self):
        before=copy.deepcopy(self.source);mask=self.mask
        receipt=r.validate_nominal_source(self.source,mask)
        self.assertTrue(receipt['physical_geometry_unchanged']);self.assertEqual(self.mask_sha,receipt['mask_byte_SHA256'])
        self.assertEqual(before,self.source);self.assertEqual(mask,self.mask)
        self.assertEqual(2304,len(self.rows));self.assertEqual([576]*4,[sum(q==p for q,i,j,a in self.rows)for p in range(4)])

    def test_mask_contour_area_wiring_or_nominal_source_identity_drift_is_rejected(self):
        for change in('id','sc','shape','wire','outline','mask','area'):
            source=copy.deepcopy(self.source);mask=self.mask
            if change=='id':source['id']=rounded.CASE_ID
            elif change=='sc':source['sc_cells']=2
            elif change=='shape':source['design']['pads'][0]['shape']='circle'
            elif change=='wire':source['design']['pads'][2]['source_output']=2
            elif change=='outline':source['design']['pads'][1]['polygon_mm'][0][0]+=.625
            elif change=='area':source['expected_pad_areas_m2'][0]*=.99
            else:
                rows=list(self.rows);p,i,j,a=rows[0];rows[0]=(p,i,j,a*.25);mask=rounded._mask_bytes(rows)
                source['mask_sha256']=hashlib.sha256(mask).hexdigest()
            with self.subTest(change=change),self.assertRaises(ValueError):r.validate_nominal_source(source,mask)

    def test_finite_two_case_resource_bound_and_failed_context_preserve_evidence_without_jvm(self):
        self.assertEqual(('rounded-fullface225-contact0p5-sc4-xy80','rounded-fullface225-contact2-sc4-xy80'),r.CASE_IDS)
        self.assertEqual(361728,r.EXPECTED_CELLS);self.assertLessEqual(r.EXPECTED_CELLS,800000)
        self.assertEqual(434073600,r.EXPECTED_RAW_BOUND_BYTES);self.assertEqual(2*r.EXPECTED_CELLS*600,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(1800,r.MIN_REMAINING_SECONDS);self.assertEqual(120,r.PREPARATION_SECONDS)
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);(root/'data-native').mkdir();(root/'runtime').mkdir();run=root/'data-native/cloud-synthetic-rounded-contact'
            ledger=dict(limit_seconds=13800,spent_seconds=7.,runs=[dict(stage='past',seconds=7.)])
            r.core.write(root/'runtime/task1-budget.json',ledger)
            with mock.patch.object(r.core,'REPO',root),mock.patch.object(r,'_caller_owns_execution_lock'),mock.patch.object(r.os,'sched_setaffinity'),\
                mock.patch.object(r.policy,'load_ledger',return_value=copy.deepcopy(ledger)),\
                mock.patch.object(r.policy,'effective_limit',return_value=13800),\
                mock.patch.object(r,'verify_context',side_effect=ValueError('synthetic completed-SC4 context drift')),\
                mock.patch.object(r.subprocess,'Popen')as popen:
                with self.assertRaisesRegex(ValueError,'completed-SC4 context drift'):
                    r.prepare_rounded_contact(run,root/'decision.json',root/'feedback.json')
            popen.assert_not_called();self.assertFalse(run.exists())
            self.assertTrue(run.with_name(run.name+'.preparation-failure.json').is_file())
            after=r.core.read(root/'runtime/task1-budget.json')
            self.assertGreater(after['spent_seconds'],7.);self.assertEqual(ledger['runs'],after['runs'][:1])


if __name__=='__main__':unittest.main()
