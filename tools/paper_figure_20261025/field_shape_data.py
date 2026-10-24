"""Reuse verified display exports for a paper-inspired figure, no native solve/read."""
from __future__ import annotations
import copy,hashlib,json
from pathlib import Path

SOURCE=Path(__file__).resolve().parent
PRIOR=Path('/dev/shm/task1-field-shape-export-20261025')
RESULT_COMMIT='df92c38fdff02a11fe5df635ff9de0b15777ec21'
PUBLIC='docs/TASK1_FIELD_SHAPE_20261025'
NAMES=('field-shape.json','index.html','validation.json')

def require(ok,message):
    if not ok:raise ValueError(message)
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()
def required_inputs():
    """Only a small readback manifest is decoded; native bases stay untouched."""
    path=PRIOR/'result-publication.json';raw=path.read_bytes();require(len(raw)<256*1024,'Small publication manifest')
    manifest=json.loads(raw);require(manifest['status']=='published_readback_verified'and manifest['commit']==RESULT_COMMIT,'Exact completed field export required')
    pins={str(path):hashlib.sha256(raw).hexdigest()}
    for name in NAMES:
        proof=manifest['files'][PUBLIC+'/'+name];require(proof['readback_passed']and 0<=proof['bytes']<8*1024**2,'Immutable export evidence')
        p=PRIOR/'results'/name;require(p.is_file()and not p.is_symlink()and p.stat().st_size==proof['bytes'],'Exact verified file size/path')
        # Hash only, no vector decode or numerical processing during preparation.
        require(digest(p)==proof['SHA256'],'Published export bytes changed')
        pins[str(p)]=proof['SHA256']
    return pins

def build(guard,pins):
    guard();declared=required_inputs();require(all(pins.get(p)==h for p,h in declared.items()),'Pre-register every cached export input')
    payload=json.loads((PRIOR/'results/field-shape.json').read_text())
    require(payload['schema']=='task1-native-field-shape-display-v1'and payload['new_PDE']==0 and len(payload['planes'])==7,
        'Actual previously verified native display export required')
    require(payload['proofs']['TIS_full_volume_RMS_reconstruction']['passed']and payload['proofs']['C1_ROI_energy_RMS_reconstruction']['passed'],
        'Original Float64 reconstruction evidence must remain available')
    analysis=copy.deepcopy(payload['analysis'])
    import paper_metrics
    proof=paper_metrics.mathematical_validation()
    require(proof['status']=='passed','Complex two-tone signal/envelope analytic tests failed')
    payload['paper_reference']=dict(title='Noninvasive Deep Brain Stimulation via Temporally Interfering Electric Fields',authors='Grossman et al.',year=2017,
        DOI='10.1016/j.cell.2017.05.024',url='https://doi.org/10.1016/j.cell.2017.05.024',author_lab_reference='https://www.tmslab.org/publications/629.pdf',
        figure_references=['Figure1A-C','Figure2','FigureS2/S3'],publication_read_access='Cell direct403; primary author-lab PDF read; no article/figure redistribution',
        application='Independent figures from this project data: separate carriers, analytic envelope, directional modulation maps and linecuts',
        differences='Article salineD50x10mm/isolated sources differs from fixed layeredD50x25.1mm/top electrodes/commonGND/50ohm; no activation or experimental equivalence')
    payload['paper_proofs']=dict(mathematical_validation=proof,cached_source_result_commit=RESULT_COMMIT,new_PDE=0,display_vectors_reused_unchanged=True,
        Float64_statistics_unchanged=True,native_field_redecode_in_this_stage=False,cached_export_files_SHA256_verified=True,
        display_precision='Existing Float32 native-cell complex display samples and their conversion bounds; existing source Float64 ROI statistics retained separately',
        directional_two_tone_formula='For fixed real unit n: a=n dot E3000, b=n dot E3030 after coherent output sum. A(t)=abs(a exp(jw1t)+b exp(jw2t)); modulation depth=max(A)-min(A)=2min(abs(a),abs(b))',
        maximum_direction_scope='Saved2074-direction maxTIS statistics are separate; no new continuous maximum or direction search',
        maps_are_measurements=False,paper_data_reused=False)
    require(payload['analysis']==analysis,'No change to existing native Float64 metrics')
    for p,h in declared.items():guard();require(digest(p)==h,'Cached export changed during paper figure preparation')
    return payload
