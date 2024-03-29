import json
import numpy as np
import os
import pkg_resources
import re
from typing import Any, AnyStr, Dict, List, Optional, Tuple


def load_peripheral(pdata, templates=None):
    """Load a peripheral from a dict

    This loads a peripheral with support for templates, as used in the board
    definition file format

    Args:
        pdata: A dict containing the peripheral definition
        templates: A dict mapping types to template definitions
    """
    if not 'type' in pdata:
        raise ValueError("Peripheral definition requires a type field")

    template = None
    if templates is not None and pdata['type'] in templates:
        template = templates[pdata['type']]

    periph = pdata

    # Override electrodes with fields from template
    def map_electrode(e):
        eid = e['id']
        if template is None:
            return e
        e_template = next((x for x in template['electrodes'] if x['id'] == eid), None)
        if e_template is None:
            return e
        # Merge dicts, with values in e taking priority in case of duplicate keys
        return {**e_template, **e}

    periph['electrodes'] = [map_electrode(e) for e in periph['electrodes']]

    return periph

class Fiducial(object):
    """Represents a fiducial location
    """
    def __init__(self, corners: List[List[int]], label: str=""):
        self.corners = corners
        self.label = label

    @staticmethod
    def from_dict(data):
        return Fiducial(**data)

    def to_dict(self):
        return {
            'corners': self.corners,
            'label': self.label
        }

class ControlPoint(object):
    """Represents a control point in an image

    A control point is a pair of corresponding points -- one in image coordinates
    and the other in grid coordinates -- used to calibrate the position of
    the electrode grid relative to fiducials.
    """
    def __init__(self, grid_coord: Tuple[float, float], image_coord: Tuple[float, float]):
        self.grid = grid_coord
        self.image = image_coord

    def from_dict(data):
        if not 'grid' in data:
            raise ValueError(f'A control point must have a `grid` and `image` attribute: {data}')
        if not 'image' in data:
            raise ValueError(f'A control point must have a `grid` and `image` attribute: {data}')

        return ControlPoint(data['grid'], data['image'])

class Registration(object):
    """A registration is a collection of fiducials and control points which
    together define relationship between the electrode locations and fiducials
    """
    def __init__(self, data: dict):
        if not 'fiducials' in data:
            raise ValueError(f'A Registration requires a fiducials attribute, not found in: {data}')
        if not 'control_points' in data:
            raise ValueError(f'A Registration requires a control points attribute, not found in: {data}')
        if not isinstance(data['fiducials'], list):
            raise ValueError(f'A Registration `fiducial` attribute must be a list: {data}')
        if not isinstance(data['control_points'], list):
            raise ValueError(f'a Registration `control_points` attribute must be a list: {data}')

        self.fiducials = [Fiducial.from_dict(f) for f in data['fiducials']]
        self.control_points = [ControlPoint.from_dict(cp) for cp in data['control_points']]

