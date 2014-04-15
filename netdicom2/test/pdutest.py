__author__ = 'Blane'

import unittest
import cStringIO
import netdicom2.pdu


class PDUEncodingTestCase(unittest.TestCase):
    def compare_pdu(self, pdu1, pdu2):
        self.assertIsInstance(pdu1, pdu2.__class__)
        self.assertEqual(pdu1.__dict__, pdu2.__dict__)

    def decode_and_compare(self, pdu):
        self.compare_pdu(pdu, type(pdu).decode(pdu.encode()))

    def decode_and_compare_sub_item(self, item):
        encoded = item.encode()
        stream = cStringIO.StringIO(encoded)
        self.compare_pdu(item, type(item).decode(stream))

    def test_a_associate_rq_pdu(self):
        pdu = netdicom2.pdu.AAssociateRqPDU(called_ae_title='aet1',
                                            calling_ae_title='aet2',
                                            pdu_length=16000)
        self.decode_and_compare(pdu)

    def test_a_associate_ac_pdu(self):
        pdu = netdicom2.pdu.AAssociateAcPDU(pdu_length=16000, reserved3='aet1',
                                            reserved4='aet2')
        self.decode_and_compare(pdu)

    def test_user_information_item(self):
        item = netdicom2.pdu.UserInformationItem(item_length=0,
                                                 user_data=[])
        self.decode_and_compare_sub_item(item)

    def test_maximum_length_sub_item(self):
        item = netdicom2.pdu.MaximumLengthSubItem(maximum_length_received=5)
        self.decode_and_compare_sub_item(item)

    def test_presentation_data_value_item(self):
        test_string = 'test data'
        item = netdicom2.pdu.PresentationDataValueItem(
            presentation_context_id=3,
            presentation_data_value=test_string)
        self.decode_and_compare_sub_item(item)

    def test_generic_user_data_sub_item(self):
        test_string = 'test data'
        item = netdicom2.pdu.GenericUserDataSubItem(item_type=0x5,
                                                    user_data=test_string)
        self.decode_and_compare_sub_item(item)

if __name__ == '__main__':
    unittest.main()
