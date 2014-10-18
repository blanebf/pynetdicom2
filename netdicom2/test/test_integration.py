__author__ = 'Blane'

import unittest

import dicom.UID
import dicom.dataset
import dicom.datadict

import netdicom2.applicationentity as ae
import netdicom2.sopclass as sc


class CEchoTestCase(unittest.TestCase):
    def test_c_echo_positive(self):
        ae1 = ae.ClientAE('AET1').add_scu(sc.verification_scu)
        ae2 = ae.AE('AET2', 11112).add_scp(sc.verification_scp)
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
        ae1 = ae.ClientAE('AET1').add_scu(sc.qr_find_scu)
        ae2 = CFindServerAE('AET2', 11112).add_scp(sc.qr_find_scp)
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


class CStoreTestCase(unittest.TestCase):
    def test_c_store_positive(self):
        class CStoreAE(ae.AE):
            def on_receive_store(self, context, ds):
                test.assertEquals(context.sop_class, sc.BASIC_TEXT_SR_STORAGE)
                test.assertEquals(ds.PatientName, rq.PatientName)
                test.assertEquals(ds.StudyInstanceUID, rq.StudyInstanceUID)
                test.assertEquals(ds.SeriesInstanceUID, rq.SeriesInstanceUID)
                test.assertEquals(ds.SOPInstanceUID, rq.SOPInstanceUID)
                test.assertEquals(ds.SOPClassUID, rq.SOPClassUID)
                return sc.SUCCESS

        test = self
        ae1 = ae.ClientAE('AET1').add_scu(sc.storage_scu)
        ae2 = CStoreAE('AET2', 11112).add_scp(sc.storage_scp)
        with ae2:
            remote_ae = dict(address='127.0.0.1', port=11112, aet='AET2')
            with ae1.request_association(remote_ae) as assoc:
                service = assoc.get_scu(sc.BASIC_TEXT_SR_STORAGE)
                rq = dicom.dataset.Dataset()
                rq.PatientName = 'Patient^Name^Test'
                rq.PatientID = 'TestID'
                rq.StudyInstanceUID = '1.2.3.4.5'
                rq.SeriesInstanceUID = '1.2.3.4.5.1'
                rq.SOPInstanceUID = '1.2.3.4.5.1.1'
                rq.SOPClassUID = sc.BASIC_TEXT_SR_STORAGE
                status = service(rq, 1)
                self.assertEquals(status, sc.SUCCESS)