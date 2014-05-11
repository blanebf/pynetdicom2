# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

"""
Implementation of DICOM Standard, PS 3.8, section 9.3
DICOM Upper Layer Protocol for TCP/IP
Data Unit Structure


Module implementing the Data Unit Structures
There are seven different PDUs, each of them corresponds to distinct class.
    A_ASSOCIATE_RQ_PDU
    A_ASSOCIATE_AC_PDU
    A_ASSOCIATE_RJ_PDU
    P_DATA_TF_PDU
    A_RELEASE_RQ_PDU
    A_RELEASE_RP_PDU
    A_ABORT_PDU


    All PDU classes implement the following methods:

      from_params(DULServiceParameterObject):  Builds a PDU from a
                                              DULServiceParameter object.
                                              Used when receiving primitives
                                              from the DULServiceUser.
      to_params()                           :  Convert the PDU into a
                                              DULServiceParameter object.
                                              Used for sending primitives to
                                              the DULServiceUser.
      encode()                     :  Returns the encoded PDU as a string,
                                      ready to be sent over the net.
      decode(string)               :  Construct PDU from "string".
                                      Used for reading PDU's from the net.

                        from_params                 encode
  |------------ -------| ------->  |------------| -------> |------------|
  | Service parameters |           |     PDU    |          |    TCP     |
  |       object       |           |   object   |          |   socket   |
  |____________________| <-------  |____________| <------- |____________|
                         to_params                  decode



In addition to PDUs, several items and sub-items classes are implemented.
These classes are:

        ApplicationContextItem
        PresentationContextItemRQ
        AbstractSyntaxSubItem
        TransferSyntaxSubItem
        UserInformationItem
        PresentationContextItemAC
        PresentationDataValueItem
"""

import struct
from cStringIO import StringIO

import netdicom2.exceptions as exceptions
import netdicom2.userdataitems as userdataitems


SUB_ITEM_TYPES = {
    0x52: userdataitems.ImplementationClassUIDSubItem,
    0x51: userdataitems.MaximumLengthSubItem,
    0x55: userdataitems.ImplementationVersionNameSubItem,
    0x53: userdataitems.AsynchronousOperationsWindowSubItem,
    0x54: userdataitems.ScpScuRoleSelectionSubItem,
    0x56: userdataitems.SOPClassExtendedNegotiationSubItem,
    0x58: userdataitems.UserIdentityNegotiationSubItem,
    0x59: userdataitems.UserIdentityNegotiationSubItemAc
}


def next_type(stream):
    char = stream.read(1)
    if char == '':
        return None  # we are at the end of the file
    stream.seek(-1, 1)
    return struct.unpack('B', char)[0]


