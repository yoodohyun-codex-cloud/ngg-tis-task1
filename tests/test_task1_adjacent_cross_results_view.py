"""Synthetic adjacent-cross JSON view contracts; no native reads or jobs."""
from __future__ import annotations

import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BASELINE='baseline-square15-xy80'
RUN='cloud-adjacent-cross-20261021T164000Z'
IDS=('adjacent-square15-xy80','crossalloc-source225-return225-xy80','balancedcross225-adjacent-sources-xy80')
RUNS=('cloud-mesh-c1-20261019T190000Z','cloud-finite-loop-20261020T002600Z-fine',
      'cloud-cross-allocation-20261021T150000Z',RUN)
PRIMARY='primary_r5_depth15_20'
GATES=[dict(name='primary_maxTIS_'+stat,unit='V/m',required_direction='greater')for stat in ('mean','p10')]
for _region in ('surface_0_5','primary_complement'):
    GATES.append(dict(name=_region+'_maxTIS_p95',unit='V/m',required_direction='less'))
    GATES.extend(dict(name=_region+'_high_volume_at_'+PRIMARY+'_'+stat,unit='m3',required_direction='less')for stat in ('mean','p10'))


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Selects(HTMLParser):
    def __init__(self):super().__init__();self.ids=set()
    def handle_starttag(self,tag,attrs):
        if tag=='select':self.ids.add(dict(attrs).get('id'))


class AdjacentCrossViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(ROOT/'tools'))
        for name,path in (('fixture',ROOT/'tests/test_task1_volume_audit_view.py'),
                          ('view',ROOT/'tools/task1_adjacent_cross_results_view.py')):
            spec=importlib.util.spec_from_file_location('adjacent_cross_'+name,path)
            module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
            setattr(cls,name,module)
        cls.fixture.VolumeAuditViewTests.setUpClass()

    def setUp(self):
        self.base=self.fixture.VolumeAuditViewTests('runTest');self.base.setUp();self.addCleanup(self.base.doCleanups)
        self.root=self.base.directory;self.audit_path=self.base.path;self.report=self.base.report
        self.previous=self.root/'previous44.html';self.previous.write_text('<html>Historical44</html>')
        self.previous_receipt=self.previous.with_suffix('.receipt.json')
        self.previous_receipt.write_text(json.dumps(dict(schema='task1-volume-two-report-merge-receipt-v1',
            status='rendered_precomputed_JSON_only',case_count=44,output=dict(SHA256=digest(self.previous),bytes=self.previous.stat().st_size))))
        self.maps=self.root/'common-maps.html';self.maps.write_text('<html>Historical maps only</html>')
        self.screen_path=self.root/'screen.json';self.marker_paths=[]
        rows=[]
        for index,(identifier,pads) in enumerate(zip((BASELINE,*IDS),(4,4,4,4))):
            row=self.base.case('baseline'if index==0 else'candidate',pads)
            run=RUNS[index]
            summary=self.root/run/'postprocess'/identifier/'summary.json';summary.parent.mkdir(parents=True)
            summary.write_text(json.dumps(dict(id=identifier,status='complete')))
            self.report['inputs_sha256'][str(summary)]=digest(summary)
            row.update(case_id=identifier,condition_id=identifier+'-square_3h',run_id=run,
                summary_path=str(summary),design_id='baseline-square15'if index==0 else identifier.rsplit('-xy80',1)[0])
            row['mesh']['h_xy_mm']=.625;row['mesh']['cells']=351680
            if index==0:baseline_path=str(summary)
            row['baseline_summary']=baseline_path
            marker=self.root/run/'bases'/identifier/'BASIS_COMPLETE';marker.parent.mkdir(parents=True);marker.write_bytes(b'')
            self.marker_paths.append(marker);self.report['inputs_sha256'][str(marker)]=digest(marker)
            rows.append(row)
        self.report['cases']=rows
        self.screen=dict(schema='task1-candidate-screen-v1',status='screen_complete_not_adopted',
            input_volume_report=dict(path=str(self.audit_path),SHA256=''),normalization='skin_contact_only',
            baseline_case_id=BASELINE,baseline_native_receipt={},fixed_baseline_cutoffs_V_m=copy.deepcopy(rows[0]['fixed_same_grid_baseline_cutoffs_V_m']),
            candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,
            source_hash_scope='JSON/configuration/frozen implementation only; native fields/potentials/NPZ not read or independently reproduced',
            holds=['Numerical screens only; unloaded probes, no experimental/convergence/adoption claim'],cases=[])
        for row in rows[-1:]:
            checks=[dict(definition,baseline=4.,candidate=3.,passed=i<2,
                relative_change_percent=-25.,arithmetic_tolerance=1e-10)for i,definition in enumerate(GATES)]
            self.screen['cases'].append(dict(case_id=row['case_id'],run_id=row['run_id'],checks=checks,
                all_screen_checks_passed=False,failed_checks=[c['name']for c in checks if not c['passed']],
                decision='Reject candidate nomination under unchanged eight-gate screen',candidate_adopted=False,
                native_source_receipt={},all_five_normalizations=copy.deepcopy(row['normalizations']),
                circuit=copy.deepcopy(row['circuit']),mesh=copy.deepcopy(row['mesh']),
                physical_model_version=row['physical_model_version'],raw_probe_artifact_reference=copy.deepcopy(row['raw_probe_artifact_reference'])))
        self.write_audit()

    def write_audit(self):
        self.audit_path.write_text(json.dumps(self.report,ensure_ascii=False))
        self.screen['input_volume_report']['SHA256']=digest(self.audit_path);self.write_screen()

    def write_screen(self):self.screen_path.write_text(json.dumps(self.screen,ensure_ascii=False))

    def model(self):return self.view.load_model(self.audit_path,self.screen_path,self.previous)

    def test_exact_four_factorial_cases_preserve_values_and_original_square_baseline(self):
        model=self.model()
        self.assertEqual([r['case_id']for r in model['cases']],[BASELINE,*IDS])
        self.assertEqual([r['circuit']['n_pads']for r in model['cases']],[4,4,4,4])
        self.assertEqual(len(model['cohorts']),1)
        self.assertEqual(model['cohorts'][0]['baseline_id'],model['cases'][0]['viewer_id'])
        for actual,expected in zip(model['cases'],self.report['cases']):
            self.assertEqual(actual['normalizations'],expected['normalizations'])
            self.assertTrue(actual['baseline_present']);self.assertEqual(actual['circuit']['n_outputs'],2)

    def test_exact_case_pool_and_no_duplicate_or_missing_case(self):
        original=copy.deepcopy(self.report)
        for variant in ('missing','extra','duplicate','coarse_id'):
            self.report=copy.deepcopy(original)
            if variant=='missing':self.report['cases'].pop()
            elif variant=='extra':self.report['cases'].append(copy.deepcopy(self.report['cases'][-1]))
            elif variant=='duplicate':self.report['cases'][2]['case_id']=self.report['cases'][1]['case_id']
            else:self.report['cases'][2]['case_id']='balancedcross225-adjacent-sources-xy40'
            self.write_audit()
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_fine_same_grid_circuit_and_run_metadata_required(self):
        original=copy.deepcopy(self.report)
        variants=(('h_xy_mm',1.25),('sc_cells',4),('bulk_layer_counts',[14,14,41]))
        for key,value in variants:
            self.report=copy.deepcopy(original);self.report['cases'][1]['mesh'][key]=value;self.write_audit()
            with self.subTest(key=key),self.assertRaises((ValueError,RuntimeError)):self.model()
        for variant in ('run','signature','outputs','pads','baseline'):
            self.report=copy.deepcopy(original);row=self.report['cases'][1]
            if variant=='run':row['run_id']='coarse-run'
            elif variant=='signature':row['comparison_signature']='another-cohort'
            elif variant=='outputs':row['circuit']['n_outputs']=4
            elif variant=='pads':row['circuit']['n_pads']=8
            else:row['baseline_summary']=row['summary_path']
            self.write_audit()
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_screen_is_bound_to_exact_current_audit_bytes_and_path(self):
        original=copy.deepcopy(self.screen)
        for key,value in (('SHA256','0'*64),('path',str(self.root/'other-audit.json'))):
            self.screen=copy.deepcopy(original);self.screen['input_volume_report'][key]=value;self.write_screen()
            with self.subTest(key=key),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_changed_small_source_is_rejected_but_native_files_never_opened(self):
        original=Path.open
        def guard(path,*args,**kwargs):
            if Path(path).suffix in ('.npz','.bin','.gz'):raise AssertionError('Viewer opened native data')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guard):self.model()
        Path(self.report['cases'][1]['summary_path']).write_text('{"tampered":true}')
        with self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_nonempty_or_unregistered_completion_marker_is_rejected(self):
        marker=self.marker_paths[1];marker.write_bytes(b'nonempty')
        self.report['inputs_sha256'][str(marker)]=digest(marker);self.write_audit()
        with self.assertRaises((ValueError,RuntimeError)):self.model()
        marker.write_bytes(b'');self.report['inputs_sha256'][str(marker)]=digest(marker)
        unsupported=marker.with_name('OTHER_COMPLETE');unsupported.write_bytes(b'')
        self.report['inputs_sha256'][str(unsupported)]=digest(unsupported);self.write_audit()
        with self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_stored_screen_must_have_frozen_eight_definitions_and_consistent_flags(self):
        original=copy.deepcopy(self.screen)
        for variant in ('count','name','unit','direction','flag','allpassed','failedlist','adopted'):
            self.screen=copy.deepcopy(original);row=self.screen['cases'][0]
            if variant=='count':row['checks'].pop()
            elif variant=='name':row['checks'][0]['name']='invented'
            elif variant=='unit':row['checks'][0]['unit']='V/cm'
            elif variant=='direction':row['checks'][0]['required_direction']='less'
            elif variant=='flag':row['checks'][0]['passed']=1
            elif variant=='allpassed':row['all_screen_checks_passed']=True
            elif variant=='failedlist':row['failed_checks']=[]
            else:row['candidate_adopted']=True
            self.write_screen()
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_terminal_unadopted_screen_is_only_for_the_new_adjacent_cross(self):
        original=copy.deepcopy(self.screen)
        for variant in ('schema','running','adopted','converged','experiment','missing','duplicate','run','baseline','historical_case'):
            self.screen=copy.deepcopy(original)
            if variant=='schema':self.screen['schema']='other'
            elif variant=='running':self.screen['status']='running'
            elif variant=='adopted':self.screen['candidate_adopted']=True
            elif variant=='converged':self.screen['full_convergence_validated']=True
            elif variant=='experiment':self.screen['experimentally_validated']=True
            elif variant=='missing':self.screen['cases'].pop()
            elif variant=='duplicate':self.screen['cases'].append(copy.deepcopy(self.screen['cases'][0]))
            elif variant=='run':self.screen['cases'][0]['run_id']='coarse-run'
            elif variant=='historical_case':self.screen['cases'][0]['case_id']=IDS[0]
            else:self.screen['baseline_case_id']=IDS[-1]
            self.write_screen()
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_screen_cannot_substitute_normalizations_circuit_mesh_or_probe_receipts(self):
        original=copy.deepcopy(self.screen)
        for variant in ('normalizations','circuit','mesh','probe'):
            self.screen=copy.deepcopy(original);row=self.screen['cases'][0]
            if variant=='normalizations':row['all_five_normalizations']['raw_1Vpp']['source_Vpp_per_output']=99.
            elif variant=='circuit':row['circuit']['n_outputs']=4
            elif variant=='mesh':row['mesh']['h_xy_mm']=1.25
            else:row['raw_probe_artifact_reference']['SHA256']='0'*64
            self.write_screen()
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_previous_44_case_snapshot_requires_success_receipt_and_exact_html(self):
        original=self.previous_receipt.read_bytes()
        receipt=json.loads(original)
        for key,value in (('schema','other'),('status','failed'),('case_count',43)):
            mutated=copy.deepcopy(receipt);mutated[key]=value;self.previous_receipt.write_text(json.dumps(mutated))
            with self.subTest(key=key),self.assertRaises((ValueError,RuntimeError)):self.model()
        self.previous_receipt.write_bytes(original);self.previous.write_text('<html>Changed historical screen</html>')
        with self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_only_new_cross_receives_current_screen_and_old_maps_keep_historical_scope(self):
        model=self.model();screen=model['adjacent_cross_screen']
        self.assertEqual([row['case_id']for row in screen['cases']],[IDS[-1]])
        self.assertEqual(screen['cases'][0]['checks'],self.screen['cases'][0]['checks'])
        document=self.view.render_html(model,self.root/'new.html',self.maps,self.previous)
        self.assertIn('The other three comparison rows do not receive new screen verdicts here.',document)
        self.assertIn('Historical fine grouped-pad maps',document)
        self.assertIn('not physical maps of the current cross-adjacent result',document)
        self.assertIn('original V/m scales',document)

    def test_safe_offline_html_keeps_controls_screen_and_historical_links(self):
        model=self.model();before=copy.deepcopy(model)
        document=self.view.render_html(model,self.root/'new.html',self.maps,self.previous)
        self.assertEqual(model,before)
        parser=Selects();parser.feed(document)
        self.assertTrue({'cohort-select','roi-select','metric-select','normalization-select','cutoff-select'}<=parser.ids)
        self.assertIn(self.previous.name,document);self.assertIn(self.maps.name,document)
        self.assertIn('unloaded',document.lower());self.assertIn('V/m',document)
        for definition in GATES:self.assertIn(definition['name'],document)
        self.assertNotIn('<script src=',document);self.assertNotIn('fetch(',document)

    def test_script_terminator_and_unicode_are_safe_without_statistic_changes(self):
        literal='</script><script>not executable</script> 한글 Ω'
        self.report['scope']['limits']+=' '+literal;self.write_audit();model=self.model()
        document=self.view.render_html(model,self.root/'new.html',self.maps,self.previous)
        raw=re.search(r'<script\b[^>]*type="application/json"[^>]*>(.*?)</script\s*>',document,re.DOTALL).group(1)
        self.assertIn(literal,json.dumps(json.loads(raw),ensure_ascii=False));self.assertNotIn('</script>',raw.lower())


if __name__=='__main__':unittest.main()
