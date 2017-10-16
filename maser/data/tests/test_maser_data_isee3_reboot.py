import unittest
import datetime
import os
import numpy
import maser.data.tests
import maser.data.data
import maser.data.isee3.reboot

maser.data.tests.load_test_data("isee3")

files = [os.path.join('data', 'isee3', 'tlm_uiowa', 'telm_2014-08-09T22_uiframe.bin'),
         os.path.join('data', 'isee3', 'tlm_uiowa', 'telm_2014-08-09T23_uiframe.bin')]
o1 = maser.data.isee3.reboot.ISEE3SBHFile(files[0])


class ISEE3SBHFileClassTest(unittest.TestCase):

    def test_init(self):
        self.assertIsInstance(o1, maser.data.data.MaserDataFromFile)
        self.assertEqual(o1.n_minor_frame, 7204)
        self.assertIsInstance(o1.data, maser.data.isee3.reboot.ISEE3SBHMajorFrames)
        self.assertEqual(o1.n_major_frame, 29)
        #self.assertSequenceEqual(numpy.shape(o1.data.minor_frames), (7204, 128))

    def test_u_iowa_hdr(self):
        self.assertEqual(o1.data.u_iowa_hdr[0], '2014-08-09T22:00:00.067148')
        self.assertEqual(o1.data.u_iowa_hdr[10], '2014-08-09T22:00:05.048031')
        self.assertEqual(len(o1.data.u_iowa_hdr), o1.n_minor_frame)

    def test_get_project_hdr(self):
        self.assertEqual(o1.data.reboot_hdr[0],
                         'Frame 16,026 at symbol 32,821,070 (08:54:11.826) with Fano from Boccum')
        self.assertEqual(o1.data.reboot_hdr[10],
                         'Frame 16,036 at symbol 32,841,550 (08:54:31.826) with Fano from Boccum')
        self.assertEqual(len(o1.data.reboot_hdr), o1.n_minor_frame)

