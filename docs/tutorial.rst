Tutorial
========

This tutorial shows how to use the most common DICOM services with
pynetdicom2. Every service can be used on two levels:

* a set of **high-level functions** (:func:`~pynetdicom2.commands.verify`,
  :func:`~pynetdicom2.commands.store`, :func:`~pynetdicom2.commands.find`,
  :func:`~pynetdicom2.commands.move`, :func:`~pynetdicom2.commands.storage`)
  exported directly from the package - one function call does everything;
* the **application entity** classes
  (:class:`~pynetdicom2.applicationentity.ClientAE` and
  :class:`~pynetdicom2.applicationentity.AE`) combined with service classes
  from the :mod:`pynetdicom2.sopclass` module - more verbose, but fully
  configurable.

Both approaches are described below. All examples use
:class:`~pynetdicom2.asceprovider.RemoteAEConfig` to describe the remote
application entity they talk to:

.. code-block:: python

   from pynetdicom2.asceprovider import RemoteAEConfig

   remote_ae = RemoteAEConfig(
       aet='ANY-SCP',       # remote AE title
       address='127.0.0.1', # remote IP address or host name
       port=104             # remote port
   )

Verification (C-ECHO)
---------------------

The Verification service lets you check whether a remote AE is reachable and
configured to talk to you. It is the DICOM equivalent of "ping".

High-level
^^^^^^^^^^

.. code-block:: python

   from pynetdicom2 import verify
   from pynetdicom2.asceprovider import RemoteAEConfig

   remote_ae = RemoteAEConfig(
       aet='ANY-SCP', address='dicom.example.com', port=104
   )
   status = verify('MY_AET', remote_ae)
   assert status.is_success

If the association is rejected or cannot be established an exception is
raised (see :ref:`tutorial-error-handling`).

Low-level
^^^^^^^^^

The same request using the application entity classes looks like this:

.. code-block:: python

   from pynetdicom2 import ClientAE, verification_scu, uids
   from pynetdicom2.asceprovider import RemoteAEConfig

   ae = ClientAE('MY_AET').add_scu(verification_scu)

   remote_ae = RemoteAEConfig(
       aet='ANY-SCP', address='dicom.example.com', port=104
   )
   with ae.request_association(remote_ae) as assoc:
       service = assoc.get_scu(uids.VERIFICATION_SOP_CLASS)
       status = service(1)
       assert status.is_success

The steps are always the same:

#. Create a :class:`~pynetdicom2.applicationentity.ClientAE` (or
   :class:`~pynetdicom2.applicationentity.AE`) and register the service
   implementations you want to use with
   :meth:`~pynetdicom2.applicationentity.AEBase.add_scu`. The call returns
   the AE itself, so calls can be chained.
#. Request an association with
   :meth:`~pynetdicom2.applicationentity.AEBase.request_association`. It is
   a context manager: when the block is left the association is released (or
   aborted if something went wrong).
#. Pick the service to invoke with
   :meth:`~pynetdicom2.asceprovider.AssociationRequester.get_scu` and call
   it. The returned callable already has the association and presentation
   context bound to it, so only the service-specific arguments are left.

Providing a Verification SCP
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Accepting verification requests (and any other service in the SCP role)
requires the full :class:`~pynetdicom2.applicationentity.AE`, which listens
for incoming connections on a port:

.. code-block:: python

   import threading

   from pynetdicom2 import AE, verification_scp

   ae = AE('ECHOSCP', 104).add_scp(verification_scp)
   with ae:
       # AE is running, accepting connections until interrupted
       threading.Event().wait()

The default C-ECHO handling always returns
:attr:`~pynetdicom2.statuses.SUCCESS`. To customise it, sub-class
:class:`~pynetdicom2.applicationentity.AE` and override
:meth:`~pynetdicom2.applicationentity.AEBase.on_receive_echo`.

Storage (C-STORE)
-----------------

Sending a dataset
^^^^^^^^^^^^^^^^^

The simplest way to store a DICOM file on a remote Storage SCP:

.. code-block:: python

   from pynetdicom2 import store
   from pynetdicom2.asceprovider import RemoteAEConfig

   remote_ae = RemoteAEConfig(
       aet='STORESCP', address='dicom.example.com', port=104
   )
   status = store('MY_AET', remote_ae, 'path/to/image.dcm')
   assert status.is_success

