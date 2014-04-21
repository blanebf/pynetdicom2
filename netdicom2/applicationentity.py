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
import netdicom2.exceptions as exceptions
import netdicom2.dulprovider as dulprovider
import netdicom2.dimseprovider as dimseprovider
import netdicom2.asceprovider as asceprovider
import netdicom2.userdataitems as userdataitems


class Association(object):
    """Base association class.

    Class is not intended for direct usage and meant to be sub-classed.
    Class provides basic association interface: creation, release and abort.
    """

    def __init__(self, local_ae, dul_socket):
        """Initializes Association instance with local AE title and DUL service
        provider

        :param local_ae: local AE title parameters
        :param dul_socket: socket for DUL provider or None if it's not needed
        """
        super(Association, self).__init__()
        self.dul = dulprovider.DULServiceProvider(dul_socket)
        self.ae = local_ae
        self.association_established = False
        self.asce = asceprovider.ACSEServiceProvider(self.dul)
        self.dimse = dimseprovider.DIMSEServiceProvider(self.dul)

    def kill(self):
        """Stops internal DUL service provider.

        In most cases you won't need to use this method directly. Refer to
        release and abort instead.
        :rtype : None
        """
        for _ in xrange(1000):
            if self.dul.stop():
                continue
            time.sleep(0.001)
        self.dul.kill()

    def release(self, reason):
        """Releases association with specified reason.

        :rtype : None
        :param reason: release reason
        """
        self.asce.release(reason)
        self.kill()

    def abort(self, reason):
        """Aborts association with specified reason

        :rtype : None
        :param reason: abort reason
        """
        # self.asce.abort(reason) TODO: Look into passing abort reason
        self.asce.abort()
        self.kill()


class AssociationAcceptor(threading.Thread, Association):
    """'Server-side' association implementation.

    Class is intended for handling incoming association requests.
    """

    def __init__(self, local_ae, client_socket):
        """Initializes AssociationAcceptor instance with specified client socket

        :param local_ae: local AE title
        :param client_socket: client socket
        """
        Association.__init__(self, local_ae, client_socket)
        threading.Thread.__init__(self)
        self.client_socket = client_socket
        self._kill = False
        self.sop_classes_as_scp = []
        self.start()

    def kill(self):
        """Overrides base class kill method to set stop-flag for running thread

        :rtype : None
        """
        self._kill = True
        super(AssociationAcceptor, self).kill()

    def run(self):
        assoc_req = self.dul.receive(wait=True)
        result, source, diag = self.ae.on_association_request(assoc_req)
        if result == 0:
            self.asce.accept(assoc_req,
                             self.ae.acceptable_presentation_contexts)
        else:
            self.asce.reject(result, source, diag)
            self.kill()
            return

        # build list of SOPClasses supported
        self.sop_classes_as_scp = [(c[0], c[1], c[2]) for c in
                                   self.asce.accepted_presentation_contexts]
        self.association_established = True

        # association established. Listening on local and remote interfaces
        while not self._kill:
            time.sleep(0.001)
            dimse_msg, pcid = self.dimse.receive(wait=False, timeout=None)
            if dimse_msg:  # dimse message received
                uid = dimse_msg.affected_sop_class_uid
                try:
                    pcid, sop_class, transfer_syntax = \
                        [x for x in self.sop_classes_as_scp if x[0] == pcid][0]
                except IndexError:
                    raise exceptions.ClassNotSupportedError(
                        'SOP Class {0} not supported as SCP'.format(uid))
                obj = sopclass.SOP_CLASSES[uid.value](
                    ae=self.ae, uid=sop_class, dimse=self.dimse, pcid=pcid,
                    transfer_syntax=transfer_syntax,
                    max_pdu_length=self.asce.max_pdu_length)
                obj.scp(dimse_msg)  # run SCP
            if self.asce.check_release():
                self.kill()
            if self.asce.check_abort():
                self.kill()


class AssociationRequester(Association):
    def __init__(self, local_ae, remote_ae=None):
        super(AssociationRequester, self).__init__(local_ae, None)
        self.ae = local_ae
        self.remote_ae = remote_ae
        self.sop_classes_as_scu = []
        self.association_refused = False
        self._request()

    def _request(self):
        ext = [userdataitems.ScpScuRoleSelectionSubItem(i[0], 0, 1)
               for i in self.ae.acceptable_presentation_contexts]

        ans = self.asce.request(self.ae.local_ae, self.remote_ae,
                                self.ae.max_pdu_length,
                                self.ae.presentation_context_definition_list,
                                users_pdu=ext)
        self.ae.on_association_response(ans)
        if not ans:
            self.association_refused = True
            self.dul.kill()
            return
        self.sop_classes_as_scu = [(context[0], context[1], context[2])
                                   for context in
                                   self.asce.accepted_presentation_contexts]

        self.association_established = True

    def scu(self, ds, id_):
        uid = ds.SOPClassUID
        try:
            pcid, _, transfer_syntax = \
                [x for x in self.sop_classes_as_scu if x[1] == uid][0]
        except IndexError:
            raise exceptions.ClassNotSupportedError(
                'SOP Class %s not supported as SCU')

        obj = sopclass.SOP_CLASSES[uid](ae=self.ae, uid=uid, dimse=self.dimse,
                                        pcid=pcid,
                                        transfer_syntax=transfer_syntax,
                                        max_pdu_length=self.asce.max_pdu_length)
        return obj.scu(ds, id_)

    def get_scu(self, sop_class):
        try:
            pcid, _, transfer_syntax = \
                [x for x in self.sop_classes_as_scu if x[1] == sop_class][0]
        except IndexError:
            raise exceptions.ClassNotSupportedError(
                'SOP Class %s not supported as SCU' % sop_class)
        obj = sopclass.SOP_CLASSES[sop_class](ae=self.ae, uid=sop_class,
                                              dimse=self.dimse, pcid=pcid,
                                              transfer_syntax=transfer_syntax,
                                              max_pdu_length=self.asce.max_pdu_length)
        return obj


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
                self.associations.append(AssociationAcceptor(self,
                                                             client_socket))

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
        assoc = AssociationRequester(self, remote_ae=remote_ae)
        while not assoc.association_established and not assoc.association_refused:
            time.sleep(0.1)
        if not assoc.association_established:
            # TODO Replace this exception
            raise Exception('Failed to establish association')
        self.associations.append(assoc)
        yield assoc
        assoc.release(0)

    def on_association_request(self, assoc):
        """Returns result of association request.

        Based on return value association accept or association reject PDU is
        sent in response. Default implementation of the method accepts all
        incoming association requests.

        :param assoc: association request parameters
        :return: tuple of the following values: Result, Source, Reason/Diag. as
        described in PS 3.8 (9.3.4 A-ASSOCIATE-RJ PDU STRUCTURE). If association
        is accepted the first value of the tuple (result) should be 0.
        """
        return 0, 0, 0

    def on_association_response(self, result):
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
