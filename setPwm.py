#!/usr/bin/env python3

import click
import sys
import time

from purpledrop.messages import SetPwmMsg, CommandAckMsg
from purpledrop.purpledrop import PurpleDropDevice, list_purpledrop_devices

@click.command()
@click.argument("chan", type=int)
@click.argument("duty_cycle", type=float)
def main(chan, duty_cycle):
    msg = SetPwmMsg()
    msg.chan = chan
    msg.duty_cycle = duty_cycle
    
    devices = list_purpledrop_devices()
    if(len(devices) == 0):
        print("No PurpleDrop USB device found")
        sys.exit(1)
    elif len(devices) > 1: 
        print("Multiple PurpleDrop devices found. Please ammend software to allow selection by serial number")
        for d in devices:
            print(f"{d.device}: Serial {d.serial_number}")
        sys.exit(1)
    print(f"Connecting to purple drop on {devices[0].device}")
    dev = PurpleDropDevice(devices[0].device)
    listener = dev.get_sync_listener(msg_filter=CommandAckMsg)
    print("Sending Message\n")
    dev.send_message(msg)
    print("Waiting for ack\n")
    ack = listener.wait(timeout=1.0)
    if ack is None:
        print("No ACK message received")
    else:
        print("Got ACK: " + str(ack))

    
if __name__ == '__main__':
    main()