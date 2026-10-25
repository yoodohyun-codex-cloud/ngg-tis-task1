"""Pure final color-transform synchronization for three fixed-range GUI layers."""
from fixed_legacy import once

def function(script,name,edit):
    a=script.index('function '+name+'(');b=script.find('\nfunction ',a+1)
    if b<0:raise ValueError('Following function anchor required')
    return script[:a]+edit(script[a:b])+script[b:]

def original(script):
    script=once(script,'function color(v,max){','function color(v,max,field=true){')
    script=once(script,'let t=Math.max(0,Math.min(1,v/max))*5,','let t=(field?window.task1FixedScales.colorFraction(v,max):Math.max(0,Math.min(1,v/max)))*5,')
    script=once(script,'function pixels(f,v,max,scale){','function pixels(f,v,max,scale,field=true){')
    script=once(script,'c.fillStyle=color(v[j*(xe.length-1)+i]*scale,max);','c.fillStyle=color(v[j*(xe.length-1)+i]*scale,max,field);')
    script=function(script,'field',lambda x:once(x,"canvas.dataset.vmin='0';","canvas.dataset.colorTransform=window.task1FixedScales.transform();canvas.dataset.vmin='0';"))
    def contact(block):
        block=once(block,'pixels(f,v,max,scale);','pixels(f,v,max,scale,false);')
        return once(block,"canvas.dataset.vmin='0';","canvas.dataset.colorTransform='linear';canvas.dataset.vmin='0';")
    script=function(script,'contact',contact)
    # These pure color functions are retained for actual browser pixel checks.
    script=once(script,'window.task1Best1Pair=Object.freeze({render:update,payload});','window.task1Best1Pair=Object.freeze({render:update,payload,fixedColorForTest:v=>color(v,TASK1_LOCKED_E,true)});')
    return script

def vectors(script):
    script=once(script,'const z=Math.min(1,Math.max(0,max>0?v/max:0))*(COLORS.length-1)','const z=window.task1FixedScales.colorFraction(v,max)*(COLORS.length-1)')
    script=once(script,"el.dataset.vmin='0';","el.dataset.colorTransform=window.task1FixedScales.transform();el.dataset.vmin='0';")
    script=once(script,'x.textContent=nice(v*max);','x.textContent=nice(window.task1FixedScales.colorValueAtFraction(v,max));')
    script=once(script,'instantForTest:instant,validateForTest','instantForTest:instant,fixedColorForTest:v=>color(v,TASK1_LOCKED_E),validateForTest')
    return script

def paper(script):
    script=once(script,"const q=max>0?($('paper-color').value==='log'?Math.log1p(v)/Math.log1p(max):v/max):0,",'const q=window.task1FixedScales.colorFraction(v,max),')
    script=once(script,"el.dataset.vmin='0';el.dataset.vmax=String(max);","el.dataset.colorTransform=window.task1FixedScales.transform();el.dataset.vmin='0';el.dataset.vmax=String(max);")
    script=once(script,'mathForTest:Object.freeze({vectorRMS,projection,fixedAM,toneReal,envelope})','fixedColorForTest:v=>color(v,TASK1_LOCKED_E),mathForTest:Object.freeze({vectorRMS,projection,fixedAM,toneReal,envelope})')
    return script
