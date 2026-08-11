Introduction
============

About
-----

**pynetdicom2** is a pure Python package implementing the DICOM network
protocol. DICOM (Digital Imaging and Communications in Medicine,
http://medical.nema.org) is a standard for exchanging medical images and
related information such as structured reports and radiotherapy objects.

pynetdicom2 is a fork/rewrite of the original pynetdicom (formerly hosted on
the now-defunct Google Code and succeeded by
https://github.com/pydicom/pynetdicom). The two packages are **not**
backwards compatible with each other.

The package is built on top of `pydicom <https://pydicom.github.io/>`_, which
is used for reading and writing DICOM datasets, and provides implementations
of the commonly used DICOM services such as Storage, Query/Retrieve and
Verification.

Features
--------

The following services can be used both as a Service Class User (SCU, i.e.
the party that initiates the request) and, where noted, as a Service Class
Provider (SCP, i.e. the party that fulfils the request):

* Verification (C-ECHO) - SCU and SCP
* Storage (C-STORE) - SCU and SCP
* Query/Retrieve C-FIND - SCU and SCP
* Query/Retrieve C-MOVE - SCU and SCP
* Query/Retrieve C-GET - SCU
* Modality Worklist (C-FIND) - SCU and SCP
* Storage Commitment (N-ACTION / N-EVENT-REPORT) - SCU and SCP

Both plain TCP and TLS protected associations are supported, as well as the
DICOM User Identity Negotiation (username/password, Kerberos, SAML and JWT).

Installation
------------

pynetdicom2 requires Python 3.9 or newer and pydicom (>= 2.4). Install it
with pip:

.. code-block:: bash

   $ python -m pip install pynetdicom2

TLS support relies on the :mod:`ssl` module of the Python standard library;
if your Python distribution was built without it, the
:mod:`pynetdicom2.ssl_ae` module will not be usable.

Basic Concepts
--------------

Some of the terms used throughout this documentation, and by the DICOM
standard itself:

Application Entity (AE)
   An instance of a DICOM application. Communication happens between two
   application entities over a network. Each AE is identified by an
   *AE Title* (a string of up to 16 characters).

Service Class User (SCU) and Service Class Provider (SCP)
   Services such as Storage or Query/Retrieve are always used between two
   application entities: one takes on the *user* role (sends the request)
   and the other takes on the *provider* role (answers the request). A single
   AE may act as SCU for some services and as SCP for others at the same
   time.

Association
   Before any service can be used, the two AEs must negotiate and establish
   an *association* over TCP. During the negotiation each side declares which
   services (identified by SOP Class UIDs) and transfer syntaxes it supports.
   Once established, DIMSE messages are exchanged over the association until
   it is released or aborted.

Presentation Context
   An association may contain multiple presentation contexts. Each context
   associates one SOP Class UID with a set of proposed transfer syntaxes.
   The acceptor picks one transfer syntax for every context it accepts.

Transfer Syntax
   Defines how DICOM datasets are encoded for transmission, e.g. Implicit VR
   Little Endian, Explicit VR Little Endian or one of the JPEG variants.

DIMSE
   The messaging layer of DICOM (C-ECHO, C-STORE, C-FIND, C-MOVE, C-GET,
   N-ACTION, N-EVENT-REPORT and their responses). DIMSE messages are split
   into fragments that fit into PDUs for transmission.

Architecture Overview
---------------------

The package is organised in layers. Unless you need fine-grained control you
will normally only touch the top-most ones:

* ``applicationentity`` - Application Entity classes (:class:`~pynetdicom2.applicationentity.AE`
  and :class:`~pynetdicom2.applicationentity.ClientAE`), your main entry point
  into the library.
* ``commands`` / top-level package functions (``verify``, ``find``, ``store``,
  ``storage``, ``move``) - high-level one-call wrappers around the most
  common operations.
* ``sopclass`` - ready-made SCU/SCP implementations of the supported service
  classes.
* ``asceprovider`` - the ACSE layer: association establishment, negotiation
  of presentation contexts and DIMSE transport.
* ``dulprovider`` - the DUL layer: socket handling and PDU fragmentation.
* ``dimsemessages`` - encoding/decoding of DIMSE messages.
* ``pdu`` and ``userdataitems`` - encoding/decoding of protocol data units.
* ``fsm`` - the association state machine and presentation context
  definitions.
* ``statuses`` - response status codes and the
  :class:`~pynetdicom2.statuses.Status` type.
* ``uids`` - SOP Class UIDs and transfer syntaxes supported by the package.
* ``ssl_ae`` - TLS variants of the application entity classes.
* ``exceptions`` - the exception hierarchy raised by the package.

Getting Started
---------------

For simple use cases the high-level functions exported from the package are
usually enough. For example, sending a verification request takes a few
lines:

.. code-block:: python

   from pynetdicom2 import verify
   from pynetdicom2.asceprovider import RemoteAEConfig

   remote_ae = RemoteAEConfig(
       aet='ANY-SCP', address='dicom.example.com', port=104
   )
   status = verify('MY_AET', remote_ae)
   print(status.is_success)

When you need more control - for example to provide your own SCP services -
work with the application entity classes instead. See the :doc:`tutorial`
for a step-by-step guide covering both approaches.

Licence
-------

pynetdicom2 is released under a modified MIT licence. See the ``LICENCE.txt``
file that ships with the package for details.
