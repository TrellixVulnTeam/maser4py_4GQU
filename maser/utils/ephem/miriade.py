#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Ephemeris module for maser-py package."""

# ________________ IMPORT _________________________
# (Include here the modules to import, e.g. import sys)

import re
import io
import zeep
import fortranformat
import astropy.io.votable

# ________________ HEADER _________________________

# Mandatory
__version__ = "0.10"
__author__ = "Baptiste Cecconi"
__date__ = "2017-Nov-25"

# Optional
__institute__ = "LESIA, Observatoire de Paris, CNRS, PSL Research University"
__project__ = "MASER"
__license__ = "GPLv3"
__credit__ = ["Baptiste Cecconi"]
__maintainer__ = "Baptiste Cecconi"
__email__ = "baptiste.cecconi@obspm.fr"
__change__ = {"0.10": "Initial Release"}

# ________________ Global Variables _____________
# (define here the global variables)
#logger = logging.getLogger(__name__)

# ________________ Class Definition __________
# (If required, define here classes)


class Miriade(object):
    """
    This class defines methods to access the miriad webservices at IMCCE
    """

    def __init__(self, webservice, request):
        self.wdsl = 'http://vo.imcce.fr/webservices/miriade/miriade.wsdl'
        self.client = zeep.Client(self.wdsl)
        self.webservice = webservice
        self.request = request
        self.response = self._get_client_response()
        self.meta = {}
        self.data = []
        self._extract_results()

    @classmethod
    def ephemph(cls, request):
        return Miriade('ephemph', request)

    @classmethod
    def ephemcc(cls, request):
        return Miriade('ephemcc', request)

    @classmethod
    def rts(cls, request):
        return Miriade('rts', request)

    def _get_client_response(self):

        if self.webservice == 'ephemph':
            return self.client.service.ephemph(self.request)
        elif self.webservice == 'ephemcc':
            return self.client.service.ephemcc(self.request)
        elif self.webservice == 'rts':
            return self.client.service.rts(self.request)
        else:
            raise Exception('wrong Miriade webservice name')

    def _extract_results(self):

        if self.request['mime'] == 'text':
            result = [item for item in self.response['result'].split(';')]

            tmp_data = []
            cur_index = -1
            start_index = 0
            for line in result:
                cur_index += 1
                if len(line) != 0:
                    if line[0] != '#':
                        if start_index == 0:
                            start_index = cur_index
                        tmp_data.append(line)
                    elif line.startswith("# >"):
                        tmp_line = line[4:].split(':')
                        self.meta[tmp_line[0].strip()] = tmp_line[1].strip()

            dat_reader = fortranformat.FortranRecordReader(self.meta['Data Format'])
            str_format = re.sub('\.[0-9]', '', self.meta['Data Format']).replace('E', 'A').replace('F', 'A')
            str_reader = fortranformat.FortranRecordReader(str_format)

            for line in tmp_data:
                self.data.append(dat_reader.read(line))

            header = str_reader.read(result[start_index-3])
            for i, val in enumerate(str_reader(result[start_index-2])):
                header[i] = ''.join([header[i], val])

        elif self.request['mime'] == 'votable':
            #fixing votable output:
            result = self.response['result']
            result = result.replace('eproc ', '')
            result = result.replace('time.epoch;meta.number', 'time.epoch')
            result = result.replace('toDate', 'J2017.01')
            result = result.replace('unit="-"', 'unit=""')
            result = result.replace('h:m:s', '')
            result = result.replace('d:m:s', '')
            result = result.replace('"1d"', '"1"')
            result = result.replace('ucd="pos.bodyrc"', '')
            f = io.BytesIO(result.encode())
            result = astropy.io.votable.parse(f)
            self.data = result.get_first_tables()
