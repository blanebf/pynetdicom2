# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com

import threading
import socket
import sys
import select
import platform
import gc
import time
import contextlib

from dicom.UID import ExplicitVRLittleEndian, ImplicitVRLittleEndian, \
    ExplicitVRBigEndian, UID

import netdicom2.sopclass as sopclass
import netdicom2.asceprovider as asceprovider


class AE(threading.Thread):
    """Represents a DICOM application entity

    Instance if this class represent an application entity. Once
    instantiated, it starts a new thread and enters an event loop,
    where events are association requests from remote AEs. Events
    trigger callback functions that perform user defined actions based
    on received events.
    """

    def __init__(self, ae_title, port, sop_scu, sop_scp,
                 supported_transfer_syntax=None, max_pdu_length=16000):
        if supported_transfer_syntax is None:
            supported_transfer_syntax = [ExplicitVRLittleEndian,
                                         ImplicitVRLittleEndian,
                                         ExplicitVRBigEndian]
        self.local_ae = {'address': platform.node(), 'port': port,
                         'aet': ae_title}
        self.supported_sop_classes_as_scu = sop_scu
        self.supported_sop_classes_as_scp = sop_scp
        self.supported_transfer_syntax = supported_transfer_syntax
        self.max_number_of_associations = 25
        threading.Thread.__init__(self, name=self.local_ae['aet'])

        self.local_server_socket = socket.socket(socket.AF_INET,
                                                 socket.SOCK_STREAM)
        self.local_server_socket.setsockopt(socket.SOL_SOCKET,
                                            socket.SO_REUSEADDR, 1)
        self.local_server_socket.bind(('', port))
        self.local_server_socket.listen(1)
        self.max_pdu_length = max_pdu_length

        # build presentation context definition list to be sent to remote
        # AE when requesting association.
        count = 1
        self.presentation_context_definition_list = []
        for sop_class in self.supported_sop_classes_as_scu + self.supported_sop_classes_as_scp:
            self.presentation_context_definition_list.append(
                [count, UID(sop_class),
                 [x for x in self.supported_transfer_syntax]])
            count += 2

        # build acceptable context definition list used to decide whether an
        # association from a remote AE will be accepted or not.
        # This is based on the supported_sop_classes_as_scp and
        # supported_transfer_syntax values set for this AE.
        self.acceptable_presentation_contexts = [
            [sop_class, [x for x in self.supported_transfer_syntax]]
            for sop_class in self.supported_sop_classes_as_scp]

        # used to terminate AE
        self._quit = False

        # list of active association objects
        self.associations = []

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    def run(self):
        if not self.supported_sop_classes_as_scp:
            # no need to loop. This is just a client AE.
            # All events will be triggered by the user
            return
        count = 0
        while not self._quit:
            # main loop
            time.sleep(0.1)
            a, _, _ = select.select([self.local_server_socket], [], [], 0)
            if a:
                # got an incoming connection
                client_socket, remote_address = self.local_server_socket.accept()
                # create a new association
                self.associations.append(
                    asceprovider.AssociationAcceptor(self, client_socket)
                )

            # delete dead associations
            # TODO Fix removing dead  associations
            for association in self.associations:
                if hasattr(association, 'isAlive') and \
                        not association.isAlive():
                    self.associations.remove(association)
            if not count % 50:
                gc.collect()
            count += 1
            if count > 1e6:
                count = 0

    def quit(self):
        for aa in self.associations:
            aa.kill()
        self._quit = True

    def quit_on_keyboard_interrupt(self):
        # must be called from the main thread in order to catch the
        # KeyboardInterrupt exception
        while 1:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.quit()
                sys.exit(0)
            except IOError:
                # Catch this exception otherwise when we run an app,
                # using this module as a service this exception is raised
                # when we logoff.
                continue

    @contextlib.contextmanager
    def request_association(self, remote_ae):
        """Requests association to a remote application entity"""
        assoc = asceprovider.AssociationRequester(self, remote_ae=remote_ae)
        self.associations.append(assoc)
        yield assoc
        if assoc.association_established:
            assoc.release()
        else:
            assoc.kill()

    def on_association_request(self, assoc):
        """Extra processing of the association request.

        Default implementation of the method does nothing and thus accepts all
        incoming association requests.
        If association should be rejected user should override this method
        in a sub-class and raise `AssociationRejectedError` when appropriate

        :param assoc: association request parameters
        """
        pass

    def on_association_response(self, response):
        pass

    def on_receive_echo(self, service):
        """Default handling of C-ECHO command. Always returns SUCCESS code

        User should override this method in sub-class to provide custom
        handling of the command.

        :param service: service instance that received C-ECHO
        :return: status that should be sent in response
        """
        return sopclass.SUCCESS

    def on_receive_store(self, service, ds):
        pass

    def on_receive_find(self, service, ds):
        pass

    def on_receive_move(self, service, ds, destination):
        pass
