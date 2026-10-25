"""Pure queue identity contracts; no live processes, locks, credentials or Git."""
import copy,unittest
from git_publish_verified import validate_queue_identity,executed_script_argument
CONTROLLER='/dev/shm/task1-u19-supervisor/source/controller.py'
PUBLISHER='/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py'
def registration():
 return dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=42,proc_start_ticks=99,
  controller_path=CONTROLLER,controller_sha256='a'*64,publisher_path=PUBLISHER,publisher_sha256='b'*64)
class QueueIdentityContracts(unittest.TestCase):
 def test_exact_registered_identity(self):
  self.assertTrue(validate_queue_identity(registration(),42,99,CONTROLLER,'a'*64,PUBLISHER,'b'*64))
 def test_publisher_source_mismatch_rejected(self):
  reg=registration();reg['publisher_sha256']='c'*64
  with self.assertRaises(ValueError):validate_queue_identity(reg,42,99,CONTROLLER,'a'*64,PUBLISHER,'b'*64)
 def test_PID_reuse_startticks_rejected(self):
  with self.assertRaises(ValueError):validate_queue_identity(registration(),42,100,CONTROLLER,'a'*64,PUBLISHER,'b'*64)
 def test_later_forged_controller_argument_is_not_executed_script(self):
  actual=executed_script_argument(['python','-B','/dev/shm/task1-other/source/other.py','--forged',CONTROLLER])
  with self.assertRaises(ValueError):validate_queue_identity(registration(),42,99,actual,'a'*64,PUBLISHER,'b'*64)
 def test_python_c_cannot_impersonate_source_path(self):
  with self.assertRaises(ValueError):executed_script_argument(['python','-c','pass',CONTROLLER])
if __name__=='__main__':unittest.main()
