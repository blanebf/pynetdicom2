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

import socket

import netdicom2.pdu as pdu

# Finite State machine action definitions


def ae_1(provider):
    """Issue TransportConnect request primitive to local transport service."""
    provider.dul_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    provider.dul_socket.connect(provider.primitive.called_presentation_address)


def ae_2(provider):
    """Send A_ASSOCIATE-RQ PDU."""
    provider.dul_socket.send(provider.primitive.encode())


def ae_3(provider):
    """Issue A-ASSOCIATE confirmation (accept) primitive."""
    provider.to_service_user.put(provider.primitive)


def ae_4(provider):
    """Issue A-ASSOCIATE confirmation (reject) primitive and close transport
    connection.
    """
    provider.to_service_user.put(provider.primitive)
    provider.dul_socket.close()
    provider.dul_socket = None


def ae_5(provider):
    """Issue transport connection response primitive; start ARTIM timer."""
    # Don't need to send this primitive.
    provider.timer.start()


def ae_6(provider):
    """Check A-ASSOCIATE-RQ.

    Stop ARTIM timer and if A-ASSOCIATE-RQ acceptable by service provider
    - Issue A-ASSOCIATE indication primitive
    """
    provider.timer.stop()
    # Accept
    provider.to_service_user.put(provider.primitive)
    provider.state_machine.next_state('Sta3')


def ae_7(provider):
    """Send A-ASSOCIATE-AC PDU."""
    provider.dul_socket.send(provider.primitive.encode())


def ae_8(provider):
    """Send A-ASSOCIATE-RJ PDU."""
    # not sure about this ...
    provider.dul_socket.send(provider.primitive.encode())


def dt_1(provider):
    """Send P-DATA-TF PDU."""
    provider.dul_socket.send(provider.primitive.encode())
    provider.primitive = None


def dt_2(provider):
    """Send P-DATA indication primitive."""
    provider.to_service_user.put(provider.primitive)


def ar_1(provider):
    """Send A-RELEASE-RQ PDU."""
    provider.primitive = pdu.AReleaseRqPDU()
    provider.dul_socket.send(provider.primitive.encode())


def ar_2(provider):
    """Send A-RELEASE indication primitive."""
    provider.to_service_user.put(provider.primitive)


def ar_3(provider):
    """Issue A-RELEASE confirmation primitive and close transport connection."""
    provider.to_service_user.put(provider.primitive)
    provider.dul_socket.close()
    provider.dul_socket = None


def ar_4(provider):
    """Issue A-RELEASE-RP PDU and start ARTIM timer."""
    provider.primitive = pdu.AReleaseRpPDU()
    provider.dul_socket.send(provider.primitive.encode())
    provider.timer.start()


def ar_5(provider):
    """Stop ARTIM timer."""
    provider.timer.stop()


def ar_6(provider):
    """Issue P-DATA indication."""
    provider.to_service_user.put(provider.primitive)


def ar_7(provider):
    """Issue P-DATA-TF PDU."""
    provider.dul_socket.send(provider.primitive.encode())


def ar_8(provider):
    """Issue A-RELEASE indication (release collision)."""
    provider.to_service_user.put(provider.primitive)
    if provider.requestor == 1:
        provider.state_machine.next_state('Sta9')
    else:
        provider.state_machine.next_state('Sta10')


def ar_9(provider):
    """Send A-RELEASE-RP PDU."""
    provider.primitive = pdu.AReleaseRpPDU()
    provider.dul_socket.send(provider.primitive.encode())


def ar_10(provider):
    """Issue A-RELEASE confirmation primitive."""
    provider.to_service_user.put(provider.primitive)


def aa_1(provider):
    """Send A-ABORT PDU (service-user source) and start (or restart)
    ARTIM timer.
    """
    provider.dul_socket.send(provider.primitive.encode())
    provider.timer.restart()


def aa_2(provider):
    """Stop ARTIM timer if running. Close transport connection."""
    provider.timer.stop()
    provider.dul_socket.close()
    provider.dul_socket = None


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


def aa_4(provider):
    """Issue A-P-ABORT indication primitive."""
    # TODO look into this action
    provider.primitive = pdu.AAbortPDU(source=0, reason_diag=0)
    provider.to_service_user.put(provider.primitive)


def aa_5(provider):
    """Stop ARTIM timer."""
    provider.timer.stop()


def aa_6(provider):
    """Ignore PDU."""
    provider.primitive = None


def aa_7(provider):
    """Send A-ABORT PDU."""
    provider.dul_socket.send(provider.primitive.encode())


def aa_8(provider):
    """Send A-ABORT PDU, issue an A-P-ABORT indication and start ARTIM timer."""
    provider.primitive = pdu.AAbortPDU(source=2, reason_diag=0)
    if provider.dul_socket:
        provider.dul_socket.send(provider.primitive.encode())

        # Issue A-P-ABORT indication
        provider.to_service_user.put(provider.primitive)
        provider.timer.start()


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