class AAssociatePDUBase(object):
    pdu_type = None
    header = struct.Struct('>B B I H H 16s 16s 8I')

    def __init__(self, called_ae_title, calling_ae_title, variable_items,
                 protocol_version=1, reserved1=0x00, reserved2=0x00,
                 reserved3=None):
        self.called_ae_title = called_ae_title  # string of length 16
        self.calling_ae_title = calling_ae_title  # string of length 16
        self.variable_items = variable_items
        self.protocol_version = protocol_version  # unsigned short
        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned short
        if not reserved3:  # 32 bytes
            self.reserved3 = (0, 0, 0, 0, 0, 0, 0, 0)
        else:
            self.reserved3 = reserved3

    @property
    def pdu_length(self):
        return 68 + sum((i.total_length() for i in self.variable_items))

    def to_params(self):
        return self

    def encode(self):
        return self.header.pack(self.pdu_type, self.reserved1, self.pdu_length,
                                self.protocol_version, self.reserved2,
                                self.called_ae_title, self.calling_ae_title,
                                *self.reserved3) \
            + ''.join([item.encode() for item in self.variable_items])

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-ASSOCIATE-RQ PDU instance from raw string.

        :rtype : AAssociateRqPDU
        :param rawstring: rawstring containing binary representation of the
        A-ASSOCIATE-RQ PDU
        :return: decoded PDU
        :raise RuntimeError:
        """
        def iter_items():
            item_type = next_type(stream)
            while item_type:
                if item_type == 0x10:
                    yield ApplicationContextItem.decode(stream)
                elif item_type == 0x20:
                    yield PresentationContextItemRQ.decode(stream)
                elif item_type == 0x21:
                    yield PresentationContextItemAC.decode(stream)
                elif item_type == 0x50:
                    yield UserInformationItem.decode(stream)
                else:
                    raise exceptions.PDUProcessingError('Invalid variable item')
                item_type = next_type(stream)

        stream = StringIO(rawstring)
        values = cls.header.unpack(stream.read(74))
        _, reserved1, _, protocol_version, reserved2, \
            called_ae_title, calling_ae_title = values[:7]
        reserved3 = values[7:]
        called_ae_title = called_ae_title.strip('\0')
        calling_ae_title = calling_ae_title.strip('\0')
        variable_items = list(iter_items())
        return cls(called_ae_title=called_ae_title,
                   calling_ae_title=calling_ae_title,
                   variable_items=variable_items,
                   protocol_version=protocol_version, reserved1=reserved1,
                   reserved2=reserved2, reserved3=reserved3)

    def total_length(self):
        return 6 + self.pdu_length


class AAssociateRqPDU(AAssociatePDUBase):
    """This class represents the A-ASSOCIATE-RQ PDU"""
    pdu_type = 0x01

    def __repr__(self):
        return 'AAssociateRqPDU(called_ae_title={self.called_ae_title}, ' \
               'calling_ae_title={self.calling_ae_title}, ' \
               'variable_items={self.variable_items}, ' \
               'protocol_version={self.protocol_version}, ' \
               'reserved1={self.reserved1}, reserved2={self.reserved2}, ' \
               'reserved3={self.reserved3})'.format(self=self)


class AAssociateAcPDU(AAssociatePDUBase):
    """This class represents the A-ASSOCIATE-AC PDU"""
    pdu_type = 0x02

    def __repr__(self):
        return 'AAssociateAcPDU(called_ae_title={self.called_ae_title}, ' \
               'calling_ae_title={self.calling_ae_title}, ' \
               'variable_items={self.variable_items}, ' \
               'protocol_version={self.protocol_version}, ' \
               'reserved1={self.reserved1}, reserved2={self.reserved2}, ' \
               'reserved3={self.reserved3})'.format(self=self)


class AAssociateRjPDU(object):
    """This class represents the A-ASSOCIATE-RJ PDU"""
    pdu_type = 0x03
    pdu_length = 4  # PDU has fixed length
    format = struct.Struct('>B B I B B B B')

    def __init__(self, result, source, reason_diag, reserved1=0x00,
                 reserved2=0x00):
        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned byte
        self.result = result  # unsigned byte
        self.source = source  # unsigned byte
        self.reason_diag = reason_diag  # unsigned byte

    def __repr__(self):
        return 'AAssociateRjPDU(result={self.result}, source={self.source}, ' \
               'reason_diag={self.reason_diag}, reserved1={self.reserved1}, ' \
               'reserved2={self.reserved2})'.format(self=self)

    def to_params(self):
        return self

    def encode(self):
        return self.format.pack(self.pdu_type, self.reserved1, self.pdu_length,
                                self.reserved2, self.result, self.source,
                                self.reason_diag)

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-ASSOCIATE-RJ PDU instance from raw string.

        :rtype : AAssociateRjPDU
        :param rawstring: rawstring containing binary representation of the
        A-ASSOCIATE-RJ PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        _, reserved1, _, reserved2, result, source, \
            reason_diag = cls.format.unpack(stream.read(10))
        return cls(result=result, source=source, reason_diag=reason_diag,
                   reserved1=reserved1, reserved2=reserved2)

    @staticmethod
    def total_length():
        """Returns PDU total length.

        This PDU has a fixed length of 10, so method always returns 10
        regardless of specific instance
        :return: PDU total length
        """
        return 10


class PDataTfPDU(object):
    """This class represents the P-DATA-TF PDU"""
    pdu_type = 0x04
    header = struct.Struct('>B B I')

    def __init__(self, data_value_items, reserved=0x00):
        self.reserved = reserved  # unsigned byte

        # List of one of more PresentationDataValueItem
        self.data_value_items = data_value_items

    def __repr__(self):
        return 'PDataTfPDU(pdu_length={self.pdu_length}, ' \
               'data_value_items=' \
               '{self.data_value_items}, ' \
               'reserved={self.reserved})'.format(self=self)

    @property
    def pdu_length(self):
        return sum((i.total_length()
                    for i in self.data_value_items))

    def to_params(self):
        return self

    def encode(self):
        return self.header.pack(self.pdu_type, self.reserved, self.pdu_length)\
            + ''.join([item.encode()
                       for item in self.data_value_items])

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes P-DATA-TF PDU instance from raw string.

        :rtype : PDataTfPDU
        :param rawstring: rawstring containing binary representation of the
        P-DATA-TF PDU
        :return: decoded PDU
        """
        def iter_items():
            length_read = 0
            while length_read != pdu_length:
                item = PresentationDataValueItem.decode(stream)
                length_read += item.total_length()
                yield item

        stream = StringIO(rawstring)
        pdu_type, reserved, pdu_length = cls.header.unpack(stream.read(6))
        data_value_items = list(iter_items())
        return cls(data_value_items, reserved)

    def total_length(self):
        return 6 + self.pdu_length


