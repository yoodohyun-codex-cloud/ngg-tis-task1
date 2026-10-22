"""Synthetic distinct-layout catalog contracts; never run the real collector."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('top5_catalog_tested',ROOT/'tools/task1_top5_catalog.py')
tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tool;spec.loader.exec_module(tool)


def modes():
    caps={k:(.01 if 'voltage'in k else .001 if 'power'in k else 10.)for k in tool.screen.CAP_DEGREES};caps['source_power_W']=.1
    result={}
    for name in tool.screen.MODES:
        regions={}
        for r in tool.REGIONS:
            vol=4e-7 if r==tool.screen.PRIMARY else 5e-5
            stats=dict(min=0.,max=100.,mean=4.,p10=3.5,p95=25.,std=1.,CV=.25,volume_m3=vol,positive_weight_cells=50,
                fixed_baseline_threshold_volume={tool.screen.PRIMARY+'_mean':dict(cutoff_V_m=4.,volume_m3=1e-7),
                    tool.screen.PRIMARY+'_p10':dict(cutoff_V_m=3.5,volume_m3=2e-7)})
            regions[r]={m:copy.deepcopy(stats)for m in tool.METRICS}
        result[name]=dict(amplitude_scale=1.,regions=regions,normalized_burdens=caps.copy(),baseline_derived_numerical_limits=caps.copy(),
            source_output_RMS_by_output_mA=[1.,1.],sum_source_output_RMS_mA=2.,includes_source_power_cap=False,includes_1Vpp_ceiling=False)
    return result


def physical_case(mask='a'*64,offset=0.,node0='out0'):
    pads=[]
    for i,(x,y)in enumerate(((-10,-10),(10,10),(10,-10),(-10,10))):
        x+=offset;pads.append(dict(pad=i,polygon_mm=[[x-2,y-2],[x+2,y-2],[x+2,y+2],[x-2,y+2]]))
    return dict(mask_sha256=mask,design=dict(pads=pads),circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,
        return_topology='all_return_pads_ideal_common_GND',pad_to_node={'0':node0,'1':'out1','2':'GND','3':'GND'}))


def row(ident,geometry='base',degradation=0.):
    n=modes();n['skin_contact_only']['regions'][tool.screen.PRIMARY]['maxTIS']['mean']*=1-degradation
    n['skin_contact_only']['regions'][tool.screen.PRIMARY]['maxTIS']['p10']*=1-degradation
    return dict(id=ident,condition_id=ident,source_case_id='case-'+geometry,source_run_id='native-run',source_commit='commit',
        configuration_sha256='config-'+geometry,geometry_key=geometry,waveform='square_3h',normalizations=n,
        scales={k:v['amplitude_scale']for k,v in n.items()},condition_source=None,native_summary=dict(path='/synthetic/'+geometry+'/summary.json',SHA256='s'),source_refs={})


def native_fixture(root):
    """Only tiny JSON/properties exist; all declared native arrays are absent."""
    run=root/'data-native/synthetic';folder=run/'postprocess/square';folder.mkdir(parents=True);(run/'cases').mkdir()
    config=run/'square.properties';config.write_text('mask.path=absent-mask.csv\nmask.sha256='+('a'*64)+'\nsc.sigma=0.01\nz.3000=1,0\n')
    config_sha=hashlib.sha256(config.read_bytes()).hexdigest();case=physical_case()
    case.update(id='square',config_file=str(config),config_sha256=config_sha,source_coating_nm=10,source_Rs_fit_window_Hz=500)
    case['circuit'].update(source_resistance_ohm=50,source_peak_V=.5,source_Vpp_each=1)
    mesh=dict(h_xy_mm=.625,sc_cells=2,bulk_layer_counts=[14,14,40],cells=351680,config_sha256=config_sha)
    meshpath=folder/'mesh-metadata.json';meshpath.write_text(json.dumps(mesh));meshsha=hashlib.sha256(meshpath.read_bytes()).hexdigest()
    validation={k:0. for k in tool.screen.NATIVE_GATES}
    summary=dict(id='square',status='complete',mesh_metadata=mesh,source_inputs_unchanged=True,validation=validation,
        validation_gate_status={k:dict(status='passed',value=0.,limit=v)for k,v in tool.screen.NATIVE_GATES.items()},
        input_sha256={str(meshpath):meshsha,str(folder/'grid.csv.gz'):'b'*64},conditions=[])
    path=folder/'summary.json';path.write_text(json.dumps(summary));sha=hashlib.sha256(path.read_bytes()).hexdigest()
    (run/'preregistration.json').write_text(json.dumps(dict(source_commit='synthetic-source-commit',gates=tool.screen.NATIVE_GATES,cases=[case])))
    (run/'cases/square.json').write_text(json.dumps(dict(id='square',status='complete',postprocess_sha256=sha,config_sha256=config_sha,validation=validation)))
    return path,config


class Top5CatalogTests(unittest.TestCase):
    def test_metadata_store_rejects_native_arrays_masks_grids_and_symlinks(self):
        with tempfile.TemporaryDirectory()as d:
            r=Path(d);store=tool.MetadataStore(r)
            for name in('volume.npz','grid.csv','grid.csv.gz','field-3000.bin.gz','mask.csv'):
                p=r/name;p.write_text('{}')
                with self.subTest(name=name),self.assertRaises(ValueError):store.load(p)
            p=r/'safe.json';p.write_text('{"ok":true}');alias=r/'alias.json';alias.symlink_to(p)
            self.assertEqual(store.load(p),{'ok':True})
            with self.assertRaises(ValueError):store.load(alias)
            with self.assertRaises(ValueError):store.load(p,'wrong-sha')

    def test_metadata_size_budget_is_enforced_before_read(self):
        with tempfile.TemporaryDirectory()as d:
            r=Path(d);p=r/'too-large.json';p.write_text('{"large":"'+('a'*100)+'"}')
            with patch.object(tool,'MAX_FILE_BYTES',32),self.assertRaises(ValueError):tool.MetadataStore(r).load(p)

    def test_native_metadata_sha_and_derived_commit_guard_without_existing_arrays(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);path,config=native_fixture(root);builder=tool.CatalogBuilder(root);native=builder.native(path)
            self.assertEqual(native['source_commit'],'synthetic-source-commit');self.assertEqual(native['configuration_sha256'],hashlib.sha256(config.read_bytes()).hexdigest())
            self.assertFalse(Path(native['grid']['path']).exists());self.assertTrue(all(Path(p).suffix in('.json','.properties')for p in builder.store.cache))
            condition=dict(status='calculated_unadopted',source_run_id=native['source_run_id'],source_case_id=native['source_case_id'],
                configuration_sha256=native['configuration_sha256'],source_commit='wrong-source',candidate_adopted=False)
            with self.assertRaisesRegex(ValueError,'source/config/commit'):builder.normalize(native,modes(),'new','sine',path,condition=condition)
            config.write_text(config.read_text()+'sc.epsilon_r=10\n')
            with self.assertRaisesRegex(ValueError,'SHA mismatch'):tool.CatalogBuilder(root).native(path)

    def test_geometry_aliases_vertex_order_path_mask_encoding_but_keeps_actual_node_roles(self):
        a=physical_case();b=copy.deepcopy(a);b['mask_sha256']='b'*64
        for pad in b['design']['pads']:pad['polygon_mm']=list(reversed(pad['polygon_mm'][1:]+pad['polygon_mm'][:1]))
        key,proof=tool.geometry_identity(a);self.assertEqual(key,tool.geometry_identity(b)[0])
        self.assertEqual(proof['method'],'physical_polygons_and_node_assignment')
        self.assertNotEqual(key,tool.geometry_identity(physical_case(offset=.625))[0])
        self.assertNotEqual(key,tool.geometry_identity(physical_case(node0='GND'))[0])
        self.assertEqual(a['mask_sha256'],'a'*64)

    def test_missing_polygon_fallback_is_explicit_and_mask_sensitive(self):
        a=physical_case();a['design'].pop('pads');b=copy.deepcopy(a);b['mask_sha256']='different'
        self.assertNotEqual(tool.geometry_identity(a)[0],tool.geometry_identity(b)[0])
        self.assertIn('fallback',tool.geometry_identity(a)[1]['method'])

    def test_all5_full6ROI_statistics_original_cutoffs_and8burdens_required(self):
        base=modes();candidate=copy.deepcopy(base);before=copy.deepcopy(candidate)
        self.assertTrue(all(r['passed']for r in tool.validate_modes(candidate,base).values()));self.assertEqual(candidate,before)
        for change in('mode','region','std','cutoff','cap','volume','cellcount'):
            bad=copy.deepcopy(base);skin=bad['skin_contact_only']
            if change=='mode':bad.pop('equal_total_power')
            elif change=='region':skin['regions'].pop('primary_complement')
            elif change=='std':skin['regions'][tool.screen.PRIMARY]['maxTIS'].pop('std')
            elif change=='cutoff':skin['regions'][tool.screen.PRIMARY]['maxTIS']['fixed_baseline_threshold_volume'][tool.screen.PRIMARY+'_mean']['cutoff_V_m']=4.01
            elif change=='cap':skin['normalized_burdens']['surface_J_RMS_p95_A_m2']*=1.00001
            elif change=='volume':skin['regions'][tool.screen.PRIMARY]['RMS']['volume_m3']*=1.01
            else:skin['regions'][tool.screen.PRIMARY]['RMS']['positive_weight_cells']=0
            with self.subTest(change=change),self.assertRaises((ValueError,KeyError)):tool.validate_modes(bad,base)

    def test_skin8_caps_do_not_add_sourcepower_or1Vpp_ceiling(self):
        base=modes();candidate=copy.deepcopy(base);candidate['skin_contact_only']['normalized_burdens']['source_power_W']*=100
        candidate['skin_contact_only']['source_Vpp_upper_by_output_V']=[3.,4.]
        self.assertTrue(all(c['passed']for c in tool.validate_modes(candidate,base).values()))
        candidate['skin_contact_only']['includes_source_power_cap']=True
        with self.assertRaises(ValueError):tool.validate_modes(candidate,base)

    def test_eight_violation_ranking_uses_target_absolute_values_not_ratio_or_passcount(self):
        base=modes();a=copy.deepcopy(base);b=copy.deepcopy(base)
        a['skin_contact_only']['regions'][tool.screen.PRIMARY]['maxTIS']['mean']*=.98
        b['skin_contact_only']['regions']['primary_complement']['maxTIS']['p95']*=1.03
        ac,ascore=tool.spatial_checks(a,base);bc,bscore=tool.spatial_checks(b,base)
        self.assertEqual(len(ac),8);self.assertLess(ascore,bscore)
        self.assertAlmostEqual(ascore[0],.02,places=8);self.assertAlmostEqual(bscore[0],.03,places=8)
        a['skin_contact_only']['regions'][tool.screen.PRIMARY]['maxTIS']['p10']=0.
        self.assertGreater(tool.spatial_checks(a,base)[1][0],.99)

    def test_top5_are_distinct_nonbaseline_layouts_one_best_drive_per_layout(self):
        builder=tool.CatalogBuilder();builder.baseline=row('baseline');builder.add(copy.deepcopy(builder.baseline),'/synthetic/base.json')
        builder.baseline=next(iter(builder.rows.values()))
        builder.add(row('baseline-new-perfect-drive','base'),'/synthetic/base-new.json')
        for i in range(1,7):builder.add(row('design-'+str(i),'g'+str(i),i*.01),'/synthetic/'+str(i)+'.json')
        builder.add(row('drive-best-layout1','g1',.005),'/synthetic/drive.json')
        result=builder.finish();self.assertEqual(len(result['selected_layouts']),5)
        self.assertEqual(len({r['geometry_key']for r in result['selected_layouts']}),5)
        self.assertTrue(all(r['geometry_key']!='base'for r in result['selected_layouts']))
        self.assertEqual(result['selected_layouts'][0]['id'],'drive-best-layout1')
        self.assertEqual(result['selected_layouts'][0]['layout_competitor_count'],2)
        self.assertIn('normalizations',result['canonical_baseline']);self.assertNotIn('normalizations',result['all_competitor_rows'][0])

    def test_replayed_same_condition_config_waveform_is_alias_not_new_competitor(self):
        builder=tool.CatalogBuilder();builder.baseline=row('baseline');a=row('same','g1',.01);before=copy.deepcopy(a)
        builder.add(a,'/first.json');builder.add(copy.deepcopy(before),'/second.json')
        self.assertEqual(len(builder.rows),1);self.assertEqual(len(builder.aliases),1)
        self.assertIn('no_new_computation',builder.aliases[0]['reason'])

    def test_conflicting_duplicate_values_are_quarantined_not_best_picked(self):
        builder=tool.CatalogBuilder();builder.baseline=row('baseline');a=row('same','g1',.01);builder.add(a,'/first.json')
        b=row('same','g1',.02)
        with self.assertRaises(ValueError):builder.add(b,'/conflicting.json')
        self.assertEqual(len(builder.rows),0);self.assertEqual(len(builder.conflicted_keys),1)
        with self.assertRaises(ValueError):builder.add(row('same','g1',.01),'/third.json')

    def test_duplicate_with_same8gates_but_different_carrierRMS_is_quarantined(self):
        builder=tool.CatalogBuilder();builder.baseline=row('baseline');a=row('same','g1',.01);builder.add(a,'/first.json')
        b=row('same','g1',.01);b['normalizations']['raw_1Vpp']['regions']['total']['RMS']['mean']*=1.01
        self.assertEqual(tool.screen.gate_values(a),tool.screen.gate_values(b))
        with self.assertRaises(ValueError):builder.add(b,'/conflicting-carrier.json')
        self.assertEqual(builder.rows,{})

    def test_metadata_preservation_recheck_and_actual_harmonics(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);p=root/'metadata.json';p.write_text('{"value":1}');store=tool.MetadataStore(root);store.load(p);store.verify_unchanged()
            p.write_text('{"value":2}')
            with self.assertRaisesRegex(ValueError,'changed during collection'):store.verify_unchanged()
        condition=dict(actual_fundamental_Hz=[3000,3030],metrics=dict(source_current_spectrum=[
            dict(frequency_Hz=f,real_A=[1.,0.],imaginary_A=[0.,0.])for f in(3000,3030,9000,9090)]))
        self.assertEqual(tool.native_active_frequencies(condition),[3000,3030,9000,9090]);self.assertEqual(condition['actual_fundamental_Hz'],[3000,3030])

    def test_discovery_includes_nested_return_current_brief_and_v8_receipt_volume_proofs(self):
        with tempfile.TemporaryDirectory()as d:
            r=Path(d);(r/'docs/cloud-return-current-context').mkdir(parents=True);nested=r/'docs/cloud-return-current-context/result-brief.json';nested.write_text('{}')
            (r/'docs/cloud-family').mkdir();good=r/'docs/cloud-family/volume.json';good.write_text('{}')
            (r/'docs/legacy').mkdir();legacy=r/'docs/legacy/volume-old.json';legacy.write_text('{}')
            receipt=r/tool.V8_RECEIPT;receipt.write_text(json.dumps(dict(historical_snapshot=dict(historical_input_artifact_proofs=[dict(path=str(legacy),SHA256=hashlib.sha256(legacy.read_bytes()).hexdigest())]),current_audits=[])))
            for n in('native-volume-metrics.json','checkpoint-volume.json','volume-plan.json','volume.attempt.json'):(r/'docs/cloud-family'/n).write_text('{}')
            paths,proofs=tool.discover(tool.MetadataStore(r));self.assertEqual(set(paths),{good,nested,legacy});self.assertIn(str(legacy),proofs)

    def test_conditions_conditionJSON_schema_rehydrates_full_actual_source_not_snapshot(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);source=root/'condition.json';actual=dict(status='calculated_unadopted',id='weak-condition',source_run_id='native',source_case_id='square',waveform='sine',normalizations=modes())
            source.write_text(json.dumps(actual));brief=root/'weak.result-brief.json'
            snapshot=dict(conditions=[dict(id='weak-condition',normalizations={'truncated':True},condition_JSON=dict(path=str(source),SHA256=hashlib.sha256(source.read_bytes()).hexdigest()))])
            brief.write_text(json.dumps(snapshot));builder=tool.CatalogBuilder(root);builder.store.load(brief)
            with patch.object(builder,'native',return_value={}),patch.object(builder,'producer',return_value=()),patch.object(builder,'normalize',return_value=row('weak'))as normalized,patch.object(builder,'add')as added:
                builder.brief(brief,snapshot)
            self.assertEqual(normalized.call_args.args[1],actual['normalizations']);self.assertEqual(normalized.call_args.kwargs['condition'],actual)
            self.assertEqual(added.call_count,1);self.assertEqual(builder.exclusions,[])

    def test_catalog_is_metadata_only_and_output_bound_is_small(self):
        self.assertEqual(tool.MAX_OUTPUT_BYTES,2*1024**2);self.assertLessEqual(tool.MAX_DISCOVERY_FILES,512)
        builder=tool.CatalogBuilder();builder.baseline=row('baseline');builder.add(copy.deepcopy(builder.baseline),'/synthetic/base.json')
        builder.baseline=next(iter(builder.rows.values()))
        result=builder.finish();self.assertEqual(result['selected_layouts'],[]);self.assertFalse(result['native_arrays_read'])
        self.assertFalse(result['native_raw_hashes_independently_verified']);self.assertFalse(result['candidate_adopted'])
        self.assertFalse(result['full_convergence_validated']);self.assertFalse(result['experimentally_validated'])


if __name__=='__main__':unittest.main()
