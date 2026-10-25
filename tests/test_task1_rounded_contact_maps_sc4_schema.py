"""SC4 physical outlines stay genuine; research contrast flags are not geometry."""
from pathlib import Path
import json
import copy
import sys
import unittest
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'tools'))
import task1_rounded_contact_maps as m
class SC4PhysicalContacts(unittest.TestCase):
    def test_actual_sc4_cases_preserve_identity_and_never_claim_shape_only(self):
        runs=['cloud-rounded-sc4-20261021T204000Z','cloud-rounded-contact-20261021T210000Z']
        for run in runs:
            for case in json.loads((R/'data-native'/run/'preregistration.json').read_text())['cases']:
                before=copy.deepcopy(case);self.assertFalse(case['shape_only_contrast']);self.assertEqual(4,case['sc_cells'])
                shapes=m.validate_sc4_contact_shapes(case)
                self.assertEqual([70.]*4,[p['perimeter_mm']for p in shapes]);self.assertEqual(before,case)
                bad=copy.deepcopy(case);bad['sc_cells']=2
                with self.assertRaises(ValueError):m.validate_sc4_contact_shapes(bad)
                bad=copy.deepcopy(case);bad['design']['pads'][0]['analytic_area_mm2']=224
                with self.assertRaises(ValueError):m.validate_sc4_contact_shapes(bad)
