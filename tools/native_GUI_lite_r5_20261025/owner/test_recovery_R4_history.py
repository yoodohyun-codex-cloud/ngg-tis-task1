"""Pure numeric metadata fixture; no old RUN or source file read."""
import unittest
from recovery_R4_history import validate_record,OLD_RUN,S_COMMIT,S_SHA

class ActualR4NumericFailureContracts(unittest.TestCase):
 def test_recorded_numeric_block_cannot_be_relabelled_as_test_or_native_success(self):
  n=dict(admitted=False,physical_forecast_bytes=8004039390,forecast_excess_bytes=4039390,physical_cap_bytes=8000000000,all_owned_tmpfs_bytes=7656256734,all_research_RSS_bytes=35782656,forecast_child_RSS_bytes=300000000,forecast_new_output_bytes=12000000)
  a=dict(schema='task1-native-GUI-lite-R4-source-published-numeric-budget-failure-v1',status='actual_R4_S_published_numeric_block_before_MFG_native_GUI',original_run=str(OLD_RUN),original_owner_status='failed_preserved',actual_failed_phase='numeric-admission',terminal_UTC='2026-10-25T17:25:26.113534+00:00',source_publication_available=True,source_commit=S_COMMIT,source_publication_SHA256=S_SHA,result_publication_available=False,actual_MFG_run=False,actual_native_byte_reads=False,actual_GUI_built=False,exact_original_numeric_admission=n,no_original_files_modified=True,no_large_source_or_spec_bytes_duplicated=True,original_registered_source_files=[{}for _ in range(58)])
  self.assertTrue(validate_record(a));a['actual_MFG_run']=True
  with self.assertRaises(ValueError):validate_record(a)
