"""Root-only donor authentication and exact physical-pad CSV composition.

No source import causes file reads, masks, NumPy, arrays, tests or calculations.
Existing B0/P23 geometry is immutable; only whole physicalpad groups are copied.
"""
from __future__ import annotations
import copy,csv,hashlib,io,json
from fractions import Fraction
from pathlib import Path
SOURCE=Path('/dev/shm/task1-mixed-fourpad-r2-20261025/source')
FIRST=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
FAILED=Path('/dev/shm/task1-peripheral-fourpad-20261025-run')
RECOVERY=Path('/dev/shm/task1-peripheral-recovery-20261025-run')
PARTIAL=Path('/dev/shm/task1-local-lease-and-cloud-failure-20261025-run/failure-publication/result-publication.json')
FIRST_S='c8e5f2f9d4fbba5646944772d526533ecedbbab1';FIRST_S_SHA='cb8939fdd21b3c4d7103eeb26c3591037402553d4369aa195888e30930b1eb49'
FIRST_R='4d6207caa60ae16ab7a7e997022ac72653b97ec3';FIRST_R_SHA='d20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159'
FAILED_S='3329379d39bd8632dc75308e32dc4e30fb9296e7';FAILED_S_SHA='d73f9f51cca8909849c66de98ee75bf4b4533ef07160cd098d16d7cb332f4753'
PARTIAL_R='2d8ad63f714e549c60e1db4d78792a193ed83c2c';PARTIAL_SHA='2cae4bdbc3580ec14653eb5b23e1b48ca15c2851323bf89386e2e02e52040a07'
B0='B0-square15-c10-diagonal';P23='P23p5-peripheral-polyomino225'
IDS=(B0,P23,'M_Speriph_Rsquare','M_Ssquare_Rperiph')
EXPECTED_DONORS=(('B0','B0','B0','B0'),('P23','P23','P23','P23'),('P23','P23','B0','B0'),('B0','B0','P23','P23'))
H=Fraction(1,2000);R=Fraction(1,40);MAX_META=8*1024**2;MAX_RAW=80*1024**2

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return(json.dumps(value,allow_nan=False,sort_keys=True,indent=2)+'\n').encode()
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for chunk in iter(lambda:stream.read(1024**2),b''):h.update(chunk)
 return h.hexdigest()
def read(path,expected=None):
 p=Path(path);require(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=MAX_META,'Bounded regular metadata/input')
 raw=p.read_bytes();require(expected is None or sha(raw)==expected,'Exact immutable input SHA');return raw
def js(path,expected=None):return json.loads(read(path,expected))
def publication(path,expected_sha,commit):
 p=js(path,expected_sha);require(p.get('status')=='published_readback_verified'and p.get('commit')==commit,'Actual fully-readback verified publication');return p

def file_proof(pub,path,root,expected=None):
 p=Path(path);require(p.is_relative_to(root),'Expected publication run path');relative=p.relative_to(root).as_posix();matches=[(t,r)for t,r in pub['files'].items()if t.endswith('/'+relative)]
 require(len(matches)==1,'Unique direct published file '+relative);target,row=matches[0]
 require(row.get('readback_passed')is True and isinstance(row.get('bytes'),int)and 0<row['bytes']<=MAX_RAW and isinstance(row.get('SHA256'),str)and len(row['SHA256'])==64,'Full bounded file readback proof')
 require(expected is None or row['SHA256']==expected,'Published file differs from declared identity')
 require(p.is_file()and not p.is_symlink()and p.stat().st_size==row['bytes'],'Actual published regular-file size')
 return dict(path=str(p),SHA256=row['SHA256'],bytes=row['bytes'],publication_commit=pub['commit'],target=target,readback_passed=True)

