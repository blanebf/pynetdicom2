# Copyright (c) 2021 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

"""
In this module you can find classes that implements DIMSE-C and DIMSE-N messages
as they are described in PS3.7 Sections 9 (DIMSE-C) and 10 (DIMSE-N).

.. note::

    Please note, that in this version of the library message classes does not
    provide any form of validation for required and conditional fields. If your
    service class requires such validation you are responsible for implementing
    one.
    Service classes implementations provided in :doc:`sopclasses` do not expose
    messages to the user (aside from C-MOVE SCU, but it only yields received
    message). With that said if you are using services from this library you
    should not worry about any kind of message validation.
"""
from __future__ import absolute_import

import struct
from typing import Iterator, Tuple, IO, Union

from six.moves import range  # type: ignore
from pydicom.dataset import Dataset

from . import dsutils
from . import pdu

NO_DATASET = 0x0101

PRIORITY_LOW = 0x0002
PRIORITY_MEDIUM = 0x0000
PRIORITY_HIGH = 0x0001


def value_or_none(elem):
    """Gets element value or returns None, if element is None

    :param elem: dataset element or None
    :return: element value or None
    """
    return elem.value if elem else None


def chunks(seq, size):
    """Breaks a sequence of bytes into chunks of provided size

    :param seq: sequence of bytes
    :param size: chunk size
    :return: generator that yields tuples of sequence chunk and boolean that indicates if chunk is
             the last one
    """
    length = len(seq)
    return ((seq[pos:pos + size], (pos + size < length))
            for pos in range(0, length, size))


def fragment(data_set, max_pdu_length, normal, last):
    # type: (bytes,int,int,int) -> Iterator[Tuple[bytes,int]]
    """Fragmets dataset byte stream into chunks

    :param data_set: dataset bytes stream
    :type data_set: bytes
    :param max_pdu_length: maximum PDU length
    :type max_pdu_length: int
    :param normal: regular chunk code
    :type normal: int
    :param last: last chunk code
    :type last: int
    :yield: tuple of bytes: fragment and its code
    :rtype: Tuple[bytes,int]
    """
    maxsize = max_pdu_length - 6
    for chunk, has_next in chunks(data_set, maxsize):
        yield chunk, normal if has_next else last


def fragment_file(fp, max_pdu_length, normal, last):
    # type: (IO[bytes],int,int,int) -> Iterator[Tuple[bytes,int]]
    """Fragmets dataset from a file-like object into chunks

    :param f: file-like object
    :type f: IO[bytes]
    :param max_pdu_length: maximum PDU length
    :type max_pdu_length: int
    :param normal: regular chunk code
    :type normal: int
    :param last: last chunk code
    :type last: int
    :yield: tuple of bytes: fragment and its code
    :rtype: Tuple[bytes,int]
    """
    maxsize = max_pdu_length - 6
    while True:
        chunk = fp.read(maxsize)
        if not chunk:
            break
        has_next = fp.read(1)
        if has_next:
            fp.seek(-1, 1)

        yield chunk, normal if has_next else last


def dimse_property(tag):
    """Creates property for DIMSE message using specified attribute tag

    :param tag: tuple with group and element numbers
    :return: property that gets/sets value in command dataset
    """

    def setter(self, value):
        self.command_set[tag].value = value
    return property(lambda self: value_or_none(self.command_set.get(tag)), setter)


class StatusMixin(object):  # pylint: disable=too-few-public-methods
    """Helper mixin that defines common `status` property in provided
    DIMSE message class.

    This property is usually found in response messages.
    """
    status = dimse_property((0x0000, 0x0900))


class PriorityMixin(object):  # pylint: disable=too-few-public-methods
    """Helper mixin that defines common `priority` property in provided
    DIMSE message class.

    This property is usually found in request messages
    """
    priority = dimse_property((0x0000, 0x0700))


