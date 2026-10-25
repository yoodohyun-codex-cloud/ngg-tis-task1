import unittest
import compact_windows_export as c

def publication(paths,commit='a'*40):
    return dict(status='published_readback_verified',commit=commit,files={p:dict(SHA256='b'*64,bytes=4,readback_passed=True)for p in paths})

class CompactPaths(unittest.TestCase):
    def test_native_case_and_gui_paths_stay_short(self):
        paths=['data-native/cloud-all-layer-sc-epsilon-sensitivity-20261025/bases/baseline-square15-sc-eps1100-xy80/field-3000.bin.gz','data-native/cloud-all-layer-sc-epsilon-sensitivity-20261025/postprocess/scalars.npz']
        entries=c.build_entries([('SC2',publication(paths)),('GUI',publication(['docs/TASK1_ALL_LAYER_SENSITIVITY_20261025/index.html'],'c'*40))])
        self.assertIn('layer-20261025/SC2/raw/field-3000.bin.gz',[x['local_path']for x in entries])
        self.assertIn('layer-20261025/gui/index.html',[x['local_path']for x in entries])
        self.assertTrue(all(len(x['local_path'])<=100 for x in entries))
    def test_case_collisions_are_disambiguated_deterministically(self):
        pub=publication(['data-native/a/bases/c/A.bin','data-native/b/bases/c/a.bin'])
        entries=c.build_entries([('SC2',pub)])
        self.assertEqual(len({x['local_path'].casefold()for x in entries}),2)
        reversed_pub=publication(list(reversed(list(pub['files']))))
        self.assertEqual(entries,c.build_entries([('SC2',reversed_pub)]))
    def test_unverified_and_unsafe_paths_rejected(self):
        for path in ('../secret','a/NUL','a/f:stream','a/b"c','a/\x01bad'):
            with self.subTest(path=path),self.assertRaises(ValueError):c.build_entries([('SC2',publication([path]))])
        pub=publication(['a/safe']);pub['files']['a/safe']['readback_passed']=False
        with self.assertRaises(ValueError):c.build_entries([('SC2',pub)])
    def test_script_uses_compact_destination_and_separate_remote_path(self):
        entries=c.build_entries([('SC4',publication(['data-native/run/bases/c/field-3000.bin.gz']))])
        script=c.render(entries)
        self.assertIn('$relative=[string]$spec.local_path',script)
        self.assertIn('$spec.path -split',script)
        self.assertIn('OneDrive_sync_verified=$false',script)
        self.assertNotIn('__MANIFEST__',script)
        self.assertNotIn('C:'+chr(92)+'Users'+chr(92),script)

if __name__=='__main__':unittest.main()
