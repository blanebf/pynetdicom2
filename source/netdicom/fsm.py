#
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

import PDU
import DULparameters

# Finite State machine action definitions

import logging
logger = logging.getLogger(__name__)


def ae_1(provider):
    # Issue TRANSPORT CONNECT request primitive to local transport service
    provider.remote_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    provider.remote_client_socket.connect(provider.primitive.called_presentation_address)


def ae_2(provider):
    # Send A-ASSOCIATE-RQ PDU
    provider.pdu = PDU.AAssociateRqPDU()
    provider.pdu.from_params(provider.primitive)
    provider.remote_client_socket.send(provider.pdu.encode())


def ae_3(provider):
    # Issue A-ASSOCIATE confirmation (accept) primitive
    provider.ToServiceUser.put(provider.primitive)


def ae_4(provider):
    # Issue A-ASSOCIATE confirmation (reject) primitive and close transport connection
    provider.to_service_user.put(provider.primitive)
    provider.remote_client_socket.close()
    provider.remote_client_socket = None


def ae_5(provider):
    # Issue connection response primitive start ARTIM timer
    # Don't need to send this primitive.
    provider.timer.start()


def ae_6(provider):
    # Stop ARTIM timer and if A-ASSOCIATE-RQ acceptable by service provider
    # - Issue A-ASSOCIATE indication primitive
    provider.timer.stop()
    # Accept
    provider.state_machine.next_state('Sta3')
    provider.ToServiceUser.put(provider.primitive)
    # otherwise????


def ae_7(provider):
    # Send A-ASSOCIATE-AC PDU
    provider.pdu = PDU.AAssociateAcPDU()
    provider.pdu.from_params(provider.primitive)
    provider.remote_client_socket.send(provider.pdu.encode())


def ae_8(provider):
    # Send A-ASSOCIATE-RJ PDU and start ARTIM timer
    provider.pdu = PDU.AAssociateRjPDU()
    # not sure about this ...
    if provider.primitive.diagnostic is not None:
        provider.primitive.result_source = 1
    else:
        provider.primitive.diagnostic = 1
        provider.primitive.result_source = 2

    provider.pdu.from_params(provider.primitive)
    provider.remote_client_socket.send(provider.pdu.encode())


def dt_1(provider):
    # Send P-DATA-TF PDU
    provider.pdu = PDU.PDataTfPDU()
    provider.pdu.from_params(provider.primitive)
    provider.primitive = None
    provider.remote_client_socket.send(provider.pdu.encode())


def dt_2(provider):
    # Send P-DATA indication primitive
    provider.ToServiceUser.put(provider.primitive)


def ar_1(provider):
    # Send A-RELEASE-RQ PDU
    provider.pdu = PDU.AReleaseRqPDU()
    provider.pdu.from_params(provider.primitive)
    provider.remote_client_socket.send(provider.pdu.encode())


def ar_2(provider):
    # Send A-RELEASE indication primitive
    provider.ToServiceUser.put(provider.primitive)


def ar_3(provider):
    # Issue A-RELEASE confirmation primitive and close transport connection
    provider.ToServiceUser.put(provider.primitive)
    provider.remote_client_socket.close()
    provider.remote_client_socket = None


def ar_4(provider):
    # Issue A-RELEASE-RP PDU and start ARTIM timer
    provider.pdu = PDU.AReleaseRpPDU()
    provider.pdu.from_params(provider.primitive)
    provider.remote_client_socket.send(provider.pdu.encode())
    provider.timer.start()


def ar_5(provider):
    # Stop ARTIM timer
    provider.timer.stop()


def ar_6(provider):
    # Issue P-DATA indication
    provider.ToServiceUser.put(provider.primitive)


def ar_7(provider):
    # Issue P-DATA-TF PDU
    provider.pdu = PDU.PDataTfPDU()
    provider.pdu.from_params(provider.primitive)
    provider.remote_client_socket.send(provider.pdu.encode())


def ar_8(provider):
    # Issue A-RELEASE indication (release collision)
    provider.ToServiceUser.put(provider.primitive)
    if provider.requestor == 1:
        provider.state_machine.next_state('Sta9')
    else:
        provider.state_machine.next_state('Sta10')


def ar_9(provider):
    # Send A-RELEASE-RP PDU
    provider.pdu = PDU.AReleaseRpPDU()
    provider.pdu.from_params(provider.primitive)
    provider.remote_client_socket.send(provider.pdu.encode())


def ar_10(provider):
    # Issue A-RELEASE confirmation primitive
    provider.ToServiceUser.put(provider.primitive)


def aa_1(provider):
    # Send A-ABORT PDU (service-user source) and start (or restart
    # if already started) ARTIM timer.
    provider.pdu = PDU.AAbortPDU()
    # CHECK THIS ...
    provider.pdu.abort_source = 1
    provider.pdu.reason_diag = 0
    provider.pdu.from_params(provider.primitive)
    provider.remote_client_socket.send(provider.pdu.encode())
    provider.timer.restart()


def aa_2(provider):
    # Stop ARTIM timer if running. Close transport connection.
    provider.timer.stop()
    provider.remote_client_socket.close()
    provider.remote_client_socket = None


def aa_3(provider):
    # If (service-user initiated abort):
    #   - Issue A-ABORT indication and close transport connection.
    # Otherwise (service-provider initiated abort):
    #   - Issue A-P-ABORT indication and close transport connection.
    # This action is triggered by the reception of an A-ABORT PDU
    provider.ToServiceUser.put(provider.primitive)
    provider.remote_client_socket.close()
    provider.remote_client_socket = None


