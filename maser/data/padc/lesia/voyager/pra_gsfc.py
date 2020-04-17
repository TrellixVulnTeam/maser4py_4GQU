#! /usr/bin/env python
# -*- coding: latin-1 -*-

"""
Python module to read a Voyager/PRA data file from MLK@GSFC datasets (stored by MASER).
@author: B.Cecconi(LESIA)
"""

import os
import struct
from maser.data.classes import MaserError
from maser.data.classes import MaserDataSweep
from maser.data.classes import MaserDataFromFileText
from maser.data.pds.voyager.pra import PDSPPIVoyagerPRARDRLowBand6SecSweep, PDSPPIVoyagerPRADataObject
from astropy.units import Unit
import datetime
import numpy
import logging
_module_logger = logging.getLogger('maser.data.padc.lesia.voyager.pra_gsfc')

__author__ = "Baptiste Cecconi"
__date__ = "17-APR-2020"
__version__ = "0.01"

__all__ = ["load_voyager_pra_gsfc_lowband_6sec"]

VOYAGER_PRA_GSFC_TXT_FILE_COLUMN_WIDTHS = [4, 2, 2, 6] + [4] * 71 * 8
VOYAGER_PRA_GSFC_TXT_FILE_NUMPY_DTYPE = numpy.int
VOYAGER_PRA_FREQUENCY_LIST = numpy.arange(1326, -18, -19.2) * Unit('kHz')


def _expand_rows(array):
    return numpy.tile(array, (8,)).reshape((8, len(array))).transpose().flatten()


class GSFCVoyagerPRARDRLowBand6SecSweep(PDSPPIVoyagerPRARDRLowBand6SecSweep, MaserDataSweep):

    def __init__(self, parent, index=0):
        self.logger = logging.getLogger('maser.data.padc.lesia.voyager.pra_gsfc.GSFCVoyagerPRARDRLowBand6SecSweep')
        MaserDataSweep.__init__(self, parent, index, parent.verbose, parent.debug)
        self._cur_row, self._cur_swp = self.parent._split_index(index)
        self.raw_sweep = self.parent.get_raw_sweep(self.index)
        self.status = self.raw_sweep[0]
        polar_indices = self._get_polar_indices()
        self.data = {}
        self.freq = {}
        for item in ['R', 'L']:
            self.data[item] = self.raw_sweep[1:][polar_indices[item]]
            self.freq[item] = self.parent.frequency[polar_indices[item]]
        self.freq['avg'] = (self.freq['R']+self.freq['L'])/2
        self.attenuator = self._get_attenuator_value()
        self.type = self._get_sweep_type()


class GSFCVoyagerPRAData(MaserDataFromFileText):

    def __init__(self, file, verbose=False, debug=False):
        MaserDataFromFileText.__init__(self, file, verbose, debug)
        self._data = self.load_data()
        self.frequency = self._get_freq_axis()
        self.time = self._get_time_axis()

    def load_data(self):
        return numpy.genfromtxt(
            self.file,
            dtype=VOYAGER_PRA_GSFC_TXT_FILE_NUMPY_DTYPE,
            delimiter=VOYAGER_PRA_GSFC_TXT_FILE_COLUMN_WIDTHS
        )

    def get_raw_sweep(self, index):
        cur_row, cur_swp = self._split_index(index)
        return self._data[cur_row, 4+cur_swp*71:4+(cur_swp+1)*71]

    def get_single_sweep(self, index=0, **kwargs):
        return GSFCVoyagerPRARDRLowBand6SecSweep(self, index)

    @staticmethod
    def _split_index(index):
        return index // 8, index % 8

    def get_row(self, row_index):
        return self._data[row_index]

    @staticmethod
    def _get_freq_axis():
        return VOYAGER_PRA_FREQUENCY_LIST

    def get_freq_axis(self, unit="kHz"):
        return self._get_freq_axis().to(unit)

    @property
    def _nrows(self):
        return len(self._data)

    def _seconds_of_day(self):
        sec_start_row = _expand_rows(self._data[:,3])
        sec_row_sweep = numpy.tile(numpy.arange(8)*6, (self._nrows,))
        return sec_start_row + sec_row_sweep

    def get_single_datetime(self, index):
        return self.time[index]

    def _get_time_axis(self):
        to_datetime = numpy.vectorize(
            lambda y, m, d:
            datetime.datetime(year=y, month=m, day=d)
        )
        seconds_to_timedelta = numpy.vectorize(
            lambda s: datetime.timedelta(seconds=float(s))
        )
        dates = _expand_rows(to_datetime(self._data[:, 0], self._data[:, 1], self._data[:, 2]))
        seconds = seconds_to_timedelta(self._seconds_of_day())
        return dates+seconds

    def __repr__(self):
        return f'<Voyager-PRA (GSFC) LowBand 6sec ({self.get_file_name()})>'


def load_voyager_pra_gsfc_lowband_6sec(file):
    return GSFCVoyagerPRAData(file)