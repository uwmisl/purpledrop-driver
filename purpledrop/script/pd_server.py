from gevent import monkey
monkey.patch_all()

import click
import logging

from purpledrop.purpledrop import PersistentPurpleDropDevice, PurpleDropController
import purpledrop.server as server

@click.command()
@click.option('-v', '--verbose', count=True, help='-v for INFO, -vv for DEBUG')
def main(verbose):
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

    pd_dev = PersistentPurpleDropDevice()
    pd_control = PurpleDropController(pd_dev)

    # TODO: make video host configurable
    pdcam_host = "localhost:5000"
    server.run_server(pd_control, pdcam_host)

if __name__ == '__main__':
    main()