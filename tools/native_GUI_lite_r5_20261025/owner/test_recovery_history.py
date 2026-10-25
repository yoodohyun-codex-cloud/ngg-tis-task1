"""Tiny pure history-status fixtures, no original files or helpers invoked."""
import unittest
from recovery_history import validate_archive_record,OLD_RUN

def record():return dict(schema='task1-native-GUI-lite-R1-preS-failure-archive-v1',status='actual_failed_before_source_publication_preserved',original_run=str(OLD_RUN),original_owner_status='failed_preserved',actual_phase='preparing',terminal_UTC='2026-10-25T15:39:32.995873+00:00',source_publication_available=False,result_publication_available=False,actual_MFG_run=False,actual_native_byte_reads=False,actual_GUI_built=False,no_original_files_modified=True,original_metadata_files=[{}],original_registered_source_files=[dict(UTF8='pass\n',bytes=5,SHA256='9f56e761d79bfdb34304a012586cb04d16b435ef6130091a97702e559260a2f2')],actual_absent_outputs=['source-publication/result-publication.json','result-publication/result-publication.json','synthetic-test-receipt.json','worker-receipt.json','index.html'])
class PreSFailureHistoryContracts(unittest.TestCase):
 def test_unpublished_attempt_cannot_become_source_or_result_pass(self):
  for key in('source_publication_available','result_publication_available','actual_MFG_run','actual_native_byte_reads','actual_GUI_built'):
   value=record();value[key]=True
   with self.assertRaises(ValueError):validate_archive_record(value)
 def test_old_failed_state_and_no_GUI_not_completion(self):
  value=record();value['original_owner_status']='completed'
  with self.assertRaises(ValueError):validate_archive_record(value)
 def test_corrupt_archived_source_or_missing_absence_rejected(self):
  value=record();value['original_registered_source_files'][0]['SHA256']='0'*64
  with self.assertRaises(ValueError):validate_archive_record(value)
  value=record();value['actual_absent_outputs']=[]
  with self.assertRaises(ValueError):validate_archive_record(value)
