"""Synthetic input transformations only; no native/template reads or PDE."""
import csv
import io
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import centered_inputs as inputs


class CenteredInputTest(unittest.TestCase):
    def fixture(self):
        p={'h_mm':'.625','channels':'1','validation.sc_cells':'2','bulk.counts':'14,14,40',
           'frequencies':'3000,3030,9000,9090','mask.path':'/old/mask.csv','mask.sha256':'old',
           'z.3000.re':'4.4523250115054224e-05','z.3000.im':'-9.587510512701813e-05','sc.sigma':'.0002'}
        for pad,x in enumerate((-10.,10.)):
            for k,v in {'x_mm':str(x),'y_mm':'-10.0','shape':'rectangle','width_mm':'15','height_mm':'15',
                        'rotation_deg':'0','analytic_area_mm2':'225','represented_area_m2':'.000225'}.items():p[f'pad.{pad}.{k}']=v
        text=''.join(k+'='+v+'\n' for k,v in p.items())
        rows=[dict(pad=pad,i=i,j=j,area_m2=(.625/1000)**2) for pad,start in ((0,12),(1,44))
              for j in range(12,36) for i in range(start,start+24)]
        return text,rows

    def test_only_geometry_y_and_selected_frequency_and_mask_identity_change(self):
        text,rows=self.fixture();before=[dict(r)for r in rows]
        config,mask,proof=inputs.transform_inputs(text,rows,Path('/new/masks/centered.csv'))
        after=inputs.properties(config.decode());old=inputs.properties(text)
        self.assertEqual('3000',after['frequencies']);self.assertEqual('0.0',after['pad.0.y_mm']);self.assertEqual('0.0',after['pad.1.y_mm'])
        self.assertEqual({k:v for k,v in old.items()if k not in proof['changed_fields']},
                         {k:v for k,v in after.items()if k not in proof['changed_fields']})
        self.assertEqual(after['mask.sha256'],inputs.sha(mask));self.assertEqual(rows,before)
        self.assertFalse(proof['old_fields_translated'])

    def test_translated_native_mask_retains_area_and_fixed_finite_boundary(self):
        text,rows=self.fixture();_,mask,proof=inputs.transform_inputs(text,rows,'/new/mask.csv')
        new=list(csv.DictReader(io.StringIO(mask.decode())))
        self.assertEqual(1152,len(new));self.assertEqual(set(range(28,52)),{int(r['j'])for r in new})
        self.assertEqual(576,sum(int(r['pad'])==0 for r in new));self.assertEqual(576,sum(int(r['pad'])==1 for r in new))
        self.assertAlmostEqual(225e-6,proof['areas_m2'][0]);self.assertAlmostEqual(225e-6,proof['areas_m2'][1])
        self.assertEqual(20.,proof['centre_distance_mm']);self.assertEqual(5.,proof['edge_gap_mm'])
        for pad in proof['pads']:
            self.assertEqual(0.,pad['center_mm'][1]);self.assertTrue(all(x*x+y*y<625 for x,y in pad['polygon_mm']))
        self.assertEqual(362.5,proof['physical_vertex_radius_squared_max_mm2'])

    def test_wrong_template_partial_area_or_duplicate_face_fails(self):
        text,rows=self.fixture()
        for badtext,badrows in ((text.replace('channels=1','channels=2'),rows),(text,rows+[rows[0]]),
            (text,[dict(rows[0],area_m2=rows[0]['area_m2']/2),*rows[1:]]),
            (text,[dict(rows[0],j=0),*rows[1:]])):
            with self.assertRaises(ValueError):inputs.transform_inputs(badtext,badrows,'/new/mask.csv')


if __name__=='__main__':unittest.main()
