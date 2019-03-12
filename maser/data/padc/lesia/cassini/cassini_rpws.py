import numpy as np
import os
import glob
import sys
import struct

from astropy.time import Time, TimeDelta
import pylab as plt
import itertools



# ================================================================================= #
# ================================================================================= #
class Stream(object):
    """ Build streams to send to DAS2
    """
    def __init__(self, start, stop, binary=False):
        self.tstart = start
        self.tstop = stop
        self._binary = binary

    # ================================================================================= #
    # ================================================================================= #
    @property
    def tstart(self):
        return self._tstart
    @tstart.setter
    def tstart(self, t):
        if not isinstance(t, Time):
            t = Time(t)
        self._tstart = t
        return

    # --------------------------------------------------------------------------------- #
    @property
    def tstop(self):
        return self._tstop
    @tstop.setter
    def tstop(self, t):
        if not isinstance(t, Time):
            t = Time(t)
        self._tstop = t
        return
    # ================================================================================= #

    # ================================================================================= #
    def stream_header(self, dt, title='Stream'):
        """ Build the stream header.

            Parameters
            ----------
            dt : float
                Time step in seconds
        """
        stream_header = '<stream version="2.2">\n' \
                        '    <properties title="{}" Datum:xTagWidth="{} s"\n' \
                        '                DatumRange:xRange="{} to {} UTC"\n' \
                        '                String:renderer="spectrogram"/>\n' \
                        '</stream>'.format(title, dt, self.tstart.iso, self.tstop.iso)

        stream_header = "[00]{:06d}{}".format(len(stream_header) + 1, stream_header)
        return stream_header

    # --------------------------------------------------------------------------------- #
    def packet_header(self, y, yunit, ylabel, var_title, var_label):
        """
            Parameters
            ----------
            y : numpy.array
                The y data
            ylabel : str
                The name of the 'y' axis (e.g. 'Frequency')
            yunit : str
                The unit of the 'y' axis (e.g. 'MHz')
            var_title : str
                The big title of the data
            var_label : str
                The 'one-word' label of the data
        """
        var_unit = 'adu'
        var_range = ''
        if self.binary:
            x_time = '<x type="little_endian_real8" units="t2000" />'
            d_format = 'little_endian_real4'
        else:
            x_time = '<x type="time20" units="us2000" />'
            d_format = 'ascii12'

        packet_header = '<packet>\n' \
                        '    {}\n' \
                        '    <yscan nitems="{}" type="{}" yUnits="{}" name="{}" zUnits="{}"\n' \
                        '           yTags="{}">\n' \
                        '        <properties String:yLabel="{}" String:zLabel="{}" double:zFill="0.0" {}/>\n' \
                        '    </yscan>\n' \
                        '</packet>'.format(x_time, y.size, d_format, yunit, var_title, var_unit, 
                                          ','.join(["{:5.2f}".format(item) for item in y]), ylabel, var_label, var_range)
        packet_header = "[01]{:06d}{}".format(len(packet_header) + 1, packet_header)
        return packet_header

    # --------------------------------------------------------------------------------- #
    def packet(self, times, data):
        """
            data : 2D numpy.array
                'Instantaneous' data set, if time-frequency types, format is data = (time, frequency)
        """
        if not isinstance(times, Time):
            times = Time(times)

        for i in range(times.size):
            cur_dt = times[i]
            if cur_dt >= self.tstart and cur_dt <= self.tstop:
                cur_data = data[i, :]
                if self.binary:
                    cur_write_buffer = bytearray()
                    cur_write_buffer.extend(bytes(":01:", 'ascii'))
                    cur_write_buffer.extend(struct.pack("<d", (cur_dt-Time('2000-01-01 00:00:00')).sec))
                    for item in cur_data:
                        cur_write_buffer.extend(struct.pack('<f', item))
                    sys.stdout.buffer.write(cur_write_buffer)
                    sys.stdout.flush()
                else:
                    print(":01:{}{}".format(str(cur_dt), ''.join(["{:12.4e}".format(item) for item in cur_data])))
        return

# ===================================================================================== #
# ===================================================================================== #


DATA_PATH = os.path.abspath('/kronos/rpws_data')

