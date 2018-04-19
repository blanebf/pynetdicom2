__author__ = 'Blane'

import unittest

try:
    import pydicom as dicom
    from pydicom import uid
    from pydicom import dataset
    from pydicom import datadict
except ImportError:
    # pre 1.0 pydicom
    import dicom
    from dicom import UID as uid
    from dicom import dataset
    from dicom import datadict

import netdicom2.applicationentity as ae
import netdicom2.sopclass as sc

from netdicom2 import c_find


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


class CFindServerAE(ae.AE):
    def __init__(self, test_name, test, *args, **kwargs):
        super(CFindServerAE, self).__init__(*args, **kwargs)
        self.test_name = test_name
        self.test = test

    def on_receive_find(self, context, ds):
        self.test.assertEquals(ds.PatientName, self.test_name)
        rsp = dataset.Dataset()
        rsp.PatientName = self.test_name
        return iter([(rsp, sc.SUCCESS)])


class CFindTestCase(unittest.TestCase):
    def test_c_find_positive(self):
        test_name = 'Patient^Name^Test'
        ae1 = ae.ClientAE('AET1').add_scu(sc.qr_find_scu)
        ae2 = CFindServerAE(test_name, self, 'AET2', 11112)\
            .add_scp(sc.qr_find_scp)
        with ae2:
            remote_ae = dict(address='127.0.0.1', port=11112, aet='AET2',
                             username='admin', password='123')
            with ae1.request_association(remote_ae) as assoc:
                service = assoc.get_scu(sc.PATIENT_ROOT_FIND_SOP_CLASS)
                req = dataset.Dataset()
                req.PatientName = test_name
                for result, status in service(req, 1):
                    self.assertEquals(result.PatientName, test_name)
                    self.assertEquals(status, sc.SUCCESS)


class CFindWrapperTestCase(unittest.TestCase):
    def test_c_find_positive(self):
        test_name = 'Patient^Name^Test'
        remote_ae = dict(address='127.0.0.1', port=11112, aet='AET2',
                         username='admin', password='123')

        ds = dataset.Dataset()
        ds.PatientName = test_name

        ae2 = CFindServerAE(test_name, self, 'AET2', 11112)\
            .add_scp(sc.qr_find_scp)
        with ae2:
            for result, status in c_find(remote_ae, 'AET1', ds):
                self.assertEquals(result.PatientName, test_name)
                self.assertEquals(status, sc.SUCCESS)


class CStoreAE(ae.AE):
    def __init__(self, test, rq, *args, **kwargs):
        ae.AE.__init__(self, *args, **kwargs)
        self.test = test
        self.rq = rq

    def on_receive_store(self, context, ds):
        d = dicom.read_file(ds)
        self.test.assertEquals(context.sop_class, self.rq.SOPClassUID)
        self.test.assertEquals(d.PatientName, self.rq.PatientName)
        self.test.assertEquals(d.StudyInstanceUID, self.rq.StudyInstanceUID)
        self.test.assertEquals(d.SeriesInstanceUID, self.rq.SeriesInstanceUID)
        self.test.assertEquals(d.SOPInstanceUID, self.rq.SOPInstanceUID)
        self.test.assertEquals(d.SOPClassUID, self.rq.SOPClassUID)
        return sc.SUCCESS


class CStoreTestCase(unittest.TestCase):
    def test_c_store_positive(self):
        rq = dataset.Dataset()
        rq.PatientName = 'Patient^Name^Test'
        rq.PatientID = 'TestID'
        rq.StudyInstanceUID = '1.2.3.4.5'
        rq.SeriesInstanceUID = '1.2.3.4.5.1'
        rq.SOPInstanceUID = '1.2.3.4.5.1.1'
        rq.SOPClassUID = sc.BASIC_TEXT_SR_STORAGE

        ae1 = ae.ClientAE('AET1').add_scu(sc.storage_scu)
        ae2 = CStoreAE(self, rq, 'AET2', 11112).add_scp(sc.storage_scp)
        with ae2:
            remote_ae = dict(address='127.0.0.1', port=11112, aet='AET2')
            with ae1.request_association(remote_ae) as assoc:
                service = assoc.get_scu(sc.BASIC_TEXT_SR_STORAGE)

                status = service(rq, 1)
                self.assertEquals(status, sc.SUCCESS)

    def test_c_store_from_file(self):
        file_name = 'test_sr.dcm'
        rq = dicom.read_file(file_name)

        ae1 = ae.ClientAE('AET1', [uid.ExplicitVRLittleEndian])\
            .add_scu(sc.storage_scu)
        ae2 = CStoreAE(self, rq, 'AET2', 11112).add_scp(sc.storage_scp)
        with ae2:
            remote_ae = dict(address='127.0.0.1', port=11112, aet='AET2')
            with ae1.request_association(remote_ae) as assoc:
                service = assoc.get_scu(sc.COMPREHENSIVE_SR_STORAGE)

                status = service(file_name, 1)
                self.assertEquals(status, sc.SUCCESS)


