__author__ = 'Blane'
import pathlib
import socket
import ssl
import threading
import unittest
from typing import BinaryIO, Iterable, Iterator, Union

import pydicom
from pydicom import uid
from pydicom import dataset

import pynetdicom2.applicationentity as ae
import pynetdicom2.sopclass as sc
from pynetdicom2 import (
    asceprovider, dulprovider, exceptions, fsm, pdu, statuses, ssl_ae,
    commands, uids
)


BASE_PATH = pathlib.Path(__file__).absolute().parent


def _free_port() -> int:
    """Gets an ephemeral free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class CEchoTestCase(unittest.TestCase):
    def test_c_echo_positive(self) -> None:
        port = _free_port()
        ae1 = ae.ClientAE('AET1').add_scu(sc.verification_scu)
        ae2 = ae.AE('AET2', port, bind_and_activate=False)
        ae2.add_scp(sc.verification_scp)
        with ae2:
            remote_ae = asceprovider.RemoteAEConfig(
                address='127.0.0.1',
                port=port,
                aet='AET2',
                username='admin',
                password='123'
            )
            with ae1.request_association(remote_ae) as assoc:
                self.assertIsNotNone(assoc)
                service = assoc.get_scu(uids.VERIFICATION_SOP_CLASS)
                self.assertIsNotNone(service)
                result = service(1)
                self.assertTrue(result.is_success)

    def test_ssl_c_echo_positive(self) -> None:
        port = _free_port()
        client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client_context.load_verify_locations(BASE_PATH / 'cert.pem')
        client_context.check_hostname = False
        client_ae = ssl_ae.SSLClientAE(client_context, 'AET1')
        client_ae.add_scu(sc.verification_scu)

        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(
            BASE_PATH / 'cert.pem', BASE_PATH / 'key.pem', password='12345'
        )
        server_ae = ssl_ae.SSLApplicationEntity(
            server_context,
            'AET2',
            port,
            bind_and_activate=False
        )
        server_ae.add_scp(sc.verification_scp)
        with server_ae:
            remote_ae = asceprovider.RemoteAEConfig(
                address='127.0.0.1',
                port=port,
                aet='AET2',
                username='admin',
                password='123'
            )
            with client_ae.request_association(remote_ae) as assoc:
                service = assoc.get_scu(uids.VERIFICATION_SOP_CLASS)
                result = service(1)
                self.assertIsInstance(result, statuses.Status)
                self.assertTrue(result.is_success)


class CFindServerAE(ae.AE):
    def __init__(
            self,
            test_name: str,
            test: unittest.TestCase,
            ae_title: str,
            port: int
    ) -> None:
        super().__init__(ae_title, port, bind_and_activate=False)
        self.test_name = test_name
        self.test = test

    def on_receive_find(
            self,
            context: fsm.PContextDef,
            ds: dataset.Dataset
    ) -> Iterator[tuple[dataset.Dataset, statuses.Status]]:
        self.test.assertEqual(ds.PatientName, self.test_name)
        rsp = dataset.Dataset()
        rsp.PatientName = self.test_name
        return iter([(rsp, statuses.C_FIND_PENDING)])


class CFindTestCase(unittest.TestCase):
    def test_c_find_positive(self) -> None:
        test_name = 'Patient^Name^Test'
        port = _free_port()
        ae1 = ae.ClientAE('AET1').add_scu(sc.qr_find_scu)
        ae2 = CFindServerAE(test_name, self, 'AET2', port)
        ae2.add_scp(sc.qr_find_scp)
        with ae2:
            remote_ae = asceprovider.RemoteAEConfig(
                address='127.0.0.1',
                port=port,
                aet='AET2',
                username='admin',
                password='123'
            )
            with ae1.request_association(remote_ae) as assoc:
                service = assoc.get_scu(uids.PATIENT_ROOT_FIND_SOP_CLASS)
                req = dataset.Dataset()
                req.PatientName = test_name
                for result, status in service(req, 1):
                    if result:
                        self.assertEqual(result.PatientName, test_name)
                        self.assertTrue(status.is_pending)


class CFindWrapperTestCase(unittest.TestCase):
    def test_c_find_positive(self) -> None:
        test_name = 'Patient^Name^Test'
        port = _free_port()
        remote_ae = asceprovider.RemoteAEConfig(
            address='127.0.0.1',
            port=port,
            aet='AET2',
            username='admin',
            password='123'
        )

        ds = dataset.Dataset()
        ds.PatientName = test_name

        ae2 = CFindServerAE(test_name, self, 'AET2', port)
        ae2.add_scp(sc.qr_find_scp)
        with ae2:
            for result in commands.find('AET1', remote_ae, ds):
                self.assertEqual(result.PatientName, test_name)


class CStoreAE(ae.AE):
    def __init__(
            self,
            test: unittest.TestCase,
            rq: dataset.Dataset,
            ae_title: str,
            port: int
    ) -> None:
        super().__init__(
            ae_title, port, max_pdu_length=1024, bind_and_activate=False
        )
        self.test = test
        self.rq = rq

    def on_receive_store(
            self,
            context: fsm.PContextDef,
            ds: Union[BinaryIO, bytes]
    ) -> statuses.Status:
        d = pydicom.dcmread(ds)
        self.test.assertEqual(context.sop_class, self.rq.SOPClassUID)
        self.test.assertEqual(d.PatientName, self.rq.PatientName)
        self.test.assertEqual(d.StudyInstanceUID, self.rq.StudyInstanceUID)
        self.test.assertEqual(d.SeriesInstanceUID, self.rq.SeriesInstanceUID)
        self.test.assertEqual(d.SOPInstanceUID, self.rq.SOPInstanceUID)
        self.test.assertEqual(d.SOPClassUID, self.rq.SOPClassUID)
        return statuses.SUCCESS


class CStoreTestCase(unittest.TestCase):
    def test_c_store_positive(self) -> None:
        rq = dataset.Dataset()
        rq.PatientName = 'Patient^Name^Test'
        rq.PatientID = 'TestID'
        rq.StudyInstanceUID = '1.2.3.4.5'
        rq.SeriesInstanceUID = '1.2.3.4.5.1'
        rq.SOPInstanceUID = '1.2.3.4.5.1.1'
        rq.SOPClassUID = uids.BASIC_TEXT_SR_STORAGE

        port = _free_port()
        ae1 = ae.ClientAE('AET1')
        ae1.add_scu(sc.storage_scu, [uids.BASIC_TEXT_SR_STORAGE])
        ae2 = CStoreAE(self, rq, 'AET2', port)
        ae2.add_scp(sc.storage_scp)
        with ae2:
            remote_ae = asceprovider.RemoteAEConfig(
                address='127.0.0.1', port=port, aet='AET2'
            )
            with ae1.request_association(remote_ae) as assoc:
                service = assoc.get_scu(uids.BASIC_TEXT_SR_STORAGE)
                status = service(rq, 1)
                self.assertTrue(status.is_success)

    def test_c_store_from_file(self) -> None:
        file_name = BASE_PATH / 'test_sr.dcm'
        rq = pydicom.dcmread(file_name)

        port = _free_port()
        ae1 = ae.ClientAE(
            'AET1', [uid.ExplicitVRLittleEndian],  max_pdu_length=1024
        )
        ae1.add_scu(sc.storage_scu, [uids.COMPREHENSIVE_SR_STORAGE])
        ae2 = CStoreAE(self, rq, 'AET2', port).add_scp(sc.storage_scp)
        with ae2:
            remote_ae = asceprovider.RemoteAEConfig(
                address='127.0.0.1', port=port, aet='AET2'
            )
            with ae1.request_association(remote_ae) as assoc:
                service = assoc.get_scu(uids.COMPREHENSIVE_SR_STORAGE)
                status = service(str(file_name), 1)
                self.assertTrue(status.is_success)


class CommitmentAE(ae.AE):
    def __init__(
            self,
            test: unittest.TestCase,
            transaction: uid.UID,
            success: list[tuple[uid.UID, uid.UID]],
            failure: list[tuple[uid.UID, uid.UID]],
            event: threading.Event,
            remote_ae: asceprovider.RemoteAEConfig,
            ae_title: str,
            port: int
    ) -> None:
        super().__init__(ae_title, port, bind_and_activate=False)

        self.test = test
        self.transaction = transaction
        self.success = success
        self.failure = failure
        self.event = event
        self.remote_ae = remote_ae

    def on_commitment_request(
            self,
            remote_ae: str,
            uids: Iterable[tuple[uid.UID, uid.UID]]
    ) -> tuple[
        asceprovider.RemoteAEConfig,
        Iterable[tuple[uid.UID, uid.UID]],
        Iterable[tuple[uid.UID, uid.UID, int]]
    ]:
        success = []
        failures = []
        for _uid in uids:
            if _uid in self.success:
                success.append(_uid)
            else:
                cls, inst = _uid
                failures.append(
                    (cls, inst, sc.StorageCommitment.NO_SUCH_OBJECT_INSTANCE)
                )
        return self.remote_ae, success, failures

    def on_commitment_response(
            self,
            transaction_uid: uid.UID,
            success: Iterable[tuple[uid.UID, uid.UID]],
            failure: Iterable[tuple[uid.UID, uid.UID, int]]
    ) -> None:
        self.test.assertEqual(self.transaction, transaction_uid)
        self.test.assertEqual(self.success, list(success))
        for i, failed in enumerate(failure):
            cls, inst, reason = failed
            self.test.assertEqual(
                reason, sc.StorageCommitment.NO_SUCH_OBJECT_INSTANCE
            )
            self.test.assertEqual(self.failure[i], (cls, inst))
        self.event.set()


class StorageCommitmentTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.event = threading.Event()
        self.port1 = _free_port()
        self.port2 = _free_port()
        self.remote_ae1 = asceprovider.RemoteAEConfig(
            address='127.0.0.1', port=self.port1, aet='AET1'
        )
        self.remote_ae2 = asceprovider.RemoteAEConfig(
            address='127.0.0.1', port=self.port2, aet='AET2'
        )
        self.transaction = uid.generate_uid()

    def test_commitment_positive(self) -> None:
        _uids = [
            (uids.COMPREHENSIVE_SR_STORAGE, uid.generate_uid())
            for _ in range(5)
        ]

        ae1 = CommitmentAE(
            test=self,
            transaction=self.transaction,
            success=_uids,
            failure=[],
            event=self.event,
            remote_ae=self.remote_ae1,
            ae_title='AET2',
            port=self.port1
        )
        ae1.add_scp(sc.StorageCommitment())
        ae1.add_scu(sc.storage_commitment_scu)

        ae2 = CommitmentAE(
            test=self,
            transaction=self.transaction,
            success=_uids,
            failure=[],
            event=self.event,
            remote_ae=self.remote_ae2,
            ae_title='AET2',
            port=self.port2
        )
        ae2.add_scp(sc.StorageCommitment())

        with ae2, ae1:
            with ae1.request_association(self.remote_ae2) as assoc:
                service = assoc.get_scu(uids.STORAGE_COMMITMENT_SOP_CLASS)

                status = service(self.transaction, _uids, 1)
                self.assertTrue(status.is_success)
                self.assertTrue(
                    self.event.wait(20),
                    'commitment response was not received'
                )

    def test_commitment_failure(self) -> None:
        _uids = [
            (uids.COMPREHENSIVE_SR_STORAGE, uid.generate_uid())
            for i in range(10)
        ]

        ae1 = CommitmentAE(
            test=self,
            transaction=self.transaction,
            success=_uids[:5],
            failure=_uids[5:],
            event=self.event,
            remote_ae=self.remote_ae1,
            ae_title='AET2',
            port=self.port1
        )
        ae1.add_scp(sc.StorageCommitment())
        ae1.add_scu(sc.storage_commitment_scu)

        ae2 = CommitmentAE(
            test=self,
            transaction=self.transaction,
            success=_uids[:5],
            failure=_uids[5:],
            event=self.event,
            remote_ae=self.remote_ae2,
            ae_title='AET2',
            port=self.port2
        )
        ae2.add_scp(sc.StorageCommitment())

        with ae2, ae1:
            with ae1.request_association(self.remote_ae2) as assoc:
                service = assoc.get_scu(uids.STORAGE_COMMITMENT_SOP_CLASS)

                status = service(self.transaction, _uids, 1)
                self.assertTrue(status.is_success)
                self.assertTrue(
                    self.event.wait(20),
                    'commitment response was not received'
                )


class RejectingAE(ae.AE):
    """AE that refuses every incoming association request."""

    def on_association_request(
            self,
            asce: asceprovider.AssociationAcceptor,
            assoc: pdu.AAssociateRqPDU
    ) -> None:
        raise exceptions.AssociationRejectedError(1, 1, 7)


class AssociationRejectTestCase(unittest.TestCase):
    def test_reject_propagates_to_requester(self) -> None:
        port = _free_port()
        ae1 = ae.ClientAE('AET1').add_scu(sc.verification_scu)
        ae2 = RejectingAE('AET2', port, bind_and_activate=False)
        with ae2:
            remote_ae = asceprovider.RemoteAEConfig(
                address='127.0.0.1', port=port, aet='AET2'
            )
            with self.assertRaises(
                    exceptions.AssociationRejectedError) as ctx:
                with ae1.request_association(remote_ae):
                    self.fail('association should have been rejected')
            self.assertEqual(ctx.exception.result, 1)
            self.assertEqual(ctx.exception.source, 1)
            self.assertEqual(ctx.exception.diagnostic, 7)


class AbortReceptionTestCase(unittest.TestCase):
    def test_abort_is_delivered_to_service_user(self) -> None:
        # An A-ABORT received while negotiating must surface to the service
        # user as an abort indication with its source/reason intact.
        left, right = socket.socketpair()
        self.addCleanup(right.close)
        provider = dulprovider.DULServiceProvider(
            set(), lambda ctx, ds: (None, 0), dul_socket=left
        )
        try:
            rq = pdu.AAssociateRqPDU('CALLED', 'CALLING', [])
            right.sendall(rq.encode())
            received = provider.receive(5)
            self.assertIsInstance(received, pdu.AAssociateRqPDU)

            right.sendall(pdu.AAbortPDU(source=0, reason_diag=2).encode())
            abort = provider.receive(5)
            self.assertIsInstance(abort, pdu.AAbortPDU)
            self.assertEqual(abort.source, 0)
            self.assertEqual(abort.reason_diag, 2)
        finally:
            provider.kill()
