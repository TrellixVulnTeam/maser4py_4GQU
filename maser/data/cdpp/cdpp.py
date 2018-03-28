#! /usr/bin/env python
# -*- coding: latin-1 -*-

"""
Python module to define classes for CDPP deep archive data (http://cdpp-archive.cnes.fr).
For more info on CCSDS time formats, refer to "TIME CODE FORMATS" CCSDS 301.0-B-3, Jan. 2002.
@author: B.Cecconi(LESIA)
"""

import datetime
import requests
import dateutil.parser
import time
import json
import os
import getpass
from maser.data.data import MaserDataFromFile, MaserError
import socket
hostname = socket.getfqdn()

__author__ = "Baptiste Cecconi"
__institute__ = "LESIA, Observatoire de Paris, PSL Research University, CNRS."
__date__ = "23-JAN-2018"
__version__ = "0.12"
__project__ = "MASER/CDPP"

__all__ = ["CDPPDataFromFile", "CDPPDataFromWebService"]


class CCSDSDate:

    def __init__(self, p_field, t_field):
        self.P_field = p_field
        self.T_field = t_field

        try:
            # decoding P_FIELD
            self.EXTENSION_FLAG = self.P_field & 1
            self.TIME_CODE_ID = int((self.P_field & 14)/2)

            # EXTENSION_FLAG = 0: 1 byte P_field
            # EXTENSION_FLAG = 1: 2 bytes P_field [NB: not sure it is used yet...]
            self.P_field_size = self.EXTENSION_FLAG+1

            # names of TIME_CODE_ID
            time_code_name_values = ["_UNK_", "CUC_LEVEL_1", "CUC_LEVEL_2", "_UNK_", "CDS", "CCS", "AGENCY_DEFINED",
                                     "_UNK_"]
            self.TIME_CODE_NAME = time_code_name_values[self.TIME_CODE_ID]

            if self.TIME_CODE_NAME == "CUC_LEVEL_1" or self.TIME_CODE_NAME == "CUC_LEVEL_2":

                self.N_BYTES_COARSE_TIME = int(((self.P_field & 48) / 16) + 1)
                self.N_BYTES_FINE_TIME = int((self.P_field & 192) / 64)
                self.N_BYTES_T_FIELD = self.N_BYTES_COARSE_TIME + self.N_BYTES_FINE_TIME
                self.TIME_SCALE = "TAI"

                if self.TIME_CODE_NAME == "CUC_LEVEL_1":
                    self.EPOCH_TYPE = "CCSDS"
                    self.TIME_EPOCH = datetime.date(1958, 1, 1)
                    self.datetime = self.decode_cuc_t()

            if self.TIME_CODE_NAME == "CUC_LEVEL_2":
                self.EPOCH_TYPE = "AGENCY_DEFINED"
                raise Exception('AGENCY_DEFINED epoch not implemented')

            if self.TIME_CODE_NAME == "CDS":

                if self.P_field & 16 == 0:
                    self.EPOCH_TYPE = "CCSDS"
                else:
                    self.EPOCH_TYPE = "AGENCY_DEFINED"
                    raise Exception('AGENCY_DEFINED epoch not implemented')

                self.N_BYTES_DAY = int(((self.P_field & 32) / 32) + 2)
                self.N_BYTES_MILLISECOND = 4
                self.N_BYTES_SUB_MILLISECOND = int((self.P_field & 192) / 32)
                self.N_BYTES_T_FIELD = self.N_BYTES_DAY + self.N_BYTES_MILLISECOND + self.N_BYTES_SUB_MILLISECOND
                self.TIME_SCALE = "UTC"

                self.datetime = self.decode_cds_t()

            if self.TIME_CODE_NAME == "CCS":

                self.EPOCH_TYPE = "N/A"
                self.CALENDAR_VARIATION_FLAG = (self.P_field & 16) / 16
                self.RESOLUTION = int((self.P_field & 224) / 32)
                self.N_BYTES_T_FIELD = 7 + self.RESOLUTION
                self.TIME_SCALE = "UTC"

                self.datetime = self.decode_ccs_t()

            if self.TIME_CODE_NAME == "AGENCY_DEFINED":

                self.EPOCH_TYPE = "AGENCY_DEFINED"
                self.N_BYTES_T_FIELD = ((self.P_field & 240) / 16) + 1
                raise Exception('AGENCY_DEFINED time_code not implemented')

        except Exception as e:
            e_message = e.args
            print("Error: {}".format(e_message))

    def decode_cuc_t(self):

        print("INFO: decoding CUC formatted date.")
        days = 0
        day_fraction_num = 0
        day_fraction_den = 2**(8*self.N_BYTES_FINE_TIME)

        for i in range(self.N_BYTES_COARSE_TIME):
            days = days + self.T_field[i]*2**(8*i)
        for i in range(self.N_BYTES_FINE_TIME):
            day_fraction_num = day_fraction_num + self.T_field[i+self.N_BYTES_COARSE_TIME]*2**(8*i)

        micro = int((day_fraction_num * 1e6) / day_fraction_den)

        if self.N_BYTES_FINE_TIME == 3:
            print("{}: {}".format("Warning", "Python datetime module doesn't handle sub-microsecond accuracy."))

        return self.TIME_EPOCH + datetime.timedelta(days=days) + datetime.timedelta(microseconds=micro)

    def decode_cds_t(self):

        print("INFO: decoding CDS formatted date.")
        days = 0
        for i in range(self.N_BYTES_DAY):
            days = days + self.T_field[i]*2**(8*i)

        milli = 0
        for i in range(4):
            milli = milli + self.T_field[i+self.N_BYTES_DAY]*2**(8*i)

        sub_milli = 0
        for i in range(self.N_BYTES_SUB_MILLISECOND):
            sub_milli = sub_milli + self.T_field[i+self.N_BYTES_DAY+4]*2**(8*i)

        if self.N_BYTES_SUB_MILLISECOND == 2:
            micro = sub_milli
        else:
            micro = int(sub_milli / 1e6)
            print("{}: {}".format("Warning", "Python datetime module doesn't handle sub-microsecond accuracy."))

        return self.TIME_EPOCH + datetime.timedelta(days=days) + datetime.timedelta(microseconds=micro)

    def decode_ccs_t(self):

        print("INFO: decoding CCS formatted date.")
        year = self.T_field[0] + self.T_field[1]*256
        if self.CALENDAR_VARIATION_FLAG:
            month = self.T_field[2]
            day = self.T_field[3]
        else:
            month = 1
            day = self.T_field[2] + self.T_field[3]*256
        hour = self.T_field[4]
        minute = self.T_field[5]
        second = self.T_field[6]

        sub_second = 0.
        for i in range(self.RESOLUTION):
            sub_second = self.T_field[7+i]/(100.*(i+1))

        micro = int(sub_second * 1e6)
        if self.RESOLUTION > 4:
            print("{}: {}".format("Warning", "Python datetime module doesn't handle sub-microsecond accuracy."))

        return datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second) \
            + datetime.timedelta(microseconds=micro)


