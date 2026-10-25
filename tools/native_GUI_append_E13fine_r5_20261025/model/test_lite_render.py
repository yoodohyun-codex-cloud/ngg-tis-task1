"""Tiny synthetic renderer contracts. No actual test/render run by author."""
import base64
import copy
import json
import re
import struct
import unittest
from lite_render import render


def payload():
    plane=dict(display_only=True,horizontal_axis='x_mm',vertical_axis='depth_mm',orientation='xz',
        h_edges_mm=[-1.,1.],v_edges_mm=[15.,20.],shape=[1,1],
        values_b64_float16LE=base64.b64encode(struct.pack('<e',1.)).decode(),
        valid_mask_b64_u8=base64.b64encode(b'\1').decode(),sampling_metadata=dict(method='synthetic native cell'))
    def case(identifier,pads,new=False):
        c=dict(id=identifier,label=identifier,pad_count=pads,independent_outputs=2,
            grid_version='synthetic display fixture',amplitude_scales=dict(raw=1.),stats=dict(original_only=True),
            bar_values=dict(target_AM_mean=dict(raw=1.)),provenance=dict(source_commit='a'*40,run_id='synthetic'),
            display=dict(planes=dict(AM_max2074=dict(xz=plane),contact_J=dict(status='unavailable',reason='synthetic missing data')),pad_outlines=[]))
        if new:
            rows=[]
            for i in range(40):
                rows.append(dict(probe_id='synthetic-probe-'+str(i),status='calculated_unloaded_only',centre_xyz_mm=[0.,0.,5.],differential_axis='x',tip_spacing_mm=5.,strict_same_layer_bracket_available=i<20,same_layer_extrapolation_used=i>=20,
                    unloaded=dict(carrier_waveform_Vpp=.1,carrier_waveform_N65536_Vpp=.1,carrier_RMS_exact_V=.03,envelope_AM_exact_V_peak=.02,physical_voltage_10Hz_DFT_peak_V=0.,envelope_10Hz_DFT_peak_V=.01),
                    waveform=dict(carrier_excerpt_time_s=[0.,.00001],carrier_excerpt_V=[-.01,.01],envelope_time_s=[0.,.1],envelope_V=[.01,.02])))
            c['probe_summary']=dict(probe_count=40,calculated_probe_count=40,unavailable_probe_count=0,strict_same_layer_bracket_available_probe_count=20,same_layer_extrapolated_probe_count=20,probes=rows)
        return c
    return dict(schema='task1-native-GUI-append-E13fine-display-v1',title='Synthetic test',repository='yoodohyun-codex-cloud/ngg-tis-task1',
        normalization_modes=[dict(id='raw',label='Fixed voltage')],bar_metrics=[dict(id='target_AM_mean',label='Stored target mean',unit='V/m')],
        shared_initial_ranges=dict(x_mm=[-25.,25.],y_mm=[-25.,25.],depth_mm=[0.,25.1],AM_V_m=[0.,2.],RMS_V_m=[0.,2.],J_A_m2=[0.,2.],bar_value=[0.,2.],wave_time_ms=[0.,100.],wave_voltage_V=[-1.,1.]),
        sections=[dict(id='new_native',kind='new_native',title='New native',cases=[case(name,4,True)for name in('fine-B0','fine-P23','coarse-E13','fine-E13')]),
            dict(id='legacy_reference',kind='legacy_reference',title='Legacy 4/8/12/16',cases=[case('legacy-'+str(n),n)for n in(4,8,12,16)])])



