import click
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
def info():
    """Get device information from a connected purpledrop
    """
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