class CDPPDataFromFile(MaserDataFromFile):

    def __init__(self, file, header, data, name):
        MaserDataFromFile.__init__(self, file)
        self.header = header
        self.data = data
        self.name = name

    def __len__(self):
        return len(self.data)

    def __getitem__(self, item):
        var_names = self.getvar_names()
        hdr_names = self.gethdr_names()
        if item in var_names:
            return self.getvar(item)
        elif item in hdr_names:
            return self.gethdr(item)
        elif item == "DATETIME":
            return self.get_datetime()
        else:
            print("Key {} not found.".format(item))
            return None

    def gethdr(self, hdr_name):
        """
        Method to retrieve the list of values for the select header item
        :return hdr: 
        """
        hdr_data = list()
        for cur_header in self.header:
            hdr_data.append(cur_header[hdr_name])
        return hdr_data

    def gethdr_names(self):
        """
        Method to retrieve the list of variable names
        :return: 
        """
        return self.header[0].keys()

    def getvar(self, var_name):
        """
        Method to retrieve the list of values for the select variable
        :return var: 
        """
        var_data = list()
        for cur_data in self.data:
            var_data.append(cur_data[var_name])
        return var_data

    def getvar_names(self):
        """
        Method to retrieve the list of variable names
        :return: 
        """
        cur_data = None
        for i in range(len(self)):
            cur_data = self.data[i]
            if cur_data is not None:
                break
        return cur_data.keys()

    def keys(self):
        return list(self.gethdr_names()) + ["DATETIME"] + list(self.getvar_names())

    def get_datetime(self):
        pass

    def get_datetime_ur8(self):
        """
        Method to retrieve the list of datetime per sweep (from UR8 format)
        :return dt: list of datetime
        """
        dt = list()
        for cur_header in self.header:
            ur8_day = int(cur_header['UR8_TIME'])
            ur8_micro = int((cur_header['UR8_TIME']-ur8_day)*86400e6)
            cur_date = datetime.datetime(1982, 1, 1) + \
                datetime.timedelta(days=ur8_day) + \
                datetime.timedelta(microseconds=ur8_micro)
            dt.append(cur_date)
        return dt

    def get_datetime_ccsds_cds(self):
        """
        Method to retrieve the list of datetime par sweep (from CCSDS-CDS format)
        :return dt: list of datetime 
        """
        dt = list()
        for cur_header in self.header:
            days = cur_header["CCSDS_JULIAN_DAY_B1"] * 2**16 + \
                   cur_header["CCSDS_JULIAN_DAY_B2"] * 2**8 + \
                   cur_header["CCSDS_JULIAN_DAY_B3"]
            milli = cur_header["CCSDS_MILLISECONDS_OF_DAY"]

            dt.append(datetime.datetime(1950, 1, 1) + datetime.timedelta(days=days) +
                      datetime.timedelta(milliseconds=milli))

        return dt

    def get_datetime_ccsds_ccs(self, prefix=None):
        """Method to retrieve the list of datetime par sweep (from CCSDS-CCS format)
        :param prefix: CCSDS_CCS key string prefix (default = None)
        :return dt: list of datetime
        """

        dt = list()
        if prefix is None:
            prefix_str = ""
        else:
            prefix_str = prefix

        for cur_header in self.header:
            dt.append(datetime.datetime(cur_header[prefix_str+"CCSDS_YEAR"], cur_header[prefix_str+"CCSDS_MONTH"],
                                        cur_header[prefix_str+"CCSDS_DAY"], cur_header[prefix_str+"CCSDS_HOUR"],
                                        cur_header[prefix_str+"CCSDS_MINUTE"], cur_header[prefix_str+"CCSDS_SECOND"],
                                        int(cur_header[prefix_str+"CCSDS_SECOND_E_2"] * 1e4) +
                                        int(cur_header[prefix_str+"CCSDS_SECOND_E_4"] * 1e2)))

        return dt

    def get_epncore_meta(self):

        md = MaserDataFromFile.get_epncore_meta(self)

        md["granule_uid"] = "{}_{}".format(self.name.lower(), self.file.lower())
        md["granule_gid"] = self.name.lower()
        md["obs_id"] = self.file.lower()
        md["dataproduct_type"] = "ds"
        md["target_name"] = "Sun#Earth#Jupiter"
        md["target_class"] = "star#planet"
        md["time_min"] = self["DATETIME"][0]
        md["time_min"] = self["DATETIME"][-1]
        md["time_sampling_step_min"] = None
        md["time_sampling_step_max"] = None
        md["time_exp_min"] = None
        md["time_exp_max"] = None
        md["spectral_range_min"] = None
        md["spectral_range_max"] = None
        md["spectral_sampling_step_min"] = None
        md["spectral_sampling_step_max"] = None
        md["spectral_resolution_min"] = None
        md["spectral_resolution_max"] = None
        md["c1min"] = None
        md["c1max"] = None
        md["c2min"] = None
        md["c2max"] = None
        md["c3min"] = None
        md["c3max"] = None
        md["s_region"] = None
        md["c1_resol_min"] = None
        md["c1_resol_max"] = None
        md["c2_resol_min"] = None
        md["c2_resol_max"] = None
        md["c3_resol_min"] = None
        md["c3_resol_max"] = None
        md["spatial_frame_type"] = None
        md["incidence_min"] = None
        md["incidence_max"] = None
        md["emergence_min"] = None
        md["emergence_max"] = None
        md["phase_min"] = None
        md["phase_max"] = None
        md["instrument_host_name"] = self.name.split('_')[0]
        md["instrument_name"] = self.name.split('_')[1]
        md["measurement_type"] = "phys.flux.density;em.radio"
        md["processing_level"] = None
        md["creation_date"] = None
        md["modification_date"] = None
        md["release_date"] = datetime.datetime.now()
        md["service_title"] = "maser-cdpp"
        md["access_url"] = None
        md["access_format"] = None
        md["access_estsize"] = None
        md["access_md5"] = None
        md["thumbnail_url"] = None
        md["file_name"] = self.file
        md["species"] = None
        md["target_region"] = None
        md["feature_name"] = None
        md["bib_reference"] = None
        md["time_scale"] = "SCET"
        md["time_origin"] = md["instrument_host_name"]

        return md


