# Copyright (c) 2014 Pavel 'Blane' Tuchin
# This file is part of pynetdicom2, released under a modified MIT license.
#    See the file license.txt included with this distribution.
__author__ = 'Blane'

import unittest
import pynetdicom2.dimsemessages


class MessageTesterBase(unittest.TestCase):
    def assert_command_attributes(self, msg):
        self.assertEqual(msg.command_field, msg.command_set.CommandField)
        for field in msg.command_fields:
            self.assertTrue(hasattr(msg.command_set, field))


class CEchoRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CEchoRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.message_id, '')

    def test_properties_set_values(self):
        message_id = 5
        self.msg.message_id = 5
        self.assertEqual(self.msg.message_id, message_id)

        affected_sop_class_uid = '1.2.3.4.5'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid,
                         affected_sop_class_uid)


class CEchoRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CEchoRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.message_id_being_responded_to, '')

    def test_properties_set_values(self):
        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(self.msg.message_id_being_responded_to,
                         message_id_being_responded_to)


class CStoreRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CStoreRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.message_id, '')
        self.assertEqual(self.msg.priority, '')
        self.assertEqual(self.msg.affected_sop_instance_uid, '')
        self.assertEqual(self.msg.move_originator_aet, '')
        self.assertEqual(self.msg.move_originator_message_id, '')

    def test_properties_set_values(self):
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid,
                         affected_sop_class_uid)

        message_id = 5
        self.msg.message_id = message_id
        self.assertEqual(self.msg.message_id, message_id)

        priority = pynetdicom2.dimsemessages.PRIORITY_HIGH
        self.msg.priority = priority
        self.assertEqual(self.msg.priority, priority)

        affected_sop_instance_uid = '1.2.3.5'
        self.msg.affected_sop_instance_uid = affected_sop_instance_uid
        self.assertEqual(self.msg.affected_sop_instance_uid,
                         affected_sop_instance_uid)

        move_originator_aet = 'aet1'
        self.msg.move_originator_aet = move_originator_aet
        self.assertEqual(self.msg.move_originator_aet, move_originator_aet)

        move_originator_message_id = 6
        self.msg.move_originator_message_id = move_originator_message_id
        self.assertEqual(self.msg.move_originator_message_id,
                         move_originator_message_id)


class CStoreRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CStoreRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.message_id_being_responded_to, '')
        self.assertEqual(self.msg.status, '')
        self.assertEqual(self.msg.affected_sop_instance_uid, '')

    def test_properties_set_values(self):
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid,
                         affected_sop_class_uid)

        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(self.msg.message_id_being_responded_to,
                         message_id_being_responded_to)

        status = 0
        self.msg.status = status
        self.assertEqual(self.msg.status, status)

        affected_sop_instance_uid = '1.2.3.5'
        self.msg.affected_sop_instance_uid = affected_sop_instance_uid
        self.assertEqual(self.msg.affected_sop_instance_uid,
                         affected_sop_instance_uid)


class CFindRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CFindRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.message_id, '')
        self.assertEqual(self.msg.priority, '')

    def test_properties_set_values(self):
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid,
                         affected_sop_class_uid)

        message_id = 5
        self.msg.message_id = message_id
        self.assertEqual(self.msg.message_id,
                         message_id)

        priority = pynetdicom2.dimsemessages.PRIORITY_LOW
        self.msg.priority = priority
        self.assertEqual(self.msg.priority, priority)


class CFindRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CFindRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.message_id_being_responded_to, '')
        self.assertEqual(self.msg.status, '')

    def test_properties_set_values(self):
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid,
                         affected_sop_class_uid)

        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(self.msg.message_id_being_responded_to,
                         message_id_being_responded_to)

        status = 0
        self.msg.status = status
        self.assertEqual(self.msg.status, status)


class CGetRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CGetRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.message_id, '')
        self.assertEqual(self.msg.priority, '')

    def test_properties_set_values(self):
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid,
                         affected_sop_class_uid)

        message_id = 5
        self.msg.message_id = message_id
        self.assertEqual(self.msg.message_id,
                         message_id)

        priority = pynetdicom2.dimsemessages.PRIORITY_LOW
        self.msg.priority = priority
        self.assertEqual(self.msg.priority, priority)


class CGetRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CGetRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.message_id_being_responded_to, '')
        self.assertEqual(self.msg.status, '')

        self.assertEqual(self.msg.num_of_remaining_sub_ops, '')
        self.assertEqual(self.msg.num_of_completed_sub_ops, '')
        self.assertEqual(self.msg.num_of_failed_sub_ops, '')
        self.assertEqual(self.msg.num_of_warning_sub_ops, '')

    def test_properties_set_values(self):
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid,
                         affected_sop_class_uid)

        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(self.msg.message_id_being_responded_to,
                         message_id_being_responded_to)

        status = 0
        self.msg.status = status
        self.assertEqual(self.msg.status, status)

        num_of_remaining_sub_ops = 10
        self.msg.num_of_remaining_sub_ops = num_of_remaining_sub_ops
        self.assertEqual(self.msg.num_of_remaining_sub_ops,
                         num_of_remaining_sub_ops)

        num_of_completed_sub_ops = 11
        self.msg.num_of_completed_sub_ops = num_of_completed_sub_ops
        self.assertEqual(self.msg.num_of_completed_sub_ops,
                         num_of_completed_sub_ops)

        num_of_failed_sub_ops = 12
        self.msg.num_of_failed_sub_ops = num_of_failed_sub_ops
        self.assertEqual(self.msg.num_of_failed_sub_ops, num_of_failed_sub_ops)

        num_of_warning_sub_ops = 13
        self.msg.num_of_warning_sub_ops = num_of_warning_sub_ops
        self.assertEqual(self.msg.num_of_warning_sub_ops,
                         num_of_warning_sub_ops)


class CMoveRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CMoveRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.message_id, '')
        self.assertEqual(self.msg.priority, '')
        self.assertEqual(self.msg.move_destination, '')

    def test_properties_set_values(self):
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid,
                         affected_sop_class_uid)

        message_id = 5
        self.msg.message_id = message_id
        self.assertEqual(self.msg.message_id,
                         message_id)

        priority = pynetdicom2.dimsemessages.PRIORITY_LOW
        self.msg.priority = priority
        self.assertEqual(self.msg.priority, priority)

        move_destination = 'aet1'
        self.msg.move_destination = move_destination
        self.assertEqual(self.msg.move_destination, move_destination)


class CMoveRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CMoveRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.message_id_being_responded_to, '')
        self.assertEqual(self.msg.status, '')

        self.assertEqual(self.msg.num_of_remaining_sub_ops, '')
        self.assertEqual(self.msg.num_of_completed_sub_ops, '')
        self.assertEqual(self.msg.num_of_failed_sub_ops, '')
        self.assertEqual(self.msg.num_of_warning_sub_ops, '')

    def test_properties_set_values(self):
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid,
                         affected_sop_class_uid)

        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(self.msg.message_id_being_responded_to,
                         message_id_being_responded_to)

        status = 0
        self.msg.status = status
        self.assertEqual(self.msg.status, status)

        num_of_remaining_sub_ops = 10
        self.msg.num_of_remaining_sub_ops = num_of_remaining_sub_ops
        self.assertEqual(self.msg.num_of_remaining_sub_ops,
                         num_of_remaining_sub_ops)

        num_of_completed_sub_ops = 11
        self.msg.num_of_completed_sub_ops = num_of_completed_sub_ops
        self.assertEqual(self.msg.num_of_completed_sub_ops,
                         num_of_completed_sub_ops)

        num_of_failed_sub_ops = 12
        self.msg.num_of_failed_sub_ops = num_of_failed_sub_ops
        self.assertEqual(self.msg.num_of_failed_sub_ops, num_of_failed_sub_ops)

        num_of_warning_sub_ops = 13
        self.msg.num_of_warning_sub_ops = num_of_warning_sub_ops
        self.assertEqual(self.msg.num_of_warning_sub_ops,
                         num_of_warning_sub_ops)


class CCancelRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.CCancelRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.message_id_being_responded_to, '')

    def test_properties_set_values(self):
        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(self.msg.message_id_being_responded_to,
                         message_id_being_responded_to)


class NEventReportRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NEventReportRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.event_type_id, '')
        self.assertEqual(self.msg.affected_sop_instance_uid, '')


class NEventReportRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NEventReportRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.event_type_id, '')
        self.assertEqual(self.msg.status, '')
        self.assertEqual(self.msg.affected_sop_instance_uid, '')


class NGetRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NGetRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.requested_sop_instance_uid, '')
        self.assertEqual(self.msg.attribute_identifier_list, '')


class NGetRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NGetRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.status, '')
        self.assertEqual(self.msg.affected_sop_instance_uid, '')


class NSetRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NSetRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.requested_sop_instance_uid, '')


class NSetRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NSetRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.status, '')
        self.assertEqual(self.msg.affected_sop_instance_uid, '')


class NActionRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NActionRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.requested_sop_instance_uid, '')
        self.assertEqual(self.msg.action_type_id, '')


class NActionRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NActionRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.status, '')
        self.assertEqual(self.msg.affected_sop_instance_uid, '')
        self.assertEqual(self.msg.action_type_id, '')


class NCreateRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NCreateRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.affected_sop_instance_uid, '')


class NCreateRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NCreateRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.status, '')
        self.assertEqual(self.msg.affected_sop_instance_uid, '')


class NDeleteRQMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NDeleteRQMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.requested_sop_instance_uid, '')


class NDeleteRSPMessage(MessageTesterBase):
    def setUp(self):
        self.msg = pynetdicom2.dimsemessages.NDeleteRSPMessage()

    def test_default_init(self):
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self):
        self.assertEqual(self.msg.sop_class_uid, '')
        self.assertEqual(self.msg.status, '')
        self.assertEqual(self.msg.affected_sop_instance_uid, '')
