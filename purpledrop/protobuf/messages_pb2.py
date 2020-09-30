# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: protobuf/messages.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='protobuf/messages.proto',
  package='protobuf',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n\x17protobuf/messages.proto\x12\x08protobuf\"+\n\tTimestamp\x12\x0f\n\x07seconds\x18\x01 \x01(\x03\x12\r\n\x05nanos\x18\x02 \x01(\x05\"I\n\x0f\x45lectrodeLayout\x12&\n\ttimestamp\x18\x01 \x01(\x0b\x32\x13.protobuf.Timestamp\x12\x0e\n\x06layout\x18\x02 \x01(\t\"E\n\x08Settings\x12&\n\ttimestamp\x18\x01 \x01(\x0b\x32\x13.protobuf.Timestamp\x12\x11\n\tfrequency\x18\x02 \x01(\x02\"L\n\x0e\x45lectrodeState\x12&\n\ttimestamp\x18\x01 \x01(\x0b\x32\x13.protobuf.Timestamp\x12\x12\n\nelectrodes\x18\x02 \x03(\x08\"P\n\x16\x43\x61pacitanceMeasurement\x12\x13\n\x0b\x63\x61pacitance\x18\x01 \x01(\x02\x12\x14\n\x0c\x64rop_present\x18\x02 \x01(\x08\x12\x0b\n\x03raw\x18\x03 \x01(\x02\"q\n\x0fScanCapacitance\x12&\n\ttimestamp\x18\x01 \x01(\x0b\x32\x13.protobuf.Timestamp\x12\x36\n\x0cmeasurements\x18\x02 \x03(\x0b\x32 .protobuf.CapacitanceMeasurement\"v\n\x11\x41\x63tiveCapacitance\x12&\n\ttimestamp\x18\x01 \x01(\x0b\x32\x13.protobuf.Timestamp\x12\x10\n\x08\x62\x61seline\x18\x03 \x01(\x02\x12\x13\n\x0bmeasurement\x18\x04 \x01(\x02\x12\x12\n\ncalibrated\x18\x05 \x01(\x02\"C\n\x05Image\x12&\n\ttimestamp\x18\x01 \x01(\x0b\x32\x13.protobuf.Timestamp\x12\x12\n\nimage_data\x18\x02 \x01(\x0c\"\x93\x02\n\x0eImageTransform\x12&\n\ttimestamp\x18\x01 \x01(\x0b\x32\x13.protobuf.Timestamp\x12\x11\n\ttransform\x18\x02 \x03(\x02\x12\x39\n\x08qr_codes\x18\x03 \x03(\x0b\x32\'.protobuf.ImageTransform.QrCodeLocation\x12\x13\n\x0bimage_width\x18\x04 \x01(\x05\x12\x14\n\x0cimage_height\x18\x05 \x01(\x05\x1a\x1d\n\x05Point\x12\t\n\x01x\x18\x01 \x01(\x05\x12\t\n\x01y\x18\x02 \x01(\x05\x1a\x41\n\x0eQrCodeLocation\x12/\n\x07\x63orners\x18\x01 \x03(\x0b\x32\x1e.protobuf.ImageTransform.Point\"\\\n\x0bHvRegulator\x12\x0f\n\x07voltage\x18\x01 \x01(\x02\x12\x14\n\x0cv_target_out\x18\x02 \x01(\x02\x12&\n\ttimestamp\x18\x03 \x01(\x0b\x32\x13.protobuf.Timestamp\"g\n\x12TemperatureControl\x12\x14\n\x0ctemperatures\x18\x01 \x03(\x02\x12\x13\n\x0b\x64uty_cycles\x18\x02 \x03(\x02\x12&\n\ttimestamp\x18\x03 \x01(\x0b\x32\x13.protobuf.Timestamp\"P\n\nDeviceInfo\x12\x11\n\tconnected\x18\x01 \x01(\x08\x12\x15\n\rserial_number\x18\x02 \x01(\t\x12\x18\n\x10software_version\x18\x03 \x01(\t\"\x8e\x04\n\x0fPurpleDropEvent\x12\x35\n\x10\x65lectrode_layout\x18\x01 \x01(\x0b\x32\x19.protobuf.ElectrodeLayoutH\x00\x12\x33\n\x0f\x65lectrode_state\x18\x02 \x01(\x0b\x32\x18.protobuf.ElectrodeStateH\x00\x12 \n\x05image\x18\x03 \x01(\x0b\x32\x0f.protobuf.ImageH\x00\x12\x33\n\x0fimage_transform\x18\x04 \x01(\x0b\x32\x18.protobuf.ImageTransformH\x00\x12&\n\x08settings\x18\x05 \x01(\x0b\x32\x12.protobuf.SettingsH\x00\x12\x35\n\x10scan_capacitance\x18\x06 \x01(\x0b\x32\x19.protobuf.ScanCapacitanceH\x00\x12\x39\n\x12\x61\x63tive_capacitance\x18\x07 \x01(\x0b\x32\x1b.protobuf.ActiveCapacitanceH\x00\x12-\n\x0chv_regulator\x18\x08 \x01(\x0b\x32\x15.protobuf.HvRegulatorH\x00\x12;\n\x13temperature_control\x18\t \x01(\x0b\x32\x1c.protobuf.TemperatureControlH\x00\x12+\n\x0b\x64\x65vice_info\x18\n \x01(\x0b\x32\x14.protobuf.DeviceInfoH\x00\x42\x05\n\x03msgb\x06proto3')
)




