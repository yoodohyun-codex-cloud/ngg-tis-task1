"""Pure, source-verified per-frequency human-reference/surrogate input builder.

No material default or I/O on import. Root must supply a verified material receipt
before preparation. Source verification does not imply four-layer physiological
validation; explicitly labelled surrogate assignments remain surrogate models.
"""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-human-tissue-20261025/source')
RUN=Path('/dev/shm/task1-human-tissue-20261025-run')
CASE='baseline-square15-human-reference-xy80'
SCHEMA='task1-human-tissue-native-v1'
TEMPLATE=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/configs/baseline-square15-xy80.properties'
MASK=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/masks/baseline-square15-h0.625.csv'
TEMPLATE_SHA256='f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b'
MASK_SHA256='7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2'
MATERIAL_INPUT=SOURCE/'material-input.json'
COMPARATOR=Path('/dev/shm/task1-all-layer-sensitivity-20261025-run')
COMPARATOR_CASE='baseline-square15-sc-eps1100-xy80'
FREQUENCIES=(3000,3030,9000,9090)
LAYERS=('sc','dermis','fat','muscle')
EPS0=8.8541878128e-12
ASSIGNMENTS={'primary_measurement','published_model','declared_surrogate'}

def require(ok,message):
    if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def properties(raw):
    require(isinstance(raw,bytes)and len(raw)<128*1024,'Bounded explicit configuration bytes')
    out={}
    for line in raw.decode().splitlines():
        if not line.strip()or line.lstrip().startswith('#'):continue
        require('='in line,'Assignment required');key,value=line.split('=',1);key=key.strip();value=value.strip()
        require(key and key not in out,'Duplicate property');out[key]=value
    return out

def verified_materials(raw):
    require(isinstance(raw,bytes)and len(raw)<1024**2,'Bounded mandatory material receipt')
    obj=json.loads(raw)
    require(obj.get('schema')=='task1-human-tissue-materials-v1'and obj.get('status')=='source_verified_for_declared_scope',
        'Source-verified receipt required; no invented or default human parameters')
    require(isinstance(obj.get('rows'),list)and len(obj['rows'])==16,'Exactly16 source-verified layer/carrier rows')
    rows={}
    for row in obj['rows']:
        key=(row.get('layer'),row.get('frequency_Hz'))
        require(key[0]in LAYERS and key[1]in FREQUENCIES and key not in rows,'Exact unique layer/carrier pairs')
        require(row.get('source_verified')is True and row.get('assignment_type')in ASSIGNMENTS,
            'Explicit source verification and measured/model/surrogate assignment required')
        require(isinstance(row.get('source_id'),str)and row['source_id'].strip()and
            isinstance(row.get('source_location'),str)and row['source_location'].strip(),'Traceable primary source/model identifier and location required')
        require(row.get('sigma_unit')=='S/m'and row.get('epsilon_r_unit')=='dimensionless','Explicit source-converted SI/relative units required')
        sigma=row.get('sigma_S_m');epsilon=row.get('epsilon_r')
        require(type(sigma)in(int,float)and type(epsilon)in(int,float)and math.isfinite(sigma)and sigma>0 and math.isfinite(epsilon)and epsilon>0,
            'Finite positive source-verified material numbers required')
        if row['assignment_type']=='declared_surrogate':
            require(isinstance(row.get('limitation'),str)and row['limitation'].strip(),'Surrogate assignment requires its explicit layer mismatch/limitation')
        rows[key]=dict(row)
    require(set(rows)=={(layer,f)for layer in LAYERS for f in FREQUENCIES},'All four layers and frequencies required')
    return obj,rows

def derive_config(template_raw,mask_raw,material_raw,run=RUN):
    run=Path(run)
    require(run==RUN and run.is_absolute()and run.parent==Path('/dev/shm'),'Exact unique human-reference run')
    require(digest(template_raw)==TEMPLATE_SHA256 and digest(mask_raw)==MASK_SHA256,'Frozen canonical geometry/circuit/mask required')
    old=properties(template_raw);material,rows=verified_materials(material_raw)
    require(old['frequencies']=='3000,3030,9000,9090'and old['channels']=='2'and old['h_mm']=='0.625'and
        old['validation.sc_cells']=='2'and old['bulk.counts']=='14,14,40'and old['mask.sha256']==MASK_SHA256,'Canonical SC2 circuit/grid required')
    legacy={layer+'.'+kind for layer in LAYERS for kind in('sigma','epsilon_r')}
    require(legacy.issubset(old),'Exact old material block must be audited')
    lines=[]
    for line in template_raw.decode().splitlines():
        key=line.split('=',1)[0].strip()if '='in line else None
        if key in legacy:continue
        if key=='mask.path':line='mask.path='+str(run/'masks'/(CASE+'.csv'))
        lines.append(line)
    lines+=['# Source-verified per-frequency human reference/surrogate lookup; no legacy material fallback.',
        'material.lookup=source_verified_per_frequency','material.input_path='+str(run/'material-input.json'),
        'material.input_sha256='+digest(material_raw)]
    table=[]
    for f in FREQUENCIES:
        for layer in LAYERS:
            row=rows[layer,f];sigma=float(row['sigma_S_m']);epsilon=float(row['epsilon_r'])
            lines.extend((layer+'.sigma.'+str(f)+'='+format(sigma,'.17g'),layer+'.epsilon_r.'+str(f)+'='+format(epsilon,'.17g')))
            table.append(dict(row,gamma_real_S_m=sigma,gamma_imag_S_m=2*math.pi*f*EPS0*epsilon,
                epsilon0_F_m=EPS0,gamma_unit='S/m',old_sigma_S_m=float(old[layer+'.sigma']),old_epsilon_r=float(old[layer+'.epsilon_r'])))
    config=('\n'.join(lines)+'\n').encode();new=properties(config)
    added=set(new)-set(old);removed=set(old)-set(new);changed={k:dict(old=old[k],proposed=new[k])for k in old.keys()&new.keys()if old[k]!=new[k]}
    allowed_added={layer+'.'+kind+'.'+str(f)for layer in LAYERS for kind in('sigma','epsilon_r')for f in FREQUENCIES}|{'material.lookup','material.input_path','material.input_sha256'}
    require(removed==legacy and added==allowed_added and set(changed)=={'mask.path'},'Only explicit material lookup block and mask-path mapping may change')
    return dict(case_id=CASE,config_bytes=config,mask_bytes=bytes(mask_raw),material_bytes=bytes(material_raw),
        config_file=str(run/'configs'/(CASE+'.properties')),mask_file=str(run/'masks'/(CASE+'.csv')),
        config_sha256=digest(config),mask_sha256=digest(mask_raw),material_input_sha256=digest(material_raw),
        config_diff=dict(changed=changed,removed_legacy_material_keys={k:old[k]for k in sorted(removed)},added={k:new[k]for k in sorted(added)}),
        material_table=dict(schema='task1-human-source-material-lookup-v1',case_id=CASE,rows=table,
            source_material_receipt_sha256=digest(material_raw),material_calibrated=False,
            scope='Source-verified human-reference/model/surrogate values; not measurements of this phantom or physiological activation validation'))
