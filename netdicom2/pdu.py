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

import itertools
import struct
from cStringIO import StringIO

import netdicom2.dulparameters as dulparameters
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


class AAssociateRqPDU(object):
    """This class represents the A-ASSOCIATE-RQ PDU"""

    def __init__(self, pdu_length, called_ae_title, calling_ae_title, **kwargs):
        self.pdu_type = kwargs.get('pdu_type', 0x01)  # unsigned byte
        self.reserved1 = kwargs.get('reserved1', 0x00)  # unsigned byte
        self.pdu_length = pdu_length  # unsigned int

        # unsigned short
        self.protocol_version = kwargs.get('protocol_version', 1)
        self.reserved2 = kwargs.get('reserved2', 0x00)  # unsigned short
        self.called_ae_title = called_ae_title  # string of length 16
        self.calling_ae_title = calling_ae_title  # string of length 16

        # 32 bytes
        self.reserved3 = kwargs.get('reserved3', (0, 0, 0, 0, 0, 0, 0, 0))

        # variable_items is a list containing the following:
        #   1 ApplicationContextItem
        #   1 or more PresentationContextItemRQ
        #   1 UserInformationItem
        self.variable_items = kwargs.get('variable_items', [])

    def __repr__(self):
        tmp = 'A-ASSOCIATE-RQ PDU {{type: 0x{self.pdu_type:02x}, length: ' \
              '{self.pdu_length:d}, called AE title: {self.called_ae_title},' \
              ' calling AE title: {self.calling_ae_title} '.format(self=self)
        tmp2 = ''.join([repr(item) for item in self.variable_items])
        return '{0} variable items: {1}}}'.format(tmp, tmp2)

    @classmethod
    def from_params(cls, params):
        """Factory method. Create PDU from AAssociateServiceParameters instance

        :rtype : AAssociateRqPDU
        :param params: AAssociateServiceParameters instance
        :return: PDU instance
        """
        variable_items = list(itertools.chain(
            [ApplicationContextItem.from_params(
                params.application_context_name)],
            [PresentationContextItemRQ.from_params(c)
             for c in params.presentation_context_definition_list],
            [UserInformationItem.from_params(params.user_information)]))

        pdu_length = 68 + sum((i.total_length() for i in variable_items))
        return cls(pdu_length, params.called_ae_title, params.calling_ae_title,
                   variable_items=variable_items)

    def to_params(self):
        # Returns an A_ASSOCIATE_ServiceParameters object
        assoc = dulparameters.AAssociateServiceParameters()
        assoc.calling_ae_title = self.calling_ae_title
        assoc.called_ae_title = self.called_ae_title
        assoc.application_context_name = self.variable_items[
            0].application_context_name

        # Write presentation contexts
        for ii in self.variable_items[1:-1]:
            assoc.presentation_context_definition_list.append(ii.to_params())

        # Write user information
        assoc.user_information = self.variable_items[-1].to_params()
        return assoc

    def encode(self):
        return struct.pack('>B B I H H 16s 16s 8I', self.pdu_type,
                           self.reserved1, self.pdu_length,
                           self.protocol_version, self.reserved2,
                           self.called_ae_title,
                           self.calling_ae_title, *self.reserved3) \
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
                elif item_type == 0x50:
                    yield UserInformationItem.decode(stream)
                else:
                    raise exceptions.PDUProcessingError('Invalid variable item')
                item_type = next_type(stream)

        stream = StringIO(rawstring)
        pdu_type, reserved1, pdu_length, protocol_version, \
            reserved2, called_ae_title, \
            calling_ae_title = struct.unpack('> B B I H H 16s 16s',
                                             stream.read(42))
        reserved3 = struct.unpack('> 8I', stream.read(32))
        called_ae_title = called_ae_title.strip('\0')
        calling_ae_title = calling_ae_title.strip('\0')
        variable_items = list(iter_items())
        return cls(pdu_type=pdu_type, reserved1=reserved1,
                   pdu_length=pdu_length, protocol_version=protocol_version,
                   reserved2=reserved2, called_ae_title=called_ae_title,
                   calling_ae_title=calling_ae_title, reserved3=reserved3,
                   variable_items=variable_items)

    def total_length(self):
        return 6 + self.pdu_length


