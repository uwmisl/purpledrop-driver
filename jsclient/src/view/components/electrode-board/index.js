import './styles.scss';
import {Pd, Video} from '../../../models/Pd';

export default function() {
    var board = null;
    var brushSize = 2;
    var hoverPositions = {};

    let handler = (e, position) => {
        let row = position[1];
        let col = position[0];
        console.log(`Clicked pin ${board.grid[row][col].pin} @ ${row}, ${col}`);
        if(!e.shiftKey) {
            board.deactivateAll();
        }
        for(var x=0; x<brushSize; x++) {
            for(var y=0; y<brushSize; y++) {
                board.activate(row+y, col+x);
            }
        }
        board.writeToDevice();
    };

    let move = (xdelta, ydelta) => {
        console.log('move: ', xdelta, ydelta);
        board.move(xdelta, ydelta);
        m.redraw();
        board.writeToDevice();
    };

    let onMouseOut = () => {
        hoverPositions = {};
    };

    let onMouseOver = (position) => {
        let row = position[1];
        let col = position[0];
        hoverPositions = {};
        for(var x=0; x<brushSize; x++) {
            for(var y=0; y<brushSize; y++) {
                hoverPositions[[col+x, row+y]] = true;
            }
        }
    };

    let createElectrode = (position, active, hover, M) => {
        let cstr = hover ? 'electrode hover' : (active ? 'electrode active' : 'electrode');

        const cornerOffset = 0.1;

        // Points in grid coordinates, where each electrode's top-left corner
        // is at integer coordinate (n, m)
        let points = [
            [position[0] + cornerOffset, position[1] + cornerOffset],
            [position[0] + 1 - cornerOffset, position[1] + cornerOffset],
            [position[0] + 1 - cornerOffset, position[1] + 1 - cornerOffset],
            [position[0] + cornerOffset, position[1] + 1 - cornerOffset],
        ];

        let image_points = points.map((p) => {
            let x = M[0][0] * p[0] + M[0][1] * p[1] + M[0][2];
            let y = M[1][0] * p[0] + M[1][1] * p[1] + M[1][2];
            let z = M[2][0] * p[0] + M[2][1] * p[1] + M[2][2];
            return [x / z, y / z];
        });
        return <polygon
            class={cstr}
            onmouseout={() => onMouseOut(position)}
            onmouseover={() => onMouseOver(position)}
            onclick={(e) => handler(e, position)}
            points={image_points.map((p) => `${p[0]}, ${p[1]}`).join(' ')}
        />;
    };

    function incrementBrushSize() {
        if(brushSize < 5) {
            brushSize++;
        }
    }

    function decrementBrushSize() {
        if(brushSize > 1) {
            brushSize--;
        }
    }

    return {
        oninit: function() {
            window.addEventListener('keydown', function (event) {
                if (event.defaultPrevented) {
                    return; // Do nothing if the event was already processed
                }

                switch (event.key) {
                case 'ArrowDown':
                    move(0, 1);
                    break;
                case 'ArrowUp':
                    move(0, -1);
                    break;
                case 'ArrowLeft':
                    move(-1, 0);
                    break;
                case 'ArrowRight':
                    move(1, 0);
                    break;
                default:
                    return; // Quit when this doesn't handle the key event.
                }

                // Cancel the default action to avoid it being handled twice
                event.preventDefault();
            }, true);
        },
        view: function(vnode) {
            let board = vnode.attrs.board;
            let electrodePolys = [];

            for(let row=0; row < board.height; row++) {
                for(let col=0; col < board.width; col++) {
                    let cell = board.grid[row][col];
                    let position = [col, row];
                    if(cell.pin !== null) {
                        let transform = null;
                        if (Video.latestTransform) {
                            transform = Video.latestTransform;
                        } else {
                            // If no transform, just create a default to put the grid into the center of the img div
                            // Although transform is not, Video.imageWidth/imageHeight should always be valid
                            let scale = Math.min(Video.imageWidth, Video.imageHeight) / Math.max(board.width, board.height) * 0.8;
                            transform = [
                                [scale, 0.0, (Video.imageWidth - board.width * scale) / 2],
                                [0.0, scale, (Video.imageHeight - board.height * scale) / 2],
                                [0.0, 0.0, 1.0],
                            ];
                        }
                        electrodePolys.push(createElectrode(position, cell.active, hoverPositions[position], transform));
                    }
                }
            }

            return <div>
                <div class="toolbar">
                    <button class="brushsize" onclick={() => decrementBrushSize()}>Smaller</button>
                    <input id="brushsize" type="text" disabled value={brushSize} name="brushsize" />
                    <button class="brushsize" onclick={() => incrementBrushSize()}>Bigger</button>
                </div>
                <div class='electrode-grid-wrapper'>
                    {/* TODO: /latest is a lot of requests and the browser seems to work very hard. 
                     the MJPEG route doesn't recover well from errors. Need to resolve this still... */}
                    {/* <img class='electrode-grid-img' src={Video.latestFrame} /> */}
                    <img class='electrode-grid-img' src='http://10.144.112.21:5000/video' />
                    <svg class='electrode-grid-svg' viewBox={`0 0 ${Video.imageWidth} ${Video.imageHeight}`}>
                        {electrodePolys}
                    </svg>
                </div>
            </div>;
        },
    };
}