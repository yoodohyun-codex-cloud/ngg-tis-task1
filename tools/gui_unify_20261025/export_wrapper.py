#!/usr/bin/env python3
"""Use the hierarchy-preserving exporter through the same locked finite owner.
GUI sources and original build provenance remain unchanged. The new helper and
this wrapper are published with full byte readback before export execution.
"""
import sys,runpy
sys.dont_write_bytecode=True
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
import unified_export
sys.modules['human_export']=unified_export
if __name__=='__main__':
    runpy.run_path(str(__import__('pathlib').Path(__file__).with_name('unify_run.py')),run_name='__main__')
