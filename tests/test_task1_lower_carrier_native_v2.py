"""Recovery tests preserve the frozen original loader and released mask."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tests'))
import task1_lower_carrier_native_v2 as r
from test_task1_lower_carrier_native import make_fixture

ORIGINAL=ROOT/'tis-java/runs/selectivity-design-20261019T155933Z/masks/baseline-square15-h0.625.csv'
ORIGINAL_SHA256='7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2'
ONE_ULP_BELOW=3.9062499999999997e-7
FULL_FACE=(.625/1000)**2


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def original_rows():
    return np.genfromtxt(ORIGINAL,delimiter=',',names=True)


def set_csv_areas(path,area):
    with Path(path).open(newline='')as stream:
        reader=csv.DictReader(stream);columns=reader.fieldnames;rows=list(reader)
    for row in rows:row['area_m2']=format(area,'.17g')
    with Path(path).open('w',newline='')as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


class LowerCarrierNativeV2Tests(unittest.TestCase):
    def test_released_mask_one_ulp_area_is_accepted_without_changing_original_bytes(self):
        before=sha(ORIGINAL);rows=original_rows()
        self.assertEqual(ORIGINAL_SHA256,before)
        self.assertEqual(2304,len(rows));self.assertTrue(np.any(rows['area_m2']==ONE_ULP_BELOW))
        receipt=r._validate_full_face_mask(rows)
        self.assertEqual(2304,receipt['contact_count'])
        self.assertEqual(4*np.finfo(float).eps,receipt['full_face_relative_tolerance'])
        self.assertEqual(0.,receipt['full_face_absolute_tolerance'])
        self.assertLessEqual(receipt['maximum_relative_area_error'],4*np.finfo(float).eps)
        self.assertEqual(before,sha(ORIGINAL))

    def test_direct_h_squared_and_all_one_ulp_below_full_faces_are_both_valid(self):
        for area in (FULL_FACE,ONE_ULP_BELOW):
            rows=original_rows();rows['area_m2']=area
            receipt=r._validate_full_face_mask(rows)
            self.assertEqual(2304,receipt['contact_count'])
            self.assertLessEqual(receipt['maximum_relative_area_error'],4*np.finfo(float).eps)

    def test_finite_partial_faces_and_one_e_minus8_relative_area_change_are_rejected(self):
        for area in (FULL_FACE*(1-1e-8),FULL_FACE/4):
            rows=original_rows();rows['area_m2'][0]=area
            with self.assertRaises(ValueError):r._validate_full_face_mask(rows)

    def test_wrong_geometry_count_duplicate_and_noninteger_indices_are_rejected(self):
        changes=[]
        rows=original_rows();rows['i'][0]=0.;changes.append(rows)
        rows=original_rows();rows['j'][0]=0.;changes.append(rows)
        rows=original_rows();rows['pad'][0]=4.;changes.append(rows)
        rows=original_rows();rows['i'][0]+=.5;changes.append(rows)
        rows=original_rows();rows[1]=rows[0];changes.append(rows)
        changes.append(original_rows()[:-1])
        changes.append(original_rows().reshape(4,576))
        changes.append(original_rows()[['pad','j','area_m2']])
        for rows in changes:
            with self.assertRaises(ValueError):r._validate_full_face_mask(rows)

    def test_nonfinite_or_negative_area_is_rejected(self):
        for area in (np.nan,np.inf,-FULL_FACE,0.):
            rows=original_rows();rows['area_m2'][0]=area
            with self.assertRaises(ValueError):r._validate_full_face_mask(rows)

    def test_synthetic_loader_accepts_one_ulp_mask_and_contact_areas_with_updated_pins(self):
        original_sha=sha(ORIGINAL)
        with tempfile.TemporaryDirectory()as temporary:
            fixture=make_fixture(temporary,(3000,3030));case=fixture['case']
            mask=Path(case['mask_file']);set_csv_areas(mask,ONE_ULP_BELOW)
            old_mask_sha=case['mask_sha256'];new_mask_sha=sha(mask)
            config=Path(case['config_file'])
            config.write_text(config.read_text().replace('mask.sha256='+old_mask_sha,'mask.sha256='+new_mask_sha))
            case['mask_sha256']=new_mask_sha;case['config_sha256']=sha(config)
            metadata=fixture['metadata'];metadata['config_sha256']=case['config_sha256']
            (fixture['folder']/'mesh-metadata.json').write_text(json.dumps(metadata,allow_nan=False)+'\n')
            for f in (3000,3030):set_csv_areas(fixture['folder']/f'contacts-{f}.csv',ONE_ULP_BELOW)
            basis=r.load_basis(fixture['folder'],case,time.monotonic()+120.)
            self.assertEqual({3000,3030},set(basis['f']))
            self.assertTrue(np.all(basis['f'][3000]['contacts']['area_m2']==ONE_ULP_BELOW))
        self.assertEqual(original_sha,sha(ORIGINAL))

    def test_lower_bundle_requires_actual_recovery_identity_without_reclassifying_donor(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture=make_fixture(temporary,(1000,1030,2000,2030));folder=fixture['folder']
            with self.assertRaises(ValueError):r.load_basis(folder,fixture['case'],time.monotonic()+120.)
            metadata=fixture['metadata']
            metadata.update(exporter_class='CloudFrequencyRecoveryBasis',exporter_kind='frequency_recovery_native')
            (folder/'mesh-metadata.json').write_text(json.dumps(metadata,allow_nan=False)+'\n')
            wrapper=json.loads((folder/'runtime-wrapper.json').read_text())
            wrapper['runtime_wrapper_class']='CloudFrequencyRecoveryBasis'
            (folder/'runtime-wrapper.json').write_text(json.dumps(wrapper,allow_nan=False)+'\n')
            basis=r.load_basis(folder,fixture['case'],time.monotonic()+120.)
            geometry,_=r.geometry(basis,fixture['case'])
            self.assertEqual('CloudFrequencyRecoveryBasis',basis['metadata']['exporter_class'])
            self.assertEqual('CloudFrequencyRecoveryBasis',geometry['reconstruction_adapter']['actual_exporter_class'])
            self.assertEqual({1000,1030,2000,2030},set(geometry['gamma_S_m']))


if __name__=='__main__':
    unittest.main()