_TIMESTAMP = _descriptor.Descriptor(
  name='Timestamp',
  full_name='protobuf.Timestamp',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='seconds', full_name='protobuf.Timestamp.seconds', index=0,
      number=1, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='nanos', full_name='protobuf.Timestamp.nanos', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=37,
  serialized_end=80,
)


_ELECTRODELAYOUT = _descriptor.Descriptor(
  name='ElectrodeLayout',
  full_name='protobuf.ElectrodeLayout',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='protobuf.ElectrodeLayout.timestamp', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='layout', full_name='protobuf.ElectrodeLayout.layout', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=82,
  serialized_end=155,
)


_SETTINGS = _descriptor.Descriptor(
  name='Settings',
  full_name='protobuf.Settings',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='protobuf.Settings.timestamp', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='frequency', full_name='protobuf.Settings.frequency', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=157,
  serialized_end=226,
)


_ELECTRODESTATE = _descriptor.Descriptor(
  name='ElectrodeState',
  full_name='protobuf.ElectrodeState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='protobuf.ElectrodeState.timestamp', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='electrodes', full_name='protobuf.ElectrodeState.electrodes', index=1,
      number=2, type=8, cpp_type=7, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=228,
  serialized_end=304,
)


_CAPACITANCEMEASUREMENT = _descriptor.Descriptor(
  name='CapacitanceMeasurement',
  full_name='protobuf.CapacitanceMeasurement',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='capacitance', full_name='protobuf.CapacitanceMeasurement.capacitance', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='drop_present', full_name='protobuf.CapacitanceMeasurement.drop_present', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='raw', full_name='protobuf.CapacitanceMeasurement.raw', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=306,
  serialized_end=386,
)


_SCANCAPACITANCE = _descriptor.Descriptor(
  name='ScanCapacitance',
  full_name='protobuf.ScanCapacitance',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='protobuf.ScanCapacitance.timestamp', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='measurements', full_name='protobuf.ScanCapacitance.measurements', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=388,
  serialized_end=501,
)


_ACTIVECAPACITANCE = _descriptor.Descriptor(
  name='ActiveCapacitance',
  full_name='protobuf.ActiveCapacitance',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='protobuf.ActiveCapacitance.timestamp', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='baseline', full_name='protobuf.ActiveCapacitance.baseline', index=1,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='measurement', full_name='protobuf.ActiveCapacitance.measurement', index=2,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='calibrated', full_name='protobuf.ActiveCapacitance.calibrated', index=3,
      number=5, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=503,
  serialized_end=621,
)


