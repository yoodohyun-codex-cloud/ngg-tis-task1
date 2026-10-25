"""Pure path whitelist contracts; root alone chooses actual test execution."""
import unittest
from publish_caches import canonical_target


class PortableTargets(unittest.TestCase):
 def test_accepts_only_cache_and_tool_repository_paths(self):
  for name in('data-native/retained-eigen-cache-20261025/xy100/index.json',
               'tools/retained_eigen_cache_20261025/publish_caches.py'):
   self.assertEqual(canonical_target(name),name)

 def test_rejects_absolute_traversal_private_and_noncanonical_paths(self):
  for name in('/dev/shm/task1-cache/Q.f64le','C:/Users/example/Q.f64le',
               'data-native/retained-eigen-cache-20261025/../private.json',
               'data-native/retained-eigen-cache-20261025//xy100/index.json',
               'data-native/retained-eigen-cache-20261025/xy100/.git/config',
               'runtime/private.json','tools/retained_eigen_cache_20261025/a\\b'):
   with self.subTest(name=name),self.assertRaises(ValueError):canonical_target(name)


if __name__=='__main__':unittest.main()