DTYPES = {
    'n1': np.dtype([
        ('ydh', '<u4'), # yyyydddhh of current file
        ('num', '<u4'), # index of record in current file
        ('ti', '<u4'), # time index
        ('fi', '<u4'), # frequency index
        ('dti', '<i2'), # integration time (msec)
        ('c', 'u1'), # hundreds of second
        ('ant', 'u1'), # antenna selection: 0-3=NoDF, (Ex=Off,+X,-X,D), 11=DF/+X, 12=DF/-X
        ('agc1', 'u1'), # agc 'X'
        ('agc2', 'u1'), # agc 'Z'
        ('auto1', 'u1'), # auto-correlation 'X'
        ('auto2', 'u1'), # auto-correlation 'Z'
        ('cross1', '<i2'), # cross-correlation (real)
        ('cross2', '<i2') # cross-correlation (Imaginary)
        ]),
    'n2': np.dtype([
        ('ydh', '<u4'), # 
        ('num', '<u4'), # 
        ('t97', '<f8'), # time (decimal days, epoch = 1997.0)
        ('f', '<f4'), # frequency (kHz)
        ('dt', '<f4'), # effective integration time (msec)
        ('df', '<f4'), # effective bandwidth (kHz)
        ('autoX', '<f4'), # auto-correlation 'X' (V2/Hz)
        ('autoZ', '<f4'), # auto-correlation 'Z' (V2/Hz)
        ('crossR', '<f4'), # cross-correlation (real)
        ('crossI', '<f4'), # cross-correlation (Imaginary)
        ('ant', 'i1') # 
        ]),
    'n3b': np.dtype([
        ('ydh', '<u4'), # 
        ('num', '<u4', 2), # 
        ('s', '<f4', 2), # Intensity (V2 m-2 Hz-1)
        ('q', '<f4', 2), # Normalized linear polarization
        ('u', '<f4', 2), # parameters Q & U
        ('v', '<f4', 2), # Normalized circular polar. V
        ('th', '<f4'), # Source colatitude ( in S/C frame)
        ('ph', '<f4'), # Source azimuth ( in S/C frame)
        ('zr', '<f4'), # ratio of 2 Azz values (Azz+ / Azz-)
        ('snx', '<f4', 2), # S/N ratio on autocorrel. values
        ('snz', '<f4', 2) # S/N ratio on autocorrel. values
        ]),
    'n3c': np.dtype([
        ('ydh', '<i4'), # 
        ('num', '<i4', 2), # 
        ('s', '<f4'), # 
        ('q', '<f4'), # 
        ('u', '<f4'), # 
        ('v', '<f4', 2), # 
        ('th', '<f4', 2), # 
        ('ph', '<f4', 2), # 
        ('zr', '<f4'), # 
        ('snx', '<f4', 2), # 
        ('snz', '<f4', 2) # 
        ]),
    'n3d': np.dtype([
        ('ydh', '<i4'), # 
        ('num', '<i4'), # 
        ('s', '<f4'), # 
        ('q', '<f4'), # 
        ('u', '<f4'), # 
        ('v', '<f4'), # 
        ('th', '<f4'), # 
        ('ph', '<f4'), # 
        ('snx', '<f4'), # 
        ('snz', '<f4') # 
        ]),
    'n3e': np.dtype([
        ('ydh', '<i4'), # 
        ('num', '<i4'), # 
        ('s', '<f4'), # 
        ('q', '<f4'), # 
        ('u', '<f4'), # 
        ('v', '<f4'), # 
        ('th', '<f4'), # 
        ('ph', '<f4'), # 
        ('snx', '<f4'), # 
        ('snz', '<f4') # 
        ])
    }