def validate_admission(a):
 require(isinstance(a,dict)and a.get('schema')=='task1-mixed-fourpad-root-admission-v1'and a.get('status')=='selected_finite_mixed_fourpad_screen'and a.get('root_selected')is True,'Separate root finite mixed-footprint selection after recovery result')
 require(a.get('recovery_run')==str(RECOVERY)and a.get('new_RHS')==4 and a.get('new_metric_evaluations')==2 and a.get('control_aliases')==2 and a.get('source_allocation_amplitudes')==[1.,1.]and a.get('candidate_adopted')is False,'Exactly four new RHS/two metrics/two immutable controls, original equal voltage')
 require(isinstance(a.get('decision_basis'),str)and a['decision_basis'].strip(),'Actual preceding result rationale required')
 for key,n in(('recovery_publication_sha256',64),('recovery_result_commit',40)):
  require(isinstance(a.get(key),str)and len(a[key])==n and all(c in'0123456789abcdef'for c in a[key]),'Explicit verified recovery identity')
 require(Path(a['recovery_publication_path']).is_absolute(),'Absolute actual recovery receipt');return a

def _context(admission=None):
 a=validate_admission(js(SOURCE/'root-admission.json')if admission is None else admission);refs={};proofs={}
 def pub(path,expected,commit):
  p=publication(path,expected,commit);refs[str(path)]=expected;return p
 fs=pub(FIRST/'source-publication/result-publication.json',FIRST_S_SHA,FIRST_S);fr=pub(FIRST/'result-publication/result-publication.json',FIRST_R_SHA,FIRST_R)
 ps=pub(FAILED/'source-publication/result-publication.json',FAILED_S_SHA,FAILED_S);pr=pub(PARTIAL,PARTIAL_SHA,PARTIAL_R);rr=pub(Path(a['recovery_publication_path']),a['recovery_publication_sha256'],a['recovery_result_commit'])
 def record(publication,path,root,expected=None,parse=False):
  d=file_proof(publication,path,root,expected);refs[d['path']]=d['SHA256'];proofs[d['path']]=d
  return js(path,d['SHA256'])if parse else d
 fc=record(fs,FIRST/'catalog-inputs.json',FIRST,parse=True);pc=record(ps,FAILED/'catalog-inputs.json',FAILED,parse=True)
 fsum=record(fr,FIRST/'summary.json',FIRST,parse=True);rsum=record(rr,RECOVERY/'summary.json',RECOVERY,parse=True)
 require(fsum['status']=='provisional_eight_layout_screen_computed_unadopted'and fsum['completed_candidates']==8,'Actual original first8 completed')
 require(rsum['status']=='peripheral_recovery_computed_without_P23_PDE_repeat'and rsum['completed_conditions']==4 and rsum['actual_new_driven_RHS']==2 and rsum['actual_reused_saved_RHS']==2 and rsum['actual_new_metric_evaluations']==2 and rsum['new_P23_RHS']==0,'Actual completed memory-separated P23 metric recovery')
 for key in('gamma_by_frequency','z_by_frequency','common_ROI','grid','drives','source_resistance_ohm'):
  require(fc[key]==pc[key]==rsum['spec']['recovery_inputs']['catalog'][key],'Same actual material/contact/ROI/grid/circuit donors: '+key)
 require(fsum['spec']['provisional_field']['derived_field_version']==rsum['spec']['recovery_inputs']['original_spec']['provisional_field']['derived_field_version'],'Same common reconstructed field ABI')
 donors={};controls={}
 for family,cid,catalog,maskpub,maskroot,summary,metricpub,metricroot,rawpub,rawroot in(('B0',B0,fc,fs,FIRST,fsum,fr,FIRST,fr,FIRST),('P23',P23,pc,ps,FAILED,rsum,rr,RECOVERY,pr,FAILED)):
  row=next(c for c in catalog['candidates']if c['candidate_id']==cid);mp=record(maskpub,Path(row['mask_path']),maskroot,row['mask_sha256']);rp=record(maskpub,Path(row['mask_receipt_path']),maskroot,row['mask_receipt_sha256']);receipt=js(rp['path'],rp['SHA256']);require(receipt['exact_area_proof']is True and receipt['no_overlap']is True,'Actual donor area/disjointness proof')
  if family=='P23':record(pr,Path(row['mask_path']),FAILED,row['mask_sha256']);record(pr,Path(row['mask_receipt_path']),FAILED,row['mask_receipt_sha256'])
  result=next(c for c in summary['candidates']if c['candidate_id']==cid);require(result['geometry']['mask_sha256']==mp['SHA256']and all(p['passed']is True for p in result['source_physics_proofs']),'Actual compatible passed donor physics, not prepared source')
  scalar=record(metricpub,Path(result['scalar_arrays']['path']),metricroot,result['scalar_arrays']['SHA256']);raw={}
  for f in(2000,2010):
   item=summary['raw_artifacts'][cid+'-'+str(f)];raw[str(f)]=record(rawpub,Path(item['path']),rawroot,item['SHA256'])
  donors[family]=dict(candidate_id=cid,mask=mp,receipt=rp,pads=receipt['pads'],source_commit=FIRST_S if family=='B0'else FAILED_S,original_result_commit=FIRST_R if family=='B0'else PARTIAL_R,metric_result_commit=metricpub['commit'])
  controls[cid]=dict(record=copy.deepcopy(result),scalar_arrays=scalar,raw_by_frequency=raw,source_summary=proofs[str(metricroot/'summary.json')])
 material=record(fs,Path(fc['material_path']),FIRST,fc['material_sha256']);contact=record(fs,Path(fc['contact_path']),FIRST,fc['contact_sha256'])
 common=record(fr,FIRST/'common-grid-and-ROI.npz',FIRST);roi=record(fr,FIRST/'ROI-receipt.json',FIRST,parse=True)
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(js(ap)==a,'Immutable admission bytes agree');refs[str(ap)]=digest(ap)
 return dict(admission=a,base_catalog=fc,donors=donors,controls=controls,material=material,contact=contact,common_grid_ROI=common,ROI_receipt=roi,input_pins=refs,publication_file_proofs=proofs,provisional_field=fsum['spec']['provisional_field'],holds=fsum['spec']['holds'])

