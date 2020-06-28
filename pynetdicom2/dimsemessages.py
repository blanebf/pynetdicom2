# Copyright (c) 2014 Pavel 'Blane' Tuchin
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

from six.moves import range

from . import dsutils
from . import pdu

try:
    from pydicom.dataset import Dataset
except ImportError:
    from dicom.dataset import Dataset

    import dicom._dicom_dict as dicomdict
    import dicom.datadict

    #  pydicom's dictionary misses command tags. Add them.
    dicomdict.DicomDictionary.update({
        0x00000000: ('UL', '1', 'Command Group Length', '', 'CommandGroupLength'),
        0x00000002: ('UI', '1', 'Affected SOP Class UID', '',
                     'AffectedSOPClassUID'),
        0x00000003: ('UI', '1', 'Requested SOP Class UID', '',
                     'RequestedSOPClassUID'),
        0x00000100: ('US', '1', 'Command Field', '', 'CommandField'),
        0x00000110: ('US', '1', 'Message ID', '', 'MessageID'),
        0x00000120: ('US', '1', 'Message ID Being Responded To', '',
                     'MessageIDBeingRespondedTo'),
        0x00000600: ('AE', '1', 'Move Destination', '', 'MoveDestination'),
        0x00000700: ('US', '1', 'Priority', '', 'Priority'),
        0x00000800: ('US', '1', 'DataSet Type', '', 'CommandDataSetType'),
        0x00000900: ('US', '1', 'Status', '', 'Status'),
        0x00000901: ('AT', '1', 'Offending Element', '', 'OffendingElement'),
        0x00000902: ('LO', '1', 'Error Comment', '', 'ErrorComment'),
        0x00000903: ('US', '1', 'Error ID', '', 'ErrorID'),
        0x00001000: ('UI', '1', 'Affected SOP Instance UID', '',
                     'AffectedSOPInstanceUID'),
        0x00001001: ('UI', '1', 'Requested SOP Instance UID', '',
                     'RequestedSOPInstanceUID'),
        0x00001002: ('US', '1', 'Event Type ID', '', 'EventTypeID'),
        0x00001005: ('AT', '1', 'Attribute Identifier List', '',
                     'AttributeIdentifierList'),
        0x00001008: ('US', '1', 'Action Type ID', '', 'ActionTypeID'),
        0x00001020: ('US', '1', 'Number Of Remaining Sub-operations', '',
                     'NumberOfRemainingSuboperations'),
        0x00001021: ('US', '1', 'Number Of Completed Sub-operations', '',
                     'NumberOfCompletedSuboperations'),
        0x00001022: ('US', '1', 'Number Of Failed Sub-operations', '',
                     'NumberOfFailedSuboperations'),
        0x00001023: ('US', '1', 'Number Of Warning Sub-operations', '',
                     'NumberOfWarningSuboperations'),
        0x00001030: ('AE', '1', 'Move Originator Application Entity Title', '',
                     'MoveOriginatorApplicationEntityTitle'),
        0x00001031: ('US', '1', 'Move Originator Message ID', '',
                     'MoveOriginatorMessageID'),
    })
    dicom.datadict.keyword_dict = dict(
        [(dicom.datadict.dictionary_keyword(tag), tag)
         for tag in dicomdict.DicomDictionary])


NO_DATASET = 0x0101

PRIORITY_LOW = 0x0002
PRIORITY_MEDIUM = 0x0000
PRIORITY_HIGH = 0x0001


def value_or_none(elem):
    return elem.value if elem else None


def chunks(seq, size):
    l = len(seq)
    return ((seq[pos:pos + size], True if pos + size < l else False)
            for pos in range(0, l, size))


def fragment(data_set, max_pdu_length, normal, last):
    maxsize = max_pdu_length - 6
    for chunk, has_next in chunks(data_set, maxsize):
        yield chunk, normal if has_next else last


def fragment_file(f, max_pdu_length, normal, last):
    maxsize = max_pdu_length - 6
    while True:
        chunk = f.read(maxsize)
        if not chunk:
            break
        has_next = f.read(1)
        if has_next:
            f.seek(-1, 1)

        yield chunk, normal if has_next else last


def dimse_property(tag):
    """Creates property for DIMSE message using specified attribute tag

    :param tag: tuple with group and element numbers
    :return: property that gets/sets value in command dataset
    """

    def setter(self, value):
        self.command_set[tag].value = value
    return property(lambda self: value_or_none(self.command_set.get(tag)),
                    setter)


