"""Read the immutable cached GUI export; add a display-only manual-range policy."""
from pathlib import Path
import hashlib,json
PRIOR=Path('/dev/shm/task1-fixed-scales-20261025-r2')
PUBLIC='docs/TASK1_FIXED_SCALES_20261025';COMMIT='b7460d42d63381a53c36daf7d2826286ddb9131b'
def require(ok,msg):
    if not ok:raise ValueError(msg)
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as s:
        for block in iter(lambda:s.read(1024**2),b''):h.update(block)
    return h.hexdigest()
def required_inputs():
    p=PRIOR/'result-publication.json';raw=p.read_bytes();require(len(raw)<256*1024,'Bounded source publication manifest');pub=json.loads(raw)
    require(pub['commit']==COMMIT and pub['status']=='published_readback_verified','Exact fully readback-verified source GUI')
    refs={str(p):hashlib.sha256(raw).hexdigest()}
    for name in('index.html','field-shape.json','validation.json','fixed-scale-contract.json'):
        p=PRIOR/'results'/name;proof=pub['files'][PUBLIC+'/'+name]
        require(proof['readback_passed']and p.is_file()and not p.is_symlink()and p.stat().st_size==proof['bytes']<8*1024**2 and digest(p)==proof['SHA256'],'Source immutable byte/size proof')
        refs[str(p)]=proof['SHA256']
    return refs
def build(guard,pins):
    guard();refs=required_inputs();require(all(pins.get(p)==h for p,h in refs.items()),'Preregister exact cached inputs')
    P=json.loads((PRIOR/'results/field-shape.json').read_text())
    P['manual_range_proof']=dict(schema='task1-manual-display-policy-v1',new_PDE=0,new_native_field_decode=0,prior_source_GUI_commit=COMMIT,
        scientific_data_unchanged=True,Float64_ROI_statistics_unchanged=True,default_range_contract_preserved_as_reset_reference=True,
        manually_editable=True,automatic_fitting_after_user_edit=False,controls='Per-chart axes/colour min-max, group apply, reset and settingsJSON export/import',
        clipping='Out-of-display counts/marks only; underlying values and raw hover retained',
        waveform_time='Reconstruct the actual existing complex two-tone projection at the requested start/end times; display sampling remains bounded')
    for p,h in refs.items():guard();require(digest(p)==h,'Immutable source changed during display preparation')
    return P