import threading


class CommitmentAE(ae.AE):
    def __init__(self, test, transaction, success, failure, event, remote_ae,
                 *args, **kwargs):
        ae.AE.__init__(self, *args, **kwargs)

        self.test = test
        self.transaction = transaction
        self.success = success
        self.failure = failure
        self.event = event
        self.remote_ae = remote_ae

    def on_commitment_request(self, remote_ae, uids):
        success = []
        failures = []
        for uid in uids:
            if uid in self.success:
                success.append(uid)
            else:
                cls, inst = uid
                failures.append((cls, inst,
                                 sc.StorageCommitment.NO_SUCH_OBJECT_INSTANCE))
        return self.remote_ae, success, failures

    def on_commitment_response(self, transaction_uid, success, failure):
        self.test.assertEquals(self.transaction, transaction_uid)
        self.test.assertEquals(self.success, list(success))
        for i, failed in enumerate(failure):
            cls, inst, reason = failed
            self.test.assertEquals(reason,
                                   sc.StorageCommitment.NO_SUCH_OBJECT_INSTANCE)
            self.test.assertEquals(self.failure[i], (cls, inst))
        self.event.set()


class StorageCommitmentTestCase(unittest.TestCase):
    def setUp(self):
        self.event = threading.Event()
        self.remote_ae1 = dict(address='127.0.0.1', port=11113, aet='AET1')
        self.remote_ae2 = dict(address='127.0.0.1', port=11112, aet='AET2')
        self.transaction = uid.generate_uid()

    def test_commitment_positive(self):
        uids = [(sc.COMPREHENSIVE_SR_STORAGE, uid.generate_uid())
                for _ in xrange(5)]

        ae1 = CommitmentAE(self, self.transaction, uids, [], self.event,
                           self.remote_ae1,
                           'AET2', 11113)\
            .add_scp(sc.StorageCommitment())\
            .add_scu(sc.storage_commitment_scu)

        ae2 = CommitmentAE(self, self.transaction, uids, [], self.event,
                           self.remote_ae2,
                           'AET2', 11112)\
            .add_scp(sc.StorageCommitment())

        with ae2:
            with ae1:
                with ae1.request_association(self.remote_ae2) as assoc:
                    service = assoc.get_scu(sc.STORAGE_COMMITMENT_SOP_CLASS)

                    status = service(self.transaction, uids, 1)
                    self.assertEquals(status, sc.SUCCESS)
                    self.event.wait(20)

    def test_commitment_failure(self):
        uids = [(sc.COMPREHENSIVE_SR_STORAGE, uid.generate_uid()+str(i))
                for i in xrange(10)]

        ae1 = CommitmentAE(self, self.transaction, uids[:5], uids[5:],
                           self.event, self.remote_ae1,
                           'AET2', 11113)\
            .add_scp(sc.StorageCommitment())\
            .add_scu(sc.storage_commitment_scu)

        ae2 = CommitmentAE(self, self.transaction, uids[:5], uids[5:],
                           self.event, self.remote_ae2,
                           'AET2', 11112)\
            .add_scp(sc.StorageCommitment())

        with ae2:
            with ae1:
                with ae1.request_association(self.remote_ae2) as assoc:
                    service = assoc.get_scu(sc.STORAGE_COMMITMENT_SOP_CLASS)

                    status = service(self.transaction, uids, 1)
                    self.assertEquals(status, sc.SUCCESS)
                    self.event.wait(20)
