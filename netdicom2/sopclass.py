# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
"""
Module contains implementation of the DICOM service classes. Module
also contains useful constants for message statuses and service
SOP Class UIDs.

All services implementation subclass base ServiceClass class. Base class
uses a little bit of meta-class magic, that helps to define service supported
SOP Classes in a declarative manner (just list supported UIDs in sop_classes
class attribute.

If user wants to define their own custom service class they should inherit
from ServiceClass, list supported UIDs in sop_class attributes. Expected status
codes should also be listed in statuses class attribute.
Each service class should have scu(...) and scp(...) methods if it is intended
to be used as either SCU and(or) SCP respectively.
Currently supported service classes are: Verification (as SCU and SCP),
Storage (as SCU and SCP) Query/Retrieve (as SCU and SCP), Worklist
(as SCU and SCP).
"""
import time

import netdicom2.dsutils as dsutils
import netdicom2.exceptions as exceptions
import netdicom2.dimsemessages as dimsemessages


class Status(object):
    """Class represents message status.

    This a helper class that provides convenience methods for printing and
    converting status codes.
    """

    def __init__(self, status_type, description, code_range):
        """Initializes new Status instance

        :param status_type: status type (Success, Pending, Warning, Failure)
        :param description: status description
        :param code_range: status code range
        """
        self.status_type = status_type
        self.description = description
        self.code_range = code_range

    def __int__(self):
        """Converts status to integer (takes status lower value in range and
        returns it.

        :return: lower value in code range
        """
        return self.code_range[0]

    def __repr__(self):
        """Returns status string representation

        :return: status string representation
        """
        return 'Status(status_type={self.status_type}, ' \
               'description={self.description}, ' \
               'code_range={self.code_range})'.format(self=self)


SUCCESS = Status('Success', 'Sub-operations Complete - No Failure or Warnings',
                 xrange(0x0000, 0x0000 + 1))

PENDING = Status('Pending', 'Sub-operations are continuing',
                 xrange(0xFF00, 0xFF00 + 1))
PENDING_WARNING = Status('Pending',
                         'Matches are continuing - Warning that one or more'
                         ' optional keys were not supported for existence '
                         'and/or matching for this identifier',
                         xrange(0xFF01, 0xFF01 + 1))

CANCEL = Status('Cancel', 'Sub-operations terminated due to Cancel indication',
                xrange(0xFE00, 0xFE00 + 1))
MATCHING_TERMINATED_DUE_TO_CANCEL_REQUEST = Status('Cancel',
                                                   'Matching terminated due to '
                                                   'Cancel request',
                                                   xrange(0xFE00, 0xFE00 + 1))

WARNING = Status('Warning',
                 'Sub-operations Complete - One or more Failures or Warnings',
                 xrange(0xB000, 0xB000 + 1))
COERCION_OF_DATA_ELEMENTS = Status('Warning', 'Coercion of Data Elements',
                                   xrange(0xB000, 0xB000 + 1))
ELEMENT_DISCARDED = Status('Warning', 'Element Discarded',
                           xrange(0xB006, 0xB006 + 1))
DATASET_DOES_NOT_MATCH_SOP_CLASS_WARNING = Status('Warning',
                                                  'Data Set does not match SOP'
                                                  ' Class',
                                                  xrange(0xB007, 0xB007 + 1))

OUT_OF_RESOURCES = Status('Failure', 'Refused: Out of resources',
                          xrange(0xA700, 0xA7FF + 1))
DATASET_DOES_NOT_MATCH_SOP_CLASS_FAILURE = Status('Failure',
                                                  'Error: Data Set does not '
                                                  'match SOP Class',
                                                  xrange(0xA900, 0xA9FF + 1))
CANNOT_UNDERSTAND = Status('Failure', 'Error: Cannot understand',
                           xrange(0xC000, 0xCFFF + 1))
IDENTIFIER_DOES_NOT_MATCH_SOP_CLASS = Status('Failure',
                                             'Identifier does not match '
                                             'SOP Class',
                                             xrange(0xA900, 0xA900 + 1))
UNABLE_TO_PROCESS = Status('Failure', 'Unable to process',
                           xrange(0xC000, 0xCFFF + 1))
