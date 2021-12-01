from gevent import monkey
monkey.patch_all()

import click
import logging
import sys
import os

from purpledrop.calibration import load_electrode_offset_calibration
from purpledrop.electrode_board import load_board
from purpledrop.purpledrop import PersistentPurpleDropDevice
from purpledrop.controller import PurpleDropController
from purpledrop.playback import PlaybackPurpleDrop, index_log
from purpledrop.simulated_purpledrop import SimulatedPurpleDropDevice
from purpledrop.video_client import VideoClientProtobuf
import purpledrop.server as server

@click.command()
@click.option('-v', '--verbose', count=True, help='-v for INFO, -vv for DEBUG')
@click.option('--board', 'board_file', help='Board name or path to board definition JSON file', default='misl_v4')
@click.option('--ecal', 'electrode_calibration_file', help='Name of calibration or path to JSON file', required=False)
@click.option('--replay', 'replay_file', help='Launch replay server instead of connecting to HW', required=False)
@click.option('--sim', help='Simulate a purpledrop device', required=False)
def main(verbose, board_file, replay_file, sim, electrode_calibration_file=None, ):
    """Runs hardware gateway

    Will auto-connect to any detected purpledrop USB devices, and provides HTTP interfaces for control.
    Optionally, supports replay and simulation mode.

    In replay mode, a recorded event stream is played back.

    In sim mode, a simple simulated purpledrop device replaces actual hardware
    connection to allow for testing control scripts. Drops may be populated on
    some electrodes by providing a list of pins to the --sim argument. The
    simulator implements a very simple drop model, where each electrode is either
    empty or covered, and a drop on an inactive electrode can move to an active
    neighboring electrode. Only grid electrodes are supported (e.g. no reservoirs).

    For example: `pdserver --sim 5,10,120` to create a simulation starting with
    drops present on electrodes 5, 10, and 120.
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

    if replay_file is not None and sim is not None:
        print("Cannot run both --replay and --sim")
        sys.exit(-1)

    board = load_board(board_file)
    if board is None:
        print(f"Could not load board definition for {board_file}")
        sys.exit(1)

    ecal = None
    if sim is None:
        if electrode_calibration_file is not None:
            print(f"Loading calibration from {electrode_calibration_file}")
            ecal = load_electrode_offset_calibration(electrode_calibration_file)
        elif not os.path.exists(board_file):
            ecal = load_electrode_offset_calibration(board_file)
            if ecal is not None:
                print(f"Loading calibration based on {board_file} board name")

    video_client = None
    if replay_file is not None:
        print(f"Computing seek index for {replay_file}...")
        index, end_time = index_log(replay_file)
        start_time = index[0].timestamp
        print(f"Done. Loaded {end_time - start_time} seconds of data.")
        print("Launching replay server...")
        pd_control = PlaybackPurpleDrop(replay_file, index, board)
    elif sim:
        drop_pins = [int(x) for x in sim.split(',')]
        pd_dev = SimulatedPurpleDropDevice(board, drop_pins)
        pd_control = PurpleDropController(pd_dev, board, ecal)
        pd_dev.open()
    else:
        print("Launching HW server...")
        pd_dev = PersistentPurpleDropDevice()
        pd_control = PurpleDropController(pd_dev, board, ecal)
        # TODO: make video host configurable
        video_host = "localhost:5000"
        video_client = VideoClientProtobuf(video_host)

    server.run_server(pd_control, video_client)

if __name__ == '__main__':
    main()