# Copyright (c) 2014 Pavel 'Blane' Tuchin
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

from . import pdu

# Finite State machine action definitions


def ae_1(provider):
    """Issue TransportConnect request primitive to local transport service."""
    provider.dul_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    provider.dul_socket.connect(provider.primitive.called_presentation_address)
    return 'Sta4'


def ae_2(provider):
    """Send A_ASSOCIATE-RQ PDU."""
    provider.dul_socket.send(provider.primitive.encode())
    return 'Sta5'


def ae_3(provider):
    """Issue A-ASSOCIATE confirmation (accept) primitive."""
    provider.to_service_user.put(provider.primitive)
    return 'Sta6'


def ae_4(provider):
    """Issue A-ASSOCIATE confirmation (reject) primitive and close transport
    connection.
    """
    provider.to_service_user.put(provider.primitive)
    provider.dul_socket.close()
    provider.dul_socket = None
    return 'Sta1'


def ae_5(provider):
    """Issue transport connection response primitive; start ARTIM timer."""
    # Don't need to send this primitive.
    provider.timer.start()
    return 'Sta2'


def ae_6(provider):
    """Check A-ASSOCIATE-RQ.

    Stop ARTIM timer and if A-ASSOCIATE-RQ acceptable by service provider
    - Issue A-ASSOCIATE indication primitive
    """
    provider.timer.stop()
    # Accept
    provider.to_service_user.put(provider.primitive)
    # TODO Look into why according to standard transition to `Sta13` may occur
    return 'Sta3'


def ae_7(provider):
    """Send A-ASSOCIATE-AC PDU."""
    provider.dul_socket.send(provider.primitive.encode())
    return 'Sta6'


def ae_8(provider):
    """Send A-ASSOCIATE-RJ PDU."""
    # not sure about this ...
    provider.dul_socket.send(provider.primitive.encode())
    return 'Sta13'


def dt_1(provider):
    """Send P-DATA-TF PDU."""
    provider.dul_socket.send(provider.primitive.encode())
    provider.primitive = None
    return 'Sta6'


def dt_2(provider):
    """Send P-DATA indication primitive."""
    provider.to_service_user.put(provider.primitive)
    return 'Sta6'


def ar_1(provider):
    """Send A-RELEASE-RQ PDU."""
    provider.primitive = pdu.AReleaseRqPDU()
    provider.dul_socket.send(provider.primitive.encode())
    return 'Sta7'


def ar_2(provider):
    """Send A-RELEASE indication primitive."""
    provider.to_service_user.put(provider.primitive)
    return 'Sta8'


def ar_3(provider):
    """Issue A-RELEASE confirmation primitive and close transport connection."""
    provider.to_service_user.put(provider.primitive)
    provider.dul_socket.close()
    provider.dul_socket = None
    return 'Sta1'


def ar_4(provider):
    """Issue A-RELEASE-RP PDU and start ARTIM timer."""
    provider.primitive = pdu.AReleaseRpPDU()
    provider.dul_socket.send(provider.primitive.encode())
    provider.timer.start()
    return 'Sta13'


def ar_5(provider):
    """Stop ARTIM timer."""
    provider.timer.stop()
    return 'Sta1'


def ar_6(provider):
    """Issue P-DATA indication."""
    provider.to_service_user.put(provider.primitive)
    return 'Sta7'


def ar_7(provider):
    """Issue P-DATA-TF PDU."""
    provider.dul_socket.send(provider.primitive.encode())
    return 'Sta8'


def ar_8(provider):
    """Issue A-RELEASE indication (release collision)."""
    provider.to_service_user.put(provider.primitive)
    if provider.requestor == 1:
        return 'Sta9'
    else:
        return 'Sta10'


def ar_9(provider):
    """Send A-RELEASE-RP PDU."""
    provider.primitive = pdu.AReleaseRpPDU()
    provider.dul_socket.send(provider.primitive.encode())
    return 'Sta11'


