"""Deployment identity regression: no actual metadata, arrays or PDE are read."""
import unittest
from unittest.mock import patch
from pathlib import Path
import mixed_catalog as m

class DeploymentIdentityContracts(unittest.TestCase):
 def test_source_and_frozen_snapshot_generate_identical_input_pin_identity(self):
  canonical=m.SOURCE/'mixed_catalog.py';frozen=Path('/dev/shm/task1-owner-test-run/source/model/mixed_catalog.py');context={'input_pins':{'/published/original-metadata.json':'a'*64}}
  with patch.object(m,'_context',return_value=context),patch.object(m,'digest',return_value='b'*64):
   with patch.object(m,'__file__',str(canonical)):original=m.required_inputs(None,{'root_selected':True})
   with patch.object(m,'__file__',str(frozen)):deployed=m.required_inputs(None,{'root_selected':True})
  self.assertEqual(original,deployed)
  self.assertIn(str(canonical),deployed)
  self.assertNotIn(str(frozen),deployed)
  self.assertEqual(deployed['/published/original-metadata.json'],'a'*64)

if __name__=='__main__':unittest.main()
