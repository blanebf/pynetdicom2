# -*- coding: utf-8 -*-

# Copyright (c) 2014 Pavel 'Blane' Tuchin

"""
Compatibility layer for pre 1.0 pydicom
"""

try:
    import pydicom as dicom
except ImportError:
    # pre 1.0 pydicom
    import dicom

if dicom.__version_info__ >= ('1', '0', '0'):
    from pydicom import uid
    from pydicom.filewriter import write_file_meta_info as _write_file_meta
    from pydicom import filebase
    from pydicom import filereader
    from pydicom import filewriter
    from pydicom import dataset
    from pydicom import sequence

    from pydicom.filebase import DicomBytesIO as _DicomBytesIO

    def write_meta(fp, file_meta, enforce_standard=True):
        fp.write(b'DICM')
        _write_file_meta(fp, file_meta, enforce_standard)
else:
    from dicom import UID as uid
    from dicom.filewriter import _write_file_meta_info as write_meta
    from dicom import filebase
    from dicom import filereader
    from dicom import filewriter
    from dicom import dataset
    from dicom import sequence

    if dicom.__version_info__ >= (0, 9, 8):
        from dicom.filebase import DicomBytesIO as _DicomBytesIO
    else:
        from dicom.filebase import DicomStringIO as _DicomBytesIO


read_file = dicom.read_file

ExplicitVRLittleEndian = uid.ExplicitVRLittleEndian
ImplicitVRLittleEndian = uid.ImplicitVRLittleEndian
ExplicitVRBigEndian = uid.ExplicitVRBigEndian
UID = uid.UID

write_file_meta_info = write_meta
DicomBytesIO = _DicomBytesIO

DicomFileLike = filebase.DicomFileLike

read_preamble = filereader.read_preamble
read_file_meta_info = filereader._read_file_meta_info
read_dataset = filereader.read_dataset

write_dataset = filewriter.write_dataset
write_data_element = filewriter.write_data_element

Dataset = dataset.Dataset
Sequence = sequence.Sequence
