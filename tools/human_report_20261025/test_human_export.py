"""Pure contract tests; import has no filesystem/network or simulation activity."""
import unittest
import human_export as h


def publication(paths,commit='a'*40):
    return dict(status='published_readback_verified',commit=commit,
                files={path:dict(SHA256='b'*64,bytes=4,readback_passed=True)for path in paths})


class HumanCompactExport(unittest.TestCase):
    def test_human_sc4_and_gui_paths_are_short_and_distinct(self):
        raw='data-native/cloud-human-tissue-20261025/bases/baseline-square15-human-reference-xy80/field-3000.bin.gz'
        gui='docs/TASK1_HUMAN_REPORT_20261025/index.html'
        entries=h.build_entries([('HUMAN',publication([raw])),('HUMANSC4',publication([raw],'c'*40)),('GUI',publication([gui],'d'*40))])
        self.assertIn('layer-human-20261025/HUMAN/raw/field-3000.bin.gz',[row['local_path']for row in entries])
        self.assertIn('layer-human-20261025/HUMANSC4/raw/field-3000.bin.gz',[row['local_path']for row in entries])
        self.assertIn('layer-human-20261025/gui/index.html',[row['local_path']for row in entries])
        self.assertTrue(all(len(row['local_path'])<=100 for row in entries))

    def test_collisions_order_independent_and_duplicate_source_trusted(self):
        pub=publication(['data-native/a/bases/c/A.bin','data-native/b/bases/c/a.bin'])
        rows=h.build_entries([('HUMAN',pub)])
        reverse=publication(list(reversed(list(pub['files']))))
        self.assertEqual(rows,h.build_entries([('HUMAN',reverse)]))
        self.assertEqual(len({row['local_path'].casefold()for row in rows}),2)
        self.assertEqual(rows,h.build_entries([('HUMAN',pub),('HUMAN',pub)]))
        conflict=publication(list(pub['files']));conflict['files'][list(pub['files'])[0]]['bytes']=5
        with self.assertRaises(ValueError):h.build_entries([('HUMAN',pub),('HUMAN',conflict)])

    def test_unverified_unsafe_unpinned_and_legacy_groups_rejected(self):
        for path in ('../secret','a/NUL','a/f:stream','a/b"c','a/\x01bad'):
            with self.subTest(path=path),self.assertRaises(ValueError):h.build_entries([('HUMAN',publication([path]))])
        pub=publication(['a/safe']);pub['files']['a/safe']['readback_passed']=False
        with self.assertRaises(ValueError):h.build_entries([('HUMAN',pub)])
        with self.assertRaises(ValueError):h.build_entries([('SC2',publication(['a/safe']))])
        with self.assertRaises(ValueError):h.build_entries([('HUMAN',publication(['a/safe'],'main'))])

    def test_generic_manifest_and_script_preserve_claim_boundaries(self):
        rows=h.build_entries([('HUMAN',publication(['data-native/run/bases/c/field-3000.bin.gz']))])
        manifest=h.manifest_document(rows);script=h.powershell_document(rows)
        self.assertEqual(manifest['total_bytes'],4)
        self.assertFalse(manifest['Windows_saved'])
        self.assertFalse(manifest['OneDrive_sync_verified'])
        self.assertFalse(manifest['storage_capacity_guard_enabled'])
        self.assertIn('$relative=[string]$spec.local_path',script)
        self.assertIn('$spec.path -split',script)
        self.assertIn('layer-human-20261025/',script)
        self.assertIn('OneDrive_sync_verified=$false',script)
        self.assertNotIn('__MANIFEST__',script)
        self.assertNotIn('C:'+chr(92)+'Users'+chr(92),script)
        self.assertEqual(script,h.render(rows))


if __name__=='__main__':unittest.main()
