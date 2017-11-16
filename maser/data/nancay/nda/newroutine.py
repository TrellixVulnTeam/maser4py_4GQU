#! /usr/bin/env python
# -*- coding: latin-1 -*-

"""
Python module to read Nancay/NDA/NewRoutine data from SRN/NDA.
@author: B.Cecconi(LESIA)
"""

import struct
import os
import datetime
import numpy
import maser.utils.cdf.cdf as pycdf
from maser.data.data import MaserDataFromFileCDF
from maser.data.nancay.nda.nda import NDAError
from maser.data.nancay.nda.nda import NDADataFromFile
from maser.data.nancay.nda.nda import NDADataECube

__author__ = "Baptiste Cecconi"
__date__ = "24-OCT-2017"
__version__ = "0.11"

__all__ = ["NDANewRoutineData", "NDANewRoutineError", "NDANewRoutineECube", "read_srn_nda_new_routine"]


class NDANewRoutineError(NDAError):
    pass


class NDANewRoutineData(NDADataFromFile):

    def __init__(self, file, debug=False, filter_frequency=True):
        header = {}
        data = []
        name = "SRN/NDA NewRoutine Dataset"
        # meta = {}
        NDADataFromFile.__init__(self, file, header, data, name)
        self.file_handle = open(self.file, 'rb')

        self.file_info = {'name': self.file, 'size': self.get_file_size()}
        self.detect_format()
        self.format = self.file_info['format']
        self.set_filedate()
        self.debug = debug
        self.header = self.header_from_file()
        self.file_info['record_format'] = self.header['record_fmt']

        self.header['filter_frequency'] = filter_frequency
        self.header['ifrq_min'] = 0
        self.header['ifrq_max'] = 0
        for i in range(2048):
            if self.header['freq'][i] < 10:
                self.header['ifrq_min'] = i + 1
            if self.header['freq'][i] <= 88:
                self.header['ifrq_max'] = i

        self.header['ncube'] = (self.get_file_size() - self.header['size']) // self.header['cube_size']

        self.cur_ptr_in_file = 0

        if self.debug:
            print("{} eCubes in current file".format(self.header['ncube']))

        self.ecube_ptr_in_file = [self.header['size'] + ii * self.header['cube_size']
                                  for ii in range(self.header['ncube'])]

        self.start_time = self.get_first_ecube().get_datetime()
        self.end_time = self.get_last_ecube().get_datetime()

        meta = dict()
        meta['obsty_id'] = 'srn'
        meta['instr_id'] = 'nda'
        meta['recvr_id'] = 'newroutine'
        meta['freq_min'] = self.get_freq_axis()[0]  # MHz
        meta['freq_max'] = self.get_freq_axis()[-1]  # MHz
        meta['freq_len'] = len(self.get_freq_axis())
        meta['freq_stp'] = 48.828125  # kHz
        meta['freq_res'] = 48.828125  # kHz
        meta['time_step'] = (self.end_time - self.start_time).total_seconds() / self.header['ncube']
        meta['time_integ'] = meta['time_step']
        self.meta = meta

    def get_mime_type(self):
        if self.format == 'DAT':
            return 'application/x-binary'
        elif self.format == 'CDF':
            return 'application/x-cdf'
        else:
            raise NDANewRoutineError("Wrong file format")

    def __len__(self):
        if self.file_info['format'] == 'DAT':
            return (self.get_file_size()-self.file_info['header_size'])//self.file_info['record_size']
        else:
            raise NDANewRoutineError("NDA/NewRoutine: Format {} not implemented yet".format(self.file_info['format']))

    def detect_format(self):
        if self.file.endswith('.dat'):
            self.file_info['format'] = 'DAT'
            self.file_info['record_size'] = 32832
            self.file_info['header_size'] = 16660
            self.file_info['data_offset_in_file'] = self.file_info['record_size']
        elif self.file.endswith('.cdf'):
            self.file_info['format'] = 'CDF'
        else:
            raise NDANewRoutineError('NDA/NewRoutine: Unknown file Extension')

    def set_filedate(self):
        if self.file_info['format'] == 'DAT':
            self.file_info['filedate'] = ((os.path.basename(self.file).split('.'))[0])[1:9]
        else:
            raise NDANewRoutineError("NDA/NewRoutine: Format {} not implemented yet".format(self.file_info['format']))

    def header_from_file(self):
        if self.file_info['format'] == 'DAT':
            return self.header_from_dat()
        else:
            raise NDANewRoutineError("NDA/NewRoutine: Format {} not implemented yet".format(self.file_info['format']))

    def header_from_dat(self):

        f = self.file_handle
        self.file_info['header_raw'] = f.read(self.file_info['header_size'])

        hdr_fmt = '<68I1l2048f2048l'
        hdr_val = struct.unpack(hdr_fmt, self.file_info['header_raw'])

        header = dict()
        header['size'] = hdr_val[0]  # Header Size
        header['sel_prod0'] = hdr_val[1]  # selected products 0
        header['sel_prod1'] = hdr_val[2]  # selected products 1
        header['acc'] = hdr_val[3]  # accumulating factor
        header['subband'] = hdr_val[4:68]  # selected sub-bands
        header['nfreq'] = hdr_val[68]  # Number of FFT points
        header['freq'] = hdr_val[69:2117]  # frequency values
        header['ifrq'] = hdr_val[2117:4165]  # frequency indices

        # TODO: implement a real decoding of sel_prod0 and sel_prod1. Currently, only 2 cases are implemented
        if header['sel_prod0'] == 771:
            header['chan_names'] = ['LL', 'Re_LR', 'Im_LR', 'RR']
            header['chan_descr'] = ['Flux density spectrogram measured on the LH polarized array',
                                    'Real part of cross-correlation between the LH and RH arrays',
                                    'Imaginary part of cross-correlation between the LH and RH arrays',
                                    'Flux density spectrogram measured on the RH polarized array']
            header['chan_ucd'] = ['phys.flux.density;em.radio;phys.polarization.ll',
                                  'phys.flux.density;em.radio', 'phys.flux.density;em.radio',
                                  'phys.flux.density;em.radio;phys.polarization.rr']
            header['chan_label'] = ['LL', 'Re(LR)', 'Im(LR)', 'RR']
            nbchan = 4
        elif header['sel_prod0'] == 134480385:
            header['chan_names'] = ['LL', 'RR', 'Block LH', 'Block RH']
            header['chan_descr'] = ['Flux density spectrogram measured on the LH polarized array',
                                    'Flux density spectrogram measured on the RH polarized array',
                                    'Block LH', 'Block RH']
            header['chan_ucd'] = ['phys.flux.density;em.radio;phys.polarization.ll',
                                  'phys.flux.density;em.radio;phys.polarization.rr',
                                  'phys.flux.density;em.radio', 'phys.flux.density;em.radio']
            nbchan = 4
        else:
            sel_chan = [int(ii) for ii in
                        list('{:032b}'.format(header['sel_prod0'])[::-1] +
                             '{:032b}'.format(header['sel_prod1'])[::-1])]
            header['chan_names'] = []
            header['chan_descr'] = []
            header['chan_ucd'] = []
            nbchan = sum(sel_chan)

        record_fmt = '<8I'
        for iichan in range(0, nbchan):
            record_fmt = '{}{}'.format(record_fmt, '2I2048f')

        header['nbchan'] = nbchan
        header['cube_size'] = 4 * (8 + header['nbchan'] * (header['nfreq'] + 2))
        header['magic_word'] = 0x7F800000
        header['record_fmt'] = record_fmt

        return header

    def get_first_ecube(self, load_data=True, filter_frequency=True):
        return self.get_single_ecube(0, load_data, filter_frequency)

    def get_last_ecube(self, load_data=True, filter_frequency=True):
        return self.get_single_ecube(-1, load_data, filter_frequency)

    def get_single_ecube(self, index_input=0, load_data=True, filter_frequency=True):
        return NDANewRoutineECube(self, index_input, load_data, filter_frequency)

    def get_freq_axis(self):
        if self.header['filter_frequency']:
            return self.header['freq'][self.header['ifrq_min']:self.header['ifrq_max']]
        else:
            return self.header['freq']

    def get_time_axis(self):
        return [self.get_single_ecube(item, load_data=False).get_datetime() for item in range(len(self))]

    def build_edr_data(self, edr_start_time, edr_end_time):

        # creating time axis
        time_axis = self.get_time_axis()
        # creating variable dict
        var = {'header': self.header,
               'time': [],
               'data': {}}

        # selecting channels on their names (e.g., remove extra channels)
        for chan_item in self.header['chan_names']:
            if chan_item in ['LL', 'Re_LR', 'Im_LR', 'RR']:
                var['data'][chan_item] = list()

        # looping on time axis
        for ii in range(len(time_axis)):
            cur_time = time_axis[ii]

            # if cur_time is in input interval
            if edr_start_time <= cur_time < edr_end_time:

                # set var['time']
                var['time'].append(cur_time)
                # load data from current eCube
                cur_data = self.get_single_ecube(ii)
                # write only selected channels into var['data'
                for chan_item in var['data'].keys():
                    jj = self.header['chan_names'].index(chan_item)  # index of current channel in cur_data.data['corr']
                    var['data'][chan_item].append(cur_data.data['corr'][jj]['data'])

        return var