def ar_10(provider):
    """Issue A-RELEASE confirmation primitive."""
    provider.to_service_user.put(provider.primitive)
    return 'Sta12'


def aa_1(provider):
    """Send A-ABORT PDU (service-user source) and start (or restart)
    ARTIM timer.
    """
    provider.dul_socket.send(provider.primitive.encode())
    provider.timer.restart()
    return 'Sta13'


def aa_2(provider):
    """Stop ARTIM timer if running. Close transport connection."""
    provider.timer.stop()
    provider.dul_socket.close()
    provider.dul_socket = None
    return 'Sta1'


def aa_3(provider):
    """Issue A-ABORT or A-P-ABORT indication and close transport connection.

    If (service-user initiated abort):
       - Issue A-ABORT indication and close transport connection.
         Otherwise (service-provider initiated abort):
       - Issue A-P-ABORT indication and close transport connection.
         This action is triggered by the reception of an A-ABORT PDU."""
    provider.to_service_user.put(provider.primitive)
    provider.dul_socket.close()
    provider.dul_socket = None
    return 'Sta1'


def aa_4(provider):
    """Issue A-P-ABORT indication primitive."""
    # TODO look into this action
    provider.primitive = pdu.AAbortPDU(source=0, reason_diag=0)
    provider.to_service_user.put(provider.primitive)
    return 'Sta1'


def aa_5(provider):
    """Stop ARTIM timer."""
    provider.timer.stop()
    return 'Sta1'


def aa_6(provider):
    """Ignore PDU."""
    provider.primitive = None
    return 'Sta13'


def aa_7(provider):
    """Send A-ABORT PDU."""
    provider.dul_socket.send(provider.primitive.encode())
    return 'Sta13'


def aa_8(provider):
    """Send A-ABORT PDU, issue an A-P-ABORT indication and start ARTIM timer."""
    provider.primitive = pdu.AAbortPDU(source=2, reason_diag=0)
    if provider.dul_socket:
        provider.dul_socket.send(provider.primitive.encode())

        # Issue A-P-ABORT indication
        provider.to_service_user.put(provider.primitive)
        provider.timer.start()
    return 'Sta13'


# Finite State Machine

# states
states = {
    # No association
    'Sta1': 'Idle',
    # Association establishment
    'Sta2': 'Transport Connection Open (Awaiting A-ASSOCIATE-RQ PDU)',
    'Sta3': 'Awaiting Local A-ASSOCIATE response primitive (from local user)',
    'Sta4': 'Awaiting transport connection opening to complete (from local '
            'transport service',
    'Sta5': 'Awaiting A-ASSOCIATE-AC or A-ASSOCIATE-RJ PDU',
    # Data transfer
    'Sta6': 'Association established and ready for data transfer',
    # Association release
    'Sta7': 'Awaiting A-RELEASE-RP PDU',
    'Sta8': 'Awaiting local A-RELEASE response primitive (from local user)',
    'Sta9': 'Release collision requestor side; awaiting A-RELEASE response '
            ' (from local user)',
    'Sta10': 'Release collision acceptor side; awaiting A-RELEASE-RP PDU',
    'Sta11': 'Release collision requestor side; awaiting A-RELEASE-RP PDU',
    'Sta12': 'Release collision acceptor side; awaiting A-RELEASE response '
             'primitive (from local user)',
    'Sta13': 'Awaiting Transport Connection Close Indication (Association no '
             'longer exists)'
}

