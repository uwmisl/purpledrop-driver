# PurpleDrop

This holds the control software for PurpleDrop, a digital microfluidic device.
The hardware can be found [here](https://github.com/uwmisl/purpledrop).

# Dependencies

- dfu-util

# Protobuf messages

purpledrop/protobuf/messages_pb2.py is auto-generated from `protobuf/messages.proto`. To update, run:
`protoc --python_out=purpledrop protobuf/messages.proto`