class DIMSEMessage(object):
    """Base DIMSE message class.

    This class is not used directly, rather its subclasses, that represent specific DIMSE messages
    are used.
    """
    command_field = None
    command_fields = []

    def __init__(self, command_set=None):
        # type: (Union[Dataset,None]) -> None
        self._data_set = None
        if command_set:
            self.command_set = command_set
        else:
            self.command_set = Dataset()
            self.command_set.CommandField = self.command_field
            self.command_set.CommandDataSetType = NO_DATASET
            for field in self.command_fields:
                setattr(self.command_set, field, '')

    sop_class_uid = dimse_property((0x0000, 0x0002))

    @property
    def data_set(self):
        """Dataset included with a DIMSE Message"""
        return self._data_set

    @data_set.setter
    def data_set(self, value):
        if value:
            self.command_set.CommandDataSetType = 0x0001
        self._data_set = value

    def encode(self, pc_id, max_pdu_length):
        # type: (int,int) -> Iterator[pdu.PDataTfPDU]
        """Returns the encoded message as a series of P-DATA-TF PDU objects.

        :param pc_id: Presentation Context ID
        :type pc_id: int
        :param max_pdu_length: maximum PDU length
        :type max_pdu_length: int
        :yield: P-DATA-TF PDUs
        :rtype: pdu.PDataTfPDU
        """
        encoded_command_set = dsutils.encode(self.command_set, True, True)

        # fragment command set
        for item, bit in fragment(encoded_command_set, max_pdu_length, 1, 3):
            # send only one pdv per p-data primitive
            value_item = pdu.PresentationDataValueItem(pc_id, struct.pack('b', bit) + item)
            yield pdu.PDataTfPDU([value_item])

        # fragment data set
        if self.data_set:
            if isinstance(self.data_set, bytes):
                # got dataset as byte array
                is_file = False
                gen = fragment(self.data_set, max_pdu_length, 0, 2)
            else:
                # assume that dataset is in file-like object
                is_file = True
                gen = fragment_file(self.data_set, max_pdu_length, 0, 2)
            try:
                for item, bit in gen:
                    value_item = pdu.PresentationDataValueItem(pc_id, struct.pack('b', bit) + item)
                    yield pdu.PDataTfPDU([value_item])
            finally:
                if is_file:
                    self.data_set.close()  # type: ignore

    def set_length(self):
        """Sets DIMSE message length attribute in command dataset"""
        it = (len(dsutils.encode_element(v, True, True))
              for v in list(self.command_set.values())[1:])
        self.command_set[(0x0000, 0x0000)].value = sum(it)

    def __repr__(self):
        return str(self.command_set) + '\n'


class DIMSERequestMessage(DIMSEMessage):
    """Base class for all DIMSE request messages"""
    message_id = dimse_property((0x0000, 0x0110))


class DIMSEResponseMessage(DIMSEMessage):
    """Base class for all DIMSE response messages"""
    message_id_being_responded_to = dimse_property((0x0000, 0x0120))


class CEchoRQMessage(DIMSERequestMessage):
    """C-ECHO-RQ Message.

    Complete definition can be found in DICOM PS3.7, 9.3.5.1 C-ECHO-RQ
    """

    command_field = 0x0030
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message.
    The value of this field shall be set to 0030H for the C-ECHO-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID', 'MessageID']


class CEchoRSPMessage(DIMSEResponseMessage, StatusMixin):
    """C-ECHO-RSP Message.

    Complete definition can be found in DICOM PS3.7, 9.3.5.5 C-ECHO-RSP
    """

    command_field = 0x8030
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message.
    The value of this field shall be set to 8030H for the C-ECHO-RSP Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status']


class CStoreRQMessage(DIMSERequestMessage, PriorityMixin):
    """C-STORE-RQ Message.

    Complete definition can be found in DICOM PS3.7, 9.3.1.1 C-STORE-RQ
    """

    command_field = 0x0001
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message.
    The value of this field shall be set to 0001H for the C-STORE-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageID', 'Priority', 'AffectedSOPInstanceUID',
                      'MoveOriginatorApplicationEntityTitle',
                      'MoveOriginatorMessageID']
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    """
    Contains the UID of the SOP Instance to be stored.
    """

    move_originator_aet = dimse_property((0x0000, 0x1030))
    """
    Contains the DICOM AE Title of the DICOM AE that invoked the C-MOVE operation from
    which this C-STORE sub-operation is being performed.
    """

    move_originator_message_id = dimse_property((0x0000, 0x1031))
    """
    Contains the Message ID (0000,0110) of the C-MOVE-RQ Message from which this C-STORE
    sub-operations is being performed.
    """