Note that the file's transfer syntax is proposed to the remote AE, so the
dataset is sent exactly as it is stored on disk.

Using ``storage_scu`` directly gives you more control, and also allows
sending in-memory datasets:

.. code-block:: python

   from pydicom import uid
   from pydicom.dataset import Dataset

   from pynetdicom2 import ClientAE, storage_scu, uids
   from pynetdicom2.asceprovider import RemoteAEConfig

   ds = Dataset()
   ds.PatientName = 'Test^Patient'
   ds.PatientID = '12345'
   ds.SOPClassUID = uids.BASIC_TEXT_SR_STORAGE
   ds.SOPInstanceUID = uid.generate_uid()

   ae = ClientAE('STORESCU')
   # storage_scu ships without SOP Class UIDs - provide the ones you need
   ae.add_scu(storage_scu, [uids.BASIC_TEXT_SR_STORAGE])

   remote_ae = RemoteAEConfig(
       aet='STORESCP', address='127.0.0.1', port=11112
   )
   with ae.request_association(remote_ae) as assoc:
       service = assoc.get_scu(ds.SOPClassUID)
       status = service(ds, 1)  # (dataset or file name, message ID)
       assert status.is_success

When sending a file name instead of a dataset, make sure the AE's supported
transfer syntaxes contain the file's transfer syntax (the file contents are
sent as-is). Transfer syntaxes are passed to the
:class:`~pynetdicom2.applicationentity.ClientAE` constructor via
``supported_ts``.

Receiving datasets
^^^^^^^^^^^^^^^^^^

To receive datasets you run an SCP. The most common setup is an AE that
writes everything it receives into a folder - this is provided by
:class:`~pynetdicom2.applicationentity.StorageAE`:

.. code-block:: python

   import pathlib
   import threading

   from pynetdicom2 import StorageAE, storage_scp, uids

   ae = StorageAE(
       pathlib.Path('incoming'),  # where received datasets are stored
       'STORESCP',                # AE title
       11112,                     # listening port
       uids.ALL_TS                # accept every transfer syntax
   ).add_scp(storage_scp)

   with ae:
       threading.Event().wait()

If you just need this functionality temporarily, the equivalent one-liner
is the :func:`~pynetdicom2.commands.storage` context manager:

.. code-block:: python

   import pathlib
   from pynetdicom2 import storage

   with storage(pathlib.Path('incoming'), 'STORESCP', 11112):
       # AE is listening on port 11112 inside this block
       ...

To process datasets instead of writing them to disk, sub-class
:class:`~pynetdicom2.applicationentity.AE` and override
:meth:`~pynetdicom2.applicationentity.AEBase.on_receive_store`:

.. code-block:: python

   import pathlib
   from typing import BinaryIO, Union

   import pydicom

   from pynetdicom2 import AE, StorageAE, statuses, storage_scp
   from pynetdicom2.fsm import PContextDef


   class MyStorageAE(StorageAE):
       def on_receive_store(
               self,
               context: PContextDef,
               ds: Union[BinaryIO, bytes]
       ) -> statuses.Status:
           # when storage_scp is used, `ds` is a file-like object
           dataset = pydicom.dcmread(ds)
           print('Received SOP Instance', dataset.SOPInstanceUID)
           return statuses.SUCCESS


   ae = MyStorageAE(
       pathlib.Path('incoming'), 'STORESCP', 11112
   ).add_scp(storage_scp)

Return one of the statuses from the :mod:`pynetdicom2.statuses` module (or
raise :class:`~pynetdicom2.exceptions.EventHandlingError` to have the
service respond with a failure status on your behalf).

Query (C-FIND)
--------------

Requesting a query
^^^^^^^^^^^^^^^^^^

High-level
^^^^^^^^^^

.. code-block:: python

   from pydicom.dataset import Dataset

   from pynetdicom2 import find
   from pynetdicom2.asceprovider import RemoteAEConfig

   remote_ae = RemoteAEConfig(
       aet='QRSCP', address='dicom.example.com', port=104
   )
   request = Dataset()
   request.QueryRetrieveLevel = 'STUDY'
   request.PatientName = 'Test^Patient'

   # STUDY_ROOT_FIND_SOP_CLASS is used by default; pass `root` to change it
   for response in find('MY_AET', remote_ae, request):
       print(response.StudyInstanceUID)

