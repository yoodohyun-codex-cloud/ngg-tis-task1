"""Pure manual view/range adapters for the two earlier scientific GUI layers.

The parent owns immutable source validation, UI helper, CSP, numerical checks,
budget and publication. This module has no I/O or numerical work on import.
"""
from __future__ import annotations
import hashlib

ORIGINAL_SCRIPT_SHA256='2bdfb643e8e32cd248b77fb8ec8c2fbbf178796c668e94bb443849801928a54b'
VECTOR_SCRIPT_SHA256='c06a9def126d04330d9eb0e8c8775316e517eb1df572c02fdd196741e45d36d1'


def once(text,before,after):
    n=text.count(before)
    if n!=1:raise ValueError(f'Expected one reviewed manual legacy anchor ({n}): {before[:100]}')
    return text.replace(before,after,1)


def replace_function(script,name,replacement):
    start=script.index('function '+name+'(')
    # The reviewed sources put each following declaration on a new line, except
    # role()/locate() which follow the previous function on the same line.
    if name=='color' and 'function role(' in script[start:]:
        stop=script.index('function role(',start)
    elif name=='pixels':
        stop=script.index('\nfunction locate(',start)
    else:
        stop=script.find('\nfunction ',start+1)
    if stop<0:raise ValueError('Following reviewed function required: '+name)
    return script[:start]+replacement.rstrip()+'\n'+script[stop:]


ORIGINAL_COLOR=r'''function color(v,max,field=true,min=0){if(!Number.isFinite(v))return'#e8eef2';const q=field?window.task1FixedScales.colorFraction(v,max,min):Math.max(0,Math.min(1,(v-min)/(max-min)));let t=q*5,i=Math.min(4,Math.floor(t)),f=t-i;return'rgb('+palette[i].map((v,k)=>Math.round(v+(palette[i+1][k]-v)*f)).join(',')+')';}'''

FRAME=r'''function frame(canvas,xe,ye,down=false,kind='layout',options={}){const w=Math.max(170,canvas.clientWidth),h=canvas.classList.contains('field-map')?290:175,d=Math.min(2,devicePixelRatio||1);canvas.width=w*d;canvas.height=h*d;const c=canvas.getContext('2d');c.scale(d,d);c.fillStyle='#fff';c.fillRect(0,0,w,h);const b={l:43,r:12,t:12,b:31},pw=w-b.l-b.r,ph=h-b.t-b.b,view=window.task1ManualRanges.get(canvas.id,{xMin:xe[0],xMax:xe.at(-1),yMin:ye[0],yMax:ye.at(-1),cMin:0,cMax:kind==='JMap'?TASK1_LOCKED_J:TASK1_LOCKED_E},{kind,xLabel:'x [mm]',yLabel:down?'depth z [mm]':'y [mm]',axisX:'x',axisY:down?'z':'y',colorUnit:kind==='JMap'?'A/m²':'V/m',colour:kind!=='layout',...options}),X=x=>b.l+(x-view.xMin)/(view.xMax-view.xMin)*pw,Y=y=>b.t+(down?(y-view.yMin):(view.yMax-y))/(view.yMax-view.yMin)*ph;canvas.dataset.xMin=String(view.xMin);canvas.dataset.xMax=String(view.xMax);canvas.dataset.yMin=String(view.yMin);canvas.dataset.yMax=String(view.yMax);canvas.dataset.vmin=String(view.cMin);canvas.dataset.vmax=String(view.cMax);canvas.dataset.scaleMode='manual';canvas.dataset.axisOrientation=down?'depth_down':'y_up';return{c,w,h,b,pw,ph,X,Y,xe,ye,down,view,id:canvas.id};}'''

AXES=r'''function axes(f,xlab,ylab){const{c,X,Y,view,b,w,h}=f;c.strokeStyle='#b9cad4';c.lineWidth=.7;c.strokeRect(b.l,b.t,f.pw,f.ph);c.fillStyle='#607889';c.font='10px system-ui';c.textAlign='center';for(const x of[view.xMin,(view.xMin+view.xMax)/2,view.xMax])c.fillText(F(x,4),X(x),h-17);c.fillText(xlab,b.l+f.pw/2,h-3);c.textAlign='right';for(const y of[view.yMin,(view.yMin+view.yMax)/2,view.yMax])c.fillText(F(y,4),b.l-4,Y(y)+3);c.save();c.translate(10,b.t+f.ph/2);c.rotate(-Math.PI/2);c.textAlign='center';c.fillText(ylab,0,0);c.restore();}'''

