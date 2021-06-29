from gevent import monkey
monkey.patch_all()

import click
import logging
import sys
import os

from purpledrop.calibration import load_electrode_offset_calibration
from purpledrop.electrode_board import load_board
from purpledrop.purpledrop import PersistentPurpleDropDevice, PurpleDropController
from purpledrop.playback import PlaybackPurpleDrop, index_log
from purpledrop.video_client import VideoClientProtobuf
import purpledrop.server as server

@click.command()
@click.option('-v', '--verbose', count=True, help='-v for INFO, -vv for DEBUG')
@click.option('--board', 'board_file', help='Board name or path to board definition JSON file', default='misl_v4')
@click.option('--ecal', 'electrode_calibration_file', help='Name of calibration or path to JSON file', required=False)
@click.option('--replay', 'replay_file', help='Launch replay server instead of connecting to HW', required=False)
def main(verbose, board_file, replay_file, electrode_calibration_file=None):
    """Runs hardware gateway

    Will auto-connect to any detected purpledrop USB devices, and provides HTTP interfaces for control.
    Optionally, supports replay mode in which a recorded event stream is played back
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

    board = load_board(board_file)
    if board is None:
        print(f"Could not load board definition for {board_file}")
        sys.exit(1)

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