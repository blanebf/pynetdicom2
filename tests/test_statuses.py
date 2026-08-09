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


class CancelStatusTestCase(unittest.TestCase):
    """0xFE00 must be registered as a Cancel status for the query/retrieve
    services so ``Status.is_cancel`` can be True."""

    def test_c_find_cancel(self) -> None:
        status = statuses.Status(0xFE00, dimse.CFindRSPMessage)
        self.assertTrue(status.is_cancel)
        self.assertFalse(status.is_success)
        self.assertFalse(status.is_failure)
        self.assertIs(statuses.C_FIND_CANCEL.is_cancel, True)

    def test_c_get_cancel(self) -> None:
        status = statuses.Status(0xFE00, dimse.CGetRSPMessage)
        self.assertTrue(status.is_cancel)
        self.assertIs(statuses.C_GET_CANCEL.is_cancel, True)

    def test_c_move_cancel(self) -> None:
        status = statuses.Status(0xFE00, dimse.CMoveRSPMessage)
        self.assertTrue(status.is_cancel)
        self.assertIs(statuses.C_MOVE_CANCEL.is_cancel, True)


class StatusEqualityTestCase(unittest.TestCase):
    def test_statuses_with_same_code_are_equal(self) -> None:
        self.assertEqual(statuses.Status(0x0000), statuses.SUCCESS)
        self.assertEqual(
            statuses.Status(0x0110), statuses.PROCESSING_FAILURE
        )

    def test_statuses_with_different_codes_differ(self) -> None:
        self.assertNotEqual(statuses.SUCCESS, statuses.PROCESSING_FAILURE)

    def test_equality_is_not_identity(self) -> None:
        # Two separately constructed instances with the same code must be
        # equal even though they are distinct objects.
        self.assertEqual(statuses.Status(0x0000), statuses.Status(0x0000))

    def test_status_is_hashable(self) -> None:
        # Statuses can be used in sets and as dict keys.
        collection = {statuses.SUCCESS, statuses.Status(0x0000)}
        self.assertEqual(len(collection), 1)
        mapping = {statuses.PROCESSING_FAILURE: 'failure'}
        self.assertEqual(mapping[statuses.Status(0x0110)], 'failure')


class StatusRangeTestCase(unittest.TestCase):
    """Status code ranges must resolve without materializing one dictionary
    entry per code."""

    def test_range_lookup_resolves(self) -> None:
        # 0xC000-0xCFFF is a registered range for several commands.
        for value in (0xC000, 0xC123, 0xCFFF):
            status = statuses.Status(value, dimse.CStoreRSPMessage)
            self.assertTrue(status.is_failure)

    def test_range_codes_not_materialized(self) -> None:
        # Individual codes inside a registered range must not appear as
        # separate entries in the command-specific dictionary.
        key = (dimse.CStoreRSPMessage.command_field, 0xC123)
        self.assertNotIn(key, statuses._status_dict)

    def test_add_status_with_range(self) -> None:
        statuses.add_status(
            0xE000, 'Failure', 'Custom range', end=0xE0FF
        )
        try:
            status = statuses.Status(0xE010)
            self.assertTrue(status.is_failure)
            self.assertEqual(status.description, 'Custom range')
        finally:
            statuses._general_status_dict.pop(0xE000, None)
            statuses._general_status_ranges[:] = [
                entry for entry in statuses._general_status_ranges
                if entry[0] != 0xE000
            ]


if __name__ == '__main__':
    unittest.main()