OUT_OF_RESOURCES_NUMBER_OF_MATCHES = Status('Failure',
                                            'Refused: Out of resources - '
                                            'Unable to calcultate number '
                                            'of matches',
                                            xrange(0xA701, 0xA701 + 1))
OUT_OF_RESOURCES_UNABLE_TO_PERFORM = Status('Failure',
                                            'Refused: Out of resources - '
                                            'Unable to perform sub-operations',
                                            xrange(0xA702, 0xA702 + 1))
MOVE_DESTINATION_UNKNOWN = Status('Failure', 'Refused: Move destination '
                                             'unknown',
                                  xrange(0xA801, 0xA801 + 1))


# VERIFICATION SOP CLASSES
VERIFICATION_SOP_CLASS = '1.2.840.10008.1.1'

# STORAGE SOP CLASSES
MR_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.4'
CT_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.2'
PET_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.128'
CR_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.1'
SC_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.7'
RT_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.481.1'
RT_DOSE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.481.2'
RT_STRUCTURE_SET_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.481.3'
RT_PLAN_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.481.5'
SPATIAL_REGISTRATION_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.66.1'
ENHANCED_SR_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.88.22'
XRAY_RADIATION_DOSE_SR_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.88.67'
DX_IMAGE_STORAGE_FOR_PRESENTATION_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.1.1'
DX_IMAGE_STORAGE_FOR_PROCESSING_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.1.1.1'
MG_IMAGE_STORAGE_FOR_PRESENTATION_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.1.2'
MG_IMAGE_STORAGE_FOR_PROCESSING_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.1.2.1'
IO_IMAGE_STORAGE_FOR_PRESENTATION_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.1.3'
IO_IMAGE_STORAGE_FOR_PROCESSING_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.1.3.1'
XA_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.12.1'
ENHANCED_XA_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.12.1.1'
RF_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.12.2'
ENHANCED_RF_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.12.2.1'
ENHANCED_CT_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.2.1'
NM_IMAGE_STORAGE_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.20'

BASIC_TEXT_SR_STORAGE = '1.2.840.10008.5.1.4.1.1.88.11'
ENHANCED_SR_STORAGE = '1.2.840.10008.5.1.4.1.1.88.22'
COMPREHENSIVE_SR_STORAGE = '1.2.840.10008.5.1.4.1.1.88.33'

# QUERY RETRIEVE SOP Classes
PATIENT_ROOT_FIND_SOP_CLASS = '1.2.840.10008.5.1.4.1.2.1.1'
PATIENT_ROOT_MOVE_SOP_CLASS = '1.2.840.10008.5.1.4.1.2.1.2'
PATIENT_ROOT_GET_SOP_CLASS = '1.2.840.10008.5.1.4.1.2.1.3'
STUDY_ROOT_FIND_SOP_CLASS = '1.2.840.10008.5.1.4.1.2.2.1'
STUDY_ROOT_MOVE_SOP_CLASS = '1.2.840.10008.5.1.4.1.2.2.2'
STUDY_ROOT_GET_SOP_CLASS = '1.2.840.10008.5.1.4.1.2.2.3'
PATIENT_STUDY_ONLY_FIND_SOP_CLASS = '1.2.840.10008.5.1.4.1.2.3.1'
PATIENT_STUDY_ONLY_MOVE_SOP_CLASS = '1.2.840.10008.5.1.4.1.2.3.2'
PATIENT_STUDY_ONLY_GET_SOP_CLASS = '1.2.840.10008.5.1.4.1.2.3.3'

MODALITY_WORK_LIST_INFORMATION_FIND_SOP_CLASS = '1.2.840.10008.5.1.4.31'

SOP_CLASSES = {}  # Initialized later


class ServiceClassMeta(type):
    """Simple metaclass for ServiceClass-based class.

    Metaclass takes 'sop_classes' class attribute and registers created class
    in module-level SOP_CLASSES dictionary for SOP Class UIDs listed in
    the attribute
    """

    def __new__(mcs, name, bases, dct):
        """Handles creation and registration of the new ServiceClass class

        :param name: class name
        :param bases: base class names
        :param dct: attribute dictionary
        :return: new ServiceClass class
        """
        new_class = type.__new__(mcs, name, bases, dct)
        try:
            SOP_CLASSES.update(
                {sop_class: new_class for sop_class in dct['sop_classes']})
        except KeyError:
            pass
        return new_class