_IMAGE = _descriptor.Descriptor(
  name='Image',
  full_name='protobuf.Image',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='protobuf.Image.timestamp', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='image_data', full_name='protobuf.Image.image_data', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=623,
  serialized_end=690,
)


_IMAGETRANSFORM_POINT = _descriptor.Descriptor(
  name='Point',
  full_name='protobuf.ImageTransform.Point',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='x', full_name='protobuf.ImageTransform.Point.x', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='y', full_name='protobuf.ImageTransform.Point.y', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=872,
  serialized_end=901,
)

_IMAGETRANSFORM_QRCODELOCATION = _descriptor.Descriptor(
  name='QrCodeLocation',
  full_name='protobuf.ImageTransform.QrCodeLocation',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='corners', full_name='protobuf.ImageTransform.QrCodeLocation.corners', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=903,
  serialized_end=968,
)

_IMAGETRANSFORM = _descriptor.Descriptor(
  name='ImageTransform',
  full_name='protobuf.ImageTransform',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='protobuf.ImageTransform.timestamp', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='transform', full_name='protobuf.ImageTransform.transform', index=1,
      number=2, type=2, cpp_type=6, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='qr_codes', full_name='protobuf.ImageTransform.qr_codes', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='image_width', full_name='protobuf.ImageTransform.image_width', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='image_height', full_name='protobuf.ImageTransform.image_height', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[_IMAGETRANSFORM_POINT, _IMAGETRANSFORM_QRCODELOCATION, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=693,
  serialized_end=968,
)


_HVREGULATOR = _descriptor.Descriptor(
  name='HvRegulator',
  full_name='protobuf.HvRegulator',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='voltage', full_name='protobuf.HvRegulator.voltage', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='v_target_out', full_name='protobuf.HvRegulator.v_target_out', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='protobuf.HvRegulator.timestamp', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=970,
  serialized_end=1062,
)


_TEMPERATURECONTROL = _descriptor.Descriptor(
  name='TemperatureControl',
  full_name='protobuf.TemperatureControl',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='temperatures', full_name='protobuf.TemperatureControl.temperatures', index=0,
      number=1, type=2, cpp_type=6, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='duty_cycles', full_name='protobuf.TemperatureControl.duty_cycles', index=1,
      number=2, type=2, cpp_type=6, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='protobuf.TemperatureControl.timestamp', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1064,
  serialized_end=1167,
)


_DEVICEINFO = _descriptor.Descriptor(
  name='DeviceInfo',
  full_name='protobuf.DeviceInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='connected', full_name='protobuf.DeviceInfo.connected', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='serial_number', full_name='protobuf.DeviceInfo.serial_number', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='software_version', full_name='protobuf.DeviceInfo.software_version', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1169,
  serialized_end=1249,
)


_PURPLEDROPEVENT = _descriptor.Descriptor(
  name='PurpleDropEvent',
  full_name='protobuf.PurpleDropEvent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='electrode_layout', full_name='protobuf.PurpleDropEvent.electrode_layout', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='electrode_state', full_name='protobuf.PurpleDropEvent.electrode_state', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='image', full_name='protobuf.PurpleDropEvent.image', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='image_transform', full_name='protobuf.PurpleDropEvent.image_transform', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='settings', full_name='protobuf.PurpleDropEvent.settings', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='scan_capacitance', full_name='protobuf.PurpleDropEvent.scan_capacitance', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='active_capacitance', full_name='protobuf.PurpleDropEvent.active_capacitance', index=6,
      number=7, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='hv_regulator', full_name='protobuf.PurpleDropEvent.hv_regulator', index=7,
      number=8, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='temperature_control', full_name='protobuf.PurpleDropEvent.temperature_control', index=8,
      number=9, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='device_info', full_name='protobuf.PurpleDropEvent.device_info', index=9,
      number=10, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='msg', full_name='protobuf.PurpleDropEvent.msg',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=1252,
  serialized_end=1778,
)

_ELECTRODELAYOUT.fields_by_name['timestamp'].message_type = _TIMESTAMP
_SETTINGS.fields_by_name['timestamp'].message_type = _TIMESTAMP
_ELECTRODESTATE.fields_by_name['timestamp'].message_type = _TIMESTAMP
_SCANCAPACITANCE.fields_by_name['timestamp'].message_type = _TIMESTAMP
_SCANCAPACITANCE.fields_by_name['measurements'].message_type = _CAPACITANCEMEASUREMENT
_ACTIVECAPACITANCE.fields_by_name['timestamp'].message_type = _TIMESTAMP
_IMAGE.fields_by_name['timestamp'].message_type = _TIMESTAMP
_IMAGETRANSFORM_POINT.containing_type = _IMAGETRANSFORM
_IMAGETRANSFORM_QRCODELOCATION.fields_by_name['corners'].message_type = _IMAGETRANSFORM_POINT
_IMAGETRANSFORM_QRCODELOCATION.containing_type = _IMAGETRANSFORM
_IMAGETRANSFORM.fields_by_name['timestamp'].message_type = _TIMESTAMP
_IMAGETRANSFORM.fields_by_name['qr_codes'].message_type = _IMAGETRANSFORM_QRCODELOCATION
_HVREGULATOR.fields_by_name['timestamp'].message_type = _TIMESTAMP
_TEMPERATURECONTROL.fields_by_name['timestamp'].message_type = _TIMESTAMP
_PURPLEDROPEVENT.fields_by_name['electrode_layout'].message_type = _ELECTRODELAYOUT
_PURPLEDROPEVENT.fields_by_name['electrode_state'].message_type = _ELECTRODESTATE
_PURPLEDROPEVENT.fields_by_name['image'].message_type = _IMAGE
_PURPLEDROPEVENT.fields_by_name['image_transform'].message_type = _IMAGETRANSFORM
_PURPLEDROPEVENT.fields_by_name['settings'].message_type = _SETTINGS
_PURPLEDROPEVENT.fields_by_name['scan_capacitance'].message_type = _SCANCAPACITANCE
_PURPLEDROPEVENT.fields_by_name['active_capacitance'].message_type = _ACTIVECAPACITANCE
_PURPLEDROPEVENT.fields_by_name['hv_regulator'].message_type = _HVREGULATOR
_PURPLEDROPEVENT.fields_by_name['temperature_control'].message_type = _TEMPERATURECONTROL
_PURPLEDROPEVENT.fields_by_name['device_info'].message_type = _DEVICEINFO
_PURPLEDROPEVENT.oneofs_by_name['msg'].fields.append(
  _PURPLEDROPEVENT.fields_by_name['electrode_layout'])
_PURPLEDROPEVENT.fields_by_name['electrode_layout'].containing_oneof = _PURPLEDROPEVENT.oneofs_by_name['msg']
_PURPLEDROPEVENT.oneofs_by_name['msg'].fields.append(
  _PURPLEDROPEVENT.fields_by_name['electrode_state'])
_PURPLEDROPEVENT.fields_by_name['electrode_state'].containing_oneof = _PURPLEDROPEVENT.oneofs_by_name['msg']
_PURPLEDROPEVENT.oneofs_by_name['msg'].fields.append(
  _PURPLEDROPEVENT.fields_by_name['image'])
_PURPLEDROPEVENT.fields_by_name['image'].containing_oneof = _PURPLEDROPEVENT.oneofs_by_name['msg']
_PURPLEDROPEVENT.oneofs_by_name['msg'].fields.append(
  _PURPLEDROPEVENT.fields_by_name['image_transform'])
_PURPLEDROPEVENT.fields_by_name['image_transform'].containing_oneof = _PURPLEDROPEVENT.oneofs_by_name['msg']
_PURPLEDROPEVENT.oneofs_by_name['msg'].fields.append(
  _PURPLEDROPEVENT.fields_by_name['settings'])
_PURPLEDROPEVENT.fields_by_name['settings'].containing_oneof = _PURPLEDROPEVENT.oneofs_by_name['msg']
_PURPLEDROPEVENT.oneofs_by_name['msg'].fields.append(
  _PURPLEDROPEVENT.fields_by_name['scan_capacitance'])
_PURPLEDROPEVENT.fields_by_name['scan_capacitance'].containing_oneof = _PURPLEDROPEVENT.oneofs_by_name['msg']
_PURPLEDROPEVENT.oneofs_by_name['msg'].fields.append(
  _PURPLEDROPEVENT.fields_by_name['active_capacitance'])
_PURPLEDROPEVENT.fields_by_name['active_capacitance'].containing_oneof = _PURPLEDROPEVENT.oneofs_by_name['msg']
_PURPLEDROPEVENT.oneofs_by_name['msg'].fields.append(
  _PURPLEDROPEVENT.fields_by_name['hv_regulator'])
_PURPLEDROPEVENT.fields_by_name['hv_regulator'].containing_oneof = _PURPLEDROPEVENT.oneofs_by_name['msg']
_PURPLEDROPEVENT.oneofs_by_name['msg'].fields.append(
  _PURPLEDROPEVENT.fields_by_name['temperature_control'])
_PURPLEDROPEVENT.fields_by_name['temperature_control'].containing_oneof = _PURPLEDROPEVENT.oneofs_by_name['msg']
_PURPLEDROPEVENT.oneofs_by_name['msg'].fields.append(
  _PURPLEDROPEVENT.fields_by_name['device_info'])
_PURPLEDROPEVENT.fields_by_name['device_info'].containing_oneof = _PURPLEDROPEVENT.oneofs_by_name['msg']
DESCRIPTOR.message_types_by_name['Timestamp'] = _TIMESTAMP
DESCRIPTOR.message_types_by_name['ElectrodeLayout'] = _ELECTRODELAYOUT
DESCRIPTOR.message_types_by_name['Settings'] = _SETTINGS
DESCRIPTOR.message_types_by_name['ElectrodeState'] = _ELECTRODESTATE
DESCRIPTOR.message_types_by_name['CapacitanceMeasurement'] = _CAPACITANCEMEASUREMENT
DESCRIPTOR.message_types_by_name['ScanCapacitance'] = _SCANCAPACITANCE
DESCRIPTOR.message_types_by_name['ActiveCapacitance'] = _ACTIVECAPACITANCE
DESCRIPTOR.message_types_by_name['Image'] = _IMAGE
DESCRIPTOR.message_types_by_name['ImageTransform'] = _IMAGETRANSFORM
DESCRIPTOR.message_types_by_name['HvRegulator'] = _HVREGULATOR
DESCRIPTOR.message_types_by_name['TemperatureControl'] = _TEMPERATURECONTROL
DESCRIPTOR.message_types_by_name['DeviceInfo'] = _DEVICEINFO
DESCRIPTOR.message_types_by_name['PurpleDropEvent'] = _PURPLEDROPEVENT
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Timestamp = _reflection.GeneratedProtocolMessageType('Timestamp', (_message.Message,), dict(
  DESCRIPTOR = _TIMESTAMP,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.Timestamp)
  ))
