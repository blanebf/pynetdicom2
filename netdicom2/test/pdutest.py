__author__ = 'Blane'

import unittest
import netdicom2.pdu


class PDUEncodingTestCase(unittest.TestCase):
    def test_aa_associate_rq_pdu(self):
        rq1 = netdicom2.pdu.AAssociateRqPDU()
        rq1.pdu_length = 16000
        rq1.called_ae_title = 'aet1'
        rq1.calling_ae_title = 'aet2'
        encoded = rq1.encode()
        rq2 = netdicom2.pdu.AAssociateRqPDU()
        rq2.decode(encoded)
        self.assertEqual(rq1, rq2)
