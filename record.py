import asyncio
import click
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
                f.write(raw_event)

@click.command()
@click.argument('host')
@click.argument('outfile')
@click.option('-v', '--verbose', is_flag=True, default=False)
def main(host, outfile, verbose):
    asyncio.run(record(host, outfile, verbose))

if __name__ == '__main__':
    main()
    
