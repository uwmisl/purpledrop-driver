# PurpleDrop Software

This holds the control software for PurpleDrop, a digital microfluidic device.
The hardware can be found [here](https://github.com/uwmisl/purpledrop).

## Overview

This software provides a driver and HTTP gateway for controlling a PurpleDrop DMF device. It supports the PurpleDrop rev6 and later -- i.e. a USB-based hardware design. 

The `pdserver` executable provides a service which detects and connects to a PurpleDrop USB device, and provides access to it through the following endpoints:

1) A JSON-RPC interface is provided at `http://0.0.0.0:7000/rpc`. See `http://0.0.0.0:7000/rpc/map` for a list of RPC functions available.
2) A websocket streaming events (protobuf messages defined in `protobuf/messages.proto`) on `ws://0.0.0.0:7001`.
3) A javascript front-end at `http://0.0.0.0:7000/`.

The `pdcli` executable provides a command line interface for accessing the purpledrop. For example `pdcli info` will attempt to connect to the device and read its software version. See `pdcli --help` for full set of commands. 

The `pdrecord` executable can be used to record the eventstream during experiments for later analysis or playback. Example: `pdrecord --host ws://192.168.0.2:7001 experiment1.pdlog`. 

## Installing 

Clone the repository, and run `pip install .`.

## Rebuilding protobuf messages

purpledrop/protobuf/messages_pb2.py is auto-generated from `protobuf/messages.proto`. If the message definitions are changed, it needs to be updated manually by running:
`protoc --python_out=purpledrop protobuf/messages.proto`

## Javascript front-end

The `jsclient` directory contains a webpack project which provides a user interface for controlling a purpledrop. After running `pdserver`, point your browser at `localhost:7000` to load. 

### Deployment

The javascript is bundled into a tarball and deployed with the python package as package data (`purpledrop/frontend-dist.tar.gz`). The tarball is under source control so that the python project can be installed without working node tools. To rebuild the node project and update the tarball, run `make jsclient`. 

The jsclient project also supports a development server. For more information, see [jsclient/README.md](jsclient/README.md).



