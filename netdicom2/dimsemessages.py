#
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

"""
    All DIMSE Message classes implement the following methods:

      from_params(DIMSEServiceParameter)    :  Builds a DIMSE message from a
                                              DULServiceParameter
                                              object. Used when receiving
                                              primitives from the
                                              DIMSEServiceUser.
      to_params()                           :  Convert the Message into a
                                              DIMSEServiceParameter object.
                                              Used for sending primitives to
                                              the DIMSEServiceUser.
      encode()                             :  Returns the encoded message in
                                              one or several P-DATA parameters
                                              structure.
      decode(pdata)                        :  Construct the message from one
                                              or several P-DATA primitives

                          from_params               encode
  |----------------------| ------->  |----------| -------> |---------------|
  | Service parameters   |           |   DIMSE  |          |     P-DATA    |
  |      object          |           |  message |          |  primitive(s) |
  |______________________| <-------  |__________| <------- |_______________|
                           to_params                decode
"""

import logging
import struct

from dicom.dataset import Dataset
from dicom.UID import ImplicitVRLittleEndian

import netdicom2.dsutils as dsutils
import netdicom2.dimseparameters
import netdicom2.exceptions as exceptions
import netdicom2.pdu as pdu

from dicom._dicom_dict import DicomDictionary

logger = logging.getLogger(__name__)

#  pydicom's dictionnary misses command tags. Add them.
DicomDictionary.update({
    0x00000000: ('UL', '1', 'CommandGroupLength', ''),
    0x00000002: ('UI', '1', 'Affected SOP class', ''),
    0x00000003: ('UI', '1', 'RequestedSOPClassUID', ''),
    0x00000100: ('US', '1', 'CommandField', ''),
    0x00000110: ('US', '1', 'MessageID', ''),
    0x00000120: ('US', '1', 'MessageIDBeingRespondedTo', ''),
    0x00000600: ('AE', '1', 'MoveDestination', ''),
    0x00000700: ('US', '1', 'Priority', ''),
    0x00000800: ('US', '1', 'DataSetType', ''),
    0x00000900: ('US', '1', 'Status', ''),
    0x00000901: ('AT', '1', 'OffendingElement', ''),
    0x00000902: ('LO', '1', 'ErrorComment', ''),
    0x00000903: ('US', '1', 'ErrorID', ''),
    0x00001000: ('UI', '1', 'AffectedSOPInstanceUID', ''),
    0x00001001: ('UI', '1', 'RequestedSOPInstanceUID', ''),
    0x00001002: ('US', '1', 'EventTypeID', ''),
    0x00001005: ('AT', '1', 'AttributeIdentifierList', ''),
    0x00001008: ('US', '1', 'ActionTypeID', ''),
    0x00001020: ('US', '1', 'NumberOfRemainingSuboperations', ''),
    0x00001021: ('US', '1', 'NumberOfCompletedSuboperations', ''),
    0x00001022: ('US', '1', 'NumberOfFailedSuboperations', ''),
    0x00001023: ('US', '1', 'NumberOfWarningSuboperations', ''),
    0x00001030: ('AE', '1', 'MoveOriginatorApplicationEntityTitle', ''),
    0x00001031: ('US', '1', 'MoveOriginatorMessageID', ''),

})


def fragment(max_pdu_length, str_):
    s = str_
    fragments = []
    maxsize = max_pdu_length - 6
    while 1:
        fragments.append(s[:maxsize])
        s = s[maxsize:]
        if len(s) <= maxsize:
            if len(s) > 0:
                fragments.append(s)
            return fragments