class ServiceClass(object):
    """Base class for all service classes.

    Class provides basic initialization and several utility methods.
    """
    __metaclass__ = ServiceClassMeta

    statuses = []
    sop_classes = []

    def __init__(self, ae, uid, dimse, pcid, transfer_syntax,
                 max_pdu_length=16000):
        """

        :param ae: AE instance that this service class belongs to
        :param uid: service SOP Class UID
        :param dimse: provider for DIMSE messages
        :param pcid: presentation context ID
        :param transfer_syntax: service transfer syntax
        :param max_pdu_length: maximum PDU length. Defaults to 16000
        """
        self.ae = ae
        self.uid = uid
        self.dimse = dimse
        self.pcid = pcid
        self.transfer_syntax = transfer_syntax
        self.max_pdu_length = max_pdu_length

    def code_to_status(self, code):
        """Converts code to status

        If unexpected code is passed (code does not fall into any of the ranges
        of statuses that are listed in statuses class attribute) method
        returns 'Failure' status object.
        :param code: status code
        :return: status object converted from code
        """
        for status in self.statuses:
            if code in status.code_range:
                return status
        return Status('Failure', 'Unknown or unexpected status',
                      xrange(code, code))


class VerificationServiceClass(ServiceClass):
    """Implementation of verification service SOP Class.

    Class provides implementation for both SCU as SCP roles.
    """
    statuses = [SUCCESS, UNABLE_TO_PROCESS]
    sop_classes = [VERIFICATION_SOP_CLASS]

    def scu(self, msg_id):
        """Sends verification request and returns it's status result

        :param msg_id: message ID
        :return: status in response message. `SUCCESS` if verification was
        successfully completed.
        """
        c_echo = dimsemessages.CEchoRQMessage()
        c_echo.message_id = msg_id
        c_echo.affected_sop_class_uid = self.uid

        self.dimse.send(c_echo, self.pcid, self.max_pdu_length)

        response, msg_id = self.dimse.receive(wait=True)
        return self.code_to_status(response.status)

    def scp(self, msg):
        """Process received C-ECHO.

        Method delegates actual handling of C-ECHO to AE instance by calling
        its `on_receive_echo` method and expecting response status from it.

        :param msg: incoming C-ECHO message
        """
        try:
            status = self.ae.on_receive_echo(self)
        except exceptions.EventHandlingError:
            status = UNABLE_TO_PROCESS

        rsp = dimsemessages.CEchoRSPMessage()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.status = status
        self.dimse.send(rsp, self.pcid, self.max_pdu_length)