class CDPPWebService:
    """
    This module implements methods to connect to the CDPP webservices.
    """

    def __init__(self, cdpp_host="https://cdpp-archive.cnes.fr"):
        """
        Init method setting up attribute of the CDPPWebService object
        :param cdpp_host: CDPP web service host to connect to (default = "https://cdpp-archive.cnes.fr")
        """
        self.cdpp_host = cdpp_host
        self.auth_data = {}
        self.auth_token = {}
        self.auth_token_expire = datetime.datetime.now()

    def connect(self, user="cecconi", password=None):
        """
        Connection to CDPP webservice, in order to get a valid authentication token.
        :param user: valid CDPP web service user
        :param password: corresponding password
        """
        if password is None:
            password = getpass.getpass()
        self.auth_data = {"user": user, "password": password}
        self.auth_token = self._get_auth_token()
        self.auth_token_expire = datetime.datetime.now() + datetime.timedelta(seconds=self.auth_token['expires_in'])

    def close(self):
        """
        Close current connection.
        NB: The authentication token is still valid (up to 2 hrs after it was issued), but its values are deleted
        from the object. The connection is thus impossible.
        """
        self.auth_data = {}
        self.auth_token = {}
        self.auth_token_expire = datetime.datetime.now()

    def _check_reconnect(self):
        """
        Private method to check authentication token expire date.
        If less than 5 seconds remaining, renew it.
        """
        if (datetime.datetime.now() - self.auth_token_expire).total_seconds() > -5:
            print("Reconnecting")
            self.connect(self.auth_data['user'], self.auth_data['password'])

    def _get_auth_token(self):
        """
        Private method to get authentication token from auth_data USER and PASSWORD elements.
        """
        cdpp_auth_url = "{}/userauthenticate-rest/oauth/token".format(self.cdpp_host)
        cdpp_auth_data = "client_id=ria&client_secret=123456789&grant_type=password&username={}&password={}&scope=cdpp"\
            .format(self.auth_data['user'], self.auth_data['password']).encode('ascii')
        cdpp_auth_header = {'Content-type': 'application/x-www-form-urlencoded'}
        with requests.post(cdpp_auth_url, cdpp_auth_data, headers=cdpp_auth_header) as req:
            return json.loads(req.text)

    def _http_request_get(self, rest_url, headers=None):
        """
        Private wrapper method to build an http GET query (from requests.get module).
        The methods checks the authentication token and adds the corresponding header.
        :param rest_url: URL to query
        :param headers: extra headers (other than authentication token)
        :return: the results of the query, as a list.
        """
        if headers is None:
            headers = dict()
        headers["Authorization"] = "Bearer {}".format(self.auth_token["access_token"])
        self._check_reconnect()
        with requests.get(rest_url, headers=headers) as req:
            res = json.loads(req.text)
            return res['results']

    def _http_request_post(self, rest_url, post_data, headers=None):
        """
        Private wrapper method to build an http POST query (from requests.post module).
        The methods checks the authentication token and adds the corresponding header.
        :param rest_url: URL to query
        :param headers: extra headers (other than authentication token)
        :return: the results of the query, as a list.
        """
        if headers is None:
            headers = dict()
        headers["Authorization"] = "Bearer {}".format(self.auth_token["access_token"])
        self._check_reconnect()
        with requests.post(rest_url, post_data, headers=headers) as req:
            res = json.loads(req.text)
            return res['results']

    def get_missions(self):
        """
        Get the list of missions available through the CDPP web service.
        :return: list of mission names
        """
        cdpp_missions_rest = "{}/cdpp-rest/cdpp/cdpp/missions".format(self.cdpp_host)
        return self._http_request_get(cdpp_missions_rest)

    def get_instruments(self, mission_name):
        """
        Get the list of instruments (and associated metadata) for a given mission.
        :param mission_name: name of the mission
        :return: list of instruments
        """
        cdpp_instruments_rest = "{}/cdpp-rest/cdpp/cdpp/missions/{}/instruments".format(self.cdpp_host, mission_name)
        return self._http_request_get(cdpp_instruments_rest)

    def get_datasets(self, mission_name, instrument_name):
        """
        Get the list of datasets (and associated metadata) for a given instrument and mission
        :param mission_name: Name of mission
        :param instrument_name: Name of instrument
        :return: list of datasets
        """
        cdpp_datasets_rest = "{}/cdpp-rest/cdpp/cdpp/datasets?mission={}&instrument={}"\
            .format(self.cdpp_host, mission_name, instrument_name)
        return self._http_request_get(cdpp_datasets_rest)

    def get_files(self, dataset_name):
        """
        Get the list of files (and associated metadata) for a given dataset
        :param dataset_name: Name of dataset
        :return: list of files including start and stop times.
        """
        cdpp_header = {"Content-Type": "application/json"}
        cdpp_files_url = "{}/consultation-rest/cdpp/consultation/search/entities".format(self.cdpp_host)
        cdpp_files_data = dict([("targetList", []), ("startPosition", 1), ("paginatedEntity", "OBJECT"),
                                ("paginatedEntityType", "DATA"), ("visibility",  "IDENTIFIER"),
                                ("objectVisibility", "STANDARD"), ("returnSum", True), ("collectionDeepSearch", False),
                                ("startNode", {"entity": {"type":"DATASET", "id":dataset_name}}), ("sort", None),
                                ("sortField", None)])
        cdpp_files_result = self._http_request_post(cdpp_files_url, json.dumps(cdpp_files_data), headers=cdpp_header)
        cdpp_files = []
        for item in cdpp_files_result[0]['objectLst']:
            cur_name = item['id']['id']
            cur_start = datetime.datetime.fromtimestamp(item['startDateAsLong']//1000) \
                        + datetime.timedelta(milliseconds=item['startDateAsLong']%1000)
            cur_stop = datetime.datetime.fromtimestamp(item['stopDateAsLong']//1000) \
                       + datetime.timedelta(milliseconds=item['stopDateAsLong']%1000)
            cdpp_files.append({"name": cur_name, "start_time": cur_start, "stop_time": cur_stop})
        return cdpp_files

    def download_files_async(self, start_date, stop_date, dataset_name, dir_out='.'):
        """
        Download files for a dataset and a time interval, using async method (using order and workspace)
        :param start_date: Start time
        :param stop_date: Stop time
        :param dataset_name: Name of dataset
        :param dir_out: Output directory (default is current directory)
        """
        cdpp_command_async = "{}/cdpp-rest/cdpp/cdpp/datasets/{}/files?startdate={}&stopdate={}"\
            .format(self.cdpp_host, dataset_name, start_date.isoformat(), stop_date.isoformat())
        order_id = self._http_request_get(cdpp_command_async)
        cdpp_order_status = "{}/command-rest/cdpp/command/orders/{}/status".format(self.cdpp_host, order_id)
        while True:
            order_status = self._http_request_get(cdpp_order_status)
            if order_status == "TERMINATED_OK":
                break
            elif order_status.endswith("_CANCELLED") or order_status.endswith("_FAILED") or order_status == "DELETED":
                raise MaserError("CDPP REST interface: ORDER status = {}".format(order_status))
            time.sleep(0.5)
        cdpp_order_result = "{}/userworkspace-rest/cdpp/userworkspace/orders/{}/files"\
            .format(self.cdpp_host, order_id)
        order_files = self._http_request_get(cdpp_order_result)
        for item in order_files:
            cdpp_order_file = "{}/userworkspace-rest/download/cdpp/userworkspace/file/{}/{}/?access_token={}"\
                .format(self.cdpp_host, self.auth_data['user'], item, self.auth_token['access_token'])
            order_basename = item.split['/'][-1]
            self._check_reconnect()
            with requests.get(cdpp_order_file) as r, open(os.path.join(dir_out, order_basename), 'wb') as f:
                f.write(r.content)
        return order_files

    def download_file_sync(self, file_name, dir_out):
        """
        Download a single file, using sync method (for staged dataset only)
        :param file_name: Name of file
        :param dir_out: Output directory (default is current directory)
        """
        self._check_reconnect()
        cdpp_command_url = "{}/command-rest/download/cdpp/command/data/object/{}?access_token={}"\
            .format(self.cdpp_host, file_name, self.auth_token["access_token"])
        with requests.get(cdpp_command_url) as r, open(os.path.join(dir_out, file_name), 'wb') as f:
            f.write(r.content)


class CDPPFileFromWebService:

    def __init__(self):
        self.dataset_name = ''
        self.mission_name = ''
        self.instrument_name = ''
        pass

    def _get_download_directory(self):
        if hostname == 'macbookbc.obspm.fr':
            download_rootdir = "/Users/baptiste/Projets/CDPP/Archivage/_Downloads"
        elif hostname == 'voparis-keke.obspm.fr':
            download_rootdir = "/usr/local/das2srv/data/CDPP"
        elif hostname == 'voparis-maser-das.obspm.fr':
            download_rootdir = "/cache/cdpp-data"
        else:
            download_rootdir = '.'

        download_dir = os.path.join(download_rootdir, self.mission_name)
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)

        download_dir = os.path.join(download_dir, self.instrument_name)
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)

        download_dir = os.path.join(download_dir, self.dataset_name)
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)

        return download_dir


