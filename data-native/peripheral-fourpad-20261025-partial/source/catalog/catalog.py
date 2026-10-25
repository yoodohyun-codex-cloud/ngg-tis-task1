"""Proposed full-face peripheral polyomino family; owner-only scalar derivation.
No files, cells, mask counts, arrays, tests or numerical work execute on import.
"""
from __future__ import annotations
import hashlib,json,math
from fractions import Fraction
from pathlib import Path
SOURCE=Path('/dev/shm/task1-peripheral-fourpad-20261025/source')
U19=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run')
MATERIAL=U19/'material-input.json';CONTACT=U19/'contact-receipt.json'
MATERIAL_SHA='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
CONTACT_SHA='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
IDS=('B0-square15-c10-diagonal','G1-square12-c10-diagonal','P24-peripheral-polyomino225','P23p5-peripheral-polyomino225','P12-square-c11p5-diagonal')
LAYERS=('sc','dermis','fat','muscle');FREQUENCIES=(2000,2010);EPS0=8.8541878128e-12
H=Fraction(1,2000);R=Fraction(1,40)
class RecipeBlocker(ValueError):pass

def require(ok,message):
 if not ok:raise RecipeBlocker(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(obj):return(json.dumps(obj,allow_nan=False,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def _read(path):
 p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Bounded regular source/input');return p.read_bytes()
def source_catalog():
 data=json.loads(_read(SOURCE/'catalog.json'));require(tuple(c['candidate_id']for c in data['conditions'])==IDS,'Exactly frozen five proposed conditions');return data

def _material_contact():
 mr=_read(MATERIAL);cr=_read(CONTACT);require(sha(mr)==MATERIAL_SHA and sha(cr)==CONTACT_SHA,'Unchanged actual declared-surrogate/contact receipts')
 material=json.loads(mr);contact=json.loads(cr);m={(r['layer'],int(r['frequency_Hz'])):r for r in material['rows']};z={int(r['frequency_Hz']):r for r in contact['rows']};gamma={};sigma={};epsilon={};specific={}
 require(contact['Rs_subtractions']==1 and contact['measurement_area_multiplications']==1 and contact['division_by_two']is False,'Frozen effectiveRs/measurementarea applied once')
 for f in FREQUENCIES:
  gamma[str(f)]=[];sigma[str(f)]=[];epsilon[str(f)]=[]
  for layer in LAYERS:
   r=m[layer,f];s=float(r['sigma_S_m']);e=float(r['epsilon_r']);im=2*math.pi*f*EPS0*e;require(r['assignment_type']=='declared_surrogate'and s>0 and e>0 and math.isfinite(s+e+im),'Explicit existing row perlayer/carrier')
   gamma[str(f)].append(dict(real=s,imaginary=im));sigma[str(f)].append(s);epsilon[str(f)].append(e)
  specific[str(f)]=dict(real=float(z[f]['area_real_ohm_m2']),imaginary=float(z[f]['area_imag_ohm_m2']))
 return mr,cr,gamma,sigma,epsilon,specific

def _connected(cells):
 if not cells:return False
 seen={min(cells)};todo=list(seen)
 while todo:
  i,j=todo.pop()
  for neighbor in((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
   if neighbor in cells and neighbor not in seen:seen.add(neighbor);todo.append(neighbor)
 return len(seen)==len(cells)

def _topology(cells):
 require(_connected(cells),'Final physical pad is not four-neighbour connected; no maskrepair allowed')
 perimeter=sum((i+di,j+dj)not in cells for i,j in cells for di,dj in((-1,0),(1,0),(0,-1),(0,1)))
 lo=min(i for i,j in cells)-1;hi=max(i for i,j in cells)+1;lj=min(j for i,j in cells)-1;hj=max(j for i,j in cells)+1;unseen={(i,j)for i in range(lo,hi+1)for j in range(lj,hj+1)if(i,j)not in cells};holes=0
 while unseen:
  start=min(unseen);unseen.remove(start);todo=[start];outside=False
  while todo:
   i,j=todo.pop();outside=outside or i in(lo,hi)or j in(lj,hj)
   for n in((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
    if n in unseen:unseen.remove(n);todo.append(n)
  if not outside:holes+=1
 return dict(four_neighbor_connected=True,exposed_pixel_edges=perimeter,perimeter_mm=float(perimeter*H*1000),interior_hole_components=holes)

def select_ordered_orbits(ordered,target):
 """Whole-orbit prefix with ONE fixed parity exception, defined beforedata."""
 selected=set();skipped=[];taken=[]
 for score,orbit in ordered:
  remaining=target-len(selected)
  if remaining==0:break
  if len(orbit)>remaining:
   require(remaining==1 and len(orbit)==2,'Only declaredtwo-cellparityskip permitted')
   skipped.append(dict(orbit=[list(c)for c in orbit],radius_squared_m2=float(score),radius_squared_exact=[score.numerator,score.denominator],reason='predeclared_skip_two_cell_orbit_when_one_slot_remains'))
   continue
  selected.update(orbit);taken.append((score,orbit))
 require(len(selected)==target,'No exact whole-orbit selection of900 after fixedparityrule; no appendedcells')
 return selected,taken,skipped

def _peripheral(condition):
 outer=Fraction(str(condition['outer_radius_mm']))/1000;gap=Fraction(str(condition['minimum_axis_face_mm']))/1000;target=int(condition['target_full_cells_per_pad']);eligible={}
 require(outer<R and gap>=H and target==900,'Fixed outerradius/minimumaxisgap/exact900-fullcell target')
 for j in range(100):
  y0=-R+j*H;y1=y0+H
  if y0<gap:continue
  for i in range(100):
   x0=-R+i*H;x1=x0+H
   if x0<gap:continue
   if all(x*x+y*y<=outer*outer for x in(x0,x1)for y in(y0,y1)):
    x=(x0+x1)/2;y=(y0+y1)/2;eligible[i,j]=x*x+y*y
 require(len(eligible)>=target,'Fewer than900eligiblecontainedfullcells; no geometry/area expansion')
 orbits=[];seen=set()
 for cell,score in eligible.items():
  if cell in seen:continue
  i,j=cell;orbit=tuple(sorted({(i,j),(j,i)}));require(all(c in eligible and eligible[c]==score for c in orbit),'Exact swap symmetry of eligibility and radius');seen.update(orbit);orbits.append((score,orbit))
 ordered=sorted(orbits,key=lambda row:(-row[0],abs(row[1][0][0]-row[1][0][1]),min(row[1][0]),max(row[1][0])))
 selected,taken,skipped=select_ordered_orbits(ordered,target)
 require({(j,i)for i,j in selected}==selected,'Exact full swap symmetry, no split orbit');topology=_topology(selected);lastscore,lastorbit=taken[-1]
 return selected,dict(selection_policy_version='v2-fixed-whole-orbit-order',method='Descending exactcentre r², thenascendingabs(x-y),thenmin(x,y); wholeorbits; fixedskip2whenremaining1',
  outer_radius_mm=float(outer*1000),minimum_axis_face_mm=float(gap*1000),eligible_full_cells=len(eligible),selected_full_cells=len(selected),target_full_cells=target,
  last_selected_radius_squared_m2=float(lastscore),last_selected_radius_squared_exact=[lastscore.numerator,lastscore.denominator],last_selected_orbit=[list(c)for c in lastorbit],parity_skipped_orbits=skipped,
  lower_rank_policy='Only predeclared firstlater diagonal singleton when one slot remains; no arbitrary filler',all_equal_radius_orbits_required_together=False,orbit_split=False,extra_cells_appended=False,connectivity_repaired=False,topology=topology,shape='union of h.5mm squares, NOT smoothannularsector')

def _square(condition):
 side=Fraction(str(condition['side_mm']))/1000;c=Fraction(str(condition['center_abs_mm']))/1000;lo=c-side/2;hi=c+side/2;indices=[(lo+R)/H,(hi+R)/H];require(all(i.denominator==1 for i in indices),'Square exactcoarse facealignment');a,b=(int(i)for i in indices);cells={(i,j)for i in range(a,b)for j in range(a,b)}
 require(all(x*x+y*y<R*R for x in(lo,hi)for y in(lo,hi)),'Squarewhollyinside fixedD50');return cells,dict(method='Exactgridalignedsquare',side_mm=float(side*1000),center_abs_mm=float(c*1000),topology=_topology(cells))

def derive_mask(condition):
 cells,selection=_peripheral(condition)if condition['recipe']=='radial_orbit_prefix'else _square(condition);expected=Fraction(str(condition['expected_pad_area_mm2']))/1000000
 require(len(cells)*H*H==expected,'Exact intendedpadarea withoutrescale');text=['pad,i,j,area_m2'];pads=[];allcells=set();signs=((-1,-1),(1,1),(1,-1),(-1,1))
 for pad,(sx,sy)in enumerate(signs):
  actual={(i if sx>0 else 99-i,j if sy>0 else 99-j)for i,j in cells};require(not(actual&allcells),'Physicalpadsdisjoint');allcells.update(actual)
  for i,j in actual:
   x0=-R+i*H;y0=-R+j*H;require(all(x*x+y*y<=R*R for x in(x0,x0+H)for y in(y0,y0+H)),'Everyphysicalcontactfullcell contained in D50')
  for i,j in sorted(actual,key=lambda p:(p[1],p[0])):text.append('%d,%d,%d,%s'%(pad,i,j,format(float(H*H),'.17g')))
  topology=_topology(actual);coords=[(-R+(Fraction(i)+Fraction(1,2))*H,-R+(Fraction(j)+Fraction(1,2))*H)for i,j in actual];centroid=[float(sum(p[k]for p in coords)/len(coords)*1000)for k in(0,1)]
  pads.append(dict(pad=pad,node_index=pad if pad<2 else-1,node='out'+str(pad)if pad<2 else'GND',shape='pixelated_polyomino'if condition['recipe']=='radial_orbit_prefix'else'rectangle',analytic_area_m2=float(expected),represented_area_m2=float(len(actual)*H*H),full_cells=len(actual),area_weighted_centroid_mm=centroid,topology=topology,bounds_mm=[float((-R+min(i for i,j in actual)*H)*1000),float((-R+(max(i for i,j in actual)+1)*H)*1000),float((-R+min(j for i,j in actual)*H)*1000),float((-R+(max(j for i,j in actual)+1)*H)*1000)],all_contact_fractions_exactly_one=True))
 raw=('\n'.join(text)+'\n').encode();receipt=dict(schema='task1-peripheral-fourpad-mask-v1',candidate_id=condition['candidate_id'],selection=selection,pads=pads,physical_pads=4,independent_outputs=2,total_area_m2=float(4*expected),mask_sha256=sha(raw),exact_area_proof=True,no_overlap=True,body_size_changed=False,shape_not_smoothed=True,manufacturability_not_validated=True,mask_edge_Jmax_uncertainty_preserved=True)
 return raw,receipt

def make_spec(output_dir):
 out=Path(output_dir);require(out.is_absolute()and not out.is_symlink(),'Explicitfutureowner output');data=source_catalog();mr,cr,gamma,sigma,epsilon,z=_material_contact();cases=[];pins={str(SOURCE/'catalog.json'):sha(_read(SOURCE/'catalog.json')),str(MATERIAL):MATERIAL_SHA,str(CONTACT):CONTACT_SHA,str(out/'input-material.json'):MATERIAL_SHA,str(out/'input-contact.json'):CONTACT_SHA}
 for condition in data['conditions']:
  try:
   raw,receipt=derive_mask(condition);cid=condition['candidate_id'];mp=out/'masks'/(cid+'.csv');rp=out/'masks'/(cid+'-receipt.json');pins[str(mp)]=sha(raw);pins[str(rp)]=sha(encoded(receipt))
   cases.append(dict(candidate_id=cid,status='source_recipe_geometry_ready_root_selection_pending',baseline=cid==IDS[0],reuse_first8_case_id=condition['reuse_first8_case_id'],source_first8_case_id=condition['reuse_first8_case_id'],reuse_control_both_carriers_required=condition['reuse_first8_case_id']is not None,mask_path=str(mp),mask_sha256=sha(raw),mask_receipt_path=str(rp),mask_receipt_sha256=sha(encoded(receipt)),pads=receipt['pads'],selection=receipt['selection']))
  except RecipeBlocker as error:
   entry=dict(candidate_id=condition['candidate_id'],status='recipe_blocked',blocker=str(error),mask_path=None,blocker_receipt_path=str(out/'masks'/(condition['candidate_id']+'-BLOCKER.json')),no_forced_count_or_connectivity_repair=True);cases.append(entry);pins[entry['blocker_receipt_path']]=sha(encoded(entry))
 return dict(schema='task1-proposed-peripheral-fourpad-inputs-v1',candidates=cases,source_catalog_path=str(SOURCE/'catalog.json'),source_catalog_sha256=sha(_read(SOURCE/'catalog.json')),material_path=str(out/'input-material.json'),material_sha256=MATERIAL_SHA,contact_path=str(out/'input-contact.json'),contact_sha256=CONTACT_SHA,gamma_by_frequency=gamma,sigma_by_frequency=sigma,epsilon_r_by_frequency=epsilon,z_by_frequency=z,layer_order=list(LAYERS),frequencies=list(FREQUENCIES),drives={'2000':dict(output=0,source_peak_V=.5,source_Vpp=1.),'2010':dict(output=1,source_peak_V=.5,source_Vpp=1.)},source_resistance_ohm=50.,inactive_output='0Vbehind50ohm',return_topology='Physicalpad2and3 hardcommon0V',physical_pads=4,independent_outputs=2,
  grid=dict(backend='cached_coarse_XY100_DtN_CEM',h_mm=.5,nx=100,nxy=7860,layer_counts=[8,19,18,56],cells=793860,radius_mm=25.,layer_thickness_mm=[.1,5,5,15]),
  source_allocation_amplitudes=[1.,1.],control_alias_requires_exact_allocation=[1.,1.],unequal_future_allocation_requires_recomputed_cached_control_metrics_not_equalV_alias=True,maximum_conditions=5,maximum_new_RHS_with_B0_G1_verified_reuse=6,controls_must_reuse_first8_published_raw_and_matching_ABI=True,first8_reference_run='/dev/shm/task1-design-screen-coarse-20261025-run',
  geometry_recipe_blockers=[dict(candidate_id=c['candidate_id'],blocker=c['blocker'])for c in cases if c['status']=='recipe_blocked'],
  ready_new_candidate_ids=[c['candidate_id']for c in cases if c['status']!='recipe_blocked'and c['source_first8_case_id']is None],expected_new_RHS=2*sum(c['status']!='recipe_blocked'and c.get('source_first8_case_id')is None for c in cases),expected_new_angular_metrics=sum(c['status']!='recipe_blocked'and c.get('source_first8_case_id')is None for c in cases),ranking_status='source_only_unadmitted_nextfamily',root_finite_selection_after_current_allocation_required=True,no_actual_execution_or_candidate_adoption=True,no_new_eigen_work=True,no_local_PC_allocation_or_reservation=True,no_geometry_extension=True,
  comparison_scope='B0 vsP24/P23p5 equal225mm²/pad; G1 vsP12 matched144mm² spacingcomparison; peripherychangescentroid/coverage/gap/perimeter/shapejointly, no isolatedcausalclaim',common_ROI=dict(radius_mm=5,depth_mm=[15,20],depth_origin='physicaltop,+zdown'),comparison_modes=['fixed1Vpp','same_totalcurrent','same_totalpower','same_surfaceburden'],known_accuracy_material_contact_and_edge_uncertainty_preserved=True,input_pins=pins)

def required_inputs(output_dir=None):
 _material_contact();refs={str(SOURCE/'catalog.json'):sha(_read(SOURCE/'catalog.json')),str(Path(__file__)):sha(_read(Path(__file__))),str(MATERIAL):MATERIAL_SHA,str(CONTACT):CONTACT_SHA}
 if output_dir is not None:refs.update(make_spec(output_dir)['input_pins'])
 return refs

def prepare_inputs(output_dir):
 out=Path(output_dir);require(out.is_absolute()and out.is_dir()and not out.is_symlink(),'Futureowner-createduniquerun');(out/'masks').mkdir(exist_ok=True);spec=make_spec(out);outputs={out/'input-material.json':_read(MATERIAL),out/'input-contact.json':_read(CONTACT)}
 for condition,entry in zip(source_catalog()['conditions'],spec['candidates']):
  if entry['status']=='recipe_blocked':outputs[out/'masks'/(entry['candidate_id']+'-BLOCKER.json')]=encoded(entry);continue
  raw,receipt=derive_mask(condition);outputs[Path(entry['mask_path'])]=raw;outputs[Path(entry['mask_receipt_path'])]=encoded(receipt)
 for path,raw in outputs.items():
  if path.exists():require(_read(path)==raw,'Preservechangedorpartialinput; nooverwrite')
  else:
   with path.open('xb')as stream:stream.write(raw)
  require(_read(path)==raw,'Completepreparedinputreadback')
 cp=out/'catalog-inputs.json';raw=encoded(spec)
 if cp.exists():require(_read(cp)==raw,'Immutableperipheralcatalogsnapshot')
 else:
  with cp.open('xb')as stream:stream.write(raw)
 return spec
