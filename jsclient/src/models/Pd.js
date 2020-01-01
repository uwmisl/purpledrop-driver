import Board from './Board';
import jsonRpc from 'simple-jsonrpc-js';
import {protobuf} from 'protobuf';


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
            console.log(msg);
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
}


export const Pd = {
    board: null,

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

const video_host = 'http://10.144.112.21:5000';

export const Video = {
    lastFrameNum: 0,
    latestFrame: null,
    latestTransform: null,
    imageWidth: 1024,
    imageHeight: 768,

    update: () => {
        // return Promise.all([
        //     Video.getLatestFrame(),
        //     Video.getLatestTransform()]);
        return Video.getLatestTransform();
    },
    getLatestFrame: () => {
        return fetch(video_host + '/latest', {
            method: 'GET',
            headers: {
                'X-Min-Frame-Number': Video.lastFrameNum + 1,
            },
        }).then((response) => {
            Video.lastFrameNum = parseInt(response.headers.get('X-Frame-Number') || 0);
            return response.blob();
        }).then((blob) => {
            Video.latestFrame = URL.createObjectURL(blob);
        }).catch(error => {
            console.error('Error fetching frame: ' + error);
        });
    },
    getLatestTransform: () => {
        return fetch(video_host + '/transform', {
            method: 'GET',
        }).then((response) => {
            return response.json();
        }).then((json) => {
            Video.latestTransform = json.transform;
            Video.imageWidth = json.image_width;
            Video.imageHeight = json.image_height;
        }).catch(error => {
            console.error('Error fetching transform: ' + error);
        });
    },
};

export default Pd;