class AAssociateAcPDU(object):
    """This class represents the A-ASSOCIATE-AC PDU"""

    def __init__(self, pdu_length, reserved3, reserved4, **kwargs):
        self.pdu_type = kwargs.get('pdu_type', 0x02)  # unsigned byte
        self.reserved1 = kwargs.get('reserved1', 0x00)  # unsigned byte
        self.pdu_length = pdu_length  # unsigned int

        # unsigned short
        self.protocol_version = kwargs.get('protocol_version', 1)
        self.reserved2 = kwargs.get('reserved2', 0x00)  # unsigned short
        self.reserved3 = reserved3  # string of length 16
        self.reserved4 = reserved4  # string of length 16

        # 32 bytes
        self.reserved5 = kwargs.get('reserved5', (0, 0, 0, 0, 0, 0, 0, 0))

        # variable_items is a list containing the following:
        #   1 ApplicationContextItem
        #   1 or more PresentationContextItemAC
        #   1 UserInformationItem
        self.variable_items = kwargs.get('variable_items', [])

    def __repr__(self):
        tmp = ''.join(['A-ASSOCIATE-AC PDU\n',
                       ' PDU type: 0x%02x\n' % self.pdu_type,
                       ' PDU length: %d\n' % self.pdu_length,
                       ' Called AE title: %s\n' % self.reserved3,
                       ' Calling AE title: %s\n' % self.reserved4])
        tmp2 = ''.join([repr(item) for item in self.variable_items])
        return '%s%s\n' % (tmp, tmp2)

    @classmethod
    def from_params(cls, params):
        """Factory method. Create PDU from AAssociateServiceParameters instance

        :rtype : AAssociateAcPDU
        :param params: AAssociateServiceParameters instance
        :return: PDU instance
        """
        variable_items = list(itertools.chain(
            [ApplicationContextItem.from_params(
                params.application_context_name)],
            [PresentationContextItemAC.from_params(c)
             for c in params.presentation_context_definition_result_list],
            [UserInformationItem.from_params(params.user_information)]))

        pdu_length = 68 + sum((i.total_length() for i in variable_items))
        return cls(pdu_length, params.called_ae_title, params.calling_ae_title,
                   variable_items=variable_items)

    def to_params(self):
        assoc = dulparameters.AAssociateServiceParameters()
        assoc.called_ae_title = self.reserved3
        assoc.calling_ae_title = self.reserved4
        assoc.application_context_name = self.variable_items[0].to_params()

        # Write presentation context
        for ii in self.variable_items[1:-1]:
            assoc.presentation_context_definition_result_list.append(
                ii.to_params())

        # Write user information
        assoc.user_information = self.variable_items[-1].to_params()
        assoc.result = 'Accepted'
        return assoc

    def encode(self):
        return struct.pack('>B B I H H 16s 16s 8I', self.pdu_type,
                           self.reserved1, self.pdu_length,
                           self.protocol_version, self.reserved2,
                           self.reserved3, self.reserved4, *self.reserved5) \
            + ''.join([item.encode() for item in self.variable_items])

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-ASSOCIATE-AC PDU instance from raw string.

        :rtype : AAssociateAcPDU
        :param rawstring: rawstring containing binary representation of the
        A-ASSOCIATE-AC PDU
        :return: decoded PDU
        :raise RuntimeError:
        """
        def iter_items():
            item_type = next_type(stream)
            while item_type:
                if item_type == 0x10:
                    yield ApplicationContextItem.decode(stream)
                elif item_type == 0x21:
                    yield PresentationContextItemAC.decode(stream)
                elif item_type == 0x50:
                    yield UserInformationItem.decode(stream)
                else:
                    raise exceptions.PDUProcessingError('Invalid variable item')
                item_type = next_type(stream)

        stream = StringIO(rawstring)
        pdu_type, reserved1, pdu_length, protocol_version, reserved2, \
            reserved3, reserved4 = struct.unpack('> B B I H H 16s 16s',
                                                 stream.read(42))
        reserved3 = reserved3.strip('\0')
        reserved4 = reserved4.strip('\0')
        reserved5 = struct.unpack('>8I', stream.read(32))
        variable_items = list(iter_items())
        return cls(pdu_type=pdu_type, reserved1=reserved1,
                   pdu_length=pdu_length, protocol_version=protocol_version,
                   reserved2=reserved2, reserved3=reserved3,
                   reserved4=reserved4, reserved5=reserved5,
                   variable_items=variable_items)

    def total_length(self):
        return 6 + self.pdu_length


class AAssociateRjPDU(object):
    """This class represents the A-ASSOCIATE-RJ PDU"""

    def __init__(self, result, source, reason_diag, **kwargs):
        self.pdu_type = kwargs.get('pdu_type', 0x03)  # unsigned byte
        self.reserved1 = kwargs.get('reserved1', 0x00)  # unsigned byte
        self.pdu_length = kwargs.get('pdu_length', 0x00000004)  # unsigned int
        self.reserved2 = kwargs.get('reserved2', 0x00)  # unsigned byte
        self.result = result  # unsigned byte
        self.source = source  # unsigned byte
        self.reason_diag = reason_diag  # unsigned byte

    def __repr__(self):
        return ''.join(['A-ASSOCIATE-RJ PDU\n',
                        ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length,
                        ' Result: %d\n' % self.result,
                        ' Source: %s\n' % str(self.source),
                        ' Reason/Diagnostic: %s\n' % str(self.reason_diag),
                        '\n'])

    @classmethod
    def from_params(cls, params):
        """Factory method. Create PDU from AAssociateServiceParameters instance

        :rtype : AAssociateRjPDU
        :param params: AAssociateServiceParameters instance
        :return: PDU instance
        """
        return cls(params.result, params.result_source, params.diagnostic)

    def to_params(self):
        tmp = dulparameters.AAssociateServiceParameters()
        tmp.result = self.result
        tmp.result_source = self.source
        tmp.diagnostic = self.reason_diag
        return tmp

    def encode(self):
        return struct.pack('>B B I B B B B', self.pdu_type, self.reserved1,
                           self.pdu_length, self.reserved2, self.result,
                           self.source, self.reason_diag)

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-ASSOCIATE-RJ PDU instance from raw string.

        :rtype : AAssociateRjPDU
        :param rawstring: rawstring containing binary representation of the
        A-ASSOCIATE-RJ PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        pdu_type, reserved1, pdu_length, reserved2, result, source, \
            reason_diag = struct.unpack('> B B I B B B B', stream.read(10))
        return cls(pdu_type=pdu_type, reserved1=reserved1,
                   pdu_length=pdu_length, reserved2=reserved2,
                   result=result, source=source, reason_diag=reason_diag)

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

    def __init__(self, pdu_length, presentation_data_value_items, **kwargs):
        self.pdu_type = kwargs.get('pdu_type', 0x04)  # unsigned byte
        self.reserved = kwargs.get('reserved', 0x00)  # unsigned byte
        self.pdu_length = pdu_length  # unsigned int

        # List of one of more PresentationDataValueItem
        self.presentation_data_value_items = presentation_data_value_items

    def __repr__(self):
        tmp = ''.join(['P-DATA-TF PDU\n', ' PDU type: 0x%02x\n' % self.pdu_type,
                       ' PDU length: %d\n' % self.pdu_length])
        tmp2 = ''.join(repr(item)
                       for item in self.presentation_data_value_items)
        return '%s%s\n' % (tmp, tmp2)

    @classmethod
    def from_params(cls, params):
        """Factory method. Create PDU from PDataServiceParameters instance

        :rtype : PDataTfPDU
        :param params: PDataServiceParameters instance
        :return: PDU instance
        """
        value_items = [PresentationDataValueItem.from_params(v)
                       for v in params.presentation_data_value_list]
        pdu_length = sum((i.total_length() for i in value_items))
        return cls(pdu_length, value_items)

    def to_params(self):
        tmp = dulparameters.PDataServiceParameters()
        tmp.presentation_data_value_list = [[i.presentation_context_id,
                                             i.presentation_data_value]
                                            for i in
                                            self.presentation_data_value_items]
        return tmp

    def encode(self):
        return struct.pack('>B B I', self.pdu_type, self.reserved,
                           self.pdu_length)\
            + ''.join([item.encode()
                       for item in self.presentation_data_value_items])

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
        pdu_type, reserved, pdu_length = struct.unpack('> B B I',
                                                       stream.read(6))
        presentation_data_value_items = list(iter_items())
        return cls(pdu_type=pdu_type, reserved=reserved, pdu_length=pdu_length,
                   presentation_data_value_items=presentation_data_value_items)

    def total_length(self):
        return 6 + self.pdu_length


class AReleaseRqPDU(object):
    """This class represents the A-RELEASE-RQ PDU"""

    def __init__(self, **kwargs):
        self.pdu_type = kwargs.get('pdu_type', 0x05)  # unsigned byte
        self.reserved1 = kwargs.get('reserved1', 0x00)  # unsigned byte
        self.pdu_length = kwargs.get('pdu_length', 0x00000004)  # unsigned int
        self.reserved2 = kwargs.get('reserved2', 0x00000000)  # unsigned int

    def __repr__(self):
        return ''.join(['A-RELEASE-RQ PDU\n',
                        ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length, '\n'])

    @staticmethod
    def to_params():
        """Converts PDU to service parameters.

        Note that method is static, because A-RELEASE-RQ PDU has no
        variable parameters.
        :return: PDU converted to service parameters
        """
        tmp = dulparameters.AReleaseServiceParameters()
        tmp.reason = 'normal'
        tmp.result = 'affirmative'
        return tmp

    def encode(self):
        return struct.pack('>B B I I', self.pdu_type, self.reserved1,
                           self.pdu_length, self.reserved2)

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-RELEASE-RQ PDU instance from raw string.

        :rtype : AReleaseRqPDU
        :param rawstring: rawstring containing binary representation of the
        A-RELEASE-RQ PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        pdu_type, reserved1, pdu_length, \
            reserved2 = struct.unpack('> B B I I', stream.read(10))
        return cls(pdu_type=pdu_type, reserved1=reserved1,
                   pdu_length=pdu_length, reserved2=reserved2)

    @staticmethod
    def total_length():
        """Returns PDU total length.

        This PDU has a fixed length of 10, so method always returns 10
        regardless of specific instance
        :rtype : int
        :return: PDU total length
        """
        return 10


class AReleaseRpPDU(object):
    """This class represents the A-RELEASE-RP PDU"""

    def __init__(self, **kwargs):
        self.pdu_type = kwargs.get('pdu_type', 0x06)   # unsigned byte
        self.reserved1 = kwargs.get('reserved1', 0x00)  # unsigned byte
        self.pdu_length = kwargs.get('pdu_length', 0x00000004)  # unsigned int
        self.reserved2 = kwargs.get('reserved2', 0x00000000)  # unsigned int

    def __repr__(self):
        return ''.join(['A-RELEASE-RP PDU\n',
                        ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length + '\n'])

    @staticmethod
    def to_params():
        """Converts PDU to service parameters.

        Note that method is static, because A-RELEASE-RP PDU has no
        variable parameters.
        :return: PDU converted to service parameters
        """
        tmp = dulparameters.AReleaseServiceParameters()
        tmp.reason = 'normal'
        tmp.result = 'affirmative'
        return tmp

    def encode(self):
        return struct.pack('>B B I I', self.pdu_type, self.reserved1,
                           self.pdu_length, self.reserved2)

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-RELEASE-RP PDU instance from raw string.

        :rtype : AReleaseRpPDU
        :param rawstring: rawstring containing binary representation of the
        A-RELEASE-RP PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        pdu_type, reserved1, pdu_length, \
            reserved2 = struct.unpack('> B B I I', stream.read(10))
        return cls(pdu_type=pdu_type, reserved1=reserved1,
                   pdu_length=pdu_length, reserved2=reserved2)

    @staticmethod
    def total_length():
        """Returns PDU total length.

        This PDU has a fixed length of 10, so method always returns 10
        regardless of specific instance
        :rtype : int
        :return: PDU total length
        """
        return 10


class AAbortPDU(object):
    """This class represents the A-ABORT PDU"""

    def __init__(self, source, reason, **kwargs):
        self.pdu_type = kwargs.get('pdu_type', 0x07)  # unsigned byte
        self.reserved1 = kwargs.get('reserved1', 0x00)  # unsigned byte
        self.pdu_length = kwargs.get('pdu_length', 0x00000004)  # unsigned int
        self.reserved2 = kwargs.get('reserved2', 0x00)  # unsigned byte
        self.reserved3 = kwargs.get('reserved3', 0x00)  # unsigned byte
        self.abort_source = source  # unsigned byte
        self.reason_diag = reason  # unsigned byte

    def __repr__(self):
        return ''.join(['A-ABORT PDU\n', ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length,
                        ' Abort Source: %d\n' % self.abort_source,
                        ' Reason/Diagnostic: %d\n' % self.reason_diag, '\n'])

    @classmethod
    def from_params(cls, params):
        # params can be an AAbortServiceParameters or
        # APAbortServiceParameters object.
        try:  # User initiated abort
            return cls(params.abort_source, 0)
        except AttributeError:  # User provider initiated abort
            return cls(0, params.provider_reason)

    def to_params(self):
        # Returns either a A-ABORT of an A-P-ABORT
        if self.abort_source is not None:
            tmp = dulparameters.AAbortServiceParameters()
            tmp.abort_source = self.abort_source
        elif self.reason_diag is not None:
            tmp = dulparameters.APAbortServiceParameters()
            tmp.provider_reason = self.reason_diag
        else:
            raise RuntimeError('Unknown abort source')
        return tmp

    def encode(self):
        return struct.pack('>B B I B B B B', self.pdu_type, self.reserved1,
                           self.pdu_length, self.reserved2, self.reserved3,
                           self.abort_source, self.reason_diag)

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-ABORT PDU instance from raw string.

        :rtype : AAbortPDU
        :param rawstring: rawstring containing binary representation of
        the A-ABORT PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        pdu_type, reserved1, pdu_length, reserved2, reserved3, abort_source, \
            reason_diag = struct.unpack('> B B I B B B B', stream.read(10))
        return cls(pdu_type=pdu_type, reserved1=reserved1,
                   pdu_length=pdu_length, reserved2=reserved2,
                   reserved3=reserved3, abort_source=abort_source,
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
    def __init__(self, item_length, application_context_name, **kwargs):
        self.item_type = kwargs.get('item_type', 0x10)  # unsigned byte
        self.reserved = kwargs.get('reserved', 0x00)  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.application_context_name = application_context_name  # string

    def __repr__(self):
        return ''.join([' Application context item\n',
                        '  Item type: 0x%02x\n' % self.item_type,
                        '  Item length: %d\n' % self.item_length,
                        '  Presentation context ID: %s\n' %
                        self.application_context_name])

    @classmethod
    def from_params(cls, params):
        # Params is a string
        return cls(len(params), params)

    def to_params(self):
        # Returns the application context name
        return self.application_context_name

    def encode(self):
        return struct.pack('>B B H', self.item_type, self.reserved,
                           self.item_length) + self.application_context_name

    @classmethod
    def decode(cls, stream):
        """Decodes application context item from data stream

        :rtype : ApplicationContextItem
        :param stream: raw data stream
        :return decoded item
        """
        item_type, reserved, item_length = struct.unpack('> B B H',
                                                         stream.read(4))
        application_context_name = stream.read(item_length)
        return cls(item_type=item_type, reserved=reserved,
                   item_length=item_length,
                   application_context_name=application_context_name)

    def total_length(self):
        return 4 + self.item_length


class PresentationContextItemRQ(object):
    def __init__(self, item_length, presentation_context_id,
                 abstract_transfer_syntax_sub_items, **kwargs):
        self.item_type = kwargs.get('item_type', 0x20)  # unsigned byte
        self.reserved1 = kwargs.get('reserved1', 0x00)  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.presentation_context_id = presentation_context_id  # unsigned byte

        self.reserved2 = kwargs.get('reserved2', 0x00)  # unsigned byte
        self.reserved3 = kwargs.get('reserved3', 0x00)  # unsigned byte
        self.reserved4 = kwargs.get('reserved4', 0x00)  # unsigned byte

        # abstract_transfer_syntax_sub_items is a list
        # containing the following elements:
        #  - one AbstractSyntaxSubItem
        #  - one of more TransferSyntaxSubItem
        self.abstract_transfer_syntax_sub_items = abstract_transfer_syntax_sub_items

    def __repr__(self):
        tmp = ''.join([" Presentation context RQ item\n",
                       "  Item type: 0x%02x\n" % self.item_type,
                       "  Item length: %d\n" % self.item_length,
                       "  Presentation context ID: %d\n" %
                       self.presentation_context_id])
        tmp2 = ''.join([repr(item)
                        for item in self.abstract_transfer_syntax_sub_items])
        return tmp + tmp2

    @classmethod
    def from_params(cls, params):
        # params is a list of the form
        # [ID, AbstractSyntaxName, [TransferSyntaxNames]]
        ts_sub_items = [AbstractSyntaxSubItem.from_params(params[1])] +\
                       [TransferSyntaxSubItem.from_params(i) for i in params[2]]
        item_length = 4 + sum(i.total_length() for i in ts_sub_items)
        return cls(item_length, params[0], ts_sub_items)

    def to_params(self):
        # Returns a list of the form
        # [ID, AbstractSyntaxName, [TransferSyntaxNames]]
        return [self.presentation_context_id,
                self.abstract_transfer_syntax_sub_items[0].to_params(),
                [item.to_params()
                 for item in self.abstract_transfer_syntax_sub_items[1:]]]

    def encode(self):
        return struct.pack('>B B H B B B B', self.item_type, self.reserved1,
                           self.item_length, self.presentation_context_id,
                           self.reserved2, self.reserved3, self.reserved4)\
            + ''.join([item.encode()
                       for item in self.abstract_transfer_syntax_sub_items])

    @classmethod
    def decode(cls, stream):
        """Decodes presentation context item 'request' from data stream

        :rtype : PresentationContextItemRQ
        :param stream: raw data stream
        :return: decoded context item
        """
        def iter_items():
            yield AbstractSyntaxSubItem.decode(stream)
            next_item_type = next_type(stream)
            while next_item_type == 0x40:
                yield TransferSyntaxSubItem.decode(stream)
                next_item_type = next_type(stream)

        item_type, reserved1, item_length, presentation_context_id, \
            reserved2, reserved3, \
            reserved4 = struct.unpack('> B B H B B B B', stream.read(8))
        abstract_transfer_syntax_sub_items = list(iter_items())
        return cls(item_type=item_type, reserved1=reserved1,
                   item_length=item_length,
                   presentation_context_id=presentation_context_id,
                   reserved2=reserved2, reserved3=reserved3,
                   reserved4=reserved4,
                   abstract_transfer_syntax_sub_items=abstract_transfer_syntax_sub_items)

    def total_length(self):
        return 4 + self.item_length


class PresentationContextItemAC(object):
    def __init__(self, item_length, presentation_context_id, result_reason,
                 transfer_syntax_sub_item, **kwargs):
        self.item_type = kwargs.get('item_type', 0x21)  # unsigned byte
        self.reserved1 = kwargs.get('reserved1', 0x00)  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.presentation_context_id = presentation_context_id  # unsigned byte
        self.reserved2 = kwargs.get('reserved2', 0x00)  # unsigned byte
        self.result_reason = result_reason  # unsigned byte
        self.reserved3 = kwargs.get('reserved3', 0x00)  # unsigned byte

        # TransferSyntaxSubItem object
        self.transfer_syntax_sub_item = transfer_syntax_sub_item

    def __repr__(self):
        return ''.join([' Presentation context AC item\n',
                        '  Item type: 0x%02x\n' % self.item_type,
                        '  Item length: %d\n' % self.item_length,
                        '  Presentation context ID: %d\n' %
                        self.presentation_context_id,
                        '  Result/Reason: %d\n' % self.result_reason,
                        repr(self.transfer_syntax_sub_item)])

    @classmethod
    def from_params(cls, params):
        # params is a list of the form [ID, Response, TransferSyntax].
        ts_sub_item = TransferSyntaxSubItem.from_params(params[2])
        item_length = 4 + ts_sub_item.total_length()
        return cls(item_length, params[0], params[1], ts_sub_item)

    def to_params(self):
        # Returns a list of the form [ID, Response, TransferSyntax].
        return [self.presentation_context_id, self.result_reason,
                self.transfer_syntax_sub_item.to_params()]

    def encode(self):
        return ''.join([struct.pack('>B B H B B B B', self.item_type,
                                    self.reserved1, self.item_length,
                                    self.presentation_context_id,
                                    self.reserved2, self.result_reason,
                                    self.reserved3),
                        self.transfer_syntax_sub_item.encode()])

    @classmethod
    def decode(cls, stream):
        """Decodes presentation context item 'accepted' from data stream

        :rtype : PresentationContextItemAC
        :param stream: raw data stream
        :return: decoded context item
        """
        item_type, reserved1, item_length, presentation_context_id, \
            reserved2, result_reason, \
            reserved3 = struct.unpack('> B B H B B B B', stream.read(8))
        transfer_syntax_sub_item = TransferSyntaxSubItem.decode(stream)
        return cls(item_type=item_type, reserved1=reserved1,
                   item_length=item_length,
                   presentation_context_id=presentation_context_id,
                   reserved2=reserved2, result_reason=result_reason,
                   reserved3=reserved3,
                   transfer_syntax_sub_item=transfer_syntax_sub_item)

    def total_length(self):
        return 4 + self.item_length


class AbstractSyntaxSubItem(object):
    def __init__(self, item_length, abstract_syntax_name, **kwargs):
        self.reserved = kwargs.get('reserved', 0x00)  # unsigned byte
        self.item_type = kwargs.get('item_type', 0x30)  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.abstract_syntax_name = abstract_syntax_name  # string

    def __repr__(self):
        return ''.join(['  Abstract syntax sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   Abstract syntax name: %s\n' %
                        self.abstract_syntax_name])

    @classmethod
    def from_params(cls, params):
        # params is a string
        return cls(len(params), params)

    def to_params(self):
        # Returns the abstract syntax name
        return self.abstract_syntax_name

    def encode(self):
        return ''.join([struct.pack('>B B H', self.item_type, self.reserved,
                                    self.item_length),
                        self.abstract_syntax_name])

    @classmethod
    def decode(cls, stream):
        """Decodes abstract syntax sub-item from data stream

        :rtype : AbstractSyntaxSubItem
        :param stream: raw data stream
        :return: decoded abstract syntax sub-item
        """
        item_type, reserved, item_length = struct.unpack('> B B H',
                                                         stream.read(4))
        abstract_syntax_name = stream.read(item_length)
        return cls(item_type=item_type, reserved=reserved,
                   item_length=item_length,
                   abstract_syntax_name=abstract_syntax_name)

    def total_length(self):
        return 4 + self.item_length


class TransferSyntaxSubItem(object):
    def __init__(self, item_length, transfer_syntax_name, **kwargs):
        self.item_type = kwargs.get('item_type', 0x40)  # unsigned byte
        self.reserved = kwargs.get('reserved', 0x00)  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.transfer_syntax_name = transfer_syntax_name  # string

    def __repr__(self):
        return ''.join(['  Transfer syntax sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   Transfer syntax name: %s\n' %
                        self.transfer_syntax_name])

    @classmethod
    def from_params(cls, params):
        # params is a string.
        return cls(len(params), params)

    def to_params(self):
        # Returns the transfer syntax name
        return self.transfer_syntax_name

    def encode(self):
        return ''.join([struct.pack('>B B H', self.item_type, self.reserved,
                                    self.item_length),
                        self.transfer_syntax_name])

    @classmethod
    def decode(cls, stream):
        """Decodes transfer syntax sub-item from data stream

        :rtype : TransferSyntaxSubItem
        :param stream: raw data stream
        :return: decoded transfer syntax sub-item
        """
        item_type, reserved, \
            item_length = struct.unpack('> B B H', stream.read(4))
        transfer_syntax_name = stream.read(item_length)
        return cls(item_type=item_type, reserved=reserved,
                   item_length=item_length,
                   transfer_syntax_name=transfer_syntax_name)

    def total_length(self):
        return 4 + self.item_length


class UserInformationItem(object):
    def __init__(self, user_data, **kwargs):
        self.item_type = kwargs.get('item_type', 0x50)  # unsigned byte
        self.reserved = kwargs.get('reserved', 0x00)  # unsigned byte

        # unsigned short
        self.item_length = sum(i.total_length for i in user_data)

        #  user_data is a list containing the following:
        #  1 MaximumLengthItem
        #  0 or more raw strings encoding user data items
        # List of sub items
        self.user_data = user_data

    def __repr__(self):
        tmp = [' User information item\n',
               '  Item type: 0x%02x\n' % self.item_type,
               '  Item length: %d\n' % self.item_length, '  User Data:\n ']
        if len(self.user_data) > 1:
            tmp.append(str(self.user_data[0]))
            for ii in self.user_data[1:]:
                tmp.append('   User Data Item: ' + str(ii) + "\n")
        return ''.join(tmp)

    @classmethod
    def from_params(cls, params):
        # params is a user_data
        return cls(list(params))

    def to_params(self):
        return list(self.user_data)

    def encode(self):
        return struct.pack('>B B H', self.item_type, self.reserved,
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

        item_type, reserved, \
            item_length = struct.unpack('> B B H', stream.read(4))

        # read the rest of user info
        user_data = [sub_item for sub_item in cls.sub_items(stream)]
        return cls(item_type=item_type, reserved=reserved, user_data=user_data)

    def total_length(self):
        return 4 + self.item_length


class PresentationDataValueItem(object):
    def __init__(self, presentation_context_id, presentation_data_value):
        self.item_length = len(presentation_data_value) + 1  # unsigned int
        self.presentation_context_id = presentation_context_id  # unsigned byte
        self.presentation_data_value = presentation_data_value  # string

    def __repr__(self):
        return ''.join([' Presentation value data item\n',
                        '  Item length: %d\n' % self.item_length,
                        '  Presentation context ID: %d\n' %
                        self.presentation_context_id,
                        '  Presentation data value: %s ...\n' %
                        self.presentation_data_value[:20]])

    @classmethod
    def from_params(cls, params):
        # takes a PresentationDataValue object
        return cls(params[0], params[1])

    def to_params(self):
        # Returns a PresentationDataValue
        return PresentationDataValueItem(self.presentation_context_id,
                                         self.presentation_data_value)

    def encode(self):
        return ''.join([struct.pack('>I B', self.item_length,
                                    self.presentation_context_id),
                        self.presentation_data_value])

    @classmethod
    def decode(cls, stream):
        """Decodes presentation data value item from data stream

        Presentation data value is left in raw string format.
        The Application Entity is responsible for dealing with it.
        :rtype : PresentationDataValueItem
        :param stream: raw data stream
        :return: decoded presentation data value item
        """
        item_length, \
            presentation_context_id = struct.unpack('> I B', stream.read(5))

        presentation_data_value = stream.read(int(item_length) - 1)
        return cls(presentation_context_id, presentation_data_value)

    def total_length(self):
        return 4 + self.item_length


class GenericUserDataSubItem(object):
    """
    This class is provided only to allow user data to converted to and from
    PDUs. The actual data is not interpreted. This is left to the user.
    """

    def __init__(self, item_type, user_data, reserved=0x00):
        self.item_type = item_type  # unsigned byte
        self.reserved = reserved  # unsigned byte
        self.item_length = len(user_data)  # unsigned short
        self.user_data = user_data  # raw string

    def __repr__(self):
        tmp = ['User data item\n', '  Item type: %d\n' % self.item_type,
               '  Item length: %d\n' % self.item_length]
        if len(self.user_data) > 1:
            tmp.append('  User data: %s ...\n' % self.user_data[:10])
        return ''.join(tmp)

    @classmethod
    def from_params(cls, params):
        return cls(params.item_type, params.user_data)

    def to_params(self):
        return GenericUserDataSubItem(item_type=self.item_type,
                                      user_data=self.user_data)

    def encode(self):
        return ''.join([struct.pack('>B B H', self.item_type, self.reserved,
                                    self.item_length), self.user_data])

    @classmethod
    def decode(cls, stream):
        """Decodes generic data sub-item from data stream

        User data value is left in raw string format. The Application Entity
        is responsible for dealing with it.
        :rtype : GenericUserDataSubItem
        :param stream: raw data stream
        :return: decoded generic data sub-item
        """
        item_type, reserved, item_length = struct.unpack('> B B H',
                                                         stream.read(4))
        user_data = stream.read(int(item_length))
        return cls(item_type=item_type, user_data=user_data, reserved=reserved)

    def total_length(self):
        return 4 + self.item_length