PIXELS=r'''function pixels(f,v,max,scale,field=true){const{c,X,Y,xe,ye,view}=f;let low=0,high=0,total=0,hidden=0;c.save();c.beginPath();c.rect(f.b.l,f.b.t,f.pw,f.ph);c.clip();for(let j=0;j<ye.length-1;j++)for(let i=0;i<xe.length-1;i++){const value=v[j*(xe.length-1)+i]*scale;if(Number.isFinite(value)){total++;if(value<view.cMin)low++;if(value>view.cMax)high++;const cx=(xe[i]+xe[i+1])/2,cy=(ye[j]+ye[j+1])/2;if(cx<view.xMin||cx>view.xMax||cy<view.yMin||cy>view.yMax)hidden++;}c.fillStyle=color(value,view.cMax,field,view.cMin);const x=X(xe[i]),y=Y(ye[j]),yy=Y(ye[j+1]),top=Math.min(y,yy),width=X(xe[i+1])-x+.1,height=Math.abs(yy-y)+.1;c.fillRect(x,top,width,height);if(Number.isFinite(value)&&(value<view.cMin||value>view.cMax)){c.strokeStyle='rgba(255,255,255,.58)';c.lineWidth=.65;c.beginPath();c.moveTo(x,top+height);c.lineTo(x+width,top);c.stroke();}}c.restore();window.task1ManualRanges.note(f.id,{low,high,total,viewportHidden:hidden});}'''

HOVER=r'''function hover(canvas,f,v,scale,key,plane,z,unit){canvas.onpointermove=e=>{const r=canvas.getBoundingClientRect(),px=(e.clientX-r.left)*f.w/r.width,py=(e.clientY-r.top)*f.h/r.height;if(px<f.b.l||px>f.b.l+f.pw||py<f.b.t||py>f.b.t+f.ph)return;const x=f.view.xMin+(px-f.b.l)/f.pw*(f.view.xMax-f.view.xMin),t=(py-f.b.t)/f.ph,y=f.down?f.view.yMin+t*(f.view.yMax-f.view.yMin):f.view.yMax-t*(f.view.yMax-f.view.yMin),i=locate(f.xe,x),j=locate(f.ye,y);if(i<0||j<0){$('hover').textContent=key+' · 표시 좌표는 팬텀 native 격자 밖입니다.';return;}const a=(f.xe[i]+f.xe[i+1])/2,b=(f.ye[j]+f.ye[j+1])/2,value=v[j*(f.xe.length-1)+i]*scale,xyz=plane==='xy'?[a,b,z]:plane==='xz'?[a,G.XZ_actual_y_mm,b]:[G.YZ_actual_x_mm,a,b];$('hover').textContent=`${key} · xyz ${xyz.map(x=>F(x,5)).join(', ')} mm · ${Number.isFinite(value)?F(value,7)+' '+unit:'영역 밖 / 미지원 (NaN)'} · Float16 표시 원값 · 수동 색 범위로 값을 바꾸지 않습니다`;};}'''

LAYOUT=r'''function layout(canvas,key){const data=S[key],f=frame(canvas,G.x_edges_mm,G.y_edges_mm,false,'layout',{title:key+' 상면 전극 배치'}),{c,X,Y}=f;c.save();c.beginPath();c.rect(f.b.l,f.b.t,f.pw,f.ph);c.clip();for(const p of data.physical_outlines){const xy=p.polygon_mm;c.beginPath();c.moveTo(X(xy[0][0]),Y(xy[0][1]));for(const[x,y]of xy.slice(1))c.lineTo(X(x),Y(y));c.closePath();c.fillStyle={out0:'#e78b50',out1:'#4386c9',GND:'#bdcbd4'}[role(p.node)];c.fill();c.strokeStyle='#27485d';c.lineWidth=.8;c.stroke();}c.strokeStyle='#718c9c';c.beginPath();c.ellipse(X(0),Y(0),Math.abs(X(25)-X(0)),Math.abs(Y(25)-Y(0)),0,0,2*Math.PI);c.stroke();c.fillStyle='#153b52';c.font='bold 10px system-ui';c.textAlign='center';for(const p of data.pad_centres)c.fillText(`${p.pad}:${role(p.node)}`,X(p.x_mm),Y(p.y_mm));c.restore();axes(f,'x [mm]','y [mm]');}'''