class LiteRendererContracts(unittest.TestCase):
    def test_standalone_small_source_has_controls_and_preserves_payload(self):
        p=payload();before=copy.deepcopy(p);document=render(p)
        self.assertEqual(p,before)
        self.assertLess(len(document.encode()),8_200_000)
        for identifier in('variable','view','mode','rangeControls','waveCase','waveProbe','barMetric','exportSettings','importSettings'):
            self.assertIn('id="'+identifier+'"',document)
        self.assertIn('(()=>{',document)
        self.assertNotIn('window.top',document)
        self.assertNotIn('fetch(',document)
        self.assertNotIn('eval(',document)
        self.assertIn('No range is automatically changed',document)

    def test_script_payload_escapes_markup_without_changing_json_semantics(self):
        p=payload();p['title']='</script><img src=x onerror=alert(1)>'
        document=render(p)
        match=re.search(r'<script id="payload" type="application/json">(.*?)</script>',document,re.S)
        self.assertIsNotNone(match)
        self.assertEqual(json.loads(match.group(1)),p)
        self.assertNotIn('<img',match.group(1))
        self.assertIn('script-src \'sha256-',document)
        self.assertNotIn(" '; style-src",document)

    def test_nonfinite_or_inverted_shared_ranges_are_rejected(self):
        for value in([1.,0.],[0.,float('nan')]):
            p=payload();p['shared_initial_ranges']['AM_V_m']=value
            with self.assertRaisesRegex(ValueError,'shared initial range'):render(p)

    def test_arrows_must_remain_real_2000Hz_carrier_not_am_vectors(self):
        p=payload();plane=p['sections'][0]['cases'][0]['display']['planes']['AM_max2074']['xz']
        plane.update(arrows=[dict(h_mm=0.,v_mm=17.,u_V_m=1.,v_V_m=-1.)],arrow_frequency_Hz=10,arrow_phase_rad=0)
        with self.assertRaisesRegex(ValueError,'2000Hz'):render(p)

    def test_output_rejects_whole_large_collection_without_silent_dropping(self):
        p=payload();p['unbounded_extra']='x'*8_200_000
        with self.assertRaisesRegex(ValueError,'Trim authenticated'):render(p)
        p=payload();p['sections'][0]['cases']*=5
        with self.assertRaisesRegex(ValueError,'Exactly four'):render(p)

    def test_missing_contact_data_remains_unavailable_and_ranges_do_not_reset(self):
        document=render(payload())
        self.assertIn('Stored contact J map unavailable; no bulk J is derived.',document)
        self.assertIn('state.ranges=proposed',document)
        self.assertIn('switching variable',document.lower())
        self.assertIn('strict_same_layer_bracket_available_probe_count',document)
        self.assertIn('physical_voltage_10Hz_DFT_peak_V',document)
        self.assertIn('envelope_10Hz_DFT_peak_V',document)
        self.assertIn('Legacy 4/8/12/16 pads are preserved side by side.',document)

    def test_legacy_baseline_and_separate_pad_counts_cannot_be_omitted(self):
        p=payload();p['sections'][1]['cases'][0]['pad_count']=8
        with self.assertRaisesRegex(ValueError,'4/8/12/16'):render(p)

    def test_missing_probe_accounting_is_not_silently_treated_as_zero(self):
        p=payload();p['sections'][0]['cases'][0]['probe_summary']=dict(probe_count=40,probes=[{}]*40,calculated_probe_count=40,unavailable_probe_count=0)
        with self.assertRaisesRegex(ValueError,'strict/extrapolated/unavailable'):render(p)

    def test_stored_contact_requires_real_fill_geometry_and_hover_checks_union(self):
        p=payload();case=p['sections'][0]['cases'][0];plane=copy.deepcopy(case['display']['planes']['AM_max2074']['xz'])
        plane.update(vertical_axis='y_mm',v_edges_mm=[-1.,1.]);case['display']['planes']['contact_J']=dict(status='stored_native_map',xy=plane);case['display']['pad_outlines']=[{}]
        with self.assertRaisesRegex(ValueError,'physical footprint'):render(p)
        case['display']['pad_outlines']=[dict(pad_id=0,node=0,patch_rectangles_mm=[[-.5,.5,-.5,.5]],boundary_segments_xy_mm=[])]
        document=render(p)
        self.assertIn('physicalContains(item.c.display.pad_outlines,hv,vv)',document)
        self.assertIn('Outside physical contact; native face value is not assigned here.',document)
