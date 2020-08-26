import json
import os
import pkg_resources
from typing import Any, Dict


class Layout(object):
    def __init__(self, layout_def: Dict[str, Any]):
        self.layout = layout_def

    def grid_location_to_pin(self, x, y):
        """Return the pin number at given grid location, or None if no pin is 
        defined there.
        """
        if y < 0 or y >= len(self.layout['grid']):
            return None
        row = self.layout['grid'][y]
        if x < 0 or x >= len(row):
            return None
        return self.layout['grid'][y][x]

    def as_dict(self) -> dict:
        """Return a serializable dict version of the board definition
        """
        return self.layout

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
