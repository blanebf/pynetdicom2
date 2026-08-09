"""Unit tests for :mod:`pynetdicom2.asceprovider`.

Association normally starts a DUL service provider thread, so the tests build
a bare instance with ``object.__new__`` and populate only the attributes used
by the method under test. The DUL provider itself is replaced with a mock so
no real socket or thread is involved.
"""
import unittest
from unittest import mock

from pydicom import uid

from pynetdicom2 import asceprovider
from pynetdicom2 import dimsemessages
from pynetdicom2 import exceptions
from pynetdicom2 import pdu
from pynetdicom2 import statuses
from pynetdicom2 import uids
from pynetdicom2 import userdataitems


def _make_bare_association() -> asceprovider.Association:
    """Creates an association without starting its DUL provider."""
    assoc = object.__new__(asceprovider.Association)
    assoc.dul = mock.MagicMock()
    assoc.association_established = True
    return assoc


class KillTestCase(unittest.TestCase):
    def test_kill_stops_gracefully_and_waits(self) -> None:
        # If the provider reports it stopped gracefully, kill() still calls
        # the provider's kill() so the service thread is guaranteed to have
        # exited before returning, and the association is no longer marked
        # established.
        assoc = _make_bare_association()
        assoc.dul.stop.return_value = True

        assoc.kill()

        assoc.dul.stop.assert_called()
        assoc.dul.kill.assert_called_once()
        self.assertFalse(assoc.association_established)

    def test_kill_does_not_busy_spin_when_idle(self) -> None:
        # Once the provider stops gracefully, kill() must stop retrying the
        # graceful path immediately rather than looping over stop().
        assoc = _make_bare_association()
        assoc.dul.stop.return_value = True

        assoc.kill()

        self.assertEqual(assoc.dul.stop.call_count, 1)

    def test_kill_retries_then_forces_termination(self) -> None:
        # When the association never becomes idle, kill() retries graceful
        # stopping a bounded number of times and then forces termination.
        assoc = _make_bare_association()
        assoc.dul.stop.return_value = False

        with mock.patch('pynetdicom2.asceprovider.time.sleep') as sleep_mock:
            assoc.kill()

        self.assertEqual(assoc.dul.stop.call_count, 1000)
        self.assertEqual(sleep_mock.call_count, 1000)
        assoc.dul.kill.assert_called_once()
        self.assertFalse(assoc.association_established)


class ReleaseTestCase(unittest.TestCase):
    def test_release_normal_flow(self) -> None:
        assoc = _make_bare_association()
        assoc.ae = mock.MagicMock()
        assoc.dul.receive.return_value = pdu.AReleaseRpPDU()

        rsp = assoc.release()

        self.assertIsInstance(rsp, pdu.AReleaseRpPDU)
        rq = assoc.dul.send.call_args_list[0].args[0]
        self.assertIsInstance(rq, pdu.AReleaseRqPDU)
        assoc.dul.kill.assert_called_once()

    def test_release_collision_approves_remote_request(self) -> None:
        # PS3.7 7.2.4: if the remote AE requested release while our request
        # was in flight, approve it (send A-RELEASE-RP) and then complete our
        # own release once the remote confirmation arrives.
        assoc = _make_bare_association()
        assoc.ae = mock.MagicMock()
        assoc.dul.receive.side_effect = [
            pdu.AReleaseRqPDU(),  # remote release request
            pdu.AReleaseRpPDU()   # confirmation of our request
        ]

        rsp = assoc.release()

        self.assertIsInstance(rsp, pdu.AReleaseRpPDU)
        sent = [call.args[0] for call in assoc.dul.send.call_args_list]
        self.assertIsInstance(sent[0], pdu.AReleaseRqPDU)
        self.assertIsInstance(sent[1], pdu.AReleaseRpPDU)
        assoc.dul.kill.assert_called_once()


class CancelHandlingTestCase(unittest.TestCase):
    def test_cancel_is_accepted_without_tearing_down(self) -> None:
        # A C-CANCEL must not raise (previously it triggered a
        # DIMSEProcessingError that tore down the association): it is
        # acknowledged and the message loop keeps running.
        class StopLoop(Exception):
            pass

        cancel = dimsemessages.CCancelRQMessage()
        cancel.message_id_being_responded_to = 5

        assoc = object.__new__(asceprovider.AssociationAcceptor)
        assoc.is_killed = False
        assoc.ae = mock.MagicMock()
        assoc.dul = mock.MagicMock()
        assoc.dul.receive.side_effect = [(cancel, 1), StopLoop()]

        # StopLoop proves the loop survived the C-CANCEL and kept iterating.
        with self.assertRaises(StopLoop):
            assoc._loop()


