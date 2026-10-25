"""Additional storage admission checks; frozen scientific suite remains unchanged."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_rounded_contact_sensitivity as tool


class ContactStorageAdmissionTests(unittest.TestCase):
    tool=tool

    def test_registered_two_case_storage_bound_admits_expected_outputs_and_preserves_original_reserve(self):
        gib=1024**3;bound=128*1024**2;free=int(2.22*gib)
        self.assertEqual(self.tool.OUTPUT_BOUND_BYTES,bound)
        self.assertLess(free,2*gib+256*1024**2)
        self.assertTrue(self.tool.validate_storage(free,initial=True))
        self.assertTrue(self.tool.validate_storage(free-17100000,added_bytes=17100000))
        self.assertTrue(self.tool.validate_storage(2*gib+bound,initial=True))
        self.assertTrue(self.tool.validate_storage(2*gib,added_bytes=bound))
        for free_bytes,added,initial in((2*gib+bound-1,0,True),(2*gib-1,0,False),(2*gib,bound+1,False)):
            with self.subTest(free=free_bytes,added=added,initial=initial),self.assertRaises(ValueError):
                self.tool.validate_storage(free_bytes,added_bytes=added,initial=initial)


if __name__=='__main__':unittest.main()
