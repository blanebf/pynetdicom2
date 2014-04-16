# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#


import netdicom2.dimsemessages
import netdicom2.userdataitems


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
