import unittest
import types
import datetime
import numpy
from astropy.units import Unit, Quantity
from maser.data.tests import load_test_data, get_data_directory
from maser.data import MaserDataFromFile, MaserDataFromFileText
from maser.data.padc.lesia.voyager.pra_gsfc import GSFCVoyagerPRAData, \
    GSFCVoyagerPRARDRLowBand6SecSweep, load_voyager_pra_gsfc_lowband_6sec, \
    VOYAGER_PRA_FREQUENCY_LIST

load_test_data("gsfc")

root_data_path = get_data_directory() / 'gsfc'

file = root_data_path / 'voyager_pra_6sec' / '19890811.dat'
ovC = GSFCVoyagerPRAData(str(file))
ovF = load_voyager_pra_gsfc_lowband_6sec(str(file))


class LoadWithFunction(unittest.TestCase):

    def test_loader_function(self):
        self.assertIsInstance(ovF, GSFCVoyagerPRAData)


class LoadWithClass(unittest.TestCase):

    def test_loader_class(self):
        self.assertIsInstance(ovC, (GSFCVoyagerPRAData, MaserDataFromFileText, MaserDataFromFile))

    def test_meta(self):
        self.assertEqual(ovC.format, 'TXT')
        self.assertEqual(ovC.get_file_name(), '19890811.dat')

    def test_len(self):
        self.assertEqual(len(ovC), 14360)
        self.assertEqual(ovC._n_rows, 1795)

    def test_time(self):
        self.assertEqual(len(ovC.time), 14360)
        self.assertIsInstance(ovC.time, numpy.ndarray)
        self.assertIsInstance(ovC.time[0], datetime.datetime)
        self.assertEqual(ovC.time[0].isoformat(), '1989-08-11T00:00:00')
        self.assertEqual(ovC.time[1].isoformat(), '1989-08-11T00:00:06')
        self.assertEqual(ovC.time[-1].isoformat(), '1989-08-11T23:59:54')

    def test_frequency(self):
        self.assertIsInstance(ovC.frequency, Quantity)
        self.assertEqual(len(ovC.frequency), 70)
        self.assertListEqual(list(ovC.frequency), list(VOYAGER_PRA_FREQUENCY_LIST))
        self.assertAlmostEqual(ovC.frequency[0].value/1000, 1.326, 3)
        self.assertEqual(ovC.frequency[0].unit, Unit('kHz'))
        self.assertAlmostEqual(ovC.frequency[-1].value, 1.2, 3)
        self.assertEqual(ovC.frequency[-1].unit, Unit('kHz'))

    def test_data(self):
        self.assertIsInstance(ovC._data, numpy.ndarray)
        self.assertEqual(len(ovC._data), 1795)
        self.assertEqual(ovC._data[0, 0], 1989)
        self.assertEqual(ovC._data[0, 1], 8)
        self.assertEqual(ovC._data[0, 2], 11)
        self.assertEqual(ovC._data[0, 3], 0)
        self.assertEqual(ovC._data[1, 3], 48)
        self.assertEqual(ovC._data[2, 3], 96)
        self.assertListEqual(list(ovC._data[0, 4::71]), list([1856, 1344, 1856, 1344, 1856, 1344, 1856, 1344]))


class Sweep(unittest.TestCase):

    def test_class(self):
        self.assertIsInstance(ovC.get_single_sweep(0), GSFCVoyagerPRARDRLowBand6SecSweep)

    def test_sweeps(self):
        self.assertIsInstance(ovC.sweeps(), types.GeneratorType)
        self.assertEqual(len(list(ovC.sweeps())), len(ovC))

    def test_sweep_time(self):
        self.assertEqual(ovC.get_single_sweep(0).get_datetime(), ovC.time[0])

    def test_sweep_status(self):
        self.assertEqual(ovC.get_single_sweep(0).status, 1856)
        self.assertEqual(ovC.get_single_sweep(1).status, 1344)

    def test_sweep_attenuator(self):
        self.assertEqual(ovC.get_single_sweep(0).attenuator, 0)

    def test_sweep_data(self):
        self.assertIsInstance(ovC.get_single_sweep(0).data, dict)
        self.assertSetEqual(set(ovC.get_single_sweep(0).data.keys()), {'R', 'L'})
        self.assertEqual(ovC.get_single_sweep(0).data['R'][0], ovC.get_raw_sweep(0)[1])
        self.assertEqual(ovC.get_single_sweep(0).data['R'][1], ovC.get_raw_sweep(0)[3])
        self.assertEqual(ovC.get_single_sweep(0).data['L'][0], ovC.get_raw_sweep(0)[2])
        self.assertEqual(ovC.get_single_sweep(0).data['L'][1], ovC.get_raw_sweep(0)[4])

    def test_sweep_freq(self):
        self.assertEqual(ovC.get_single_sweep(0).attenuator, 0)
        self.assertSetEqual(set(ovC.get_single_sweep(0).freq.keys()), {'R', 'L', 'avg'})
        self.assertEqual(ovC.get_single_sweep(0).freq['R'][0], ovC.frequency[0])
        self.assertEqual(ovC.get_single_sweep(0).freq['R'][1], ovC.frequency[2])
        self.assertEqual(ovC.get_single_sweep(0).freq['L'][0], ovC.frequency[1])
        self.assertEqual(ovC.get_single_sweep(0).freq['L'][1], ovC.frequency[3])
        self.assertEqual(ovC.get_single_sweep(0).freq['avg'][0], (ovC.frequency[0]+ovC.frequency[1])/2)
        self.assertEqual(ovC.get_single_sweep(0).freq['avg'][1], (ovC.frequency[2]+ovC.frequency[3])/2)

    def test_sweep_type(self):
        self.assertEqual(ovC.get_single_sweep(0).type, 'R')
        self.assertEqual(ovC.get_single_sweep(1).type, 'L')