class AReleasePDUBase(object):
    """Base class for the A-RELEASE-* PDUs."""
    pdu_type = None
    pdu_length = 0x00000004  # unsigned int
    format = struct.Struct('>B B I I')

    def __init__(self, reserved1=0x00, reserved2=0x00):
        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned int

    def __repr__(self):
        return 'AReleaseRqPDU(reserved1={0}, reserved2={1})'.format(
            self.reserved1, self.reserved2)

    def to_params(self):
        # TODO Remove this method
        return self

    def encode(self):
        return self.format.pack(self.pdu_type, self.reserved1, self.pdu_length,
                                self.reserved2)

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-RELEASE-* PDU instance from raw string.

        :param rawstring: rawstring containing binary representation of the
        A-RELEASE-* PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        _, reserved1, _, reserved2 = cls.format.unpack(stream.read(10))
        return cls(reserved1=reserved1, reserved2=reserved2)

    @staticmethod
    def total_length():
        """Returns PDU total length.

        This PDU has a fixed length of 10, so method always returns 10
        regardless of specific instance
        :rtype : int
        :return: PDU total length
        """
        return 10


class AReleaseRqPDU(AReleasePDUBase):
    """This class represents the A-RELEASE-RQ PDU.

    PS 3.8-2009 9.3.6 A-RELEASE-RQ PDU STRUCTURE
    """
    pdu_type = 0x05

    def __repr__(self):
        return 'AReleaseRqPDU(reserved1={0}, reserved2={1})'.format(
            self.reserved1, self.reserved2)


class AReleaseRpPDU(AReleasePDUBase):
    """This class represents the A-RELEASE-RP PDU.

    PS 3.8-2009 9.3.7 A-RELEASE-RP PDU STRUCTURE
    """
    pdu_type = 0x06

    def __repr__(self):
        return 'AReleaseRpPDU(reserved1={0}, reserved2={1})'.format(
            self.reserved1, self.reserved2)


