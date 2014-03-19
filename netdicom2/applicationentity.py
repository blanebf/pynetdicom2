#
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

import threading
import socket
import sys
import select
import platform
import gc
import time

from dicom.UID import ExplicitVRLittleEndian, ImplicitVRLittleEndian, \
    ExplicitVRBigEndian, UID

import sopclass
from dulprovider import DULServiceProvider
from netdicom2.dimseprovider import DIMSEServiceProvider
from asceprovider import ACSEServiceProvider
import dimseparameters


class Association(threading.Thread):

    def __init__(self, local_ae, client_socket=None, remote_ae=None):
        if not client_socket and not remote_ae:
            raise ValueError('Both remote_ae and client_socket are not specified')
        if client_socket and remote_ae:
            raise ValueError('Both remote_ae and client_socket specified')
        super(Association, self).__init__()
        if client_socket:  # must respond for request from a remote AE
            self.mode = 'Acceptor'
        if remote_ae:  # must request
            self.mode = 'Requestor'

        self.client_socket = client_socket
        self.dul = DULServiceProvider(client_socket)
        self.ae = local_ae
        self.remote_ae = remote_ae
        self._kill = False

        self.sop_classes_as_scp = []
        self.sop_classes_as_scu = []
        self.association_established = False
        self.association_refused = None

        self.asce = ACSEServiceProvider(self.dul)
        self.dimse = DIMSEServiceProvider(self.dul)

        self.start()

    @staticmethod
    def get_sop_class(ds):
        return sopclass.SOP_CLASSES[ds.SOPClassUID]

    def scu(self, ds, id_):
        uid = ds.SOPClassUID
        try:
            pcid, _, transfer_syntax = [x for x in self.sop_classes_as_scu if x[1] == uid][0]
        except IndexError:
            raise Exception("SOP Class %s not supported as SCU")  # TODO: replace this exception

        obj = sopclass.SOP_CLASSES[uid](ae=self.ae, uid=uid, dimse=self.dimse, pcid=pcid,
                                        transfer_syntax=transfer_syntax, max_pdu_length=self.asce.max_pdu_length)
        return obj.scu(ds, id_)

    def get_scu(self, sop_class):
        try:
            pcid, _, transfer_syntax = [x for x in self.sop_classes_as_scu if x[1] == sop_class][0]
        except IndexError:
            raise Exception("SOP Class %s not supported as SCU" % sop_class)  # TODO replace this exception
        obj = sopclass.SOP_CLASSES[sop_class](ae=self.ae, uid=sop_class, dimse=self.dimse, pcid=pcid,
                                              transfer_syntax=transfer_syntax, max_pdu_length=self.asce.max_pdu_length)
        return obj

    def kill(self):
        self._kill = True
        for ii in range(1000):
            if self.dul.stop():
                continue
            time.sleep(0.001)
        self.dul.kill()

    def release(self, reason):
        self.asce.release(reason)
        self.kill()

    def abort(self, reason):
        # self.asce.abort(reason) TODO: Look into passing abort reason
        self.asce.abort()
        self.kill()

    def run(self):
        if self.mode == 'Acceptor':
            self.asce.accept(self.client_socket, self.ae.acceptable_presentation_contexts)
            # call back
            self.ae.on_association_request(self)
            # build list of SOPClasses supported
            self.sop_classes_as_scp = [(context[0], context[1], context[2])
                                       for context in self.asce.accepted_presentation_contexts]
        else:  # Requestor mode
            #  build role extended negociation
            ext = []
            for ii in self.ae.acceptable_presentation_contexts:
                tmp = dimseparameters.ScpScuRoleSelectionParameters()
                tmp.sop_class_uid = ii[0]
                tmp.scu_role = 0
                tmp.scp_role = 1
                ext.append(tmp)

            ans = self.asce.request(self.ae.local_ae, self.remote_ae,
                                    self.ae.max_pdu_length,
                                    self.ae.presentation_context_definition_list,
                                    users_pdu=ext)
            if ans:
                self.ae.on_association_response(ans)
            else:
                self.association_refused = True
                self.dul.kill()
                return
            self.sop_classes_as_scu = [(context[0], context[1], context[2])
                                       for context in self.asce.accepted_presentation_contexts]

        self.association_established = True

        # association established. Listening on local and remote interfaces
        while not self._kill:
            time.sleep(0.001)
            # look for incoming DIMSE message
            if self.mode == 'Acceptor':
                dimse_msg, pcid = self.dimse.receive(wait=False, timeout=None)
                if dimse_msg:  # dimse message received
                    uid = dimse_msg.affected_sop_class_uid
                    try:
                        pcid, sop_class, transfer_syntax = [x for x in self.sop_classes_as_scp if x[0] == pcid][0]
                    except IndexError:
                        raise Exception("SOP Class %s not supported as SCP" % uid)  # TODO Replace exception
                    obj = sopclass.SOP_CLASSES[uid.value](ae=self.ae, uid=sop_class, dimse=self.dimse, pcid=pcid,
                                                          transfer_syntax=transfer_syntax,
                                                          max_pdu_length=self.asce.max_pdu_length,
                                                          asce=self.asce)
                    obj.scp(dimse_msg)  # run SCP

                # check for release request
                if self.asce.check_release():
                    self.kill()

                # check for abort
                if self.asce.check_abort():
                    self.kill()


