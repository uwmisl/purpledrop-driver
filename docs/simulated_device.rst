Simulated Device
=================

The  :ref:`pdserver` application provides a simulator mode when the `--sim`
argument is provided, which can be used for testing scripts under development.
The simulator uses a simple drop model, in which each electrode is either 
covered or not. A drop located on an inactive electrode, with one or more
active electrodes next to it will be moved to one of the active neighbors, 
and any fluid on a connected drop is pulled along, recursively. 

When launching the simulator, a list of pins must be provided. These pins
will be initialized with a drop present. For example:

`pdserver --board misl_v4.1 --sim 4,5,12` to initialize drops on electrodes
4, 5, and 12.

The simulator is implemented by :py:class:`purpledrop.simulated_purpledrop.SimulatedPurpleDrop`. 

