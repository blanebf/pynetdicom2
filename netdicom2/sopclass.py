# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
"""
Module contains implementation of the DICOM service classes. Module
also contains useful constants for message statuses and service
SOP Class UIDs.

Each service SCU or SCP role is represent by a callable. To define which
service SOP Classes are supported by role implementation callable has an
attribute ``sop_classes`` that lists all SOP Classes.
For convenience module provides ``sop_classes`` decorator that can be used like
this::

    @sop_classes([UID1, UID2, UID3])
    def sample_scp(asce, ctx, msg):
        pass


This decorator will set (or extend if already exists) ``sop_classes`` attribute
of decorated function.

Each SCP role implementation must conform to the following interface::

    def sample_scp(asce, ctx, msg):
        pass

The arguments have the following meaning:
    * ``asce`` - ``asceprovider.Association`` object. Can be used to send and
      receive DIMSE messages, and get access to the Application Entity instance.
    * ``ctx`` - presentation context definition (``asceprovider.PContextDef``).
      contains context ID for current association, SOP Class UID and selected
      transfer syntax.
    * ``msg`` - received DIMSE message.

Each SCU role implementation must conform to the following interface::

    def sample_scu(asce, ctx, *args, **kwargs):
        pass

Arguments have similar meaning to SCP role implementation. First two mandatory
arguments are provided by association and the rest are expected from service
user.
"""

from dicom.filereader import read_preamble, _read_file_meta_info

import dicom.UID
import dicom.dataset
import dicom.sequence

import netdicom2.dsutils as dsutils
import netdicom2.exceptions as exceptions
import netdicom2.dimsemessages as dimsemessages


