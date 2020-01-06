import Board from './Board';
import jsonRpc from 'simple-jsonrpc-js';
import {protobuf} from '../protobuf';


// Hook-up transport for simple-jsonrpc-js
let rpc = new jsonRpc();
rpc.toStream = (msg) => {
    fetch('/rpc', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: msg,
    }).then(async (response) => {
        let body = await response.text();
        rpc.messageHandler(body);
    });
};

function persistent_socket() {
    let eventsocket = new WebSocket(`ws://${location.hostname}:2129`);
    eventsocket.onclose = () => {
        console.log('WebSocket closed. Will attempt reconnect.');
        setTimeout(persistent_socket, 5000);
    };
    eventsocket.onerror = (error) => {
        console.log('Websocket error: ', error);
    };
    eventsocket.onmessage = (event) => {
        event.data.arrayBuffer().then((buf) => {
            let data = new Uint8Array(buf);
            let msg = protobuf.PurpleDropEvent.decode(data);
            handle_event(msg);
        });
    };
}

persistent_socket();

function handle_event(event) {
    if (event.electrodeState) {
        Pd.board = new Board(Pd.board.config, event.electrodeState.electrodes);
        m.redraw();
    }
    else if(event.image) {
        let oldUrl = Pd.Video.latestFrame;
        let blob = new Blob([event.image.imageData]);
        Pd.Video.latestFrame = URL.createObjectURL(blob);
        URL.revokeObjectURL(oldUrl);
        Pd.Video.latestFrameTimestamp = Date.now();
        m.redraw();
    } else if(event.imageTransform) {
        if (event.imageTransform.transform.length > 0) {
            let t =  event.imageTransform.transform;
            Pd.Video.latestTransform = [
                [t[0], t[1], t[2]],
                [t[3], t[4], t[5]],
                [t[6], t[7], t[8]],
            ];
        } else {
            Pd.Video.latestTransform = null;
        }
        Pd.Video.latestTransformTimestamp = Date.now();
        Pd.Video.imageWidth = event.imageTransform.imageWidth;
        Pd.Video.imageHeight = event.imageTransform.imageHeight;
        m.redraw();
    }
}

const Video = {
    DATA_TIMEOUT: 5000, // ms
    latestFrame: null,
    latestFrameTimestamp: Date.now(),
    latestTransform: null,
    latestTransformTimestamp: Date.now(),
    imageWidth: 1024,
    imageHeight: 768,

    isFrameValid() {
        let age = Date.now() - Video.latestFrameTimestamp;
        if(Video.latestFrame == null || age > Video.DATA_TIMEOUT) {
            return false;
        }
        return true;
    },

    isTransformValid() {
        let age = Date.now() - Video.latestTransformTimestamp;
        if (Video.latestTransform == null || age > Video.DATA_TIMEOUT) {
            return false;
        }
        return true;
    },
};

export const Pd = {
    board: null,

    Video: Video,

    init() {
        return this.getBoardDefinition()
            .then((config) => {
                Pd.board = new Board(config);
            });
    },
    getBoardDefinition() {
        return rpc.call('get_board_definition');
    },
    setElectrodePins(pins) {
        // Send a list of activated pin numbers, e.g. [4, 2, 100] will enable
        // electrode outputs 4, 2, and 100 while disabling all others.
        return rpc.call('set_electrode_pins', [pins]);
    },
};

export default Pd;
