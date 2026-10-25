"""Pure JSON/HTML renderer recovery API. Import performs no input reads/render."""
import gc,hashlib,importlib,json,math,re,time
from pathlib import Path
import native_gui_inputs as inputs
SOURCE=inputs.SOURCE
OPEN=b'<script id="payload" type="application/json">'
CLOSE=b'</script>'

def require(ok,message):inputs.require(ok,message)
def encoded(value):return(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,indent=2)+'\n').encode('utf-8')
def new_json(path,value):
 raw=encoded(value)
 with Path(path).open('xb')as stream:stream.write(raw)
def check(guard,deadline):
 guard()
 if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite renderer-only recovery deadline')
def semantic_equal(a,b):
 """Exact parsed JSON equality; key order ignored, arrays ordered, bool distinct."""
 if a is None or b is None:return a is b
 if type(a)is bool or type(b)is bool:return type(a)is type(b)and a==b
 if type(a)in(int,float)and type(b)in(int,float):return math.isfinite(a)and math.isfinite(b)and a==b
 if type(a)is not type(b):return False
 if type(a)is str:return a==b
 if type(a)is list:return len(a)==len(b)and all(semantic_equal(x,y)for x,y in zip(a,b))
 if type(a)is dict:return a.keys()==b.keys()and all(semantic_equal(a[k],b[k])for k in a)
 return False
def payload_bytes(raw):
 require(raw.count(OPEN)==1,'One exact native payload script marker')
 start=raw.index(OPEN)+len(OPEN);end=raw.index(CLOSE,start);return raw[start:end]
def binding_only_HTML(raw):
 text=raw.decode('utf-8');start=text.index('<script>')+len('<script>');end=text.index('</script>',start);app=text[start:end]
 require(len(re.findall(r'\btop\b',app))==6,'Original six binding/use tokens in application script only')
 return(text[:start]+re.sub(r'\btop\b','appTopIds',app)+text[end:]).encode('utf-8')
def make_spec(admission=None):return inputs.make_spec(admission)
def required_inputs(admission=None):return inputs.required_inputs(admission)
def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(callable(guard)and spec==make_spec(spec['root_admission']),'Exact authenticated renderer-only spec')
 out=Path(output_dir);require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink()and out.parent==Path('/dev/shm')and not(out/'index.html').exists(),'New exclusive root render output')
 check(guard,deadline_monotonic);started=time.monotonic();old_path=Path(spec['inputs']['index.html']['path']);old_raw=old_path.read_bytes();require(hashlib.sha256(old_raw).hexdigest()==spec['inputs']['index.html']['SHA256'],'Original index exact SHA before extraction');original_payload=payload_bytes(old_raw)
 payload=json.loads(original_payload);require(type(payload)is dict and set(payload)=={'summary','views'},'Original admitted JSON payload structure')
 supplied={}
 for name in('summary.json','views.json'):
  check(guard,deadline_monotonic);row=spec['inputs'][name];require(inputs.sha(row['path'])==row['SHA256'],'Supplied original JSON exact SHA');supplied[name]=json.loads(Path(row['path']).read_bytes())
 require(semantic_equal(payload['summary'],supplied['summary.json'])and semantic_equal(payload['views'],supplied['views.json']),'Original embedded JSON exactly matches supplied S/V semantics')
 new_json(out/'checkpoint-01-original-payload.json',dict(status='original_payload_authenticated',original_payload_SHA256=hashlib.sha256(original_payload).hexdigest(),original_payload_bytes=len(original_payload),supplied_JSON_semantic_equal=True,new_PDE_RHS=0));del supplied;gc.collect();check(guard,deadline_monotonic)
 renderer=importlib.import_module('consolidated_gui');require(Path(renderer.__file__).resolve()==Path(spec['new_renderer']['path']).resolve()or inputs.sha(renderer.__file__)==spec['new_renderer']['SHA256'],'Loaded renderer exact reviewed source');require(inputs.sha(renderer.__file__)==spec['new_renderer']['SHA256'],'Loaded renderer full source SHA')
 html=renderer.build(payload['summary'],payload['views']);require(type(html)is str,'Renderer returns standalone HTML only');new_raw=html.encode('utf-8');new_payload=payload_bytes(new_raw);expected=binding_only_HTML(old_raw)
 proof=dict(schema='task1-native-gui-exact-payload-identity-v1',old_index_SHA256=hashlib.sha256(old_raw).hexdigest(),new_index_SHA256=hashlib.sha256(new_raw).hexdigest(),original_payload_SHA256=hashlib.sha256(original_payload).hexdigest(),new_payload_SHA256=hashlib.sha256(new_payload).hexdigest(),old_payload_bytes=len(original_payload),new_payload_bytes=len(new_payload),EXACT_payload_bytes_equal=new_payload==original_payload,EXACT_binding_only_HTML_equal=new_raw==expected,supplied_summary_views_JSON_semantic_equal=True,renderer_SHA256=spec['new_renderer']['SHA256'],original_renderer_SHA256=spec['original_renderer']['SHA256'],only_JS_binding_renamed=new_raw==expected,new_PDE_RHS=0,new_angular_evaluations=0,native_arrays_loaded=False,browser_validation_performed=False)
 new_json(out/'payload-identity-proof.json',proof)
 if not(proof['EXACT_payload_bytes_equal']and proof['EXACT_binding_only_HTML_equal']):
  with(out/'failed-index.html').open('xb')as stream:stream.write(new_raw)
  raise ValueError('Renderer payload or non-binding HTML changed; failed new artifact preserved, originals untouched')
 require(0<len(new_raw)<80*1024**2,'New standalone index publication bound');check(guard,deadline_monotonic)
 with(out/'index.html').open('xb')as stream:stream.write(new_raw)
 saved=(out/'index.html').read_bytes();require(saved==new_raw and payload_bytes(saved)==original_payload,'Exact payload/HTML byte readback after exclusive write')
 proof.update(after_write_EXACT_payload_bytes_equal=True,after_write_index_SHA256=hashlib.sha256(saved).hexdigest());new_json(out/'payload-after-write-proof.json',proof)
 aliases={name:dict(spec['inputs'][name],alias_kind='read_only_original_file_at_new_publication_prefix',originals_overwritten=False)for name in('summary.json','views.json')};new_json(out/'original-summary-views-aliases.json',aliases)
 for row in spec['inputs'].values():check(guard,deadline_monotonic);require(inputs.sha(row['path'])==row['SHA256'],'Original GUI input unchanged after render')
 receipt=dict(schema='task1-native-gui-render-recovery-result-v1',status='minimal_JS_binding_rendered_payload_EXACT_browser_unverified',new_index_SHA256=hashlib.sha256(saved).hexdigest(),new_index_bytes=len(saved),renderer_SHA256=spec['new_renderer']['SHA256'],payload_identity_proof=proof,original_summary_views_aliases=aliases,original_result_commit=spec['original_result_commit'],original_R4_error=spec['original_R4_error'],browser_validation_performed=False,browser_next_action='Separate new R5 browser validation of NEW published nativeGUI-R2; do not rerun known-bad old index',new_PDE_RHS=0,new_angular_evaluations=0,native_arrays_loaded=False,Q_loaded=False,originals_overwritten=False,candidate_adopted=False,elapsed_seconds=time.monotonic()-started)
 new_json(out/'render-receipt.json',receipt);check(guard,deadline_monotonic);return dict(summary=receipt,arrays={})
