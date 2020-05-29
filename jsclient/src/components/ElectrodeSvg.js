import React from 'react';
import PropTypes from 'prop-types';
import Offset from 'polygon-offset';
import memoize from 'memoize-one';

function transform(points, M) {
  // Map them by transform
  return points.map((p) => {
    let x = M[0][0] * p[0] + M[0][1] * p[1] + M[0][2];
    let y = M[1][0] * p[0] + M[1][1] * p[1] + M[1][2];
    let z = M[2][0] * p[0] + M[2][1] * p[1] + M[2][2];
    return [x / z, y / z];
  });
}

// Creates a transform to fill the layout within the SVG window
// allowing for a certain percent MARGIN around it
function default_transform(layout, svg_width, svg_height) {
  const MARGIN = 0.1;
  const FILL_FACTOR = 1 - 2*MARGIN;
  let extent = layout.extent();
  let board_width = extent.maxX - extent.minX;
  let board_height = extent.maxY - extent.minY;

  //let scale = Math.min(svg_width, svg_height) / Math.max(board_width, board_height) * FILL_FACTOR;
  let scale = Math.min(svg_width/board_width, svg_height/board_height) * FILL_FACTOR;
  let dx = -extent.minX * scale + (svg_width - board_width * scale) / 2;
  let dy = -extent.minY * scale + (svg_height - board_height * scale) / 2;
  let transform = [
    [scale, 0.0, dx],
    [0.0, scale, dy],
    [0.0, 0.0, 1.0],
  ];
  return transform;
}

class ElectrodeSvg extends React.Component {
  constructor(props) {
    super(props);
    this.base_polygons = memoize((layout) => {
      return layout.electrode_polygons().map((electrode) => {
  
        const shrinkOffset = 0.05;
        let points = electrode.points;
        let pin = electrode.pin;
  
        if(electrode.pin !== null) {
          // Offset the polygons inward
          let offset = new Offset();
          points = offset.data(points).padding(shrinkOffset)[0];
        }
  
        return {pin: pin, points: points};
      });
    });
  }

  

  render() {
    const layout = this.props.layout;
    const M = this.props.transform || default_transform(layout, this.props.width, this.props.height);

    let polygons = [];
    this.base_polygons(layout).forEach((electrode) => {
      let pin = electrode.pin;
      let points = electrode.points;
      
      if(pin === null) {
        return;
      }
      
      // Map them by transform to new coordinate system
      points = transform(points, M);

      let poly = <polygon
        onMouseOut={this.props.onMouseOut ? () => this.props.onMouseOut(pin) : () => {}}
        onMouseOver={this.props.onMouseOver ? () => this.props.onMouseOver(pin) : () => {}}
        onClick={this.props.onClick ? (e) => this.props.onClick(e, pin) : () => {}}
        points={points.map((p) => `${p[0]}, ${p[1]}`).join(' ')}
        style={this.props.styleMap[pin] || {}}
        className={this.props.classMap[pin] || ""}
        key={pin}
        data-pin={pin}
      />;
      polygons.push(poly);
    }, this);
  
    
    return <div>
      <svg id={this.props.svgId} width={this.props.width} height={this.props.height} viewBox={`0 0 ${this.props.width} ${this.props.height}`}>
        {polygons}
      </svg>
    </div>;
  }
}

ElectrodeSvg.propTypes = {
  transform: PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.number)),
  layout: PropTypes.object,
  width: PropTypes.number,
  height: PropTypes.number,
  onMouseOut: PropTypes.func,
  onMouseOver: PropTypes.func,
  onClick: PropTypes.func,
  styleMap: PropTypes.object,
  classMap: PropTypes.object,
};

ElectrodeSvg.defaultProps = {
  styleMap: {},
  classMap: {},
};

export default ElectrodeSvg;
