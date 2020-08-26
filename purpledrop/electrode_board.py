import json
import os
import pkg_resources
from typing import Any, Dict, List, Optional


def load_peripheral(pdata, templates=None):

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
    
class Layout(object):
    def __init__(self, layout_def: Dict[str, Any]):
        self.peripherals = None
        self.grid = []
        # Replace -1 with None
        for row in layout_def['grid']:
            new_row: List[Optional[int]] = []
            
            for pin in row:
                if pin == -1 or pin is None:
                    new_row.append(None)
                else:
                    new_row.append(int(pin))

            self.grid.append(new_row)    

        if 'peripherals' in layout_def:
            self.peripherals = [load_peripheral(p, layout_def.get('peripheral_templates', None)) for p in layout_def['peripherals']]

    def grid_location_to_pin(self, x, y):
        """Return the pin number at given grid location, or None if no pin is 
        defined there.
        """
        if y < 0 or y >= len(self.grid):
            return None
        row = self.grid[y]
        if x < 0 or x >= len(row):
            return None
        return self.grid[y][x]

    def as_dict(self) -> dict:
        """Return a serializable dict version of the board definition
        """
        return {
            "grid": self.grid,
            "peripherals": self.peripherals
        }

class Board(object):
    def __init__(self, board_def: Dict[str, Any]):
        self.layout = Layout(board_def['layout'])
        self.oversized_electrodes = board_def.get('oversized_electrodes', [])

    @staticmethod
    def load_from_file(filepath):
        with open(filepath, 'r') as f:
            data = json.loads(f.read())
            return Board(data)

    def load_from_string(data):
        return Board(json.loads(data))

    def as_dict(self) -> dict:
        return {
            'layout': self.layout.as_dict(),
            'oversized_electrodes': self.oversized_electrodes,
        }

def list_boards():
    """Return a list of board definitions available
    """
    raise RuntimeError("Not implemented")

def load_board(name):
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
