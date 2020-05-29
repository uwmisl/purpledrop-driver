
import {protobuf} from 'protobuf';

// Create a websocket client which will reconnect
export default function PdSocket(callback) {

  let eventsocket = null;
  let closed = false;

  let wrapped_socket = {
    close() {
      console.log("Disconnecting event socket");
      closed = true;
      eventsocket.close();
    },
  };

  function create_socket(uri) {
    //let eventsocket = new WebSocket(`ws://${location.hostname}:7001`);
    eventsocket = new WebSocket(uri);
    //let eventsocket = new WebSocket('ws://localhost:7001')

    eventsocket.onclose = () => {
      console.log('WebSocket closed. Will attempt reconnect.');
      setTimeout(() => {
        if(!closed) {
          console.log("Creating new event socket");
          create_socket(uri);
        }
      }, 5000);
    };
    eventsocket.onerror = (error) => {
        console.log('Websocket error: ', error);
    };
    eventsocket.onmessage = (event) => {
        event.data.arrayBuffer().then((buf) => {
            let data = new Uint8Array(buf);
            let msg = protobuf.PurpleDropEvent.decode(data);
            callback(msg);
        });
    };
  }
   //let eventsocket = new WebSocket(`ws://${location.hostname}:7001`);
   //let eventsocket = new WebSocket(');
   //let eventsocket = new WebSocket('ws://localhost:7001')
  create_socket('ws://10.144.112.21:7001');
  
  return wrapped_socket;
}