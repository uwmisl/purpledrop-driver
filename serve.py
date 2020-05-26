import sys
from gevent import monkey
monkey.patch_all()

import purpledrop.server as server
from purpledrop.purpledrop import list_purpledrop_devices, PurpleDropDevice, PurpleDropController

devices = list_purpledrop_devices()
if(len(devices) == 0):
    print("No PurpleDrop USB device found")
    sys.exit(1)
elif len(devices) > 1: 
    print("Multiple PurpleDrop devices found. Please ammend software to allow selection by serial number")
    for d in devices:
        print(f"{d.device}: Serial {d.serial_number}")
    sys.exit(1)
dev = PurpleDropDevice(devices[0].device)
controller = PurpleDropController(dev)

server.run_server(controller)