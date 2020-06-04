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

