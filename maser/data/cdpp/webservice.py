#! /usr/bin/env python
# -*- coding: latin-1 -*-

"""
Python module to define classes for CDPP deep archive data (http://cdpp-archive.cnes.fr).
@author: B.Cecconi(LESIA)
"""

__author__ = "Baptiste Cecconi"
__institute__ = "LESIA, Observatoire de Paris, PSL Research University, CNRS."
__date__ = "29-May-2020"
__version__ = "0.13"
__project__ = "MASER/CDPP"

__all__ = ["CDPPWebService", "CDPPFileFromWebService", "CDPPFileFromWebServiceSync",
           "CDPPFileFromWebServiceAsync"]

import requests
import datetime
import time
import json
import os
import filecmp
import getpass
from .. import MaserError

import socket
hostname = socket.getfqdn()


class CDPPWebService:
    """
    This module implements methods to connect to the CDPP webservices.
    """

    def __init__(self, cdpp_host="https://cdpp-archive.cnes.fr", debug=False, verbose=False):
        """
        Init method setting up attribute of the CDPPWebService object
        :param cdpp_host: CDPP web service host to connect to (default = "https://cdpp-archive.cnes.fr")
        """
        if debug:
            print("This is {}.__init__()".format(__class__.__name__))

        self.debug = debug
        self.verbose = verbose
        self.cdpp_host = cdpp_host
        self.auth_data = {}
        self.auth_token = {}
        self.auth_token_expire = datetime.datetime.now()
        self.file = {}

    def connect(self, user=None, password=None):
        """
        Connection to CDPP webservice, in order to get a valid authentication token.
        :param user: valid CDPP web service user
        :param password: corresponding password
        """
        if self.debug:
            print("This is {}.connect()".format(__class__.__name__))

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
        if self.debug:
            print("This is {}.close()".format(__class__.__name__))
        self.auth_data = {}
        self.auth_token = {}
        self.auth_token_expire = datetime.datetime.now()

    def _check_reconnect(self):
        """
        Private method to check authentication token expire date.
        If less than 5 seconds remaining, renew it.
        """
        if self.debug:
            print("This is {}._check_reconnect()".format(__class__.__name__))
        if (datetime.datetime.now() - self.auth_token_expire).total_seconds() > -5:
            print("Reconnecting")
            self.connect(self.auth_data['user'], self.auth_data['password'])

    def _get_auth_token(self):
        """
        Private method to get authentication token from auth_data USER and PASSWORD elements.
        """
        if self.debug:
            print("This is {}._get_auth_token()".format(__class__.__name__))
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
        if self.debug:
            print("This is {}._http_request_get()".format(__class__.__name__))
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
        if self.debug:
            print("This is {}._http_request_post()".format(__class__.__name__))
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
        if self.debug:
            print("This is {}.get_missions()".format(__class__.__name__))
        cdpp_missions_rest = "{}/cdpp-rest/cdpp/cdpp/missions".format(self.cdpp_host)
        return self._http_request_get(cdpp_missions_rest)

    def get_instruments(self, mission_name):
        """
        Get the list of instruments (and associated metadata) for a given mission.
        :param mission_name: name of the mission
        :return: list of instruments
        """
        if self.debug:
            print("This is {}.get_instruments()".format(__class__.__name__))
        cdpp_instruments_rest = "{}/cdpp-rest/cdpp/cdpp/missions/{}/instruments".format(self.cdpp_host, mission_name)
        return self._http_request_get(cdpp_instruments_rest)

    def get_datasets(self, mission_name, instrument_name):
        """
        Get the list of datasets (and associated metadata) for a given instrument and mission
        :param mission_name: Name of mission
        :param instrument_name: Name of instrument
        :return: list of datasets
        """
        if self.debug:
            print("This is {}.get_datasets()".format(__class__.__name__))
        cdpp_datasets_rest = "{}/cdpp-rest/cdpp/cdpp/datasets?mission={}&instrument={}"\
            .format(self.cdpp_host, mission_name, instrument_name)
        return self._http_request_get(cdpp_datasets_rest)

    def get_files(self, dataset_name):
        """
        Get the list of files (and associated metadata) for a given dataset
        :param dataset_name: Name of dataset
        :return: list of files including start and stop times.
        """
        if self.debug:
            print("This is {}.get_files()".format(__class__.__name__))
        cdpp_header = {"Content-Type": "application/json"}
        cdpp_files_url = "{}/consultation-rest/cdpp/consultation/search/entities".format(self.cdpp_host)
        cdpp_files_data = dict([("targetList", []), ("startPosition", 1), ("paginatedEntity", "OBJECT"),
                                ("paginatedEntityType", "DATA"), ("visibility",  "IDENTIFIER"),
                                ("objectVisibility", "STANDARD"), ("returnSum", True), ("collectionDeepSearch", False),
                                ("startNode", {"entity": {"type": "DATASET", "id": dataset_name}}), ("sort", None),
                                ("sortField", None)])
        cdpp_files_result = self._http_request_post(cdpp_files_url, json.dumps(cdpp_files_data), headers=cdpp_header)
        cdpp_files = []
        for item in cdpp_files_result[0]['objectLst']:
            cur_name = item['id']['id']
            cur_start = \
                datetime.datetime.fromtimestamp(item['startDateAsLong'] // 1000) + \
                datetime.timedelta(milliseconds=item['startDateAsLong'] % 1000)
            cur_stop = \
                datetime.datetime.fromtimestamp(item['stopDateAsLong'] // 1000) + \
                datetime.timedelta(milliseconds=item['stopDateAsLong'] % 1000)
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
        if self.debug:
            print("This is {}.download_files_async()".format(__class__.__name__))
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
            order_basename = item.split('/')[-1]
            self._check_reconnect()
            self.file['name'] = os.path.join(dir_out, order_basename)
            self._set_lock_file_write()
            with requests.get(cdpp_order_file) as r, open(self.file['lock'], 'wb') as f:
                f.write(r.content)
            self._unlock_file_write()
        return order_files

    def _set_lock_file_write(self):
        """
        Private method to create lock file before download
        """
        if self.debug:
            print("This is {}._set_lock_file_write()".format(__class__.__name__))

        lock_file_id = 0

        while True:

            lock_file = "{}.lock-{:02d}".format(self.file['name'], lock_file_id)

            if self.debug:
                print(" - Checking lock_file = {}".format(lock_file))

            if not os.path.exists(lock_file):
                self.file['lock'] = lock_file
                if self.debug:
                    print("   [lock_file selected]")
                break
            else:
                if self.debug:
                    print("   [lock_file already in use]")

            lock_file_id += 1

    def _unlock_file_write(self):
        """
        Private method to unlock file after download
        """
        if self.debug:
            print("This is {}._unlock_file_write()".format(__class__.__name__))

        if not os.path.exists(self.file['name']):
            if self.debug:
                print(" - file is new: renaming lock_file to {}".format(self.file['name']))
            os.rename(self.file['lock'], self.file['name'])
        else:
            if filecmp.cmp(self.file['name'], self.file['lock'], shallow=False):
                if self.debug:
                    print(" - identical file exists ({}): removing lock_file.".format(self.file['name']))
                os.remove(self.file['lock'])
            else:
                if self.debug:
                    print(" - file exists but differs: aborting.")
                raise MaserError('Downloaded file differs from previous one (check: {})'.format(self.file['name']))

    def download_file_sync(self, file_name, dir_out):
        """
        Download a single file, using sync method (for staged dataset only)
        :param file_name: Name of file
        :param dir_out: Output directory (default is current directory)
        """
        if self.debug:
            print("This is {}.download_file_sync()".format(__class__.__name__))

        self._check_reconnect()
        cdpp_command_url = "{}/command-rest/download/cdpp/command/data/object/{}?access_token={}"\
            .format(self.cdpp_host, file_name, self.auth_token["access_token"])

        self.file['name'] = os.path.join(dir_out, file_name)
        self._set_lock_file_write()

        with requests.get(cdpp_command_url) as r:
            if r.status_code == 200:
                with open(self.file['lock'], 'wb') as f:
                    f.write(r.content)
            else:
                raise MaserError("HTTP error {}: {}".format(r.status_code, r.content.decode('ascii')))

        self._unlock_file_write()


class CDPPFileFromWebService:

    def __init__(self, debug=False, verbose=False):
        if debug:
            print("This is {}.__init__()".format(__class__.__name__))

        self.debug = debug
        self.verbose = verbose
        self.dataset_name = ''
        self.mission_name = ''
        self.instrument_name = ''
        pass

    def _get_download_directory(self):
        if self.debug:
            print("This is {}._get_download_directory()".format(__class__.__name__))

        if hostname in ['macbookbc.obspm.fr', 'macbookbc.local']:
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

    def __init__(self, file_name, dataset_name, user, password, check_file=True, debug=False, verbose=False):
        if debug:
            print("This is {}.__init__()".format(__class__.__name__))

        CDPPFileFromWebService.__init__(self, debug=debug, verbose=verbose)
        self.dataset_name = dataset_name

        if dataset_name in self._staged_datasets.keys():
            self.mission_name = self._staged_datasets[self.dataset_name]['mission']
            self.instrument_name = self._staged_datasets[self.dataset_name]['instrument']
        else:
            raise MaserError("Dataset not staged, use Asynchronous method for downloading this file")

        c = CDPPWebService(debug=debug, verbose=verbose)
        c.connect(user, password)

        if check_file:
            all_file_info = c.get_files(dataset_name)
            if file_name not in [item['name'] for item in all_file_info]:
                raise MaserError("File not existing for the selected dataset")

        download_dir = self._get_download_directory()
        c.download_file_sync(file_name, download_dir)
        self.file = os.path.join(download_dir, file_name)
        c.close()


class CDPPFileFromWebServiceAsync(CDPPFileFromWebService):

    def __init__(self, start_date, stop_date, dataset_name, user, password, debug=False, verbose=False):
        if debug:
            print("This is {}.__init__()".format(__class__.__name__))

        CDPPFileFromWebService.__init__(self, debug=debug, verbose=verbose)
        c = CDPPWebService(debug=debug, verbose=verbose)
        c.connect(user, password)
        download_dir = self._get_download_directory()
        self.file = c.download_files_async(start_date, stop_date, dataset_name, download_dir)
        c.close()
