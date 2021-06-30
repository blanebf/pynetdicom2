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
import pydicom  # pylint: disable=unused-import
from pydicom import filebase
from pydicom import filereader
from pydicom import filewriter
import six
if six.PY3:
    from six import BytesIO as cStringIO
else:
    from six.moves import cStringIO  # type: ignore


def decode(rawstr, is_implicit_vr, is_little_endian):
    # type: (bytes,bool,bool) -> pydicom.Dataset
    """Decodes dataset from raw bytes

    :param rawstr: raw bytes, containing dataset
    :type rawstr: bytes
    :param is_implicit_vr: is dataset in implicit VR
    :type is_implicit_vr: bool
    :param is_little_endian: is dataset little endian-encoded
    :type is_little_endian: bool
    :return: decoded dataset
    :rtype: pydicom.Dataset
    """
    fp = cStringIO(rawstr)  # type: ignore
    return filereader.read_dataset(fp, is_implicit_vr, is_little_endian)


def encode(ds, is_implicit_vr, is_little_endian):
    # type: (pydicom.Dataset,bool,bool) -> bytes
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
    rawstr = fp.parent.getvalue()
    fp.close()
    return rawstr


def encode_element(elem, is_implicit_vr, is_little_endian):
    # type: (pydicom.DataElement,bool,bool) -> bytes
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
    rawstr = fp.parent.getvalue()
    fp.close()
    return rawstr