FIELD=r'''function field(canvas,key,scale,max){const plane=$('plane').value,i=Number($('depth').value),p=S[key].RMS,v=decode(plane==='xy'?p.xy[i]:p[plane]),xe=plane==='yz'?G.y_edges_mm:G.x_edges_mm,ye=plane==='xy'?G.y_edges_mm:G.z_faces_mm,f=frame(canvas,xe,ye,plane!=='xy','EMap',{title:key+' 전체 carrier RMS',axisX:plane==='yz'?'y':'x',axisY:plane==='xy'?'y':'z',xLabel:plane==='yz'?'y [mm]':'x [mm]',yLabel:plane==='xy'?'y [mm]':'depth z [mm]'});pixels(f,v,max,scale);canvas.dataset.colorTransform=window.task1FixedScales.transform();const{c,X,Y}=f;c.save();c.beginPath();c.rect(f.b.l,f.b.t,f.pw,f.ph);c.clip();c.strokeStyle='white';c.lineWidth=1.3;c.setLineDash([4,3]);if(plane==='xy'){c.beginPath();c.ellipse(X(0),Y(0),Math.abs(X(5)-X(0)),Math.abs(Y(5)-Y(0)),0,0,2*Math.PI);c.stroke();}else{const fixed=plane==='xz'?G.XZ_actual_y_mm:G.YZ_actual_x_mm,r=Math.sqrt(Math.max(0,25-fixed*fixed));c.strokeRect(X(-r),Y(15),X(r)-X(-r),Y(20)-Y(15));for(const z of[.1,5.1,10.1]){c.beginPath();c.moveTo(X(xe[0]),Y(z));c.lineTo(X(xe.at(-1)),Y(z));c.stroke();}}c.setLineDash([]);c.restore();axes(f,plane==='yz'?'y [mm]':'x [mm]',plane==='xy'?'y [mm]':'+z depth [mm]');hover(canvas,f,v,scale,key,plane,G.XY_actual_depths_mm[i],'V/m');}'''

CONTACT=r'''function contact(canvas,key,scale,max){const data=S[key],raw=typeof data.contactJ==='string'?data.contactJ:data.contactJ.values_b64,v=decode(raw),f=frame(canvas,G.x_edges_mm,G.y_edges_mm,false,'JMap',{title:key+' 접촉 normal J RMS'});pixels(f,v,max,scale,false);canvas.dataset.colorTransform='linear';axes(f,'x [mm]','y [mm]');hover(canvas,f,v,scale,key,'xy',0,'A/m²');}'''


def patch_original(script):
    if hashlib.sha256(script.encode()).hexdigest()!=ORIGINAL_SCRIPT_SHA256:
        raise ValueError('Reviewed original scientific GUI script changed')
    for name,replacement in [('color',ORIGINAL_COLOR),('frame',FRAME),('axes',AXES),('pixels',PIXELS),('hover',HOVER),('layout',LAYOUT),('field',FIELD),('contact',CONTACT)]:
        script=replace_function(script,name,replacement)
    script=once(script,"fill('range',{global:'모든 조건 고정 범위 · 자동 조정 없음'},'global');$('range').disabled=true;", "fill('range',{global:'각 그래프 아래 눈금 직접 조절'},'global');$('range').disabled=true;")
    script=once(script,"$('field-legend').textContent=`E RMS 고정 0–${F(fmax)} V/m · 모든 지원 조건에서 동일 / 자동 조정 없음`;", "$('field-legend').textContent='E RMS 색상 범위는 공통 설정 또는 각 그래프 아래 수동 눈금 설정을 사용합니다.';")
    script=once(script,"$('contact-legend').textContent=`접촉 normal J RMS 고정 0–${F(jmax)} A/m² · 모든 지원 조건에서 동일`;", "$('contact-legend').textContent='접촉 normal J RMS는 A/m² 단위의 공통/개별 수동 색상 범위를 사용합니다.';")
    return script