class StorageServiceClass(ServiceClass):
    statuses = [OUT_OF_RESOURCES, DATASET_DOES_NOT_MATCH_SOP_CLASS_FAILURE,
                CANNOT_UNDERSTAND, COERCION_OF_DATA_ELEMENTS,
                DATASET_DOES_NOT_MATCH_SOP_CLASS_WARNING, ELEMENT_DISCARDED,
                SUCCESS]
    sop_classes = [MR_IMAGE_STORAGE_SOP_CLASS, CT_IMAGE_STORAGE_SOP_CLASS,
                   PET_IMAGE_STORAGE_SOP_CLASS,
                   CR_IMAGE_STORAGE_SOP_CLASS, SC_IMAGE_STORAGE_SOP_CLASS,
                   RT_IMAGE_STORAGE_SOP_CLASS, RT_DOSE_STORAGE_SOP_CLASS,
                   RT_STRUCTURE_SET_STORAGE_SOP_CLASS,
                   RT_PLAN_STORAGE_SOP_CLASS, SPATIAL_REGISTRATION_SOP_CLASS,
                   ENHANCED_SR_SOP_CLASS, XRAY_RADIATION_DOSE_SR_SOP_CLASS,
                   DX_IMAGE_STORAGE_FOR_PRESENTATION_SOP_CLASS,
                   DX_IMAGE_STORAGE_FOR_PROCESSING_SOP_CLASS,
                   MG_IMAGE_STORAGE_FOR_PRESENTATION_SOP_CLASS,
                   MG_IMAGE_STORAGE_FOR_PROCESSING_SOP_CLASS,
                   IO_IMAGE_STORAGE_FOR_PRESENTATION_SOP_CLASS,
                   IO_IMAGE_STORAGE_FOR_PROCESSING_SOP_CLASS,
                   XA_IMAGE_STORAGE_SOP_CLASS,
                   ENHANCED_XA_IMAGE_STORAGE_SOP_CLASS,
                   RF_IMAGE_STORAGE_SOP_CLASS,
                   ENHANCED_RF_IMAGE_STORAGE_SOP_CLASS,
                   ENHANCED_CT_IMAGE_STORAGE_SOP_CLASS,
                   NM_IMAGE_STORAGE_SOP_CLASS, BASIC_TEXT_SR_STORAGE,
                   ENHANCED_SR_STORAGE, COMPREHENSIVE_SR_STORAGE]

    def scu(self, dataset, msg_id):
        # build C-STORE primitive
        c_store = dimsemessages.CStoreRQMessage()
        c_store.message_id = msg_id
        c_store.affected_sop_class_uid = dataset.SOPClassUID
        c_store.affected_sop_instance_uid = dataset.SOPInstanceUID
        c_store.priority = dimsemessages.PRIORITY_MEDIUM
        c_store.data_set = dsutils.encode(dataset,
                                          self.transfer_syntax.is_implicit_VR,
                                          self.transfer_syntax.is_little_endian)
        # send c_store request
        self.dimse.send(c_store, self.pcid, self.max_pdu_length)

        # wait for c-store response
        response, id_ = self.dimse.receive(wait=True)
        return self.code_to_status(response.status)

    def scp(self, msg):
        try:
            ds = dsutils.decode(msg.data_set,
                                self.transfer_syntax.is_implicit_VR,
                                self.transfer_syntax.is_little_endian)
            status = self.ae.on_receive_store(self, ds)
        except exceptions.EventHandlingError:
            status = CANNOT_UNDERSTAND
        # make response
        rsp = dimsemessages.CStoreRSPMessage()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_instance_uid = msg.affected_sop_instance_uid
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid
        rsp.status = int(status)
        self.dimse.send(rsp, self.pcid, self.max_pdu_length)


class QueryRetrieveFindSOPClass(ServiceClass):
    sop_classes = [PATIENT_ROOT_FIND_SOP_CLASS, STUDY_ROOT_FIND_SOP_CLASS,
                   PATIENT_STUDY_ONLY_FIND_SOP_CLASS]
    statuses = [OUT_OF_RESOURCES, IDENTIFIER_DOES_NOT_MATCH_SOP_CLASS,
                UNABLE_TO_PROCESS, MATCHING_TERMINATED_DUE_TO_CANCEL_REQUEST,
                SUCCESS, PENDING, PENDING_WARNING]

    def scu(self, ds, msg_id):
        # build C-FIND primitive
        c_find = dimsemessages.CFindRQMessage()
        c_find.message_id = msg_id
        c_find.affected_sop_class_uid = self.uid
        c_find.priority = dimsemessages.PRIORITY_MEDIUM
        c_find.data_set = dsutils.encode(ds,
                                         self.transfer_syntax.is_implicit_VR,
                                         self.transfer_syntax.is_little_endian)

        # send c-find request
        self.dimse.send(c_find, self.pcid, self.max_pdu_length)
        while 1:
            time.sleep(0.001)
            # wait for c-find responses
            response, id_ = self.dimse.receive(wait=False)
            if not response:
                continue
            d = dsutils.decode(response.data_set,
                               self.transfer_syntax.is_implicit_VR,
                               self.transfer_syntax.is_little_endian)
            status = self.code_to_status(response.status).status_type
            yield status, d
            if status != 'Pending':
                break

    def scp(self, msg):
        ds = dsutils.decode(msg.identifier, self.transfer_syntax.is_implicit_VR,
                            self.transfer_syntax.is_little_endian)

        # make response
        rsp = dimsemessages.CFindRSPMessage()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid

        gen = self.ae.on_receive_find(self, ds)
        for identifier_ds, status in gen:
            rsp.status = int(status)
            rsp.data_set = dsutils.encode(identifier_ds,
                                          self.transfer_syntax.is_implicit_VR,
                                          self.transfer_syntax.is_little_endian)
            # send response
            self.dimse.send(rsp, self.pcid, self.max_pdu_length)
            time.sleep(0.001)

        rsp = dimsemessages.CFindRSPMessage()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid
        rsp.status = int(SUCCESS)
        self.dimse.send(rsp, self.pcid, self.max_pdu_length)


