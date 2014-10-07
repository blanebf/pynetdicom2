__author__ = 'Blane'

import unittest

import dicom.UID
import dicom.dataset
import dicom.datadict

import netdicom2.applicationentity as ae
import netdicom2.sopclass as sc


class CEchoTestCase(unittest.TestCase):
    def test_c_echo_positive(self):
        ae1 = ae.ClientAE('AET1').add_scu(sc.VerificationService)
        ae2 = ae.AE('AET2', 11112).add_scp(sc.VerificationService)
        with ae2:
            remote_ae = dict(address='127.0.0.1', port=11112, aet='AET2',
                             username='admin', password='123')
            with ae1.request_association(remote_ae) as assoc:
                self.assertIsNotNone(assoc)
                service = assoc.get_scu(sc.VERIFICATION_SOP_CLASS)
                self.assertIsNotNone(service)
                result = service(1)
                self.assertEqual(result.status_type, 'Success')


class CFindTestCase(unittest.TestCase):
    def test_c_find_positive(self):
        class CFindServerAE(ae.AE):
            def on_receive_find(self, context, ds):
                test.assertEquals(ds.PatientName, test_name)
                rsp = dicom.dataset.Dataset()
                rsp.PatientName = test_name
                return iter([(rsp, sc.SUCCESS)])

        test = self
        test_name = 'Patient^Name^Test'
        ae1 = ae.ClientAE('AET1').add_scu(sc.QRFindService)
        ae2 = CFindServerAE('AET2', 11112).add_scp(sc.QRFindService)
        with ae2:
            remote_ae = dict(address='127.0.0.1', port=11112, aet='AET2',
                             username='admin', password='123')
            with ae1.request_association(remote_ae) as assoc:
                service = assoc.get_scu(sc.PATIENT_ROOT_FIND_SOP_CLASS)
                req = dicom.dataset.Dataset()
                req.PatientName = test_name
                for result, status in service(req, 1):
                    self.assertEquals(result.PatientName, test_name)
                    self.assertEquals(status, sc.SUCCESS)