class DIMSEMessage(object):
    command_fields = []

    def __init__(self):
        self.command_set = None
        self.encoded_data_set = None
        self.data_set = ''
        self.encoded_command_set = []
        self.id_ = None

        self.ts = ImplicitVRLittleEndian  # imposed by standard.
        if self.command_fields:
            self.command_set = Dataset()
            for field in self.command_fields:
                self.command_set.add_new(field[1], field[2], '')

    def encode(self, id_, max_pdu_length):
        """Returns the encoded message as a series of P-DATA service
        parameter objects."""
        self.id_ = id_
        p_datas = []
        encoded_command_set = dsutils.encode(self.command_set,
                                             self.ts.is_implicit_VR,
                                             self.ts.is_little_endian)

        # fragment command set
        pdvs = fragment(max_pdu_length, encoded_command_set)
        assert ''.join(pdvs) == encoded_command_set
        for pdv in pdvs[:-1]:
            # send only one pdv per p-data primitive
            value_item = pdu.PresentationDataValueItem(
                self.id_, struct.pack('b', 1) + pdv)
            p_datas.append(pdu.PDataTfPDU([value_item]))

        # last command fragment
        value_item = pdu.PresentationDataValueItem(
            self.id_, struct.pack('b', 3) + pdvs[-1])
        p_datas.append(pdu.PDataTfPDU([value_item]))

        # fragment data set
        if hasattr(self, 'data_set') and self.data_set is not None:
            pdvs = fragment(max_pdu_length, self.data_set)
            assert ''.join(pdvs) == self.data_set
            for pdv in pdvs[:-1]:
                value_item = pdu.PresentationDataValueItem(
                    self.id_, struct.pack('b', 0) + pdv)
                p_datas.append(pdu.PDataTfPDU([value_item]))
            # last data fragment
            value_item = pdu.PresentationDataValueItem(
                self.id_, struct.pack('b', 2) + pdvs[-1])
            p_datas.append(pdu.PDataTfPDU([value_item]))

        return p_datas

    def decode(self, p_data):
        """Constructs itself receiving a series of P-DATA primitives.
        Returns True when complete, False otherwise."""
        if not isinstance(p_data, pdu.PDataTfPDU):
            return False

        for value_item in p_data.data_value_items:
            # must be able to read P-DATA with several PDVs
            self.id_ = value_item.context_id
            marker = struct.unpack('b', value_item.data_value[0])[0]
            if marker in (1, 3):
                self.encoded_command_set.append(value_item.data_value[1:])
                if marker == 3:
                    self.command_set = dsutils.decode(
                        ''.join(self.encoded_command_set),
                        self.ts.is_implicit_VR, self.ts.is_little_endian)
                    self.encoded_data_set = []
                    self.__class__ = MESSAGE_TYPE[
                        self.command_set[(0x0000, 0x0100)].value]
                    if self.command_set[(0x0000, 0x0800)].value == 0x0101:
                        return True  # response: no dataset
            elif marker in (0, 2):
                self.data_set += value_item.data_value[1:]
                logger.debug('  data fragment %s', self.id_)
                if marker == 2:
                    logger.debug('  last data fragment %s', self.id_)
                    return True
            else:
                raise exceptions.DIMSEProcessingError(
                    'Incorrect first PDV byte')

        return False

    def set_length(self):
        it = (len(dsutils.encode_element(v, self.ts.is_implicit_VR,
                                         self.ts.is_little_endian))
              for v in self.command_set.values()[1:])
        self.command_set[(0x0000, 0x0000)].value = sum(it)

    def __repr__(self):
        return str(self.command_set) + '\n'


class CEchoRQMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Affected SOP Class UID', (0x0000, 0x0002), 'UI', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID', (0x0000, 0x0110), 'US', 1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1)]

    def from_params(self, params):
        self.command_set[(0x0000, 0x0002)].value = params.affected_sop_class_uid
        self.command_set[(0x0000, 0x0100)].value = 0x0030
        self.command_set[(0x0000, 0x0110)].value = params.message_id
        self.command_set[(0x0000, 0x0800)].value = 0x0101
        self.data_set = None
        self.set_length()

    def to_params(self):
        tmp = netdicom2.dimseparameters.CEchoServiceParameters()
        tmp.message_id = self.command_set.get((0x0000, 0x0110))
        tmp.affected_sop_class_uid = self.command_set.get((0x0000, 0x0002))
        return tmp


class CEchoRSPMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Affected SOP Class UID', (0x0000, 0x0002), 'UI', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID Being Responded To', (0x0000, 0x0120), 'US',
                       1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1),
                      ('Status', (0x0000, 0x0900), 'US', 1)]

    def from_params(self, params):
        if params.affected_sop_class_uid:
            self.command_set[
                (0x0000, 0x0002)].value = params.affected_sop_class_uid
        self.command_set[(0x0000, 0x0100)].value = 0x8030
        self.command_set[
            (0x0000, 0x0120)].value = params.message_id_being_responded_to
        self.command_set[(0x0000, 0x0800)].value = 0x0101
        self.command_set[(0x0000, 0x0900)].value = params.status
        self.set_length()

    def to_params(self):
        tmp = netdicom2.dimseparameters.CEchoServiceParameters()
        tmp.affected_sop_class_uid = self.command_set.get((0x0000, 0x0002))
        tmp.message_id_being_responded_to = self.command_set.get(
            (0x0000, 0x0120))
        tmp.status = 0
        return tmp


class CStoreRQMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Affected SOP Class UID', (0x0000, 0x0002), 'UI', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID', (0x0000, 0x0110), 'US', 1),
                      ('Priority', (0x0000, 0x0700), 'US', 1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1),
                      ('Affected SOP Instance UID', (0x0000, 0x1000), 'UI', 1),
                      ('Move Originator Application Entity Title',
                       (0x0000, 0x1030), 'AE', 1),
                      ('Move Originator Message ID', (0x0000, 0x1031), 'US', 1)]

    def from_params(self, params):
        self.command_set[(0x0000, 0x0002)].value = params.affected_sop_class_uid
        self.command_set[(0x0000, 0x0100)].value = 0x0001
        self.command_set[(0x0000, 0x0110)].value = params.message_id
        self.command_set[(0x0000, 0x0700)].value = params.priority
        self.command_set[(0x0000, 0x0800)].value = 0x0001
        self.command_set[
            (0x0000, 0x1000)].value = params.affected_sop_instance_uid
        if params.move_originator_application_entity_title:
            self.command_set[(0x0000,
                              0x1030)].value = params.move_originator_application_entity_title
        else:
            self.command_set[(0x0000, 0x1030)].value = ''
        if params.move_originator_message_id:
            self.command_set[
                (0x0000, 0x1031)].value = params.move_originator_message_id
        else:
            self.command_set[(0x0000, 0x1031)].value = ''
        self.data_set = params.data_set
        self.set_length()

    def to_params(self):
        tmp = netdicom2.dimseparameters.CStoreServiceParameters()
        tmp.affected_sop_class_uid = self.command_set.get((0x0000, 0x0002))
        tmp.affected_sop_instance_uid = self.command_set.get((0x0000, 0x1000))
        tmp.priority = self.command_set.get((0x0000, 0x0700))
        tmp.dataset = self.data_set
        tmp.message_id = self.command_set.get((0x0000, 0x0110))
        return tmp


class CStoreRSPMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Affected SOP Class UID', (0x0000, 0x0002), 'UI', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID Being Responded To', (0x0000, 0x0120), 'US',
                       1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1),
                      ('Status', (0x0000, 0x0900), 'US', 1),
                      ('Affected SOP Instance UID', (0x0000, 0x1000), 'UI', 1)]

    def from_params(self, params):
        self.command_set[
            (0x0000, 0x0002)].value = params.affected_sop_class_uid.value
        self.command_set[(0x0000, 0x0100)].value = 0x8001
        self.command_set[
            (0x0000, 0x0120)].value = params.message_id_being_responded_to.value
        self.command_set[(0x0000, 0x0800)].value = 0x0101
        self.command_set[(0x0000, 0x0900)].value = params.status
        self.command_set[
            (0x0000, 0x1000)].value = params.affected_sop_instance_uid.value
        self.data_set = None
        self.set_length()

    def to_params(self):
        tmp = netdicom2.dimseparameters.CStoreServiceParameters()
        tmp.affected_sop_class_uid = self.command_set.get((0x0000, 0x0002))
        tmp.message_id_being_responded_to = self.command_set.get(
            (0x0000, 0x0120))
        tmp.status = self.command_set.get((0x0000, 0x0900))
        tmp.affected_sop_instance_uid = self.command_set.get((0x0000, 0x1000))
        tmp.dataset = self.data_set
        return tmp


class CFindRQMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Affected SOP Class UID', (0x0000, 0x0002), 'UI', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID', (0x0000, 0x0110), 'US', 1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1),
                      ('Priority', (0x0000, 0x0700), 'US', 1)]

    def from_params(self, params):
        self.command_set[(0x0000, 0x0002)].value = params.affected_sop_class_uid
        self.command_set[(0x0000, 0x0100)].value = 0x0020
        self.command_set[(0x0000, 0x0110)].value = params.message_id
        self.command_set[(0x0000, 0x0700)].value = params.priority
        self.command_set[(0x0000, 0x0800)].value = 0x0001
        self.data_set = params.identifier
        self.set_length()

    def to_params(self):
        tmp = netdicom2.dimseparameters.CFindServiceParameters()
        tmp.affected_sop_class_uid = self.command_set[(0x0000, 0x0002)]
        tmp.priority = self.command_set.get((0x0000, 0x0700))
        tmp.identifier = self.data_set
        tmp.message_id = self.command_set.get((0x0000, 0x0110))
        return tmp


class CFindRSPMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Affected SOP Class UID', (0x0000, 0x0002), 'UI', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID Being Responded To', (0x0000, 0x0120), 'US',
                       1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1),
                      ('Status', (0x0000, 0x0900), 'US', 1)]

    def from_params(self, params):
        self.command_set[
            (0x0000, 0x0002)].value = params.affected_sop_class_uid.value
        self.command_set[(0x0000, 0x0100)].value = 0x8020
        self.command_set[
            (0x0000, 0x0120)].value = params.message_id_being_responded_to.value
        if not params.identifier:
            self.command_set[(0x0000, 0x0800)].value = 0x0101
        else:
            self.command_set[(0x0000, 0x0800)].value = 0x000
        self.command_set[(0x0000, 0x0900)].value = params.status
        self.data_set = params.identifier
        self.set_length()

    def to_params(self):
        tmp = netdicom2.dimseparameters.CFindServiceParameters()
        tmp.affected_sop_class_uid = self.command_set.get((0x0000, 0x0002))
        tmp.message_id_being_responded_to = self.command_set.get(
            (0x0000, 0x0120))
        tmp.status = self.command_set.get((0x0000, 0x0900))
        tmp.identifier = self.data_set
        return tmp


class CGetRQMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Affected SOP Class UID', (0x0000, 0x0002), 'UI', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID', (0x0000, 0x0110), 'US', 1),
                      ('Priority', (0x0000, 0x0700), 'US', 1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1)]

    def from_params(self, params):
        self.command_set[(0x0000, 0x0002)].value = params.affected_sop_class_uid
        self.command_set[(0x0000, 0x0100)].value = 0x0010
        self.command_set[(0x0000, 0x0110)].value = params.message_id
        self.command_set[(0x0000, 0x0700)].value = params.priority
        self.command_set[(0x0000, 0x0800)].value = 0x0001
        self.data_set = params.identifier
        self.set_length()

    def to_params(self):
        tmp = netdicom2.dimseparameters.CGetServiceParameters()
        tmp.message_id = self.command_set.get((0x0000, 0x0110)).value
        tmp.affected_sop_class_uid = self.command_set.get(
            (0x0000, 0x0002)).value
        tmp.priority = self.command_set.get((0x0000, 0x0700)).value
        tmp.identifier = self.data_set
        return tmp


class CGetRSPMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Affected SOP Class UID', (0x0000, 0x0002), 'UI', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID Being Responded To', (0x0000, 0x0120), 'US',
                       1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1),
                      ('Status', (0x0000, 0x0900), 'US', 1),
                      ('Number of Remaining Sub-operations', (0x0000, 0x1020),
                       'US', 1),
                      ('Number of Complete Sub-operations', (0x0000, 0x1021),
                       'US', 1),
                      ('Number of Failed Sub-operations', (0x0000, 0x1022),
                       'US', 1),
                      ('Number of Warning Sub-operations', (0x0000, 0x1023),
                       'US', 1)]

    def from_params(self, params):
        self.command_set[(0x0000, 0x0002)].value = params.affected_sop_class_uid
        self.command_set[(0x0000, 0x0100)].value = 0x8010
        self.command_set[
            (0x0000, 0x0120)].value = params.message_id_being_responded_to
        self.command_set[(0x0000, 0x0800)].value = 0x0101
        self.command_set[(0x0000, 0x0900)].value = params.status
        self.command_set[
            (0x0000, 0x1020)].value = params.number_of_remaining_sub_operations
        self.command_set[
            (0x0000, 0x1021)].value = params.number_of_completed_sub_operations
        self.command_set[
            (0x0000, 0x1022)].value = params.number_of_failed_sub_operations
        self.command_set[
            (0x0000, 0x1023)].value = params.number_of_warning_sub_operations
        self.set_length()

    def to_params(self):
        tmp = netdicom2.dimseparameters.CGetServiceParameters()
        tmp.affected_sop_class_uid = self.command_set.get((0x0000, 0x0002))
        tmp.message_id_being_responded_to = self.command_set.get(
            (0x0000, 0x0120))
        tmp.status = self.command_set.get((0x0000, 0x0900))
        tmp.number_of_remaining_sub_operations = self.command_set.get(
            (0x0000, 0x1020))
        tmp.number_of_complete_sub_operations = self.command_set.get(
            (0x0000, 0x1021))
        tmp.number_of_failed_sub_operations = self.command_set.get(
            (0x0000, 0x1022))
        tmp.number_of_warning_sub_operations = self.command_set.get(
            (0x0000, 0x1023))
        tmp.identifier = self.data_set
        return tmp


class CMoveRQMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Affected SOP Class UID', (0x0000, 0x0002), 'UI', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID', (0x0000, 0x0110), 'US', 1),
                      ('Priority', (0x0000, 0x0700), 'US', 1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1),
                      ('Move Destination', (0x0000, 0x0600), 'AE', 1)]

    def from_params(self, params):
        self.command_set[(0x0000, 0x0002)].value = params.affected_sop_class_uid
        self.command_set[(0x0000, 0x0100)].value = 0x0021
        self.command_set[(0x0000, 0x0110)].value = params.message_id
        self.command_set[(0x0000, 0x0700)].value = params.priority
        self.command_set[(0x0000, 0x0800)].value = 0x0001
        self.command_set[(0x0000, 0x0600)].value = params.move_destination

        self.data_set = params.identifier
        self.set_length()

    def to_params(self):
        tmp = netdicom2.dimseparameters.CMoveServiceParameters()
        tmp.message_id = self.command_set.get((0x0000, 0x0110))
        tmp.affected_sop_class_uid = self.command_set.get((0x0000, 0x0002))
        tmp.priority = self.command_set.get((0x0000, 0x0700))
        tmp.move_destination = self.command_set.get((0x0000, 0x0600))
        tmp.identifier = self.data_set
        return tmp


class CMoveRSPMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Affected SOP Class UID', (0x0000, 0x0002), 'UI', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID Being Responded To', (0x0000, 0x0120), 'US',
                       1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1),
                      ('Status', (0x0000, 0x0900), 'US', 1),
                      ('Number of Remaining Sub-operations', (0x0000, 0x1020),
                       'US', 1),
                      ('Number of Complete Sub-operations', (0x0000, 0x1021),
                       'US', 1),
                      ('Number of Failed Sub-operations', (0x0000, 0x1022),
                       'US', 1),
                      ('Number of Warning Sub-operations', (0x0000, 0x1023),
                       'US', 1)]

    def from_params(self, params):
        self.command_set[(0x0000, 0x0002)].value = params.affected_sop_class_uid
        self.command_set[(0x0000, 0x0100)].value = 0x8021
        self.command_set[
            (0x0000, 0x0120)].value = params.message_id_being_responded_to
        self.command_set[(0x0000, 0x0800)].value = 0x0101
        self.command_set[(0x0000, 0x0900)].value = params.status
        self.command_set[
            (0x0000, 0x1020)].value = params.number_of_remaining_sub_operations
        self.command_set[
            (0x0000, 0x1021)].value = params.number_of_complete_sub_operations
        self.command_set[
            (0x0000, 0x1022)].value = params.number_of_failed_sub_operations
        self.command_set[
            (0x0000, 0x1023)].value = params.number_of_warning_sub_operations
        self.set_length()

    def to_params(self):
        tmp = netdicom2.dimseparameters.CMoveServiceParameters()
        tmp.affected_sop_class_uid = self.command_set.get((0x0000, 0x0002))
        tmp.message_id_being_responded_to = self.command_set.get(
            (0x0000, 0x0120))
        tmp.status = self.command_set.get((0x0000, 0x0900))
        tmp.number_of_remaining_sub_operations = self.command_set.get(
            (0x0000, 0x1020))
        tmp.number_of_complete_sub_operations = self.command_set.get(
            (0x0000, 0x1021))
        tmp.number_of_failed_sub_operations = self.command_set.get(
            (0x0000, 0x1022))
        tmp.number_of_warning_sub_operations = self.command_set.get(
            (0x0000, 0x1023))
        tmp.identifier = self.data_set
        return tmp


class CCancelRQMessage(DIMSEMessage):
    command_fields = [('Group Length', (0x0000, 0x0000), 'UL', 1),
                      ('Command Field', (0x0000, 0x0100), 'US', 1),
                      ('Message ID Being Responded To', (0x0000, 0x0120), 'US',
                       1),
                      ('Data Set Type', (0x0000, 0x0800), 'US', 1)]

    def from_params(self, params):
        self.command_set[(0x0000, 0x0100)].value = 0x0FFF
        self.command_set[
            (0x0000, 0x0120)].value = params.message_id_being_responded_to
        self.command_set[(0x0000, 0x0800)].value = 0x0101
        self.set_length()


class CCancelFindRQMessage(CCancelRQMessage):
    def to_params(self):
        tmp = netdicom2.dimseparameters.CFindServiceParameters()
        tmp.message_id_being_responded_to = self.command_set[(0x0000, 0x0120)]
        return tmp


class CCancelGetRQMessage(CCancelRQMessage):
    def to_params(self):
        tmp = netdicom2.dimseparameters.CGetServiceParameters()
        tmp.message_id_being_responded_to = self.command_set[(0x0000, 0x0120)]
        return tmp


class CCancelMoveRQMessage(CCancelRQMessage):
    def to_params(self):
        tmp = netdicom2.dimseparameters.CMoveServiceParameters()
        tmp.message_id_being_responded_to = self.command_set[(0x0000, 0x0120)]
        return tmp


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
    0x8030: CEchoRSPMessage
}