class AAbortPDU(object):
    """This class represents the A-ABORT PDU"""
    pdu_type = 0x07
    pdu_length = 0x00000004  # unsigned int
    format = struct.Struct('>B B I B B B B')

    def __init__(self, source, reason_diag, reserved1=0x00, reserved2=0x00,
                 reserved3=0x00):
        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned byte
        self.reserved3 = reserved3  # unsigned byte
        self.source = source  # unsigned byte
        self.reason_diag = reason_diag  # unsigned byte

    def __repr__(self):
        return 'AAbortPDU(source={self.abort_source}, ' \
               'reason_diag={self.reason_diag}, reserved1={self.reserved1}, ' \
               'reserved2={self.reserved2}, ' \
               'reserved3={self.reserved3 = reserved3})'.format(self=self)

    def to_params(self):
        # TODO Remove this method
        return self

    def encode(self):
        return self.format.pack(self.pdu_type, self.reserved1, self.pdu_length,
                                self.reserved2, self.reserved3, self.source,
                                self.reason_diag)

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-ABORT PDU instance from raw string.

        :rtype : AAbortPDU
        :param rawstring: rawstring containing binary representation of
        the A-ABORT PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        _, reserved1, _, reserved2, reserved3, abort_source, \
            reason_diag = cls.format.unpack(stream.read(10))
        return cls(reserved1=reserved1, reserved2=reserved2,
                   reserved3=reserved3, source=abort_source,
                   reason_diag=reason_diag)

    @staticmethod
    def total_length():
        """Returns PDU total length.

        This PDU has a fixed length of 10, so method always returns 10
        regardless of specific instance
        :rtype : int
        :return: PDU total length
        """
        return 10


# Items and sub-items classes