_sym_db.RegisterMessage(Timestamp)

ElectrodeLayout = _reflection.GeneratedProtocolMessageType('ElectrodeLayout', (_message.Message,), dict(
  DESCRIPTOR = _ELECTRODELAYOUT,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.ElectrodeLayout)
  ))
_sym_db.RegisterMessage(ElectrodeLayout)

Settings = _reflection.GeneratedProtocolMessageType('Settings', (_message.Message,), dict(
  DESCRIPTOR = _SETTINGS,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.Settings)
  ))
_sym_db.RegisterMessage(Settings)

ElectrodeState = _reflection.GeneratedProtocolMessageType('ElectrodeState', (_message.Message,), dict(
  DESCRIPTOR = _ELECTRODESTATE,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.ElectrodeState)
  ))
_sym_db.RegisterMessage(ElectrodeState)

CapacitanceMeasurement = _reflection.GeneratedProtocolMessageType('CapacitanceMeasurement', (_message.Message,), dict(
  DESCRIPTOR = _CAPACITANCEMEASUREMENT,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.CapacitanceMeasurement)
  ))
_sym_db.RegisterMessage(CapacitanceMeasurement)

ScanCapacitance = _reflection.GeneratedProtocolMessageType('ScanCapacitance', (_message.Message,), dict(
  DESCRIPTOR = _SCANCAPACITANCE,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.ScanCapacitance)
  ))
