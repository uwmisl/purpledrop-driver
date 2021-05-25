Board Definitions
=================

Board definition files provide a description of an electrode board used by the 
purpledrop software. They describe the geometry of the electrodes, provide hints
for decisions such as, "which electrodes should be sensed at low capacitance
gain?", and provide transformations needed for using the fiducials for image 
registration. 

File Structure
--------------

A board definition is a JSON file, with the following structure: 

.. code-block:: javascript

  {
    "layout": {
      "grid": <2d array of pin numbers>,
      "grids": <array of grid objects>,
      "peripheral_templates": <array of peripheral template objects>,
      "peripherals": <array of peripheral objects>
    },
    "registration": {
      "fiducials": <array of fiducial objects>,
      "control_points": <array of control point objects>
    },
    "oversized_electrodes": [],
  }

The format of the sub-elements are discussed below. 

Grid Objects
------------

The bulk of the electrodes on most boards are laid out on a grid, where each
electrode is a square of the same size. Grid objects provide a short-hand way
to specify which positions in the grid are occupied, and which pin each is
connected to. PurpleDrop supports single grid, and multiple grids within a 
board. For multiple grids, each grid must also be given an origin location,
and a pitch to specify the size of each electrode. 

A board definition is not required to use real units of length for describing
electrodes. Board definition files with only a single electrode grid may express
all distances in "grid units", i.e. where the pitch of the grid is 1. 

For backwards compatibility, board layout objects may provide either a "grid"
object, with a single grid and no pitch or origin information, or the "grids"
collection, which allows multiple grids, and allows each grid to specify an
origin and pitch. For the "grid" object, the pitch is assumed to be 1 and the
origin is assumed to be (0, 0). 

A old format grid is simply a 2D list of pin numbers: 

.. code-block:: javascript
  
  "grid": [
    [14, 15, 11, 16, 17, 111, 110, 96, 112, 113],
    [8, 9, 10, 19, 18, 109, 108, 95, 115, 117],
    [5, 6, 23, 21, 20, 107, 106, 90, 118, 119], 
    [3, 4, 7, 24, 22, 104, 105, 93, 120, 121], 
    [1, 2, 35, 26, 25, 102, 103, 66, 122, 123], 
    [63, 0, 36, 28, 27, 100, 101, 67, 124, 125], 
    [61, 62, 37, 30, 29, 98, 99, 69, 126, 127], 
    [59, 60, 38, 32, 31, 91, 92, 70, 64, 65], 
    [55, 58, 39, 34, 33, 83, 74, 82, 72, 71], 
    [null, null, null, null, 40, 76, null, null, null, null], 
    [null, null, null, null, 41, 77, null, null, null, null], 
    [null, null, null, null, 54, 78, null, null, null, null], 
    [null, null, null, null, 53, 79, null, null, null, null]
  ]

A new format grid object includes the same array of pins, as well as additional
info alongside:

.. code-block:: javascript

  "grids": [
    {
      "origin": [0.0, 0.0], // [x, y]
      "pitch": [2.5], // in arbitrary units
      "pins": [
        [14, 15, 11, 16, 17, 111, 110, 96, 112, 113],
        [8, 9, 10, 19, 18, 109, 108, 95, 115, 117],
        [5, 6, 23, 21, 20, 107, 106, 90, 118, 119], 
        [3, 4, 7, 24, 22, 104, 105, 93, 120, 121], 
        [1, 2, 35, 26, 25, 102, 103, 66, 122, 123], 
        [63, 0, 36, 28, 27, 100, 101, 67, 124, 125], 
        [61, 62, 37, 30, 29, 98, 99, 69, 126, 127], 
        [59, 60, 38, 32, 31, 91, 92, 70, 64, 65], 
        [55, 58, 39, 34, 33, 83, 74, 82, 72, 71], 
        [null, null, null, null, 40, 76, null, null, null, null], 
        [null, null, null, null, 41, 77, null, null, null, null], 
        [null, null, null, null, 54, 78, null, null, null, null], 
        [null, null, null, null, 53, 79, null, null, null, null]
      ]
    }
  ]

Peripherals and Peripheral Templates
------------------------------------

Peripherals capture all electrodes that are not part of the grid, and allow for
grouping electrodes which are functionally related together. For example, a 
reservoir may have multiple electrodes, and the same reservoir design may be
duplicated multiple times on the board. The peripheral definition can allow
software to find reservoirs by an ID, and create a driver for the reseroir 
which supports multiple instances of a common reservoir type.

