# Copyright (c) 2014 Pavel 'Blane' Tuchin
# This file is part of pynetdicom2, released under a modified MIT license.
#    See the file license.txt included with this distribution.

__author__ = 'Blane'

import unittest
import six
import pynetdicom2.pdu
import pynetdicom2.userdataitems

if six.PY3:
    from six import BytesIO as cStringIO
else:
    from six.moves import cStringIO


class TestPDUEncoding(unittest.TestCase):
    def compare_pdu(self, pdu1, pdu2):
        self.assertIsInstance(pdu1, pdu2.__class__)
        self.assertEqual(pdu1.__dict__, pdu2.__dict__)

    def decode_and_compare(self, pdu):
        self.compare_pdu(pdu, type(pdu).decode(pdu.encode()))

    def test_a_associate_rq_pdu(self):
        pdu = pynetdicom2.pdu.AAssociateRqPDU(
            called_ae_title='aet1',
            calling_ae_title='aet2',
            variable_items=[])
        self.decode_and_compare(pdu)

    def test_a_associate_ac_pdu(self):
        pdu = pynetdicom2.pdu.AAssociateAcPDU(
            called_ae_title='aet1',
            calling_ae_title='aet2',
            variable_items=[])
        self.decode_and_compare(pdu)


class TestSubItemEncoding(unittest.TestCase):
    def decode_and_compare_sub_item(self, item):
        encoded = item.encode()
        stream = cStringIO(encoded)
        item2 = type(item).decode(stream)
        self.assertIsInstance(item, item2.__class__)
        self.assertEqual(item.__dict__, item2.__dict__)

    def test_user_information_item(self):
        item = pynetdicom2.pdu.UserInformationItem(user_data=[])
        self.decode_and_compare_sub_item(item)

    def test_data_value_item(self):
        test_string = b'test data'
        item = pynetdicom2.pdu.PresentationDataValueItem(
            context_id=3,
            data_value=test_string)
        self.decode_and_compare_sub_item(item)

    def test_generic_user_data_sub_item(self):
        test_string = b'test data'
        item = pynetdicom2.userdataitems.GenericUserDataSubItem(
            item_type=0x5, user_data=test_string)
        self.decode_and_compare_sub_item(item)

    def test_maximum_length_sub_item(self):
        item = pynetdicom2.userdataitems.MaximumLengthSubItem(
            maximum_length_received=5)
        self.decode_and_compare_sub_item(item)

    def test_scp_scu_role_selection_sub_item(self):
        item = pynetdicom2.userdataitems.ScpScuRoleSelectionSubItem(
            sop_class_uid='1.2.3.4.5', scp_role=1, scu_role=1)
        self.decode_and_compare_sub_item(item)

    def test_implementation_version_name_sub_item(self):
        item = pynetdicom2.userdataitems.ImplementationClassUIDSubItem(
            implementation_class_uid='1.2.3.4.5')
        self.decode_and_compare_sub_item(item)

    def test_asynchronous_operations_window_sub_item(self):
        item = pynetdicom2.userdataitems.AsynchronousOperationsWindowSubItem(
            max_num_ops_invoked=5, max_num_ops_performed=7)
        self.decode_and_compare_sub_item(item)

    def test_sop_class_extended_negotiation_sub_item(self):
        item = pynetdicom2.userdataitems.SOPClassExtendedNegotiationSubItem(
            sop_class_uid='1.2.3.4.5', app_info=b'test information'
        )
        self.decode_and_compare_sub_item(item)

    def test_user_identity_negotiation(self):
        item = pynetdicom2.userdataitems.UserIdentityNegotiationSubItem(
            u'user', u'password')
        self.decode_and_compare_sub_item(item)

    def test_user_identity_negotiation_name_only(self):
        item = pynetdicom2.userdataitems.UserIdentityNegotiationSubItem(
            u'user', user_identity_type=1)
        self.decode_and_compare_sub_item(item)

    def test_user_identity_negotiation_ac(self):
        item = pynetdicom2.userdataitems.UserIdentityNegotiationSubItemAc(
            u'test_key')
        self.decode_and_compare_sub_item(item)


if __name__ == '__main__':
    unittest.main()