class CStoreRSPMessage(DIMSEResponseMessage, StatusMixin):
    """C-STORE-RSP Message.

    Complete definition can be found in DICOM PS3.7, 9.3.1.2 C-STORE-RSP
    """

    command_field = 0x8001
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message. The value of this
    field shall be set to 8001H for the C-STORE-RSP Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'AffectedSOPInstanceUID']

    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    """
    Contains the UID of the SOP Instance stored.
    """


class CFindRQMessage(DIMSERequestMessage, PriorityMixin):
    """C-FIND-RQ Message.

    Complete definition can be found in DICOM PS3.7, 9.3.2.1 C-FIND-RQ
    """

    command_field = 0x0020
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message. The value of this
    field shall be set to 0020H for the C-FIND-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID', 'MessageID',
                      'Priority']


class CFindRSPMessage(DIMSEResponseMessage, StatusMixin):
    """C-FIND-RSP Message.

    Complete definition can be found in DICOM PS3.7, 9.3.2.2 C-FIND-RSP
    """

    command_field = 0x8020
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message. The value of this
    field shall be set to 8020H for the C-FIND-RSP Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status']


class CGetRQMessage(DIMSERequestMessage, PriorityMixin):
    """C-GET-RQ Message.

    Complete definition can be found in DICOM PS3.7, 9.3.3.1 C-GET-RQ
    """

    command_field = 0x0010
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message. The value of this
    field shall be set to 0010H for the C-GET-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID', 'MessageID',
                      'Priority']


class CGetRSPMessage(DIMSEResponseMessage, StatusMixin):
    """C-GET-RSP Message.

    Complete definition can be found in DICOM PS3.7, 9.3.3.2 C-GET-RSP
    """

    command_field = 0x8010
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message. The value of this
    field shall be set to 0010H for the C-GET-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'NumberOfRemainingSuboperations',
                      'NumberOfCompletedSuboperations',
                      'NumberOfFailedSuboperations',
                      'NumberOfWarningSuboperations']

    num_of_remaining_sub_ops = dimse_property((0x0000, 0x1020))
    """
    The number of remaining C-STORE sub-operations to be invoked for this C-GET operation.
    """

    num_of_completed_sub_ops = dimse_property((0x0000, 0x1021))
    """
    The number of C-STORE sub-operations invoked by this C-GET operation that have completed
    successfully.
    """

    num_of_failed_sub_ops = dimse_property((0x0000, 0x1022))
    """
    The number of C-STORE sub-operations invoked by this C-GET operation that have failed.
    """

    num_of_warning_sub_ops = dimse_property((0x0000, 0x1023))
    """
    The number of C-STORE sub-operations invoked by this C-GET operation that generated warning
    responses.
    """


class CMoveRQMessage(DIMSERequestMessage, PriorityMixin):
    """C-MOVE-RQ Message.

    Complete definition can be found in DICOM PS3.7, 9.3.4.1 C-MOVE-RQ
    """

    command_field = 0x0021
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message. The value of this
    field shall be set to 0021H for the C-MOVE-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageID', 'Priority', 'MoveDestination']

    move_destination = dimse_property((0x0000, 0x0600))
    """
    Shall be set to the DICOM AE Title of the destination DICOM AE to which the C-STORE
    sub-operations are being performed.
    """


class CMoveRSPMessage(DIMSEResponseMessage, StatusMixin):
    """C-MOVE-RSP Message.

    Complete definition can be found in DICOM PS3.7, 9.3.4.2 C-MOVE-RSP
    """

    command_field = 0x8021
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message. The value of this
    field shall be set to 8021H for the C-MOVE-RSP Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'NumberOfRemainingSuboperations',
                      'NumberOfCompletedSuboperations',
                      'NumberOfFailedSuboperations',
                      'NumberOfWarningSuboperations']

    num_of_remaining_sub_ops = dimse_property((0x0000, 0x1020))
    """
    The number of remaining sub-operations to be invoked for this C-MOVE operation.
    """

    num_of_completed_sub_ops = dimse_property((0x0000, 0x1021))
    """
    The number of C-STORE sub-operations invoked by this C-MOVE operation that have
    completed successfully.
    """

    num_of_failed_sub_ops = dimse_property((0x0000, 0x1022))
    """
    The number of C-STORE sub-operations invoked by this C-MOVE operation that have failed.
    """

    num_of_warning_sub_ops = dimse_property((0x0000, 0x1023))
    """
    The number of C-STORE sub-operations invoked by this C-MOVE operation that generated
    warning responses.
    """


