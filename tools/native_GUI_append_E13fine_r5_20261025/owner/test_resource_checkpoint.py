"""Injected fake-clock/accounting fixtures; no scans/processes/files/threads."""
import unittest
from resource_checkpoint import resource_checkpoint
class Clock:
 def __init__(self):self.value=0.
 def __call__(self):return self.value
class ResourceCheckpointContracts(unittest.TestCase):
 def test_safe_completion_time_not_scan_start_starts_the_250ms_reuse_window(self):
  c=Clock();s={};calls=[]
  def scan():calls.append(1);c.value+=1.;return dict(research_RSS_bytes=2),dict(total_bytes=3)
  self.assertTrue(resource_checkpoint(s,c,0.,10.,scan,10));self.assertEqual(s['last_completed_monotonic'],1.)
  c.value=1.1;self.assertFalse(resource_checkpoint(s,c,0.,10.,scan,10));self.assertEqual(len(calls),1)
 def test_expired_safe_age_rechecks_both_actual_components(self):
  c=Clock();s={};calls=[]
  def scan():calls.append(1);return dict(research_RSS_bytes=len(calls)),dict(total_bytes=3)
  resource_checkpoint(s,c,0.,10.,scan,10);c.value=.25
  self.assertTrue(resource_checkpoint(s,c,0.,10.,scan,10));self.assertEqual(s['observed_aggregate_bytes'],5)
 def test_forced_stage_boundary_never_reuses_even_fresh_safe_cache(self):
  c=Clock();s={};calls=[]
  def scan():calls.append(1);return dict(research_RSS_bytes=2),dict(total_bytes=3)
  resource_checkpoint(s,c,0.,10.,scan,10);c.value=.01;self.assertTrue(resource_checkpoint(s,c,0.,10.,scan,10,True));self.assertEqual(len(calls),2)
 def test_cap_failure_never_advances_safe_time_and_poison_prevents_fallback(self):
  c=Clock();s={}
  def safe():return dict(research_RSS_bytes=2),dict(total_bytes=3)
  resource_checkpoint(s,c,0.,10.,safe,10);c.value=.1
  with self.assertRaises(ValueError):resource_checkpoint(s,c,0.,10.,lambda:(dict(research_RSS_bytes=9),dict(total_bytes=3)),10,True)
  self.assertEqual(s['last_completed_monotonic'],0.)
  with self.assertRaises(ValueError):resource_checkpoint(s,c,0.,10.,safe,10)
 def test_deadline_before_or_during_scan_blocks_without_success_timestamp(self):
  c=Clock();c.value=2.;s={}
  with self.assertRaises(ValueError):resource_checkpoint(s,c,0.,1.,lambda:(_ for _ in()).throw(AssertionError('No scan')),10)
  c.value=0.;s={}
  def slow():c.value=2.;return dict(research_RSS_bytes=2),dict(total_bytes=3)
  with self.assertRaises(ValueError):resource_checkpoint(s,c,0.,1.,slow,10)
  self.assertNotIn('last_completed_monotonic',s)
 def test_failed_or_backwards_scan_never_creates_safe_cached_observation(self):
  c=Clock();s={}
  def failed():raise OSError('Synthetic unavailable actual accounting')
  with self.assertRaises(OSError):resource_checkpoint(s,c,0.,10.,failed,10)
  self.assertNotIn('last_completed_monotonic',s)
  c.value=1.;s={}
  def backwards():c.value=.5;return dict(research_RSS_bytes=2),dict(total_bytes=3)
  with self.assertRaises(ValueError):resource_checkpoint(s,c,0.,10.,backwards,10)
  self.assertNotIn('last_completed_monotonic',s)
if __name__=='__main__':unittest.main()
