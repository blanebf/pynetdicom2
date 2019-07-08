# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

from . import _dicom
import six
if six.PY3:
    from six import BytesIO as cStringIO
else:
    from six.moves import cStringIO


def decode(rawstr, is_implicit_vr, is_little_endian):
    s = cStringIO(rawstr)
    return _dicom.read_dataset(s, is_implicit_vr, is_little_endian)


def encode(ds, is_implicit_vr, is_little_endian):
    f = _dicom.DicomBytesIO()
    f.is_implicit_VR = is_implicit_vr
    f.is_little_endian = is_little_endian
    _dicom.write_dataset(f, ds)
    rawstr = f.parent.getvalue()
    f.close()
    return rawstr


def encode_element(el, is_implicit_vr, is_little_endian):
    f = _dicom.DicomBytesIO()
    f.is_implicit_VR = is_implicit_vr
    f.is_little_endian = is_little_endian
    _dicom.write_data_element(f, el)
    rawstr = f.parent.getvalue()
    f.close()
    return rawstr