class Layout(object):
    """Represents the 'layout' property of a baord definition

    A layout defines the placement and pin mapping for the electrodes on the
    board.
    """
    def __init__(self, layout_def: Dict[str, Any]):
        self.peripherals = None
        self.grids = []

        def intify_pins(grid_pins):
            result = []
            for row in grid_pins:
                new_row: List[Optional[int]] = []
                for pin in row:
                    if pin == -1 or pin is None:
                        new_row.append(None)
                    else:
                        new_row.append(int(pin))
                result.append(new_row)
            return result

        # Old format files use 'grid' to define a single grid
        # New format uses an array of objects, under the key 'grids'
        if 'grid' in layout_def:
            self.grids.append({
                'origin': [0.0, 0.0],
                'pitch': 1.0,
                'pins': intify_pins(layout_def['grid'])
            })
        elif 'grids' in layout_def:
            for g in layout_def['grids']:
                self.grids.append({
                    'origin': g['origin'],
                    'pitch': g['pitch'],
                    'pins': intify_pins(g['pins']),
                })

        if 'peripherals' in layout_def:
            self.peripherals = [load_peripheral(p, layout_def.get('peripheral_templates', None)) for p in layout_def['peripherals']]

    def grid_location_to_pin(self, x: int, y: int, grid_number:int =0):
        """Return the pin number at given grid location, or None if no pin is
        defined there.
        """
        if grid_number < len(self.grids):
            grid = self.grids[grid_number]['pins']
        else:
            grid = [[]] # Empty grid
        if y < 0 or y >= len(grid):
            return None
        row = grid[y]
        if x < 0 or x >= len(row):
            return None
        return grid[y][x]

    def pin_to_grid_location(self, pin: int) -> Optional[Tuple[Tuple[int, int], int]]:
        """Return the grid location of a given pin number
        """
        for g, grid in enumerate(self.grids):
            for y, row in enumerate(grid['pins']):
                for x, p in enumerate(row):
                    if p == pin:
                        return ((x, y), g)
        return None

    def pin_polygon(self, pin: int) -> Optional[List[Tuple[int, int]]]:
        """Get the polygon defining a pin in board coordinates
        """
        # Try to find the pin in a grid
        grid_info = self.pin_to_grid_location(pin)
        if grid_info is not None:
            loc, grid_idx = grid_info
            square = np.array([[0., 0.], [0., 1.], [1., 1.], [1., 0.]])
            grid = self.grids[grid_idx]
            polygon = (square + loc) * grid['pitch'] + grid['origin']
            return polygon.tolist()
        # Try to find the pin in a peripheral
        if self.peripherals is None:
            return None
        for periph in self.peripherals:
            for el in periph['electrodes']:
                if el['pin'] == pin:
                    polygon = np.array(el['polygon'])
                    rotation = np.deg2rad(periph.get('rotation', 0.0))
                    R = np.array([[np.cos(rotation), -np.sin(rotation)], [np.sin(rotation), np.cos(rotation)]])
                    polygon = np.dot(R, polygon.T).T
                    return (polygon + periph['origin']).tolist()
        return None

    def as_dict(self) -> dict:
        """Return a serializable dict version of the board definition
        """
        return {
            "grids": self.grids,
            "peripherals": self.peripherals
        }

class Board(object):
    """Represents the top-level object in an electrode board definition file
    """
    def __init__(self, board_def: Dict[str, Any]):
        self.registration: Optional[Registration] = None
        if not 'layout' in board_def:
            raise RuntimeError("Board definition file must contain a 'layout' object")
        self.layout = Layout(board_def['layout'])
        self.oversized_electrodes = board_def.get('oversized_electrodes', [])
        if 'registration' in board_def:
            self.registration = Registration(board_def['registration'])

    @staticmethod
    def load_from_file(filepath):
        """Create a Board from a board definition file
        """
        with open(filepath, 'r') as f:
            data = json.loads(f.read())
            return Board(data)

    @staticmethod
    def load_from_string(data: AnyStr) -> 'Board':
        """Create a board from a JSON string in memory
        """
        return Board(json.loads(data))

    def as_dict(self) -> dict:
        """Return a serializable dict representation of the board
        """
        return {
            'layout': self.layout.as_dict(),
            'oversized_electrodes': self.oversized_electrodes,
        }

def list_boards():
    """Find all available board definitions.

    Uses same search rules as load_board; see :func:`load_board`.

    Returns:
        A list of board names, which can be passed to `load_board`
    """
    config_dir = os.path.expanduser("~/.config/purpledrop/boards")
    package_files = pkg_resources.resource_listdir('purpledrop', 'boards')
    if os.path.isdir(config_dir):
        config_files = os.listdir(config_dir)
    else:
        config_files = []

    board_names = []
    def add_files(files):
        for f in files:
            print(f"Checking {f}")
            match = re.match(r'(.+).json', os.path.basename(f))
            if match:
                board_names.append(match.group(1))

    # Config files take priority, if there are any duplicates
    add_files(package_files)
    add_files(config_files)

    return board_names

def load_board(name) -> Optional[Board]:
    """Load a board definition by name or path

    Attempt to load a board definition from the name, using the following
    priorities (the first to succeed is returned):

    1. Load as a full path
    2. Load from ~/.config/purpledrop/boards/{name}.json
    3. Load from package resources (`purpledrop/boards` in repo)
    """

    if os.path.isfile(name):
        return Board.load_from_file(name)

    home_path = os.path.expanduser(f"~/.config/purpledrop/boards/{name}.json")
    if os.path.isfile(home_path):
        return Board.load_from_file(home_path)

    try:
        resource_data = pkg_resources.resource_string('purpledrop', f"boards/{name}.json")
        return Board.load_from_string(resource_data)
    except FileNotFoundError:
        pass

    return None
