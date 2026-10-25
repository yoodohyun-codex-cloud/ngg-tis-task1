import math
import unittest
import manual_ui as ui


class ManualSettings(unittest.TestCase):
    def settings(self):
        return dict(schema=ui.SCHEMA,groups={'EColour':{'cMin':0.,'cMax':10.},'wave':{'xMin':10.,'xMax':20.,'yMin':-5.,'yMax':5.}},overrides={'paper-map-TIS-am':{'cMin':1.,'cMax':3.}},colorTransform='log')
    def test_valid_independent_ranges_roundtrip(self):
        data=self.settings();saved=ui.validate_settings(data)
        self.assertEqual(saved,data);saved['groups']['wave']['yMax']=9
        self.assertEqual(data['groups']['wave']['yMax'],5)
    def test_invalid_or_overflowing_bounds_rejected(self):
        for low,high in ((1.,1.),(2.,1.),(float('nan'),2.),(-1e308,1e308),(0.,float('inf'))):
            data=self.settings();data['groups']['wave']['yMin']=low;data['groups']['wave']['yMax']=high
            with self.subTest(low=low,high=high),self.assertRaises(ValueError):ui.validate_settings(data)
    def test_half_pairs_and_negative_amplitude_colour_rejected(self):
        data=self.settings();del data['groups']['wave']['xMax']
        with self.assertRaises(ValueError):ui.validate_settings(data)
        data=self.settings();data['groups']['EColour']['cMin']=-1
        with self.assertRaises(ValueError):ui.validate_settings(data)
    def test_unknown_groups_paths_and_transform_rejected(self):
        for change in ('group','id','transform'):
            data=self.settings()
            if change=='group':data['groups']['external']={}
            if change=='id':data['overrides']={'../secret':{'cMin':0,'cMax':1}}
            if change=='transform':data['colorTransform']='javascript:alert(1)'
            with self.subTest(change=change),self.assertRaises(ValueError):ui.validate_settings(data)
    def test_helpers_are_source_only_and_no_storage_assumption(self):
        self.assertIn('window.task1ManualRanges',ui.SCRIPT)
        self.assertIn('눈금 직접 조절',ui.SECTION)
        self.assertNotIn('localStorage',ui.SCRIPT)
        self.assertNotIn('fetch(',ui.SCRIPT)


if __name__=='__main__':unittest.main()
