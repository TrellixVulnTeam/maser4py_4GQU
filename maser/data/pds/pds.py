#! /usr/bin/env python
# -*- coding: latin-1 -*-

"""
Python module to work with PDS Data
@author: B.Cecconi(LESIA)
"""

import struct
import datetime
import os
import numpy
from maser.data.data import MaserDataFromFile, MaserError, MaserData
from maser.data.pds.ppi.voyager import *

__author__ = "Baptiste Cecconi"
__copyright__ = "Copyright 2017, LESIA-PADC, Observatoire de Paris"
__credits__ = ["Baptiste Cecconi"]
__license__ = "GPLv3"
__version__ = "1.0b2"
__maintainer__ = "Baptiste Cecconi"
__email__ = "baptiste.cecconi@obspm.fr"
__status__ = "Production"
__date__ = "27-FEB-2018"
__project__ = "MASER/PADC PDS"

__all__ = ["PDSDataFromLabel"]


class PDSLabelDict(dict):
    """
    Class for the dict-form PDSLabel
    """

    class _PDSLabelList(list):
        """
        Class for the list-form PDSLabel (internal class, not accessible from outside)
        """

        def __init__(self, label_file, verbose=False, debug=False):
            list.__init__(self)
            self.debug = debug
            self.verbose = verbose
            self.file = label_file
            self.process = list()
            self._load_pds3_label_as_list()
            self._merge_multiple_line_values()
            self._add_object_depth_to_label_list()
            if self.verbose:
                print(self.process)

        def _load_pds3_label_as_list(self, input_file=None):
            """
            This method loads label lines as pairs of (key, value) separated by "=", excluding comments.
            The method recursively loads any other .FMT files, for each ^STRUCTURE key.
            """

            # If no input_file is set, retrieve current PDSLabelList file from self
            if input_file is None:
                input_file = self.file

            # Opening input_file and looping through lines
            with open(input_file, 'r') as f:

                if self.debug:
                    print("Reading from {}".format(input_file))

                for line in f.readlines():

                    if self.debug:
                        print(line)

                    # if end of label file tag, then stop the loop
                    if line.strip() == "END":
                        break

                    # skipping comment lines and empty lines
                    elif line.startswith('/*') or line.strip() == '':
                        if self.debug:
                            print("... skipping.")
                        continue

                    # processing "key = value" lines
                    elif '=' in line:
                        kv = line.strip().split('=')
                        cur_key = kv[0].strip()
                        cur_val = kv[1].strip().strip('"')
                        if self.debug:
                            print("... key = {}, value = {}".format(cur_key, cur_val))

                        # in case of external FMT file, nested call to this function with the FMT file
                        if cur_key == '^STRUCTURE':
                            extra_file = os.path.join(os.path.dirname(input_file), cur_val.strip('"'))
                            if self.verbose:
                                print("Inserting external Label from {}".format(extra_file))
                            self._load_pds3_label_as_list(extra_file)

                        # regular case: just write out a new line with (key, value)
                        else:
                            self.append((cur_key, cur_val))

                    # special case for multiple line values
                    else:
                        self.append(("", line.strip().strip('"')))

            self.process.append('Loaded from file')

        def _merge_multiple_line_values(self):
            """
            This method merges multiple line values
            """

            prev_ii = 0
            remove_list = []

            # looping on Label list item, with enumerate, so that we get the item index in the list
            for ii, item in enumerate(self.__iter__()):
                (cur_key, cur_value) = item

                # in case of multiple line values, key is an empty string
                if cur_key == '':

                    # fetching last previous line with non empty key
                    (prev_key, prev_value) = self[prev_ii]
                    cur_value = "{} {}".format(prev_value, cur_value)

                    # appending current value to value of previous line with non empty key
                    self[prev_ii] = (prev_key, cur_value)

                    # flag the current line for deletion
                    remove_list.append(ii)

                # general case: non empty key
                else:
                    prev_ii = ii

            # remove lines flagged for deletion
            if len(remove_list) > 0:
                for ii in sorted(remove_list, reverse=True):
                    del self[ii]

            self.process.append('Merged multi line')

        def _add_object_depth_to_label_list(self):
            """Adds an extra elements after in each (key, value) containing the current object depth"""

            depth = []
            remove_list = []

            for ii, item in enumerate(self.__iter__()):
                (cur_key, cur_value) = item

                # flag END_OBJECT line and removing the last element of the depth list
                if cur_key == 'END_OBJECT':
                    remove_list.append(ii)
                    del depth[-1]

                # process other lines by adding the current version of the depth list
                else:
                    self[ii] = (cur_key, cur_value, depth.copy())

                    # when we meet an OBJECT line, add the object name to the depth list
                    if cur_key == 'OBJECT':
                        depth.append(cur_value)

            # remove lines flagged for deletion
            if len(remove_list) > 0:
                for ii in sorted(remove_list, reverse=True):
                    del self[ii]

            self.process.append('Added depth tag')

    def __init__(self, label_file, verbose=False, debug=False):
        dict.__init__(self)
        self.debug = debug
        self.verbose = verbose
        self.file = label_file
        label_list = self._PDSLabelList(self.file, self.verbose, self.debug)
        self.process = label_list.process
        self._label_list_to_dict(label_list)

    def _label_list_to_dict(self, label_list):
        """This function transforms PDS3 Label list into a PDS3 Label dict"""

        for item in label_list:
            (cur_key, cur_value, cur_depth) = item

            cur_dict = self
            if len(cur_depth) > 0:
                for cur_depth_item in cur_depth:
                    cur_dict = cur_dict[cur_depth_item][-1]

            if cur_key == 'OBJECT':
                if self.verbose:
                    print('Creating {} Object'.format(cur_value))
                if cur_value not in cur_dict.keys():
                    cur_dict[cur_value] = [dict()]
                else:
                    cur_dict[cur_value].append(dict())
            else:
                if self.verbose:
                    print('Inserting {} keyword with value {}'.format(cur_key, cur_value))
                cur_dict[cur_key] = cur_value

        self.process.append('Converted to dict')


