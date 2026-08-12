"""Unit tests for :mod:`pynetdicom2.sopclass` service handlers.

These tests drive the SCP handlers directly with a light-weight fake
association object that records the DIMSE responses that would be sent, so no
real network association is required.
"""
import contextlib
import unittest
from typing import Any, Iterator, cast

import pydicom
from pydicom import uid
from pydicom.tag import Tag

from pynetdicom2 import asceprovider
from pynetdicom2 import dimsemessages
from pynetdicom2 import dsutils
from pynetdicom2 import exceptions
from pynetdicom2 import fsm
from pynetdicom2 import sopclass
from pynetdicom2 import statuses
from pynetdicom2 import uids


class FakeAE:
    """Minimal AE stub exposing the handler hooks used by the SCPs."""

    def __init__(self, **handlers: Any) -> None:
        self._handlers = handlers

    def __getattr__(self, name: str) -> Any:
        try:
            return self._handlers[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class FakeAcceptor:
    """Records responses sent by an SCP handler."""

    def __init__(self, ae: FakeAE) -> None:
        self.ae = ae
        self.remote_ae = 'REMOTE'
        self.sent: list[tuple[Any, int]] = []

    def send(self, msg: Any, ctx_id: int) -> None:
        self.sent.append((msg, ctx_id))


def _context() -> fsm.PContextDef:
    return fsm.PContextDef(
        1, uids.STUDY_ROOT_FIND_SOP_CLASS, uid.ImplicitVRLittleEndian
    )


def _as_acceptor(fake: FakeAcceptor) -> asceprovider.AssociationAcceptor:
    """Adapts the recording fake to the type the SCP handlers expect."""
    return cast(asceprovider.AssociationAcceptor, fake)


def _as_requester(fake: object) -> asceprovider.AssociationRequester:
    """Adapts a fake requester to the type the SCU handlers expect."""
    return cast(asceprovider.AssociationRequester, fake)


class ScpMissingDatasetTestCase(unittest.TestCase):
    """SCPs must respond with a failure status, not tear down the
    association, when a required Identifier/dataset is missing."""

    def test_qr_find_scp_missing_dataset(self) -> None:
        acceptor = FakeAcceptor(FakeAE())
        msg = dimsemessages.CFindRQMessage()
        msg.message_id = 7
        msg.sop_class_uid = uids.STUDY_ROOT_FIND_SOP_CLASS
        # No data_set assigned.
        sopclass.qr_find_scp(_as_acceptor(acceptor), _context(), msg)

        self.assertEqual(len(acceptor.sent), 1)
        rsp, ctx_id = acceptor.sent[0]
        self.assertEqual(ctx_id, 1)
        self.assertIsInstance(rsp, dimsemessages.CFindRSPMessage)
        status = statuses.Status(rsp.status, dimsemessages.CFindRSPMessage)
        self.assertTrue(status.is_failure)

    def test_qr_move_scp_missing_dataset(self) -> None:
        acceptor = FakeAcceptor(FakeAE())
        msg = dimsemessages.CMoveRQMessage()
        msg.message_id = 9
        msg.sop_class_uid = uids.STUDY_ROOT_MOVE_SOP_CLASS
        sopclass.qr_move_scp(_as_acceptor(acceptor), _context(), msg)

        self.assertEqual(len(acceptor.sent), 1)
        rsp, _ = acceptor.sent[0]
        self.assertIsInstance(rsp, dimsemessages.CMoveRSPMessage)
        status = statuses.Status(rsp.status, dimsemessages.CMoveRSPMessage)
        self.assertTrue(status.is_failure)


class QrMoveScpNothingToMoveTestCase(unittest.TestCase):
    def test_no_operations_sends_single_success_and_returns(self) -> None:
        # on_receive_move reports zero operations: exactly one SUCCESS response
        # must be sent, and the handler must NOT open a second association.
        def on_receive_move(context: Any, ds: Any, dest: Any) -> Any:
            return {'aet': 'DEST'}, 0, iter([])

        def request_association(remote_ae: Any) -> Any:
            raise AssertionError(
                'request_association must not be called when nop == 0'
            )

        ae = FakeAE(
            on_receive_move=on_receive_move,
            request_association=request_association,
        )
        acceptor = FakeAcceptor(ae)

        ctx = _context()
        ctx = fsm.PContextDef(
            1, uids.STUDY_ROOT_MOVE_SOP_CLASS, uid.ImplicitVRLittleEndian
        )
        msg = dimsemessages.CMoveRQMessage()
        msg.message_id = 3
        msg.sop_class_uid = uids.STUDY_ROOT_MOVE_SOP_CLASS
        msg.move_destination = 'DEST'
        query = pydicom.Dataset()
        query.QueryRetrieveLevel = 'STUDY'
        msg.data_set = dsutils.encode(query, True, True)

        sopclass.qr_move_scp(_as_acceptor(acceptor), ctx, msg)

        self.assertEqual(len(acceptor.sent), 1)
        rsp, _ = acceptor.sent[0]
        status = statuses.Status(rsp.status, dimsemessages.CMoveRSPMessage)
        self.assertTrue(status.is_success)


def _stored_instance() -> pydicom.Dataset:
    """Builds a dataset that looks like a stored SOP instance."""
    ds = pydicom.Dataset()
    ds.SOPClassUID = uids.CT_IMAGE_STORAGE
    ds.SOPInstanceUID = uid.generate_uid()
    return ds


class QrMoveScpFinalStatusTestCase(unittest.TestCase):
    """The final C-MOVE-RSP status must reflect the outcome of the
    sub-operations (PS3.4 C.4.2): Success only when nothing failed or
    warned, otherwise Warning B000."""

    def _make_move(self, sub_statuses: list[statuses.Status]) -> FakeAcceptor:
        datasets = [_stored_instance() for _ in sub_statuses]

        def on_receive_move(
                context: Any, ds: Any, dest: Any
        ) -> tuple[asceprovider.RemoteAEConfig, int, Iterator[Any]]:
            remote = asceprovider.RemoteAEConfig(
                aet='DEST', address='localhost', port=11113
            )
            return remote, len(datasets), iter(datasets)

        sub_results = list(sub_statuses)
        self.sub_op_msg_ids: list[int] = []
        sub_op_msg_ids = self.sub_op_msg_ids

        class FakeAssociation:
            def get_scu(self, sop_class_uid: Any) -> Any:
                def service(
                        data_set: Any, msg_id: int, **kwargs: Any
                ) -> statuses.Status:
                    sub_op_msg_ids.append(msg_id)
                    return sub_results.pop(0)
                return service

        @contextlib.contextmanager
        def request_association(
                remote_ae: Any
        ) -> Iterator[FakeAssociation]:
            yield FakeAssociation()

        ae = FakeAE(
            on_receive_move=on_receive_move,
            request_association=request_association
        )
        acceptor = FakeAcceptor(ae)

        ctx = fsm.PContextDef(
            1, uids.STUDY_ROOT_MOVE_SOP_CLASS, uid.ImplicitVRLittleEndian
        )
        msg = dimsemessages.CMoveRQMessage()
        msg.message_id = 5
        msg.sop_class_uid = uids.STUDY_ROOT_MOVE_SOP_CLASS
        msg.move_destination = 'DEST'
        query = pydicom.Dataset()
        query.QueryRetrieveLevel = 'STUDY'
        msg.data_set = dsutils.encode(query, True, True)

        sopclass.qr_move_scp(_as_acceptor(acceptor), ctx, msg)
        return acceptor

    def test_all_sub_ops_succeed_final_is_success(self) -> None:
        acceptor = self._make_move(
            [statuses.SUCCESS, statuses.SUCCESS]
        )
        # Two pending responses plus the final one.
        self.assertEqual(len(acceptor.sent), 3)
        final, _ = acceptor.sent[-1]
        status = statuses.Status(
            final.status, dimsemessages.CMoveRSPMessage
        )
        self.assertTrue(status.is_success)
        self.assertEqual(final.num_of_completed_sub_ops, 2)
        self.assertEqual(final.num_of_failed_sub_ops, 0)
        self.assertEqual(final.num_of_warning_sub_ops, 0)

    def test_failed_sub_op_final_is_warning(self) -> None:
        acceptor = self._make_move(
            [statuses.SUCCESS, statuses.C_STORE_OUT_OF_RESOURCES]
        )
        final, _ = acceptor.sent[-1]
        status = statuses.Status(
            final.status, dimsemessages.CMoveRSPMessage
        )
        self.assertEqual(int(status), int(statuses.C_MOVE_WARNING))
        self.assertTrue(status.is_warning)
        self.assertEqual(final.num_of_failed_sub_ops, 1)
        self.assertEqual(final.num_of_remaining_sub_ops, 0)

    def test_warning_sub_op_final_is_warning(self) -> None:
        acceptor = self._make_move(
            [statuses.SUCCESS, statuses.C_STORE_ELEMENTS_DISCARDED]
        )
        final, _ = acceptor.sent[-1]
        status = statuses.Status(
            final.status, dimsemessages.CMoveRSPMessage
        )
        self.assertEqual(int(status), int(statuses.C_MOVE_WARNING))
        self.assertTrue(status.is_warning)
        self.assertEqual(final.num_of_warning_sub_ops, 1)

    def test_sub_op_message_ids_start_at_one(self) -> None:
        # PS3.7 9.1.1.1.3: message IDs must be non-zero.
        self._make_move([statuses.SUCCESS, statuses.SUCCESS])
        self.assertEqual(self.sub_op_msg_ids, [1, 2])


class QrFindScpFinalStatusTestCase(unittest.TestCase):
    """A final (non-pending) C-FIND response must not be followed by an
    extra Success response."""

    def _make_find(self, yielded: list[Any]) -> FakeAcceptor:
        def on_receive_find(context: Any, ds: Any) -> Any:
            yield from yielded

        ae = FakeAE(on_receive_find=on_receive_find)
        acceptor = FakeAcceptor(ae)

        ctx = fsm.PContextDef(
            1, uids.STUDY_ROOT_FIND_SOP_CLASS, uid.ImplicitVRLittleEndian
        )
        msg = dimsemessages.CFindRQMessage()
        msg.message_id = 11
        msg.sop_class_uid = uids.STUDY_ROOT_FIND_SOP_CLASS
        query = pydicom.Dataset()
        query.QueryRetrieveLevel = 'STUDY'
        msg.data_set = dsutils.encode(query, True, True)

        sopclass.qr_find_scp(_as_acceptor(acceptor), ctx, msg)
        return acceptor

    def test_no_matches_sends_success(self) -> None:
        acceptor = self._make_find([])
        self.assertEqual(len(acceptor.sent), 1)
        rsp, _ = acceptor.sent[-1]
        status = statuses.Status(
            rsp.status, dimsemessages.CFindRSPMessage
        )
        self.assertTrue(status.is_success)

    def test_pending_matches_then_success(self) -> None:
        match = pydicom.Dataset()
        match.PatientID = 'ID001'
        acceptor = self._make_find([(match, statuses.C_FIND_PENDING)])
        self.assertEqual(len(acceptor.sent), 2)
        pending, _ = acceptor.sent[0]
        final, _ = acceptor.sent[1]
        pending_status = statuses.Status(
            pending.status, dimsemessages.CFindRSPMessage
        )
        final_status = statuses.Status(
            final.status, dimsemessages.CFindRSPMessage
        )
        self.assertTrue(pending_status.is_pending)
        self.assertTrue(final_status.is_success)

    def test_handler_failure_not_followed_by_success(self) -> None:
        match = pydicom.Dataset()
        acceptor = self._make_find(
            [(match, statuses.C_FIND_UNABLE_TO_PROCESS)]
        )
        self.assertEqual(len(acceptor.sent), 1)
        rsp, _ = acceptor.sent[-1]
        status = statuses.Status(
            rsp.status, dimsemessages.CFindRSPMessage
        )
        self.assertTrue(status.is_failure)


class StorageScuMoveOriginatorTestCase(unittest.TestCase):
    """Per PS3.7 9.3.1.1 the Move Originator fields are conditional: they
    must only be sent when the C-STORE is a C-MOVE sub-operation."""

    def _run_store(self, **kwargs: Any) -> Any:
        sent: list[Any] = []

        class FakeRequester:
            def send(self, msg: Any, ctx_id: int) -> None:
                sent.append((msg, ctx_id))

            def receive(self) -> Any:
                rsp = dimsemessages.CStoreRSPMessage()
                rsp.status = int(statuses.SUCCESS)
                return rsp, 1

        ctx = fsm.PContextDef(
            1, uids.CT_IMAGE_STORAGE, uid.ImplicitVRLittleEndian
        )
        sopclass.storage_scu(
            _as_requester(FakeRequester()),
            ctx, _stored_instance(), 1, **kwargs
        )
        msg, _ = sent[0]
        return msg

    def test_ordinary_store_omits_move_originator(self) -> None:
        msg = self._run_store()
        self.assertIsNone(msg.move_originator_aet)
        self.assertIsNone(msg.move_originator_message_id)
        self.assertNotIn(Tag(0x0000, 0x1030), msg.command_set)
        self.assertNotIn(Tag(0x0000, 0x1031), msg.command_set)

    def test_move_originated_store_sets_originator(self) -> None:
        msg = self._run_store(
            move_originator_aet='MOVE_AET',
            move_originator_message_id=77
        )
        self.assertEqual(msg.move_originator_aet, 'MOVE_AET')
        self.assertEqual(msg.move_originator_message_id, 77)


class QrGetScuContextTestCase(unittest.TestCase):
    """C-STORE sub-operations of C-GET must be reported with the accepted
    C-STORE presentation context - not the C-GET context."""

    def test_store_context_passed_to_handler_and_yielded(self) -> None:
        get_ctx = fsm.PContextDef(
            1, uids.STUDY_ROOT_GET_SOP_CLASS, uid.ImplicitVRLittleEndian
        )
        store_ctx = fsm.PContextDef(
            3, uids.CT_IMAGE_STORAGE, uid.ExplicitVRLittleEndian
        )

        received_contexts: list[Any] = []

        def on_receive_store(context: Any, ds: Any) -> statuses.Status:
            received_contexts.append(context)
            return statuses.SUCCESS

        ae = FakeAE(on_receive_store=on_receive_store, store_in_file=set())

        instance = _stored_instance()
        instance.PatientID = 'ID001'

        class FakeRequester:
            def __init__(self) -> None:
                self.ae = ae
                self.accepted_contexts = {3: store_ctx}
                self.sent: list[Any] = []
                store_msg = dimsemessages.CStoreRQMessage()
                store_msg.message_id = 42
                store_msg.sop_class_uid = uids.CT_IMAGE_STORAGE
                store_msg.affected_sop_instance_uid = (
                    instance.SOPInstanceUID
                )
                # Encoded with the store context transfer syntax.
                store_msg.data_set = dsutils.encode(instance, False, True)
                final_rsp = dimsemessages.CGetRSPMessage()
                final_rsp.status = int(statuses.SUCCESS)
                self._incoming = [(store_msg, 3), (final_rsp, 1)]

            def send(self, msg: Any, ctx_id: int) -> None:
                self.sent.append((msg, ctx_id))

            def receive(self) -> Any:
                return self._incoming.pop(0)

        requester = FakeRequester()
        results = list(sopclass.qr_get_scu(
            _as_requester(requester), get_ctx, pydicom.Dataset(), 1
        ))

        self.assertEqual(len(results), 1)
        yielded_ctx, yielded_ds = results[0]
        self.assertIs(yielded_ctx, store_ctx)
        self.assertEqual(yielded_ds.PatientID, 'ID001')
        self.assertEqual(received_contexts, [store_ctx])

        # C-STORE response is sent on the store presentation context with
        # the handler status.
        rsp_msg, rsp_ctx_id = requester.sent[-1]
        self.assertEqual(rsp_ctx_id, 3)
        self.assertEqual(int(rsp_msg.status), int(statuses.SUCCESS))


class StorageCommitmentEventReportTestCase(unittest.TestCase):
    def _make_report_msg(self) -> dimsemessages.NEventReportRQMessage:
        report_ds = pydicom.Dataset()
        report_ds.TransactionUID = uid.generate_uid()
        msg = dimsemessages.NEventReportRQMessage()
        msg.sop_class_uid = uids.STORAGE_COMMITMENT_SOP_CLASS
        msg.event_type_id = 1
        msg.affected_sop_instance_uid = (
            sopclass.STORAGE_COMMITMENT_PUSH_MODEL_SOP_CLASS
        )
        msg.data_set = dsutils.encode(report_ds, True, True)
        return msg

    def _context(self) -> fsm.PContextDef:
        return fsm.PContextDef(
            1,
            uids.STORAGE_COMMITMENT_SOP_CLASS,
            uid.ImplicitVRLittleEndian,
        )

    def test_failure_response_is_sent(self) -> None:
        # Previously a raising on_commitment_response left the response unsent.
        def on_commitment_response(*args: Any, **kwargs: Any) -> None:
            raise exceptions.EventHandlingError('boom')

        ae = FakeAE(on_commitment_response=on_commitment_response)
        acceptor = FakeAcceptor(ae)

        sopclass.StorageCommitment.n_event_report(
            _as_acceptor(acceptor), self._context(), self._make_report_msg()
        )

        self.assertEqual(len(acceptor.sent), 1)
        rsp, _ = acceptor.sent[0]
        self.assertEqual(rsp.status, int(statuses.PROCESSING_FAILURE))

    def test_success_response_is_sent(self) -> None:
        calls: list[Any] = []

        def on_commitment_response(*args: Any, **kwargs: Any) -> None:
            calls.append(args)

        ae = FakeAE(on_commitment_response=on_commitment_response)
        acceptor = FakeAcceptor(ae)

        sopclass.StorageCommitment.n_event_report(
            _as_acceptor(acceptor), self._context(), self._make_report_msg()
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(len(acceptor.sent), 1)
        rsp, _ = acceptor.sent[0]
        self.assertEqual(rsp.status, int(statuses.SUCCESS))


if __name__ == '__main__':
    unittest.main()
