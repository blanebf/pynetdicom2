# Copyright (c) 2014 Pavel 'Blane' Tuchin
# This file is part of pynetdicom2, released under a modified MIT license.
#    See the file license.txt included with this distribution.

"""
TODO: N-GET, N-SET, N-CREATE, N-DELETE
+-----------------+---------+------+---------------------------------------------------------+-------------------------+
| Service/Command | Status  | Code | Description                                             |  Related Attributes     |
+=================+=========+======+=========================================================+=========================+
| C-ECHO          | Success | 0000 |                                                         |                         |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Failure | 0122 | Refused: SOP Class Not Supported                        |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0210 | Duplicate Invocation                                    |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0212 | Mistyped argument                                       |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0211 | Unrecognized Operation                                  |                         |
+-----------------+---------+------+---------------------------------------------------------+-------------------------+
| C-STORE         | Failure | A7xx | Refused: Out of Resources                               | (0000,0902)             |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | A9xx | Error: Data Set does not match SOP Class                | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | Cxxx | Error: Cannot understand                                | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0112 | Failed: SOP Class Not Supported                         |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0210 | Duplicate Invocation                                    |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0117 | Invalid Object Instance                                 |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0212 | Mistyped argument                                       |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0211 | Unrecognized Operation                                  |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0124 | Refused: Not Authorized                                 |                         |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Warning | B000 | Coercion of Data Elements                               | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | B007 | Data Set does not match SOP Class                       | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | B006 | Elements Discarded                                      | (0000,0901) (0000,0902) |
\                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Success | 0000 | Success                                                 |                         |
+-----------------+---------+------+---------------------------------------------------------+-------------------------+
| C-FIND          | Failure | A700 | Refused: Out of Resources                               | (0000,0902)             |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | A900 | Error: Data Set does not match SOP Class                | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | Cxxx | Failed: Unable to process                               | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0112 | Failed: SOP Class Not Supported                         |                         |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Cancel  | FE00 | Matching terminated due to Cancel request               |                         |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Success | 0000 | Matching is complete - No final Identifier is supplied. |                         |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Pending | FF00 | Matches are continuing - Current Match is supplied and  |                         |
|                 |         |      | any Optional Keys were supported in the same manner as  |                         |
|                 |         |      | Required Keys.                                          |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | FF01 | Matches are continuing - Warning that one or more       |                         |
|                 |         |      | Optional Keys were not supported for existence and/or   |                         |
|                 |         |      | matching for this Identifier.                           |                         |
+-----------------+---------+------+---------------------------------------------------------+-------------------------+
| C-GET           | Failure | A701 | Refused: Out of Resources - Unable to calculate number  | (0000,0902)             |
|                 |         |      | of matches                                              |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | A702 | Refused: Out of Resources - Unable to perform           | (0000,1021) (0000,1022) |
|                 |         |      | sub-operations                                          | (0000,1023)             |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | A900 | Error: Data Set does not match SOP Class                | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | Cxxx | Failed: Unable to process                               | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0112 | Failed: SOP Class Not Supported                         |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0210 | Duplicate Invocation                                    |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0212 | Mistyped argument                                       |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0211 | Unrecognized Operation                                  |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0124 | Refused: Not Authorized                                 |                         |
|                 |---------+------+---------------------------------------------------------+-------------------------+
|                 | Cancel  | FE00 | Cancel Sub-operations terminated due to Cancel          | (0000,1020) (0000,1021) |
|                 |         |      | Indication                                              | (0000,1022) (0000,1023) |
|                 |---------+------+---------------------------------------------------------+-------------------------+
|                 | Warning | B000 | Sub-operations Complete - One or more Failures or       | (0000,1021) (0000,1022) |
|                 |         |      | Warnings                                                | (0000,1023)             |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Success | 0000 | Sub-operations Complete - No Failures or Warnings       | (0000,1021) (0000,1022) |
|                 |         |      |                                                         | (0000,1023)             |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Pending | FF00 | Sub-operations are continuing                           | (0000,1020) (0000,1021) |
|                 |         |      |                                                         | (0000,1022) (0000,1023) |
+-----------------+---------+------+---------------------------------------------------------+-------------------------+
| C-MOVE          | Failure | A701 | Refused: Out of Resources - Unable to calculate number  | (0000,0902)             |
|                 |         |      | of matches                                              |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | A702 | Refused: Out of Resources - Unable to perform           | (0000,1020) (0000,1021) |
|                 |         |      | sub-operations                                          | (0000,1022) (0000,1023) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | A801 | Refused: Move Destination unknown                       | (0000,0902)             |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | A900 | Error: Data Set does not match SOP Class                | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | Cxxx | Failed: Unable to process                               | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | AA00 | Failed: None of the frames requested were found in the  | (0000,0902)             |
|                 |         |      | SOP Instance                                            |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | AA01 | Failed: Unable to create new object for this SOP class  | (0000,0902)             |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | AA02 | Failed: Unable to extract frames                        | (0000,0902)             |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | AA03 | Failed: Time-based request received for a               | (0000,0902)             |
|                 |         |      | non-time-based original SOP Instance.                   |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | AA04 | Failed: Invalid Request                                 | (0000,0901) (0000,0902) |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0112 | Failed: SOP Class Not Supported                         |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0210 | Duplicate Invocation                                    |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0212 | Mistyped argument                                       |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0211 | Unrecognized Operation                                  |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0124 | Refused: Not Authorized                                 |                         |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Cancel  | FE00 | Sub-operations terminated due to Cancel Indication      | (0000,1020) (0000,1021) |
|                 |         |      |                                                         | (0000,1022) (0000,1023) |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Warning | B000 | Sub-operations Complete - One or more Failures or       | (0000,1020) (0000,1021) |
|                 |         |      | Warnings                                                | (0000,1022) (0000,1023) |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Success | 0000 | Sub-operations Complete - No Failures or Warnings       | (0000,1020) (0000,1021) |
|                 |         |      |                                                         | (0000,1022) (0000,1023) |
|                 +---------+------+---------------------------------------------------------+-------------------------+
|                 | Pending | FF00 | Sub-operations are continuing                           | (0000,1020) (0000,1021) |
|                 |         |      |                                                         | (0000,1022) (0000,1023) |
+-----------------+---------+------+---------------------------------------------------------+-------------------------+
| N-EVENT-REPORT  | Failure | 0119 | Class-Instance Conflict                                 |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0210 | Duplicate Invocation                                    | (0000,0110)             |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0115 | Invalid Argument Value                                  |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0117 | Invalid Object Instance                                 |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0212 | Mistyped Argument                                       |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0114 | No Such Argument                                        |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0113 | No Such Event Type                                      |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0118 | No Such SOP Class                                       |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0112 | No Such SOP Instance                                    |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0110 | Processing Failure                                      |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0213 | Resource Limitation                                     |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0211 | Unrecognized Operation                                  |                         |
+-----------------+---------+------+---------------------------------------------------------+-------------------------+
| N-ACTION        | Failure | 0119 | Class-Instance Conflict                                 |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0210 | Duplicate Invocation                                    | (0000,0110)             |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0115 | Invalid Argument Value                                  |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0117 | Invalid Object Instance                                 |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0212 | Mistyped Argument                                       |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0123 | No Such Action                                          |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0114 | No Such Argument                                        |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0118 | No Such SOP Class                                       |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0112 | No Such SOP Instance                                    |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0110 | Processing Failure                                      |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0213 | Resource Limitation                                     |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0211 | Unrecognized Operation                                  |                         |
|                 |         +------+---------------------------------------------------------+-------------------------+
|                 |         | 0124 | Refused: Not Authorized                                 |                         |
+-----------------+---------+------+---------------------------------------------------------+-------------------------+

"""