# ===================================================================================== #
# ===================================================================================== #
class Cassini(object):
    """
    """
    def __init__(self):
        self._levels = ['n1', 'n2', 'n3b', 'n3c', 'n3d', 'n3e']
        self.files = {level: [] for level in self._levels}
        self.data = {}


    def __add__(self, other):
        if not isinstance(other, Cassini):
            raise Exception("\n\t--> Can't concatenate <Cassini> with <{}> <--".format(type(other).__qualname__))
        assert self.level == other.level, "\n\t--> Should be the same levels <--"

        # Frequency inserts
        result_freqs = np.unique(np.hstack([self._ufreq, other._ufreq]))
        self_mask = np.in1d(result_freqs, self._ufreq, invert=True)
        selfinsert = np.arange(result_freqs.size)[self_mask]
        selfinsert -= np.arange(selfinsert.size)
        other_mask = np.in1d(result_freqs, other._ufreq, invert=True)
        otherinsert = np.arange(result_freqs.size)[other_mask]
        otherinsert -= np.arange(otherinsert.size)

        self.data['freq'] = result_freqs

        # Conf inserts
        # result_conf = np.unique(np.hstack([self._uconf, other._uconf]))
        # self_mask = np.in1d(result_conf, self._uconf, invert=True)
        # selfcinsert = np.arange(result_conf.size)[self_mask]
        # selfcinsert -= np.arange(selfcinsert.size)
        # other_mask = np.in1d(result_conf, other._uconf, invert=True)
        # othercinsert = np.arange(result_conf.size)[other_mask]
        # othercinsert -= np.arange(othercinsert.size)

        for dcol in self.dcol:
            # Inserting empty rows at missing frequencies
            self.data[dcol] = np.insert(self.data[dcol], selfinsert, np.zeros(self.data['conf'].size), axis=1)
            self.data[dcol][:, selfinsert, :] = np.ma.masked
            other.data[dcol] = np.insert(other.data[dcol], otherinsert, np.zeros(other.data['conf'].size), axis=1)
            other.data[dcol][:, otherinsert, :] = np.ma.masked

            # Inserting whole arrays at missing conf
            # self.data[dcol] = np.insert(self.data[dcol], selfcinsert, 0, axis=2)
            # self.data[dcol][:, :, selfcinsert] = np.ma.masked
            # other.data[dcol] = np.insert(other.data[dcol], othercinsert, 0, axis=2)
            # other.data[dcol][:, :, othercinsert] = np.ma.masked

            # Concatenate in time (several cases depending on overlaps):
            if   (self.data['time'][0] >= other.data['time'][0]) & (self.data['time'][-1] <= other.data['time'][-1]):
                # "self" included in self --> concat = "other"
                self.data[dcol] = other.data[dcol]
                self.data['time'] = other.data['time']

            elif (self.data['time'][0] <= other.data['time'][0]) & (self.data['time'][-1] >= other.data['time'][-1]):
                # "other" included in self --> concat = "self"
                pass

            elif self.data['time'][0] >= other.data['time'][-1]:
                # "other" ends before "self" starts --> concat "other" + "self"
                self.data[dcol] = np.concatenate((other.data[dcol], self.data[dcol]), axis=0)
                self.data['time'] = np.hstack((other.data['time'], self.data['time']))

            elif self.data['time'][-1] <= other.data['time'][0]:
                # "other" starts after "self" ends --> concat "self" + "other"
                self.data[dcol] = np.concatenate((self.data[dcol], other.data[dcol]), axis=0)
                self.data['time'] = np.hstack((self.data['time'], other.data['time']))

            elif self.data['time'][-1] >= other.data['time'][0]:
                # "other" starts before "self" ends --> remove the last bits of "self" --> concat "self" + "other"
                self.data[dcol] = np.concatenate((self.data[dcol][self.data['time'] < other.data['time'][0]], other.data[dcol]), axis=0)
                self.data['time'] = np.hstack((self.data['time'][self.data['time'] < other.data['time'][0]], other.data['time']))

            elif self.data['time'][0] <= other.data['time'][-1]:
                # "self" starts before "other" ends --> remove the last bits of "other" --> concat "other" + "self"
                self.data[dcol] = np.concatenate((other.data[dcol][other.data['time'] < self.data['time'][0]], self.data[dcol]), axis=0)
                self.data['time'] = np.hstack((other.data['time'][other.data['time'] < self.data['time'][0]], self.data['time']))

            else:
                raise Exception("Something unexpected happened")

        return self

    # ================================================================================= #
    # ================================================================================= #
    @property
    def time(self):
        return self._time
    @time.setter
    def time(self, t):
        if t is None:
            self._time = [None, None]
            return
        assert isinstance(t, list), "\n\t--> 'time' attribute: list expected <--\n"
        assert len(t) == 2, "\n\t--> 'time' attribute: length-2 list expected <--\n"
        if not isinstance(t[0], Time):
            try:
                t[0] = Time(t[0])
            except:
                raise ValueError("\n\t--> 'time' attribute: 'YYYY-MM-DD hh:mm:ss' expected <--\n")
        if not isinstance(t[1], Time):
            try:
                t[1] = Time(t[1])
            except:
                raise ValueError("\n\t--> 'time' attribute: 'YYYY-MM-DD hh:mm:ss' expected <--\n")
        self._time = t

        self._preselect()
        return

    # --------------------------------------------------------------------------------- #
    @property
    def freq(self):
        return self._freq
    @freq.setter
    def freq(self, f):
        if f is None:
            self._freq = [None, None]
            return
        assert isinstance(f, list), "\n\t--> 'freq' attribute: list expected <--\n"
        assert len(f) == 2, "\n\t--> 'freq' attribute: length-2 list expected <--\n"

        self._freq = f
        return

    # --------------------------------------------------------------------------------- #
    @property
    def conf(self):
        return self._conf
    @conf.setter
    def conf(self, c):
        if c is None:
            self._conf = None
            return
        if not isinstance(c, list):
            c = [c]
        self._conf = c
        return

    # --------------------------------------------------------------------------------- #
    @property
    def level(self):
        return self._level
    @level.setter
    def level(self, l):
        if l is None:
            self._level = None
            return
        l = l.lower()
        assert l in self._levels, "\n\t--> 'level' attribute: should be in {} <--\n".format(self._levels)
        self._level = l
        return

    # --------------------------------------------------------------------------------- #
    @property
    def dcol(self):
        return self._dcol
    @dcol.setter
    def dcol(self, d):
        if d is None:
            self._dcol = None
            return
        available = DTYPES[self.level].names
        if not isinstance(d, list):
            d = [d]
        for di in d:
            assert di in available, "\n\t--> 'dcol' attribute: should be in {} <--\n".format(available)
        self._dcol = d
    # ================================================================================= #


    # ================================================================================= #
    # ================================================================================= #
    def load(self, time=None, freq=None, dcol=None, level='n1', conf=None):
        """
        """
        self.time = time
        self.freq = freq
        self.conf = conf
        self.level = level
        self.dcol = dcol

        self._buildmasks()
        self._returndata()
        
        return

    # --------------------------------------------------------------------------------- #
    def plot(self):
        dcols = [dd for dd in self.data.keys() if dd not in ['freq', 'time', 'conf']]
        for dcol in dcols:
            for i, conf in enumerate(self.data['conf']):
                plt.title('{}, {}'.format(dcol, conf))
                # plt.pcolormesh(np.arange(self._dshape[0]), self.data['freq'], np.log10(self.data[dcol][:, :, i].T))
                
                data = np.ma.masked_invalid(self.data[dcol][:, :, i].T)
                plt.pcolormesh(np.arange(self.data[dcol].shape[0]), np.arange(self.data[dcol].shape[1]), np.log10(data))
                # plt.pcolormesh(np.arange(self.data[dcol].shape[0]), np.arange(self.data[dcol].shape[1]), self.data[dcol][:, :, i].T)

                # plt.imshow(np.log10(data), origin='lower', interpolation='nearest', aspect='auto')
                plt.colorbar()
                plt.show()
                plt.close('all')

    # --------------------------------------------------------------------------------- #
    def write_cdf(self, cdfname):
        """ Write a CDF file out of the data selection
        """
        from spacepy import pycdf

        # Opening CDF object
        pycdf.lib.set_backward(False)  # this is setting the CDF version to be used

        cdf = pycdf.CDF(cdfname, '')

        # required settings for ISTP and PDS compliance
        cdf.col_major(True)  # Column Major
        cdf.compress(pycdf.const.NO_COMPRESSION)  # No file level compression

        # Writing ISTP global attributes
        cdf.attrs["Project"] = ["PADC>Paris Astronomical Data Centre",
                                "MASER>Mesure Analyse et Simulation d'Emissions Radio",
                                "CDPP>Centre de Donnees de la Physique des Plasmas",
                                "PDS-PPI>Planetary Plasma Interaction Node of NASA Planetary Data System"]
        cdf.attrs['Discipline'] = "Planetary Physics>Waves"
        cdf.attrs['Data_type'] = 'HFR_{}'.format(self.level.upper())
        cdf.attrs['Descriptor'] = 'RPWS'
        cdf.attrs['Data_version'] = '10'
        cdf.attrs['Instrument_type'] = 'Radio and Plasma Waves (space)'
        cdf.attrs['Logical_file_id'] = 'co_rpws_hfr_{}_{}_{}_v{}'.format(self.level,
                                                                         self._time[0].strftime('%Y%m%d%H%M%S%f'),
                                                                         self._time[1].strftime('%Y%m%d%H%M%S%f'),
                                                                         '10')
        cdf.attrs['Logical_source'] = 'co_rpws_hfr_{}'.format(self.level)
        cdf.attrs['Logical_source_description'] = 'Cassini-RPWS-HFR level 2 dataset'
        cdf.attrs['File_naming_convention'] = 'source_descriptor_type_yyyyMMddHHmm_yyyyMMddHHmm_ver'
        cdf.attrs['Mission_group'] = 'Cassini-Huygens'
        cdf.attrs['PI_name'] = "W.S. Kurth"
        cdf.attrs['PI_affiliation'] = 'University of Iowa'
        cdf.attrs['Source_name'] = 'CO>Cassini Orbiter'
        cdf.attrs['TEXT'] = 'Cassini-RPWS-HFR Level 2 dataset'
        cdf.attrs['Generated_by'] = 'LESIA/ObsParis'
        cdf.attrs['Generation_date'] = Time.now().isot
        cdf.attrs['LINK_TEXT'] = ["More details on ", "CDPP archive"]
        cdf.attrs['LINK_TITLE'] = ["LESIA Cassini Kronos webpage", "web site"]
        cdf.attrs['HTTP_LINK'] = ["http://www.lesia.obspm.fr/kronos", "https://cdpp-archive.cnes.fr"]
        cdf.attrs['MODS'] = " "
        cdf.attrs['Parents'] = " "
        cdf.attrs['Rules_of_use'] = " "
        cdf.attrs['Skeleton_version'] = " "
        cdf.attrs['Software_version'] = " "
        cdf.attrs['Time_resolution'] = " "
        cdf.attrs['Acknowledgement'] = " "
        cdf.attrs['ADID_ref'] = " "
        cdf.attrs['Validate'] = " "

        # Writing PDS/PPI global attributes

