PurpleDrop Driver Software Documentation
=============================================

The `purpledrop-driver <https://github.com/uwmisl/purpledrop-driver>`_ project 
contains software which acts as a control gateway for the PurpleDrop USB
device. 

The main utilities provided by this library are the :ref:`pdserver` and 
:ref:`pdcam` executables. These two daemons provide the purpledrop control
gateway and raspberry pi camera support, respectively.

Startup Example
---------------

To run the gateway, simply run the following commands:

.. code-block:: 

    pdserver --board "misl_v4.1"
    pdcam server

You can replace "misl_v4.1" with the name of the electrode board you are using.
The name references one of the available electrode board definitions,
as described in :ref:`Board Definitions`. You can also forego the `pdcam` command
altogether if you do not require video.

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   commands
   board_definitions
   api
   reference/index