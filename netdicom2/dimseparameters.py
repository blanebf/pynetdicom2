# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

import struct


def class_printer(obj):
    return ''.join(['%s: %s\n' % (k, v) for k, v in obj.__dict__.iteritems() if
                    not callable(v)])


# DIMSE-C Services

class CStoreServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.affected_sop_class_uid = None
        self.affected_sop_instance_uid = None
        self.priority = None
        self.move_originator_application_entity_title = None
        self.move_originator_message_id = None
        self.dataset = None
        self.status = None

    def __repr__(self):
        return class_printer(self)


class CFindServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.affected_sop_class_uid = None
        self.priority = None
        self.identifier = None
        self.status = None

    def __repr__(self):
        return class_printer(self)


class CGetServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.affected_sop_class_uid = None
        self.priority = None
        self.identifier = None
        self.status = None
        self.number_of_remaining_sub_operations = None
        self.number_of_complete_sub_operations = None
        self.number_of_failed_sub_operations = None
        self.number_of_warning_sub_operations = None

    def __repr__(self):
        return class_printer(self)


class CMoveServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.affected_sop_class_uid = None
        self.priority = None
        self.move_destination = None
        self.identifier = None
        self.status = None
        self.number_of_remaining_sub_operations = None
        self.number_of_complete_sub_operations = None
        self.number_of_failed_sub_operations = None
        self.number_of_warning_sub_operations = None

    def __repr__(self):
        return class_printer(self)


class CEchoServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.affected_sop_class_uid = None
        self.status = None

    def __repr__(self):
        return class_printer(self)


# DIMSE-N services
class NEventReportServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.affected_sop_class_uid = None
        self.affected_sop_instance_uid = None
        self.event_type_id = None
        self.event_information = None
        self.event_reply = None
        self.status = None


class NGetServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.requested_sop_class_uid = None
        self.requested_sop_instance_uid = None
        self.attribute_identifier_list = None
        self.affected_sop_class_uid = None
        self.affected_sop_instance_uid = None
        self.attribute_list = None
        self.status = None


class NSetServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.requested_sop_class_uid = None
        self.requested_sop_instance_uid = None
        self.modification_list = None
        self.attribute_list = None
        self.affected_sop_class_uid = None
        self.affected_sop_instance_uid = None
        self.status = None


class NActionServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.requested_sop_class_uid = None
        self.requested_sop_instance_uid = None
        self.action_type_id = None
        self.action_information = None
        self.affected_sop_class_uid = None
        self.affected_sop_instance_uid = None
        self.action_reply = None
        self.status = None


class NCreateServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.affected_sop_class_uid = None
        self.affected_sop_instance_uid = None
        self.attribute_list = None
        self.status = None


class NDeleteServiceParameters(object):
    def __init__(self):
        self.message_id = None
        self.message_id_being_responded_to = None
        self.requested_sop_class_uid = None
        self.requested_sop_instance_uid = None
        self.affected_sop_class_uid = None
        self.affected_sop_instance_uid = None
        self.status = None


class CStoreRQMessage(object):
    def __init__(self):
        pass


class CStoreService(object):
    def __init__(self):
        self.parameters = CStoreServiceParameters()


# Extended association stuff: Defined in part 3.7


class ImplementationClassUIDParameters(object):
    def __init__(self):
        self.implementation_class_uid = None

    def to_params(self):
        tmp = ImplementationClassUIDSubItem()
        tmp.from_params(self)
        return tmp


