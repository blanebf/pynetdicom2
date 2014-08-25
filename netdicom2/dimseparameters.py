# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com


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
