"""No data or numerics: a valid published test boundary precedes real RHS."""
import unittest
import fine_screen as s
class FineTestBoundary(unittest.TestCase):
 def test_actual_published_model_tests_are_required_not_optional_ack(self):
  refs={'/canonical/source/test_mms.py':'a'*64};r=dict(status='passed',model_source_sha256=refs,model_source_test_count=5,tests_run=7,expected_total_tests=7)
  self.assertTrue(s.validate_test_receipt(r,refs,5)['passed'])
  for key,value in(('status','not_run'),('model_source_test_count',4),('tests_run',True),('expected_total_tests',8),('model_source_sha256',{})):
   bad=dict(r);bad[key]=value
   with self.assertRaises(ValueError):s.validate_test_receipt(bad,refs,5)
if __name__=='__main__':unittest.main()