Low-level
^^^^^^^^^

.. code-block:: python

   from pydicom.dataset import Dataset

   from pynetdicom2 import ClientAE, qr_find_scu, uids
   from pynetdicom2.asceprovider import RemoteAEConfig

   ae = ClientAE('FINDSCU').add_scu(qr_find_scu)

   request = Dataset()
   request.QueryRetrieveLevel = 'PATIENT'
   request.PatientName = 'Test*'

   remote_ae = RemoteAEConfig(aet='QRSCP', address='127.0.0.1', port=11112)
   with ae.request_association(remote_ae) as assoc:
       service = assoc.get_scu(uids.PATIENT_ROOT_FIND_SOP_CLASS)
       for ds, status in service(request, 1):
           if status.is_pending and ds is not None:
               # pending responses carry the matching datasets
               print(ds.PatientName)

Providing a Find SCP
^^^^^^^^^^^^^^^^^^^^

Sub-class :class:`~pynetdicom2.applicationentity.AE` and override
:meth:`~pynetdicom2.applicationentity.AEBase.on_receive_find`. The method
receives the decoded query dataset and returns (or yields) tuples of
(response dataset, status):

.. code-block:: python

   import threading
   from typing import Iterator

   from pydicom.dataset import Dataset

   from pynetdicom2 import AE, qr_find_scp, statuses
   from pynetdicom2.fsm import PContextDef


   class FindSCP(AE):
       def on_receive_find(
               self,
               context: PContextDef,
               ds: Dataset
       ) -> Iterator[tuple[Dataset, statuses.Status]]:
           for match in self._search(ds.PatientName):
               response = Dataset()
               response.PatientName = match
               yield response, statuses.C_FIND_PENDING

       def _search(self, name):
           # replace with a real search against your database
           return ['Test^Patient']


   ae = FindSCP('QRSCP', 11112).add_scp(qr_find_scp)
   with ae:
       threading.Event().wait()

Yield matches with a pending status
(:attr:`~pynetdicom2.statuses.C_FIND_PENDING`); when your iterator is
exhausted the library sends the final status automatically (Success if you
did not yield a final status yourself).

For Modality Worklist use ``modality_work_list_scu`` /
``modality_work_list_scp`` - they work exactly like the Query/Retrieve
C-FIND service but use the Modality Worklist SOP Class.

Retrieve (C-MOVE)
-----------------

Requesting a move
^^^^^^^^^^^^^^^^^

C-MOVE instructs a remote Q/R SCP to push the requested objects to a third
AE (or back to yourself) using C-STORE.

High-level
^^^^^^^^^^

.. code-block:: python

   from pydicom.dataset import Dataset

   from pynetdicom2 import move
   from pynetdicom2.asceprovider import RemoteAEConfig

   remote_ae = RemoteAEConfig(
       aet='QRSCP', address='dicom.example.com', port=104
   )
   request = Dataset()
   request.QueryRetrieveLevel = 'STUDY'
   request.StudyInstanceUID = '1.2.3.4.5'

   # ask QRSCP to move the study to AE 'STORESCP'
   result = move('MY_AET', remote_ae, request, dest_ae='STORESCP')
   print(result.num_of_completed_sub_ops, result.num_of_failed_sub_ops)

To receive the moved objects yourself, run a Storage SCP (see above) and
use its AE title as the move destination - the remote SCP must be configured
to know that title's address and port.

Providing a Move SCP
^^^^^^^^^^^^^^^^^^^^

A Move SCP needs two things: the ``qr_move_scp`` service to accept C-MOVE
requests, and a Storage SCU to actually send the datasets to the move
destination. Sub-class :class:`~pynetdicom2.applicationentity.AE` and
override :meth:`~pynetdicom2.applicationentity.AEBase.on_receive_move`:

