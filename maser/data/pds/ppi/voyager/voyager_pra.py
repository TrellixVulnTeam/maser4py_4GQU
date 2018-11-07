#! /usr/bin/env python
# -*- coding: latin-1 -*-

"""
Python module to work with PDS-PPI/Voyager/PRA data
@author: B.Cecconi(LESIA)
"""

from maser.data.pds.pds import PDSDataFromLabel
import numpy
import datetime

__author__ = "Baptiste Cecconi"
__copyright__ = "Copyright 2017, LESIA-PADC, Observatoire de Paris"
__credits__ = ["Baptiste Cecconi", "Laurent Lamy"]
__license__ = "GPLv3"
__version__ = "0.0b0"
__maintainer__ = "Baptiste Cecconi"
__email__ = "baptiste.cecconi@obspm.fr"
__status__ = "Development"
__date__ = "19-FEB-2017"
__project__ = "MASER/Voyager/PRA"

__ALL__ = ['load_voyager_rdr_low_band_6sec_data']


class VoyagerRDRLowBand6SecDataFromLabel(PDSDataFromLabel):

    def __init__(self, file, verbose=False, debug=False):
        PDSDataFromLabel.__init__(self, file, verbose=verbose, debug=debug)
        self.table = self[0]
        # TODO: split status word from data => extra column and update of SWEEPn columns
        # TODO: build polar index columns (POLARn = same shape as SWEEPn) (R=0, L=1)
        self.frequency = numpy.arange(1326, 1.2, 71)

    def _split_index(self, index):
        if index < 0:
            index += self.table.n_rows * 8
        return index // 8, index % 8

    def get_single_datetime(self, index):
        cur_row, cur_swp = self._split_index(index)
        yy = (self.table.data['DATE'][cur_row] // 10000) + 1900
        if yy < 70:
            yy += 100
        mm = (self.table.data['DATE'][cur_row] % 10000) // 100
        dd = self.table.data['DATE'][cur_row] % 100
        sec = self.table.data['SECOND'][cur_row] + 6 * cur_swp + 3.9

        return datetime.datetime(yy, mm, dd, 0, 0, 0) + datetime.timedelta(seconds=sec)

    def get_frequency(self):
        return self.frequency

    def get_single_sweep(self, index):
        cur_row, cur_swp = self._split_index(index)
        result = dict()
        result['data'] = self.table.data['SWEEP{}'.format(cur_swp)][cur_row]
        # result['polar'] = self.table.data['POLAR{}'.format(cur_swp)][cur_row]
        # result['status'] = self.table.data['STATUS'.format(cur_swp)][cur_row]
        result['datetime'] = self.get_single_datetime(index)
        return result


def load_voyager_rdr_low_band_6sec_data(file, verbose=False, debug=False):
    o = VoyagerRDRLowBand6SecDataFromLabel(file, verbose=verbose, debug=debug)
    return o