class AcceptValidationTestCase(unittest.TestCase):
    """Malformed association requests from a peer must raise descriptive
    association errors instead of raw IndexError/KeyError/AssertionError."""

    APPLICATION_CONTEXT = '1.2.840.10008.3.1.1.1'
    SOP_CLASS = uid.UID('1.2.3.4')
    TS = uid.ImplicitVRLittleEndian

    def _make_acceptor(self) -> asceprovider.AssociationAcceptor:
        assoc = object.__new__(asceprovider.AssociationAcceptor)
        assoc.dul = mock.MagicMock()
        assoc.ae = mock.MagicMock()
        assoc.ae.supported_scp = {self.SOP_CLASS: object()}
        assoc.ae.supported_ts = frozenset([self.TS])
        assoc.max_pdu_length = 65536
        assoc.sop_classes_as_scp = {}
        assoc.accepted_contexts = {}
        return assoc

    def _rq(self, variable_items: list) -> pdu.AAssociateRqPDU:
        return pdu.AAssociateRqPDU(
            called_ae_title='CALLED',
            calling_ae_title='CALLING',
            variable_items=variable_items
        )

    def _context_item(self, pc_id: int) -> pdu.PresentationContextItemRQ:
        return pdu.PresentationContextItemRQ(
            pc_id,
            pdu.AbstractSyntaxSubItem(str(self.SOP_CLASS)),
            [pdu.TransferSyntaxSubItem(str(self.TS))]
        )

    def _user_info(self) -> pdu.UserInformationItem:
        return pdu.UserInformationItem(
            [userdataitems.MaximumLengthSubItem(65536)]
        )

    def test_empty_variable_items_rejected(self) -> None:
        assoc = self._make_acceptor()
        with self.assertRaises(exceptions.AssociationError):
            assoc.accept(self._rq([]))

    def test_missing_application_context_rejected(self) -> None:
        assoc = self._make_acceptor()
        with self.assertRaises(exceptions.AssociationError):
            assoc.accept(self._rq([self._user_info()]))

    def test_user_info_without_sub_items_rejected(self) -> None:
        assoc = self._make_acceptor()
        ctx = pdu.ApplicationContextItem(self.APPLICATION_CONTEXT)
        with self.assertRaises(exceptions.AssociationError):
            assoc.accept(self._rq([ctx, pdu.UserInformationItem([])]))

    def test_invalid_and_duplicate_context_ids_refused(self) -> None:
        assoc = self._make_acceptor()
        ctx = pdu.ApplicationContextItem(self.APPLICATION_CONTEXT)
        assoc.accept(self._rq([
            ctx,
            self._context_item(1),   # valid
            self._context_item(1),   # duplicate
            self._context_item(2),   # even ID - invalid
            self._user_info()
        ]))

        res = assoc.dul.send.call_args.args[0]
        ac_items = [
            item for item in res.variable_items
            if isinstance(item, pdu.PresentationContextItemAC)
        ]
        self.assertEqual(
            [item.result_reason for item in ac_items], [0, 2, 2]
        )
        self.assertEqual(list(assoc.accepted_contexts), [1])


class UnsupportedRequestTestCase(unittest.TestCase):
    """A request for an unsupported SOP Class must be refused with a
    failure response, not tear down the whole association."""

    def test_unsupported_request_refused_not_fatal(self) -> None:
        class StopLoop(Exception):
            pass

        echo = dimsemessages.CEchoRQMessage()
        echo.message_id = 12
        echo.sop_class_uid = uids.VERIFICATION_SOP_CLASS

        assoc = object.__new__(asceprovider.AssociationAcceptor)
        assoc.is_killed = False
        assoc.ae = mock.MagicMock()
        assoc.ae.supported_scp = {}  # nothing supported
        assoc.dul = mock.MagicMock()
        assoc.dul.receive.side_effect = [(echo, 3), StopLoop()]
        assoc.sop_classes_as_scp = {
            3: (3, uid.UID('1.2.3'), uid.ImplicitVRLittleEndian)
        }

        with mock.patch.object(
                asceprovider.Association, 'send') as send_mock:
            # StopLoop proves the loop kept running after refusing the
            # request instead of raising ClassNotSupportedError.
            with self.assertRaises(StopLoop):
                assoc._loop()

        self.assertEqual(send_mock.call_count, 1)
        rsp, ctx_id = send_mock.call_args.args
        self.assertIsInstance(rsp, dimsemessages.CEchoRSPMessage)
        self.assertEqual(ctx_id, 3)
        self.assertEqual(rsp.message_id_being_responded_to, 12)
        self.assertEqual(
            rsp.status, int(statuses.SOP_CLASS_NOT_SUPPORTED)
        )


if __name__ == '__main__':
    unittest.main()
