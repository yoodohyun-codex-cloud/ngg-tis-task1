"""Synthetic disappearance regressions; no real paths scanned."""
import unittest
from types import SimpleNamespace
from temporary_accounting import counted_bytes
class Entry:
    def __init__(self,n=None):self.n=n
    def is_file(self):return True
    def stat(self):
        if self.n is None:raise FileNotFoundError('Synthetic vanished sibling')
        return SimpleNamespace(st_size=self.n)
class Directory:
    def __init__(self,children):self.children=children
    def is_file(self):return False
    def rglob(self,_):return iter(self.children)
class TemporaryAccountingContracts(unittest.TestCase):
    def test_one_vanished_file_does_not_erase_other_directory_bytes(self):
        self.assertEqual(counted_bytes(Directory([Entry(13),Entry(),Entry(29)])),42)
    def test_multiple_vanished_entries_preserve_stable_siblings(self):
        self.assertEqual(counted_bytes(Directory([Entry(),Entry(7),Entry(),Entry(19)])),26)
    def test_absent_file_counts_zero_without_touching_other_roots(self):
        self.assertEqual(counted_bytes(Entry()),0)
        self.assertEqual(counted_bytes(Entry(14341)),14341)
