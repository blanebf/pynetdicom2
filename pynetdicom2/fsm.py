# Copyright (c) 2021 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#
"""
Implementation of the OSI Upper Layer Services
DICOM, Part 8, Section 7
"""

from __future__ import absolute_import

import socket

from typing import Dict, Tuple, Callable
import six

from . import dimsemessages
from . import dsutils
from . import exceptions
from . import pdu


# TODO Make into enum after dropping Py2 support
class States(object):  # pylint: disable=too-few-public-methods
    """Services states enumeration."""

    # No association
    STA_1 = 0
    """Idle"""

    # Association establishment
    STA_2 = 1
    """Transport Connection Open (Awaiting A-ASSOCIATE-RQ PDU)"""

    STA_3 = 2
    """Awaiting Local A-ASSOCIATE response primitive (from local user)"""

    STA_4 = 3
    """
    Awaiting transport connection opening to complete
    (from local transport service)
    """

    STA_5 = 4
    """Awaiting A-ASSOCIATE-AC or A-ASSOCIATE-RJ PDU"""

    # Data transfer
    STA_6 = 5
    """Association established and ready for data transfer"""

    # Association release
    STA_7 = 6
    """Awaiting A-RELEASE-RP PDU"""

    STA_8 = 7
    """Awaiting local A-RELEASE response primitive (from local user)"""

    STA_9 = 8
    """Release collision requestor side; awaiting A-RELEASE response (from local user)"""

    STA_10 = 9
    """Release collision acceptor side; awaiting A-RELEASE-RP PDU"""

    STA_11 = 10
    """Release collision requestor side; awaiting A-RELEASE-RP PDU"""

    STA_12 = 11
    """Release collision acceptor side; awaiting A-RELEASE response primitive (from local user)"""

    STA_13 = 12
    """Awaiting Transport Connection Close Indication (Association no longer exists)"""


# TODO Make into enum after dropping Py2 support
class Events(object):  # pylint: disable=too-few-public-methods
    """Events enumeration."""

    EVT_1 = 0
    """A-ASSOCIATE request (local user)"""

    EVT_2 = 1
    """Transport connect confirmation (local transport service)"""

    EVT_3 = 2
    """A-ASSOCIATE-AC PDU (received on transport connection)"""

    EVT_4 = 3
    """A-ASSOCIATE-RJ PDU (received on transport connection)"""

    EVT_5 = 4
    """Transport connection indication (local transport service)"""

    EVT_6 = 5
    """A-ASSOCIATE-RQ PDU (on tranport connection)"""

    EVT_7 = 6
    """A-ASSOCIATE response primitive (accept)"""

    EVT_8 = 7
    """A-ASSOCIATE response primitive (reject)"""

    EVT_9 = 8
    """P-DATA request primitive"""

    EVT_10 = 9
    """P-DATA-TF PDU (on transport connection)"""

    EVT_11 = 10
    """A-RELEASE request primitive"""

    EVT_12 = 11
    """A-RELEASE-RQ PDU (on transport)"""

    EVT_13 = 12
    """A-RELEASE-RP PDU (on transport)"""

    EVT_14 = 13
    """A-RELEASE response primitive"""

    EVT_15 = 14
    """A-ABORT request primitive"""

    EVT_16 = 15
    """A-ABORT PDU (on transport)"""

    EVT_17 = 16
    """Transport connection closed"""

    EVT_18 = 17
    """ARTIM timer expired (rej/rel)"""

    EVT_19 = 18
    """Unrecognized/invalid PDU"""


