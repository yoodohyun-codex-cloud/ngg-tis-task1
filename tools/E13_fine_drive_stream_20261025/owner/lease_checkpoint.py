"""Completion-based child lease audit gate; injected clock/callbacks only."""
import math

def lease_checkpoint(state,clock,quick,full,force=False):
 """Quick checks ALWAYS run. Only a successful completed full audit is reused."""
 state.setdefault('poisoned',False)
 try:
  quick();now=clock()
  if not math.isfinite(now)or now<state.get('last_requested_monotonic',now):raise ValueError('Child lease clock moved backwards or is nonfinite')
  state['last_requested_monotonic']=now
  if state.get('poisoned',False):raise ValueError('Earlier child lease audit failed; no cached fallback')
  completed=state.get('last_completed_monotonic');age=None if completed is None else now-completed
  if age is not None and age<0:raise ValueError('Child lease completion timestamp is in future')
  state['max_observed_age_seconds']=max(state.get('max_observed_age_seconds',0.),age or 0.)
  if not force and age is not None and age<.25:
   state['cache_hits']=state.get('cache_hits',0)+1;state['last_request_forced']=False;return
  started=clock()
  if started<now:raise ValueError('Child lease audit start clock moved backwards')
  full();quick();finished=clock()
  if not math.isfinite(finished)or finished<started:raise ValueError('Child lease audit completion clock moved backwards')
  state.update(last_completed_monotonic=finished,last_audit_started_monotonic=started,last_audit_finished_monotonic=finished,last_audit_duration_seconds=finished-started,last_request_forced=bool(force),full_audits=state.get('full_audits',0)+1)
  state['max_audit_duration_seconds']=max(state.get('max_audit_duration_seconds',0.),finished-started)
 except BaseException:
  state['poisoned']=True;state['failed_requests']=state.get('failed_requests',0)+1;raise