class ImplementationClassUIDSubItem(object):
    def __init__(self):
        self.item_type = 0x52  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte 0x00
        self.item_length = None  # Unsigned short
        self.implementation_class_uid = None  # String

    def __repr__(self):
        return ''.join(['  Implementation class IUD sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   SOP class UID length: %s\n' % self.implementation_class_uid])

    def from_params(self, params):
        self.implementation_class_uid = params.implementation_class_uid
        self.item_length = len(self.implementation_class_uid)

    def to_params(self):
        tmp = ImplementationClassUIDParameters()
        tmp.implementation_class_uid = self.implementation_class_uid
        return tmp

    def encode(self):
        return ''.join(
            [struct.pack('B', self.item_type), struct.pack('B', self.reserved),
             struct.pack('>H', self.item_length),
             self.implementation_class_uid])

    def decode(self, stream):
        self.item_type, self.reserved, self.item_length = struct.unpack(
            '> B B H', stream.read(4))
        self.implementation_class_uid = stream.read(self.item_length)

    def total_length(self):
        return 4 + self.item_length


class ImplementationVersionNameParameters(object):
    def __init__(self):
        self.implementation_version_name = None

    def to_params(self):
        tmp = ImplementationVersionNameSubItem()
        tmp.from_params(self)
        return tmp


class ImplementationVersionNameSubItem(object):
    def __init__(self):
        self.item_type = 0x55  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte 0x00
        self.item_length = None  # Unsigned short
        self.implementation_version_name = None  # String

    def __repr__(self):
        return ''.join(['  Implementation version name sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   SOP class UID length: %s\n' % self.implementation_version_name])

    def from_params(self, params):
        self.implementation_version_name = params.implementation_version_name
        self.item_length = len(self.implementation_version_name)

    def to_params(self):
        tmp = ImplementationVersionNameParameters()
        tmp.implementation_version_name = self.implementation_version_name
        return tmp

    def encode(self):
        return ''.join(
            [struct.pack('B', self.item_type), struct.pack('B', self.reserved),
             struct.pack('>H', self.item_length),
             self.implementation_version_name])

    def decode(self, stream):
        self.item_type, self.reserved, self.item_length = struct.unpack(
            '> B B H', stream.read(4))
        self.implementation_version_name = stream.read(self.item_length)

    def total_length(self):
        return 4 + self.item_length


class AsynchronousOperationsWindowSubItem(object):
    def __init__(self):
        self.item_type = 0x53  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte
        self.item_length = 0x0004  # Unsigned short
        self.maximum_number_operations_invoked = None  # Unsigned short
        self.maximum_number_operations_performed = None  # Unsigned short

    def __repr__(self):
        return ''.join(['  Asynchronous operation window sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   Maximum number of operations invoked: %d\n' % self.maximum_number_operations_invoked,
                        '   Maximum number of operations performed: %d\n' % self.maximum_number_operations_performed])

    def from_params(self, params):
        self.maximum_number_operations_invoked = params.maximum_number_operations_invoked
        self.maximum_number_operations_performed = params.maximum_number_operations_performed

    def to_params(self):
        tmp = AsynchronousOperationsWindowSubItem()
        tmp.maximum_number_operations_invoked = self.maximum_number_operations_invoked
        tmp.maximum_number_operations_performed = self.maximum_number_operations_performed
        return tmp

    def encode(self):
        return ''.join(
            [struct.pack('B', self.item_type), struct.pack('B', self.reserved),
             struct.pack('>H', self.item_length),
             struct.pack('>H', self.maximum_number_operations_invoked),
             struct.pack('>H', self.maximum_number_operations_performed)])

    def decode(self, stream):
        self.item_type, self.reserved, self.item_length, \
            self.maximum_number_operations_invoked, \
            self.maximum_number_operations_performed = struct.unpack('> B B H H H',
                                                                     stream.read(8))

    def total_length(self):
        return 4 + self.item_length


class ScpScuRoleSelectionParameters(object):
    def __init__(self):
        self.sop_class_uid = None
        self.scu_role = None
        self.scp_role = None

    def to_params(self):
        tmp = ScpScuRoleSelectionSubItem()
        tmp.from_params(self)
        return tmp


