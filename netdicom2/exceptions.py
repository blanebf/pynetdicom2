# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
"""
Module contains all exception class that are used in this package.

NetDICOMError serves as base exception class.

The class hierarchy for exceptions is:

Exception
 +-- NetDICOMError
      +-- ClassNotSupportedError
      +-- PDUProcessingError
      +-- DIMSEProcessingError
      +-- AssociationError
           +-- AssociationRejectedError
           +-- AssociationReleasedError
           +-- AssociationAbortedError
      +-- EventHandlingError

"""


class NetDICOMError(Exception):
    """Base class for all library specific exceptions exception."""

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization

        :param args: positional arguments
        :param kwargs: keyword arguments
        """
        super(NetDICOMError, self).__init__(*args, **kwargs)


class ClassNotSupportedError(NetDICOMError):
    """Raised when requested SOP Class is not supported by
    application entity."""

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization

        :param args: positional arguments
        :param kwargs: keyword arguments
        """
        super(ClassNotSupportedError, self).__init__(*args, **kwargs)


class PDUProcessingError(NetDICOMError):
    """Raised when error occurs while processing PDU.

    Can be raised, for example, when PDU failed to decode from data.
    """

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization

        :param args: positional arguments
        :param kwargs: keyword arguments
        """
        super(PDUProcessingError, self).__init__(*args, **kwargs)


class DIMSEProcessingError(NetDICOMError):
    """Raised when error occurs while processing DIMSE.

    Can be raised, for example, while DIMSEProvider tries to decode DIMSE from
    fragments.
    """

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization

        :param args: positional arguments
        :param kwargs: keyword arguments
        """
        super(DIMSEProcessingError, self).__init__(*args, **kwargs)


class AssociationError(NetDICOMError):
    """Base association error.

    This error shall not be raised directly, instead its more specialized
    sub-classes are raised in appropriate situations.
    """

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization

        :param args: positional arguments
        :param kwargs: keyword arguments
        """
        super(AssociationError, self).__init__(*args, **kwargs)


class AssociationRejectedError(AssociationError):
    """Raised when remote application entity has rejected
    requested association."""

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization

        :param args: positional arguments
        :param kwargs: keyword arguments
        """
        super(AssociationRejectedError, self).__init__(*args, **kwargs)


class AssociationReleasedError(AssociationError):
    """Raised when remote application entity has released active
    association."""

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization

        :param args: positional arguments
        :param kwargs: keyword arguments
        """
        super(AssociationReleasedError, self).__init__(*args, **kwargs)


class AssociationAbortedError(AssociationError):
    """Raised when remote application entity has aborted association."""

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization

        :param args: positional arguments
        :param kwargs: keyword arguments
        """
        super(AssociationAbortedError, self).__init__(*args, **kwargs)


class EventHandlingError(NetDICOMError):
    """This exception is not raised by the package itself.

    This exception should be raised by the user when sub-classing AE class and
    implementing custom event handlers. This exception would indicate that
    the AE failed to process received event. Service classes expect this
    exception and would act accordingly. If event handler would raise any
    other exception (not a sub-class of this one), service class won't handle
    it."""

    def __init__(self, *args, **kwargs):
        """Overrides base exception initialization

        :param args: positional arguments
        :param kwargs: keyword arguments
        """
        super(EventHandlingError, self).__init__(*args, **kwargs)