def aa_4(provider):
    # Issue A-P-ABORT indication primitive.
    provider.primitive = DULparameters.AAbortServiceParameters()
    provider.ToServiceUser.put(provider.primitive)


def aa_5(provider):
    # Stop ARTIM timer.
    provider.timer.stop()


def aa_6(provider):
    # Ignore PDU.
    provider.primitive = None


def aa_7(provider):
    # Send A-ABORT PDU.
    provider.pdu = PDU.AAbortPDU()
    provider.pdu.from_params(provider.primitive)
    provider.remote_client_socket.send(provider.pdu.encode())


def aa_8(provider):
    # Send A-ABORT PDU (service-provider source), issue and A-P-ABORT
    # indication, and start ARTIM timer.
    # Send A-ABORT PDU
    provider.pdu = PDU.AAbortPDU()
    provider.pdu.source = 2
    provider.pdu.reason_diag = 0  # No reason given
    if provider.remote_client_socket:
        provider.remote_client_socket.send(provider.pdu.encode())
        # Issue A-P-ABORT indication
        provider.ToServiceUser.put(provider.primitive)
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
    'AE-1': ('Issue TransportConnect request primitive to local transport '
             'service', ae_1, 'Sta4'),
    'AE-2': ('Send A_ASSOCIATE-RQ PDU', ae_2, 'Sta5'),
    'AE-3': ('Issue A-ASSOCIATE confirmation (accept) primitive', ae_3,
             'Sta6'),
    'AE-4': ('Issue A-ASSOCIATE confirmation (reject) primitive and close '
             'transport connection', ae_4, 'Sta1'),
    'AE-5': ('Issue transport connection response primitive; start ARTIM '
             'timer', ae_5, 'Sta2'),
    'AE-6': ('Check A-ASSOCIATE-RQ', ae_6, ('Sta3', 'Sta13')),
    'AE-7': ('Send A-ASSOCIATE-AC PDU', ae_7, 'Sta6'),
    'AE-8': ('Send A-ASSOCIATE-RJ PDU', ae_8, 'Sta13'),
    # Data transfer related actions
    'DT-1': ('Send P-DATA-TF PDU', dt_1, 'Sta6'),
    'DT-2': ('Send P-DATA indication primitive', dt_2, 'Sta6'),
    # Assocation Release related actions
    'AR-1': ('Send A-RELEASE-RQ PDU', ar_1, 'Sta7'),
    'AR-2': ('Send A-RELEASE indication primitive', ar_2, 'Sta8'),
    'AR-3': ('Issue A-RELEASE confirmation primitive and close transport '
             'connection', ar_3, 'Sta1'),
    'AR-4': ('Issue A-RELEASE-RP PDU and start ARTIM timer', ar_4, 'Sta13'),
    'AR-5': ('Stop ARTIM timer', ar_5, 'Sta1'),
    'AR-6': ('Issue P-DATA indication', ar_6, 'Sta7'),
    'AR-7': ('Issue P-DATA-TF PDU', ar_7, 'Sta8'),
    'AR-8': ('Issue A-RELEASE indication (release collision)', ar_8,
             ('Sta9', 'Sta10')),
    'AR-9': ('Send A-RELEASE-RP PDU', ar_9, 'Sta11'),
    'AR-10': ('Issue A-RELEASE confimation primitive', ar_10, 'Sta12'),
    # Association abort related actions
    'AA-1': ('Send A-ABORT PDU (service-user source) and start (or restart) '
             'ARTIM timer', aa_1, 'Sta13'),
    'AA-2': ('Stop ARTIM timer if running. Close transport connection', aa_2,
             'Sta1'),
    'AA-3': ('Issue A-ABORT or A-P-ABORT indication and close transport '
             'connection', aa_3, 'Sta1'),
    'AA-4': ('Issue A-P-ABORT indication primitive', aa_4, 'Sta1'),
    'AA-5': ('Stop ARTIM timer', aa_5, 'Sta1'),
    'AA-6': ('Ignore PDU', aa_6, 'Sta13'),
    'AA-7': ('Send A-ABORT PDU', aa_6, 'Sta13'),
    'AA-8': ('Send A-ABORT PDU, issue an A-P-ABORT indication and start '
             'ARTIM timer', aa_8, 'Sta13')}


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


class StateMachine:

    def __init__(self, provider):
        self.current_state = 'Sta1'
        self.provider = provider

    def action(self, event, c):
        """ Execute the action triggered by event """
        try:
            action_name = TransitionTable[(event, self.current_state)]
        except KeyError:
            logger.debug('%s: current state is: %s %s' %
                         (self.provider.name, self.current_state, states[self.current_state]))
            logger.debug('%s: event: %s %s' % (self.provider.name, event, events[event]))
            raise

        action = actions[action_name]
        try:
            logger.debug('')
            logger.debug('%s: current state is: %s %s' %
                         (self.provider.name, self.current_state, states[self.current_state]))
            logger.debug('%s: event: %s %s' % (self.provider.name, event, events[event]))
            logger.debug('%s: entering action: (%s, %s) %s %s' %
                         (self.provider.name, event, self.current_state, action_name, actions[action_name][0]))
            action[1](c)
            #if type(action[2]) != type(()):
            if not isinstance(action[2], tuple):
                # only one next state possible
                self.current_state = action[2]
            logger.debug('%s: action complete. State is now %s %s' %
                         (self.provider.name, self.current_state, states[self.current_state]))
        finally:
            self.provider.kill()

    def next_state(self, state):
        self.current_state = state
