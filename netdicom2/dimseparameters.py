# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

import struct

import netdicom2.dimsemessages


def class_printer(obj):
    return ''.join(['%s: %s\n' % (k, v) for k, v in obj.__dict__.iteritems() if
                    not callable(v)])


class DIMSEParamsBase(object):
    """Base class for DIMSE parameters classes.

    Class is not intended to be used directly, but rather it should be
    sub-classed when implementing DIMSE parameters classes. When sub-classing
    user should proved <request_message> and <response_message> class
    attributes. These attributes are used for converting parameters to
    corresponding message types
    """
    request_message = None
    response_message = None

    def __init__(self, message_id=None, message_id_being_responded_to=None,
                 status=None):
        """Provides basic initialization for DIMSE parameters class/

        :param message_id: message ID (int)
        :param message_id_being_responded_to: just what parameter name says.
        Used in response message.
        :param status: message status
        """
        self.message_id = message_id
        self.message_id_being_responded_to = message_id_being_responded_to
        self.status = status

    def __repr__(self):
        """Prints all parameters attributes. Very simple and straight forward.

        :return: all parameter attributes converted to string.
        """
        return class_printer(self)

    def to_message(self):
        """Converts DIMSE parameters to corresponding DIMSE message.

        :return: DIMSE message
        """
        if self.message_id:
            dimse_type = self.request_message
        else:
            dimse_type = self.response_message
        dimse_msg = dimse_type()
        dimse_msg.from_params(self)
        return dimse_msg


# DIMSE-C Services

class CStoreServiceParameters(DIMSEParamsBase):
    request_message = netdicom2.dimsemessages.CStoreRQMessage
    response_message = netdicom2.dimsemessages.CStoreRSPMessage

    def __init__(self, *args, **kwargs):
        super(CStoreServiceParameters, self).__init__(*args, **kwargs)
        self.affected_sop_class_uid = None
        self.affected_sop_instance_uid = None
        self.move_originator_application_entity_title = None
        self.move_originator_message_id = None
        self.dataset = None


class CFindServiceParameters(DIMSEParamsBase):
    request_message = netdicom2.dimsemessages.CFindRQMessage
    response_message = netdicom2.dimsemessages.CFindRSPMessage

    def __init__(self, *args, **kwargs):
        super(CFindServiceParameters, self).__init__(*args, **kwargs)
        self.affected_sop_class_uid = None
        self.priority = None
        self.identifier = None


class CGetServiceParameters(DIMSEParamsBase):
    request_message = netdicom2.dimsemessages.CGetRQMessage
    response_message = netdicom2.dimsemessages.CGetRSPMessage

    def __init__(self, *args, **kwargs):
        super(CGetServiceParameters, self).__init__(*args, **kwargs)
        self.affected_sop_class_uid = None
        self.priority = None
        self.identifier = None
        self.number_of_remaining_sub_operations = None
        self.number_of_complete_sub_operations = None
        self.number_of_failed_sub_operations = None
        self.number_of_warning_sub_operations = None


class CMoveServiceParameters(DIMSEParamsBase):
    request_message = netdicom2.dimsemessages.CMoveRQMessage
    response_message = netdicom2.dimsemessages.CMoveRSPMessage

    def __init__(self, *args, **kwargs):
        super(CMoveServiceParameters, self).__init__(*args, **kwargs)
        self.affected_sop_class_uid = None
        self.priority = None
        self.move_destination = None
        self.identifier = None
        self.number_of_remaining_sub_operations = None
        self.number_of_complete_sub_operations = None
        self.number_of_failed_sub_operations = None
        self.number_of_warning_sub_operations = None


class CEchoServiceParameters(DIMSEParamsBase):
    request_message = netdicom2.dimsemessages.CEchoRQMessage
    response_message = netdicom2.dimsemessages.CEchoRSPMessage

    def __init__(self, *args, **kwargs):
        super(CEchoServiceParameters, self).__init__(*args, **kwargs)
        self.affected_sop_class_uid = None


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


# Extended association stuff: Defined in part 3.7


class ImplementationClassUIDParameters(object):
    def __init__(self):
        self.implementation_class_uid = None

    def to_params(self):
        return ImplementationClassUIDSubItem.from_params(self)


class ImplementationClassUIDSubItem(object):
    def __init__(self, item_length, implementation_class_uid, **kwargs):
        self.item_type = kwargs.get('item_type', 0x52)  # unsigned byte
        self.reserved = kwargs.get('reserved', 0x00)  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.implementation_class_uid = implementation_class_uid  # string

    def __repr__(self):
        return ''.join(['  Implementation class IUD sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   SOP class UID length: %s\n' % self.implementation_class_uid])

    @classmethod
    def from_params(cls, params):
        return cls(len(params.implementation_class_uid),
                   params.implementation_class_uid)

    def to_params(self):
        tmp = ImplementationClassUIDParameters()
        tmp.implementation_class_uid = self.implementation_class_uid
        return tmp

    def encode(self):
        return ''.join([struct.pack('>B B H', self.item_type, self.reserved,
                                    self.item_length),
                        self.implementation_class_uid])

    @classmethod
    def decode(cls, stream):
        item_type, reserved, item_length = struct.unpack('> B B H',
                                                         stream.read(4))
        implementation_class_uid = stream.read(item_length)
        return cls(item_type=item_type, reserved=reserved,
                   item_length=item_length,
                   implementation_class_uid=implementation_class_uid)

    def total_length(self):
        return 4 + self.item_length


