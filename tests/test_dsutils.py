"""Unit tests for :mod:`pynetdicom2.dsutils`."""
import unittest

import pydicom
from pydicom import dataelem

from pynetdicom2 import dsutils


class EncodeDecodeRoundTripTestCase(unittest.TestCase):
    def _make_dataset(self) -> pydicom.Dataset:
        ds = pydicom.Dataset()
        ds.PatientName = 'Doe^John'
        ds.PatientID = 'ID-123'
        ds.StudyInstanceUID = '1.2.3.4.5'
        return ds

    def _roundtrip(self, implicit: bool, little: bool) -> None:
        ds = self._make_dataset()
        raw = dsutils.encode(ds, implicit, little)
        self.assertIsInstance(raw, bytes)
        decoded = dsutils.decode(raw, implicit, little)
        self.assertEqual(decoded.PatientName, ds.PatientName)
        self.assertEqual(decoded.PatientID, ds.PatientID)
        self.assertEqual(decoded.StudyInstanceUID, ds.StudyInstanceUID)

    def test_implicit_vr_little_endian(self) -> None:
        self._roundtrip(implicit=True, little=True)

    def test_explicit_vr_little_endian(self) -> None:
        self._roundtrip(implicit=False, little=True)

    def test_explicit_vr_big_endian(self) -> None:
        self._roundtrip(implicit=False, little=False)

    def test_empty_dataset(self) -> None:
        raw = dsutils.encode(pydicom.Dataset(), True, True)
        self.assertEqual(raw, b'')
        decoded = dsutils.decode(raw, True, True)
        self.assertEqual(len(decoded), 0)

    def test_encode_element(self) -> None:
        elem = dataelem.DataElement(0x00100010, 'PN', 'Doe^John')
        raw = dsutils.encode_element(elem, False, True)
        self.assertIsInstance(raw, bytes)
        self.assertGreater(len(raw), 0)


if __name__ == '__main__':
    unittest.main()