class NDANewRoutineECube(NDADataECube):
    pass


def read_srn_nda_new_routine(file_path):
    """

    :param file_path:
    :return:
    """

    return NDANewRoutineData(file_path)


def make_nda_newroutine_cdf(file_path, start_time, end_time, verbose=True):

    if verbose:
        print("Loading data from {}".format(os.path.basename(file_path)))

    dat = read_srn_nda_new_routine(file_path)
    file_name = os.path.basename(file_path)
    edr = dat.build_edr_data(start_time, end_time)
    nt = len(edr['time'])
    nf = dat.meta['freq_len']

    if verbose:
        print("Loaded {} eCubes".format(nt))

    # CDF file name with template: srn_nda_newroutine_edr_YYYYMMDD_HH00_vXX.cdf
    cdf_version = '00'
    cdf_filename = "{}_{}_{}_edr_{:04d}{:02d}{:02d}_{:02d}00_v{}.cdf"\
        .format(dat.meta['obsty_id'], dat.meta['instr_id'], dat.meta['recvr_id'],
                start_time.year, start_time.month, start_time.day, start_time.hour, cdf_version)

    if verbose:
        print("Writing into {}".format(cdf_filename))

    # removing existing CDF file
    if os.path.exists(cdf_filename):
        os.remove(cdf_filename)

    # Initialize CDF file with ISTP convention
    pycdf.lib.set_backward(False)
    cdf = pycdf.CDF(cdf_filename, '')
    cdf.col_major(True)
    cdf.compress(pycdf.const.NO_COMPRESSION)

    # Write Global Attributes

    # SETTING ISTP GLOBAL ATTRIBUTES
    cdf.attrs['TITLE'] = "SRN NDA NewRoutine Jupiter EDR hourly files Dataset"
    cdf.attrs['Project'] = ["SRN>Station de Radioastronomie de Nancay",
                            "PADC>Paris Astronomical Data Centre"]
    cdf.attrs['Discipline'] = "Space Physics>Magnetospheric Science"
    cdf.attrs['Data_type'] = "EDR"
    cdf.attrs['Descriptor'] = "{}_{}".format(dat.meta['obsty_id'], dat.meta['instr_id']).upper()
    cdf.attrs['Data_version'] = cdf_version
    cdf.attrs['Instrument_type'] = "Radio Telescope"
    cdf.attrs['Logical_source'] = "srn_{}_{}".format(cdf.attrs['Descriptor'],
                                                     cdf.attrs['Data_type']).lower()
    cdf.attrs['Logical_file_id'] = "{}_00000000_0000_v00".format(cdf.attrs['Logical_source'])
    cdf.attrs['Logical_source_description'] = "SNR/NDA/Newroutine hourly files"
    cdf.attrs['File_naming_convention'] = "source_descriptor_datatype_yyyyMMdd_vVV"
    cdf.attrs['Mission_group'] = "SRN>Station de Radioastronomie de Nancay"
    cdf.attrs['PI_name'] = "L. Lamy"
    cdf.attrs['PI_affiliation'] = ["LESIA>LESIA, Observatoire de Paris, PSL Research University, CNRS, "
                                   "Sorbonne Universites, UPMC Univ. Paris 06, Univ. Paris Diderot, "
                                   "Sorbonne Paris Cite, 5 place Jules Janssen, 92195 Meudon, France",
                                   "SRN>Station de Radioastronomie de Nancay, Observatoire de Paris, PSL Research "
                                   "University, CNRS, Univ. Orleans, 18330 Nancay, France"]
    cdf.attrs['Source_name'] = "SRN_NDA>Nancay Decametric Array"
    cdf.attrs['TEXT'] = "SRN/NDA instrument data. More info at " \
                        "http://www.obs-nancay.fr/-Le-reseau-decametrique-.html?lang=en"
    cdf.attrs['Generated_by'] = ["LESIA>Laboratoire d'Etudes Spatiales et d'Instrumentation en Astrophysique",
                                 "SRN>Station de Radioastronomie de Nancay",
                                 "PADC>Paris Astronomical Data Center"]
    cdf.attrs['Generation_date'] = "{:%Y%m%d}".format(datetime.datetime.now())
    cdf.attrs['LINK_TEXT'] = ["The NDA NewRoutine data are available at"]
    cdf.attrs['LINK_TITLE'] = ["Station de Radioastronomie de Nancay"]
    cdf.attrs['HTTP_LINK'] = ["http://www.obs-nancay.fr/"]
    cdf.attrs['MODS'] = ""
    cdf.attrs['Rules_of_use'] = ["SRN/NDA observations in open access can be freely used for scientific purposes. "
                                 "Their acquisition, processing and distribution is ensured by the SRN/NDA team, "
                                 "which can be contacted for any questions and/or collaborative purposes.",
                                 "Contact email : contact_nda@obs-nancay.fr",
                                 "We kindly request the authors of any communications and publications using these "
                                 "data to let us know about them, include minimal citation to the reference below "
                                 "and appropriate acknowledgements whenever needed.",
                                 "Reference : A. Lecacheux, The Nancay Decameter Array: A Useful Step Towards Giant, "
                                 "New Generation Radio Telescopes for Long Wavelength Radio Astronomy, in Radio "
                                 "Astronomy at Long Wavelengths, eds. R. G. Stone, K. W. Weiler, M. L. Goldstein, & "
                                 "J.-L. Bougeret, AGU Geophys. Monogr. Ser., 119, 321, 2000.",
                                 "Acknowledgements : see the acknowledgement field."]
    cdf.attrs['Skeleton_version'] = ""
    cdf.attrs['Sotfware_version'] = __version__
    cdf.attrs['Time_resolution'] = "0.5 seconds"
    cdf.attrs['Acknowledgement'] = "The authors acknowledge the Station de Radioastronomie de Nancay of the " \
                                   "Observatoire de Paris (USR 704-CNRS, supported by Universite d'Orleans, OSUC, " \
                                   "and Region Centre in France) for providing access to NDA observations accessible " \
                                   "online at http://www.obs-nancay.fr "
    cdf.attrs['ADID_ref'] = ""
    cdf.attrs['Validate'] = ""
    cdf.attrs['Parent'] = file_name
    cdf.attrs['Software_language'] = 'Python 3.5 + Maser4py'

    # SETTING PDS GLOBAL ATTRIBUTES
    cdf.attrs['PDS_Start_time'] = start_time.isoformat() + 'Z'
    cdf.attrs['PDS_Stop_time'] = end_time.isoformat() + 'Z'
    if file_name[0] == 'J':
        cdf.attrs['PDS_Observation_target'] = 'Jupiter'
    elif file_name[0] == 'S':
        cdf.attrs['PDS_Observation_target'] = 'Sun'
    else:
        cdf.attrs['PDS_Observation_target'] = ''
    cdf.attrs['PDS_Observation_type'] = 'Radio'

    # SETTING VESPA GLOBAL ATTRIBUTES
    cdf.attrs['VESPA_dataproduct_type'] = "ds>Dynamic Spectra"
    if file_name[0] == 'J':
        cdf.attrs['VESPA_target_class'] = "planet"
        cdf.attrs['VESPA_target_region'] = "Magnetosphere"
        cdf.attrs['VESPA_feature_name'] = "Radio Emissions#Aurora"
    elif file_name[0] == 'S':
        cdf.attrs['VESPA_target_class'] = "star"
        cdf.attrs['VESPA_target_region'] = "Solar wind"
        cdf.attrs['VESPA_feature_name'] = "Radio Emissions"
    else:
        cdf.attrs['VESPA_target_class'] = ""
        cdf.attrs['VESPA_target_region'] = ""
        cdf.attrs['VESPA_feature_name'] = ""

    cdf.attrs['VESPA_time_min'] = edr['time'][0].isoformat()
    cdf.attrs['VESPA_time_max'] = edr['time'][-1].isoformat()
    cdf.attrs['VESPA_time_sampling_step'] = dat.meta['time_step']
    cdf.attrs['VESPA_time_exp'] = dat.meta['time_integ']

    cdf.attrs['VESPA_spectral_range_min'] = dat.meta['freq_min']
    cdf.attrs['VESPA_spectral_range_max'] = dat.meta['freq_max']
    cdf.attrs['VESPA_spectral_sampling_step'] = dat.meta['freq_stp']
    cdf.attrs['VESPA_spectral_resolution'] = dat.meta['freq_res']

    cdf.attrs['VESPA_instrument_host_name'] = dat.meta['obsty_id']
    cdf.attrs['VESPA_instrument_name'] = dat.meta['instr_id']
    cdf.attrs['VESPA_measurement_type'] = "phys.flux;em.radio"
    cdf.attrs['VESPA_access_format'] = "application/x-cdf"

    # SETTING SRN/NDA/NewRoutine GLOBAL ATTRIBUTES

    cdf.attrs['NDA_newroutine_sel_prod'] = [dat.header['sel_prod0'], dat.header['sel_prod1']]
    cdf.attrs['NDA_newroutine_acc'] = dat.header['acc']

    # SETTING UP VARIABLES AND VARIABLE ATTRIBUTES
    #   The EPOCH variable type must be CDF_TIME_TT2000
    #   PDS-CDF requires no compression for variables.
    cdf.new('EPOCH', data=edr['time'], type=pycdf.const.CDF_TIME_TT2000, compress=pycdf.const.NO_COMPRESSION)
    cdf['EPOCH'].attrs.new('VALIDMIN', data=datetime.datetime(2000, 1, 1), type=pycdf.const.CDF_TIME_TT2000)
    cdf['EPOCH'].attrs.new('VALIDMAX', data=datetime.datetime(2100, 1, 1), type=pycdf.const.CDF_TIME_TT2000)
    cdf['EPOCH'].attrs.new('SCALEMIN', data=start_time, type=pycdf.const.CDF_TIME_TT2000)
    cdf['EPOCH'].attrs.new('SCALEMAX', data=end_time, type=pycdf.const.CDF_TIME_TT2000)
    cdf['EPOCH'].attrs['CATDESC'] = "Default time (TT2000)"
    cdf['EPOCH'].attrs['FIELDNAM'] = "Epoch"
    cdf['EPOCH'].attrs.new('FILLVAL', data=-9223372036854775808, type=pycdf.const.CDF_TIME_TT2000)
    cdf['EPOCH'].attrs['LABLAXIS'] = "Epoch"
    cdf['EPOCH'].attrs['UNITS'] = "ns"
    cdf['EPOCH'].attrs['VAR_TYPE'] = "support_data"
    cdf['EPOCH'].attrs['SCALETYP'] = "linear"
    cdf['EPOCH'].attrs['MONOTON'] = "INCREASE"
    cdf['EPOCH'].attrs['TIME_BASE'] = "J2000"
    cdf['EPOCH'].attrs['TIME_SCALE'] = "UTC"
    cdf['EPOCH'].attrs['REFERENCE_POSITION'] = "Earth"
    cdf['EPOCH'].attrs['SI_CONVERSION'] = "1.0e-9>s"
    cdf['EPOCH'].attrs['UCD'] = "time.epoch"

    # PDS-CDF requires no compression for variables.
    cdf.new('FREQUENCY', data=dat.get_freq_axis(), type=pycdf.const.CDF_FLOAT, compress=pycdf.const.NO_COMPRESSION,
            recVary=False)
    cdf['FREQUENCY'].attrs['CATDESC'] = "Frequency"
    cdf['FREQUENCY'].attrs['FIELDNAM'] = "FREQUENCY"
    cdf['FREQUENCY'].attrs.new('FILLVAL', data=-1.0e+31, type=pycdf.const.CDF_REAL4)
    cdf['FREQUENCY'].attrs['FORMAT'] = "F6.3"
    cdf['FREQUENCY'].attrs['LABLAXIS'] = "Frequency"
    cdf['FREQUENCY'].attrs['UNITS'] = "MHz"
    cdf['FREQUENCY'].attrs.new('VALIDMIN', data=0., type=pycdf.const.CDF_REAL4)
    cdf['FREQUENCY'].attrs.new('VALIDMAX', data=100., type=pycdf.const.CDF_REAL4)
    cdf['FREQUENCY'].attrs['VAR_TYPE'] = "support_data"
    cdf['FREQUENCY'].attrs['SCALETYP'] = "linear"
    cdf['FREQUENCY'].attrs.new('SCALEMIN', data=dat.meta['freq_min'], type=pycdf.const.CDF_REAL4)
    cdf['FREQUENCY'].attrs.new('SCALEMAX', data=dat.meta['freq_max'], type=pycdf.const.CDF_REAL4)
    cdf['FREQUENCY'].attrs['SI_CONVERSION'] = "1.0e6>Hz"
    cdf['FREQUENCY'].attrs['UCD'] = "em.freq"

    for var_name, var_values in edr['data'].items():
        jj = dat.header['chan_names'].index(var_name)

        cdf.new(var_name, data=numpy.array(var_values), type=pycdf.const.CDF_REAL4, compress=pycdf.const.NO_COMPRESSION)
        cdf[var_name].attrs['CATDESC'] = dat.header['chan_descr'][jj]
        cdf[var_name].attrs['DEPEND_0'] = "EPOCH"
        cdf[var_name].attrs['DEPEND_1'] = "FREQUENCY"
        cdf[var_name].attrs['DICT_KEY'] = "electric_field>power"
        cdf[var_name].attrs['DISPLAY_TYPE'] = "spectrogram"
        cdf[var_name].attrs['FIELDNAM'] = var_name
        cdf[var_name].attrs.new('FILLVAL', data=-1e31, type=pycdf.const.CDF_REAL4)
        cdf[var_name].attrs['FORMAT'] = "E12.2"
        cdf[var_name].attrs['LABLAXIS'] = dat.header['chan_label'][jj]
        cdf[var_name].attrs['UNITS'] = "ADU"
        # TODO: check with intense bursts to see what would be the max possible value
        cdf[var_name].attrs.new('VALIDMIN', data=1e6, type=pycdf.const.CDF_REAL4)
        cdf[var_name].attrs.new('VALIDMAX', data=1e21, type=pycdf.const.CDF_REAL4)
        cdf[var_name].attrs['VAR_TYPE'] = "data"
        cdf[var_name].attrs['SCALETYP'] = "linear"
        cdf[var_name].attrs.new('SCALEMIN', data=1e7, type=pycdf.const.CDF_REAL4)
        cdf[var_name].attrs.new('SCALEMAX', data=1e12, type=pycdf.const.CDF_REAL4)
        cdf[var_name].attrs['FORMAT'] = "E12.2"
        cdf[var_name].attrs['FORM_PTR'] = ""
        cdf[var_name].attrs['SI_CONVERSION'] = " "
        cdf[var_name].attrs['UCD'] = dat.header['chan_ucd'][jj]

    cdf.close()

    if verbose:
        print("CDF file completed and closed.")

    # validating and fixing CDF file
    out = MaserDataFromFileCDF(cdf_filename, verbose=True)
    out.fix_cdf()
    out.validate_pds()