class ApplicationContextItem(object):
    item_type = 0x10
    header = struct.Struct('> B B H')

    def __init__(self, context_name, reserved=0x00):
        self.reserved = reserved  # unsigned byte
        self.context_name = context_name  # string

    def __repr__(self):
        return 'ApplicationContextItem(context_name={0}, reserved={1})'.format(
            self.context_name, self.reserved)

    @property
    def item_length(self):
        return len(self.context_name)

    def encode(self):
        return self.header.pack(self.item_type, self.reserved,
                                self.item_length) + self.context_name

    @classmethod
    def decode(cls, stream):
        """Decodes application context item from data stream

        :rtype : ApplicationContextItem
        :param stream: raw data stream
        :return decoded item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        context_name = stream.read(item_length)
        return cls(reserved=reserved, context_name=context_name)

    def total_length(self):
        return 4 + self.item_length


class PresentationContextItemRQ(object):
    item_type = 0x20
    header = struct.Struct('>B B H B B B B')

    def __init__(self, context_id, abs_sub_item, ts_sub_items, reserved1=0x00,
                 reserved2=0x00, reserved3=0x00, reserved4=0x00):
        self.context_id = context_id  # unsigned byte
        self.abs_sub_item = abs_sub_item  # AbstractSyntaxSubItem
        self.ts_sub_items = ts_sub_items  # TransferSyntaxSubItems

        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned byte
        self.reserved3 = reserved3  # unsigned byte
        self.reserved4 = reserved4  # unsigned byte

    def __repr__(self):
        return 'PresentationContextItemRQ(context_id={self.context_id}, ' \
               'abs_sub_item={self.abs_sub_item}, ' \
               'ts_sub_items={self.ts_sub_items}, ' \
               'reserved1={self.reserved1}, reserved2={self.reserved2}, ' \
               'reserved3={self.reserved3}, ' \
               'reserved4={self.reserved4})'.format(self=self)

    @property
    def item_length(self):
        return 4 + (self.abs_sub_item.total_length() +
                    sum(i.total_length() for i in self.ts_sub_items))

    @classmethod
    def from_params(cls, params):
        # params is a list of the form
        # [ID, AbstractSyntaxName, [TransferSyntaxNames]]
        context_id = params[0]
        abs_sub_item = AbstractSyntaxSubItem.from_params(params[1])
        ts_sub_items = [TransferSyntaxSubItem.from_params(i) for i in params[2]]
        return cls(context_id, abs_sub_item, ts_sub_items)

    def to_params(self):
        # Returns a list of the form
        # [ID, AbstractSyntaxName, [TransferSyntaxNames]]
        return [self.context_id, self.abs_sub_item.to_params(),
                [item.to_params() for item in self.ts_sub_items[1:]]]

    def encode(self):
        return self.header.pack(self.item_type, self.reserved1,
                                self.item_length, self.context_id,
                                self.reserved2, self.reserved3,
                                self.reserved4)\
            + self.abs_sub_item.encode() \
            + ''.join([item.encode() for item in self.ts_sub_items])

    @classmethod
    def decode(cls, stream):
        """Decodes presentation context item 'request' from data stream

        :rtype : PresentationContextItemRQ
        :param stream: raw data stream
        :return: decoded context item
        """
        def iter_items():
            while next_type(stream) == 0x40:
                yield TransferSyntaxSubItem.decode(stream)

        _, reserved1, item_length, context_id, \
            reserved2, reserved3, reserved4 = cls.header.unpack(stream.read(8))
        abs_sub_item = AbstractSyntaxSubItem.decode(stream)
        ts_sub_items = list(iter_items())
        return cls(context_id=context_id, abs_sub_item=abs_sub_item,
                   ts_sub_items=ts_sub_items,
                   reserved1=reserved1, reserved2=reserved2,
                   reserved3=reserved3, reserved4=reserved4)

    def total_length(self):
        return 4 + self.item_length


class PresentationContextItemAC(object):
    item_type = 0x21
    header = struct.Struct('>B B H B B B B')

    def __init__(self, context_id, result_reason, ts_sub_item,
                 reserved1=0x00, reserved2=0x00, reserved3=0x00):
        self.context_id = context_id  # unsigned byte
        self.result_reason = result_reason  # unsigned byte
        self.ts_sub_item = ts_sub_item  # TransferSyntaxSubItem object

        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned byte
        self.reserved3 = reserved3  # unsigned byte

    def __repr__(self):
        return 'PresentationContextItemAC(context_id={self.context_id}, ' \
               'result_reason={self.result_reason}, ' \
               'ts_sub_item={self.ts_sub_item}, reserved1={self.reserved1}, ' \
               'reserved2={self.reserved2}, ' \
               'reserved3={self.reserved3})'.format(self=self)

    @property
    def item_length(self):
        return 4 + self.ts_sub_item.total_length()

    @classmethod
    def from_params(cls, params):
        # params is a list of the form [ID, Response, TransferSyntax].
        ts_sub_item = TransferSyntaxSubItem.from_params(params[2])
        return cls(params[0], params[1], ts_sub_item)

    def to_params(self):
        # Returns a list of the form [ID, Response, TransferSyntax].
        return [self.context_id, self.result_reason,
                self.ts_sub_item.to_params()]

    def encode(self):
        return ''.join([self.header.pack(self.item_type, self.reserved1,
                                         self.item_length, self.context_id,
                                         self.reserved2, self.result_reason,
                                         self.reserved3),
                        self.ts_sub_item.encode()])

    @classmethod
    def decode(cls, stream):
        """Decodes presentation context item 'accepted' from data stream

        :rtype : PresentationContextItemAC
        :param stream: raw data stream
        :return: decoded context item
        """
        _, reserved1, item_length, context_id, reserved2, result_reason, \
            reserved3 = cls.header.unpack(stream.read(8))
        ts_sub_item = TransferSyntaxSubItem.decode(stream)
        return cls(context_id=context_id, result_reason=result_reason,
                   ts_sub_item=ts_sub_item, reserved1=reserved1,
                   reserved2=reserved2, reserved3=reserved3)

    def total_length(self):
        return 4 + self.item_length


class AbstractSyntaxSubItem(object):
    item_type = 0x30
    header = struct.Struct('>B B H')

    def __init__(self, name, reserved=0x00):
        self.reserved = reserved  # unsigned byte
        self.name = name  # string

    def __repr__(self):
        return 'AbstractSyntaxSubItem(name={0}, reserved={1})'.format(
            self.name, self.reserved)

    @property
    def item_length(self):
        return len(self.name)

    @classmethod
    def from_params(cls, params):
        # params is a string
        return cls(params)

    def to_params(self):
        # Returns the abstract syntax name
        return self.name

    def encode(self):
        return ''.join([self.header.pack(self.item_type, self.reserved,
                                         self.item_length),
                        self.name])

    @classmethod
    def decode(cls, stream):
        """Decodes abstract syntax sub-item from data stream

        :rtype : AbstractSyntaxSubItem
        :param stream: raw data stream
        :return: decoded abstract syntax sub-item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        name = stream.read(item_length)
        return cls(name=name, reserved=reserved)

    def total_length(self):
        return 4 + self.item_length