class AE(threading.Thread):

    """Represents a DICOM application entity

    Instance if this class represent an application entity. Once
    instantiated, it starts a new thread and enters an event loop,
    where events are association requests from remote AEs. Events
    trigger callback functions that perform user defined actions based
    on received events.
    """

    def __init__(self, ae_title, port, sop_scu, sop_scp, supported_transfer_syntax=None, max_pdu_length=16000):
        if supported_transfer_syntax is None:
            supported_transfer_syntax = [ExplicitVRLittleEndian, ImplicitVRLittleEndian, ExplicitVRBigEndian]
        self.local_ae = {'Address': platform.node(), 'Port': port, 'AET': ae_title}
        self.supported_sop_classes_as_scu = sop_scu
        self.supported_sop_classes_as_scp = sop_scp
        self.supported_transfer_syntax = supported_transfer_syntax
        self.max_number_of_associations = 25
        threading.Thread.__init__(self, name=self.local_ae['AET'])

        self.local_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.local_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.local_server_socket.bind(('', port))
        self.local_server_socket.listen(1)
        self.max_pdu_length = max_pdu_length

        # build presentation context definition list to be sent to remote AE when requesting association.
        count = 1
        self.presentation_context_definition_list = []
        for sop_class in self.supported_sop_classes_as_scu + self.supported_sop_classes_as_scp:
            self.presentation_context_definition_list.append([count, UID(sop_class),
                                                             [x for x in self.supported_transfer_syntax]])
            count += 2

        # build acceptable context definition list used to decide whether an association from a remote AE will
        # be accepted or not. This is based on the supported_sop_classes_as_scp and supported_transfer_syntax
        # values set for this AE.
        self.acceptable_presentation_contexts = [[sop_class, [x for x in self.supported_transfer_syntax]]
                                                 for sop_class in self.supported_sop_classes_as_scp]

        # used to terminate AE
        self._quit = False

        # list of active association objects
        self.associations = []

    def run(self):
        if not self.supported_sop_classes_as_scp:
            # no need to loop. This is just a client AE. All events will be triggered by the user
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
                self.associations.append(Association(self, client_socket))

            # delete dead associations
            for association in self.associations:
                if not association.isAlive():
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

    def request_association(self, remote_ae):
        """Requests association to a remote application entity"""
        assoc = Association(self, remote_ae=remote_ae)
        while not assoc.association_established and not assoc.association_refused:
            time.sleep(0.1)
        if assoc.association_established:
            self.associations.append(assoc)
            return assoc
        else:
            return None

    def on_association_request(self, assoc):
        pass

    def on_association_response(self, result):
        pass

    def on_receive_echo(self, service):
        pass

    def on_receive_store(self, service, ds):
        pass

    def on_receive_find(self, service, ds):
        pass

    def on_receive_move(self, service, ds, destination):
        pass
