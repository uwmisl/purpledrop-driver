import asyncio
import click
import struct
import websockets

import purpledrop.protobuf.messages_pb2 as messages_pb2

async def record(uri, filepath, verbose):
    with open(filepath, 'wb') as f:
        async with websockets.connect(uri) as ws:
            while True:
                raw_event = await ws.recv()
                if verbose:
                    event = messages_pb2.PurpleDropEvent()
                    event.ParseFromString(raw_event)
                    print(event.WhichOneof('msg'))
                length_bytes = struct.pack('I', len(raw_event))
                f.write(length_bytes)
                f.write(raw_event)

@click.command()
@click.option('--host', help="Websocket URI (e.g. 'ws://localhost:7001')", default='ws://localhost:7001')
@click.option('-v', '--verbose', is_flag=True, default=False)
@click.argument('filename', required=True)
def main(host, filename, verbose):
    asyncio.run(record(host, filename, verbose))

if __name__ == '__main__':
    main()