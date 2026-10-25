"""Research ownership classification; import is inert, no process scan until root.

All research-root families and remembered live identities count once. Merely
sharing a UID with the framework is not ownership. Diagnostics omit raw argv.
This module never sends signals; only the guardian's own children may be killed.
"""
import hashlib,json,os,re
from pathlib import Path
ROOT=Path('/workspace/ngg-tis-task1')
PATH_PATTERN=re.compile(r'/dev/shm/task1-[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*|/workspace/ngg-tis-task1(?:/[A-Za-z0-9_.-]+)*')
PAIRS=(('supervisor_pid','proc_start_ticks'),('queue_pid','queue_start_ticks'),('pid','proc_start_ticks'),('controller_pid','controller_start_ticks'),('child_pid','child_start_ticks'),('browser_pid','browser_start_ticks'),('server_pid','server_start_ticks'))

def classify(records,authenticated,registered=(),remembered=None):
 bypid={r['pid']:r for r in records};reasons={};remembered=remembered or{}
 def add(pid,reason):reasons.setdefault(pid,[]).append(reason)
 for pid,row in bypid.items():
  tick=row['start_ticks']
  if authenticated.get(pid)==tick:add(pid,'current_authenticated_guardian_family')
  if remembered.get(pid)==tick:add(pid,'previously_proven_live_research_identity')
  paths=PATH_PATTERN.findall(row.get('cwd','')+' '+' '.join(row.get('argv',[])))
  if paths:add(pid,'actual_argv_or_cwd_research_path:'+sorted(set(paths))[0])
 for item in registered:
  pid=item['pid']
  if pid in bypid and bypid[pid]['start_ticks']==item['start_ticks']:add(pid,'live_identity_in_research_registry:'+item['registry'])
 changed=True
 while changed:
  changed=False
  for pid,row in bypid.items():
   parent=row.get('ppid')
   if pid not in reasons and parent in reasons and bypid[parent]['start_ticks']<=row['start_ticks']:add(pid,'live_descendant_of_research_root:'+str(parent));changed=True
 members={pid:bypid[pid]['start_ticks']for pid in reasons};audit=[]
 for pid,row in sorted(bypid.items()):
  audit.append(dict(pid=pid,start_ticks=row['start_ticks'],ppid=row.get('ppid'),uid=row.get('uid'),RSS_bytes=row['rss_bytes'],research_owned=pid in members,reasons=reasons.get(pid,['excluded_no_proven_research_root_registry_or_family']),argv_SHA256=hashlib.sha256('\0'.join(row.get('argv',[])).encode()).hexdigest()))
 return members,audit,sum(bypid[pid]['rss_bytes']for pid in members)

def collect_processes(ticks):
 records=[];errors=[]
 for directory in Path('/proc').glob('[0-9]*'):
  if not directory.name.isdigit():continue
  pid=int(directory.name)
  try:
   before=ticks(pid)
   if before is None:continue
   status=directory.joinpath('status').read_text();values={line.split(':',1)[0]:line.split(':',1)[1].strip()for line in status.splitlines()if':'in line}
   argv=[v.decode(errors='replace')for v in directory.joinpath('cmdline').read_bytes().split(b'\0')if v]
   try:cwd=str(directory.joinpath('cwd').resolve(strict=True))
   except OSError:cwd=''
   after=ticks(pid)
   if before!=after:continue
   records.append(dict(pid=pid,start_ticks=before,ppid=int(values.get('PPid','0')),uid=int(values.get('Uid','-1').split()[0]),rss_bytes=int(values.get('VmRSS','0 kB').split()[0])*1024,argv=argv,cwd=cwd))
  except(FileNotFoundError,ProcessLookupError):continue
  except OSError as error:errors.append(dict(pid=pid,error_type=type(error).__name__))
 return records,errors

def registry_identities():
 paths=list(Path('/dev/shm').glob('task1-*/registration.json'))+list((ROOT/'runtime').glob('*registration*.json'))+list((ROOT/'runtime').glob('*research*process*.json'));result=[]
 def walk(value,registry):
  if isinstance(value,dict):
   for p,t in PAIRS:
    if type(value.get(p))is int and type(value.get(t))is int:result.append(dict(pid=value[p],start_ticks=value[t],registry=registry))
   for nested in value.values():walk(nested,registry)
  elif isinstance(value,list):
   for nested in value:walk(nested,registry)
 for path in paths:
  try:
   if path.is_file()and not path.is_symlink()and path.stat().st_size<=2*1024**2:walk(json.loads(path.read_text()),str(path))
  except(FileNotFoundError,OSError,json.JSONDecodeError):continue
 return result

def safe_ticks(ticks,pid):
 try:return ticks(pid)
 except OSError:return None

def observe(authenticated,ticks,remembered=None):
 records,errors=collect_processes(ticks);registered=registry_identities();members,audit,rss=classify(records,authenticated,registered,remembered)
 known=list(authenticated.items())+list((remembered or{}).items())+[(row['pid'],row['start_ticks'])for row in registered]
 if any(safe_ticks(ticks,pid)==start and pid not in members for pid,start in known):raise ValueError('Live known research identity unreadable or omitted from RSS scope')
 uid=os.getuid();all_uid_rss=sum(r['rss_bytes']for r in records if r['uid']==uid)
 return dict(members=members,research_RSS_bytes=rss,scanned_processes=audit,unreadable_processes=errors,diagnostic_same_UID_RSS_bytes=all_uid_rss,scope='ALL proven research argv/cwd/registered-root process families plus live remembered identities and authenticated guardian family; unrelated same-UID framework excluded; all scanned PID/startticks reasons recorded; this observer never kills other families')
