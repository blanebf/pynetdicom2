# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com

import threading
import platform
import copy
import contextlib

from itertools import izip, count
from threading import Lock


import SocketServer

from dicom.UID import ExplicitVRLittleEndian, ImplicitVRLittleEndian, \
    ExplicitVRBigEndian, UID

import netdicom2.sopclass as sopclass
import netdicom2.asceprovider as asceprovider


class AEBase(object):
    default_ts = [ExplicitVRLittleEndian, ImplicitVRLittleEndian,
                  ExplicitVRBigEndian]

    def __init__(self, supported_ts, max_pdu_length):
        if supported_ts is None:
            supported_ts = self.default_ts

        self.supported_ts = frozenset(supported_ts)
        self.timeout = 15
        self.max_pdu_length = max_pdu_length

        self.context_def_list = {}
        self.store_in_file = set()
        self.supported_scu = {}
        self.supported_scp = {}
        self.lock = Lock()

    def add_scu(self, service):
        self.supported_scu.update({
            uid: service for uid in service.sop_classes
        })
        store_in_file = (hasattr(service, 'store_in_file') and
                         service.store_in_file)
        self.update_context_def_list(service.sop_classes, store_in_file)
        return self

    def update_context_def_list(self, sop_classes, store_in_file=False):
        start = max(self.context_def_list.keys()) if self.context_def_list \
            else 1

        self.context_def_list.update(
            self._build_context_def_list(sop_classes, start, store_in_file)
        )

    def copy_context_def_list(self):
        with self.lock:
            return copy.copy(self.context_def_list)

    @contextlib.contextmanager
    def request_association(self, remote_ae):
        """Requests association to a remote application entity"""
        assoc = asceprovider.AssociationRequester(self, remote_ae=remote_ae)
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
        """Extra processing for association response.

        Default implementation does nothing.

        :param response: response received from remote AE
        """
        pass

    def on_receive_echo(self, context):
        """Default handling of C-ECHO command. Always returns SUCCESS code

        User should override this method in sub-class to provide custom
        handling of the command.

        :param context: presentation context (contains ID, SOP Class UID and
                        Transfer Syntax)
        :return: status that should be sent in response
        """
        return sopclass.SUCCESS

    def on_receive_store(self, context, ds):
        """Default handling of C-STORE command. Always returns
        ELEMENT_DISCARDED code.

        User should override this method in sub-class to provide custom handling
        of the command

        :param context: presentation context (contains ID, SOP Class UID and
                        Transfer Syntax)
        :param ds: dataset that should be stored
        :return: status code
        """
        return sopclass.ELEMENT_DISCARDED

    def on_receive_find(self, context, ds):
        """Default handling of C-FIND command. Returns empty iterator.

        :param context: presentation context (contains ID, SOP Class UID and
                        Transfer Syntax)
        :param ds: dataset with C-FIND parameters
        :return: iterator that returns tuples: (<result dataset>, <status code>)
        """
        return iter([])

    def on_receive_move(self, context, ds, destination):
        """Default handling of C-MOVE command. Returns empty empty values

        :param context: presentation context (contains ID, SOP Class UID and
                        Transfer Syntax)
        :param ds: dataset with C-MOVE parameters
        :param destination: C-MOVE command destination
        :return: tuple: remote AE parameters, number of operations and iterator
        that will return datasets for moving
        """
        return None, 0, iter([])

    def _build_context_def_list(self, sop_classes, start, store_in_file):
        if store_in_file:
            self.store_in_file.update(sop_classes)
        return {pc_id: asceprovider.PContextDef(pc_id, UID(sop_class),
                                                self.supported_ts)
                for sop_class, pc_id in izip(sop_classes,
                                             count(start, 2))}


class ClientAE(AEBase):
    def __init__(self, ae_title, supported_ts=None,
                 max_pdu_length=16000):
        super(ClientAE, self).__init__(supported_ts, max_pdu_length)
        self.local_ae = {'address': platform.node(), 'aet': ae_title}


class AE(AEBase, SocketServer.ThreadingTCPServer):
    """Represents a DICOM application entity

    Instance if this class represent an application entity. Once
    instantiated, it starts a new thread and enters an event loop,
    where events are association requests from remote AEs. Events
    trigger callback functions that perform user defined actions based
    on received events.
    """

    def __init__(self, ae_title, port, supported_ts=None, max_pdu_length=16000):
        SocketServer.ThreadingTCPServer.__init__(
            self,
            ('', port),
            asceprovider.AssociationAcceptor
        )
        AEBase.__init__(self, supported_ts, max_pdu_length)

        self.daemon_threads = True
        self.allow_reuse_address = True

        self.local_ae = {'address': platform.node(), 'port': port,
                         'aet': ae_title}

    def __enter__(self):
        threading.Thread(target=self.serve_forever).start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    def add_scp(self, service):
        self.supported_scp.update({
            uid: service for uid in service.sop_classes
        })
        store_in_file = (hasattr(service, 'store_in_file') and
                         service.store_in_file)
        self.update_context_def_list(service.sop_classes, store_in_file)
        return self

    def quit(self):
        """Stops AE.

        This will close any open associations and will break from event loop
        for AEs that supports service SOP Classes as SCP.
        """
        self.shutdown()
        self.server_close()
