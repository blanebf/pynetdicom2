"""Unit tests for :mod:`pynetdicom2.exceptions`."""
import unittest

from pynetdicom2 import exceptions


class ExceptionHierarchyTestCase(unittest.TestCase):
    def test_all_exceptions_derive_from_net_dicom_error(self) -> None:
        for exc_type in (
            exceptions.ClassNotSupportedError,
            exceptions.PDUProcessingError,
            exceptions.DIMSEProcessingError,
            exceptions.AssociationError,
            exceptions.AssociationRejectedError,
            exceptions.AssociationReleasedError,
            exceptions.AssociationAbortedError,
            exceptions.DCMTimeoutError,
            exceptions.EventHandlingError
        ):
            with self.subTest(exc=exc_type):
                self.assertTrue(
                    issubclass(exc_type, exceptions.NetDICOMError)
                )


class AssociationRejectedErrorTestCase(unittest.TestCase):
    def test_attributes_are_stored(self) -> None:
        exc = exceptions.AssociationRejectedError(1, 2, 3)
        self.assertEqual(exc.result, 1)
        self.assertEqual(exc.source, 2)
        self.assertEqual(exc.diagnostic, 3)

    def test_is_association_error(self) -> None:
        exc = exceptions.AssociationRejectedError(1, 1, 1)
        self.assertIsInstance(exc, exceptions.AssociationError)


class AssociationAbortedErrorTestCase(unittest.TestCase):
    def test_attributes_are_stored(self) -> None:
        exc = exceptions.AssociationAbortedError(2, 4)
        self.assertEqual(exc.source, 2)
        self.assertEqual(exc.reason_diag, 4)

    def test_is_association_error(self) -> None:
        exc = exceptions.AssociationAbortedError(0, 0)
        self.assertIsInstance(exc, exceptions.AssociationError)


if __name__ == '__main__':
    unittest.main()
