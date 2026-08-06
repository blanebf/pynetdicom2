"""Unit tests for :mod:`pynetdicom2.sopclass` service handlers.

These tests drive the SCP handlers directly with a light-weight fake
association object that records the DIMSE responses that would be sent, so no
real network association is required.
"""
import unittest
from typing import Any

import pydicom
from pydicom import uid

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


class ScpMissingDatasetTestCase(unittest.TestCase):
    """SCPs must respond with a failure status, not tear down the
    association, when a required Identifier/dataset is missing."""

    def test_qr_find_scp_missing_dataset(self) -> None:
        acceptor = FakeAcceptor(FakeAE())
        msg = dimsemessages.CFindRQMessage()
        msg.message_id = 7
        msg.sop_class_uid = uids.STUDY_ROOT_FIND_SOP_CLASS
        # No data_set assigned.
        sopclass.qr_find_scp(acceptor, _context(), msg)

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
        sopclass.qr_move_scp(acceptor, _context(), msg)

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

        sopclass.qr_move_scp(acceptor, ctx, msg)

        self.assertEqual(len(acceptor.sent), 1)
        rsp, _ = acceptor.sent[0]
        status = statuses.Status(rsp.status, dimsemessages.CMoveRSPMessage)
        self.assertTrue(status.is_success)


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
            acceptor, self._context(), self._make_report_msg()
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
            acceptor, self._context(), self._make_report_msg()
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(len(acceptor.sent), 1)
        rsp, _ = acceptor.sent[0]
        self.assertEqual(rsp.status, int(statuses.SUCCESS))


if __name__ == '__main__':
    unittest.main()
