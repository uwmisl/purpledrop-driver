function rotate(center, points, angle) {
  angle = angle * Math.PI / 180.0;
  let s = Math.sin(angle);
  let c = Math.cos(angle);
  return points.map((p) => {
    let x = p[0] - center[0];
    let y = p[1] - center[1];
    return [c*x - s*y + center[0],
            s*x + c*y + center[1]];
  });  
}

class Layout {
  constructor(layout) {
    this.grid = layout.grid;
    this.extra = layout.extra;
    this.memoized_polygons = null;
  }

  electrode_polygons() {
    if(!this.memoized_polygons) {
      let polygons = [];
      this.grid.forEach((row, y) => {
        row.forEach((pin, x) => {
          if(pin === null) {
            return;
          }
          let position = [x, y];
          // Points in grid coordinates, where each electrode's top-left corner
          // is at integer coordinate (n, m)
          let points = [
            [position[0], position[1]],
            [position[0] + 1, position[1]],
            [position[0] + 1, position[1] + 1],
            [position[0], position[1] + 1],
            [position[0], position[1]],
          ];

          polygons.push({pin: pin, points: points});
        });
      });

      this.extra.forEach((group) => {
        let group_origin = group.origin;
        group.electrodes.forEach((electrode) => {
          let electrode_origin = [group_origin[0] + electrode.origin[0], group_origin[1] + electrode.origin[1]];
          let points = electrode.polygon.map((p) => [p[0] + electrode_origin[0], p[1] + electrode_origin[1]]);
          points.push(points[0]); // Close the polygon for offset calculation
          
          let pin = electrode.pin;

          if(group.rotation) {
            points = rotate(group_origin, points, group.rotation);
          }
          
          polygons.push({pin: pin, points: points});
        });
      });
      this.memoized_polygons = polygons;
    }
    return this.memoized_polygons;
  }

  extent() {
    let maxX = Number.NEGATIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;

    this.electrode_polygons().forEach((poly) => {
      poly.points.forEach((p) => {
        maxX = Math.max(p[0], maxX);
        maxY = Math.max(p[1], maxY);
        minX = Math.min(p[0], minX);
        minY = Math.min(p[1], minY);
      });
    });
    return {minX: minX, maxX: maxX, minY: minY, maxY: maxY};
  }

  getPinAtPos(x, y) {
    if(y >= this.grid.length) {
      return null;
    }
    let row = this.grid[y];
    if(x >= row.length) {
      return null;
    }
    return row[x];
  }

  findPinLocation(pin) {
    for(let y=0; y<this.grid.length; y++) {
      let row = this.grid[y];
      for(let x=0; x<row.length; x++) {
        if(pin == row[x]) {
          return [x, y];
        }
      }
    }
    return null;
  }

  getBrushPins(pin, size) {
    if (typeof size === 'undefined') {
      size = (1, 1);
    }
    let origin = this.findPinLocation(pin);
    if(origin === null) {
      return [];
    }
    let result = [];
    for(let x = 0; x<size[0]; x++) {
      for(let y = 0; y<size[1]; y++) {
        result.push(this.getPinAtPos(x + origin[0], y + origin[1]));
      }
    }
    return result;
  }
}

export default Layout;