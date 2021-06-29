# Calibration

## Electrode Offset Capacitance

This calibration accounts for the capacitance of each electrode when no liquid
is present on the board. This capacitance depends on electrode size, trace
length, distance of the top plate from the electrodes, etc. It is calibrated
by measuring the capacitance of each electrode while empty, at high gain, at
a voltage setting near where you intend to operate[^voltage].

The calibration is loaded by the purpledrop-driver software to the device upon
connecting. If a calibration file is stored in 
`~/.config/purpledrop/electrode_calibrations/<board name>.json`, it will be 
automatically loaded when that board is used. 

### Example calibration script

```python
#calibrate_electrodes.py
import click
import json
import numpy as np
import pdclient
import time

@click.command()
@click.option('-h', '--host', default='localhost', help="Hostname of purpledrop")
@click.option('-o', '--output', help="File to store calibration to")
@click.option('-n', type=int, default=32, help="Number of sample to collect")
def main(host, output, n):
    client = pdclient.PdClient(f'http://{host}:7000/rpc')
    # Set the active calibration to zeros before measuring
    client.client.set_electrode_calibration(200.0, [0]*128)
    samples = []
    for _ in range(n):
        samples.append(client.scan_capacitance()['raw'])
        time.sleep(1.0)
    voltage = client.hv_supply_voltage()
    offsets = np.median(samples, axis=0).tolist()
    offsets = [int(x) for x in offsets]
    cal = {
        'voltage': voltage,
        'offsets': offsets
    }
    if output is not None:
        with open(output, 'w') as f:
            f.write(json.dumps(cal))
    else:
        print(json.dumps(cal))

    # Store the calibration back to the device
    client.client.set_electrode_calibration(voltage, offsets)

if __name__ == '__main__':
    main()
```

To take a calibration, and store it so that it will be automatically loaded
whenever the 'misl_4.1' board is used: 
`python3 calibrate_electrodes.py -h <pdserver host or ip> -o ~/.config/purpledrop/electrode_calibrations/misl_v4.1.json`

The `pdserver` process should already be running when you run this script.

[^voltage]: The calibration value will be adjusted when used based on the 
current operating voltage. Calibrating at a similar voltage limits the size of
this correction.

## Capacitance Amplifier Offset Calibration

This calibration corrects for the offset in the integrator circuit which will
be read even when no charge current is present. This is a single scalar, and
because it does not depend on the state of the device (e.g. whether there
is any liquid on the board, or whether there is even a board plugged in or if
the high voltage supply is turned on) it is automatically measured by the
software every time the board is powered on. A re-calibration can be forced
by calling the `calibrate_capacitance_offset` RPC method. This is not 
generally necessary, but may be necessary in certain cases. The main example
is that it can be sensitive to the sampling period configuration parameters;
if these ared changed you should re-calibrate the amplifier offset manually.
