"""Completion-based resource checkpoint, derived from reviewed Root7 design.

Inert, no resource scans/imports on load. Caller MUST serialize with its own
accounting mutex. A completed safe pass starts the maximum250ms reuse interval;
forced stage boundaries always rescan. Failures poison reuse and never advance
last_completed_monotonic. Existing process ownership observer stays byte-exact.
"""
ROOT7_SOURCE='/dev/shm/task1-verified-transport-retirement-20261025-seventh.py'
ROOT7_SOURCE_SHA256='9267e662044297da1b92e4201339a930209f07a34270995b4f4724af9bc4dae5'
MAX_SAFE_REUSE_SECONDS=.25

def require(ok,message):
 if not ok:raise ValueError(message)
def resource_checkpoint(state,clock,started,cap_seconds,observe,total_memory_bytes,force=False):
 begin=clock();require(begin-started<cap_seconds,'Finite owner deadline before resource accounting')
 require(not state.get('poisoned_error'),'Previous failed resource scan forbids safe-cache reuse')
 previous=state.get('last_completed_monotonic');age=None if previous is None else begin-previous
 require(age is None or age>=0,'Monotonic accounting age')
 state.update(last_requested_monotonic=begin,accounting_age_at_request_seconds=age,last_request_forced=bool(force))
 if not force and age is not None and age<MAX_SAFE_REUSE_SECONDS:
  state['cache_hits']=state.get('cache_hits',0)+1;return False
 try:
  observation,auxiliary=observe();finished=clock()
  require(finished>=begin,'Monotonic full resource accounting duration')
  aggregate=observation['research_RSS_bytes']+auxiliary['total_bytes']
  require(finished-started<cap_seconds,'Finite owner deadline after full resource accounting')
  require(aggregate<=total_memory_bytes,'Actual ALL research RSS plus BOTH task1 auxiliary roots8e9')
 except BaseException as error:
  state.update(poisoned_error=dict(error_type=type(error).__name__,error=str(error)),failed_scan_count=state.get('failed_scan_count',0)+1)
  raise
 state.update(processes=observation,auxiliary=auxiliary,observed_aggregate_bytes=aggregate,accounting_started_monotonic=begin,accounting_finished_monotonic=finished,accounting_duration_seconds=finished-begin,last_completed_monotonic=finished,safe_scan_count=state.get('safe_scan_count',0)+1)
 return True
