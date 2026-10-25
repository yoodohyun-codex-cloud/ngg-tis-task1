"""Guarded cached display loading; compute fixed scale bounds without a PDE."""
from pathlib import Path
import base64,gzip,hashlib,json,re
PRIOR=Path('/dev/shm/task1-paper-figure-20261025')
PUBLIC='docs/TASK1_PAPER_FIGURE_20261025';COMMIT='2b4abb6206fe1e3d0dc30c7d3bd7e1ba350da077'

def require(ok,msg):
    if not ok:raise ValueError(msg)
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as s:
        for block in iter(lambda:s.read(1024**2),b''):h.update(block)
    return h.hexdigest()
def required_inputs():
    p=PRIOR/'result-publication.json';raw=p.read_bytes();require(len(raw)<256*1024,'Bounded prior publication manifest');pub=json.loads(raw)
    require(pub['commit']==COMMIT and pub['status']=='published_readback_verified','Exact source GUI publication')
    refs={str(p):hashlib.sha256(raw).hexdigest()}
    for name in ('index.html','field-shape.json','validation.json'):
        item=pub['files'][PUBLIC+'/'+name];p=PRIOR/'results'/name
        require(item['readback_passed']and p.is_file()and not p.is_symlink()and p.stat().st_size==item['bytes']<8*1024**2 and digest(p)==item['SHA256'],'Verified source export bytes')
        refs[str(p)]=item['SHA256']
    return refs
def build(guard,pins):
    guard();declared=required_inputs();require(all(pins.get(p)==h for p,h in declared.items()),'Pre-register exact immutable display inputs')
    P=json.loads((PRIOR/'results/field-shape.json').read_text());source=(PRIOR/'results/index.html').read_text()
    match=re.search(r'<script id="packed" type="application/octet-stream">(.*?)</script>',source,re.S);require(match is not None,'Original packed scientific payload')
    packed=base64.b64decode(match.group(1),validate=True)
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(packed))as stream:raw=stream.read(16*1024**2+1)
    require(len(raw)<=16*1024**2,'Bounded original data unpack')
    base=json.loads(raw);require(P['analysis']==base['analysis'],'All GUI layers share actual existing analysis')
    from fixed_scale_contract import build_contract
    contract=build_contract(P,base,guard)
    P['fixed_scale_contract']=contract
    P['fixed_scale_proof']=dict(status='calculated_cached_display_bounds',new_PDE=0,new_native_field_decode=0,original_scientific_payload_SHA256=hashlib.sha256(raw).hexdigest(),
        source_GUI_commit=COMMIT,analysis_unchanged=True,Float64_ROI_statistics_unchanged=True,automatic_rescaling=False)
    for p,h in declared.items():guard();require(digest(p)==h,'Prior immutable display changed during bound construction')
    return P