class ScpScuRoleSelectionSubItem(object):
    def __init__(self):
        self.item_type = 0x54  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte 0x00
        self.item_length = None  # Unsigned short
        self.uid_length = None  # Unsigned short
        self.sop_class_uid = None  # String
        self.scu_role = None  # Unsigned byte
        self.scp_role = None  # Unsigned byte

    def __repr__(self):
        return ''.join(['  SCU/SCP role selection sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   SOP class UID length: %d\n' % self.uid_length,
                        '   SOP class UID: %s\n' % self.sop_class_uid,
                        '   SCU Role: %d\n' % self.scu_role,
                        '   SCP Role: %d' % self.scp_role])

    def from_params(self, params):
        self.sop_class_uid = params.sop_class_uid
        self.scu_role = params.scu_role
        self.scp_role = params.scp_role
        self.item_length = 4 + len(self.sop_class_uid)
        self.uid_length = len(self.sop_class_uid)

    def to_params(self):
        tmp = ScpScuRoleSelectionParameters()
        tmp.sop_class_uid = self.sop_class_uid
        tmp.scu_role = self.scu_role
        tmp.scp_role = self.scp_role
        return tmp

    def encode(self):
        return ''.join(
            [struct.pack('B', self.item_type), struct.pack('B', self.reserved),
             struct.pack('>H', self.item_length),
             struct.pack('>H', self.uid_length),
             self.sop_class_uid,
             struct.pack('B B', self.scu_role, self.scp_role)])

    def decode(self, stream):
        self.item_type, self.reserved, self.item_length, \
            self.uid_length = struct.unpack('> B B H H', stream.read(6))
        self.sop_class_uid = stream.read(self.uid_length)
        self.scu_role, self.scp_role = struct.unpack('B B', stream.read(2))

    def total_length(self):
        return 4 + self.item_length


# needs to be re-worked
# class SOPClassExtentedNegociationSubItem:
#    def __init__(self):
# self.item_type = 0x56                                   # Unsigned byte
# self.reserved = 0x00                                   # Unsigned byte - 0x00
# self.item_length = None                                 # Unsigned short
# self.SOPClassuid_length = None                          # Unsigned short
# self.SOPClassUID = None                                # String
# self.ServiceClassApplicationInformation = None         # Class
#
#    def from_params(self, Params):
#        self.SOPClassUID = Params.SOPClassUID
#        self.ServiceClassApplicationInformation = \
#            Params.ServiceClassApplicationInformation()
#        self.SOPClassuid_length = len(self.SOPClassUID)
#        self.item_length = 2 + self.SOPClassUIDLength + \
#        self.ServiceClassApplicationInformation.total_length()
#
#    def to_params(self):
#        tmp = SOPClassExtentedNegociationSubItem()
#        tmp.SOPClassUID = self.SOPClassUID
#        tmp.ServiceClassApplicationInformation = \
#            self.ServiceClassApplicationInformation
#        return  (self.SOPClassUID, \
#                  self.ServiceClassApplicationInformation.Decompose())
#
#    def encode(self):
#        tmp = ''
#        tmp = tmp + struct.pack('B', self.item_type)
#        tmp = tmp + struct.pack('B', self.reserved)
#        tmp = tmp + struct.pack('>H', self.item_length)
#        tmp = tmp + struct.pack('>H', self.SOPClassUIDLength)
#        tmp = tmp + self.SOPClassUID
#        tmp = tmp + self.ServiceClassApplicationInformation.encode()
#        return tmp
#
#    def decode(self,Stream):
#        (self.item_type, self.reserved,
#         self.item_length, self.SOPClassUIDLength) = \
#              struct.unpack('> B B H H', Stream.read(6))
#        self.SOPClassUID = Stream.read(self.UIDLength)
#        self.ServiceClassApplicationInformation.decode(Stream)
#
#    def total_length(self):
#        return 4 + self.item_length
#
#
#
#    def __repr__(self):
#        tmp = "  SOP class extended negociation sub item\n"
#        tmp = tmp + "   Item type: 0x%02x\n" % self.item_type
#        tmp = tmp + "   Item length: %d\n" % self.item_length
#        tmp = tmp + "   SOP class UID length: %d\n" % self.SOPClassUIDLength
#        tmp = tmp + "   SOP class UID: %s" % self.SOPClassUID
#        return tmp
#
