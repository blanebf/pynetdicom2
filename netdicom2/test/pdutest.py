__author__ = 'Blane'

import unittest
import netdicom2.pdu


class PDUEncodingTestCase(unittest.TestCase):
    def compare_pdu(self, pdu1, pdu2):
        return (isinstance(pdu1, pdu2.__class__)
                and pdu1.__dict__ == pdu2.__dict__)

    def test_a_associate_rq_pdu(self):
        rq1 = netdicom2.pdu.AAssociateRqPDU()
        rq1.pdu_length = 16000
        rq1.called_ae_title = 'aet1'
        rq1.calling_ae_title = 'aet2'
        encoded = rq1.encode()
        rq2 = netdicom2.pdu.AAssociateRqPDU.decode(encoded)
        self.assertTrue(self.compare_pdu(rq1, rq2))

    def test_a_associate_ac_pdu(self):
        rq1 = netdicom2.pdu.AAssociateAcPDU()
        encoded = rq1.encode()
        rq2 = netdicom2.pdu.AAssociateAcPDU.decode(encoded)
        self.assertTrue(self.compare_pdu(rq1, rq2))

if __name__ == '__main__':
    unittest.main()