class QueryRetrieveGetSOPClass(ServiceClass):
    sop_classes = [PATIENT_ROOT_GET_SOP_CLASS, STUDY_ROOT_GET_SOP_CLASS,
                   PATIENT_STUDY_ONLY_GET_SOP_CLASS]
    statuses = [OUT_OF_RESOURCES_NUMBER_OF_MATCHES,
                OUT_OF_RESOURCES_UNABLE_TO_PERFORM,
                IDENTIFIER_DOES_NOT_MATCH_SOP_CLASS,
                UNABLE_TO_PROCESS, CANCEL, WARNING, SUCCESS, PENDING]

    def scu(self, ds, msg_id):
        # build C-GET primitive
        c_get = dimsemessages.CGetRQMessage()
        c_get.message_id = msg_id
        c_get.affected_sop_class_uid = self.uid
        c_get.priority = dimsemessages.PRIORITY_MEDIUM
        c_get.data_set = dsutils.encode(ds,
                                        self.transfer_syntax.is_implicit_VR,
                                        self.transfer_syntax.is_little_endian)

        # send c-get primitive
        self.dimse.send(c_get, self.pcid, self.max_pdu_length)
        while 1:
            # receive c-store
            msg, id_ = self.dimse.receive(wait=True)
            if msg.command_field == dimsemessages.CGetRSPMessage.command_field:
                if self.code_to_status(msg.status).status_type == 'Pending':
                    pass  # pending. intermediate C-GET response
                else:
                    break  # last answer
            elif (msg.command_field ==
                    dimsemessages.CStoreRQMessage.command_field):
                # send c-store response
                rsp = dimsemessages.CStoreRSPMessage()
                rsp.message_id_being_responded_to = msg.message_id
                rsp.affected_sop_instance_uid = msg.affected_sop_instance_uid
                rsp.affected_sop_class_uid = msg.affected_sop_class_uid
                try:
                    d = dsutils.decode(msg.data_set,
                                       self.transfer_syntax.is_implicit_VR,
                                       self.transfer_syntax.is_little_endian)
                    status = self.ae.on_receive_store(self, d)
                    yield self, d
                except exceptions.EventHandlingError:
                    status = CANNOT_UNDERSTAND

                rsp.status = int(status)
                self.dimse.send(rsp, id_, self.max_pdu_length)