class StateMachine(object):  # pylint: disable=too-many-public-methods
    """Service State Machine implementation.

    :ivar current_state: current state
    :ivar provider: DUL provider
    :ivar timer:
    :ivar store_in_file: set of SOP Class UIDs, for which incoming datasets should be stored in
                         a file, rather than in-memory
    :ivar get_file_cb: callback for getting a file object for storage
    :ivar accepted_contexts: accepted presentation contexts in current association
    :ivar dimse_decoder: decoder for incoming P-DATA-TF PDUs, used to re-create incoming DIMSE
                         message
    :ivar transition_table: state machine transition table
    """
    def __init__(self, provider, timer, store_in_file, get_file_cb):
        self.current_state = States.STA_1
        self.provider = provider
        self.timer = timer
        self.store_in_file = store_in_file
        self.get_file_cb = get_file_cb
        self.accepted_contexts = {}

        self.dimse_decoder = None

        self.transition_table = {
            (Events.EVT_1, States.STA_1): self.ae_1,

            (Events.EVT_2, States.STA_4): self.ae_2,

            (Events.EVT_3, States.STA_2): self.aa_1,
            (Events.EVT_3, States.STA_3): self.aa_8,
            (Events.EVT_3, States.STA_5): self.ae_3,
            (Events.EVT_3, States.STA_6): self.aa_8,
            (Events.EVT_3, States.STA_7): self.aa_8,
            (Events.EVT_3, States.STA_8): self.aa_8,
            (Events.EVT_3, States.STA_9): self.aa_8,
            (Events.EVT_3, States.STA_10): self.aa_8,
            (Events.EVT_3, States.STA_11): self.aa_8,
            (Events.EVT_3, States.STA_12): self.aa_8,
            (Events.EVT_3, States.STA_13): self.aa_6,

            (Events.EVT_4, States.STA_2): self.aa_1,
            (Events.EVT_4, States.STA_3): self.aa_8,
            (Events.EVT_4, States.STA_5): self.ae_4,
            (Events.EVT_4, States.STA_6): self.aa_8,
            (Events.EVT_4, States.STA_7): self.aa_8,
            (Events.EVT_4, States.STA_8): self.aa_8,
            (Events.EVT_4, States.STA_9): self.aa_8,
            (Events.EVT_4, States.STA_10): self.aa_8,
            (Events.EVT_4, States.STA_11): self.aa_8,
            (Events.EVT_4, States.STA_12): self.aa_8,
            (Events.EVT_4, States.STA_13): self.aa_6,

            (Events.EVT_5, States.STA_1): self.ae_5,

            (Events.EVT_6, States.STA_2): self.ae_6,
            (Events.EVT_6, States.STA_3): self.aa_8,
            (Events.EVT_6, States.STA_5): self.aa_8,
            (Events.EVT_6, States.STA_6): self.aa_8,
            (Events.EVT_6, States.STA_7): self.aa_8,
            (Events.EVT_6, States.STA_8): self.aa_8,
            (Events.EVT_6, States.STA_9): self.aa_8,
            (Events.EVT_6, States.STA_10): self.aa_8,
            (Events.EVT_6, States.STA_11): self.aa_8,
            (Events.EVT_6, States.STA_12): self.aa_8,
            (Events.EVT_6, States.STA_13): self.aa_7,

            (Events.EVT_7, States.STA_3): self.ae_7,

            (Events.EVT_8, States.STA_3): self.ae_8,

            (Events.EVT_9, States.STA_6): self.dt_1,
            (Events.EVT_9, States.STA_8): self.ar_7,

            (Events.EVT_10, States.STA_2): self.aa_1,
            (Events.EVT_10, States.STA_3): self.aa_8,
            (Events.EVT_10, States.STA_5): self.aa_8,
            (Events.EVT_10, States.STA_6): self.dt_2,
            (Events.EVT_10, States.STA_7): self.ar_6,
            (Events.EVT_10, States.STA_8): self.aa_8,
            (Events.EVT_10, States.STA_9): self.aa_8,
            (Events.EVT_10, States.STA_10): self.aa_8,
            (Events.EVT_10, States.STA_11): self.aa_8,
            (Events.EVT_10, States.STA_12): self.aa_8,
            (Events.EVT_10, States.STA_13): self.aa_6,

            (Events.EVT_11, States.STA_6): self.ar_1,

            (Events.EVT_12, States.STA_2): self.aa_1,
            (Events.EVT_12, States.STA_3): self.aa_8,
            (Events.EVT_12, States.STA_5): self.aa_8,
            (Events.EVT_12, States.STA_6): self.ar_2,
            (Events.EVT_12, States.STA_7): self.ar_8,
            (Events.EVT_12, States.STA_8): self.aa_8,
            (Events.EVT_12, States.STA_9): self.aa_8,
            (Events.EVT_12, States.STA_10): self.aa_8,
            (Events.EVT_12, States.STA_11): self.aa_8,
            (Events.EVT_12, States.STA_12): self.aa_8,
            (Events.EVT_12, States.STA_13): self.aa_6,

            (Events.EVT_13, States.STA_2): self.aa_1,
            (Events.EVT_13, States.STA_3): self.aa_8,
            (Events.EVT_13, States.STA_5): self.aa_8,
            (Events.EVT_13, States.STA_6): self.aa_8,
            (Events.EVT_13, States.STA_7): self.ar_3,
            (Events.EVT_13, States.STA_8): self.aa_8,
            (Events.EVT_13, States.STA_9): self.aa_8,
            (Events.EVT_13, States.STA_10): self.ar_10,
            (Events.EVT_13, States.STA_11): self.ar_3,
            (Events.EVT_13, States.STA_12): self.aa_8,
            (Events.EVT_13, States.STA_13): self.aa_6,

            (Events.EVT_14, States.STA_8): self.ar_4,
            (Events.EVT_14, States.STA_9): self.ar_9,
            (Events.EVT_14, States.STA_12): self.ar_4,

            (Events.EVT_15, States.STA_3): self.aa_1,
            (Events.EVT_15, States.STA_4): self.aa_2,
            (Events.EVT_15, States.STA_5): self.aa_1,
            (Events.EVT_15, States.STA_6): self.aa_1,
            (Events.EVT_15, States.STA_7): self.aa_1,
            (Events.EVT_15, States.STA_8): self.aa_1,
            (Events.EVT_15, States.STA_9): self.aa_1,
            (Events.EVT_15, States.STA_10): self.aa_1,
            (Events.EVT_15, States.STA_11): self.aa_1,
            (Events.EVT_15, States.STA_12): self.aa_1,

            (Events.EVT_16, States.STA_2): self.aa_2,
            (Events.EVT_16, States.STA_3): self.aa_3,
            (Events.EVT_16, States.STA_5): self.aa_3,
            (Events.EVT_16, States.STA_6): self.aa_3,
            (Events.EVT_16, States.STA_7): self.aa_3,
            (Events.EVT_16, States.STA_8): self.aa_3,
            (Events.EVT_16, States.STA_9): self.aa_3,
            (Events.EVT_16, States.STA_10): self.aa_3,
            (Events.EVT_16, States.STA_11): self.aa_3,
            (Events.EVT_16, States.STA_12): self.aa_3,
            (Events.EVT_16, States.STA_13): self.aa_2,

            (Events.EVT_17, States.STA_2): self.aa_5,
            (Events.EVT_17, States.STA_3): self.aa_4,
            (Events.EVT_17, States.STA_4): self.aa_4,
            (Events.EVT_17, States.STA_5): self.aa_4,
            (Events.EVT_17, States.STA_6): self.aa_4,
            (Events.EVT_17, States.STA_7): self.aa_4,
            (Events.EVT_17, States.STA_8): self.aa_4,
            (Events.EVT_17, States.STA_9): self.aa_4,
            (Events.EVT_17, States.STA_10): self.aa_4,
            (Events.EVT_17, States.STA_11): self.aa_4,
            (Events.EVT_17, States.STA_12): self.aa_4,
            (Events.EVT_17, States.STA_13): self.ar_5,

            (Events.EVT_18, States.STA_2): self.aa_2,
            (Events.EVT_18, States.STA_13): self.aa_2,

            (Events.EVT_19, States.STA_2): self.aa_1,
            (Events.EVT_19, States.STA_3): self.aa_8,
            (Events.EVT_19, States.STA_5): self.aa_8,
            (Events.EVT_19, States.STA_6): self.aa_8,
            (Events.EVT_19, States.STA_7): self.aa_8,
            (Events.EVT_19, States.STA_8): self.aa_8,
            (Events.EVT_19, States.STA_9): self.aa_8,
            (Events.EVT_19, States.STA_10): self.aa_8,
            (Events.EVT_19, States.STA_11): self.aa_8,
            (Events.EVT_19, States.STA_12): self.aa_8,
            (Events.EVT_19, States.STA_13): self.aa_7
        }  # type: Dict[Tuple[int,int],Callable[[],int]]

    @property
    def primitive(self):
        """Current PDU."""
        return self.provider.primitive

    @primitive.setter
    def primitive(self, value):
        self.provider.primitive = value

    @property
    def dul_socket(self):
        # type: () -> socket.socket
        """TCP Socket"""
        return self.provider.dul_socket

    @dul_socket.setter
    def dul_socket(self, value):
        self.provider.dul_socket = value

    @property
    def to_service_user(self):
        """Outgoing PDU/DIMSE message queue"""
        return self.provider.to_service_user

    def action(self, event):
        # (int) -> None
        """Execute the action triggered by event"""
        action = self.transition_table[(event, self.current_state)]
        self.current_state = action()

    def ae_1(self):
        """Issue TransportConnect request primitive to local transport service."""
        self.dul_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dul_socket.connect(self.primitive.called_presentation_address)
        return States.STA_4

    def ae_2(self):
        """Send A_ASSOCIATE-RQ PDU."""
        self.dul_socket.sendall(self.primitive.encode())
        return States.STA_5

    def ae_3(self):
        """Issue A-ASSOCIATE confirmation (accept) primitive."""
        self.to_service_user.put(self.primitive)
        return States.STA_6

    def ae_4(self):
        """Issue A-ASSOCIATE confirmation (reject) primitive and close transport
        connection.
        """
        self.to_service_user.put(self.primitive)
        self.dul_socket.close()
        self.dul_socket = None
        return States.STA_1

    def ae_5(self):
        """Issue transport connection response primitive; start ARTIM timer."""
        # Don't need to send this primitive.
        self.timer.start()
        return States.STA_2

    def ae_6(self):
        """Check A-ASSOCIATE-RQ.

        Stop ARTIM timer and if A-ASSOCIATE-RQ acceptable by service provider - issue
        A-ASSOCIATE indication primitive.
        """
        self.timer.stop()
        # Accept
        self.to_service_user.put(self.primitive)
        # TODO Look into why according to standard transition to `Sta13` may occur
        return States.STA_3

    def ae_7(self):
        """Send A-ASSOCIATE-AC PDU."""
        self.dul_socket.sendall(self.primitive.encode())
        return States.STA_6

    def ae_8(self):
        """Send A-ASSOCIATE-RJ PDU."""
        # not sure about this ...
        self.dul_socket.sendall(self.primitive.encode())
        return States.STA_13

    def dt_1(self):
        """Send P-DATA-TF PDU."""
        self.dul_socket.sendall(self.primitive.encode())
        self.primitive = None
        return States.STA_6

    def dt_2(self):
        """Send P-DATA indication primitive."""
        if self.dimse_decoder is None:
            self.dimse_decoder = DIMSEDecoder(
                self.accepted_contexts, self.store_in_file,
                self.get_file_cb
            )
        self.dimse_decoder.process(self.primitive)
        if not self.dimse_decoder.receiving:
            msg, pc_id = self.dimse_decoder.msg, self.dimse_decoder.pc_id
            self.to_service_user.put((msg, pc_id))
            self.dimse_decoder = None
        return States.STA_6

    def ar_1(self):
        """Send A-RELEASE-RQ PDU."""
        self.primitive = pdu.AReleaseRqPDU()
        self.dul_socket.sendall(self.primitive.encode())
        return States.STA_7

    def ar_2(self):
        """Send A-RELEASE indication primitive."""
        self.to_service_user.put(self.primitive)
        return States.STA_8

    def ar_3(self):
        """Issue A-RELEASE confirmation primitive and close transport connection."""
        self.to_service_user.put(self.primitive)
        self.dul_socket.close()
        self.dul_socket = None
        return States.STA_1

    def ar_4(self):
        """Issue A-RELEASE-RP PDU and start ARTIM timer."""
        self.primitive = pdu.AReleaseRpPDU()
        self.dul_socket.sendall(self.primitive.encode())
        self.timer.start()
        return States.STA_13

    def ar_5(self):
        """Stop ARTIM timer."""
        self.timer.stop()
        return States.STA_1

    def ar_6(self):
        """Issue P-DATA indication."""
        if self.dimse_decoder is None:
            self.dimse_decoder = DIMSEDecoder(
                self.accepted_contexts, self.store_in_file,
                self.get_file_cb
            )
        self.dimse_decoder.process(self.primitive)
        if not self.dimse_decoder.receiving:
            msg, pc_id = self.dimse_decoder.msg, self.dimse_decoder.pc_id
            self.to_service_user.put((msg, pc_id))
            self.dimse_decoder = None
        return States.STA_7

    def ar_7(self):
        """Issue P-DATA-TF PDU."""
        self.dul_socket.sendall(self.primitive.encode())
        return States.STA_8

    def ar_8(self):
        """Issue A-RELEASE indication (release collision)."""
        self.to_service_user.put(self.primitive)
        if self.provider.requestor == 1:
            return States.STA_9
        return States.STA_10

    def ar_9(self):
        """Send A-RELEASE-RP PDU."""
        self.primitive = pdu.AReleaseRpPDU()
        self.dul_socket.sendall(self.primitive.encode())
        return States.STA_11

    def ar_10(self):
        """Issue A-RELEASE confirmation primitive."""
        self.to_service_user.put(self.primitive)
        return States.STA_12

    def aa_1(self):
        """Send A-ABORT PDU (service-user source) and start (or restart)
        ARTIM timer.
        """
        self.dul_socket.sendall(self.primitive.encode())
        self.timer.restart()
        return States.STA_13

    def aa_2(self):
        """Stop ARTIM timer if running. Close transport connection."""
        self.timer.stop()
        self.dul_socket.close()
        self.dul_socket = None
        return States.STA_1

    def aa_3(self):
        """Issue A-ABORT or A-P-ABORT indication and close transport connection.

        If (service-user initiated abort):

            * Issue A-ABORT indication and close transport connection.

        Otherwise (service-provider initiated abort):

            * Issue A-P-ABORT indication and close transport connection.

        This action is triggered by the reception of an A-ABORT PDU.
        """
        self.to_service_user.put(self.primitive)
        self.dul_socket.close()
        self.dul_socket = None
        return States.STA_1

    def aa_4(self):
        """Issue A-P-ABORT indication primitive."""
        # TODO look into this action
        self.primitive = pdu.AAbortPDU(source=0, reason_diag=0)
        self.to_service_user.put(self.primitive)
        return States.STA_1

    def aa_5(self):
        """Stop ARTIM timer."""
        self.timer.stop()
        return States.STA_1

    def aa_6(self):
        """Ignore PDU."""
        self.primitive = None
        return States.STA_13

    def aa_7(self):
        """Send A-ABORT PDU."""
        self.dul_socket.sendall(self.primitive.encode())
        return States.STA_13

    def aa_8(self):
        """Send A-ABORT PDU, issue an A-P-ABORT indication and start ARTIM timer."""
        self.primitive = pdu.AAbortPDU(source=2, reason_diag=0)
        if self.dul_socket:
            self.dul_socket.sendall(self.primitive.encode())

            # Issue A-P-ABORT indication
            self.to_service_user.put(self.primitive)
            self.timer.start()
        return States.STA_13