class TransferSyntaxSubItem(object):
    item_type = 0x40
    header = struct.Struct('>B B H')

    def __init__(self, name, reserved=0x00):
        self.reserved = reserved  # unsigned byte
        self.name = name  # string

    def __repr__(self):
        return 'TransferSyntaxSubItem(name={0}, reserved={1})'.format(
            self.name, self.reserved)

    @property
    def item_length(self):
        return len(self.name)

    @classmethod
    def from_params(cls, params):
        # params is a string.
        return cls(params)

    def to_params(self):
        # Returns the transfer syntax name
        return self.name

    def encode(self):
        return ''.join([self.header.pack(self.item_type, self.reserved,
                                         self.item_length),
                        self.name])

    @classmethod
    def decode(cls, stream):
        """Decodes transfer syntax sub-item from data stream

        :rtype : TransferSyntaxSubItem
        :param stream: raw data stream
        :return: decoded transfer syntax sub-item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        name = stream.read(item_length)
        return cls(name=name, reserved=reserved)

    def total_length(self):
        return 4 + self.item_length


class UserInformationItem(object):
    item_type = 0x50
    header = struct.Struct('>B B H')

    def __init__(self, user_data, reserved=0x00):
        self.reserved = reserved  # unsigned byte

        #  user_data is a list containing the following:
        #  1 MaximumLengthItem
        #  0 or more raw strings encoding user data items
        self.user_data = user_data

    def __repr__(self):
        return 'UserInformationItem(user_data={0}, reserved={1})'.format(
            self.user_data, self.reserved)

    @property
    def item_length(self):
        return sum(i.total_length for i in self.user_data)

    @classmethod
    def from_params(cls, params):
        # params is a user_data
        return cls(list(params))

    def to_params(self):
        return list(self.user_data)

    def encode(self):
        return self.header.pack(self.item_type, self.reserved,
                                self.item_length) \
            + ''.join([data.encode() for data in self.user_data])

    @staticmethod
    def sub_items(stream):
        item_type = next_type(stream)
        while item_type:
            try:
                yield SUB_ITEM_TYPES[item_type].decode(stream)
                item_type = next_type(stream)
            except KeyError:
                raise exceptions.PDUProcessingError(
                    'Invalid sub-item', "0x%X" % item_type)

    @classmethod
    def decode(cls, stream):
        """Decodes user information item from data stream

        :rtype : UserInformationItem
        :param stream: raw data stream
        :return: decoded user information item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        # read the rest of user info
        user_data = [sub_item for sub_item in cls.sub_items(stream)]
        return cls(user_data=user_data, reserved=reserved)

    def total_length(self):
        return 4 + self.item_length


class PresentationDataValueItem(object):
    header = struct.Struct('>I B')

    def __init__(self, context_id, data_value):
        self.context_id = context_id  # unsigned byte
        self.data_value = data_value  # string

    def __repr__(self):
        return 'PresentationDataValueItem(context_id={0}, ' \
               'data_value)={1}'.format(
                   self.context_id, self.data_value)

    @property
    def item_length(self):
        return len(self.data_value) + 1

    def encode(self):
        return ''.join([self.header.pack(self.item_length,
                                         self.context_id),
                        self.data_value])

    @classmethod
    def decode(cls, stream):
        """Decodes presentation data value item from data stream

        Presentation data value is left in raw string format.
        The Application Entity is responsible for dealing with it.
        :rtype : PresentationDataValueItem
        :param stream: raw data stream
        :return: decoded presentation data value item
        """
        item_length, context_id = cls.header.unpack(stream.read(5))
        data_value = stream.read(int(item_length) - 1)
        return cls(context_id, data_value)

    def total_length(self):
        return 4 + self.item_length