class Status(object):
    """Class represents message status.

    This is a helper class that provides convenience methods for printing and
    converting status codes.
    """

    def __init__(self, status_type, description, code_range):
        """Initializes new Status instance based on type, description and
        code range.

        :param status_type: status type (Success, Pending, Warning, Failure)
        :param description: status description
        :param code_range: status code range
        """
        self.status_type = status_type
        self.description = description
        self.code_range = code_range

    def __int__(self):
        """Converts status to integer (takes status lowest value in range and
        returns it.

        :return: lowest value in code range
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

STATUSES = [SUCCESS, PENDING, PENDING_WARNING, CANCEL,
            MATCHING_TERMINATED_DUE_TO_CANCEL_REQUEST,
            WARNING, COERCION_OF_DATA_ELEMENTS, ELEMENT_DISCARDED,
            DATASET_DOES_NOT_MATCH_SOP_CLASS_WARNING, OUT_OF_RESOURCES,
            DATASET_DOES_NOT_MATCH_SOP_CLASS_FAILURE, CANNOT_UNDERSTAND,
            IDENTIFIER_DOES_NOT_MATCH_SOP_CLASS, UNABLE_TO_PROCESS,
            OUT_OF_RESOURCES_NUMBER_OF_MATCHES,
            OUT_OF_RESOURCES_UNABLE_TO_PERFORM, MOVE_DESTINATION_UNKNOWN]


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

STORAGE_COMMITMENT_SOP_CLASS = '1.2.840.10008.1.20.1'


def code_to_status(code):
        """Converts code to status.

        If unexpected code is passed (code does not fall into any of the ranges
        of the known statuses that are listed in this module) function
        returns 'Failure' status object.

        :param code: status code
        :return: :class:`~netdicom2.sopclass.Status` object converted from code
        """
        for status in STATUSES:
            if code in status.code_range:
                return status
        return Status('Failure', 'Unknown or unexpected status',
                      xrange(code, code))


def sop_classes(uids):
    def augemnt(service):
        if not hasattr(service, 'sop_classes'):
            service.sop_classes = []
        service.sop_classes.extend(uids)
        return service
    return augemnt


def store_in_file(service):
    service.store_in_file = True
    return service


class MessageDispatcher(object):
    message_to_method = {
        0x0001: 'c_store',
        0x0020: 'c_find',
        0x0010: 'c_get',
        0x0021: 'c_move',
        0x0030: 'c_echo',
        0x0100: 'n_event_report',
        0x0110: 'n_get',
        0x0120: 'n_set',
        0x0130: 'n_action',
        0x0140: 'n_create',
        0x0150: 'n_delete',
    }

    def get_method(self, msg):
        try:
            name = self.message_to_method[msg.command_field]
            return getattr(self, name)
        except KeyError:
            raise exceptions.DIMSEProcessingError('Unknown message type')
        except AttributeError:
            raise exceptions.DIMSEProcessingError(
                'Message type is not supported by service class')


class MessageDispatcherSCU(MessageDispatcher):
    def __call__(self, asce, ctx, msg, *args, **kwargs):
        method = self.get_method(msg)
        return method(asce, ctx, msg, *args, **kwargs)


class MessageDispatcherSCP(MessageDispatcher):
    def __call__(self, asce, ctx, msg):
        method = self.get_method(msg)
        return method(asce, ctx, msg)


@sop_classes([VERIFICATION_SOP_CLASS])
def verification_scu(asce, ctx, msg_id):
    """Sends verification request and returns it's status result

    :param msg_id: message ID
    :return: status in response message. `SUCCESS` if verification was
             successfully completed.
    """
    c_echo = dimsemessages.CEchoRQMessage()
    c_echo.message_id = msg_id
    c_echo.sop_class_uid = ctx.sop_class

    asce.send(c_echo, ctx.id)

    response, msg_id = asce.receive()
    return code_to_status(response.status)


@sop_classes([VERIFICATION_SOP_CLASS])
def verification_scp(asce, ctx, msg):
    """Process received C-ECHO.

    Method delegates actual handling of C-ECHO to AE instance by calling
    its `on_receive_echo` method and expecting response status from it.

    :param msg: incoming C-ECHO message
    """
    try:
        status = asce.ae.on_receive_echo(ctx)
    except exceptions.EventHandlingError:
        status = UNABLE_TO_PROCESS

    rsp = dimsemessages.CEchoRSPMessage()
    rsp.message_id_being_responded_to = msg.message_id
    rsp.status = status
    asce.send(rsp, ctx.id)


STORAGE_SOP_CLASSES = [
    MR_IMAGE_STORAGE_SOP_CLASS, CT_IMAGE_STORAGE_SOP_CLASS,
    PET_IMAGE_STORAGE_SOP_CLASS, CR_IMAGE_STORAGE_SOP_CLASS,
    SC_IMAGE_STORAGE_SOP_CLASS, RT_IMAGE_STORAGE_SOP_CLASS,
    RT_DOSE_STORAGE_SOP_CLASS, RT_STRUCTURE_SET_STORAGE_SOP_CLASS,
    RT_PLAN_STORAGE_SOP_CLASS, SPATIAL_REGISTRATION_SOP_CLASS,
    ENHANCED_SR_SOP_CLASS, XRAY_RADIATION_DOSE_SR_SOP_CLASS,
    DX_IMAGE_STORAGE_FOR_PRESENTATION_SOP_CLASS,
    DX_IMAGE_STORAGE_FOR_PROCESSING_SOP_CLASS,
    MG_IMAGE_STORAGE_FOR_PRESENTATION_SOP_CLASS,
    MG_IMAGE_STORAGE_FOR_PROCESSING_SOP_CLASS,
    IO_IMAGE_STORAGE_FOR_PRESENTATION_SOP_CLASS,
    IO_IMAGE_STORAGE_FOR_PROCESSING_SOP_CLASS, XA_IMAGE_STORAGE_SOP_CLASS,
    ENHANCED_XA_IMAGE_STORAGE_SOP_CLASS, RF_IMAGE_STORAGE_SOP_CLASS,
    ENHANCED_RF_IMAGE_STORAGE_SOP_CLASS, ENHANCED_CT_IMAGE_STORAGE_SOP_CLASS,
    NM_IMAGE_STORAGE_SOP_CLASS, BASIC_TEXT_SR_STORAGE, ENHANCED_SR_STORAGE,
    COMPREHENSIVE_SR_STORAGE
]


@sop_classes(STORAGE_SOP_CLASSES)
def storage_scu(asce, ctx, dataset, msg_id):
    """SCU role implementation.

    :param dataset: dataset that should be sent via Storage service
    :param msg_id: message identifier
    :return: status code when dataset is stored.
    """
    c_store = dimsemessages.CStoreRQMessage()
    c_store.message_id = msg_id
    c_store.priority = dimsemessages.PRIORITY_MEDIUM

    if isinstance(dataset, (str, unicode)):
        # Got file name
        with open(dataset, 'rb') as ds:
            read_preamble(ds, False)
            meta = _read_file_meta_info(ds)
            c_store.sop_class_uid = meta.MediaStorageSOPClassUID
            c_store.affected_sop_instance_uid = meta.MediaStorageSOPInstanceUID
            c_store.data_set = ds
            asce.send(c_store, ctx.id)
    else:
        # Assume it's dataset object
        c_store.sop_class_uid = dataset.SOPClassUID
        c_store.affected_sop_instance_uid = dataset.SOPInstanceUID
        ds = dsutils.encode(dataset, ctx.supported_ts.is_implicit_VR,
                            ctx.supported_ts.is_little_endian)
        c_store.data_set = ds
        # send c_store request
        asce.send(c_store, ctx.id)

    # wait for c-store response
    response, _ = asce.receive()
    return code_to_status(response.status)


@store_in_file
@sop_classes(STORAGE_SOP_CLASSES)
def storage_scp(asce, ctx, msg):
    """SCP role implementation.

    Service extracts dataset from received message and passes it to
    `on_receive_store` method of the application entity.

    :param msg: received message
    """
    try:
        status = asce.ae.on_receive_store(ctx, msg.data_set)
    except exceptions.EventHandlingError:
        status = CANNOT_UNDERSTAND
    finally:
        if msg.data_set:
            msg.data_set.close()
    # make response
    rsp = dimsemessages.CStoreRSPMessage()
    rsp.message_id_being_responded_to = msg.message_id
    rsp.affected_sop_instance_uid = msg.affected_sop_instance_uid
    rsp.sop_class_uid = msg.sop_class_uid
    rsp.status = int(status)
    asce.send(rsp, ctx.id)


FIND_SOP_CLASSES = [PATIENT_ROOT_FIND_SOP_CLASS, STUDY_ROOT_FIND_SOP_CLASS]
                    #PATIENT_STUDY_ONLY_FIND_SOP_CLASS


@sop_classes(FIND_SOP_CLASSES)
def qr_find_scu(asce, ctx, ds, msg_id):
    """SCU role is implement as iterator that returns responses from remote
    AE.

    Method yields dataset and status for each one received from server.
    If status changes from 'Pending' iteration stops.

    :param ds: dataset that is passed to remote AE with C-FIND command
    :param msg_id: message identifier
    """
    c_find = dimsemessages.CFindRQMessage()
    c_find.message_id = msg_id
    c_find.sop_class_uid = ctx.sop_class
    c_find.priority = dimsemessages.PRIORITY_MEDIUM
    c_find.data_set = dsutils.encode(ds,
                                     ctx.supported_ts.is_implicit_VR,
                                     ctx.supported_ts.is_little_endian)

    # send c-find request
    asce.send(c_find, ctx.id)
    while True:
        response, _ = asce.receive()
        if response.data_set:
            data_set = dsutils.decode(response.data_set,
                                      ctx.supported_ts.is_implicit_VR,
                                      ctx.supported_ts.is_little_endian)
        else:
            data_set = None
        status = code_to_status(response.status)
        yield data_set, status
        if status.status_type != 'Pending':
            break


@sop_classes(FIND_SOP_CLASSES)
def qr_find_scp(asce, ctx, msg):
    """SCP role implementation.

    Method calls `on_receive_find` from AE with received C-FIND parameters
    and expect generator that would yield dataset responses for
    C-FIND command.

    :param msg: received C-FIND message
    """
    ds = dsutils.decode(msg.data_set, ctx.supported_ts.is_implicit_VR,
                        ctx.supported_ts.is_little_endian)

    # make response
    rsp = dimsemessages.CFindRSPMessage()
    rsp.message_id_being_responded_to = msg.message_id
    rsp.sop_class_uid = msg.sop_class_uid

    gen = asce.ae.on_receive_find(ctx, ds)
    for data_set, status in gen:
        rsp.status = int(status)
        rsp.data_set = dsutils.encode(data_set,
                                      ctx.supported_ts.is_implicit_VR,
                                      ctx.supported_ts.is_little_endian)
        asce.send(rsp, ctx.id)

    rsp = dimsemessages.CFindRSPMessage()
    rsp.message_id_being_responded_to = msg.message_id
    rsp.sop_class_uid = msg.sop_class_uid
    rsp.status = int(SUCCESS)
    asce.send(rsp, ctx.id)


GET_SOP_CLASSES = [PATIENT_ROOT_GET_SOP_CLASS, STUDY_ROOT_GET_SOP_CLASS,
                   PATIENT_STUDY_ONLY_GET_SOP_CLASS]


@sop_classes(GET_SOP_CLASSES)
def qr_get_scu(asce, ctx, ds, msg_id):
    def decode_ds(ds):
        return dsutils.decode(ds, ctx.supported_ts.is_implicit_VR,
                              ctx.supported_ts.is_little_endian)

    c_get = dimsemessages.CGetRQMessage()
    c_get.message_id = msg_id
    c_get.sop_class_uid = ctx.sop_class
    c_get.priority = dimsemessages.PRIORITY_MEDIUM
    c_get.data_set = dsutils.encode(ds,
                                    ctx.supported_ts.is_implicit_VR,
                                    ctx.supported_ts.is_little_endian)

    asce.send(c_get, ctx.id)
    while True:
        # receive c-store
        msg, pc_id = asce.receive()
        if msg.command_field == dimsemessages.CGetRSPMessage.command_field:
            if code_to_status(msg.status).status_type == 'Pending':
                pass  # pending. intermediate C-GET response
            else:
                break  # last answer
        elif (msg.command_field == dimsemessages.CStoreRQMessage.command_field):
            store_ctx = asce.ae.context_def_list[pc_id]
            in_file = store_ctx.sop_class in asce.ae.store_in_file

            rsp = dimsemessages.CStoreRSPMessage()
            rsp.message_id_being_responded_to = msg.message_id
            rsp.affected_sop_instance_uid = msg.affected_sop_instance_uid
            rsp.sop_class_uid = msg.sop_class_uid

            try:
                status = asce.ae.on_receive_store(ctx, msg.data_set)
                yield ctx, msg.data_set if in_file else decode_ds(msg.data_set)
            except exceptions.EventHandlingError:
                status = CANNOT_UNDERSTAND
            finally:
                if in_file and msg.data_set:
                    msg.data_set.close()

            rsp.status = int(status)
            asce.send(rsp, pc_id)


MOVE_SOP_CLASSES = [PATIENT_ROOT_MOVE_SOP_CLASS, STUDY_ROOT_MOVE_SOP_CLASS,
                    PATIENT_STUDY_ONLY_MOVE_SOP_CLASS]


@sop_classes(MOVE_SOP_CLASSES)
def qr_move_scu(asce, ctx, ds, dest_ae, msg_id):
    # build C-FIND primitive
    c_move = dimsemessages.CMoveRQMessage()
    c_move.message_id = msg_id
    c_move.sop_class_uid = ctx.sop_class
    c_move.move_destination = dest_ae
    c_move.priority = dimsemessages.PRIORITY_MEDIUM
    c_move.data_set = dsutils.encode(ds,
                                     ctx.supported_ts.is_implicit_VR,
                                     ctx.supported_ts.is_little_endian)
    # send c-find request
    asce.send(c_move, ctx.id)

    while 1:
        # wait for c-move responses
        response, _ = asce.receive()
        status = code_to_status(response.status).status_type
        if status != 'Pending':
            break
        yield status


@sop_classes(MOVE_SOP_CLASSES)
def qr_move_scp(asce, ctx, msg):
    ds = dsutils.decode(msg.data_set, ctx.supported_ts.is_implicit_VR,
                        ctx.supported_ts.is_little_endian)

    # make response
    rsp = dimsemessages.CMoveRSPMessage()
    rsp.message_id_being_responded_to = msg.message_id
    rsp.sop_class_uid = msg.sop_class_uid
    remote_ae, nop, gen = asce.ae.on_receive_move(ctx, ds,
                                                  msg.move_destination)
    if not nop:
        # nothing to move
        _send_response(asce, ctx, msg, 0, 0, 0, 0)

    with asce.ae.request_association(remote_ae) as assoc:
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
            asce.send(rsp, ctx.id)
        _send_response(asce, ctx, msg, nop, failed, warning, completed)


def _send_response(asce, ctx, msg, nop, failed, warning, completed):
    rsp = dimsemessages.CMoveRSPMessage()
    rsp.message_id_being_responded_to = msg.message_id
    rsp.sop_class_uid = msg.sop_class_uid
    rsp.num_of_remaining_sub_ops = nop - completed
    rsp.num_of_completed_sub_ops = completed
    rsp.num_of_failed_sub_ops = failed
    rsp.num_of_warning_sub_ops = warning
    rsp.status = int(SUCCESS)
    asce.send(rsp, ctx.id)


@sop_classes([MODALITY_WORK_LIST_INFORMATION_FIND_SOP_CLASS])
def modality_work_list_scu(asce, ctx, ds, msg_id):
    # build C-FIND primitive
    c_find = dimsemessages.CFindRQMessage()
    c_find.message_id = msg_id
    c_find.sop_class_uid = ctx.sop_class
    c_find.priority = dimsemessages.PRIORITY_MEDIUM
    c_find.data_set = dsutils.encode(ds,
                                     ctx.supported_ts.is_implicit_VR,
                                     ctx.supported_ts.is_little_endian)

    # send c-find request
    asce.send(c_find, ctx.id)
    while 1:
        # wait for c-find responses
        response, _ = asce.receive()
        d = dsutils.decode(response.data_set,
                           ctx.supported_ts.is_implicit_VR,
                           ctx.supported_ts.is_little_endian)
        status = code_to_status(response.status).status_type
        yield status, d
        if status != 'Pending':
            break


@sop_classes([MODALITY_WORK_LIST_INFORMATION_FIND_SOP_CLASS])
def modality_work_list_scp(asce, ctx, msg):
    ds = dsutils.decode(msg.data_set, ctx.supported_ts.is_implicit_VR,
                        ctx.supported_ts.is_little_endian)

    # make response
    rsp = dimsemessages.CFindRSPMessage()
    rsp.message_id_being_responded_to = msg.message_id
    rsp.sop_class_uid = msg.sop_class_uid

    gen = asce.ae.on_receive_find(ctx, ds)
    for identifier_ds, status in gen:
        rsp.status = int(status)
        rsp.data_set = dsutils.encode(identifier_ds,
                                      ctx.supported_ts.is_implicit_VR,
                                      ctx.supported_ts.is_little_endian)
        # send response
        asce.send(rsp, ctx.id)

    # send final response
    rsp = dimsemessages.CFindRSPMessage()
    rsp.message_id_being_responded_to = msg.message_id
    rsp.sop_class_uid = msg.sop_class_uid
    rsp.status = int(SUCCESS)
    asce.send(rsp, ctx.id)


STORAGE_COMMITMENT_PUSH_MODEL_SOP_CLASS = '1.2.840.10008.1.20.1.1'


class StorageCommitment(MessageDispatcherSCP):
    sop_classes = [STORAGE_COMMITMENT_SOP_CLASS]

    PROCESSING_FAILURE = 0x0110
    NO_SUCH_OBJECT_INSTANCE = 0x0112
    RESOURCE_LIMITATION = 0x0213
    REFERENCED_SOP_CLASS_NOT_SUPPORTED = 0x0122
    CLASS_OR_INSTANCE_CONFLICT = 0x0119
    DUPLICATE_TRANSACTION_UID = 0x0131

    def n_event_report(self, asce, ctx, msg):
        rsp = dimsemessages.NEventReportRSPMessage()
        rsp.sop_class_uid = ctx.sop_class
        rsp.status = int(SUCCESS)
        rsp.event_type_id = msg.event_type_id
        rsp.affected_sop_instance_uid = msg.affected_sop_instance_uid

        ds = dsutils.decode(msg.data_set, ctx.supported_ts.is_implicit_VR,
                            ctx.supported_ts.is_little_endian)
        transaction_uid = ds.TransactionUID
        if hasattr(ds, 'ReferencedSOPSequence'):
            success = ((item.ReferencedSOPClassUID,
                        item.ReferencedSOPInstanceUID)
                       for item in ds.ReferencedSOPSequence)
        else:
            success = []

        if hasattr(ds, 'FailedSOPSequence'):
            failure = ((item.ReferencedSOPClassUID,
                        item.ReferencedSOPInstanceUID,
                        item.FailureReason)
                       for item in ds.FailedSOPSequence)
        else:
            failure = []
        try:
            asce.ae.on_commitment_response(transaction_uid, success, failure)
        except exceptions.EventHandlingError:
            rsp.status = int(UNABLE_TO_PROCESS)
        else:
            asce.send(rsp, ctx.id)

    def n_action(self, asce, ctx, msg):
        instance_uid = STORAGE_COMMITMENT_PUSH_MODEL_SOP_CLASS
        rsp = dimsemessages.NActionRSPMessage()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.action_type_id = 1
        rsp.sop_class_uid = ctx.sop_class
        rsp.affected_sop_instance_uid = instance_uid
        ds = dsutils.decode(msg.data_set, ctx.supported_ts.is_implicit_VR,
                            ctx.supported_ts.is_little_endian)
        uids = ((item.ReferencedSOPClassUID, item.ReferencedSOPInstanceUID)
                for item in ds.ReferencedSOPSequence)
        try:
            remote_ae, success, failure = asce.ae.on_commitment_request(
                asce.remote_ae, uids
            )
        except exceptions.EventHandlingError:
            rsp.status = int(UNABLE_TO_PROCESS)
            asce.send(rsp, ctx.id)
        else:
            rsp.status = int(SUCCESS)
            asce.send(rsp, ctx.id)

            report = dimsemessages.NEventReportRQMessage()
            report.sop_class_uid = ctx.sop_class
            report.affected_sop_instance_uid = instance_uid
            report.event_type_id = 2 if failure else 1

            report_ds = dicom.dataset.Dataset()
            report_ds.TransactionUID = ds.TransactionUID
            if success:
                seq = []
                for sop_class_uid, sop_instance_uid in success:
                    ref = dicom.dataset.Dataset()
                    ref.ReferencedSOPClassUID = sop_class_uid
                    ref.ReferencedSOPInstanceUID = sop_instance_uid
                    seq.append(ref)
                report_ds.ReferencedSOPSequence = dicom.sequence.Sequence(seq)

            if failure:
                seq = []
                for sop_class_uid, sop_instance_uid, reason in failure:
                    ref = dicom.dataset.Dataset()
                    ref.ReferencedSOPClassUID = sop_class_uid
                    ref.ReferencedSOPInstanceUID = sop_instance_uid
                    ref.FailureReason = reason
                    seq.append(ref)
                report_ds.FailedSOPSequence = dicom.sequence.Sequence(seq)

            report.data_set = dsutils.encode(report_ds,
                                             ctx.supported_ts.is_implicit_VR,
                                             ctx.supported_ts.is_little_endian)

            with asce.ae.request_association(remote_ae) as assoc:
                assoc.send(report, ctx.id)
                assoc.receive()  # Get response. Current implementation ignores
                                 # it


@sop_classes([STORAGE_COMMITMENT_SOP_CLASS])
def storage_commitment_scu(asce, ctx, transaction_uid, uids, msg_id):
    rq = dimsemessages.NActionRQMessage()
    rq.message_id = msg_id
    rq.action_type_id = 1
    rq.sop_class_uid = ctx.sop_class
    rq.requested_sop_instance_uid = STORAGE_COMMITMENT_PUSH_MODEL_SOP_CLASS

    ds = dicom.dataset.Dataset()
    ds.TransactionUID = transaction_uid
    seq = []
    for sop_class_uid, sop_instance_uid in uids:
        ref = dicom.dataset.Dataset()
        ref.ReferencedSOPClassUID = sop_class_uid
        ref.ReferencedSOPInstanceUID = sop_instance_uid
        seq.append(ref)

    ds.ReferencedSOPSequence = dicom.sequence.Sequence(seq)

    rq.data_set = dsutils.encode(ds, ctx.supported_ts.is_implicit_VR,
                                 ctx.supported_ts.is_little_endian)
    asce.send(rq, ctx.id)

    rsp, _ = asce.receive()
    return code_to_status(rsp.status)