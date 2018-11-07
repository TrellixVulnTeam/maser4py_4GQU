import unittest
import os
from maser.data import *

test_file = os.path.join('data', 'cdpp', 'isee3', 'SBH_ISEE3_19780820')
o = MaserDataFromFile(test_file)


class MaserDataFromFileTest(unittest.TestCase):

    """Test case for MaserData class"""

    def test_file_name_method(self):
        self.assertEqual(o.get_file_name(), 'SBH_ISEE3_19780820')

    def test_file_path_method(self):
        self.assertEqual(o.get_file_path(), os.path.join(os.path.abspath(os.path.curdir), 'data', 'cdpp', 'isee3'))

    def test_file_size_method(self):
        self.assertEqual(o.get_file_size(), 5817420)

