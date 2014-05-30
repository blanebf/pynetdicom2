# Copyright (c) 2014 Pavel 'Blane' Tuchin
# This file is part of pynetdicom2, released under a modified MIT license.
#    See the file license.txt included with this distribution.
__author__ = 'Blane'

import unittest
import netdicom2.dimsemessages


class CEchoRQMessage(unittest.TestCase):
    def test_default_init(self):
        msg = netdicom2.dimsemessages.CEchoRQMessage()
        # self.assertEqual(msg.affected_sop_class_uid, )