# Copyright (c) 2014 Pavel 'Blane' Tuchin
# This file is part of pynetdicom2, released under a modified MIT license.
#    See the file license.txt included with this distribution.
__author__ = 'Blane'

import unittest
from pynetdicom2 import dimsemessages


class MessageTesterBase(unittest.TestCase):
    def assert_command_attributes(
            self,
            msg: dimsemessages.DIMSEMessage
    ) -> None:
        self.assertEqual(msg.command_field, msg.command_set.CommandField)
        for field in msg.command_fields:
            self.assertTrue(hasattr(msg.command_set, field))


class CEchoRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CEchoRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.message_id, None)

    def test_properties_set_values(self) -> None:
        message_id = 5
        self.msg.message_id = 5
        self.assertEqual(self.msg.message_id, message_id)

        affected_sop_class_uid = '1.2.3.4.5'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid, affected_sop_class_uid)


class CEchoRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CEchoRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.message_id_being_responded_to, None)

    def test_properties_set_values(self) -> None:
        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(
            self.msg.message_id_being_responded_to,
            message_id_being_responded_to
        )


class CStoreRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CStoreRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.message_id, None)
        self.assertEqual(self.msg.priority, None)
        self.assertEqual(self.msg.affected_sop_instance_uid, None)
        self.assertEqual(self.msg.move_originator_aet, None)
        self.assertEqual(self.msg.move_originator_message_id, None)

    def test_properties_set_values(self) -> None:
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid, affected_sop_class_uid)

        message_id = 5
        self.msg.message_id = message_id
        self.assertEqual(self.msg.message_id, message_id)

        priority = dimsemessages.PRIORITY_HIGH
        self.msg.priority = priority
        self.assertEqual(self.msg.priority, priority)

        affected_sop_instance_uid = '1.2.3.5'
        self.msg.affected_sop_instance_uid = affected_sop_instance_uid
        self.assertEqual(
            self.msg.affected_sop_instance_uid,
            affected_sop_instance_uid
        )

        move_originator_aet = 'aet1'
        self.msg.move_originator_aet = move_originator_aet
        self.assertEqual(self.msg.move_originator_aet, move_originator_aet)

        move_originator_message_id = 6
        self.msg.move_originator_message_id = move_originator_message_id
        self.assertEqual(
            self.msg.move_originator_message_id,
            move_originator_message_id
        )


class CStoreRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CStoreRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.message_id_being_responded_to, None)
        self.assertEqual(self.msg.status, None)
        self.assertEqual(self.msg.affected_sop_instance_uid, None)

    def test_properties_set_values(self) -> None:
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid, affected_sop_class_uid)

        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(
            self.msg.message_id_being_responded_to,
            message_id_being_responded_to
        )

        status = 0
        self.msg.status = status
        self.assertEqual(self.msg.status, status)

        affected_sop_instance_uid = '1.2.3.5'
        self.msg.affected_sop_instance_uid = affected_sop_instance_uid
        self.assertEqual(
            self.msg.affected_sop_instance_uid,
            affected_sop_instance_uid
        )


class CFindRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CFindRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.message_id, None)
        self.assertEqual(self.msg.priority, None)

    def test_properties_set_values(self) -> None:
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(
            self.msg.sop_class_uid,
            affected_sop_class_uid
        )

        message_id = 5
        self.msg.message_id = message_id
        self.assertEqual(self.msg.message_id, message_id)

        priority = dimsemessages.PRIORITY_LOW
        self.msg.priority = priority
        self.assertEqual(self.msg.priority, priority)


class CFindRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CFindRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.message_id_being_responded_to, None)
        self.assertEqual(self.msg.status, None)

    def test_properties_set_values(self) -> None:
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid, affected_sop_class_uid)

        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(
            self.msg.message_id_being_responded_to,
            message_id_being_responded_to
        )

        status = 0
        self.msg.status = status
        self.assertEqual(self.msg.status, status)


class CGetRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CGetRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.message_id, None)
        self.assertEqual(self.msg.priority, None)

    def test_properties_set_values(self) -> None:
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid, affected_sop_class_uid)

        message_id = 5
        self.msg.message_id = message_id
        self.assertEqual(self.msg.message_id, message_id)

        priority = dimsemessages.PRIORITY_LOW
        self.msg.priority = priority
        self.assertEqual(self.msg.priority, priority)


class CGetRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CGetRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.message_id_being_responded_to, None)
        self.assertEqual(self.msg.status, None)

        self.assertEqual(self.msg.num_of_remaining_sub_ops, None)
        self.assertEqual(self.msg.num_of_completed_sub_ops, None)
        self.assertEqual(self.msg.num_of_failed_sub_ops, None)
        self.assertEqual(self.msg.num_of_warning_sub_ops, None)

    def test_properties_set_values(self) -> None:
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid, affected_sop_class_uid)

        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(
            self.msg.message_id_being_responded_to,
            message_id_being_responded_to
        )

        status = 0
        self.msg.status = status
        self.assertEqual(self.msg.status, status)

        num_of_remaining_sub_ops = 10
        self.msg.num_of_remaining_sub_ops = num_of_remaining_sub_ops
        self.assertEqual(
            self.msg.num_of_remaining_sub_ops,
            num_of_remaining_sub_ops
        )

        num_of_completed_sub_ops = 11
        self.msg.num_of_completed_sub_ops = num_of_completed_sub_ops
        self.assertEqual(
            self.msg.num_of_completed_sub_ops,
            num_of_completed_sub_ops
        )

        num_of_failed_sub_ops = 12
        self.msg.num_of_failed_sub_ops = num_of_failed_sub_ops
        self.assertEqual(self.msg.num_of_failed_sub_ops, num_of_failed_sub_ops)

        num_of_warning_sub_ops = 13
        self.msg.num_of_warning_sub_ops = num_of_warning_sub_ops
        self.assertEqual(
            self.msg.num_of_warning_sub_ops,
            num_of_warning_sub_ops
        )


class CMoveRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CMoveRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.message_id, None)
        self.assertEqual(self.msg.priority, None)
        self.assertEqual(self.msg.move_destination, None)

    def test_properties_set_values(self) -> None:
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid, affected_sop_class_uid)

        message_id = 5
        self.msg.message_id = message_id
        self.assertEqual(self.msg.message_id, message_id)

        priority = dimsemessages.PRIORITY_LOW
        self.msg.priority = priority
        self.assertEqual(self.msg.priority, priority)

        move_destination = 'aet1'
        self.msg.move_destination = move_destination
        self.assertEqual(self.msg.move_destination, move_destination)


class CMoveRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CMoveRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.message_id_being_responded_to, None)
        self.assertEqual(self.msg.status, None)

        self.assertEqual(self.msg.num_of_remaining_sub_ops, None)
        self.assertEqual(self.msg.num_of_completed_sub_ops, None)
        self.assertEqual(self.msg.num_of_failed_sub_ops, None)
        self.assertEqual(self.msg.num_of_warning_sub_ops, None)

    def test_properties_set_values(self) -> None:
        affected_sop_class_uid = '1.2.3.4'
        self.msg.sop_class_uid = affected_sop_class_uid
        self.assertEqual(self.msg.sop_class_uid, affected_sop_class_uid)

        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(
            self.msg.message_id_being_responded_to,
            message_id_being_responded_to
        )

        status = 0
        self.msg.status = status
        self.assertEqual(self.msg.status, status)

        num_of_remaining_sub_ops = 10
        self.msg.num_of_remaining_sub_ops = num_of_remaining_sub_ops
        self.assertEqual(
            self.msg.num_of_remaining_sub_ops,
            num_of_remaining_sub_ops
        )

        num_of_completed_sub_ops = 11
        self.msg.num_of_completed_sub_ops = num_of_completed_sub_ops
        self.assertEqual(
            self.msg.num_of_completed_sub_ops,
            num_of_completed_sub_ops
        )

        num_of_failed_sub_ops = 12
        self.msg.num_of_failed_sub_ops = num_of_failed_sub_ops
        self.assertEqual(self.msg.num_of_failed_sub_ops, num_of_failed_sub_ops)

        num_of_warning_sub_ops = 13
        self.msg.num_of_warning_sub_ops = num_of_warning_sub_ops
        self.assertEqual(
            self.msg.num_of_warning_sub_ops,
            num_of_warning_sub_ops
        )


class CCancelRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.CCancelRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.message_id_being_responded_to, None)

    def test_properties_set_values(self) -> None:
        message_id_being_responded_to = 5
        self.msg.message_id_being_responded_to = message_id_being_responded_to
        self.assertEqual(
            self.msg.message_id_being_responded_to,
            message_id_being_responded_to
        )


class NEventReportRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NEventReportRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.event_type_id, None)
        self.assertEqual(self.msg.affected_sop_instance_uid, None)


class NEventReportRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NEventReportRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.event_type_id, None)
        self.assertEqual(self.msg.status, None)
        self.assertEqual(self.msg.affected_sop_instance_uid, None)


class NGetRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NGetRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.requested_sop_instance_uid, None)
        self.assertEqual(self.msg.attribute_identifier_list, None)


class NGetRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NGetRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.status, None)
        self.assertEqual(self.msg.affected_sop_instance_uid, None)


class NSetRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NSetRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.requested_sop_instance_uid, None)


class NSetRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NSetRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.status, None)
        self.assertEqual(self.msg.affected_sop_instance_uid, None)


class NActionRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NActionRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.requested_sop_instance_uid, None)
        self.assertEqual(self.msg.action_type_id, None)


class NActionRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NActionRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.status, None)
        self.assertEqual(self.msg.affected_sop_instance_uid, None)
        self.assertEqual(self.msg.action_type_id, None)


class NCreateRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NCreateRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.affected_sop_instance_uid, None)


class NCreateRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NCreateRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.status, None)
        self.assertEqual(self.msg.affected_sop_instance_uid, None)


class NDeleteRQMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NDeleteRQMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.requested_sop_instance_uid, None)


class NDeleteRSPMessage(MessageTesterBase):
    def setUp(self) -> None:
        self.msg = dimsemessages.NDeleteRSPMessage()

    def test_default_init(self) -> None:
        self.assert_command_attributes(self.msg)

    def test_properties_default_values(self) -> None:
        self.assertEqual(self.msg.sop_class_uid, None)
        self.assertEqual(self.msg.status, None)
        self.assertEqual(self.msg.affected_sop_instance_uid, None)
