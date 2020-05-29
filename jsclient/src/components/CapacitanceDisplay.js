import React from 'react';
import PropTypes from 'prop-types';
import ElectrodeSvg from './ElectrodeSvg';
import colormap from 'colormap';

class CapacitanceDisplay extends React.Component {
  constructor(props) {
    super(props);
    this.onMouseOver = this.onMouseOver.bind(this);
    this.onMouseOut = this.onMouseOut.bind(this);
    this.state = {message: "Temp"};
    this.colormap = colormap({
        colormap: 'jet',
        nshades: 10,
        format: 'hex',
        alpha: 1.0,
    });
  }

  onMouseOver(pin) {
    let capacitance = this.props.capacitance[pin];
    let measurement = "NA";
    if (capacitance) {
      measurement = capacitance.capacitance;
    }
    this.setState({message: `Pin ${pin}: ${measurement}`});
  }
  onMouseOut() {
    this.setState({message: ""});
  }

  render() {
    const NormMax = 3000;
    let styleMap = {};
    for(var i=0; i<this.props.capacitance.length; i++) {
      let cap = this.props.capacitance[i];
      if(cap.drop_present) {
        let colorIdx = Math.min(this.colormap.length-1, Math.floor(cap.capacitance * this.colormap.length / NormMax));
        styleMap[i] = {fill: this.colormap[colorIdx]};
      }
    }

    let layout = this.props.layout;
    let extent = layout.extent();
    let aspect_ratio = (extent.maxX - extent.minX) / (extent.maxY - extent.minY);
    let height = this.props.height;
    let width = this.props.width;
    if(aspect_ratio > width/height) {
      height = width / aspect_ratio;
    } else {
      width = height * aspect_ratio;
    }
    return <div>
      <ElectrodeSvg 
        layout={this.props.layout}
        width={width}
        height={height}
        styleMap={styleMap}
        onMouseOver={this.onMouseOver}
        onMouseOut={this.onMouseOut}
      />
      <br />
      <span>{this.state.message}</span>
    </div>;
  }
}

CapacitanceDisplay.propTypes = {
  capacitance: PropTypes.arrayOf(PropTypes.exact({capacitance: PropTypes.number, drop_present: PropTypes.bool})).isRequired,
  layout: PropTypes.object,
  height: PropTypes.number,
  width: PropTypes.number,
};

export default CapacitanceDisplay;