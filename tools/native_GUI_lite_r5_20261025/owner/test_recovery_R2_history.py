"""Pure metadata contracts; no historical files are opened by these fixtures."""
import unittest
from recovery_R2_history import validate_record,direct_source_proof,OLD_RUN,S_COMMIT,S_SHA

def record():
 return dict(schema='task1-native-GUI-lite-R2-postS-preMFG-failure-archive-v1',status='actual_source_published_budget_block_before_MFG_native_GUI',original_run=str(OLD_RUN),original_owner_status='failed_preserved',actual_failed_phase='source-publication',terminal_UTC='2026-10-25T16:40:32.717762+00:00',source_publication_available=True,source_commit=S_COMMIT,source_publication_SHA256=S_SHA,result_publication_available=False,actual_MFG_run=False,actual_native_byte_reads=False,actual_GUI_built=False,old_numeric_admission_diagnostic_available=False,old_blocked_forecast_exact_values_known=False,no_original_files_modified=True,historical_peak_resources_are_not_coincident_forecast_values=True,actual_absent_outputs=['numeric-admission.json','synthetic-test-receipt.json','worker-receipt.json','summary.json','index.html','result-publication/result-publication.json'],original_registered_source_files=[{}for _ in range(32)],original_metadata_files=[{}for _ in range(8)])

class ActualR2HistoryContracts(unittest.TestCase):
 def test_actual_S_with_no_R_MFG_or_GUI_remains_failure(self):
  a=record();self.assertTrue(validate_record(a));a['actual_GUI_built']=True
  with self.assertRaises(ValueError):validate_record(a)
 def test_old_missing_numeric_diagnostic_cannot_be_reconstructed_as_recorded(self):
  a=record();a['old_blocked_forecast_exact_values_known']=True
  with self.assertRaises(ValueError):validate_record(a)
 def test_direct_S_proof_requires_exact_target_full_SHA_bytes_and_readback(self):
  row=dict(published_target='tools/model/source.py',SHA256='a'*64,bytes=123)
  proof=dict(status='published_readback_verified',commit=S_COMMIT,remote_branch_head_verified=S_COMMIT,files={'tools/model/source.py':dict(SHA256='a'*64,bytes=123,readback_passed=True)})
  self.assertTrue(direct_source_proof(proof,row));row['published_target']='other/source.py'
  with self.assertRaises(ValueError):direct_source_proof(proof,row)