class CDPPFileFromWebServiceSync(CDPPFileFromWebService):

    _staged_datasets = {'DA_TC_INT_AUR_POLRAD_RSP': {'mission': 'INTERBALL', 'instrument': 'POLRAD'},
                        'DA_TC_DMT_N1_1134': {'mission': 'Demeter', 'instrument': ''},
                        'DA_TC_VIKING_V4_DATA': {'mission': '', 'instrument': ''},
                        'DA_TC_ISEE3_ICE_RADIO_3D_SOURCES': {'mission': '', 'instrument': ''}}

    def __init__(self, file_name, dataset_name, user, password, check_file=True):

        CDPPFileFromWebService.__init__(self)
        self.dataset_name = dataset_name

        if dataset_name in self._staged_datasets.keys():
            self.mission_name = self._staged_datasets[self.dataset_name]['mission']
            self.instrument_name = self._staged_datasets[self.dataset_name]['instrument']
        else:
            raise MaserError("Dataset not staged, use Asynchronous method for downloading this file")

        c = CDPPWebService()
        c.connect(user, password)

        if check_file:
            all_file_info = c.get_files(dataset_name)
            if file_name not in [item['name'] for item in all_file_info]:
                raise MaserError("File not existing for the selected dataset")

        download_dir = self._get_download_directory()
        c.download_file_sync(file_name, download_dir)
        self.file = os.path.join(download_dir, file_name)


class CDPPFileFromWebServiceAsync(CDPPFileFromWebService):

    def __init__(self, start_date, stop_date, dataset_name):

        CDPPFileFromWebService.__init__(self)
        c = CDPPWebService()
        c.connect()
        download_dir = self._get_download_directory()
        self.file = c.download_files_async(start_date, stop_date, dataset_name, download_dir)

