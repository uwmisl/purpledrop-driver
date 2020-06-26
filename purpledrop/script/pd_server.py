from gevent import monkey
monkey.patch_all()

import click
import logging
import sys

from purpledrop.electrode_board import load_board
from purpledrop.purpledrop import PersistentPurpleDropDevice, PurpleDropController
from purpledrop.playback import PlaybackPurpleDrop, index_log
from purpledrop.video_client import VideoClientProtobuf
import purpledrop.server as server

@click.command()
@click.option('-v', '--verbose', count=True, help='-v for INFO, -vv for DEBUG')
@click.option('--board', 'board_file', help='Board name or path to board definition JSON file', default='misl_v4')
@click.option('--replay', 'replay_file', help='Launch replay server instead of connecting to HW', required=False)
def main(verbose, board_file, replay_file):
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
        print("Could not load board definition for {board_file}")
        sys.exit(1)

    video_client = None
    if replay_file is not None:
        print(f"Computing seek index for {replay_file}...")
        index, end_time = index_log(replay_file)
        start_time = index[0].timestamp
        print(f"Done. Loaded {end_time - start_time} seconds of data.")
        print("Launching replay server...")
        pd_control = PlaybackPurpleDrop(replay_file, index, board)
    else:
        pd_dev = PersistentPurpleDropDevice()
        pd_control = PurpleDropController(pd_dev, board)
        print("Launching HW server...")
        # TODO: make video host configurable
        video_host = "localhost:5000"
        video_client = VideoClientProtobuf(video_host)

    server.run_server(pd_control, video_client)

if __name__ == '__main__':
    main()