.. code-block:: python

   from pynetdicom2 import AE, qr_move_scp, storage_scu, uids
   from pynetdicom2.asceprovider import RemoteAEConfig
   from pynetdicom2.fsm import PContextDef


   class MoveSCP(AE):
       def __init__(self, ae_title, port):
           super().__init__(ae_title, port)
           self.add_scp(qr_move_scp)
           self.add_scu(storage_scu, [uids.CT_IMAGE_STORAGE])

       def on_receive_move(self, context, ds, destination):
           # map the move destination to connection parameters
           destinations = {
               'STORESCP': RemoteAEConfig(
                   aet='STORESCP', address='127.0.0.1', port=11112
               )
           }
           try:
               remote_ae = destinations[destination]
           except KeyError:
               # unknown destination: report zero sub-operations
               return None, 0, iter([])

           # find the datasets matching the query...
           datasets = self._find(ds)
           # ...and return destination, number of sub-operations and an
           # iterator that yields the datasets one by one
           return remote_ae, len(datasets), iter(datasets)

The library opens a new association with the move destination and sends one
C-STORE per dataset yielded by your iterator, reporting progress with
intermediate C-MOVE responses along the way.

Retrieve (C-GET)
----------------

C-GET is similar to C-MOVE except the datasets are returned over the *same*
association that was used for the request. Only the SCU role is provided by
this package.

When using C-GET remember that:

* your AE must propose presentation contexts for the SOP Classes of the
  objects you expect to receive, because they arrive as C-STORE requests
  over the current association;
* it is strongly recommended to register those contexts with
  ``store_in_file`` set to ``True`` (via
  :meth:`~pynetdicom2.applicationentity.AEBase.update_context_def_list`) so
  incoming datasets are streamed to a file instead of being kept in memory.

:class:`~pynetdicom2.applicationentity.ClientStorageAE` is a convenient base
that stores received datasets in a folder:

.. code-block:: python

   import pathlib

   from pydicom.dataset import Dataset

   from pynetdicom2 import ClientStorageAE, qr_get_scu, uids
   from pynetdicom2.asceprovider import RemoteAEConfig

   ae = ClientStorageAE(pathlib.Path('incoming'), 'GETSCU')
   ae.add_scu(qr_get_scu)
   ae.update_context_def_list(
       [uids.MR_IMAGE_STORAGE], store_in_file=True
   )

   request = Dataset()
   request.QueryRetrieveLevel = 'STUDY'
   request.StudyInstanceUID = '1.2.3.4.5'

   remote_ae = RemoteAEConfig(aet='QRSCP', address='127.0.0.1', port=11112)
   with ae.request_association(remote_ae) as assoc:
       service = assoc.get_scu(uids.PATIENT_ROOT_GET_SOP_CLASS)
       for context, ds in service(request, 1):
           # `ds` is a file object with the received dataset; it is closed
           # automatically once you request the next item
           print('Received', context.sop_class)

Storage Commitment
------------------

With Storage Commitment a Storage SCU asks an SCP to confirm that previously
stored objects are permanently kept. The SCP replies with an N-EVENT-REPORT
on a new association.

The SCP role is the ``StorageCommitment`` class. Sub-class
:class:`~pynetdicom2.applicationentity.AE` and implement both callbacks -
``on_commitment_request`` decides which instances were kept and where to
send the report, ``on_commitment_response`` handles incoming reports:

.. code-block:: python

   from pynetdicom2 import AE, StorageCommitment, storage_commitment_scu
   from pynetdicom2.asceprovider import RemoteAEConfig


   class CommitmentSCP(AE):
       def on_commitment_request(self, remote_ae, uids):
           # `uids` is an iterable of (SOP Class UID, SOP Instance UID)
           success = []
           failure = []
           for sop_class, sop_instance in uids:
               if self._was_stored(sop_class, sop_instance):
                   success.append((sop_class, sop_instance))
               else:
                   failure.append(
                       (
                           sop_class, sop_instance,
                           StorageCommitment.NO_SUCH_OBJECT_INSTANCE
                       )
                   )
           report_to = RemoteAEConfig(
               aet=remote_ae, address='127.0.0.1', port=11113
           )
           return report_to, success, failure

       def on_commitment_response(self, transaction_uid, success, failure):
           print('Committed:', list(success), 'Failed:', list(failure))

       def _was_stored(self, sop_class, sop_instance):
           return True


   ae = CommitmentSCP('STG_CMT', 11112)
   ae.add_scp(StorageCommitment())
   ae.add_scu(storage_commitment_scu)

