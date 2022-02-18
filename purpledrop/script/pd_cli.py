from gevent import monkey
monkey.patch_all()

import click
import logging
import sys

from purpledrop.purpledrop import SerialPurpleDropDevice, list_purpledrop_devices
import purpledrop.messages as messages

def get_device():
    devices = list_purpledrop_devices()
    if(len(devices) == 0):
        print("No PurpleDrop USB device found")
        sys.exit(1)
    elif len(devices) > 1:
        print("Multiple PurpleDrop devices found. Please ammend software to allow selection by serial number")
        for d in devices:
            print(f"{d.device}: Serial {d.serial_number}")
        sys.exit(1)

    return devices[0]
@click.group()
def main():
    pass

@main.command()
@click.option('-v', '--verbose', count=True, help='-v for INFO, -vv for DEBUG')
def info(verbose):
    """Get device information from a connected purpledrop
    """

    if verbose == 0:
        console_log_level = logging.WARNING
    elif verbose == 1:
        print("Setting stdout logging to INFO")
        console_log_level = logging.INFO
    else:
        print("Setting stdout logging to DEBUG")
        console_log_level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)s (%(name)s): %(message)s",
        datefmt="%H:%M:%S",
        level=console_log_level)

    device = get_device()
    port = device.device
    print(f"Connecting to {port}")
    print(f"Serial number: {device.serial_number}")
    pd = SerialPurpleDropDevice(port)
    with pd.get_sync_listener(msg_filter=messages.DataBlobMsg) as listener:
        versionRequest = messages.DataBlobMsg()
        versionRequest.blob_id = messages.DataBlobMsg.SOFTWARE_VERSION_ID
        pd.send_message(versionRequest)
        msg = listener.next(1.0)
    if msg is None:
        print("Timeout waiting for version response")
    else:
        print(f"Software version: {msg.payload.decode('utf-8')}")

if __name__ == '__main__':
    main()