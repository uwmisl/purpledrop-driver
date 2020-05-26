#!/usr/bin/env python3

import click
import sys
import time

from purpledrop.messages import SetParameterMsg
from purpledrop.purpledrop import PurpleDropDevice, list_purpledrop_devices

@click.command()
@click.argument("id", type=int)
@click.argument("value")
@click.option('--float', is_flag=True)
def main(id, value, float):
    msg = SetParameterMsg()
    msg.set_param_idx(id)
    if float:
        msg.set_param_value_float(float(value))
    else:
        msg.set_param_value_int(int(value))
    
    msg.set_write_flag(True)

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
    listener = dev.get_sync_listener(msg_filter=SetParameterMsg)
    dev.send_message(msg)
    ack = listener.wait(timeout=1.0)
    if ack is None:
        print("No ACK message received")
    else:
        print("Got ACK: " + str(ack))

    
if __name__ == '__main__':
    main()