"""Defines an HTTP server for controlling the PurpleDrop.

The server acts as a gateway between the PurpleDrop USB device, and any clients.
It also serves a single-page javascript app, which provides a user interface for
controlling the PurpleDrop.

The server consists of:
  - HTTP server proving a JSON-RPC endpoint, and serving the single-page app
  - A websocket which provides a stream of events for real-time state update
"""

import gevent
from gevent.pywsgi import WSGIServer
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource
from geventwebsocket.exceptions import WebSocketError
from flask import Flask, Response, send_file
from jsonrpc.backend.flask import api
import logging
import pkg_resources
import tarfile

from .controller import PurpleDropController

logger = logging.getLogger('purpledrop')

class Config(object):
    """Collects configuration parameters for server and defines defaults
    """
    HTTP_PORT = 7000
    WS_PORT = 7001
    WEBROOT = None

class EventApp(WebSocketApplication):
    """Empty Application. This server only broadcasts events
    """
    def on_message(self, msg):
        pass

def extract_frontend_file(path):
    tarball_data = pkg_resources.resource_stream('purpledrop', 'frontend-dist.tar.gz')
    #print(f"Tarball is {len(tarball_data)}")
    tar = tarfile.open(fileobj=tarball_data)
    return tar.extractfile(path)

def run_server(purpledrop: PurpleDropController, video_client=None):
    lock = gevent.lock.Semaphore()

    flask_app = Flask(__name__)

    def return_files(path):
        logger.debug(f"GET {path}")
        try:
            return send_file(extract_frontend_file(path), attachment_filename=path)
        except KeyError:
            logger.info(f"File {path} not found. Returning 404.")
            return Response("File not found", status=404)

    flask_app.add_url_rule(
        '/rpc', view_func=api.as_view(), methods=['POST'])
    flask_app.add_url_rule(
        '/rpc/map', view_func=api.jsonrpc_map, methods=['GET'])
    flask_app.add_url_rule(
        '/<path:path>', view_func=return_files, methods=['GET'])
    flask_app.add_url_rule(
        '/', view_func=return_files, methods=['GET'], defaults={'path':'index.html'})

    # Register RPC methods
    for method_name in purpledrop.RPC_METHODS:
        api.dispatcher.add_method(getattr(purpledrop, method_name))

    http_server = WSGIServer(('', 7000), flask_app, log=None)
    http_server.start()

    ws_server = WebSocketServer(('', 7001), Resource([('^/', EventApp)]), debug=False)
    ws_server.start()


    def handle_event(event):
        data = event.SerializeToString()
        with lock:
            for client in ws_server.clients.values():
                try:
                    client.ws.send(data)
                except WebSocketError:
                    pass

    def handle_video_update(image_event, transform_event):
        for event in [transform_event, image_event]:
            data = event.SerializeToString()
            with lock:
                clients = list(ws_server.clients.values())
                for client in clients:
                    try:
                        client.ws.send(data)
                    except WebSocketError:
                        pass

    if video_client is not None:
        video_client.register_callback(handle_video_update)

    purpledrop.register_event_listener(handle_event)

    while(True):
        gevent.sleep(1.0)


