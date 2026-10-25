"""Pure, source-verified per-frequency human-reference/surrogate input builder.

No material default or I/O on import. Root must supply a verified material receipt
before preparation. Source verification does not imply four-layer physiological
validation; explicitly labelled surrogate assignments remain surrogate models.
"""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-human-sc4-20261025/source')
RUN=Path('/workspace/task1-human-sc4-20261025-run')
CASE='baseline-square15-human-reference-sc4-xy80'
SCHEMA='task1-human-sc4-native-v1'
COMPARATOR=Path('/dev/shm/task1-human-tissue-20261025-run')
COMPARATOR_CASE='baseline-square15-human-reference-xy80'
TEMPLATE=COMPARATOR/'configs'/(COMPARATOR_CASE+'.properties')
MASK=COMPARATOR/'masks'/(COMPARATOR_CASE+'.csv')
TEMPLATE_SHA256='8820712d379574c307328096a2b6817da8b59aca9d5be97aa5306668f48633a0'
MASK_SHA256='7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2'
MATERIAL_INPUT=SOURCE/'material-input.json'
MATERIAL_INPUT_SHA256='d1cae451cfce3cbed3aa51d0a84621690af46aec29f0db08949fcca337e80ced'
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
    """Only SC cell count and two explicit storage path mappings change."""
    run=Path(run)
    require(run==RUN and run.is_absolute()and run.parent==Path('/workspace'),'Exact canonical new disk-backed humanSC4 run')
    require(digest(template_raw)==TEMPLATE_SHA256 and digest(mask_raw)==MASK_SHA256 and digest(material_raw)==MATERIAL_INPUT_SHA256,
        'Actual humanSC2 config/mask/material bytes must remain identical')
    old=properties(template_raw);material,rows=verified_materials(material_raw)
    require(old['frequencies']=='3000,3030,9000,9090'and old['channels']=='2'and old['h_mm']=='0.625'and
        old['validation.sc_cells']=='2'and old['bulk.counts']=='14,14,40'and old['mask.sha256']==MASK_SHA256 and
        old['material.lookup']=='source_verified_per_frequency'and old['material.input_sha256']==MATERIAL_INPUT_SHA256,
        'Actual completed humanSC2 per-frequency circuit/grid/receipt required')
    require(all(old[layer+'.sigma.'+str(f)]and old[layer+'.epsilon_r.'+str(f)]for layer in LAYERS for f in FREQUENCIES),
        'All unchanged per-frequency human material keys required')
    mapped={'validation.sc_cells':'4','mask.path':str(run/'masks'/(CASE+'.csv')),'material.input_path':str(run/'material-input.json')}
    lines=[];seen=set()
    for line in template_raw.decode().splitlines():
        key=line.split('=',1)[0].strip()if '='in line else None
        if key in mapped:
            require(key not in seen,'One assignment for each remapped key');seen.add(key);line=key+'='+mapped[key]
        lines.append(line)
    require(seen==set(mapped),'All three mapped keys required')
    config=('\n'.join(lines)+'\n').encode();new=properties(config)
    changed={k:dict(old=old[k],proposed=new[k])for k in old if old[k]!=new[k]}
    require(old.keys()==new.keys()and set(changed)==set(mapped),'Only SCcells2to4 plus mask/material path mappings')
    table=[]
    for f in FREQUENCIES:
        for layer in LAYERS:
            row=rows[layer,f];sigma=float(old[layer+'.sigma.'+str(f)]);epsilon=float(old[layer+'.epsilon_r.'+str(f)])
            require(sigma==float(row['sigma_S_m'])and epsilon==float(row['epsilon_r']),'No material model reevaluation or adjustment')
            table.append(dict(row,gamma_real_S_m=sigma,gamma_imag_S_m=2*math.pi*f*EPS0*epsilon,
                epsilon0_F_m=EPS0,gamma_unit='S/m',SC2_sigma_S_m=sigma,SC2_epsilon_r=epsilon,material_value_changed=False))
    return dict(case_id=CASE,config_bytes=config,mask_bytes=bytes(mask_raw),material_bytes=bytes(material_raw),
        config_file=str(run/'configs'/(CASE+'.properties')),mask_file=str(run/'masks'/(CASE+'.csv')),
        config_sha256=digest(config),mask_sha256=digest(mask_raw),material_input_sha256=digest(material_raw),
        config_diff=changed,material_table=dict(schema='task1-human-SC4-unchanged-material-lookup-v1',case_id=CASE,rows=table,
            source_material_receipt_sha256=digest(material_raw),SC_cells_before=2,SC_cells_after=4,
            comparator_run_id=COMPARATOR.name,comparator_case_id=COMPARATOR_CASE,material_calibrated=False,
            scope='One same-material humanSC2-to-SC4 grid check; material functions are not reevaluated or changed'))
