# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com

"""
Module contains all exception class that are used in this package.

NetDICOMError serves as base exception class.

The class hierarchy for exceptions is:

| Exception
| +-- NetDICOMError
|      +-- ClassNotSupportedError
|      +-- PDUProcessingError
|      +-- DIMSEProcessingError
|      +-- AssociationError
|           +-- AssociationRejectedError
|           +-- AssociationReleasedError
|           +-- AssociationAbortedError
|      +-- EventHandlingError

"""

from __future__ import absolute_import, unicode_literals


class NetDICOMError(Exception):
    """Base class for all library specific exceptions exception."""

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization."""
        super(NetDICOMError, self).__init__(*args, **kwargs)


class ClassNotSupportedError(NetDICOMError):
    """Raised when requested SOP Class is not supported by
    application entity."""

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization."""
        super(ClassNotSupportedError, self).__init__(*args, **kwargs)


class PDUProcessingError(NetDICOMError):
    """Raised when error occurs while processing PDU.

    Can be raised, for example, when PDU failed to decode from data.
    """

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization."""
        super(PDUProcessingError, self).__init__(*args, **kwargs)


class DIMSEProcessingError(NetDICOMError):
    """Raised when error occurs while processing DIMSE.

    Can be raised, for example, while DIMSEProvider tries to decode DIMSE from
    fragments.
    """

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization."""
        super(DIMSEProcessingError, self).__init__(*args, **kwargs)


class AssociationError(NetDICOMError):
    """Base association error.

    This error shall not be raised directly, instead its more specialized
    sub-classes are raised in appropriate situations.
    """

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization."""
        super(AssociationError, self).__init__(*args, **kwargs)


class AssociationRejectedError(AssociationError):
    """Raised when remote application entity has rejected
    requested association.

    Exception has 3 instance attributes to indicate why association was
    rejected:

        * Result,
        * Source,
        * Reason/Diag

    as described in PS 3.8 (9.3.4 A-ASSOCIATE-RJ PDU STRUCTURE).

    For convenience the following documentation has quotes from DICOM
    standard (2011) explaining possible values of the exception attributes
    and their meaning.

    :param result: 1 - rejected-permanent or  2 - rejected-transient
    :param source: This Source field shall contain an integer value
                   encoded as an unsigned binary number.
                   One of the following values shall be used:

                        * 1 - DICOM UL service-user
                        * 2 - DICOM UL service-provider
                          (ACSE related function)
                        * 3 - DICOM UL service-provider
                          (Presentation related function)

    :param diagnostic: This field shall contain an integer value encoded
                       as an unsigned binary number. If the Source field has the
                       value
                       (1) DICOM UL service-user, it shall take one of the
                       following:

                            * 1 - no-reason-given
                            * 2 - application-context-name-not-supported
                            * 3 - calling-AE-title-not-recognized
                            * 4-6 - reserved
                            * 7 - called-AE-title-not-recognized
                            * 8-10 - reserved

                       If the Source field has the value (2) DICOM UL service
                       provided (ACSE related function), it shall take one of
                       the following:

                            * 1 - no-reason-given
                            * 2 - protocol-version-not-supported

                       If the Source field has the value (3) DICOM UL service
                       provided (Presentation related function), it shall take
                       one of the following:

                            * 0 - reserved
                            * 1 - temporary-congestion
                            * 2 - local-limit-exceeded
                            * 3-7 - reserved

    """

    def __init__(self, result, source, diagnostic, *args, **kwargs):
        """Overrides base exception initialization."""

        super(AssociationRejectedError, self).__init__(*args, **kwargs)
        self.result = result
        self.source = source
        self.diagnostic = diagnostic


class AssociationReleasedError(AssociationError):
    """Raised when remote application entity has released active association."""

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization."""
        super(AssociationReleasedError, self).__init__(*args, **kwargs)


class AssociationAbortedError(AssociationError):
    """Raised when remote application entity has aborted association.

    :param source:
    :param reason_diag:
    """

    def __init__(self, source, reason_diag, *args, **kwargs):
        """Overrides base exception initialization."""
        super(AssociationAbortedError, self).__init__(*args, **kwargs)
        self.source = source
        self.reason_diag = reason_diag


class TimeoutError(NetDICOMError):
    """Raised if timeout occurred when expected PDU from DUL."""
    pass


class EventHandlingError(NetDICOMError):
    """This exception is not raised by the package itself.

    This exception should be raised by the user when sub-classing AE class and
    implementing custom event handlers. This exception would indicate that
    the AE failed to process received event. Service classes expect this
    exception and would act accordingly. If event handler would raise any
    other exception (not a sub-class of this one), service class won't handle
    it."""

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization."""
        super(EventHandlingError, self).__init__(*args, **kwargs)
