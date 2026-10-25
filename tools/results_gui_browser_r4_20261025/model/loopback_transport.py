"""Finite worker-owned, read-only loopback transport. Import starts nothing.

Only the three authenticated GUI artifacts can be streamed. This does not
alter files, start another process, expose a public port or bypass a browser
policy. A real browser must still exercise and pass all existing checks.
"""
import contextlib, hashlib, json, math, os, re, stat, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

CHUNK_BYTES=64*1024
MAX_FILE=80*1024**2
NAMES=('index.html','summary.json','views.json')

def require(ok,message):
 if not ok:raise RuntimeError(message)

def new_json(path,value):
 raw=(json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
 with Path(path).open('xb')as stream:stream.write(raw)

def identity(path):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink(),'Canonical regular admitted HTTP input')
 s=p.stat();return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

def validate_inputs(inputs):
 require(set(inputs)==set(NAMES),'Exactly three authenticated GUI files, no arbitrary HTTP roots')
 routes={}
 for name in NAMES:
  row=inputs[name];p=Path(row['path']);token=identity(p)
  require(p.name==name and type(row.get('bytes'))is int and 0<row['bytes']<MAX_FILE and token[2]==row['bytes']and re.fullmatch('[0-9a-f]{64}',row.get('SHA256',''))is not None,'Exact bounded file identity for loopback streaming')
  routes['/'+name]=dict(path=p,SHA256=row['SHA256'],bytes=row['bytes'],identity=token,content_type='text/html; charset=utf-8'if name.endswith('.html')else'application/json; charset=utf-8')
 return routes

