"""Native metadata schema regression; JSON only, no arrays or numerical run."""
from pathlib import Path
import json
import sys
import unittest
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'tools'))
import task1_rounded_direction_bounds as b

class ActualMetadataSchema(unittest.TestCase):
    def test_exporter_stores_channels_in_mesh_and_outputs_in_circuit(self):
        runs=[('cloud-rounded-fullface-20261021T200000Z','rounded-fullface225-xy80'),('cloud-rounded-sc4-20261021T204000Z','rounded-fullface225-sc4-xy80')]
        metadata=[];configs=[]
        for run,ident in runs:
            path=R/'data-native'/run
            metadata.append(json.loads((path/'postprocess'/ident/'summary.json').read_text())['mesh_metadata'])
            case=next(c for c in json.loads((path/'preregistration.json').read_text())['cases']if c['id']==ident)
            self.assertNotIn('n_outputs',metadata[-1]);self.assertEqual(2,case['circuit']['n_outputs'])
            configs.append(b.native._properties(Path(case['config_file'])))
        result=b.validate_mesh_identity(*metadata,*configs)
        self.assertEqual((351680,361728),(result['SC2_cells'],result['SC4_cells']))
        self.assertFalse(result['full_convergence_validated'])