__author__ = 'Blane'
from collections import namedtuple

from . import dimsemessages as dimse

s = namedtuple('status', ['code_type', 'description'])


_general_status_dict = {}

_status_dict = {}


UNKONWN = s('Failure', 'Unknown Status')


def add_status(code, code_type, description, end=None, command=None):
    status = s(code_type, description)
    if end is not None:
        code_range = range(code, end + 1)
    else:
        code_range = [code]

    if command is None:
        for _code in code_range:
            _general_status_dict[_code] = status
    else:
        for _code in code_range:
            _status_dict[(command.command_field, _code)] = status


class Status(int):
    """Class represents message status.

    This is a helper class that provides convenience methods for printing status codes.
    """

    def __init__(self, value, command=None):
        """Initializes new Status .

        :param value status code
        :param command: command for which status is created. Some codes depends on the
                        type of service.
        """
        int.__init__(self, value)
        if command:
            status = _status_dict.get((command.command_field, value), UNKONWN)
        else:
            status = _general_status_dict.get(value, UNKONWN)
        self.status_type = status.code_type
        self.description = status.description
        self.is_success = self.status_type == 'Success'
        self.is_pending = self.status_type == 'Pending'
        self.is_failure = self.status_type == 'Failure'
        self.is_warning = self.status_type == 'Warning'
        self.is_cancel = self.status_type == 'Cancel'

    def __str__(self):
        return '(self) {self.status_type}: self.description'.format(self=self)

    def __repr__(self):
        """Returns status string representation

        :return: status string representation
        """
        return 'Status({self.value})'.format(self=self)