VECTOR_COLOR=r'''function color(v,max,min=0){const z=window.task1FixedScales.colorFraction(v,max,min)*(COLORS.length-1),i=Math.min(COLORS.length-2,Math.floor(z)),t=z-i,a=COLORS[i],b=COLORS[i+1];return 'rgb('+a.map((v,k)=>Math.round(v+(b[k]-v)*t)).join(',')+')';}'''

PLOT=r'''function plot(c,p,V,max){const {el,g,w,h}=canvas('shape-'+c),pad={l:49,r:15,t:17,b:44},ue=edge(p.u_mm,p.u_edges_mm),ve=edge(p.v_mm,p.v_edges_mm),nu=p.u_mm.length,nv=p.v_mm.length,view=window.task1ManualRanges.get(el.id,{xMin:ue[0],xMax:ue.at(-1),yMin:ve[0],yMax:ve.at(-1),cMin:0,cMax:TASK1_LOCKED_E},{kind:'EMap',title:c+' 순간 전기장',axisX:p.kind==='YZ'?'y':'x',axisY:p.kind==='XY'?'y':'z',xLabel:p.u_label,yLabel:p.v_label,colorUnit:'V/m',colour:true}),umin=view.xMin,umax=view.xMax,vmin=view.yMin,vmax=view.yMax,width=w-pad.l-pad.r,height=h-pad.t-pad.b;
const down=p.kind!=='XY',xp=u=>pad.l+(u-umin)/(umax-umin)*width,yp=v=>pad.t+(down?(v-vmin):(vmax-v))/(vmax-vmin)*height;el.dataset.colorTransform=window.task1FixedScales.transform();el.dataset.vmin=String(view.cMin);el.dataset.vmax=String(view.cMax);el.dataset.xMin=String(umin);el.dataset.xMax=String(umax);el.dataset.yMin=String(vmin);el.dataset.yMax=String(vmax);el.dataset.scaleMode='manual';el.dataset.axisOrientation=down?'depth_down':'y_up';
g.clearRect(0,0,w,h);g.fillStyle='#e9f0f3';g.fillRect(pad.l,pad.t,width,height);g.save();g.beginPath();g.rect(pad.l,pad.t,width,height);g.clip();let low=0,high=0,total=0,hidden=0;
for(let j=0;j<nv;j++)for(let i=0;i<nu;i++){const k=j*nu+i;if(p.native_indices[k]<0)continue;const value=V.mag[k];total++;if(value<view.cMin)low++;if(value>view.cMax)high++;if(p.u_mm[i]<umin||p.u_mm[i]>umax||p.v_mm[j]<vmin||p.v_mm[j]>vmax)hidden++;g.fillStyle=color(value,view.cMax,view.cMin);const xx=xp(ue[i]),yy=Math.min(yp(ve[j]),yp(ve[j+1])),ww=Math.max(.3,xp(ue[i+1])-xp(ue[i])+.2),hh=Math.max(.3,Math.abs(yp(ve[j+1])-yp(ve[j]))+.2);g.fillRect(xx,yy,ww,hh);if(value<view.cMin||value>view.cMax){g.beginPath();g.strokeStyle='rgba(255,255,255,.58)';g.lineWidth=.65;g.moveTo(xx,yy+hh);g.lineTo(xx+ww,yy);g.stroke();}}
if(p.kind!=='XY'){for(const z of [.1,5.1,10.1]){g.beginPath();g.strokeStyle='rgba(255,255,255,.8)';g.setLineDash([4,3]);g.moveTo(xp(ue[0]),yp(z));g.lineTo(xp(ue.at(-1)),yp(z));g.stroke();}g.setLineDash([]);if(Math.abs(p.fixed_mm)<=5){const half=Math.sqrt(25-p.fixed_mm*p.fixed_mm);g.strokeStyle='#ffdd8c';g.lineWidth=2;g.strokeRect(xp(-half),yp(15),xp(half)-xp(-half),yp(20)-yp(15));}}else if(p.fixed_mm>=15&&p.fixed_mm<=20){g.beginPath();g.strokeStyle='#ffdd8c';g.lineWidth=2;g.ellipse(xp(0),yp(0),5/(umax-umin)*width,5/(vmax-vmin)*height,0,0,Math.PI*2);g.stroke();}
const ax0=p.kind==='YZ'?1:0,ax1=p.kind==='XY'?1:2,stepU=Math.max(1,Math.round(nu/15)),stepV=Math.max(1,Math.round(nv/14)),length=Math.min(width/15,height/14)*.74,arrows=[];
for(let j=Math.floor(stepV/2);j<nv;j+=stepV)for(let i=Math.floor(stepU/2);i<nu;i+=stepU){const k=j*nu+i;if(p.native_indices[k]<0||p.u_mm[i]<umin||p.u_mm[i]>umax||p.v_mm[j]<vmin||p.v_mm[j]>vmax)continue;const a=V.E[k*3+ax0],b=V.E[k*3+ax1],q=Math.hypot(a,b);if(!(q>Math.max(max*1e-10,1e-14)))continue;let dx=a/(umax-umin)*width,dy=(p.kind==='XY'?-b:b)/(vmax-vmin)*height,l=Math.hypot(dx,dy);dx=dx/l*length;dy=dy/l*length;if($('shape-arrows').value==='magnitude'){const m=view.cMax>0?Math.min(1,q/view.cMax):0;dx*=m;dy*=m;}const x=xp(p.u_mm[i]),y=yp(p.v_mm[j]),x0=x-dx*.5,y0=y-dy*.5,x1=x+dx*.5,y1=y+dy*.5,ang=Math.atan2(dy,dx),head=Math.max(2.2,Math.min(4,length*.21));const draw=()=>{g.beginPath();g.moveTo(x0,y0);g.lineTo(x1,y1);g.moveTo(x1-head*Math.cos(ang-.55),y1-head*Math.sin(ang-.55));g.lineTo(x1,y1);g.lineTo(x1-head*Math.cos(ang+.55),y1-head*Math.sin(ang+.55));g.stroke();};g.lineWidth=2.8;g.strokeStyle='rgba(255,255,255,.88)';draw();g.lineWidth=1;g.strokeStyle='#102c40';draw();arrows.push(k);}
g.restore();g.strokeStyle='#527488';g.lineWidth=1;g.strokeRect(pad.l,pad.t,width,height);g.font='10px system-ui';g.fillStyle='#32556a';g.textAlign='center';for(const v of[umin,(umin+umax)/2,umax])g.fillText(nice(v),xp(v),h-24);g.fillText(p.u_label,w/2,h-7);g.textAlign='right';for(const v of[vmin,(vmin+vmax)/2,vmax])g.fillText(nice(v),pad.l-6,yp(v)+3);g.save();g.translate(12,h/2);g.rotate(-Math.PI/2);g.textAlign='center';g.fillText(p.v_label,0,0);g.restore();if(p.kind!=='XY'){g.textAlign='left';g.fillText('z=0 표면 / 깊이 +z ↓',pad.l+5,pad.t+13);}cache.transform[c]={xp,yp,umin,umax,vmin,vmax,pad,width,height,arrows,down};window.task1ManualRanges.note(el.id,{low,high,total,viewportHidden:hidden});return arrows.length;}'''


def patch_vectors(script):
    if hashlib.sha256(script.encode()).hexdigest()!=VECTOR_SCRIPT_SHA256:
        raise ValueError('Reviewed vector scientific GUI script changed')
    script=replace_function(script,'color',VECTOR_COLOR)
    script=replace_function(script,'plot',PLOT)
    script=once(script,"if(u<tr.umin||u>tr.umax||v<tr.vmin||v>tr.vmax)return;",
        "if(u<tr.umin||u>tr.umax||v<tr.vmin||v>tr.vmax)return;const actualU=p.u_edges_mm,actualV=p.v_edges_mm;if(u<actualU[0]||u>actualU.at(-1)||v<actualV[0]||v>actualV.at(-1)){$('shape-hover').textContent='팬텀 native 격자 밖 · 수동 표시 좌표';return;}")
    script=once(script,"$('shape-range').textContent='공통 색 범위 0–'+nice(max)+' V/m · 전체 지원 조건 고정 상한 / 시간·단면·구동 변경에도 동일';", "$('shape-range').textContent='각 순간 전기장 그래프 아래에서 표시 좌표와 색상 범위를 직접 조절합니다. 범위 밖 값은 빗금·개수로 표시하고 원값은 유지합니다.';")
    return script
