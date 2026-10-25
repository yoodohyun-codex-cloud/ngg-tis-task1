"""Deferred, fail-closed U19 inputs. Import performs no I/O or computation.

The owner must supply a completed MMS, immutable public evidence and an explicit
positive root decision. No manufactured result automatically admits a native run.
"""
from pathlib import Path
import hashlib,json,math,re

ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-vs19-uniform-2000-20261025/source')
RUN=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run')
CASE='baseline-square15-human-sine2000-sc8-vs19uniform-bulk19-18-56-xy100'
SCHEMA='task1-vs19-uniform-2000-native-v1'
COMPARATOR=Path('/dev/shm/task1-sc8-2000-20261025-run')
COMPARATOR_CASE='baseline-square15-human-sine2000-sc8-bulk18-18-56-xy100'
TEMPLATE=COMPARATOR/'configs'/(COMPARATOR_CASE+'.properties')
MASK=COMPARATOR/'masks'/(COMPARATOR_CASE+'.csv')
TEMPLATE_SHA256='b7d043a5f8287e6916367e0f4d53576ca738e48de725ed7f2bbd4c805c2dee18'
MASK_SHA256='884d3bc2537bc88d87a82bffcd735a197c48afda02485573ec27b80469b688ca'
MATERIAL_INPUT=COMPARATOR/'material-input.json'
CONTACT_INPUT=COMPARATOR/'contact-receipt.json'
MATERIAL_SHA256='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
CONTACT_SHA256='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
MMS_RUN=Path('/dev/shm/task1-vs-estimator-20261025-run')
FREQUENCIES=(2000,)
LAYERS=('sc','dermis','fat','muscle')
COUNTS=(8,19,18,56)

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def properties(raw):
 out={}
 for line in raw.decode().splitlines():
  if not line.strip()or line.lstrip().startswith(('#','!')):continue
  require('='in line,'Assignment required');key,value=line.split('=',1);key=key.strip()
  require(key not in out,'Duplicate property');out[key]=value.strip()
 return out
def verified_materials(raw):
 require(digest(raw)==MATERIAL_SHA256,'Exact completed material receipt bytes')
 obj=json.loads(raw);rows={}
 for row in obj['rows']:
  require(row['source_verified']is True and row['assignment_type']=='declared_surrogate','Preserve source and surrogate uncertainty')
  rows[row['layer'],row['frequency_Hz']]=row
 require(len(rows)==8 and all((name,2000)in rows for name in LAYERS),'Actual eight receipt rows, including2000Hz')
 return obj,rows

def validate_faces(faces):
 require(isinstance(faces,list)and len(faces)==102 and all(type(v)in(int,float)and math.isfinite(v)for v in faces),'102 finite U19 faces in metres')
 boundaries=(0.,.0001,.0051,.0101,.0251);at=0
 for layer,count in enumerate(COUNTS):
  require(abs(faces[at]-boundaries[layer])<=1e-14,'Fixed layer boundary')
  width=(boundaries[layer+1]-boundaries[layer])/count
  for _ in range(count):
   require(faces[at+1]>faces[at]and abs(faces[at+1]-faces[at]-width)<=1e-14,'Strictly positive uniform U19 layer widths');at+=1
 require(abs(faces[-1]-.0251)<=1e-14,'Fixed25.1mm depth')
 return list(faces)

def verified_admission(spec_raw,summary_raw,decision_raw,root_decision_public_commit):
 """Pure verification; public readback authenticity remains the owner's job."""
 require(re.fullmatch('[0-9a-f]{40}',root_decision_public_commit or'')is not None,'Actual immutable root-decision public commit required')
 spec=json.loads(spec_raw);summary=json.loads(summary_raw);decision=json.loads(decision_raw)
 require(spec['schema']=='task1-fixed-SC8-VS-estimator-spec-v1'and spec['modes']==[1,2,4,8,16]and spec['case_count']==15,'Actual frozen15-case MMS specification')
 require(summary['schema']=='task1-SC8-VS-estimator-manufactured-result-v1'and summary['status']=='calculated_manufactured_only_unadopted'and summary['spec']==spec and summary['analytic_contracts']['passed']is True and summary['new_real_native_PDE']==0,'Actual completed MMS with analytic contracts; no native result implied')
 reviews=[row for row in summary['predeclared_native_review']if row['candidate']=='U19']
 require(len(reviews)==1 and reviews[0]['true_continuum_error_nonregression']is True and reviews[0]['physical_error_improvement_review']is True and reviews[0]['automatic_native_admission']is False,'Actual U19 predeclared nonregression and physical-error review must pass')
 require(decision['schema']=='task1-u19-native-root-admission-v1'and decision['status']=='admitted_native_diagnostic'and decision['candidate']=='U19'and decision['root_review_positive']is True and decision['automatic_native_admission']is False and decision['candidate_adopted']is False,'Explicit root U19 admission; no implicit candidate adoption')
 require(decision['new_native_conditions']==1 and decision['maximum_native_RHS']==2 and decision['mms_spec_sha256']==digest(spec_raw)and decision['mms_summary_sha256']==digest(summary_raw),'Root decision binds exact actual MMS and one-condition/two-RHS scope')
 require(all(re.fullmatch('[0-9a-f]{40}',decision[key])is not None for key in('mms_result_commit','sc8_result_commit'))and isinstance(decision['decision_basis'],str)and bool(decision['decision_basis'].strip()),'Actual published MMS/SC8 commit references and root rationale')
 g=spec['geometry']['U19'];faces=validate_faces(g['faces_m'])
 require(g['vertical_cells']==101 and g['XY_columns']==7860 and g['real_equivalent_native_cells']==793860,'Frozen U19 counts within800000')
 require(g['face_table_sha256']==digest(json.dumps(faces,separators=(',',':'),allow_nan=False).encode()),'Exact MMS compact-array face hash')
 expected=dict(id='U19',h_mm=.5,sc_cells=8,bulk_counts=[19,18,56],VS_grading='uniform')
 require([row for row in spec['grids']if row['id']=='U19']==[expected],'Exact selected uniform U19 tuple')
 return spec,summary,decision,faces

