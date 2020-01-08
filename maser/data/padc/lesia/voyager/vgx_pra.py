#! /usr/bin/env python
# -*- coding: latin-1 -*-

"""
Python module to read a Voyager/PRA data file from LESIA datasets (recovered from CNES/SERAD archive).
@author: B.Cecconi(LESIA)
"""

import os
import struct
from maser.data.classes import MaserError
from maser.data.classes import MaserDataFromFile
from maser.data.classes import MaserDataFromInterval
import datetime
import numpy
import hashlib
import collections.abc

__author__ = "Baptiste Cecconi"
__date__ = "05-FEB-2017"
__version__ = "0.01"

__all__ = [""]


class VoyagerPRALevel(object):

    def __init__(self, level: str, sublevel='', verbose=False, debug=False):
        self.name = level
        self.sublevel = sublevel
        self.implemented = True
        self.record_def = dict()
        self.verbose = verbose
        self.debug = debug
        if self.name == '':
            self.file_format = None
            self.implemented = False
            self.description = "Dummy empty level"
            self.depends = None
        elif self.name == 'band':
            self.file_format = 'bin-compressed'
            self.implemented = False
            self.description = "Voyager/PRA EDR bands (Telemetry)"
            self.depends = [None]

#        elif self.name == 'n1':
#            self.file_format = 'bin-fixed-record-length'
#            self.implemented = True
#            self.record_def['fields'] = ["band", "bloc", "date", "iso_yr", "iso_mon", "iso_day", "iso_hr", "iso_min",
#                                         "iso_sec", "iso_usec", "status_0", "status_1", "status_p", "config_p",
#                                         "mode_p", "intensity", "polar"]
#            self.record_def['dtype'] = "<LLLLhbbbbbbhh"
#            self.record_def['np_dtype'] = [('band', '<i1'), ('bloc', '<i2'),
#                                           ('date', '<f8'), ('iso_time',
#                                                             (('year', '<i2'), ('month', 'u1'), ('day', 'u1'),
#                                                              ('minute', 'u1'), ('second', 'u1'), ('microsecond', 'u4'))),
#                                           ('status', ('<u2', '<u2')), ('status_pred', '<u2'), ('mode_pred', '<u2'),
#                                           ('intensity', ('<'+198*'i2'), ('agc2', 'u1'), ('auto1', 'u1'), ('auto2', 'u1'),
#                                           ('cross1', '<i2'), ('cross2', '<i2')]
#            self.record_def['length'] = struct.calcsize(self.record_def['dtype'])  # = 28
#            self.description = "Cassini/RPWS/HFR Level 1 (Receiver units)"
#            self.depends = [None]
#
#
#band:0, bloc:0, date:0.0d, iso_date:{iso_time}, $
#              status:intarr(2), status_pred:0, $
#              config_pred:0, mode_pred:0, intensity:intarr(198), $
#              polar: intarr(198)
#year:0, month:0b, day:0b, hour:0b, minute:0b, second:0b, microsecond:0l
#
#
#class VoyagerPRAData(MaserDataFromFile):
#
#    def __init__(self, file, start_time=None, end_time=None, input_level=CassiniKronosLevel(''),
#                 verbose=False, debug=False):