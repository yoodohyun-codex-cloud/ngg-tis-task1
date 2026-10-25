"""Authorization and historical-integrity contracts; never mutate the live ledger."""
import copy,json,math,unittest
from pathlib import Path
import task1_resource_policy as policy
ROOT=Path(__file__).resolve().parents[1]
class CumulativeTimeContracts(unittest.TestCase):
 def setUp(self):
  self.live=policy.load_ledger();self.old=json.loads((ROOT/'runtime/time-unlimited-20261025/runtime__task1-budget.json.before').read_text())
 def test_authorized_null_limit_and_finite_accounting(self):
  self.assertIsNone(policy.effective_limit(self.live));self.assertIsNone(policy.remaining_seconds(self.live));self.assertTrue(policy.time_available(self.live,175));self.assertTrue(policy.time_available(self.live,1000000));self.assertIn('"limit_seconds": null',json.dumps(self.live,allow_nan=False));self.assertEqual(self.live['runs'][:len(self.old['runs'])],self.old['runs'])
 def test_old_finite_admission_remains_exact(self):
  self.assertEqual(policy.effective_limit(self.old),13800);self.assertAlmostEqual(policy.remaining_seconds(self.old),52.02410019196941);self.assertFalse(policy.time_available(self.old,175))
 def test_cumulative_history_still_accepts_actual_new_spending(self):
  x=copy.deepcopy(self.live);x['spent_seconds']+=1;x['runs'].append(dict(stage='contract_example_only',seconds=1));self.assertIsNone(policy.effective_limit(x))
 def test_unauthorized_null_and_missing_pins_rejected(self):
  for key in ('cumulative_time_unlimited','cumulative_time_policy'):
   x=copy.deepcopy(self.live);x.pop(key)
   with self.assertRaises(ValueError):policy.effective_limit(x)
 def test_bad_approval_hash_rejected(self):
  x=copy.deepcopy(self.live);x['cumulative_time_policy']['approval_sha256']='0'*64
  with self.assertRaises(ValueError):policy.effective_limit(x)
 def test_history_or_spending_reset_rejected(self):
  for kind in ('prefix','spent','finite_policy'):
   x=copy.deepcopy(self.live)
   if kind=='prefix':x['runs'][0]['seconds']+=.001
   elif kind=='spent':x['spent_seconds']=self.old['spent_seconds']-1
   else:x['resource_policy']=None
   with self.assertRaises(ValueError):policy.effective_limit(x)
 def test_fake_numeric_unlimited_and_infinite_stage_rejected(self):
  x=copy.deepcopy(self.live);x['limit_seconds']=10**100
  with self.assertRaises(ValueError):policy.effective_limit(x)
  for duration in (math.inf,math.nan,-1):
   with self.assertRaises(ValueError):policy.time_available(self.live,duration)
if __name__=='__main__':unittest.main()