_sym_db.RegisterMessage(ScanCapacitance)

ActiveCapacitance = _reflection.GeneratedProtocolMessageType('ActiveCapacitance', (_message.Message,), dict(
  DESCRIPTOR = _ACTIVECAPACITANCE,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.ActiveCapacitance)
  ))
_sym_db.RegisterMessage(ActiveCapacitance)

Image = _reflection.GeneratedProtocolMessageType('Image', (_message.Message,), dict(
  DESCRIPTOR = _IMAGE,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.Image)
  ))
_sym_db.RegisterMessage(Image)

ImageTransform = _reflection.GeneratedProtocolMessageType('ImageTransform', (_message.Message,), dict(

  Point = _reflection.GeneratedProtocolMessageType('Point', (_message.Message,), dict(
    DESCRIPTOR = _IMAGETRANSFORM_POINT,
    __module__ = 'protobuf.messages_pb2'
    # @@protoc_insertion_point(class_scope:protobuf.ImageTransform.Point)
    ))
  ,

  QrCodeLocation = _reflection.GeneratedProtocolMessageType('QrCodeLocation', (_message.Message,), dict(
    DESCRIPTOR = _IMAGETRANSFORM_QRCODELOCATION,
    __module__ = 'protobuf.messages_pb2'
    # @@protoc_insertion_point(class_scope:protobuf.ImageTransform.QrCodeLocation)
    ))
  ,
  DESCRIPTOR = _IMAGETRANSFORM,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.ImageTransform)
  ))
