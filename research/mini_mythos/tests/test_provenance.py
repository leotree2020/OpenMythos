import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from provenance import github_repository


class ProvenanceTests(unittest.TestCase):
    def test_https(self):
        self.assertEqual(github_repository('https://github.com/leotree2020/OpenMythos.git'), 'leotree2020/OpenMythos')

    def test_ssh(self):
        self.assertEqual(github_repository('git@github.com:leotree2020/OpenMythos.git'), 'leotree2020/OpenMythos')

    def test_ssh_url(self):
        self.assertEqual(github_repository('ssh://git@github.com/leotree2020/OpenMythos'), 'leotree2020/OpenMythos')

    def test_reject_untrusted_host(self):
        self.assertIsNone(github_repository('https://fake.github.com/leotree2020/OpenMythos'))

    def test_reject_secret_bearing_url(self):
        self.assertIsNone(github_repository('https://secret@github.com/leotree2020/OpenMythos.git'))


if __name__ == '__main__':
    unittest.main()
