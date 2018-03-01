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

    def get_epncore(self):

        md = MaserDataFromFile.get_epncore(self)

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


class CDPPDataFromWebService(CDPPDataFromFile):

    def __init__(self, user, password, start_date=None, stop_date=None,
                 mission_name=None, instrument_name=None, dataset_name=None):
        self.mission_name = mission_name
        self.instrument_name = instrument_name
        self.dataset_name = dataset_name
        self.start_time = dateutil.parser.parse(start_date)
        self.stop_time = datetime.datetime.strptime(stop_date)

        self.auth = {"user": user, "password": password}
        self.auth_token = {}
        self.get_auth_token()

        if hostname == 'macbookbc.obspm.fr':
            self.download_dir = "/Users/baptiste/Projets/CDPP/Archivage/_Downloads/{}/{}/{}"\
                .format(mission_name, instrument_name, dataset_name)
        elif hostname == 'voparis-maser-das.obspm.fr':
            self.download_dir = "/cache/cdpp-data/{}/{}/{}".format(mission_name, instrument_name, dataset_name)

        self.cdpp_host = "https://cdpp-archive.cnes.fr"
        self.header = {}
        self.data = {}
        self.name = ""

        CDPPDataFromFile.__init__(self, self.file, self.header, self.data, self.name)

    def get_auth_token(self):

        cdpp_auth_url = "{}/userauthenticate-rest/oauth/token".format(self.cdpp_host)
        cdpp_auth_data = "client_id=ria&client_secret=123456789&grant_type=password&username={}&password={}"\
            .format(self.auth['user'], self.auth['password']).encode('ascii')
        cdpp_auth_header = {'Content-type': 'application/x-www-form-urlencoded'}
        with requests.post(cdpp_auth_url, cdpp_auth_data, headers=cdpp_auth_header) as r:
            self.auth_token = json.loads(r.text)

    def get_instruments(self, mission_name):

        cdpp_header_auth = {"Authorization": "Bearer {}".format(self.auth_token["access_token"])}
        cdpp_instruments_rest = "{}/cdpp-rest/cdpp/cdpp/missions/{}/instruments".format(self.cdpp_host, mission_name)
        with requests.get(cdpp_instruments_rest, headers=cdpp_header_auth) as r:
            return json.loads(r.text)

    def get_datasets(self, mission_name, instrument_name):

        cdpp_header_auth = {"Authorization": "Bearer {}".format(self.auth_token["access_token"])}
        cdpp_datasets_rest = "{}/cdpp-rest/cdpp/cdpp/datasets?mission={}&instrument={}"\
            .format(self.cdpp_host, mission_name, instrument_name)
        with requests.get(cdpp_datasets_rest, headers=cdpp_header_auth) as r:
            return json.loads(r.text)

    def get_files_async(self, start_date, stop_date, dataset_name):

        cdpp_header_auth = {"Authorization": "Bearer {}".format(self.auth_token["access_token"])}
        cdpp_command_async = "{}/cdpp-rest/cdpp/cdpp/datasets/{}/files?startdate={}&stopdate={}"\
            .format(self.cdpp_host, dataset_name, start_date.isoformat(), stop_date.isoformat())
        with requests.get(cdpp_command_async, headers=cdpp_header_auth) as r:
            rr = json.loads(r.text)
            order_id = rr["results"]

        cdpp_order_status = "{}/command-rest/cdpp/command/orders/{}/status".format(self.cdpp_host, order_id)
        while True:
            with requests.get(cdpp_order_status, headers=cdpp_header_auth) as r:
                rr = json.loads(r.text)
                order_status = rr["results"]
                if order_status == "TERMINATED_OK":
                    break
                elif order_status.endswith("_CANCELLED") \
                        or order_status.endswith("_FAILED") \
                        or order_status == "DELETED":
                    raise MaserError("CDPP REST interface: ORDER status = {}".format(order_status))
            time.sleep(0.5)

        cdpp_order_result = "{}/userworkspace-rest/cdpp/userworkspace/orders/{}/files"\
            .format(self.cdpp_host, order_id)
        with requests.get(cdpp_order_result, headers=cdpp_header_auth):
            rr = json.loads(r.text)
            order_files = rr["results"]
            for item in order_files:
                cdpp_order_file = "{}/userworkspace-rest/download/cdpp/userworkspace/file/{}/{}/?access_token={}"\
                    .format(self.cdpp_host, self.auth['user'], item, self.auth_token['access_token'])
                order_basename = item.split['/'][-1]
                with requests.get(cdpp_order_file) as r, open(os.path.join(self.download_dir, order_basename), 'wb') as f:
                    f.write(r.content)

    def download_file_sync(self):

        file_name = self.file
        cdpp_command_url = "{}/command-rest/download/cdpp/command/data/object/{}?access_token={}"\
            .format(self.cdpp_host, file_name, self.auth_token["access_token"])
        with requests.get(cdpp_command_url) as r, open(os.path.join(self.download_dir, file_name), 'wb') as f:
            f.write(r.content)
