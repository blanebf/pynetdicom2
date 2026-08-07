# Copyright (c) 2014 Pavel 'Blane' Tuchin
# This file is part of pynetdicom2, released under a modified MIT license.
#    See the file license.txt included with this distribution.

__author__ = 'Blane'
from io import BytesIO
import struct
from typing import Union

import unittest
from pydicom import uid
from pynetdicom2 import exceptions, fsm, pdu, userdataitems


class TestPDUEncoding(unittest.TestCase):
    def compare_pdu(self, pdu1: fsm.PDUType, pdu2: fsm.PDUType) -> None:
        self.assertIsInstance(pdu1, pdu2.__class__)
        self.assertEqual(pdu1.__dict__, pdu2.__dict__)

    def decode_and_compare(self, pdu: fsm.PDUType) -> None:
        self.compare_pdu(pdu, type(pdu).decode(pdu.encode()))

    def test_a_associate_rq_pdu(self) -> None:
        _pdu = pdu.AAssociateRqPDU(
            called_ae_title='aet1',
            calling_ae_title='aet2',
            variable_items=[]
        )
        self.decode_and_compare(_pdu)

    def test_a_associate_ac_pdu(self) -> None:
        _pdu = pdu.AAssociateAcPDU(
            called_ae_title='aet1',
            calling_ae_title='aet2',
            variable_items=[]
        )
        self.decode_and_compare(_pdu)


class TestSubItemEncoding(unittest.TestCase):
    def decode_and_compare_sub_item(
            self,
            item: Union[
                pdu.UserItem,
                pdu.UserInformationItem,
                pdu.PresentationDataValueItem
            ]
    ) -> None:
        encoded = item.encode()
        stream = BytesIO(encoded)
        item2 = type(item).decode(stream)
        self.assertIsInstance(item, item2.__class__)
        self.assertEqual(item.__dict__, item2.__dict__)

    def test_user_information_item(self) -> None:
        item = pdu.UserInformationItem(user_data=[])
        self.decode_and_compare_sub_item(item)

    def test_data_value_item(self) -> None:
        test_string = b'test data'
        item = pdu.PresentationDataValueItem(
            context_id=3,
            data_value=test_string
        )
        self.decode_and_compare_sub_item(item)

    def test_generic_user_data_sub_item(self) -> None:
        test_string = b'test data'
        item = userdataitems.GenericUserDataSubItem(
            item_type=0x5, user_data=test_string
        )
        self.decode_and_compare_sub_item(item)

    def test_maximum_length_sub_item(self) -> None:
        item = userdataitems.MaximumLengthSubItem(
            maximum_length_received=5
        )
        self.decode_and_compare_sub_item(item)

    def test_scp_scu_role_selection_sub_item(self) -> None:
        item = userdataitems.ScpScuRoleSelectionSubItem(
            sop_class_uid=uid.UID('1.2.3.4.5'), scp_role=1, scu_role=1
        )
        self.decode_and_compare_sub_item(item)

    def test_implementation_version_name_sub_item(self) -> None:
        item = userdataitems.ImplementationClassUIDSubItem(
            implementation_class_uid='1.2.3.4.5'
        )
        self.decode_and_compare_sub_item(item)

    def test_asynchronous_operations_window_sub_item(self) -> None:
        item = userdataitems.AsynchronousOperationsWindowSubItem(
            max_num_ops_invoked=5, max_num_ops_performed=7
        )
        self.decode_and_compare_sub_item(item)

    def test_sop_class_extended_negotiation_sub_item(self) -> None:
        item = userdataitems.SOPClassExtendedNegotiationSubItem(
            sop_class_uid=uid.UID('1.2.3.4.5'), app_info=b'test information'
        )
        self.decode_and_compare_sub_item(item)

    def test_user_identity_negotiation(self) -> None:
        item = userdataitems.UserIdentityNegotiationSubItem(
            u'user', u'password'
        )
        self.decode_and_compare_sub_item(item)

    def test_user_identity_negotiation_name_only(self) -> None:
        item = userdataitems.UserIdentityNegotiationSubItem(
            u'user', user_identity_type=1
        )
        self.decode_and_compare_sub_item(item)

    def test_user_identity_negotiation_ac(self) -> None:
        item = userdataitems.UserIdentityNegotiationSubItemAc(
            u'test_key'
        )
        self.decode_and_compare_sub_item(item)