class DIMSEDecoder(object):  # pylint: disable=too-few-public-methods
    """DIMSE Message decoder.

    Decodes incoming P-DATA-TF PDUs into DIMSE message instance.

    :ivar accepted_contexts: accepted presentation contexts in current association
    :ivar store_in_file: set of SOP Class UIDs, for which incoming datasets should be stored in
                         a file, rather than in-memory
    :ivar get_file_cb: callback for getting a file object for storage
    :ivar receiving: `True` if :class:`~pynetdicom2.fsm.DIMSEDecoder` instnace has not received all
                     P-DATA-TF PDUs for the current DIMSE message
    :ivar command_set_received: `True` if Command Set for DIMSE message is received
    :ivar data_set_received: `True` if Dataset  for DIMSE message is received
    :ivar pc_id: Presentation Context ID
    :ivar msg: decoded DIMSE message
    """
    def __init__(self, accepted_contexts, store_in_file, get_file_cb):
        """Initializes DIMSEDecoder instance

        :param accepted_contexts: accepted presentation contexts in current association
        :param store_in_file: set of SOP Class UIDs, for which incoming datasets should be stored in
                              a file, rather than in-memory
        :param get_file_cb: callback for getting a file object for storage
        """
        self.accepted_contexts = accepted_contexts
        self.store_in_file = store_in_file
        self.get_file_cb = get_file_cb

        self.receiving = True

        self.command_set_received = False
        self.data_set_received = False

        self.pc_id = None
        self.msg = None

        self._encoded_command_set = []
        self._encoded_data_set = []
        self._dataset_fp = None
        self._start = 0

    def process(self, p_data):
        """Processes new incoming P-DATA-TF PDU

        :param p_data: incoming P-DATA-TF PDU
        :raises exceptions.DIMSEProcessingError: raised if unknown PDV type is encountered
        """
        try:
            for value_item in p_data.data_value_items:
                # must be able to read P-DATA with several PDVs
                self.pc_id = value_item.context_id
                marker = six.indexbytes(value_item.data_value, 0)
                if marker in (1, 3):
                    self._encoded_command_set.append(value_item.data_value[1:])
                    if marker == 3:
                        self.command_set_received = True
                        command_set = dsutils.decode(
                            b''.join(self._encoded_command_set),
                            True, True
                        )

                        self.msg = self._command_set_to_message(command_set)
                        no_ds = command_set[(0x0000, 0x0800)].value == 0x0101
                        use_file = (self.msg.sop_class_uid in self.store_in_file)
                        if not no_ds and use_file:
                            ctx = self.accepted_contexts[self.pc_id]
                            self._dataset_fp, self._start = self.get_file_cb(ctx, command_set)
                            if self._encoded_data_set:
                                self._dataset_fp.writelines(self._encoded_data_set)
                        if no_ds or self.data_set_received:
                            self.receiving = False  # response: no dataset
                            break
                elif marker in (0, 2):
                    if self._dataset_fp:
                        self._dataset_fp.write(value_item.data_value[1:])
                    else:
                        self._encoded_data_set.append(value_item.data_value[1:])
                    if marker == 2:
                        self.data_set_received = True
                        if self.command_set_received:
                            self.receiving = False
                            break
                else:
                    raise exceptions.DIMSEProcessingError('Incorrect first PDV byte')
        except Exception:
            if self._dataset_fp:
                self._dataset_fp.close()
            raise

        if self.data_set_received:
            if self._dataset_fp:
                self._dataset_fp.seek(self._start)
                self.msg.data_set = self._dataset_fp
            else:
                self.msg.data_set = b''.join(self._encoded_data_set)

    @staticmethod
    def _command_set_to_message(command_set):
        command_field = command_set[(0x0000, 0x0100)].value
        msg_type = dimsemessages.MESSAGE_TYPE[command_field]
        msg = msg_type(command_set)
        return msg
