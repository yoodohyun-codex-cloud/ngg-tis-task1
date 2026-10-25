"""Synthetic registry/history fixtures; no actual source/data/old RUN read."""
import hashlib,io,unittest
from pathlib import Path
from unittest.mock import patch
import gui_inputs as inputs
from owner_contracts import source_paths
from recovery_R3_history import validate_record,OLD_RUN,S_COMMIT,S_SHA

class LogRegistryRecoveryContracts(unittest.TestCase):
 def test_actual_plaintext_log_suffix_is_selected_by_both_production_inventories(self):
  root=Path('/dev/shm/task1-synthetic-source');log=root/'previous-R2-07-2-source-publication.log';code=root/'source.py';native=root/'field.npz'
  with patch.object(Path,'iterdir',return_value=iter([log,code,native])),patch.object(Path,'is_file',return_value=True):
   self.assertEqual(source_paths(root),[log,code])
  with patch.object(Path,'iterdir',return_value=iter([log,code,native])),patch.object(Path,'is_file',return_value=True):
   self.assertEqual(inputs.source_paths(root),[log,code])
  raw=(b'actual publisher plaintext, not JSON\n'+b'x'*664)[:664]
  with patch.object(Path,'open',return_value=io.BytesIO(raw)),patch.object(inputs.json,'loads',side_effect=AssertionError('Plaintext log is never JSON parsed')):
   self.assertEqual(inputs.digest(log),hashlib.sha256(raw).hexdigest())
 def test_actual_preS_failure_cannot_be_relabelled_with_older_S_publication(self):
  a=dict(schema='task1-native-GUI-lite-R3-preS-registration-failure-archive-v1',status='actual_preS_failure_missing_log_registration_preserved',original_run=str(OLD_RUN),original_owner_status='failed_preserved',actual_failed_phase='preparing',terminal_UTC='2026-10-25T16:59:08.741778+00:00',source_publication_available=False,result_publication_available=False,actual_MFG_run=False,actual_native_byte_reads=False,actual_GUI_built=False,source_reuse_commit=S_COMMIT,source_reuse_publication_SHA256=S_SHA,missing_registered_log_bytes=664,actual_log_bytes_match_prior_R2_archive=True,original_registered_source_count=46,source_record_count=47,source_records=[{}for _ in range(47)],reused_actual_published_S_records=27,unpublished_UTF8_records=20,original_metadata_files=[{}for _ in range(8)],no_original_files_modified=True,no_original_spec_or_large_nested_archive_duplicated=True)
  self.assertTrue(validate_record(a));a['source_publication_available']=True
  with self.assertRaises(ValueError):validate_record(a)
