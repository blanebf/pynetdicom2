# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#
from pydicom import filebase
from pydicom import filereader
from pydicom import filewriter
import six
if six.PY3:
    from six import BytesIO as cStringIO
else:
    from six.moves import cStringIO  # type: ignore


def decode(rawstr, is_implicit_vr, is_little_endian):
    fp = cStringIO(rawstr)
    return filereader.read_dataset(fp, is_implicit_vr, is_little_endian)


def encode(ds, is_implicit_vr, is_little_endian):
    fp = filebase.DicomBytesIO()
    fp.is_implicit_VR = is_implicit_vr
    fp.is_little_endian = is_little_endian
    filewriter.write_dataset(fp, ds)
    rawstr = fp.parent.getvalue()
    fp.close()
    return rawstr


def encode_element(el, is_implicit_vr, is_little_endian):
    fp = filebase.DicomBytesIO()
    fp.is_implicit_VR = is_implicit_vr
    fp.is_little_endian = is_little_endian
    filewriter.write_data_element(fp, el)
    rawstr = fp.parent.getvalue()
    fp.close()
    return rawstr