_sym_db.RegisterMessage(ImageTransform)
_sym_db.RegisterMessage(ImageTransform.Point)
_sym_db.RegisterMessage(ImageTransform.QrCodeLocation)

HvRegulator = _reflection.GeneratedProtocolMessageType('HvRegulator', (_message.Message,), dict(
  DESCRIPTOR = _HVREGULATOR,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.HvRegulator)
  ))
_sym_db.RegisterMessage(HvRegulator)

TemperatureControl = _reflection.GeneratedProtocolMessageType('TemperatureControl', (_message.Message,), dict(
  DESCRIPTOR = _TEMPERATURECONTROL,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.TemperatureControl)
  ))
_sym_db.RegisterMessage(TemperatureControl)

DeviceInfo = _reflection.GeneratedProtocolMessageType('DeviceInfo', (_message.Message,), dict(
  DESCRIPTOR = _DEVICEINFO,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.DeviceInfo)
  ))
_sym_db.RegisterMessage(DeviceInfo)

PurpleDropEvent = _reflection.GeneratedProtocolMessageType('PurpleDropEvent', (_message.Message,), dict(
  DESCRIPTOR = _PURPLEDROPEVENT,
  __module__ = 'protobuf.messages_pb2'
  # @@protoc_insertion_point(class_scope:protobuf.PurpleDropEvent)
  ))
_sym_db.RegisterMessage(PurpleDropEvent)


# @@protoc_insertion_point(module_scope)