def status_mixin(dimse_class):
    """Helper decorator that defines common `status` property in provided
    DIMSE message class.

    This property is usually found in response messages.

    :param dimse_class: DIMSE message class
    :return: DIMSE message class with defined `status` property
    """
    dimse_class.status = dimse_property((0x0000, 0x0900))
    return dimse_class


def priority_mixin(dimse_class):
    """Helper decorator that defines common `priority` property in provided
    DIMSE message class.

    This property is usually found in request messages

    :param dimse_class: DIMSE message class
    :return: DIMSE message class with defined `priority` property
    """
    dimse_class.priority = dimse_property((0x0000, 0x0700))
    return dimse_class


class DIMSEMessage(object):
    command_field = None
    command_fields = []

    def __init__(self, command_set=None):
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
        return self._data_set

    @data_set.setter
    def data_set(self, value):
        if value:
            self.command_set.CommandDataSetType = 0x0001
        self._data_set = value

    def encode(self, pc_id, max_pdu_length):
        """Returns the encoded message as a series of P-DATA service
        parameter objects."""
        encoded_command_set = dsutils.encode(self.command_set, True, True)

        # fragment command set
        for item, bit in fragment(encoded_command_set, max_pdu_length, 1, 3):
            # send only one pdv per p-data primitive
            value_item = pdu.PresentationDataValueItem(
                pc_id, struct.pack('b', bit) + item)
            yield pdu.PDataTfPDU([value_item])

        # fragment data set
        if self.data_set:
            if isinstance(self.data_set, bytes):
                # got dataset as byte array
                gen = fragment(self.data_set, max_pdu_length, 0, 2)
            else:
                # assume that dataset is in file-like object
                gen = fragment_file(self.data_set, max_pdu_length, 0, 2)
            for item, bit in gen:
                value_item = pdu.PresentationDataValueItem(
                    pc_id, struct.pack('b', bit) + item)
                yield pdu.PDataTfPDU([value_item])

    def set_length(self):
        it = (len(dsutils.encode_element(v, True, True))
              for v in list(self.command_set.values())[1:])
        self.command_set[(0x0000, 0x0000)].value = sum(it)

    def __repr__(self):
        return str(self.command_set) + '\n'


class DIMSERequestMessage(DIMSEMessage):
    message_id = dimse_property((0x0000, 0x0110))


class DIMSEResponseMessage(DIMSEMessage):
    message_id_being_responded_to = dimse_property((0x0000, 0x0120))


class CEchoRQMessage(DIMSERequestMessage):
    command_field = 0x0030
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID', 'MessageID']


@status_mixin
class CEchoRSPMessage(DIMSEResponseMessage):
    command_field = 0x8030
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status']


@priority_mixin
class CStoreRQMessage(DIMSERequestMessage):
    command_field = 0x0001
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageID', 'Priority', 'AffectedSOPInstanceUID',
                      'MoveOriginatorApplicationEntityTitle',
                      'MoveOriginatorMessageID']
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    move_originator_aet = dimse_property((0x0000, 0x1030))
    move_originator_message_id = dimse_property((0x0000, 0x1031))


@status_mixin
class CStoreRSPMessage(DIMSEResponseMessage):
    command_field = 0x8001
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'AffectedSOPInstanceUID']
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))


@priority_mixin
class CFindRQMessage(DIMSERequestMessage):
    command_field = 0x0020
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID', 'MessageID',
                      'Priority']


@status_mixin
class CFindRSPMessage(DIMSEResponseMessage):
    command_field = 0x8020
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status']


@priority_mixin
class CGetRQMessage(DIMSERequestMessage):
    command_field = 0x0010
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID', 'MessageID',
                      'Priority']


@status_mixin
class CGetRSPMessage(DIMSEResponseMessage):
    command_field = 0x8010
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'NumberOfRemainingSuboperations',
                      'NumberOfCompletedSuboperations',
                      'NumberOfFailedSuboperations',
                      'NumberOfWarningSuboperations']
    num_of_remaining_sub_ops = dimse_property((0x0000, 0x1020))
    num_of_completed_sub_ops = dimse_property((0x0000, 0x1021))
    num_of_failed_sub_ops = dimse_property((0x0000, 0x1022))
    num_of_warning_sub_ops = dimse_property((0x0000, 0x1023))


