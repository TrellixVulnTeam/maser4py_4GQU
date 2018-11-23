#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
    Class to handle ExPRES simulation CDF files
"""

import os
import glob
import numpy as np
from astropy.time import Time, TimeDelta
from astropy import units as u
# import astropy.wcs

from spacepy.pycdf import CDF
# from ndcube import NDCube
# from maser.data import MaserError, MaserDataSweep # MaserDataFromFile
from rfdata import RadioData

__author__ = 'Alan Loh'
__date__ = "07-NOV-2018"
__version__ = '0.0.1'
__all__ = ['ExPRES']


class ExPRES(object):
    """ A doctring

        Parameters
        ----------
        cdffile : `str` or `list`
            blablabla
        tmin :
            blablabla
        tmax :
            blablabla
    """

    def __init__(self, cdffile):
        self._cdffile = None
        self._tmin = None
        self._tmax = None
        self._fmin = None
        self._fmax = None
        self._pola = None

        self.propdict = None

        self.cdffile = cdffile
        self.dcube = None
        self.data = None

        self.tmin = None
        self.tmax = None
        self.fmin = None
        self.fmax = None
        self.pola = None


    def __setattr__(self, att, val):
        """ Is called when an attribute is filled
        """
        object.__setattr__(self, att, val)

        # if (att.startswith('tmin') or att.startswith('tmax')) and val is not None:
        #     print('{} filled to {}'.format(att, val))
        # elif (att.startswith('fmin') or att.startswith('fmax')) and val is not None:
        #     print('{} filled to {}'.format(att, val))
        # else:
        #     pass

        return


    @property
    def cdffile(self):
        """ A docstring
        """
        cdfs = []

        for cdf in sorted(self._cdffile):
            cdfdict = self.propdict[os.path.basename(cdf)]

            if (cdfdict['tmin'] >= self.tmin) & (cdfdict['tmax'] <= self.tmax):
                cdfs.append(cdf)

            elif (cdfdict['tmin'] <= self.tmin) & (cdfdict['tmax'] >= self.tmax):
                cdfs.append(cdf)

            elif (cdfdict['tmax'] >= self.tmin) & (cdfdict['tmax'] <= self.tmax):
                cdfs.append(cdf)

            elif (cdfdict['tmin'] >= self.tmin) & (cdfdict['tmin'] <= self.tmax):
                cdfs.append(cdf)

            else:
                pass

        return cdfs
    @cdffile.setter
    def cdffile(self, cdf):
        if isinstance(cdf, str) and not os.path.isfile(cdf):
            # This is a dataset
            cdf = glob.glob(cdf + '*')

        if not isinstance(cdf, list):
            cdf = [cdf]

        assert all([os.path.isfile(ci) for ci in cdf]), 'Some files were not found'
        assert all([ci.lower().endswith('cdf') for ci in cdf]), 'Some files are not CDF files'

        self._cdffile = cdf
        self._properties()

        return


    @property
    def tmin(self):
        """ A docstring
        """
        return self._tmin
    @tmin.setter
    def tmin(self, timemin):
        if timemin is None:
            timemin = self.get_tmin

        if isinstance(timemin, str):
            try:
                timemin = Time(timemin)
            except:
                raise ValueError('Use time format YYYY-MM-DDThh:mm:ss')

        assert isinstance(timemin, Time), 'Wrong time format'

        assert timemin >= self.get_tmin, 'Time min should be >= {}'.format(self.get_tmin)

        assert timemin < self.get_tmax, 'Time min should be < {}'.format(self.get_tmax)

        self._tmin = timemin
        return


    @property
    def tmax(self):
        """ A docstring
        """
        return self._tmax
    @tmax.setter
    def tmax(self, timemax):
        if timemax is None:
            timemax = self.get_tmax

        if isinstance(timemax, str):
            try:
                timemax = Time(timemax)
            except:
                raise ValueError('Use time format YYYY-MM-DDThh:mm:ss')

        assert isinstance(timemax, Time), 'Wrong time format'

        assert timemax <= self.get_tmax, 'Time max should be <= {}'.format(self.get_tmax)

        assert timemax > self.get_tmin, 'Time max should be > {}'.format(self.get_tmin)

        self._tmax = timemax
        return


    @property
    def fmin(self):
        """ A docstring
        """
        return self._fmin
    @fmin.setter
    def fmin(self, freqmin):
        if freqmin is None:
            freqmin = self.get_fmin

        assert freqmin >= self.get_fmin, 'Freq min should be >= {}'.format(self.get_fmin)

        assert freqmin < self.get_fmax, 'Freq min should be < {}'.format(self.get_fmax)

        self._fmin = freqmin
        return


    @property
    def fmax(self):
        """ A docstring
        """
        return self._fmax
    @fmax.setter
    def fmax(self, freqmax):
        if freqmax is None:
            freqmax = self.get_fmax

        assert freqmax <= self.get_fmax, 'Freq max should be <= {}'.format(self.get_fmax)

        assert freqmax > self.get_fmin, 'Freq max should be > {}'.format(self.get_fmin)

        self._fmax = freqmax
        return


    @property
    def pola(self):
        """ A docstring
        """
        return self._pola
    @pola.setter
    def pola(self, polar):
        available = [self.propdict[k]['pols'] for k in self.propdict][0]
        if polar is None:
            polar = available[0]

        assert polar in available, 'Unknown polarization'

        self._pola = polar
        return


    @property
    def get_tmin(self):
        """ A docstring
        """
        tmin = min([self.propdict[k]['tmin'] for k in self.propdict])
        return tmin


    @property
    def get_tmax(self):
        """ A docstring
        """
        tmax = max([self.propdict[k]['tmax'] for k in self.propdict])
        return tmax


    @property
    def get_fmin(self):
        """ A docstring
        """
        fmin = min([self.propdict[k]['fmin'] for k in self.propdict])
        return fmin


    @property
    def get_fmax(self):
        """ A docstring
        """
        fmax = max([self.propdict[k]['fmax'] for k in self.propdict])
        return fmax


    @property
    def get_fstep(self):
        """ A docstring
        """
        steps = [self.propdict[k]['df'] for k in self.propdict]
        assert all([stepi == steps[0] for stepi in steps]), 'Freq steps are not equal for all files'
        return steps[0]


    # def load_v0(self, var='Theta'):
    #     """ Load the data
    #     """
    #     for cdffile in sorted(self.cdffile):
    #         with CDF(cdffile) as cdf:
    #             if not 'data' in locals():
    #                 data = cdf[var][:, :, :]
    #             else:
    #                 # concatenate
    #                 data = np.vstack((data, cdf[var][:, :, :]))

    #             if not 'time' in locals():
    #                 time = cdf['Epoch'][:]
    #             else:
    #                 # concatenate
    #                 time = np.hstack((time, cdf['Epoch'][:]))

    #             freq = cdf['Frequency'][:]
    #             hems = np.array(['North', 'South'])

    #     time = np.array([(timei - time[0]).total_seconds() for timei in time])

    #     wcs_input_dict = {
    #         'CTYPE3': 'TIME',
    #         'CUNIT3': 's',
    #         'CDELT3': 60,
    #         'CRPIX3': 1,
    #         'CRVAL3': time[0],
    #         'NAXIS3': data.shape[0],
    #         'CTYPE2': 'FREQ',
    #         'CUNIT2': 'MHz',
    #         'CDELT2': self.get_fstep.value,
    #         'CRPIX2': 1,
    #         'CRVAL2': self.get_fmin.value,
    #         'NAXIS2': data.shape[1],
    #         'CTYPE1': 'POLA',
    #         'CUNIT1': '',
    #         'CDELT1': 1,
    #         'CRPIX1': 1,
    #         'CRVAL1': 0,
    #         'NAXIS1': data.shape[2]}
    #     input_wcs = astropy.wcs.WCS(wcs_input_dict)

    #     # extra_c = [('time', 0, time),
    #     #            ('frequency', 1, freq),
    #     #            ('hemisphere', 2, hems)]

    #     # self.dcube = NDCube(data, input_wcs, extra_coords=extra_c, unit=u.deg)

    #     self.dcube = NDCube(data, input_wcs, unit=u.deg)

    #   return


    def load(self, var='Theta', **kwargs):
        """ Load the data
        """
        for key, value in kwargs.items():
            if key == 'tmin':
                self.tmin = value

            elif key == 'tmax':
                self.tmax = value

            elif key == 'fmin':
                self.fmin = value

            elif key == 'fmax':
                self.fmax = value

            elif key == 'pola':
                self.pola = value

            else:
                pass

        for cdffile in sorted(self.cdffile):
            with CDF(cdffile) as cdf:
                if not 'data' in locals():
                    data = cdf[var][:, :, :]
                else:
                    # concatenate
                    data = np.vstack((data, cdf[var][:, :, :]))

                if not 'time' in locals():
                    time = cdf['Epoch'][:]
                else:
                    # concatenate
                    time = np.hstack((time, cdf['Epoch'][:]))

                freq = cdf['Frequency'][:]
                hems = cdf['Src_ID_Label'][:] # np.array(['North', 'South'])

        main_data = data
        ax1 = ('time axis', Time(time), 'time', 0)
        ax2 = ('freq axis', freq * u.MHz, 'freq', 1)
        ax3 = ('hemisphere', hems, 'pola', 2)
        data_axes = [ax1, ax2, ax3]

        self.dcube = RadioData(data=main_data, axes=data_axes, meta=None)

        t_mask = self.time_mask()
        f_mask = self.freq_mask()
        p_mask = self.polar_mask()

        # self.data = self.dcube[t_mask, f_mask, p_mask]
        self.data = self.dcube[t_mask, :, :]
        self.data = self.data[:, f_mask, :]
        self.data = self.data[:, :, p_mask]
        return


    def time_mask(self):
        """ A docstring
        """
        assert self.dcube.axes[0].dtype == 'time', 'Not a time axis'
        geq_tmin = self.dcube.axes[0].value >= self.tmin
        leq_tmax = self.dcube.axes[0].value <= self.tmax

        return geq_tmin & leq_tmax


    def freq_mask(self):
        """ A docstring
        """
        assert self.dcube.axes[1].dtype == 'freq', 'Not a frequency axis'
        geq_fmin = self.dcube.axes[1].value >= self.fmin
        leq_fmax = self.dcube.axes[1].value <= self.fmax

        return geq_fmin & leq_fmax


    def polar_mask(self):
        """ A docstring
        """
        assert self.dcube.axes[2].dtype == 'pola', 'Not a polarization axis'
        polar_mask = self.dcube.axes[2].value == self.pola

        return polar_mask


    def _properties(self):
        """ A docstring
        """
        self.propdict = {}
        for cdffile in self._cdffile:
            with CDF(cdffile) as cdf:
                cdft = cdf['Epoch'].attrs
                tmin = Time(cdft['SCALEMIN'])
                tmax = Time(cdft['SCALEMAX'])
                tstep = TimeDelta(cdf.attrs['VESPA_time_sampling_step'][0], format='sec')

                cdff = cdf['Frequency'].attrs
                assert cdff['UNITS'].lower() == 'mhz', 'Frequency unit not understood'
                funit = u.MHz
                fmin = cdff['SCALEMIN'] * funit
                fmax = cdff['SCALEMAX'] * funit
                assert cdff['SCALETYP'].lower() == 'linear', 'Freq scaling is not linear'
                fstep = (fmax - fmin) / (cdf['Frequency'].shape[0] - 1)

                filename = os.path.basename(cdffile)

                self.propdict[filename] = {'dt': tstep,
                                           'tmin': tmin,
                                           'tmax': tmax,
                                           'df': fstep,
                                           'fmin': fmin,
                                           'fmax': fmax,
                                           'pols': cdf['Src_ID_Label'][:]}

        return