class PDSError(MaserError):
    pass


class PDSDataObject(MaserDataFromFile):
    def __init__(self, product, parent, obj_label, obj_name, verbose=False, debug=False):
        self.verbose = verbose
        self.debug = debug
        self.product = product
        self.parent = parent
        self.obj_type = obj_name
        self.label = obj_label
        data_file = product.pointers[obj_name]
        MaserDataFromFile.__init__(self, data_file, verbose, debug)
        self.data = self.data_from_object_type()

    def data_from_object_type(self):
        if self.obj_type == 'TABLE':
            return PDSDataTableObject(self.product, self, self.label, self.verbose, self.debug)
        else:
            raise PDSError('Object type {} not yet implemented'.format(self.obj_type))

    def load_data(self):
        self.data.load_data()


class PDSDataFromLabel(MaserDataFromFile):
    """
    This object contains PDS3 archive data, loaded from their label file.
    This is MaserDataFromFile object, based on the label file.
    Attributes:
        label: parsed label data mapped into a dictionary (PDSLabelDict object)
        pointers: dict containing {pointer_name: pointer_file} elements
        objects: list of object names (pointers to data files)
        dataset_name: name of PDS3 archive volume
        header: header info (depending on each volume)
        object: dict containing {object_name: MaserDataFromFile(object_file)} elements
    Methods:
        _detect_pointers(self)
        _detect_data_object_type(self)
        _load_data(self)
        get_single_sweep(self, index)
        get_first_sweep(self)
        get_last_sweep(self)
    """

    def __init__(self, file, verbose=False, debug=False):

        if not file.lower().endswith('.lbl'):
            raise PDSError('Select label file instead of data file')

        self.debug = debug
        self.verbose = verbose
        self.label_file = file
        MaserDataFromFile.__init__(self, file, verbose, debug)

        self.label = PDSLabelDict(self.label_file, verbose, debug)
        self.pointers = self._detect_pointers()
        self.objects = self._detect_data_object_type()
        self.dataset_name = self.label['DATA_SET_ID'].strip('"')
        self._fix_object_label_entries()

        self.header = None
        self.object = {}

        for cur_data_obj in self.objects:

            if self.debug:
                print("Processing object: {}".format(cur_data_obj))

            self.object[cur_data_obj] = PDSDataObject(self, self, self.label[cur_data_obj], cur_data_obj,
                                                      self.verbose, self.debug)

            if self.debug:
                print("Loading data into object: {}".format(cur_data_obj))

            self.object[cur_data_obj].load_data()

    def _detect_pointers(self):
        pointers = {}
        for key in self.label.keys():
            if key.startswith('^'):
                value = self.label[key]
                if value.startswith('('):
                    basename = value.split('"')[1]
                else:
                    basename = value
                pointers[key[1:]] = os.path.join(os.path.dirname(self.file), basename)

        if self.debug:
            print("Pointer(s) found: {}".format(', '.join(list(pointers.keys()))))

        return pointers

    def _detect_data_object_type(self):
        data_types = []
        for item in self.pointers.keys():
            if item in self.label.keys():
                data_types.append(item)

        if self.debug:
            print("Data type(s) found: {}".format(', '.join(data_types)))

        return data_types

    def _fix_object_label_entries(self):
        for item in self.objects:
            self.label[item] = self.label[item][0]

    def _load_data(self):
        for cur_data_obj in self.object.keys():
            self.object[cur_data_obj].load_data()

    def get_single_sweep(self, index):
        pass

    def get_first_sweep(self):
        return self.get_single_sweep(0)

    def get_last_sweep(self):
        return self.get_single_sweep(-1)