#        cdf.attrs['PDS_orbit_number'] = self.rev_id
#        cdf.attrs['PDS_mission_phase'] = self._get_mission_phase()
        cdf.attrs['PDS_start_time'] = self.data['time'][0].isot
        cdf.attrs['PDS_stop_time'] =  self.data['time'][-1].isot
        cdf.attrs['PDS_observation_target'] = "Saturn"
        cdf.attrs['PDS_observation_type'] = "Waves"
        cdf.attrs['PDS_collection_id'] = "urn:nasa:pds:co-rpws-saturn:hfr-n2-data"
        cdf.attrs['PDS_LID'] = "urn:nasa:pds:co-rpws-saturn:hfr-n2-data:{}-{}-cdf".\
            format(self._time[0].strftime('%Y%m%d%H%M%S%f'), self._time[1].strftime('%Y%m%d%H%M%S%f'))
#        cdf.attrs['PDS_LID_plot'] = "urn:nasa:pds:co-rpws-saturn:hfr-qtn-browse:{}-{}-plot".\
#            format(self._get_ymdhm_start(), self._get_ymdhm_end())
#        cdf.attrs['PDS_LID_thumbnail'] = "urn:nasa:pds:co-rpws-saturn:hfr-qtn-browse:{}-{}-thumbnail".\
#            format(self._get_ymdhm_start(), self._get_ymdhm_end())
#        cdf.attrs['PDS_LID_index'] = "urn:nasa:pds:co-rpws-saturn:hfr-qtn-document:index"

        cdf.attrs['VESPA_access_format'] = 'application/x-cdf'
        cdf.attrs['VESPA_dataproduct_type'] = 'DS>Dynamic Spectrum'
        cdf.attrs['VESPA_feature_name'] = ' '
        cdf.attrs['VESPA_instrument_host_name'] = 'Cassini'
        cdf.attrs['VESPA_instrument_name'] = 'RPWS'
        cdf.attrs['VESPA_measurement_type'] = 'em.radio'
        cdf.attrs['VESPA_publisher'] = 'LESIA/MASER/PADC'
        cdf.attrs['VESPA_spectral_range_max'] = self.data['freq'].max() * 1.e3
        cdf.attrs['VESPA_spectral_range_min'] = self.data['freq'].min() * 1.e3

        # SETTING UP VARIABLES AND VARIABLE ATTRIBUTES
        #   The EPOCH variable type must be CDF_TIME_TT2000
        #   PDS-CDF requires no compression for variables.
        cdf.new('EPOCH', data=self.data['time'].datetime, type=pycdf.const.CDF_TIME_TT2000,
                compress=pycdf.const.NO_COMPRESSION)
        cdf['EPOCH'].attrs.new('VALIDMIN', data=self.data['time'][0].datetime, type=pycdf.const.CDF_TIME_TT2000)
        cdf['EPOCH'].attrs.new('VALIDMAX', data=self.data['time'][-1].datetime, type=pycdf.const.CDF_TIME_TT2000)
        cdf['EPOCH'].attrs.new('SCALEMIN', data=self.data['time'][0].datetime, type=pycdf.const.CDF_TIME_TT2000)
        cdf['EPOCH'].attrs.new('SCALEMAX', data=self.data['time'][-1].datetime, type=pycdf.const.CDF_TIME_TT2000)
        cdf['EPOCH'].attrs['CATDESC'] = "Default time (TT2000)"
        cdf['EPOCH'].attrs['FIELDNAM'] = "Epoch"
        cdf['EPOCH'].attrs.new('FILLVAL', data=-9223372036854775808, type=pycdf.const.CDF_TIME_TT2000)
        cdf['EPOCH'].attrs['LABLAXIS'] = "Epoch"
        cdf['EPOCH'].attrs['UNITS'] = "ns"
        cdf['EPOCH'].attrs['FORM_PTR'] = "CDF_TIME_TT2000"
        cdf['EPOCH'].attrs['VAR_TYPE'] = "support_data"
        cdf['EPOCH'].attrs['SCALETYP'] = "linear"
        cdf['EPOCH'].attrs['MONOTON'] = "INCREASE"
        cdf['EPOCH'].attrs['REFERENCE_POSITION'] = "Spacecraft barycenter"
        cdf['EPOCH'].attrs['SI_CONVERSION'] = "1.0e-9>s"
        cdf['EPOCH'].attrs['UCD'] = "time.epoch"
        cdf['EPOCH'].attrs['TIME_BASE'] = 'UTC'

        cdf.new('Frequency', data=self.data['freq'], type=pycdf.const.CDF_REAL4,
                compress=pycdf.const.NO_COMPRESSION)
        cdf['Frequency'] = self.data['freq']
        cdf['EPOCH'].attrs.new('VALIDMIN', 3.5, type=pycdf.const.CDF_REAL4)
        cdf['EPOCH'].attrs.new('VALIDMAX', 16125, type=pycdf.const.CDF_REAL4)
        cdf['Frequency'].attrs['SCALEMIN'] = self.data['freq'][0]
        cdf['Frequency'].attrs['SCALEMAX'] = self.data['freq'][-1]
        cdf['Frequency'].attrs['UNITS'] = 'kHz'

        for dcol in self.dcol:
            cdf[dcol] = np.squeeze(self.data[dcol])
            cdf[dcol].attrs['DEPEND_0'] = 'EPOCH'
            cdf[dcol].attrs['DEPEND_1'] = 'Frequency'
            cdf[dcol].attrs['level'] = self.level
            cdf[dcol].attrs['ant'] = self.conf

        cdf.close()
        return
    # ================================================================================= #


    # ================================================================================= #
    # ================================================================================= #
    def _preselect(self):
        """ Preselect the hourly files once self.time has been set
        """
        print("\n\tSearching for files...")
        begin_trim = np.array([1, 91, 181, 271])
        end_trim = np.array([90, 180, 270, 366])

        # Parse the time selection
        yday1 = self.time[0].yday
        yday2 = self.time[1].yday
        year1, day1, hh1 = yday1.split(':')[:3]
        year2, day2, hh2 = yday2.split(':')[:3]
        yday1float = float(year1 + day1 + '.' + hh1)
        yday2float = float(year2 + day2 + '.' + hh2)

        # Find the repositories (formatted as YYYY_DDD_DDD)
        year_span = np.arange(int(year1), int(year2) + 1)
        count_trimester = False
        repositories = []
        for year in year_span:
            for t0, t1 in zip(begin_trim, end_trim):
                if (yday1 >= Time('{}:{}:00:00:00.000'.format(year, t0)))\
                    and (yday1 < Time('{}:{}:00:00:00.000'.format(year, t1))):
                    count_trimester = True
                if count_trimester:
                    repositories.append('{0:04}_{1:03}_{2:03}'.format(year, t0, t1))
                if (yday2 >= Time('{}:{}:00:00:00.000'.format(year, t0)))\
                    and (yday2 < Time('{}:{}:00:00:00.000'.format(year, t1))):
                    count_trimester = False
                    break
        
        # Find the files
        one_hour = TimeDelta(3600, format='sec')
        for level in self._levels:
            for repo in sorted(repositories):
                f_syntax = os.path.join(DATA_PATH, '{}/{}/*'.format(repo, level))
                files = np.array(glob.glob(f_syntax))
                ydays = np.array([ff[-10:] for ff in files]).astype(float)                

                mask = (ydays >= yday1float) & (ydays <= yday2float)

                self.files[level] = np.hstack([self.files[level], files[mask]])

            self.files[level] = sorted( self.files[level] )
        print("\t...files found.")
        return

    # --------------------------------------------------------------------------------- #
    def _readdata(self, level=None):
        """ Read all preselected Cassini hourly files and concatenate them for a specific level
        """
        if level is None:
            level = self.level
        data = []
        for file in self.files[level]:
            data.append( np.fromfile(file, count=-1, dtype=DTYPES[level]) )
        return np.hstack(data)

    # --------------------------------------------------------------------------------- #
    def _buildmasks(self):
        """
        """
        print("\n\tBuilding selection masks...")

        self._n1 = self._readdata(level='n1')
        self._n2 = self._readdata(level='n2')
        self.data['time'] = Time('1997-01-01') + TimeDelta((self._n2['t97'] - 1)*86400, format='sec')
        self.data['freq'] = self._n2['f']

        # Build the selection mask
        self._dataselect = np.ones(self._n1['ti'].size, dtype=bool)
        if self.time is not None:
            assert self.data['time'].size == self._n1['ti'].size, '\n\t--> Time size issue! <--'
            self._dataselect *= (self.data['time'] >= self.time[0])
            self._dataselect *= (self.data['time'] <= self.time[1])
        if self.freq is not None:
            assert self.data['freq'].size == self._n1['fi'].size, '\n\t--> Freq size issue! <--'
            if self.freq[0] is not None:
                self._dataselect *= (self.data['freq'] >= self.freq[0])
            if self.freq[1] is not None:
                self._dataselect *= (self.data['freq'] <= self.freq[1])
        if self.conf is not None:
            conf_mask = np.zeros(self._dataselect.size, dtype=bool)
            for cc in self.conf:
                assert cc in self._n1['ant'], '\n\t--> conf could only be one of: {} <--'.format(np.unique(self._n1['ant']))
                conf_mask += (self._n1['ant'] == cc)
            self._dataselect *= conf_mask

        self._n1 = self._n1[self._dataselect]
        self._n2 = self._n2[self._dataselect]
        self.data['time'] = self.data['time'][self._dataselect]
        self.data['freq'] = self.data['freq'][self._dataselect]

        self._utime, self._tidx = np.unique(self._n1['ti'], return_index=True)
        self._ufreq, self._fidx = np.unique(self._n1['fi'], return_index=True)
        self._uconf, self._cidx = np.unique(self._n1['ant'], return_index=True)
        self.data['time'] = self.data['time'][self._tidx]
        self.data['freq'] = self.data['freq'][self._fidx]
        self.data['conf'] = self._uconf.copy()
    
        self._dshape = (self._utime.size, self._ufreq.size, self._uconf.size)

        if self._dshape[0] == 0:
            # No data after the filters
            for dcol in self.dcol:
                self.data[dcol] = np.empty(self._dshape)
            return

        possibl_combi = list(itertools.product(self._utime, self._ufreq, self._uconf))
        current_combi = [(tt, ff, cc) for tt, ff, cc in zip(self._n1['ti'], self._n1['fi'], self._n1['ant'])]
        possibl_combi = np.array(possibl_combi)
        current_combi = np.array(current_combi)
        possibl_label = self._makelabel([possibl_combi[:, 0], possibl_combi[:, 1], possibl_combi[:, 2]])
        current_label = self._makelabel([current_combi[:, 0], current_combi[:, 1], current_combi[:, 2]])
        idx_mask = np.in1d(possibl_label, current_label)
        self._insertidx = np.arange( len(possibl_combi) )[~idx_mask]
        self._insertidx -= np.arange(self._insertidx.size)

        print("\t...done.")

        return
    
    # --------------------------------------------------------------------------------- #
    def _returndata(self):
        """
        """
        if self._dshape[0] == 0:
            return

        if self.level == 'n1':
            for dcol in self.dcol:
                self.data[dcol] = np.insert(self._n1[dcol], self._insertidx, 0)
                self.data[dcol][self._insertidx] = np.ma.masked # cannot fill an integer array with NaN
                self.data[dcol] = self.data[dcol].reshape(self._dshape)

        elif self.level == 'n2':
            assert len(self.conf) == 1, 'multiple conf not allowed for now'
            for dcol in self.dcol:                
                self.data[dcol] = np.insert(self._n2[dcol], self._insertidx, 0)
                self.data[dcol][self._insertidx] = np.ma.masked # cannot fill an integer array with NaN
                self.data[dcol] = self.data[dcol].reshape(self._dshape)

        elif self.level in ['n3b', 'n3c']:
            assert sorted(self.data['conf'])==[11, 12], "\n\t--> 'conf' attribute: must be [11, 12] for n3b/c levels. <--"
            self.data['conf'] = np.array(['11-12'])  
            
            n3 = self._readdata()

            n3nu0_label = self._makelabel([ n3['ydh'], n3['num'][:, 0] ])
            n3nu1_label = self._makelabel([ n3['ydh'], n3['num'][:, 1] ])
            n1num_label = self._makelabel([ self._n1['ydh'], self._n1['num'] ])

            mask1 = np.in1d(n3nu0_label, n1num_label)
            mask2 = np.in1d(n3nu1_label, n1num_label)
            subset_mask = mask1 & mask2

            for dcol in self.dcol:
                self.data[dcol] = np.insert(n3[dcol][subset_mask], self._insertidx, 0)
                self.data[dcol][self._insertidx] = np.ma.masked # cannot fill an integer array with NaN
                if not n3.dtype.fields[dcol][0].shape == (2,):
                    shape = (self._dshape[0], self._dshape[1], 1)
                else:
                    shape = self._dshape
                self.data[dcol] = self.data[dcol].reshape(shape)

        elif self.level in ['n3d', 'n3e']:
            assert len(self.conf) == 1, 'multiple conf not allowed for now'
            n3 = self._readdata()

            n3num_label = self._makelabel([ n3['ydh'], n3['num'][:, 0] ])
            n1num_label = self._makelabel([ self._n1['ydh'], self._n1['num'] ])
            subset_mask = np.in1d(n3num_label, n1num_label)

            for dcol in self.dcol:
                self.data[dcol] = np.insert(n3[dcol][subset_mask], self._insertidx, 0)
                self.data[dcol][self._insertidx] = np.ma.masked # cannot fill an integer array with NaN
                self.data[dcol] = self.data[dcol].reshape(self._dshape)

        else:
            pass

        return

    # --------------------------------------------------------------------------------- #
    def _makelabel(self, array):
        """ Stack all arguments as strings with a '-' between them
        """
        label = array[0].astype(str)
        join = np.repeat('-', label.size)
        for elem in array[1:]:
            label = np.core.defchararray.add(label, join)
            elem = elem.astype(str)
            label = np.core.defchararray.add(label, elem)
        return label
    # ================================================================================= #



# --------- Examples --------- #

#c = Cassini()
#c.load(time=['2012-06-29 15:00:00', '2012-06-29 16:20:00'], level='n2', dcol=['autoX'], conf=[3])
# c.load(time=['2012-06-29 09:00:01', '2012-06-29 23:59:59'], level='n2', dcol=['autoX'], conf=[3, 11])
#c.write_cdf('/root/aloh/cassini/test.cdf')

# d = Cassini()
# d.load(time=['2012-06-29 16:00:00', '2012-06-29 16:30:00'], level='n3b', dcol=['crossR', 'crossI'], conf=[3])
# c = c+d

# c.plot()