# events
events = {
    'Evt1': "A-ASSOCIATE request (local user)",
    'Evt2': "Transport connect confirmation (local transport service)",
    'Evt3': "A-ASSOCIATE-AC PDU (received on transport connection)",
    'Evt4': "A-ASSOCIATE-RJ PDU (received on transport connection)",
    'Evt5': "Transport connection indication (local transport service)",
    'Evt6': "A-ASSOCIATE-RQ PDU (on tranport connection)",
    'Evt7': "A-ASSOCIATE response primitive (accept)",
    'Evt8': "A-ASSOCIATE response primitive (reject)",
    'Evt9': "P-DATA request primitive",
    'Evt10': "P-DATA-TF PDU (on transport connection)",
    'Evt11': "A-RELEASE request primitive",
    'Evt12': "A-RELEASE-RQ PDU (on transport)",
    'Evt13': "A-RELEASE-RP PDU (on transport)",
    'Evt14': "A-RELEASE response primitive",
    'Evt15': "A-ABORT request primitive",
    'Evt16': "A-ABORT PDU (on transport)",
    'Evt17': "Transport connection closed",
    'Evt18': "ARTIM timer expired (rej/rel)",
    'Evt19': "Unrecognized/invalid PDU"}

TransitionTable = {
    ('Evt1', 'Sta1'): ae_1,

    ('Evt2', 'Sta4'): ae_2,

    ('Evt3', 'Sta2'): aa_1,
    ('Evt3', 'Sta3'): aa_8,
    ('Evt3', 'Sta5'): ae_3,
    ('Evt3', 'Sta6'): aa_8,
    ('Evt3', 'Sta7'): aa_8,
    ('Evt3', 'Sta8'): aa_8,
    ('Evt3', 'Sta9'): aa_8,
    ('Evt3', 'Sta10'): aa_8,
    ('Evt3', 'Sta11'): aa_8,
    ('Evt3', 'Sta12'): aa_8,
    ('Evt3', 'Sta13'): aa_6,

    ('Evt4', 'Sta2'): aa_1,
    ('Evt4', 'Sta3'): aa_8,
    ('Evt4', 'Sta5'): ae_4,
    ('Evt4', 'Sta6'): aa_8,
    ('Evt4', 'Sta7'): aa_8,
    ('Evt4', 'Sta8'): aa_8,
    ('Evt4', 'Sta9'): aa_8,
    ('Evt4', 'Sta10'): aa_8,
    ('Evt4', 'Sta11'): aa_8,
    ('Evt4', 'Sta12'): aa_8,
    ('Evt4', 'Sta13'): aa_6,

    ('Evt5', 'Sta1'): ae_5,

    ('Evt6', 'Sta2'): ae_6,
    ('Evt6', 'Sta3'): aa_8,
    ('Evt6', 'Sta5'): aa_8,
    ('Evt6', 'Sta6'): aa_8,
    ('Evt6', 'Sta7'): aa_8,
    ('Evt6', 'Sta8'): aa_8,
    ('Evt6', 'Sta9'): aa_8,
    ('Evt6', 'Sta10'): aa_8,
    ('Evt6', 'Sta11'): aa_8,
    ('Evt6', 'Sta12'): aa_8,
    ('Evt6', 'Sta13'): aa_7,

    ('Evt7', 'Sta3'): ae_7,

    ('Evt8', 'Sta3'): ae_8,

    ('Evt9', 'Sta6'): dt_1,
    ('Evt9', 'Sta8'): ar_7,

    ('Evt10', 'Sta2'): aa_1,
    ('Evt10', 'Sta3'): aa_8,
    ('Evt10', 'Sta5'): aa_8,
    ('Evt10', 'Sta6'): dt_2,
    ('Evt10', 'Sta7'): ar_6,
    ('Evt10', 'Sta8'): aa_8,
    ('Evt10', 'Sta9'): aa_8,
    ('Evt10', 'Sta10'): aa_8,
    ('Evt10', 'Sta11'): aa_8,
    ('Evt10', 'Sta12'): aa_8,
    ('Evt10', 'Sta13'): aa_6,

    ('Evt11', 'Sta6'): ar_1,

    ('Evt12', 'Sta2'): aa_1,
    ('Evt12', 'Sta3'): aa_8,
    ('Evt12', 'Sta5'): aa_8,
    ('Evt12', 'Sta6'): ar_2,
    ('Evt12', 'Sta7'): ar_8,
    ('Evt12', 'Sta8'): aa_8,
    ('Evt12', 'Sta9'): aa_8,
    ('Evt12', 'Sta10'): aa_8,
    ('Evt12', 'Sta11'): aa_8,
    ('Evt12', 'Sta12'): aa_8,
    ('Evt12', 'Sta13'): aa_6,

    ('Evt13', 'Sta2'): aa_1,
    ('Evt13', 'Sta3'): aa_8,
    ('Evt13', 'Sta5'): aa_8,
    ('Evt13', 'Sta6'): aa_8,
    ('Evt13', 'Sta7'): ar_3,
    ('Evt13', 'Sta8'): aa_8,
    ('Evt13', 'Sta9'): aa_8,
    ('Evt13', 'Sta10'): ar_10,
    ('Evt13', 'Sta11'): ar_3,
    ('Evt13', 'Sta12'): aa_8,
    ('Evt13', 'Sta13'): aa_6,

    ('Evt14', 'Sta8'): ar_4,
    ('Evt14', 'Sta9'): ar_9,
    ('Evt14', 'Sta12'): ar_4,

    ('Evt15', 'Sta3'): aa_1,
    ('Evt15', 'Sta4'): aa_2,
    ('Evt15', 'Sta5'): aa_1,
    ('Evt15', 'Sta6'): aa_1,
    ('Evt15', 'Sta7'): aa_1,
    ('Evt15', 'Sta8'): aa_1,
    ('Evt15', 'Sta9'): aa_1,
    ('Evt15', 'Sta10'): aa_1,
    ('Evt15', 'Sta11'): aa_1,
    ('Evt15', 'Sta12'): aa_1,

    ('Evt16', 'Sta2'): aa_2,
    ('Evt16', 'Sta3'): aa_3,
    ('Evt16', 'Sta5'): aa_3,
    ('Evt16', 'Sta6'): aa_3,
    ('Evt16', 'Sta7'): aa_3,
    ('Evt16', 'Sta8'): aa_3,
    ('Evt16', 'Sta9'): aa_3,
    ('Evt16', 'Sta10'): aa_3,
    ('Evt16', 'Sta11'): aa_3,
    ('Evt16', 'Sta12'): aa_3,
    ('Evt16', 'Sta13'): aa_2,

    ('Evt17', 'Sta2'): aa_5,
    ('Evt17', 'Sta3'): aa_4,
    ('Evt17', 'Sta4'): aa_4,
    ('Evt17', 'Sta5'): aa_4,
    ('Evt17', 'Sta6'): aa_4,
    ('Evt17', 'Sta7'): aa_4,
    ('Evt17', 'Sta8'): aa_4,
    ('Evt17', 'Sta9'): aa_4,
    ('Evt17', 'Sta10'): aa_4,
    ('Evt17', 'Sta11'): aa_4,
    ('Evt17', 'Sta12'): aa_4,
    ('Evt17', 'Sta13'): ar_5,

    ('Evt18', 'Sta2'): aa_2,
    ('Evt18', 'Sta13'): aa_2,

    ('Evt19', 'Sta2'): aa_1,
    ('Evt19', 'Sta3'): aa_8,
    ('Evt19', 'Sta5'): aa_8,
    ('Evt19', 'Sta6'): aa_8,
    ('Evt19', 'Sta7'): aa_8,
    ('Evt19', 'Sta8'): aa_8,
    ('Evt19', 'Sta9'): aa_8,
    ('Evt19', 'Sta10'): aa_8,
    ('Evt19', 'Sta11'): aa_8,
    ('Evt19', 'Sta12'): aa_8,
    ('Evt19', 'Sta13'): aa_7}


class StateMachine(object):
    def __init__(self, provider):
        self.current_state = 'Sta1'
        self.provider = provider

    def action(self, event, provider):
        """ Execute the action triggered by event """
        action = TransitionTable[(event, self.current_state)]
        self.current_state = action(provider)