class MalformedPduDecodingTestCase(unittest.TestCase):
    """Decoding untrusted data must raise ``PDUProcessingError`` instead of
    mis-parsing, reading past the declared item bounds, or leaking raw
    parsing exceptions."""

    def test_truncated_application_context_item(self) -> None:
        # Declares 10 bytes of context name but provides only 3.
        stream = BytesIO(b'\x10\x00\x00\x0a' + b'abc')
        with self.assertRaises(exceptions.PDUProcessingError):
            pdu.ApplicationContextItem.decode(stream)

    def test_data_value_item_zero_length_rejected(self) -> None:
        # An item length of 0 is invalid (it must cover at least the context
        # ID byte) and historically made the decoder read the whole stream.
        stream = BytesIO(struct.pack('>I B', 0, 1))
        with self.assertRaises(exceptions.PDUProcessingError):
            pdu.PresentationDataValueItem.decode(stream)

    def test_sop_class_extended_uid_length_out_of_bounds(self) -> None:
        # Item length 5 cannot fit a UID of length 10 plus its 2-byte length
        # field; without validation this read the whole remaining stream.
        stream = BytesIO(struct.pack('>B B H H', 0x56, 0x00, 5, 10))
        with self.assertRaises(exceptions.PDUProcessingError):
            userdataitems.SOPClassExtendedNegotiationSubItem.decode(stream)

    def test_role_selection_inconsistent_lengths_rejected(self) -> None:
        # Item length must equal UID length + 4 (UID length field + roles).
        stream = BytesIO(struct.pack('>B B H H', 0x54, 0x00, 5, 10))
        with self.assertRaises(exceptions.PDUProcessingError):
            userdataitems.ScpScuRoleSelectionSubItem.decode(stream)

    def test_truncated_user_identity_item(self) -> None:
        # Primary field declares 10 bytes but only 3 are present.
        stream = BytesIO(
            struct.pack('>B B H B B H', 0x58, 0x00, 12, 2, 0, 10) + b'abc'
        )
        with self.assertRaises(exceptions.PDUProcessingError):
            userdataitems.UserIdentityNegotiationSubItem.decode(stream)

    def test_sop_class_extended_keeps_stream_alignment(self) -> None:
        # Regression: decoding a SOP Class Extended item followed by another
        # sub-item must leave the stream positioned exactly at the next
        # sub-item (a previous off-by-two made the decoder eat into it).
        extended = userdataitems.SOPClassExtendedNegotiationSubItem(
            sop_class_uid=uid.UID('1.2.3.4.5'), app_info=b'info'
        )
        version = userdataitems.ImplementationVersionNameSubItem(
            implementation_version_name='TESTNAME'
        )
        item = pdu.UserInformationItem(user_data=[extended, version])
        decoded = pdu.UserInformationItem.decode(BytesIO(item.encode()))
        self.assertEqual(len(decoded.user_data), 2)
        self.assertEqual(decoded.user_data[0].__dict__, extended.__dict__)
        self.assertEqual(decoded.user_data[1].__dict__, version.__dict__)


class AeTitleDecodingTestCase(unittest.TestCase):
    """AE title fields are fixed 16-byte fields (called title at offset 10,
    calling title at offset 26 of the A-ASSOCIATE header)."""

    def _encoded(self) -> bytearray:
        return bytearray(pdu.AAssociateRqPDU('aet1', 'aet2', []).encode())

    def test_space_and_null_padding_is_stripped(self) -> None:
        raw = self._encoded()
        raw[10:26] = b'SCPAET          '
        raw[26:42] = b'SCUAET\0\0\0\0\0\0\0\0\0\0'
        decoded = pdu.AAssociateRqPDU.decode(bytes(raw))
        self.assertEqual(decoded.called_ae_title, 'SCPAET')
        self.assertEqual(decoded.calling_ae_title, 'SCUAET')

    def test_title_with_internal_space_kept(self) -> None:
        raw = self._encoded()
        raw[10:26] = b'MY AET          '
        decoded = pdu.AAssociateRqPDU.decode(bytes(raw))
        self.assertEqual(decoded.called_ae_title, 'MY AET')

    def test_invalid_characters_rejected(self) -> None:
        raw = self._encoded()
        raw[26:42] = b'CTRL\x01TITLE      '
        with self.assertRaises(exceptions.PDUProcessingError):
            pdu.AAssociateRqPDU.decode(bytes(raw))


if __name__ == '__main__':
    unittest.main()
