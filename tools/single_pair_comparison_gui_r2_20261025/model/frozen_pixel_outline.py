"""Exact boundary of authenticated full contact-cell unions, no import work.

Physical masks are not replaced by bounding boxes, fitted circles or smoothing.
The root passes already SHA-verified CSV bytes; no filesystem or numerical
libraries are used here. Vertices stay on the native half-millimetre faces.
"""
import csv,io

def require(ok,message):
 if not ok:raise ValueError(message)

def mask_cells(raw,h_mm=.5):
 require(type(raw)is bytes and h_mm==.5,'Actual registered h0.5 full-face CSV bytes')
 reader=csv.DictReader(io.StringIO(raw.decode()));require(reader.fieldnames==['pad','i','j','area_m2'],'Canonical actual contact mask schema');pads={};allcells=set()
 for row in reader:
  p,i,j=(int(row[key])for key in('pad','i','j'));require(p>=0 and 0<=i<100 and 0<=j<100 and float(row['area_m2'])==(h_mm*.001)**2,'Actual full-face area, not contact fraction')
  require((i,j)not in allcells,'Disjoint physical pads; no duplicate contact cell');allcells.add((i,j));pads.setdefault(p,set()).add((i,j))
 require(pads,'No actual contact cells');return pads

def integer_contours(cells):
 """Counterclockwise exterior/clockwise hole loops with foreground on left."""
 cells=set(cells);require(cells and all(type(i)is int and type(j)is int for i,j in cells),'Nonempty integer grid cells');edges=set()
 for i,j in cells:
  if(i,j-1)not in cells:edges.add(((i,j),(i+1,j)))
  if(i+1,j)not in cells:edges.add(((i+1,j),(i+1,j+1)))
  if(i,j+1)not in cells:edges.add(((i+1,j+1),(i,j+1)))
  if(i-1,j)not in cells:edges.add(((i,j+1),(i,j)))
 remaining=set(edges);outgoing={}
 for a,b in edges:outgoing.setdefault(a,set()).add(b)
 dirs={(1,0):0,(0,1):1,(-1,0):2,(0,-1):3};turn_priority={1:0,0:1,3:2,2:3};loops=[]
 while remaining:
  first=min(remaining);a,b=first;remaining.remove(first);path=[a,b];previous=a;current=b
  while current!=path[0]:
   candidates=[v for v in outgoing.get(current,())if(current,v)in remaining];require(candidates,'Actual pixel boundary does not close');incoming=dirs[(current[0]-previous[0],current[1]-previous[1])]
   def priority(v):
    direction=dirs[(v[0]-current[0],v[1]-current[1])];return turn_priority[(direction-incoming)%4],v
   nxt=min(candidates,key=priority);remaining.remove((current,nxt));previous,current=current,nxt;path.append(current);require(len(path)<=len(edges)+1,'Boundary traversal repeated an edge')
  loops.append(path)
 signed_twice=[sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(loop[:-1],loop[1:]))for loop in loops]
 require(sum(signed_twice)==2*len(cells),'Pixel boundary signed area differs from actual contact-cell count')
 return loops,signed_twice

def electrodes(raw,pad_metadata,h_mm=.5):
 cells=mask_cells(raw,h_mm);definitions={int(p['pad']):dict(p)for p in pad_metadata};require(set(cells)==set(definitions),'Every physical pad needs its actual metadata; no inferred electrical outputs');result=[]
 for p in sorted(cells):
  loops,areas=integer_contours(cells[p]);definition=definitions[p];represented=len(cells[p])*h_mm*h_mm*1e-6;expected=definition.get('analytic_area_m2',definition.get('represented_area_m2'))
  require(expected is not None and abs(represented-float(expected))<=1e-10*max(represented,float(expected)),'Actual outline area agrees with registered physical pad')
  definition.update(mask_contours_mm=[[[-25+i*h_mm,-25+j*h_mm]for i,j in loop]for loop in loops],mask_contour_signed_area_mm2=[area*h_mm*h_mm/2 for area in areas],mask_fill_rule='evenodd',mask_full_cell_count=len(cells[p]),mask_h_mm=h_mm,mask_display_definition='Exact unsmoothed union of authenticated contact squares, with explicit hole contours',outline_area_m2=represented)
  result.append(definition)
 return result