def parse_mask(raw):
 rows=[];reader=csv.DictReader(io.StringIO(raw.decode()));require(reader.fieldnames==['pad','i','j','area_m2'],'Canonical donor CSV schema')
 for row in reader:
  p,i,j=(int(row[k])for k in('pad','i','j'));require(p in(0,1,2,3)and 0<=i<100 and 0<=j<100 and float(row['area_m2'])==float(H*H),'Existing full-face donor cell only');rows.append((p,i,j))
 require(len(rows)==len(set(rows)),'No duplicate donor pad/cell');return rows

def merge_rows(donor_rows,donor_by_pad):
 require(len(donor_by_pad)==4 and all(x in donor_rows for x in donor_by_pad),'Four explicit physicalpad donor assignments')
 rows=[];covered=set()
 for pad,family in enumerate(donor_by_pad):
  chosen=[r for r in donor_rows[family]if r[0]==pad];require(chosen,'Donor contains physicalpad')
  for p,i,j in chosen:
   require((i,j)not in covered,'Physical mixed pad overlap, no repair');covered.add((i,j));rows.append((p,i,j))
 return sorted(rows,key=lambda row:(row[0],row[2],row[1]))

def _physical_proof(rows):
 require(len(rows)==3600,'Exactly900mm2/3600 full faces across four physicalpads');pads=[]
 for p in range(4):
  cells={(i,j)for pad,i,j in rows if pad==p};require(len(cells)==900,'Eachphysicalpad225mm2 exact, no renormalization')
  for i,j in cells:
   x0=-R+i*H;y0=-R+j*H;require(all(x*x+y*y<=R*R for x in(x0,x0+H)for y in(y0,y0+H)),'Full cell remains inside unchangedD50')
  seen={min(cells)};todo=list(seen)
  while todo:
   i,j=todo.pop()
   for n in((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
    if n in cells and n not in seen:seen.add(n);todo.append(n)
  require(len(seen)==len(cells),'Copied physicalpad remains four-neighbour connected')
  pads.append(dict(pad=p,exact_area_m2=float(900*H*H),four_neighbor_connected=True))
 return pads

def _derive(context,recipe):
 donor_rows={family:parse_mask(read(d['mask']['path'],d['mask']['SHA256']))for family,d in context['donors'].items()};rows=merge_rows(donor_rows,recipe['donor_by_pad']);physical=_physical_proof(rows)
 raw=('pad,i,j,area_m2\n'+'\n'.join('%d,%d,%d,%s'%(p,i,j,format(float(H*H),'.17g'))for p,i,j in rows)+'\n').encode();pads=[]
 for pad,family in enumerate(recipe['donor_by_pad']):
  d=context['donors'][family];definition=copy.deepcopy(next(p for p in d['pads']if p['pad']==pad))
  if 'area_weighted_centroid_mm'not in definition:
   require(definition.get('shape')=='rectangle'and 'center_mm'in definition,'Published donor centroid metadata required');definition['area_weighted_centroid_mm']=copy.deepcopy(definition['center_mm']);definition['centroid_provenance']='Published rectangle center equals its area centroid'
  if 'topology'in definition:definition['perimeter_mm']=definition['topology']['perimeter_mm'];definition['perimeter_provenance']='Copied published donor full-face topology receipt'
  else:
   require(definition.get('shape')=='rectangle','Published donor perimeter metadata required');definition['perimeter_mm']=2*(definition['width_mm']+definition['height_mm']);definition['perimeter_provenance']='Exact rectangle perimeter from published width/height, no shape re-generation'
  definition.update(donor_family=family,donor_case_id=d['candidate_id'],donor_mask_sha256=d['mask']['SHA256'],node_index=pad if pad<2 else-1,node='out'+str(pad)if pad<2 else'GND',physical_pad_index=pad,all_contact_fractions_exactly_one=True);pads.append(definition)
 if recipe['control_source_case_id']is not None:
  family=recipe['donor_by_pad'][0];require(raw==read(context['donors'][family]['mask']['path'],context['donors'][family]['mask']['SHA256']),'Control CSV must remain exact byte alias, no re-encoding difference')
 receipt=dict(schema='task1-mixed-fourpad-mask-v1',candidate_id=recipe['candidate_id'],mask_sha256=sha(raw),physical_pads=4,independent_outputs=2,total_area_m2=float(3600*H*H),pads=pads,physical_checks=physical,donor_by_pad=recipe['donor_by_pad'],exact_area_proof=True,no_overlap=True,no_new_shape_algorithm=True,no_pad_repositioning=True,no_geometry_extension=True,all_contact_fractions_exactly_one=True)
 return raw,receipt

def make_spec(output_dir,admission=None):
 out=Path(output_dir);require(out.is_absolute()and out==out.resolve()and not out.is_symlink(),'Canonical new owner run');context=_context(admission);recipes=js(SOURCE/'catalog.json');require(tuple(r['candidate_id']for r in recipes['conditions'])==IDS and tuple(tuple(r['donor_by_pad'])for r in recipes['conditions'])==EXPECTED_DONORS and tuple(r['control_source_case_id']for r in recipes['conditions'])==(B0,P23,None,None),'Frozen exact four whole-pad donor recipes and control flags');catalog=copy.deepcopy(context['base_catalog']);pins=dict(context['input_pins']);pins[str(SOURCE/'catalog.json')]=digest(SOURCE/'catalog.json');cases=[]
 for recipe in recipes['conditions']:
  raw,receipt=_derive(context,recipe);cid=recipe['candidate_id'];mp=out/'masks'/(cid+'.csv');rp=out/'masks'/(cid+'-receipt.json');pins[str(mp)]=sha(raw);pins[str(rp)]=sha(encoded(receipt));control=recipe['control_source_case_id'];source=context['controls'].get(control)
  cases.append(dict(candidate_id=cid,status='source_recipe_geometry_ready_root_selection_pending',baseline=cid==B0,cached_alias_only=control is not None,control_source_case_id=control,source_case_id=control,reuse_first8_case_id=B0 if cid==B0 else None,mask_path=str(mp),mask_sha256=sha(raw),mask_receipt_path=str(rp),mask_receipt_sha256=sha(encoded(receipt)),pads=receipt['pads'],donor_by_pad=recipe['donor_by_pad'],source_control_record=copy.deepcopy(source['record'])if source else None,source_scalar=source['scalar_arrays']if source else None,source_raw_by_frequency=source['raw_by_frequency']if source else None))
 for kind,key in(('material','input-material.json'),('contact','input-contact.json')):pins[str(out/key)]=context[kind]['SHA256']
 catalog.update(schema='task1-mixed-fourpad-inputs-v1',candidates=cases,material_path=str(out/'input-material.json'),contact_path=str(out/'input-contact.json'),input_pins=pins,source_catalog_path=str(SOURCE/'catalog.json'),source_catalog_sha256=pins[str(SOURCE/'catalog.json')],source_allocation_amplitudes=[1.,1.],maximum_conditions=4,maximum_new_RHS=4,expected_new_RHS=4,expected_new_angular_metrics=2,control_metric_aliases=2,donors=context['donors'],common_grid_ROI=context['common_grid_ROI'],ROI_receipt=context['ROI_receipt'],root_admission=context['admission'],publication_file_proofs=context['publication_file_proofs'],provisional_field=context['provisional_field'],holds=context['holds'],source_input_snapshots=dict(material=context['material'],contact=context['contact']),grouped_geometry_scope='Signal pads0/1 versus commonreturn pads2/3 footprint, each225mm2; no independent source count increase',comparison_scope='Two mixed footprints plus original B0/P23 full aliases. Exact existing wholepads; field/contact uncertainty retained. No isolated pad-count, safety, physiological activation or adopted-convergence claim.',candidate_adopted=False,no_local_PC_allocation_or_reservation=True)
 return catalog

def required_inputs(output_dir=None,admission=None):
 if output_dir is not None:return dict(make_spec(output_dir,admission)['input_pins'])
 c=_context(admission);refs=dict(c['input_pins']);refs[str(SOURCE/'catalog.json')]=digest(SOURCE/'catalog.json')
 # SOURCE is the immutable admitted input namespace. __file__ becomes the
 # byte-identical worker snapshot path on deployment, so it cannot be an input
 # identity. The owner independently verifies both source and snapshot hashes.
 canonical_source=SOURCE/'mixed_catalog.py';refs[str(canonical_source)]=digest(canonical_source);return refs

def prepare_inputs(output_dir,admission=None):
 out=Path(output_dir);require(out.is_dir()and not out.is_symlink(),'Unique root-created output');catalog=make_spec(out,admission);context=_context(admission);(out/'masks').mkdir(exist_ok=True);outputs={out/'input-material.json':read(context['material']['path'],context['material']['SHA256']),out/'input-contact.json':read(context['contact']['path'],context['contact']['SHA256'])}
 for recipe,candidate in zip(js(SOURCE/'catalog.json')['conditions'],catalog['candidates']):
  raw,receipt=_derive(context,recipe);outputs[Path(candidate['mask_path'])]=raw;outputs[Path(candidate['mask_receipt_path'])]=encoded(receipt)
 outputs[out/'catalog-inputs.json']=encoded(catalog)
 for path,raw in outputs.items():
  if path.exists():require(read(path)==raw,'Preserve changed/partial mixed input, no overwrite')
  else:
   with path.open('xb')as stream:stream.write(raw)
  require(read(path)==raw,'Complete immutable mixed input readback')
 return catalog
