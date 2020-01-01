export class Board {
    constructor(config, active_pins) {
        active_pins = active_pins || [];
        this.height = config.layout.pins.length;
        this.width = 0;
        this.config = config;
        config.layout.pins.forEach((row) => {
            if(row.length > this.width) {
                this.width = row.length;
            }
        });
        this.grid = config.layout.pins.map((row) => {
            return row.map((elem) => {
                let pin = parseInt(elem);
                if(isNaN(pin)) {
                    return {
                        pin: null,
                        active: false,
                    };
                } else {
                    return {
                        pin: pin,
                        active: active_pins[pin] || false,
                    };
                }
            });
        });
    }

    clone() {
        return new Board(this.config, this.activePinVector());
    }

    deactivateAll() {
        return new Board(this.config);
    }

    activate(row, col) {
        let clone = this.clone();
        clone.grid[row][col].active = true;
        return clone;
    }

    deactivate(row, col) {
        let clone = this.clone();
        clone.grid[row][col].active = false;
        return clone;
    }

    isActive(row, col) {
        return this.grid[row][col].active;
    }

    activePinList() {
        let activePins = [];
        for(var row=0; row<this.height; row++) {
            for(var col=0; col<this.width; col++) {
                if(this.grid[row][col].active) {
                    activePins.push(this.grid[row][col].pin);
                }
            }
        }
        return activePins;
    }

    activePinVector() {
        let vec = [];
        for(var i=0; i<128; i++) {
            vec.push(false);
        }
        this.activePinList().forEach((p) => {
            vec[p] = true;
        });
        return vec;
    }

    /* Activate electrodes at an offset from each currently active electrode */
    move(xdelta, ydelta) {
        let activePositions = [];
        for(var row=0; row<this.height; row++) {
            for(var col=0; col<this.width; col++) {
                if(this.grid[row][col].active) {
                    activePositions.push([row, col]);
                }
            }
        }
        let clone = this.deactivateAll();
        activePositions.forEach((p) => {
            let newRow = p[0] + ydelta;
            let newCol = p[1] + xdelta;
            if(newRow < 0 || newCol < 0 || newRow >= clone.height || newCol >= clone.width) {
                return;
            }
            if(clone.grid[newRow][newCol].pin === null) {
                // No electrode at this coordinate, so we drop it
                return;

            }
            clone.grid[newRow][newCol].active = true;
        });
        return clone;
    }
}

export default Board;