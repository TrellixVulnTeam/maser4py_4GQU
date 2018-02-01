import unittest
import datetime
import os
import maser.data.tests
import maser.data.nancay.nda.routine

maser.data.tests.load_test_data("nda")

test_file_rt1 = os.path.join('data', 'nda', 'routine', 'J160131.RT1')
o_rt1 = maser.data.nancay.nda.routine.load_nda_routine_from_file(test_file_rt1)

test_file_cdf = os.path.join('data', 'nda', 'routine', 'srn_nda_routine_jup_edr_201601302247_201601310645_V12.cdf')
o_cdf= maser.data.nancay.nda.routine.load_nda_routine_from_file(test_file_cdf)


class NancayNDARoutineDataRT1Class(unittest.TestCase):

    """Test case for NDARoutineDataRT1 class"""

    def test_class(self):
        self.assertIsInstance(o_rt1, maser.data.nancay.nda.routine.NDARoutineDataRT1)

    def test_dataset_name(self):
        self.assertEqual(o_rt1.name, "SRN/NDA Routine RT1 Dataset")

    def test_filedate(self):
        self.assertEqual(o_rt1.file_info['filedate'], "20160131")

    def test_len(self):
        self.assertEqual(len(o_rt1), 57469)

    def test_format(self):
        self.assertEqual(o_rt1.file_info['format'], 'RT1')

    def test_header_version(self):
        self.assertEqual(o_rt1.file_info['header_version'], 6)

    def test_meridian(self):
        self.assertEqual(o_rt1.get_meridian_datetime(), datetime.datetime(2016, 1, 31, 2, 46))
        self.assertEqual(o_rt1.get_meridian_time(), datetime.time(2, 46))

    def test_get_single_sweep(self):
        sweep = o_rt1.get_single_sweep(0)
        self.assertIsInstance(sweep, maser.data.nancay.nda.routine.NDARoutineSweepRT1)

    def test_get_freq_axis(self):
        f = o_rt1.get_freq_axis()
        self.assertEqual(len(f), 400)
        self.assertEqual(f[0], 10)
        self.assertEqual(f[-1], 39.925)

    def test_get_time_axis(self):
        t = o_rt1.get_time_axis()
        self.assertEqual(len(t), 57469)
        self.assertEqual(t[0], datetime.datetime(2016, 1, 30, 22, 47, 6, 30000))
        self.assertEqual(t[-1], datetime.datetime(2016, 1, 31, 6, 45, 59, 680000))

    def test_get_first_sweep(self):
        sweep = o_rt1.get_first_sweep()
        self.assertEqual(sweep.index, 0)

    def test_get_last_sweep(self):
        sweep = o_rt1.get_last_sweep()
        self.assertEqual(sweep.index, 57468)

    def test_get_start_date(self):
        self.assertEqual(o_rt1.get_start_date(), datetime.date(2016, 1, 30))


class NancayNDARoutineDataCDFClass(unittest.TestCase):

    """Test case for NDARoutineDataCDF class"""

    def test_class(self):
        self.assertIsInstance(o_cdf, maser.data.nancay.nda.routine.NDARoutineDataCDF)

    def test_dataset_name(self):
        self.assertEqual(o_cdf.name, "SRN/NDA Routine EDR CDF Dataset")

    def test_filedate(self):
        self.assertEqual(o_cdf.file_info['filedate'], "20160131")

    def test_len(self):
        self.assertEqual(len(o_cdf), 28734)

    def test_format(self):
        self.assertEqual(o_cdf.file_info['format'], 'CDF')

    def test_meridian(self):
        self.assertEqual(o_cdf.get_meridian_datetime(), datetime.datetime(2016, 1, 31, 2, 46))
        self.assertEqual(o_cdf.get_meridian_time(), datetime.time(2, 46))

    def test_get_single_sweep(self):
        sweep = o_cdf.get_single_sweep(0)
        self.assertIsInstance(sweep, maser.data.nancay.nda.routine.NDARoutineSweepCDF)

    def test_get_freq_axis(self):
        f = o_cdf.get_freq_axis()
        self.assertEqual(len(f), 400)
        self.assertEqual(f[0], 10)
        self.assertEqual(f[-1], 39.92499923706055)

    def test_get_time_axis(self):
        t = o_cdf.get_time_axis()
        self.assertEqual(len(t), 28734)
        self.assertEqual(t[0], datetime.datetime(2016, 1, 30, 22, 47, 6, 30000))
        self.assertEqual(t[-1], datetime.datetime(2016, 1, 31, 6, 45, 58, 680000))

    def test_get_first_sweep(self):
        sweep = o_cdf.get_first_sweep()
        self.assertEqual(sweep.index, 0)

    def test_get_last_sweep(self):
        sweep = o_cdf.get_last_sweep()
        self.assertEqual(sweep.index, 28733)

    def test_get_start_date(self):
        self.assertEqual(o_cdf.get_start_date(), datetime.date(2016, 1, 30))


class NancayNDARoutineSweepRT1Class(unittest.TestCase):

    """Test case for NDARoutineSweep class"""

    def test_polar(self):
        sweep = maser.data.nancay.nda.routine.NDARoutineSweepRT1(o_rt1, 0)
        self.assertEqual(sweep.data['polar'], 'LH')
        sweep = maser.data.nancay.nda.routine.NDARoutineSweepRT1(o_rt1, 1)
        self.assertEqual(sweep.data['polar'], 'RH')
        sweep = maser.data.nancay.nda.routine.NDARoutineSweepRT1(o_rt1, 1234)
        self.assertEqual(sweep.data['polar'], 'LH')
        sweep = maser.data.nancay.nda.routine.NDARoutineSweepRT1(o_rt1, 2345)
        self.assertEqual(sweep.data['polar'], 'RH')

    def test_load_data(self):
        sweep = maser.data.nancay.nda.routine.NDARoutineSweepRT1(o_rt1, 0, False)
        self.assertEqual(len(sweep.data['data']), 0)
        sweep.load_data()
        self.assertEqual(len(sweep.data['data']), 400)

    def test_get_data(self):
        sweep = maser.data.nancay.nda.routine.NDARoutineSweepRT1(o_rt1, 0)
        direct = sweep.data['data']
        method = sweep.get_data()
        self.assertEqual(direct, method)
        self.assertEqual(direct[0], 32)
        self.assertEqual(direct[399], 69)

    def test_get_data_in_db(self):
        sweep = maser.data.nancay.nda.routine.NDARoutineSweepRT1(o_rt1, 0)
        data = sweep.get_data_in_db()
        self.assertEqual(data[0], 10.0)

    def test_get_time(self):
        sweep = maser.data.nancay.nda.routine.NDARoutineSweepRT1(o_rt1, 0)
        self.assertEqual(sweep.get_time(), datetime.time(22, 47, 6, 30000))
        self.assertEqual(sweep.get_time().hour, sweep.data['hms']['hr'])
        self.assertEqual(sweep.get_time().minute, sweep.data['hms']['min'])
        self.assertEqual(sweep.get_time().second, sweep.data['hms']['sec'])
        self.assertEqual(sweep.get_time().microsecond, sweep.data['hms']['cs'] * 10000)

    def test_get_datetime(self):
        sweep = o_rt1.get_first_sweep()
        self.assertEqual(sweep.get_datetime(), datetime.datetime(2016, 1, 30, 22, 47, 6, 30000))
        sweep = o_rt1.get_last_sweep()
        self.assertEqual(sweep.get_datetime(), datetime.datetime(2016, 1, 31, 6, 45, 59, 680000))