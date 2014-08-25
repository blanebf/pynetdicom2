===========
pynetdicom2
===========

pynetdicom2 is a pure python package implementing the DICOM network
protocol.
This library is a fork of the original pynetdicom that can be found here
http://pynetdicom.googlecode.com.

Most of the classes/function/modules were renamed to follow PEP8 and upper
layer of the library was refactored so current version is not backwards
compatible with old pynetdicom.The goal of this fork is to make both code
and interface of this library more pythonic. Currently refactoring is not
complete and there is no test suite provided (it was also missing from
original library) so I would advise against using it in production
at the moment.

Working with pydicom, it allows DICOM clients (SCUs) and
servers (SCPs) to be easily created.  DICOM is a standard
(http://medical.nema.org) for communicating medical images and related
information such as reports and radiotherapy objects.
      
The main class is AE and represent an application entity. User
typically create an ApplicationEntity object, specifying the SOP
service class supported as SCP and SCU, and a port to listen to. The
user then starts the ApplicationEntity which runs in a thread. The use
can initiate associations as SCU or respond to remote SCU association
with the means of callbacks.
  
