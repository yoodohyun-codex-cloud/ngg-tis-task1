"""Six pure fake-time lease/cache fixtures, with no PID or filesystem access."""
import unittest
from lease_checkpoint import lease_checkpoint
class LeaseCheckpointContracts(unittest.TestCase):
 def test_slow_audit_completion_starts_reuse_window(self):
  state={};clock=[0.];calls=[]
  def full():calls.append(1);clock[0]+=1.
  lease_checkpoint(state,lambda:clock[0],lambda:None,full);clock[0]=1.1
  lease_checkpoint(state,lambda:clock[0],lambda:None,full)
  self.assertEqual(len(calls),1);self.assertEqual(state['last_completed_monotonic'],1.);self.assertEqual(state['cache_hits'],1)
 def test_exact250ms_expiry_performs_a_new_full_audit(self):
  state={};clock=[0.];calls=[];full=lambda:calls.append(1)
  lease_checkpoint(state,lambda:clock[0],lambda:None,full);clock[0]=.25;lease_checkpoint(state,lambda:clock[0],lambda:None,full)
  self.assertEqual(len(calls),2)
 def test_forced_boundary_ignores_fresh_cache(self):
  state={};calls=[];full=lambda:calls.append(1)
  lease_checkpoint(state,lambda:0.,lambda:None,full);lease_checkpoint(state,lambda:0.,lambda:None,full,True)
  self.assertEqual(len(calls),2);self.assertTrue(state['last_request_forced'])
 def test_failed_full_audit_does_not_advance_completion_or_allow_fallback(self):
  state={};clock=[0.];lease_checkpoint(state,lambda:clock[0],lambda:None,lambda:None);clock[0]=.1
  def fail():raise ValueError('Synthetic full lease failure')
  with self.assertRaises(ValueError):lease_checkpoint(state,lambda:clock[0],lambda:None,fail,True)
  self.assertEqual(state['last_completed_monotonic'],0.)
  with self.assertRaises(ValueError):lease_checkpoint(state,lambda:clock[0],lambda:None,lambda:None)
 def test_live_parent_quick_check_runs_and_can_fail_inside_reuse_window(self):
  state={};calls=[];alive=[True]
  def quick():
   calls.append(1)
   if not alive[0]:raise ValueError('Synthetic dead/wrong parent')
  lease_checkpoint(state,lambda:0.,quick,lambda:None);alive[0]=False
  with self.assertRaises(ValueError):lease_checkpoint(state,lambda:.1,quick,lambda:None)
  self.assertEqual(len(calls),3);self.assertTrue(state['poisoned'])
 def test_backward_clock_or_deadline_during_full_audit_poison_cache(self):
  state={};lease_checkpoint(state,lambda:1.,lambda:None,lambda:None)
  with self.assertRaises(ValueError):lease_checkpoint(state,lambda:.9,lambda:None,lambda:None)
  state={};expired=[False]
  def quick():
   if expired[0]:raise TimeoutError('Synthetic expired hard deadline')
  def full():expired[0]=True
  with self.assertRaises(TimeoutError):lease_checkpoint(state,lambda:0.,quick,full)
  self.assertNotIn('last_completed_monotonic',state);self.assertTrue(state['poisoned'])
if __name__=='__main__':unittest.main()
