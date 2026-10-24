import unittest
import windows_export as w


class WindowsExportContract(unittest.TestCase):
    def row(self, path='data-native/sample/ShapeNet$Edge.class'):
        return dict(path=path, commit='b'*40, SHA256='a'*64, bytes=40)

    def test_unicode_spaces_and_dollar_allowed(self):
        text=w.render([self.row('docs/전기장 모양/ShapeNet$Edge.class')])
        self.assertIn('EscapeDataString',text)
        self.assertIn('OneDrive_sync_verified=$false',text)
        self.assertNotIn('lijil',text)
        self.assertNotIn('__MANIFEST__',text)

    def test_traversal_ads_devices_rejected(self):
        for path in ('../secret','C:/a','a\\b','a/../b','a//b','a/file:stream','a/NUL','a/COM1.txt','a/b.'):
            with self.subTest(path=path), self.assertRaises(ValueError):w.render([self.row(path)])

    def test_case_conflict_and_nonimmutable_refs_rejected(self):
        with self.assertRaises(ValueError):w.render([self.row('docs/A'),self.row('docs/a')])
        r=self.row();r['commit']='main'
        with self.assertRaises(ValueError):w.render([r])
        r=self.row();r['bytes']=-1
        with self.assertRaises(ValueError):w.render([r])


if __name__=='__main__':unittest.main()