class QueryRetrieveMoveSOPClass(ServiceClass):
    sop_classes = [PATIENT_ROOT_MOVE_SOP_CLASS, STUDY_ROOT_MOVE_SOP_CLASS,
                   PATIENT_STUDY_ONLY_MOVE_SOP_CLASS]
    statuses = [OUT_OF_RESOURCES_NUMBER_OF_MATCHES,
                OUT_OF_RESOURCES_UNABLE_TO_PERFORM, MOVE_DESTINATION_UNKNOWN,
                IDENTIFIER_DOES_NOT_MATCH_SOP_CLASS, UNABLE_TO_PROCESS, CANCEL,
                WARNING, SUCCESS, PENDING]

    def scu(self, ds, dest_ae, msg_id):
        # build C-FIND primitive
        c_move = dimsemessages.CMoveRQMessage()
        c_move.message_id = msg_id
        c_move.affected_sop_class_uid = self.uid
        c_move.move_destination = dest_ae
        c_move.priority = dimsemessages.PRIORITY_MEDIUM
        c_move.data_set = dsutils.encode(ds,
                                         self.transfer_syntax.is_implicit_VR,
                                         self.transfer_syntax.is_little_endian)
        # send c-find request
        self.dimse.send(c_move, self.pcid, self.max_pdu_length)

        while 1:
            # wait for c-move responses
            time.sleep(0.001)
            response, id_ = self.dimse.receive(wait=False)
            if not response:
                continue
            status = self.code_to_status(response.status).status_type
            if status != 'Pending':
                break
            yield status

    def scp(self, msg):
        ds = dsutils.decode(msg.data_set, self.transfer_syntax.is_implicit_VR,
                            self.transfer_syntax.is_little_endian)

        # make response
        rsp = dimsemessages.CMoveRSPMessage()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid
        remote_ae, nop, gen = self.ae.on_receive_move(self, ds,
                                                      msg.move_destination)
        assoc = self.ae.request_association(remote_ae)
        failed = 0
        warning = 0
        completed = 0
        for data_set in gen:
            # request an association with destination send C-STORE
            obj = assoc.get_scu(data_set.SOPClassUID)
            status = obj.scu(data_set, completed)
            if status.type_ == 'Failed':
                failed += 1
            if status.type_ == 'Warning':
                warning += 1
            rsp.status = int(PENDING)
            rsp.num_of_remaining_sub_ops = nop - completed
            rsp.num_of_completed_sub_ops = completed
            rsp.num_of_failed_sub_ops = failed
            rsp.num_of_warning_sub_ops = warning
            completed += 1

            # send response
            self.dimse.send(rsp, self.pcid, self.max_pdu_length)

        rsp = dimsemessages.CMoveRSPMessage()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid
        rsp.num_of_remaining_sub_ops = nop - completed
        rsp.num_of_completed_sub_ops = completed
        rsp.num_of_failed_sub_ops = failed
        rsp.num_of_warning_sub_ops = warning
        rsp.status = int(SUCCESS)
        self.dimse.send(rsp, self.pcid, self.max_pdu_length)
        assoc.release(0)


class BasicWorkListServiceClass(ServiceClass):
    sop_classes = [MODALITY_WORK_LIST_INFORMATION_FIND_SOP_CLASS]


class ModalityWorkListServiceSOPClass(BasicWorkListServiceClass):
    statuses = [OUT_OF_RESOURCES, IDENTIFIER_DOES_NOT_MATCH_SOP_CLASS,
                UNABLE_TO_PROCESS, MATCHING_TERMINATED_DUE_TO_CANCEL_REQUEST,
                SUCCESS, PENDING, PENDING_WARNING]

    def scu(self, ds, msg_id):
        # build C-FIND primitive
        c_find = dimsemessages.CFindRQMessage()
        c_find.message_id = msg_id
        c_find.affected_sop_class_uid = self.uid
        c_find.priority = dimsemessages.PRIORITY_MEDIUM
        c_find.data_set = dsutils.encode(ds,
                                         self.transfer_syntax.is_implicit_VR,
                                         self.transfer_syntax.is_little_endian)

        # send c-find request
        self.dimse.send(c_find, self.pcid, self.max_pdu_length)
        while 1:
            time.sleep(0.001)
            # wait for c-find responses
            response, id_ = self.dimse.receive(wait=False)
            if not response:
                continue
            d = dsutils.decode(response.data_set,
                               self.transfer_syntax.is_implicit_VR,
                               self.transfer_syntax.is_little_endian)
            status = self.code_to_status(response.status).status_type
            yield status, d
            if status != 'Pending':
                break

    def scp(self, msg):
        ds = dsutils.decode(msg.data_set, self.transfer_syntax.is_implicit_VR,
                            self.transfer_syntax.is_little_endian)

        # make response
        rsp = dimsemessages.CFindRSPMessage()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid

        gen = self.ae.on_receive_find(self, ds)
        for identifier_ds, status in gen:
            rsp.status = int(status)
            rsp.data_set = dsutils.encode(identifier_ds,
                                          self.transfer_syntax.is_implicit_VR,
                                          self.transfer_syntax.is_little_endian)
            # send response
            self.dimse.send(rsp, self.pcid, self.max_pdu_length)
            time.sleep(0.001)

        # send final response
        rsp = dimsemessages.CFindRSPMessage()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid
        rsp.status = int(SUCCESS)
        self.dimse.send(rsp, self.pcid, self.max_pdu_length)
