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
from flask import Flask
from jsonrpc.backend.flask import api

from .purpledrop import PurpleDropController, PurpleDropRpc


class Config(object):
    """Collects configuration parameters for server and defines defaults
    """
    HTTP_PORT = 7000
    WS_PORT = 7001
    WEBROOT = None


class EventApp(WebSocketApplication):
    """Empty Application. Could override methods, e.g. `on_message` to
    handle incoming data, but atm this server only broadcasts events
    """
    pass
    

def run_server(purpledrop: PurpleDropController):
    flask_app = Flask(__name__)

    flask_app.add_url_rule(
        '/rpc', view_func=api.as_view(), methods=['POST'])
    flask_app.add_url_rule(
        '/rpc/map', view_func=api.jsonrpc_map, methods=['GET'])

    pdrpc = PurpleDropRpc(purpledrop)

    # Register all public methods of pdrpc as RPC calls
    api.dispatcher.build_method_map(pdrpc)
    
    http_server = WSGIServer(('', 7000), flask_app)
    http_server.start()

    ws_server = WebSocketServer(('', 7001), Resource([('^/', EventApp)]), debug=False)
    ws_server.start()

    def handle_event(event):
        data = event.SerializeToString()
        for client in ws_server.clients.values():
            client.ws.send(data)

    purpledrop.register_event_listener(handle_event)

    while(True):
        gevent.sleep(1.0)