class PDSDataTableColumnHeaderObject:
    def __init__(self, product, parent, column_label, verbose=False, debug=False):
        self.verbose = verbose
        self.debug = debug
        self.product = product
        self.parent = parent
        self.n_rows = parent.n_rows
        self.label = column_label
        self.name = self.label['NAME']

        if 'ITEMS' in self.label.keys():
            self.n_items = int(self.label['ITEMS'])
        else:
            self.n_items = 1

        self.start_byte = int(self.label['START_BYTE'])
        self.bytes = int(self.label['BYTES'])

        if 'ITEM_BYTES' in self.label.keys():
            self.item_bytes = self.label['ITEM_BYTES']
        else:
            self.item_bytes = self.bytes

        self.struct_format = self._get_struct_format()
        if self.debug:
            print(self.struct_format)

        self.np_data_type = self._get_np_data_type()
        if self.debug:
            print(self.np_data_type)

    def _get_np_data_type(self):

        struct_to_np_data_type = {
            'b': numpy.int8,
            'B': numpy.uint8,
            'h': numpy.int16,
            'H': numpy.uint16,
            'l': numpy.int32,
            'L': numpy.uint32,
            'q': numpy.int64,
            'Q': numpy.uint64
        }
        return struct_to_np_data_type[self.struct_format[-1]]

    def _get_struct_format(self):

        data_type = ''
        endianess = ''

        if self.debug:
            print("Data type = {}".format(self.label['DATA_TYPE']))
            print("Item bytes= {}".format(self.item_bytes))

        if self.label['DATA_TYPE'].endswith('INTEGER'):
            if int(self.item_bytes) == 1:
                data_type = 'b'
            elif int(self.item_bytes) == 2:
                data_type = 'h'
            elif int(self.item_bytes) == 4:
                data_type = 'l'
            elif int(self.item_bytes) == 8:
                data_type = 'q'
            elif self.label['DATA_TYPE'].startswith('ASCII'):
                data_type = 'l'
        elif self.label['DATA_TYPE'].endswith('BIT_STRING'):
            if int(self.item_bytes) == 1:
                data_type = 'B'
        else:
            raise PDSError('Unknown (or not yet implemented) data type ({})'.format(self.label['DATA_TYPE']))

        if 'UNSIGNED' in self.label['DATA_TYPE']:
            data_type = data_type.upper()

        if self.label['DATA_TYPE'].startswith('MSB'):
            endianess = '>'
        elif self.label['DATA_TYPE'].startswith('LSB'):
            endianess = '<'

        return '{}{}{}'.format(endianess, self.n_items, data_type)