# actions
actions = {
    # Association establishment actions
    'AE-1': (ae_1, 'Sta4'),
    'AE-2': (ae_2, 'Sta5'),
    'AE-3': (ae_3, 'Sta6'),
    'AE-4': (ae_4, 'Sta1'),
    'AE-5': (ae_5, 'Sta2'),
    'AE-6': (ae_6, ('Sta3', 'Sta13')),
    'AE-7': (ae_7, 'Sta6'),
    'AE-8': (ae_8, 'Sta13'),

    # Data transfer related actions
    'DT-1': (dt_1, 'Sta6'),
    'DT-2': (dt_2, 'Sta6'),

    # Assocation Release related actions
    'AR-1': (ar_1, 'Sta7'),
    'AR-2': (ar_2, 'Sta8'),
    'AR-3': (ar_3, 'Sta1'),
    'AR-4': (ar_4, 'Sta13'),
    'AR-5': (ar_5, 'Sta1'),
    'AR-6': (ar_6, 'Sta7'),
    'AR-7': (ar_7, 'Sta8'),
    'AR-8': (ar_8, ('Sta9', 'Sta10')),
    'AR-9': (ar_9, 'Sta11'),
    'AR-10': (ar_10, 'Sta12'),

    # Association abort related actions
    'AA-1': (aa_1, 'Sta13'),
    'AA-2': (aa_2, 'Sta1'),
    'AA-3': (aa_3, 'Sta1'),
    'AA-4': (aa_4, 'Sta1'),
    'AA-5': (aa_5, 'Sta1'),
    'AA-6': (aa_6, 'Sta13'),
    'AA-7': (aa_6, 'Sta13'),
    'AA-8': (aa_8, 'Sta13')}


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

    ('Evt1', 'Sta1'): 'AE-1',

    ('Evt2', 'Sta4'): 'AE-2',

    ('Evt3', 'Sta2'): 'AA-1',
    ('Evt3', 'Sta3'): 'AA-8',
    ('Evt3', 'Sta5'): 'AE-3',
    ('Evt3', 'Sta6'): 'AA-8',
    ('Evt3', 'Sta7'): 'AA-8',
    ('Evt3', 'Sta8'): 'AA-8',
    ('Evt3', 'Sta9'): 'AA-8',
    ('Evt3', 'Sta10'): 'AA-8',
    ('Evt3', 'Sta11'): 'AA-8',
    ('Evt3', 'Sta12'): 'AA-8',
    ('Evt3', 'Sta13'): 'AA-6',

    ('Evt4', 'Sta2'): 'AA-1',
    ('Evt4', 'Sta3'): 'AA-8',
    ('Evt4', 'Sta5'): 'AE-4',
    ('Evt4', 'Sta6'): 'AA-8',
    ('Evt4', 'Sta7'): 'AA-8',
    ('Evt4', 'Sta8'): 'AA-8',
    ('Evt4', 'Sta9'): 'AA-8',
    ('Evt4', 'Sta10'): 'AA-8',
    ('Evt4', 'Sta11'): 'AA-8',
    ('Evt4', 'Sta12'): 'AA-8',
    ('Evt4', 'Sta13'): 'AA-6',

    ('Evt5', 'Sta1'): 'AE-5',

    ('Evt6', 'Sta2'): 'AE-6',
    ('Evt6', 'Sta3'): 'AA-8',
    ('Evt6', 'Sta5'): 'AA-8',
    ('Evt6', 'Sta6'): 'AA-8',
    ('Evt6', 'Sta7'): 'AA-8',
    ('Evt6', 'Sta8'): 'AA-8',
    ('Evt6', 'Sta9'): 'AA-8',
    ('Evt6', 'Sta10'): 'AA-8',
    ('Evt6', 'Sta11'): 'AA-8',
    ('Evt6', 'Sta12'): 'AA-8',
    ('Evt6', 'Sta13'): 'AA-7',

    ('Evt7', 'Sta3'): 'AE-7',

    ('Evt8', 'Sta3'): 'AE-8',

    ('Evt9', 'Sta6'): 'DT-1',
    ('Evt9', 'Sta8'): 'AR-7',

    ('Evt10', 'Sta2'): 'AA-1',
    ('Evt10', 'Sta3'): 'AA-8',
    ('Evt10', 'Sta5'): 'AA-8',
    ('Evt10', 'Sta6'): 'DT-2',
    ('Evt10', 'Sta7'): 'AR-6',
    ('Evt10', 'Sta8'): 'AA-8',
    ('Evt10', 'Sta9'): 'AA-8',
    ('Evt10', 'Sta10'): 'AA-8',
    ('Evt10', 'Sta11'): 'AA-8',
    ('Evt10', 'Sta12'): 'AA-8',
    ('Evt10', 'Sta13'): 'AA-6',

    ('Evt11', 'Sta6'): 'AR-1',

    ('Evt12', 'Sta2'): 'AA-1',
    ('Evt12', 'Sta3'): 'AA-8',
    ('Evt12', 'Sta5'): 'AA-8',
    ('Evt12', 'Sta6'): 'AR-2',
    ('Evt12', 'Sta7'): 'AR-8',
    ('Evt12', 'Sta8'): 'AA-8',
    ('Evt12', 'Sta9'): 'AA-8',
    ('Evt12', 'Sta10'): 'AA-8',
    ('Evt12', 'Sta11'): 'AA-8',
    ('Evt12', 'Sta12'): 'AA-8',
    ('Evt12', 'Sta13'): 'AA-6',

    ('Evt13', 'Sta2'): 'AA-1',
    ('Evt13', 'Sta3'): 'AA-8',
    ('Evt13', 'Sta5'): 'AA-8',
    ('Evt13', 'Sta6'): 'AA-8',
    ('Evt13', 'Sta7'): 'AR-3',
    ('Evt13', 'Sta8'): 'AA-8',
    ('Evt13', 'Sta9'): 'AA-8',
    ('Evt13', 'Sta10'): 'AR-10',
    ('Evt13', 'Sta11'): 'AR-3',
    ('Evt13', 'Sta12'): 'AA-8',
    ('Evt13', 'Sta13'): 'AA-6',

    ('Evt14', 'Sta8'): 'AR-4',
    ('Evt14', 'Sta9'): 'AR-9',
    ('Evt14', 'Sta12'): 'AR-4',

    ('Evt15', 'Sta3'): 'AA-1',
    ('Evt15', 'Sta4'): 'AA-2',
    ('Evt15', 'Sta5'): 'AA-1',
    ('Evt15', 'Sta6'): 'AA-1',
    ('Evt15', 'Sta7'): 'AA-1',
    ('Evt15', 'Sta8'): 'AA-1',
    ('Evt15', 'Sta9'): 'AA-1',
    ('Evt15', 'Sta10'): 'AA-1',
    ('Evt15', 'Sta11'): 'AA-1',
    ('Evt15', 'Sta12'): 'AA-1',

    ('Evt16', 'Sta2'): 'AA-2',
    ('Evt16', 'Sta3'): 'AA-3',
    ('Evt16', 'Sta5'): 'AA-3',
    ('Evt16', 'Sta6'): 'AA-3',
    ('Evt16', 'Sta7'): 'AA-3',
    ('Evt16', 'Sta8'): 'AA-3',
    ('Evt16', 'Sta9'): 'AA-3',
    ('Evt16', 'Sta10'): 'AA-3',
    ('Evt16', 'Sta11'): 'AA-3',
    ('Evt16', 'Sta12'): 'AA-3',
    ('Evt16', 'Sta13'): 'AA-2',

    ('Evt17', 'Sta2'): 'AA-5',
    ('Evt17', 'Sta3'): 'AA-4',
    ('Evt17', 'Sta4'): 'AA-4',
    ('Evt17', 'Sta5'): 'AA-4',
    ('Evt17', 'Sta6'): 'AA-4',
    ('Evt17', 'Sta7'): 'AA-4',
    ('Evt17', 'Sta8'): 'AA-4',
    ('Evt17', 'Sta9'): 'AA-4',
    ('Evt17', 'Sta10'): 'AA-4',
    ('Evt17', 'Sta11'): 'AA-4',
    ('Evt17', 'Sta12'): 'AA-4',
    ('Evt17', 'Sta13'): 'AR-5',

    ('Evt18', 'Sta2'): 'AA-2',
    ('Evt18', 'Sta13'): 'AA-2',

    ('Evt19', 'Sta2'): 'AA-1',
    ('Evt19', 'Sta3'): 'AA-8',
    ('Evt19', 'Sta5'): 'AA-8',
    ('Evt19', 'Sta6'): 'AA-8',
    ('Evt19', 'Sta7'): 'AA-8',
    ('Evt19', 'Sta8'): 'AA-8',
    ('Evt19', 'Sta9'): 'AA-8',
    ('Evt19', 'Sta10'): 'AA-8',
    ('Evt19', 'Sta11'): 'AA-8',
    ('Evt19', 'Sta12'): 'AA-8',
    ('Evt19', 'Sta13'): 'AA-7'}


class StateMachine(object):
    def __init__(self, provider):
        self.current_state = 'Sta1'
        self.provider = provider

    def action(self, event, provider):
        """ Execute the action triggered by event """
        action_name = TransitionTable[(event, self.current_state)]
        action, state = actions[action_name]
        action(provider)

        if not isinstance(state, tuple):
            # only one next state possible
            self.current_state = state

    def next_state(self, state):
        self.current_state = state