class ImplementationVersionNameParameters(object):
    def __init__(self):
        self.implementation_version_name = None

    def to_params(self):
        return ImplementationVersionNameSubItem.from_params(self)


class ImplementationVersionNameSubItem(object):
    def __init__(self, item_length, implementation_version_name, **kwargs):
        self.item_type = kwargs.get('item_type', 0x55)  # unsigned byte
        self.reserved = kwargs.get('reserved', 0x00)  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.implementation_version_name = implementation_version_name  # string

    def __repr__(self):
        return ''.join(['  Implementation version name sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   SOP class UID length: %s\n' % self.implementation_version_name])

    @classmethod
    def from_params(cls, params):
        return cls(len(params.implementation_version_name),
                   params.implementation_version_name)

    def to_params(self):
        tmp = ImplementationVersionNameParameters()
        tmp.implementation_version_name = self.implementation_version_name
        return tmp

    def encode(self):
        return ''.join([struct.pack('> B B H', self.item_type, self.reserved,
                                    self.item_length),
                        self.implementation_version_name])

    @classmethod
    def decode(cls, stream):
        item_type, reserved, item_length = struct.unpack('> B B H',
                                                         stream.read(4))
        implementation_version_name = stream.read(item_length)
        return cls(item_type=item_type, reserved=reserved,
                   item_length=item_length,
                   implementation_version_name=implementation_version_name)

    def total_length(self):
        return 4 + self.item_length


class AsynchronousOperationsWindowSubItem(object):
    def __init__(self, max_num_ops_invoked, max_num_ops_performed, **kwargs):
        self.item_type = kwargs.get('item_type', 0x53)  # unsigned byte
        self.reserved = kwargs.get('reserved', 0x00)  # unsigned byte
        self.item_length = kwargs.get('item_length', 0x0004)  # unsigned short
        self.max_num_ops_invoked = max_num_ops_invoked  # unsigned short
        self.max_num_ops_performed = max_num_ops_performed  # unsigned short

    def __repr__(self):
        return ''.join(['  Asynchronous operation window sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   Maximum number of operations invoked: %d\n' % self.max_num_ops_invoked,
                        '   Maximum number of operations performed: %d\n' % self.max_num_ops_performed])

    @classmethod
    def from_params(cls, params):
        return cls(params.max_num_ops_invoked, params.max_num_ops_performed)

    def to_params(self):
        return AsynchronousOperationsWindowSubItem(self.max_num_ops_invoked,
                                                   self.max_num_ops_performed)

    def encode(self):
        return struct.pack('>B B H H H', self.item_type, self.reserved,
                           self.item_length, self.max_num_ops_invoked,
                           self.max_num_ops_performed)

    @classmethod
    def decode(cls, stream):
        item_type, reserved, item_length, max_num_ops_invoked, \
            max_num_ops_performed = struct.unpack('> B B H H H', stream.read(8))
        return cls(item_type=item_type, reserved=reserved,
                   item_length=item_length,
                   max_num_ops_invoked=max_num_ops_invoked,
                   max_num_ops_performed=max_num_ops_performed)

    def total_length(self):
        return 4 + self.item_length


class ScpScuRoleSelectionParameters(object):
    def __init__(self):
        self.sop_class_uid = None
        self.scu_role = None
        self.scp_role = None

    def to_params(self):
        return ScpScuRoleSelectionSubItem.from_params(self)


class ScpScuRoleSelectionSubItem(object):
    def __init__(self, item_length, uid_length, sop_class_uid, scu_role,
                 scp_role, **kwargs):
        self.item_type = kwargs.get('item_type', 0x54)  # unsigned byte
        self.reserved = kwargs.get('reserved', 0x00)  # unsigned byte 0x00
        self.item_length = item_length  # unsigned short
        self.uid_length = uid_length  # unsigned short
        self.sop_class_uid = sop_class_uid  # string
        self.scu_role = scu_role  # unsigned byte
        self.scp_role = scp_role  # unsigned byte

    def __repr__(self):
        return ''.join(['  SCU/SCP role selection sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   SOP class UID length: %d\n' % self.uid_length,
                        '   SOP class UID: %s\n' % self.sop_class_uid,
                        '   SCU Role: %d\n' % self.scu_role,
                        '   SCP Role: %d' % self.scp_role])

    @classmethod
    def from_params(cls, params):
        uid_length = len(params.sop_class_uid)
        return cls(4 + uid_length, uid_length, params.sop_class_uid,
                   params.scu_role, params.scp_role)

    def to_params(self):
        tmp = ScpScuRoleSelectionParameters()
        tmp.sop_class_uid = self.sop_class_uid
        tmp.scu_role = self.scu_role
        tmp.scp_role = self.scp_role
        return tmp

    def encode(self):
        return ''.join(
            [struct.pack('>B B H H', self.item_type, self.reserved,
                         self.item_length, self.uid_length),
             self.sop_class_uid,
             struct.pack('B B', self.scu_role, self.scp_role)])

    @classmethod
    def decode(cls, stream):
        item_type, reserved, item_length, \
            uid_length = struct.unpack('> B B H H', stream.read(6))
        sop_class_uid = stream.read(uid_length)
        scu_role, scp_role = struct.unpack('B B', stream.read(2))
        return cls(item_type=item_type, reserved=reserved,
                   item_length=item_length, uid_length=uid_length,
                   sop_class_uid=sop_class_uid, scu_role=scu_role,
                   scp_role=scp_role)

    def total_length(self):
        return 4 + self.item_length


# needs to be re-worked
class SOPClassExtendedNegotiationSubItem(object):
    pass
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
