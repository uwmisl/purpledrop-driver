import React from 'react';
import PropTypes from 'prop-types';
import ElectrodeSvg from './ElectrodeSvg';
import colormap from 'colormap';

import './CapacitanceDisplay.css';

class CapacitanceDisplay extends React.Component {
  constructor(props) {
    super(props);
    this.onMouseOver = this.onMouseOver.bind(this);
    this.onMouseOut = this.onMouseOut.bind(this);
    this.state = {mouseOverPin: null};
    this.colormap = colormap({
        colormap: 'jet',
        nshades: 16,
        format: 'hex',
        alpha: 1.0,
    });
  }

  onMouseOver(pin) {
    this.setState({mouseOverPin: pin});
  }

  onMouseOut() {
    this.setState({mouseOverPin: null});
  }

  render() {
    const NormMax = 1500;
    let styleMap = {};
    for(var i=0; i<this.props.capacitance.length; i++) {
      let cap = this.props.capacitance[i];
      if(cap.dropPresent && cap.capacitance > 75) {
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
    let message = "";
    if(this.state.mouseOverPin) {
      let capacitance = this.props.capacitance[this.state.mouseOverPin];
      let measurement = "NA";
      if (capacitance) {
        measurement = capacitance.capacitance;
      }
      message = `Pin ${this.state.mouseOverPin}: ${measurement}`;
    }
    return <div style={{display: "flex", flexDirection: "column", alignContent: 'center', width: "100%"}}>
      <h3 style={{textAlign:'center'}}>Capacitance</h3>
      <ElectrodeSvg 
        svgId="capacitance-display-svg"
        layout={this.props.layout}
        width={width}
        height={height}
        styleMap={styleMap}
        onMouseOver={this.onMouseOver}
        onMouseOut={this.onMouseOut}
      />
      <div style={{textAlign: 'center'}}><span>{message}</span></div>
    </div>;
  }
}

CapacitanceDisplay.propTypes = {
  capacitance: PropTypes.arrayOf(PropTypes.exact({capacitance: PropTypes.number, dropPresent: PropTypes.bool})).isRequired,
  layout: PropTypes.object,
  height: PropTypes.number,
  width: PropTypes.number,
};

export default CapacitanceDisplay;