def derive_config(template_raw,mask_raw,material_raw,*,contact_raw,spec_raw,summary_raw,decision_raw,root_decision_public_commit,run=RUN):
 """Return new bytes/metadata; performs no file write and no native solve."""
 require(Path(run)==RUN and digest(template_raw)==TEMPLATE_SHA256 and digest(mask_raw)==MASK_SHA256,'Exact completed SC8 comparator config and physical mask')
 material,rows=verified_materials(material_raw);require(digest(contact_raw)==CONTACT_SHA256,'Exact completed contact receipt')
 spec,summary,decision,faces=verified_admission(spec_raw,summary_raw,decision_raw,root_decision_public_commit)
 contact=json.loads(contact_raw);z=next(row for row in contact['rows']if row['frequency_Hz']==2000)
 old=properties(template_raw);require(old['h_mm']=='0.5'and old['frequencies']=='2000'and old['validation.sc_cells']=='8'and old['bulk.counts']=='18,18,56'and old['channels']=='2','Only uniform VS18to19 at fixedSC8/XY0.5/twooutputs')
 face_obj=dict(schema='task1-u19-explicit-z-faces-v1',units='m',grid_id='U19',layer_counts=list(COUNTS),z_faces_m=faces,face_table_sha256=spec['geometry']['U19']['face_table_sha256'],mms_spec_sha256=digest(spec_raw))
 face_raw=(json.dumps(face_obj,allow_nan=False,separators=(',',':'))+'\n').encode();new=dict(old)
 new.update({'bulk.counts':'19,18,56','validation.expected_cells':'793860','mask.path':str(RUN/'masks'/(CASE+'.csv')),'material.input_path':str(RUN/'material-input.json'),'contact.input_path':str(RUN/'contact-receipt.json'),
  'mesh.z_faces_path':str(RUN/'z-faces.json'),'mesh.z_faces_sha256':digest(face_raw),'mesh.face_table_sha256':face_obj['face_table_sha256'],'mesh.mms_spec_sha256':digest(spec_raw)})
 for name in LAYERS:
  require(float(new[name+'.sigma.2000'])==rows[name,2000]['sigma_S_m']and float(new[name+'.epsilon_r.2000'])==rows[name,2000]['epsilon_r'],'No material reevaluation')
 require(new['material.input_sha256']==MATERIAL_SHA256 and new['contact.input_sha256']==CONTACT_SHA256 and float(new['z.2000.re'])==z['area_real_ohm_m2']and float(new['z.2000.im'])==z['area_imag_ohm_m2'],'No contact reevaluation or duplicate subtraction')
 changed={key:dict(old=old[key],proposed=new[key])for key in old if old[key]!=new[key]};added={key:value for key,value in new.items()if key not in old}
 require(set(changed)=={'bulk.counts','validation.expected_cells','mask.path','material.input_path','contact.input_path'}and set(added)=={'mesh.z_faces_path','mesh.z_faces_sha256','mesh.face_table_sha256','mesh.mms_spec_sha256'},'Only registered VS count/face/storage mappings change')
 raw=('\n'.join(key+'='+value for key,value in new.items())+'\n').encode()
 return dict(config_bytes=raw,mask_bytes=bytes(mask_raw),material_bytes=bytes(material_raw),contact_bytes=bytes(contact_raw),z_faces_bytes=face_raw,mms_spec_bytes=bytes(spec_raw),mms_summary_bytes=bytes(summary_raw),root_decision_bytes=bytes(decision_raw),
  config_file=str(RUN/'configs'/(CASE+'.properties')),mask_file=str(RUN/'masks'/(CASE+'.csv')),config_sha256=digest(raw),mask_sha256=MASK_SHA256,material_input_sha256=MATERIAL_SHA256,contact_receipt_sha256=CONTACT_SHA256,
  z_faces_file=str(RUN/'z-faces.json'),z_faces_sha256=digest(face_raw),mms_spec_sha256=digest(spec_raw),mms_summary_sha256=digest(summary_raw),root_decision_sha256=digest(decision_raw),root_decision_public_commit=root_decision_public_commit,
  native_cells=793860,native_XY_columns=7860,material_table=material,config_diff=dict(changed=changed,added=added,scope='One2000Hz uniformVS18to19 diagnostic, fixedSC8/XY0.5/material/contact/pads/circuit; no TIS or physical validation'),
  selected_MMS_review=next(row for row in summary['predeclared_native_review']if row['candidate']=='U19'),root_decision=decision)
