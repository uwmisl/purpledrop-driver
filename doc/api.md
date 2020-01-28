# APIs for controlling Purple Drop

The Purple Drop software provides a [JSON-RPC](www.jsonrpc.org) based api for controlling purpledrop, as well as a WebSocket event stream for getting asynchronous state updates.

## RPC API

The JSON RPC api is served via HTTP on port 80 of your purpledrop. For instructions on how to setup networking on your purple drop, see [PI Setup](pi-setup.md).

The endpoint for all RPC calls is `/rpc`.

### Method: get_board_definition

Retrieves the electrode board definition currently in use by the purple drop. This defines the layout of the electrode grid, and the mapping of grid positions to electrode pin numbers. 

#### Example Request

```json
POST /rpc
{
    "method": "get_board_definition",
    "params": [],
    "jsonrpc": "2.0",
    "id": 1,
}
```

#### Example Response

```json
{
    "jsonrpc": "2.0",
    "result": {
        "layout": {
            "pins": [
                [null, null, null, null, null, null, null, null, null, 113, 113],
                [null, null, null, null, null, 16, 14, 17, 110, 110, 113],
                [13, 18, 12, 19, 111, 112, 115, 108, null, 113, 113],
                [11, 20, 10, 21, 109, 114, 116, 106, null, null, null],
                [9, 22, 8, 23, 107, 117, 105, 119, null, 104, 118],
                [5, 26, 4, 27, 7, 24, 6, 25, 120, 102, 121],
                [3, 28, 2, 29, 103, 101, 122, 100, null, 123, 125],
                [1, 30, 0, 31, 99, 124, 98, 127, null, null, null],
                [63, 32, 62, 33, 97, 126, 96, 65, null, 92, 67],
                [61, 34, 60, 35, 95, 64, 94, 93, 66, 90, 69],
                [59, 36, 58, 37, 91, 68, 89, 70, null, 88, 71],
                [57, 38, 56, 39, 87, 72, 86, 73, null, null, null],
                [53, 42, 52, 43, 55, 40, 54, 41, 74, 84, 75],
                [51, 44, 50, 45, 78, 81, 85, 83, 76, 82, 77],
                [46, null, null, null, null, 47, null, null, null, null, 80],
                [49, null, null, null, null, 48, null, null, null, null, 79]
            ]
        }
    },
    "id": 1
}
```

### Method: set_electrode_pins

Activate a subset of electrodes, any electrodes not in the list will be deactivated. The parameters to this method are the pins which should be enabled.

#### Example Request

Activates electrodes 2, 80, and 100. All other electrodes are de-activated.

```json
POST /rpc
{
    "method": "set_electrode_pins",
    "params": [2, 100, 80],
    "jsonrpc": "2.0",
    "id": 1
}
```

#### Example Response

```json
{"jsonrpc": "2.0", "result": null, "id": 0}
```

### Method: move_drop

Perform a move operation on a drop.

**Parameters**:

- *size*: A 2-tuple giving the x and y size of the drop being moved. Example: (2, 2) for a 2x2 square.

- *start*: A 2-tuple giving the starting position of the top-left corner of the drop.

- *direction*: One of, "up", "down", "left", or "right".

**Returns**:

- error: None on success, or string indicating error

- initial_c: Capacitance measured before drop move

- final_c: Capacitance measured after move

- duration: Total time, in seconds to perform the move

- series: Object

    ```
    {
        time: Array of time points
        c: Array of corresponding capacitance values
    }
    ```
