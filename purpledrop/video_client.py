import logging
import requests
import threading
import time
from typing import AnyStr

import purpledrop.protobuf.messages_pb2 as messages_pb2

class VideoClient(object):
    def __init__(self, host: str, callback):
        self.host = host
        self.callback = callback
        self.last_frame = 0
        self.connected = False

        self.thread = threading.Thread(name="VideoClient", daemon=True, target=self.run)
        self.thread.start()

    def run(self):
        while True:
            self.last_frame = 0
            s = requests.Session()

            try:
                resp = requests.get(
                    f"http://{self.host}/latest",
                    headers={'X-Min-Frame-Number': str(self.last_frame + 1)},
                    stream=True,
                )
                resp.raise_for_status()
                self.last_frame = int(resp.headers.get('X-Frame-Number'))
                jpeg_bytes = resp.content

                resp = requests.get(f"http://{self.host}/transform")
                resp.raise_for_status()
                transform = resp.json()

                self.callback(jpeg_bytes, transform)
                if not self.connected:
                    self.connected = True
                    logging.info("Connected to video host")

            except requests.exceptions.RequestException as ex:
                logging.debug(f"Failed to capture frame from video host: {ex}")
                if(self.connected):
                    self.connected = False
                    logging.info("Lost connection to video host")
                time.sleep(3.0)


class VideoClientProtobuf(object):
    def __init__(self, host, callback):
        self.client = VideoClient(host, self.handler)
        self.callback = callback

    def handler(self, jpeg, transform):
        image_event = messages_pb2.PurpleDropEvent()
        transform_event = messages_pb2.PurpleDropEvent()

        timestamp = time.time()
        image_event.image.timestamp.seconds = int(timestamp)
        image_event.image.timestamp.nanos = int((timestamp % 1) * 1e9)
        image_event.image.image_data = jpeg
        transform_event.image_transform.timestamp.seconds = int(timestamp)
        transform_event.image_transform.timestamp.nanos = int((timestamp % 1) * 1e9)
        if transform['transform'] is not None:
            transform_event.image_transform.transform[:] = sum(transform['transform'], [])
        else:
            transform_event.image_transform.transform[:] = []
        transform_event.image_transform.image_width = transform['image_width']
        transform_event.image_transform.image_height = transform['image_height']
        self.callback(image_event, transform_event)

