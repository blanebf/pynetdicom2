"""Unit tests for :mod:`pynetdicom2.statuses`."""
import unittest

from pynetdicom2 import dimsemessages as dimse
from pynetdicom2 import statuses


class StatusPredicateTestCase(unittest.TestCase):
    def test_success(self) -> None:
        status = statuses.Status(0x0000)
        self.assertTrue(status.is_success)
        self.assertFalse(status.is_failure)
        self.assertFalse(status.is_warning)
        self.assertFalse(status.is_pending)
        self.assertFalse(status.is_cancel)

    def test_processing_failure(self) -> None:
        status = statuses.PROCESSING_FAILURE
        self.assertTrue(status.is_failure)
        self.assertFalse(status.is_success)

    def test_c_find_pending(self) -> None:
        status = statuses.Status(0xFF00, dimse.CFindRSPMessage)
        self.assertTrue(status.is_pending)
        self.assertFalse(status.is_success)

    def test_c_store_warning_elements_discarded(self) -> None:
        status = statuses.C_STORE_ELEMENTS_DISCARDED
        self.assertTrue(status.is_warning)

    def test_command_specific_range_code(self) -> None:
        # 0xC000-0xCFFF is 'Cannot understand' for C-STORE.
        status = statuses.Status(0xC123, dimse.CStoreRSPMessage)
        self.assertTrue(status.is_failure)

    def test_unknown_code(self) -> None:
        # Unrecognised codes fall back to the UNKNOWN sentinel, which is
        # classified as a Failure.
        status = statuses.Status(0x9999)
        self.assertFalse(status.is_success)
        self.assertTrue(status.is_failure)

    def test_int_roundtrip(self) -> None:
        self.assertEqual(int(statuses.Status(0x0110)), 0x0110)

    def test_repr_and_str(self) -> None:
        status = statuses.Status(0x0000)
        self.assertIn('Status', repr(status))
        self.assertIn('Success', str(status))


class TypoAliasTestCase(unittest.TestCase):
    def test_cannot_understand_alias(self) -> None:
        # The corrected spelling must exist and the old misspelled alias must
        # remain for backwards compatibility, pointing at the same value.
        self.assertIs(
            statuses.C_STORE_CANNON_UNDERSTAND,
            statuses.C_STORE_CANNOT_UNDERSTAND
        )
        self.assertEqual(int(statuses.C_STORE_CANNOT_UNDERSTAND), 0xC000)
        self.assertTrue(statuses.C_STORE_CANNOT_UNDERSTAND.is_failure)


if __name__ == '__main__':
    unittest.main()