class CCancelRQMessage(DIMSEResponseMessage):
    """C-CANCEL-FIND-RQ, C-CANCEL-GET-RQ, C-CANCEL-MOVE-RQ Messages.

    Complete definition can be found in:

        * DICOM PS3.7, 9.3.2.3 C-CANCEL-FIND-RQ
        * DICOM PS3.7, 9.3.3.3 C-CANCEL-GET-RQ
        * DICOM PS3.7, 9.3.4.3 C-CANCEL-MOVE-RQ
    """
    command_field = 0x0FFF
    """
    This field distinguishes the DIMSE-C operation conveyed by this Message. The value of this
    field shall be set to 0FFFH for the C-CANCEL-MOVE-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'MessageIDBeingRespondedTo']


class NEventReportRQMessage(DIMSERequestMessage):
    """N-EVENT-REPORT-RQ Message.

    Complete definition can be found in DICOM PS3.7, 10.3.1.1 N-EVENT-REPORT-RQ
    """

    command_field = 0x0100
    """
    This field distinguishes the DIMSE-N notification conveyed by this Message. The value of this
    field shall be set to 0100H for the N-EVENT-REPORT-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID', 'MessageID',
                      'AffectedSOPInstanceUID', 'EventTypeID']

    event_type_id = dimse_property((0x0000, 0x1002))
    """
    Values for this field are application-specific.
    """

    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    """
    Contains the UID of the SOP Instance for which this event occurred.
    """


class NEventReportRSPMessage(DIMSEResponseMessage, StatusMixin):
    """N-EVENT-REPORT-RSP Message.

    Complete definition can be found in DICOM PS3.7, 10.3.1.2 N-EVENT-REPORT-RSP
    """

    command_field = 0x8100
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 8100H for the N-EVENT-REPORT-RSP Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo',
                      'Status', 'AffectedSOPInstanceUID', 'EventTypeID']

    event_type_id = dimse_property((0x0000, 0x1002))
    """
    Values for this field are application-specific.
    """

    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    """
    Contains the UID of the SOP Instance for which this event occurred.
    """


class NGetRQMessage(DIMSERequestMessage):
    """N-GET-RQ Message.

    Complete definition can be found in DICOM PS3.7, 10.3.2.1 N-GET-RQ
    """

    command_field = 0x0110
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 0110H for the N-GET-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'RequestedSOPClassUID', 'MessageID',
                      'RequestedSOPInstanceUID', 'AttributeIdentifierList']

    sop_class_uid = dimse_property((0x0000, 0x0003))

    requested_sop_instance_uid = dimse_property((0x0000, 0x1001))
    """
    Contains the UID of the SOP Instance for which Attribute Values are to be retrieved.
    """

    attribute_identifier_list = dimse_property((0x0000, 0x1005))
    """
    This field contains an Attribute Tag for each of the n Attributes applicable to the
    N-GET operation.
    """


class NGetRSPMessage(DIMSEResponseMessage, StatusMixin):
    """N-GET-RSP Message.

    Complete definition can be found in DICOM PS3.7, 10.3.2.2 N-GET-RSP
    """

    command_field = 0x8110
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 8110H for the N-GET-RSP Message.
    """

    command_fields = ['CommandGroupLength', 'MessageIDBeingRespondedTo',
                      'Status', 'AffectedSOPInstanceUID']

    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    """
    Contains the UID of the SOP Instance for which Attribute Values are returned.
    """


class NSetRQMessage(DIMSERequestMessage):
    """N-SET-RQ Message.

    Complete definition can be found in DICOM PS3.7, 10.3.3.1 N-SET-RQ
    """

    command_field = 0x0120
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 0120H for the N-SET-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'RequestedSOPClassUID',
                      'MessageID', 'RequestedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0003))

    requested_sop_instance_uid = dimse_property((0x0000, 0x1001))
    """
    Contains the UID of the SOP Instance for which Attribute values are to be modified.
    """


class NSetRSPMessage(DIMSEResponseMessage, StatusMixin):
    """N-SET-RSP Message.

    Complete definition can be found in DICOM PS3.7, 10.3.3.2 N-SET-RSP
    """

    command_field = 0x8120
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'AffectedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0002))
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 8120H for the N-SET-RSP Message.
    """

    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    """
    Contains the UID of the SOP Instance for which Attribute Values were modified.
    """