class PDSDataTableObject(dict):

    def __init__(self, product, parent, obj_label, verbose=False, debug=False):
        dict.__init__(self)
        self.verbose = verbose
        self.debug = debug
        self.product = product
        self.parent = parent
        self.label = obj_label
        self.n_columns = int(obj_label['COLUMNS'])
        self.n_rows = int(obj_label['ROWS'])
        self.columns = list()
        for col_label in obj_label['COLUMN']:
            self.columns.append(PDSDataTableColumnHeaderObject(self.product, self, col_label,
                                                               verbose=verbose, debug=debug))
        self._create_data_structure()

    def _create_data_structure(self):

        # Setting up columns
        for cur_col in self.columns:

            if cur_col.n_items == 1:
                self[cur_col.name] = numpy.zeros(self.n_rows, cur_col.np_data_type)
            else:
                self[cur_col.name] = numpy.zeros((self.n_rows, cur_col.n_items), cur_col.np_data_type)

            if self.debug:
                print("Column {} shape = {}".format(cur_col.name, str(numpy.shape(self[cur_col.name]))))

    def load_data(self):

        # Loading data into columns
        if self.label['INTERCHANGE_FORMAT'] == 'ASCII':
            self._load_data_ascii()
        elif self.label['INTERCHANGE_FORMAT'] == 'BINARY':
            self._load_data_binary()
        else:
            raise PDSError('Unknown interchange format ({})'.format(self.label['INTERCHANGE_FORMAT']))

    def _load_data_ascii(self):

        if self.debug:
            print("Starting ASCII read from {}".format(self.parent.file))

        with open(self.parent.file, 'r') as f:

            for ii, line in enumerate(f.readlines()):
                for cur_col in self.columns:
                    cur_name = cur_col.name
                    cur_byte_start = int(cur_col.start_byte) - 1
                    cur_byte_length = int(cur_col.bytes)
                    if cur_col.n_items == 1:
                        self[cur_name][ii] = line[cur_byte_start:cur_byte_start + cur_byte_length]
                    else:
                        for cur_item in range(cur_col.n_items):
                            self[cur_name][ii, cur_item] = line[cur_byte_start:cur_byte_start + cur_byte_length]
                            cur_byte_start += cur_byte_length

    def _load_data_binary(self):

        if self.debug:
            print("Starting BINARY read from {}".format(self.parent.file))

        with open(self.parent.file, 'rb') as f:

            buf_length = int(self.label['ROW_BYTES'])
            if 'ROW_PREFIX_BYTES' in self.label.keys():
                buf_length += int(self.label['ROW_PREFIX_BYTES'])
            if 'ROW_SUFFIX_BYTES' in self.label.keys():
                buf_length += int(self.label['ROW_SUFFIX_BYTES'])

            for ii in range(self.n_rows):

                buf_data = f.read(buf_length)

                for cur_col in self.columns:
                    cur_name = cur_col.name
                    cur_byte_start = int(cur_col.start_byte) - 1
                    cur_byte_length = int(cur_col.bytes)

                    line = struct.unpack(cur_col.struct_format, buf_data[cur_byte_start:cur_byte_start + cur_byte_length])

                    if cur_col.n_items == 1:
                        self[cur_name][ii] = line[0]
                    else:
                        self[cur_name][ii, :] = line


class PDSDataTimeSeriesObject(PDSDataTableObject):

    def __init__(self, product, parent, obj_label, verbose=True, debug=False):
        PDSDataTableObject.__init__(self, product, parent, obj_label, verbose=verbose, debug=debug)
