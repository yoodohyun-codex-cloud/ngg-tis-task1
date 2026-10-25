"""Static patch contracts; no numerical/native I/O is performed by these tests."""
import ast
from pathlib import Path
import unittest
import fixed_legacy as p


def literal(path, name):
    tree=ast.parse(Path(path).read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError('Static source literal missing')


class FixedLegacySource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=literal('/workspace/ngg-tis-task1/tools/task1_best1_pair_dashboard.py','SCRIPT')
        cls.vectors=literal('/dev/shm/task1-field-shape-export-20261025/source/field_shape_gui.py','SCRIPT')

    def test_original_disables_range_and_preserves_metric_logic(self):
        value=p.patch_original(self.original)
        self.assertIn("$('range').disabled=true",value)
        self.assertIn('fmax=TASK1_LOCKED_E,jmax=TASK1_LOCKED_J',value)
        self.assertNotIn("region=$('range').value",value)
        self.assertEqual(value.count("canvas.dataset.vmin='0'"),2)
        self.assertIn('S.regions[key][primary]',value)

    def test_vector_bound_not_current_view_max(self):
        value=p.patch_vectors(self.vectors)
        self.assertIn('max=TASK1_LOCKED_E;cache.views=views;',value)
        self.assertIn("cache.scale===TASK1_LOCKED_E",value)
        self.assertIn('current_view_actual_maximum_V_m:expectedMax',value)
        self.assertIn('waveform_components_checked:waveformComponents',value)

    def test_xy_pixel_arrow_hover_transform_consistent(self):
        value=p.patch_vectors(self.vectors)
        self.assertIn("const down=p.kind!=='XY'",value)
        self.assertIn("dy=(p.kind==='XY'?-b:b)",value)
        self.assertIn('v=tr.down?',value)
        self.assertIn('Math.abs(yp(ve[j+1])-yp(ve[j]))',value)
        self.assertIn("el.dataset.axisOrientation=down?'depth_down':'y_up'",value)

    def test_fail_closed_on_missing_or_repeated_anchors(self):
        with self.assertRaises(ValueError):p.patch_original(self.original.replace("'use strict';",''))
        with self.assertRaises(ValueError):p.patch_vectors(self.vectors+self.vectors)
        with self.assertRaises(ValueError):p.patch_original(p.patch_original(self.original))


if __name__=='__main__':unittest.main()
