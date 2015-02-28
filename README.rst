pynetdicom2
===========

pynetdicom2 is a pure python package implementing the DICOM network protocol.
This library is a fork/rewrite of the original pynetdicom that can be found here
http://pynetdicom.googlecode.com. Library is not backwards compatible with
original pynetdicom.

Library is build on top of pydicom, which is used for reading/writing DICOM
datasets. Pynetdicom2 provides implementation for commonly used DICOM services
such as Storage, Query/Retrieve, Verification, etc.

DICOM is a standard (http://medical.nema.org) for communicating medical images
and related information such as reports and radiotherapy objects.

Roadmap
=======

* Documentation should really be improved (proper tutorial, some examples)
* Better test suit (some necessary unit tests and integration tests are
  missing)
* Stability and performance improvements. In its current state library performs
  'good enough', but certainly there is still room for improvement.