@contextlib.contextmanager
def serve(inputs,guard,deadline_monotonic,output_dir):
 """One bounded server thread in the authenticated worker; no new worker/PDE."""
 require(callable(guard)and math.isfinite(deadline_monotonic),'Finite authenticated worker guard/deadline')
 out=Path(output_dir);require(out.is_dir()and out==out.resolve()and not out.is_symlink(),'Existing canonical exclusive output')
 guard();routes=validate_inputs(inputs);mutex=threading.RLock();events=[];errors=[];counts={p:0 for p in routes};began=time.monotonic();thread_errors=[]
 def event(row):
  with mutex:
   if len(events)<128:events.append(row)
 def failure(message):
  with mutex:
   if len(errors)<32:errors.append(message)
 class Handler(BaseHTTPRequestHandler):
  protocol_version='HTTP/1.0'
  def log_message(self,*args):pass
  def do_GET(self):self.reply(False)
  def do_HEAD(self):self.reply(True)
  def do_POST(self):self.send_error(405,'Read-only admitted transport');self.close_connection=True
  def reply(self,head):
   # Raw exact path matching rejects traversal, queries, absolute URLs and
   # directory requests. It never decodes/normalizes an untrusted URL to disk.
   path=self.path
   if path=='/favicon.ico':
    self.send_response(204);self.send_header('Content-Length','0');self.send_header('Connection','close');self.end_headers();self.close_connection=True;return
   if path not in routes:
    event(dict(path='not_admitted',method='HEAD'if head else'GET',status=404));self.send_error(404,'Path not admitted');self.close_connection=True;return
   row=routes[path];total=0;hasher=hashlib.sha256()
   try:
    guard();require(time.monotonic()<deadline_monotonic,'Finite loopback response deadline');require(identity(row['path'])==row['identity'],'Admitted HTTP input changed before open')
    descriptor=os.open(row['path'],os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(descriptor,'rb')as stream:
     opened=os.fstat(stream.fileno());require(stat.S_ISREG(opened.st_mode)and(opened.st_dev,opened.st_ino,opened.st_size,opened.st_mtime_ns,opened.st_ctime_ns)==row['identity'],'Opened regular file must be the exact authenticated input')
     self.send_response(200);self.send_header('Content-Type',row['content_type']);self.send_header('Content-Length',str(row['bytes']));self.send_header('Cache-Control','no-store');self.send_header('Connection','close');self.end_headers()
     if not head:
      blocks=0
      while True:
       require(time.monotonic()<deadline_monotonic,'Finite loopback streaming deadline')
       block=stream.read(CHUNK_BYTES)
       if not block:break
       self.wfile.write(block);hasher.update(block);total+=len(block);blocks+=1
       if blocks%16==0:guard()
      require(total==row['bytes']and hasher.hexdigest()==row['SHA256'],'Exact streamed GUI bytes/SHA, without base64 copies')
    require(identity(row['path'])==row['identity'],'Admitted HTTP input changed during streaming');guard()
    with mutex:
     if not head:counts[path]+=1
    event(dict(path=path,method='HEAD'if head else'GET',status=200,bytes=total,SHA256=None if head else hasher.hexdigest(),streamed_SHA_passed=None if head else True))
   except BaseException as error:
    # No request headers, arbitrary URLs, argv, environment or secrets stored.
    failure(dict(path=path,error_type=type(error).__name__));self.close_connection=True
   finally:self.close_connection=True
 class BoundedHTTPServer(HTTPServer):
  allow_reuse_address=False
  def get_request(self):
   connection,address=super().get_request();connection.settimeout(2.)
   if address[0]!='127.0.0.1':connection.close();raise RuntimeError('Loopback client address required')
   return connection,address
 server=BoundedHTTPServer(('127.0.0.1',0),Handler)
 require(server.server_address[0]=='127.0.0.1'and 0<server.server_address[1]<65536,'IPv4 loopback-only ephemeral port')
 server.timeout=.1
 origin='http://127.0.0.1:'+str(server.server_address[1]);started=threading.Event();stop_event=threading.Event()
 def server_main():
  started.set()
  try:
   while not stop_event.is_set()and time.monotonic()<deadline_monotonic:server.handle_request()
  except BaseException as error:
   if not stop_event.is_set():thread_errors.append(type(error).__name__)
 thread=threading.Thread(target=server_main,name='task1-loopback-gui',daemon=True);primary_error=None
 try:
  thread.start();require(started.wait(timeout=2.)and thread.is_alive(),'Owned loopback server thread started')
  transport=dict(origin=origin,allowed_urls=[origin+p for p in routes]+[origin+'/favicon.ico'],bind_address='127.0.0.1',port=server.server_address[1],chunk_bytes=CHUNK_BYTES,read_only=True,extra_processes=0)
  new_json(out/'loopback-transport-started.json',dict(schema='task1-read-only-loopback-transport-v1',**transport,worker_pid=os.getpid(),actual_browser_policy_access_verified=False))
  yield transport
 except BaseException as error:primary_error=error;raise
 finally:
  stopped=time.monotonic()
  # No unbounded server.shutdown() wait: signal the bounded handle_request
  # loop, close its listener, and join at most3s. Handler socket I/O is2s.
  # The independent parent watchdog remains active if a thread cannot stop.
  stop_event.set();server.server_close()
  if thread.ident is not None:thread.join(timeout=3.)
  alive=thread.is_alive()
  receipt=dict(schema='task1-read-only-loopback-transport-receipt-v1',origin=origin,bind_address='127.0.0.1',worker_pid=os.getpid(),server_thread_stopped=not alive,shutdown_seconds=time.monotonic()-stopped,elapsed_seconds=time.monotonic()-began,stream_chunk_bytes=CHUNK_BYTES,request_events=events,events_truncated=len(events)>=128,completed_verified_GET_counts=counts,errors=errors,thread_errors=thread_errors,all_three_admitted_files_streamed=all(n>0 for n in counts.values()),no_directory_listing=True,no_path_translation=True,no_original_file_write=True,extra_processes=0,browser_policy_access_not_inferred=True,new_PDE_RHS=0)
  new_json(out/'loopback-transport-receipt.json',receipt)
  if primary_error is None:
   require(not alive and not errors and not thread_errors and all(n>0 for n in counts.values()),'Finite loopback lifecycle and all three exact-file streams must complete')
