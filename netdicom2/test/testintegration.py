__author__ = 'Blane'

import unittest

import dicom.UID
import dicom.dataset
import dicom.datadict

import netdicom2.applicationentity as ae
import netdicom2.sopclass as sc


class CEchoTestCase(unittest.TestCase):
    def test_c_echo_positive(self):
        ae1 = ae.AE('AET1', 11112, [sc.VERIFICATION_SOP_CLASS], [])
        ae2 = ae.AE('AET2', 11113, [], [sc.VERIFICATION_SOP_CLASS])
        with ae1:
            with ae2:
                remote_ae = dict(address='127.0.0.1', port=11113, aet='AET2')
                with ae1.request_association(remote_ae) as assoc:
                    self.assertIsNotNone(assoc)
                    service = assoc.get_scu(sc.VERIFICATION_SOP_CLASS)
                    self.assertIsNotNone(service)
                    result = service.scu(1)
                    self.assertEqual(result.type_, 'Success')