@priority_mixin
class CMoveRQMessage(DIMSERequestMessage):
    command_field = 0x0021
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageID', 'Priority', 'MoveDestination']
    move_destination = dimse_property((0x0000, 0x0600))


@status_mixin
class CMoveRSPMessage(DIMSEResponseMessage):
    command_field = 0x8021
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'NumberOfRemainingSuboperations',
                      'NumberOfCompletedSuboperations',
                      'NumberOfFailedSuboperations',
                      'NumberOfWarningSuboperations']
    num_of_remaining_sub_ops = dimse_property((0x0000, 0x1020))
    num_of_completed_sub_ops = dimse_property((0x0000, 0x1021))
    num_of_failed_sub_ops = dimse_property((0x0000, 0x1022))
    num_of_warning_sub_ops = dimse_property((0x0000, 0x1023))


class CCancelRQMessage(DIMSEResponseMessage):
    command_field = 0x0FFF
    command_fields = ['CommandGroupLength', 'MessageIDBeingRespondedTo']


class NEventReportRQMessage(DIMSERequestMessage):
    command_field = 0x0100
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID', 'MessageID',
                      'AffectedSOPInstanceUID', 'EventTypeID']
    event_type_id = dimse_property((0x0000, 0x1002))
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))


@status_mixin
class NEventReportRSPMessage(DIMSEResponseMessage):
    command_field = 0x8100
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo',
                      'Status', 'AffectedSOPInstanceUID', 'EventTypeID']
    event_type_id = dimse_property((0x0000, 0x1002))
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))


class NGetRQMessage(DIMSERequestMessage):
    command_field = 0x0110
    command_fields = ['CommandGroupLength', 'RequestedSOPClassUID', 'MessageID',
                      'RequestedSOPInstanceUID', 'AttributeIdentifierList']
    sop_class_uid = dimse_property((0x0000, 0x0003))
    requested_sop_instance_uid = dimse_property((0x0000, 0x1001))
    attribute_identifier_list = dimse_property((0x0000, 0x1005))


@status_mixin
class NGetRSPMessage(DIMSEResponseMessage):
    command_field = 0x8110
    command_fields = ['CommandGroupLength', 'MessageIDBeingRespondedTo',
                      'Status', 'AffectedSOPInstanceUID']
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))


class NSetRQMessage(DIMSERequestMessage):
    command_field = 0x0120
    command_fields = ['CommandGroupLength', 'RequestedSOPClassUID',
                      'MessageID', 'RequestedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0003))
    requested_sop_instance_uid = dimse_property((0x0000, 0x1001))


@status_mixin
class NSetRSPMessage(DIMSEResponseMessage):
    command_field = 0x8120
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'AffectedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0002))
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))


class NActionRQMessage(DIMSERequestMessage):
    command_field = 0x0130
    command_fields = ['CommandGroupLength', 'RequestedSOPClassUID', 'MessageID',
                      'RequestedSOPInstanceUID', 'ActionTypeID']

    sop_class_uid = dimse_property((0x0000, 0x0003))
    requested_sop_instance_uid = dimse_property((0x0000, 0x1001))
    action_type_id = dimse_property((0x0000, 0x1008))


@status_mixin
class NActionRSPMessage(DIMSEResponseMessage):
    command_field = 0x8130
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'AffectedSOPInstanceUID', 'ActionTypeID']

    sop_class_uid = dimse_property((0x0000, 0x0002))
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))
    action_type_id = dimse_property((0x0000, 0x1008))


class NCreateRQMessage(DIMSERequestMessage):
    command_field = 0x0140
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID', 'MessageID',
                      'AffectedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0002))
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))


@status_mixin
class NCreateRSPMessage(DIMSEResponseMessage):
    command_field = 0x8140
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'AffectedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0002))
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))


class NDeleteRQMessage(DIMSERequestMessage):
    command_field = 0x0150
    command_fields = ['CommandGroupLength', 'RequestedSOPClassUID', 'MessageID',
                      'RequestedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0003))
    requested_sop_instance_uid = dimse_property((0x0000, 0x1001))


@status_mixin
class NDeleteRSPMessage(DIMSEResponseMessage):
    command_field = 0x8150
    command_fields = ['CommandGroupLength', 'AffectedSOPClassUID',
                      'MessageIDBeingRespondedTo', 'Status',
                      'AffectedSOPInstanceUID']

    sop_class_uid = dimse_property((0x0000, 0x0002))
    affected_sop_instance_uid = dimse_property((0x0000, 0x1000))


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
