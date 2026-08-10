"""Unit tests for :mod:`pynetdicom2.uids`."""
import re
import unittest

from pydicom import uid

from pynetdicom2 import uids


UID_PATTERN = re.compile(r'^[0-9]+(\.[0-9]+)*$')


def _all_uid_constants() -> list:
    return [
        value for value in vars(uids).values()
        if isinstance(value, uid.UID)
    ]


class UidFormatTestCase(unittest.TestCase):
    def test_all_uids_are_well_formed(self) -> None:
        # DICOM UIDs must consist of dot-separated numeric components and
        # must not exceed 64 characters.
        for value in _all_uid_constants():
            with self.subTest(uid=value):
                self.assertLessEqual(len(value), 64)
                self.assertRegex(str(value), UID_PATTERN)


class TransferSyntaxCollectionTestCase(unittest.TestCase):
    def test_all_ts_not_empty_and_unique(self) -> None:
        self.assertTrue(uids.ALL_TS)
        self.assertEqual(len(uids.ALL_TS), len(set(uids.ALL_TS)))

    def test_all_ts_contains_default_syntaxes(self) -> None:
        self.assertIn(uid.ImplicitVRLittleEndian, uids.ALL_TS)
        self.assertIn(uid.ExplicitVRLittleEndian, uids.ALL_TS)

    def test_all_ts_excludes_pseudo_transfer_syntaxes(self) -> None:
        # Pseudo transfer syntaxes cannot encode Data Sets and must not be
        # negotiated on storage presentation contexts.
        self.assertNotIn(uids.RFC_2557_MIME_ENCAPSULATION, uids.ALL_TS)
        self.assertNotIn(uids.XML_ENCODING, uids.ALL_TS)

    def test_collections_are_immutable(self) -> None:
        self.assertIsInstance(uids.ALL_TS, tuple)
        self.assertIsInstance(uids.STORAGE_SOP_CLASSES, tuple)

    def test_all_ts_are_uids(self) -> None:
        for ts in uids.ALL_TS:
            with self.subTest(ts=ts):
                self.assertIsInstance(ts, uid.UID)


class SopClassCollectionTestCase(unittest.TestCase):
    def test_storage_sop_classes_not_empty_and_unique(self) -> None:
        self.assertTrue(uids.STORAGE_SOP_CLASSES)
        self.assertEqual(
            len(uids.STORAGE_SOP_CLASSES),
            len(set(uids.STORAGE_SOP_CLASSES))
        )

    def test_query_retrieve_classes_exist(self) -> None:
        # Patient root, study root and patient-study-only Q/R model classes
        # must exist for each of the FIND/MOVE/GET operations.
        for sop_class in (
            uids.PATIENT_ROOT_FIND_SOP_CLASS,
            uids.PATIENT_ROOT_MOVE_SOP_CLASS,
            uids.PATIENT_ROOT_GET_SOP_CLASS,
            uids.STUDY_ROOT_FIND_SOP_CLASS,
            uids.STUDY_ROOT_MOVE_SOP_CLASS,
            uids.STUDY_ROOT_GET_SOP_CLASS,
            uids.PATIENT_STUDY_ONLY_FIND_SOP_CLASS,
            uids.PATIENT_STUDY_ONLY_MOVE_SOP_CLASS,
            uids.PATIENT_STUDY_ONLY_GET_SOP_CLASS
        ):
            with self.subTest(sop_class=sop_class):
                self.assertIsInstance(sop_class, uid.UID)

    def test_well_known_uid_values(self) -> None:
        self.assertEqual(
            str(uids.VERIFICATION_SOP_CLASS), '1.2.840.10008.1.1'
        )
        self.assertEqual(
            str(uids.STORAGE_COMMITMENT_SOP_CLASS), '1.2.840.10008.1.20.1'
        )


if __name__ == '__main__':
    unittest.main()