Here is an example of a peripheral definition:

.. code-block:: javascript

  "peripherals": [
    {
        "class": "reservoir",
        "type": "reservoirC",
        "id": 1,
        "origin": [-0.5, 0.5],
        "rotation": 180.0,
        "electrodes": [
            { 
              "id": "A",
              "pin": 12,
              "polygon": [[0.5, -0.5], [-0.5, -0.5], [-0.5, -2], [4.0, -2], [4.0, 2], [-0.5, 2], [-0.5, 0.5], [0.5, 0.5]],
              "origin": [1.0, 0.00]
            },
            { 
              "id": "B",
              "pin": 13,
              "polygon": [[-0.5, -0.5], [1.5, -0.5], [1.5, 0.5], [-0.5, 0.5]],
              "origin": [0.0, 0.0]
            }
        ]
    }
  ]

Peripheral templates allow for some simplification of the javascript file when there
are multiple peripherals with the same electrode shapes. In this case, the
electrode polygons can be defined once in a template, and then each peripheral
definition can be shorted to only include the unique attributes of the electrode,
e.g. the pin it is connected to. Peripheral templates are always optional, and 
are mostly useful if you plan to edit your polygons vertices by hand.

The same peripheral above could be created with a template like this:

.. code-block:: javascript

  "peripheral_templates": {
    "reservoirC": {
      "electrodes": [
        {
          "id": "A",
          "polygon": [[0.5, -0.5], [-0.5, -0.5], [-0.5, -2], [4.0, -2], [4.0, 2], [-0.5, 2], [-0.5, 0.5], [0.5, 0.5]],
          "origin": [1.0, 0.00]
        },
        {
          "id": "B",
          "polygon": [[-0.5, -0.5], [1.5, -0.5], [1.5, 0.5], [-0.5, 0.5]],
          "origin": [0.0, 0.0]
        }
      ]
    }
  },
  "peripherals": [
    {
      "class": "reservoir",
      "type": "reservoirC",
      "id": 1,
      "origin": [-0.5, 0.5],
      "rotation": 180.0,
      "electrodes": [
          { "id": "A", "pin": 12 },
          { "id": "B", "pin": 13 }
      ]
    }
  ]

Registration
------------

Electrode boards can include fiducials, which can be used to find the location 
of the electrodes in an image of the board. This is used, for example, by the 
PurpleDrop live view to overlay electrode state information on the video stream
of the board.

PurpleDrop supports `April Tags`_, each of which encodes a single integer. These
labels can be used to automatically identify an electrode board from an image, so
it is recommended to use a unique set of labels for any custom electrode boards.

Here's an example of a registration object: 

.. code-block: javascript

  "registration": {
    "fiducials": [ 
      { 
        "corners": [[612.2684, 60.9334], [665.4835, 62.1736], [663.3616, 114.9999], [611.3482, 115.0000]], 
        "label": 4
      }, 
      {
        "corners": [[373.2462, 276.8540], [424.0156, 277.2910], [422.5534, 329.2864], [372.2937, 327.5831]],
        "label": 5
      }, 
      {
        "corners": [[854.2771, 284.7816], [907.1122, 285.0718], [906.7958, 337.4262], [852.5702, 335.6844]],
        "label": 6
      }
    ],
    "control_points": [
        {"grid": [0, 0], "image": [485.2965, 175.9639]},
        {"grid": [0, 8], "image": [480.9802, 411.5146]},
        {"grid": [9, 8], "image": [749.8287, 418.2975]},
        {"grid": [9, 0], "image": [755.3783, 178.4304]}
    ]
  }

The "fiducials" lists the corner locations of each tag present on the board.
It is important that the order of the corners matches the order returned by the
april tag detector software.

The "control_points" field lists a set of location pairs tieing points on the
electrode board coordinate system to pixel locations in the same image as the 
fiducials were measured. A minimum of four points must be provided, but more 
may be provided and a best-fit solution will be found. 

The `pdcam` application provides a utility for generating these control points
by clicking on locations in a reference image.

Oversized Electrodes
--------------------

The "oversized_electrodes" field provides a list of pin numbers that will have
their capacitance sampled using low gain settings during the global capacitance
scan. This can be used for large electrodes, such as on reservoirs, whose 
capacitance can be large enough to saturate the measurement in the high gain
setting.

.. _April Tags: https://github.com/AprilRobotics/apriltag