KNOWN_STATUSES = [
    (0x0000, 'Success', '', None),
    (0x0110, 'Failure', 'Processing Failure', None),
    (0x0112, 'Failure', 'Failed: SOP Class Not Supported', None),
    (0x0112, 'Failure', 'No Such SOP Instance', dimse.NEventReportRSPMessage),
    (0x0112, 'Failure', 'No Such SOP Instance', dimse.NActionRSPMessage),
    (0x0113, 'Failure', 'No Such Event Type', None),
    (0x0114, 'Failure', 'No Such Argument', None),
    (0x0115, 'Failure', 'Invalid Argument Value', None),
    (0x0117, 'Failure', 'Invalid Object Instance', None),
    (0x0118, 'Failure', 'No Such SOP Class', None),
    (0x0119, 'Failure', 'Class-Instance Conflict', None),
    (0x0122, 'Failure', 'Refused: SOP Class Not Supported', None),
    (0x0123, 'Failure', 'No Such Action', None),
    (0x0124, 'Failure', 'Refused: Not Authorized', None),
    (0x0210, 'Failure', 'Duplicate Invocation', None),
    (0x0211, 'Failure', 'Unrecognized Operation', None),
    (0x0212, 'Failure', 'Mistyped argument', None),
    (0x0213, 'Failure', 'Resource Limitation', None),

    # C-STORE
    ((0xA700, 0xA7FF), 'Failure', 'Refused: Out of Resources', dimse.CStoreRSPMessage),
    ((0xA900, 0xA9FF), 'Failure', 'Error: Data Set does not match SOP Class', dimse.CStoreRSPMessage),
    ((0xC000, 0xCFFF), 'Failure', 'Error: Cannot understand', dimse.CStoreRSPMessage),
    (0xB000, 'Warning', 'Coercion of Data Elements', dimse.CStoreRSPMessage),
    (0xB007, 'Warning', 'Data Set does not match SOP Class', dimse.CStoreRSPMessage),
    (0xB006, 'Warning', 'Elements Discarded', dimse.CStoreRSPMessage),

    # C-FIND
    (0xA700, 'Failure', 'Refused: Out of Resources', dimse.CFindRSPMessage),
    (0xA900, 'Failure', 'Error: Data Set does not match SOP Class', dimse.CFindRSPMessage),
    ((0xC000, 0xCFFF), 'Failure', 'Failed: Unable to process', dimse.CFindRSPMessage),
    (0xFF00, 'Pending', 'Matches are continuing - Current Match is supplied and any Optional Keys were supported '
                        'in the same manner as Required Keys.', dimse.CFindRSPMessage),
    (0xFF01, 'Pending', 'Matches are continuing - Warning that one or more Optional Keys were not '
                        'supported for existence and/or matching for this Identifier.', dimse.CFindRSPMessage),

    # C-GET
    (0xA701, 'Failure', 'Refused: Out of Resources - Unable to calculate number of matches', dimse.CGetRSPMessage),
    (0xA702, 'Failure', 'Refused: Out of Resources - Unable to perform sub-operations', dimse.CGetRSPMessage),
    (0xA900, 'Failure', 'Error: Data Set does not match SOP Class', dimse.CGetRSPMessage),
    ((0xC000, 0xCFFF), 'Failure', 'Failed: Unable to process', dimse.CGetRSPMessage),
    (0xB000, 'Warning', 'Sub-operations Complete - One or more Failures or Warnings', dimse.CGetRSPMessage),
    (0xFF00, 'Pending', 'Sub-operations are continuing', dimse.CGetRSPMessage),

    # C-MOVE
    (0xA701, 'Failure', 'Refused: Out of Resources - Unable to calculate number of matches', dimse.CMoveRSPMessage),
    (0xA702, 'Failure', 'Refused: Out of Resources - Unable to perform sub-operations', dimse.CMoveRSPMessage),
    (0xA801, 'Failure', 'Refused: Move Destination unknown', dimse.CMoveRSPMessage),
    (0xA900, 'Failure', 'Error: Data Set does not match SOP Class', dimse.CMoveRSPMessage),
    ((0xC000, 0xCFFF), 'Failure', 'Failed: Unable to process', dimse.CMoveRSPMessage),
    (0xAA00, 'Failure', 'Failed: None of the frames requested were found in the SOP Instance', dimse.CMoveRSPMessage),
    (0xAA01, 'Failure', 'Failed: Unable to create new object for this SOP class', dimse.CMoveRSPMessage),
    (0xAA02, 'Failure', 'Failed: Unable to extract frames', dimse.CMoveRSPMessage),
    (0xAA03, 'Failure', 'Failed: Time-based request received for a non-time-based original SOP Instance.',
     dimse.CMoveRSPMessage),
    (0xAA04, 'Failure', 'Failed: Invalid Request', dimse.CMoveRSPMessage),
    (0xB000, 'Warning', 'Sub-operations Complete - One or more Failures or Warnings', dimse.CMoveRSPMessage),
    (0xFF00, 'Pending', 'Sub-operations are continuing', dimse.CMoveRSPMessage)
]


