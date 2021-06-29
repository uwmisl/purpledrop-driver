"""Utilities for reading electrode capacitance calibration data
"""
import json
import os
from typing import Optional, List

class ElectrodeOffsetCalibration(object):
    def __init__(self, voltage: float, offsets: List[int]):
        """Create an object representing an offset calibration

        Provides a measurement of the parasitic capacitance measured for each
        electrode when no liquid is present. The measurement is performed at
        some reference voltage, which is provided. 

        voltage: The voltage (in volts) at which calibration was performed
        offsets: The measurement in raw counts, at high gain for each electrode
        """
        self.voltage = voltage
        self.offsets = offsets

    @staticmethod
    def load_from_file(fname: str) -> 'ElectrodeOffsetCalibration':
        with open(fname, 'r') as f:
            data = json.loads(f.read())
        if 'electrode_offsets' not in data:
            raise ValueError(f"Could not find 'electrode_offset' attribute in {fname}")
        data = data['electrode_offsets']
        if 'voltage' not in data:
            raise ValueError(f"Electrode Offset Calibration must contain a 'voltage' attribute ({fname})")
        if 'offsets' not in data:
            raise ValueError(f"Electrode Offset Calibration must contain a 'offsets' attribute ({fname})")
        
        return ElectrodeOffsetCalibration(float(data['voltage']), [int(x) for x in data['offsets']])

def load_electrode_offset_calibration(name) -> Optional[ElectrodeOffsetCalibration]:
    """Load a calibration by name

    Attempt to load a board definition from the name, using the following
    priorities (the first to succeed is returned):

    1. Load as a full path
    2. Load from ~/.config/purpledrop/electrode_calibrations/{name}.json
    """
    if os.path.isfile(name):
        return ElectrodeOffsetCalibration.load_from_file(name)

    home_path = os.path.expanduser(f"~/.config/purpledrop/electrode_calibrations/{name}.json")
    if os.path.isfile(home_path):
        return ElectrodeOffsetCalibration.load_from_file(home_path)

    return None