Requesting commitment as an SCU uses ``storage_commitment_scu``:

.. code-block:: python

   from pydicom import uid as pydicom_uid

   transaction_uid = pydicom_uid.generate_uid()
   instances = [
       (uids.MR_IMAGE_STORAGE, pydicom_uid.generate_uid()),
   ]

   with ae.request_association(remote_ae) as assoc:
       service = assoc.get_scu(uids.STORAGE_COMMITMENT_SOP_CLASS)
       status = service(transaction_uid, instances, 1)

(where ``ae`` is a running ``CommitmentSCP`` from the example above, i.e.
used inside its ``with`` block). Since the commitment report arrives on a
separate association, the requesting AE must also be running as an SCP with
``StorageCommitment`` registered - exactly like in the example above.

.. _tutorial-tls:

TLS Support
-----------

TLS-protected associations are available through the
:mod:`pynetdicom2.ssl_ae` module. Everything works exactly like with the
regular classes, except the AE constructors take a standard library
:class:`ssl.SSLContext`:

.. code-block:: python

   import ssl

   from pynetdicom2 import uids, verification_scu, verification_scp
   from pynetdicom2.asceprovider import RemoteAEConfig
   from pynetdicom2.ssl_ae import SSLApplicationEntity, SSLClientAE

   # Server
   server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
   server_context.load_cert_chain('cert.pem', 'key.pem')
   server_ae = SSLApplicationEntity(
       server_context, 'AET2', 104
   ).add_scp(verification_scp)

   # Client
   client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
   client_context.load_verify_locations('cert.pem')
   client_ae = SSLClientAE(client_context, 'AET1')
   client_ae.add_scu(verification_scu)

   remote_ae = RemoteAEConfig(aet='AET2', address='127.0.0.1', port=104)
   with server_ae:
       with client_ae.request_association(remote_ae) as assoc:
           service = assoc.get_scu(uids.VERIFICATION_SOP_CLASS)
           print(service(1).is_success)

Command Line Interface
----------------------

pynetdicom2 ships with a small CLI that covers verification, storage, query
and move:

.. code-block:: bash

   $ python -m pynetdicom2 verify \
         --aet ANY-SCP --address dicom.example.com --port 104

   $ python -m pynetdicom2 store \
         --aet STORESCP --address dicom.example.com --port 104 \
         --file_or_dir path/to/images

   $ python -m pynetdicom2 find \
         --aet QRSCP --address dicom.example.com --port 104 \
         --root study --level study --attr PatientName=Test*

   $ python -m pynetdicom2 move \
         --aet QRSCP --address dicom.example.com --port 104 \
         --dest_aet STORESCP --attr StudyInstanceUID=1.2.3.4.5 \
         --local_port 11113 --storage_dir incoming

Run ``python -m pynetdicom2 <command> --help`` for the full list of options
of each command.

.. _tutorial-error-handling:

Error Handling
--------------

Service results are represented by the
:class:`~pynetdicom2.statuses.Status` class, which exposes convenient flags:
``is_success``, ``is_pending``, ``is_failure`` and ``is_warning``.

Association-level problems are reported through the exceptions in the
:mod:`pynetdicom2.exceptions` module; all of them derive from
:class:`~pynetdicom2.exceptions.NetDICOMError`. The most common ones are:

* :class:`~pynetdicom2.exceptions.AssociationRejectedError` - the remote AE
  refused the association (e.g. unknown AE title). The ``result``, ``source``
  and ``diagnostic`` attributes explain why.
* :class:`~pynetdicom2.exceptions.AssociationAbortedError` - the remote AE
  aborted an established association.
* :class:`~pynetdicom2.exceptions.AssociationReleasedError` - the remote AE
  released the association unexpectedly.
* :class:`~pynetdicom2.exceptions.ClassNotSupportedError` - the requested
  SOP Class was not accepted during negotiation.

When overriding the ``on_receive_*`` handlers of an AE, raise
:class:`~pynetdicom2.exceptions.EventHandlingError` to signal a processing
failure: the corresponding service class knows about this exception and will
respond with an appropriate failure status instead of tearing down the
association.
