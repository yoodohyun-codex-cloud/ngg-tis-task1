"""Tiny synthetic status contracts; root may run, author has not executed."""
import unittest
from closure_contracts import validate_r5,validate_fine

class TerminalClosureContracts(unittest.TestCase):
 def test_r5_failure_never_becomes_browser_pass(self):
  owner=dict(schema='task1-results-gui-browser-owner-v1',status='failed_preserved',new_PDE_RHS=0,candidate_adopted=False,failed_phase='actual-browser-child',error_type='InterruptedError',error='Actual ALL research-familyRSS plus ALL task1-ownedtmpfs cap',resources=dict(peak_accounted=8_000_000_001))
  result=validate_r5(owner)
  self.assertFalse(result['browser_PASS'])
  owner['status']='consolidated_gui_actual_browser_passed'
  with self.assertRaises(ValueError):validate_r5(owner)
 def test_failed_fine_does_not_invent_actual_work_counts(self):
  owner=dict(schema='task1-P23-fineXY-owner-v1',status='failed_preserved',candidate_adopted=False,maximum_new_driven_RHS=3,automatic_fourth_fallback=False)
  pub=dict(status='published_readback_verified',commit='a'*40)
  result=validate_fine(owner,pub,pub,'failed')
  self.assertIsNone(result['recorded_accounting'])
  self.assertTrue(result['actual_completed_RHS_not_inferred'])
  with self.assertRaises(ValueError):validate_fine(owner,pub,pub,'completed')
 def test_completed_label_requires_actual_stage_and_accounting(self):
  owner=dict(schema='task1-P23-fineXY-owner-v1',status='P23_fineXY_three_RHS_computed_published',candidate_adopted=False,maximum_new_driven_RHS=3,automatic_fourth_fallback=False)
  pub=dict(status='published_readback_verified',commit='a'*40)
  with self.assertRaises(ValueError):validate_fine(owner,pub,pub,'completed')