def register_statuses():
    for status in KNOWN_STATUSES:
        code, code_type, desc, command = status
        if isinstance(code, tuple):
            code, end = code
        else:
            end = None
        add_status(code, code_type, desc, end, command)


register_statuses()

SUCCESS = Status(0x0000)
PROCESSING_FAILURE = Status(0x0110)

C_STORE_CANNON_UNDERSTAND = Status(0xC000, dimse.CStoreRSPMessage)
C_STORE_OUT_OF_RESOURCES = Status(0xA700, dimse.CStoreRSPMessage)
C_STORE_ELEMENTS_DISCARDED = Status(0xB006, dimse.CStoreRSPMessage)

C_FIND_PENDING = Status(0xFF00, dimse.CFindRSPMessage)
C_FIND_PENDING_WARNING = Status(0xFF01, dimse.CFindRSPMessage)
C_FIND_UNABLE_TO_PROCESS = Status(0xC000, dimse.CFindRSPMessage)
C_FIND_OUT_OF_RESOURCES = Status(0xA700, dimse.CFindRSPMessage)

C_GET_PENDING = Status(0xFF00, dimse.CGetRSPMessage)
C_GET_WARNING = Status(0xB000, dimse.CGetRSPMessage)
C_GET_UNABLE_TO_PROCESS = Status(0xC000, dimse.CGetRSPMessage)

C_MOVE_PENDING = Status(0xFF00, dimse.CMoveRSPMessage)
C_MOVE_WARNING = Status(0xB000, dimse.CMoveRSPMessage)
C_MOVE_UNABLE_TO_PROCESS = Status(0xC000, dimse.CMoveRSPMessage)
C_MOVE_DESTINATION_UNKNOWN = Status(0xA801, dimse.CMoveRSPMessage)
