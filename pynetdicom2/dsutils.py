# Copyright (c) 2021 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#
"""
Helper module that provides function for converting datasets or dataset elements into
bytes and back.
"""
from io import BytesIO
from typing import Union

import pydicom
from pydicom import dataelem, filebase, filereader, filewriter




def decode(
        rawstr: bytes,
        is_implicit_vr: bool,
        is_little_endian: bool
) -> pydicom.Dataset:
    """Decodes dataset from raw bytes

    :param rawstr: raw bytes, containing dataset
    :param is_implicit_vr: is dataset in implicit VR
    :param is_little_endian: is dataset little endian-encoded
    :return: decoded dataset
    """
    fp = BytesIO(rawstr)
    return filereader.read_dataset(fp, is_implicit_vr, is_little_endian)


def encode(
        ds: pydicom.Dataset,
        is_implicit_vr: bool,
        is_little_endian: bool
) -> bytes:
    """Encoded dataset into raw bytes

    :param ds: dataset to encode
    :type ds: pydicom.Dataset
    :param is_implicit_vr: encode using implicit VR
    :type is_implicit_vr: bool
    :param is_little_endian: encode as little endian
    :type is_little_endian: bool
    :return: dataset encoded into raw bytes
    :rtype: bytes
    """
    fp = filebase.DicomBytesIO()
    fp.is_implicit_VR = is_implicit_vr
    fp.is_little_endian = is_little_endian
    filewriter.write_dataset(fp, ds)
    rawstr = fp.getvalue()
    fp.close()
    return rawstr


def encode_element(
        elem: Union[pydicom.DataElement, dataelem.RawDataElement],
        is_implicit_vr: bool,
        is_little_endian: bool
) -> bytes:
    """Encodes dataset element into raw bytes

    :param elem: dataset element to encode
    :type elem: pydicom.DataElement
    :param is_implicit_vr: encode using implicit VR
    :type is_implicit_vr: bool
    :param is_little_endian: encode as little endian
    :type is_little_endian: bool
    :return: dataset element encoded into raw bytes
    :rtype: bytes
    """
    fp = filebase.DicomBytesIO()
    fp.is_implicit_VR = is_implicit_vr
    fp.is_little_endian = is_little_endian
    filewriter.write_data_element(fp, elem)
    rawstr = fp.getvalue()
    fp.close()
    return rawstr
