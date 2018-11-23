#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
"""

import numpy as np
import copy

# =================================================================== #
# ---------------------------- DataAxis ----------------------------- #
# =================================================================== #
class DataAxis(object):
    """ 
        Parameters
        ----------
        name: `str`
            Axis name
        value: `list` or `np.ndarray`
            Axis values
        dtype: `str`
            Type of data axis
        axis: `int`
            Corresponding data axis
    """

    def __init__(self, name, value, dtype, axisn=0):
        self._name = None
        self._value = None
        self._dtype = None
        self._axis = None

        self.name = name
        self.value = value
        self.dtype = dtype 
        self.axis = axisn


    def __repr__(self):
        """ Allow for printing the data
        """
        return self.value.__repr__()


    @property
    def name(self):
        """ Name of data axis

            Parameters
            ----------
            name: `str`
                Choose a name for this data axis
        """
        return self._name
    @name.setter
    def name(self, name):
        assert isinstance(name, str), 'Name must be a string.'
        
        self._name = name
        return


    @property
    def value(self):
        """ Axis values

            Parameters
            ----------
            value: `list` or `np.ndarray`
                Values of data axis
        """
        return self._value
    @value.setter
    def value(self, value):
        if isinstance(value, list):
            value = np.array(value)

        assert hasattr(value, 'size'), 'Value must be numpy.ndarray compatible'

        self._value = value

        return

    @property
    def dtype(self):
        """ Type of data axis

            Parameters
            ----------
            dtype: `str`
                Must be `'freq'`, `'time'` or `'pola'`
        """
        return self._dtype
    @dtype.setter
    def dtype(self, dtype):
        dtype = dtype.lower()
        
        allowed_types = ['freq', 'time', 'pola'] # polar --> parameter
        assert dtype in allowed_types, 'dtype should be either {}.'.format(allowed_types)
        
        self._dtype = dtype
        return


    @property
    def axis(self):
        """ Corresponding data axis

            Parameters
            ----------
            axis: `int`
                Axis index
        """
        return self._axis
    @axis.setter
    def axis(self, axis):
        assert isinstance(axis, int), 'Axis index must be integer'

        self._axis = axis

        return


# =================================================================== #
# ---------------------------- RadioData ---------------------------- #
# =================================================================== #
class RadioData(object):
    """ 
        Parameters
        ----------
        data: `list` or `np.ndarray`
            The main data
        axes: `list`
            List of tuples of shape `(name, value, dtype, axis)`
            e.g. `[('time axis', array, 'time', 0)]`
    """

    def __init__(self, data, axes, meta=None):
        self._data = None
        self._axes = None

        self.data_shape = None

        self.data = data
        self.axes = axes
        self.meta = meta


    def __getitem__(self, given):
        if isinstance(given, slice):
            # Cool, nothing to add
           pass

        elif isinstance(given, tuple):
            # Every tuple element must be a slice
            assert all([isinstance(giv, (slice, np.ndarray)) for giv in given]), 'Index syntax error'

            # Make sure to not lose a dimension when slicing
            tmp_given = []
            for i in range(len(given)):
                if isinstance(given[i], np.ndarray):
                    if given[i][given[i] == True].size == 1:
                        true_index = np.where(given[i])[0][0]
                        tmp_given.append(slice(true_index, true_index+1, None))
                        continue
                tmp_given.append(given[i])
            given = tuple(tmp_given)

        else:
            # Just a plain index
            assert isinstance(given, int), 'Must be an integer'
        
        if isinstance(given, tuple):
            new_axes = []
            for i, ax in enumerate(self.axes):
                new_ax = (ax.name, ax.value[given[i]], ax.dtype, ax.axis)
                new_axes.append(new_ax)
        else:
            ax = self.axes[0]
            new_axes = [(ax.name, ax.value[given], ax.dtype, ax.axis)]

        # new_data = copy.copy(self.data[given]) # this isnt a pointer
        new_data = self.data[given] # this is a pointer
        # for i in range(len(given)):
        #     new_data[]

        return self.__class__(new_data, new_axes, self.meta)


    def __repr__(self):
        """ Allow for printing the data
        """
        return self.data.__repr__()


    def __getattr__(self, att):
        """ Is called when an attribute is not found
        """
        print("No '{}' attribute.".format(att))
        return


    def __setattr__(self, att, val):
        """ Is called when an attribute is filled
        """
        object.__setattr__(self, att, val)
        # if not att.startswith('_'):
        #     print("Attribute '{}' filled".format(att))
        return


    @property
    def data(self):
        """
            Parameters
            ----------
            data: `list` or `np.ndarray`
                The main data
        """
        return self._data
    @data.setter
    def data(self, data):
        if isinstance(data, list):
            data = np.array(data)

        self._data = data
        self.data_shape = data.shape
        return


    @property
    def axes(self):
        """
            Parameters
            ----------
            axes: `list`
                List of tuples of shape `(name, value, dtype, axis)`
                e.g. `[('time axis', array, 'time', 0)]`
        """
        return self._axes
    @axes.setter
    def axes(self, axes):
        assert isinstance(axes, list), 'Axes must be a list'

        assert all([isinstance(ax, tuple) for ax in axes]), 'Each axis must be a tuple'

        assert all([len(ax) == 4 for ax in axes]), 'Each axis must be a length-4 tuple'

        assert len(axes) == len(self.data_shape), 'Inconsistent number of axes'

        for ax in range(len(self.data_shape)):
            assert axes[ax][1].size == self.data_shape[ax], 'Inconstent axis size'

            axes[ax] = DataAxis(name=axes[ax][0], value=axes[ax][1], dtype=axes[ax][2], axisn=axes[ax][3])

        self._axes = axes
        return


    @property
    def shape(self):
        """
            Returns the shape of the RadioData object main data
        """
        return self.data_shape


    def set_time(self, bounds):
        """ Set time limits

            Parameters
            ----------
            bounds: `tuple`
                Time boundaries definition (e.g. `(tmin, tmax)`)
        """
        return


    def _check_data(self):
        """ Check that the data and axes are properly defined
        """
        return
