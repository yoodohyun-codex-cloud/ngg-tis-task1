import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_best1_pair_run as run


class ProspectiveWriteTests(unittest.TestCase):
    def test_storage_and_output_limit_fail_before_artifact_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'runtime').mkdir();(root/'runtime/task1-budget.json').write_bytes(b'{}')
            output=root/'new';output.mkdir();target=output/'field.html'
            with patch.object(run,'ROOT',root),patch.object(run,'OUTPUT_CAP',run.FINAL_RESERVE+20):
                with patch.object(run.shutil,'disk_usage',return_value=SimpleNamespace(free=2*run.GIB+10)):
                    with self.assertRaises(ValueError):run.put_new(target,b'123',output)
                    self.assertFalse(target.exists())
                with patch.object(run.shutil,'disk_usage',return_value=SimpleNamespace(free=3*run.GIB)):
                    with self.assertRaises(ValueError):run.put_new(target,b'x'*21,output)
                    self.assertFalse(target.exists())
                    run.put_new(target,b'original',output)
                    with self.assertRaises(ValueError):run.put_new(target,b'replacement',output)
                    self.assertEqual(target.read_bytes(),b'original')

    def test_cleanup_targets_only_live_startticks_proven_children(self):
        with patch.object(run.bounded,'owned_descendants',return_value={10:100,20:200,30:300}),\
             patch.object(run.bounded,'live',side_effect=lambda pid,ticks:pid==20),\
             patch.object(run.os,'kill') as kill,\
             patch.object(run.time,'monotonic',side_effect=[0,3,4,6]):
            survivors=run.stop_owned(10,100,{10:100})
            self.assertEqual(survivors,{20:200})
            self.assertEqual([call.args for call in kill.call_args_list],[(20,run.signal.SIGTERM),(20,run.signal.SIGKILL)])


if __name__=='__main__':unittest.main()
