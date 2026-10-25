#!/usr/bin/env python3
"""Display-metadata recovery; preserves the first failed exporter and output.

The frozen first builder remains unchanged. The only display change adds each
registered physical pad area to its unchanged polygon, checked against the
native contact-area sum. No field, coefficient, normalization or rank changes.
"""
from __future__ import annotations
import copy
from pathlib import Path
import subprocess
import math
import task1_top5_build as frozen

ROOT=frozen.ROOT
_export=frozen.export_case
_implementation=frozen.implementation


def with_outline_areas(result,row):
    result=copy.deepcopy(result)
    expected=row['case']['expected_pad_areas_m2']
    represented={p['pad']:p['area_mm2']for p in result['pad_centres']}
    for outline in result.get('physical_outlines',[]):
        pad=outline['pad'];area=float(expected[pad])*1e6
        frozen.require(math.isfinite(area)and area>0 and math.isclose(area,represented[pad],rel_tol=1e-10,abs_tol=1e-9),'Registered physical outline area differs from native contact patches')
        outline['area_mm2']=area
    return result


def export_case(row,*args,**kwargs):
    return with_outline_areas(_export(row,*args,**kwargs),row)


def implementation():
    receipt=_implementation();refs=dict(receipt['implementation_sha256']);commit=receipt['source_commit']
    for name in ('tools/task1_top5_build_recovery.py','tests/test_task1_top5_build_recovery.py'):
        p=ROOT/name
        frozen.require(p.read_bytes()==subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT),'Commit the display-only recovery before execution')
        refs[str(p)]=frozen.sha(p)
    return dict(source_commit=commit,implementation_sha256=refs)


def main():
    frozen.export_case=export_case
    frozen.implementation=implementation
    frozen.main()


if __name__=='__main__':main()