class NActionRQMessage(DIMSERequestMessage):
    """N-ACTION-RQ Message.

    Complete definition can be found in DICOM PS3.7, 10.3.4.1 N-ACTION-RQ
    """

    command_field = 0x0130
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 0130H for the N-ACTION-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'RequestedSOPClassUID', 'MessageID',
                      'RequestedSOPInstanceUID', 'ActionTypeID']

    sop_class_uid = dimse_property((0x0000, 0x0003))

    requested_sop_instance_uid = dimse_property((0x0000, 0x1001))
    """
    Contains the UID of the SOP Instance for which the action is to be performed.
    """

    action_type_id = dimse_property((0x0000, 0x1008))
    """
    Values for this field are application-specific.
    """


class NActionRSPMessage(DIMSEResponseMessage, StatusMixin):
    """N-ACTION-RSP Message.

    Complete definition can be found in DICOM PS3.7, 10.3.4.2 N-ACTION-RSP
    """

    command_field = 0x8130
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 8130H for the N-ACTION-RSP Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'AffectedSOPInstanceUID', 'ActionTypeID']

    sop_class_uid = dimse_property((0x0000, 0x0002))

    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    """
    Contains the UID of the SOP Instance for which the action was performed.
    """

    action_type_id = dimse_property((0x0000, 0x1008))
    """
    Values for this field are application-specific.
    """


class NCreateRQMessage(DIMSERequestMessage):
    """N-CREATE-RQ Message.

    Complete definition can be found in DICOM PS3.7, 10.3.5.1 N-CREATE-RQ
    """

    command_field = 0x0140
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 0140H for the N-CREATE-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID', 'MessageID',
                      'AffectedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0002))

    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    """
    Contains the UID of the SOP Instance to be created.
    """


class NCreateRSPMessage(DIMSEResponseMessage, StatusMixin):
    """N-CREATE-RSP Message.

    Complete definition can be found in DICOM PS3.7, 10.3.5.2 N-CREATE-RSP
    """

    command_field = 0x8140
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 8140H for the N-CREATE-RSP Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'AffectedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0002))

    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    """
    Contains the UID of the SOP Instance that was created.
    """


class NDeleteRQMessage(DIMSERequestMessage):
    """N-DELETE-RQ Message.

    Complete definition can be found in DICOM PS3.7, 10.3.6.1 N-DELETE-RQ
    """

    command_field = 0x0150
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 0150H for the N-DELETE-RQ Message.
    """

    command_fields = ['CommandGroupLength', 'RequestedSOPClassUID', 'MessageID',
                      'RequestedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0003))

    requested_sop_instance_uid = dimse_property((0x0000, 0x1001))
    """
    Contains the UID of the SOP Instance to be deleted.
    """


class NDeleteRSPMessage(DIMSEResponseMessage, StatusMixin):
    """N-DELETE-RSP Message.

    Complete definition can be found in DICOM PS3.7, 10.3.6.2 N-DELETE-RSP
    """

    command_field = 0x8150
    """
    This field distinguishes the DIMSE-N operation conveyed by this Message. The value of this
    field shall be set to 8150H for the N-DELETE-RSP Message.
    """

    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'AffectedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0002))

    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    """
    Contains the UID of the SOP Instance that was deleted.
    """


MESSAGE_TYPE = {
    0x0001: CStoreRQMessage,
    0x8001: CStoreRSPMessage,
    0x0020: CFindRQMessage,
    0x8020: CFindRSPMessage,
    0x0FFF: CCancelRQMessage,
    0x0010: CGetRQMessage,
    0x8010: CGetRSPMessage,
    0x0021: CMoveRQMessage,
    0x8021: CMoveRSPMessage,
    0x0030: CEchoRQMessage,
    0x8030: CEchoRSPMessage,
    0x0100: NEventReportRQMessage,
    0x8100: NEventReportRSPMessage,
    0x0110: NGetRQMessage,
    0x8110: NGetRSPMessage,
    0x0120: NSetRQMessage,
    0x8120: NSetRSPMessage,
    0x0130: NActionRQMessage,
    0x8130: NActionRSPMessage,
    0x0140: NCreateRQMessage,
    0x8140: NCreateRSPMessage,
    0x0150: NDeleteRQMessage,
    0x8150: NDeleteRSPMessage
}
