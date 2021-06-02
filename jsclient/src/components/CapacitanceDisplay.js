import React from 'react';
import { SizeMe } from 'react-sizeme';
import PropTypes from 'prop-types';
import ElectrodeSvg from './ElectrodeSvg';
import colormap from 'colormap';
import Slider from '@material-ui/core/Slider';

import './CapacitanceDisplay.css';

function getDisplaySize(size, electrodeAspectRatio) {
  const containerAspect = size.width / size.height;
  let displayWidth = size.width;
  let displayHeight = size.height;
  if (containerAspect > electrodeAspectRatio) {
      displayWidth = electrodeAspectRatio * displayHeight;
  } else {
      displayHeight = displayWidth / electrodeAspectRatio;
  }
  if(isNaN(displayHeight)) {
    displayHeight = 10;
  }
  return {width: displayWidth, height: displayHeight};
}

const DEFAULT_COLOR_MAX = 10.0;

class CapacitanceDisplay extends React.Component {
  constructor(props) {
    super(props);
    this.onMouseOver = this.onMouseOver.bind(this);
    this.onMouseOut = this.onMouseOut.bind(this);
    this.onColorMaxChange = this.onColorMaxChange.bind(this);
    this.state = {
      mouseOverPin: null,
      colorMax: DEFAULT_COLOR_MAX,
    };
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

  onColorMaxChange(event, newValue) {
    this.setState({colorMax: newValue});
  }

  render() {
    let layout = this.props.layout;
    let extent = layout.extent();
    let normMax = this.state.colorMax;
    let styleMap = {};
    for(var i=0; i<this.props.capacitance.length; i++) {
      let cap = this.props.capacitance[i];
      let A = layout.getPinArea(i);
      if(cap.capacitance > normMax / 50) {
        let colorIdx = Math.min(this.colormap.length-1, Math.floor(cap.capacitance * this.colormap.length / normMax / A));
        styleMap[i] = {fill: this.colormap[colorIdx]};
      }
    }

    let electrodeAspectRatio = (extent.maxX - extent.minX) / (extent.maxY - extent.minY);
    let message = "Mouse-over for electrode capacitance";
    if(this.state.mouseOverPin) {
      let capacitance = this.props.capacitance[this.state.mouseOverPin];
      let measurement = "NA";
      let raw = '';
      if (capacitance) {
        measurement = Math.round(capacitance.capacitance*100)/100;
        raw = capacitance.raw;
      }
      message = `Pin ${this.state.mouseOverPin}: ${measurement} pF (${raw} counts)`;
    }

    const colorMaxDivStyles = {
      margin: '10px',
      display: 'flex',
    };

    const flexContainerStyle = {
      display: "flex",
      flexDirection: "column",
      alignContent: 'center',
      height: "100%",
    };

    const contentBoxStyle = {
      flexGrow: 1,
    };

    return <div id='capacitance-flex-container' style={flexContainerStyle}>
      <div id='capacitance-electrode-box' style={contentBoxStyle}>
        <SizeMe monitorHeight>
          {({size}) => {
            const {width, height} = getDisplaySize(size, electrodeAspectRatio);
            return <div style={{ position: 'relative', height: '100%' }}>
              <div style={{position: 'absolute', width: width, height: height }}>
                <ElectrodeSvg
                  svgId="capacitance-display-svg"
                  layout={this.props.layout}
                  width={width}
                  height={height}
                  imageHeight={height}
                  imageWidth={width}
                  styleMap={styleMap}
                  onMouseOver={this.onMouseOver}
                  onMouseOut={this.onMouseOut}
                />
              </div>
            </div>;
          }}
        </SizeMe>
      </div>
      <div id="color-max-slider" style={colorMaxDivStyles}>
        
        <div style={{width:"100%"}}>
          <Slider defaultValue={DEFAULT_COLOR_MAX} onChange={this.onColorMaxChange} />
        </div>
        <div style={{marginLeft: '10px'}}>
          Color max: {this.state.colorMax}pF
        </div>

      </div>
      <div id='capacitance-message-box' style={{textAlign: 'center'}}>
          <span>{message}</span>
      </div>
    </div>;
  }
}

CapacitanceDisplay.propTypes = {
  capacitance: PropTypes.arrayOf(PropTypes.object).isRequired,
  layout: PropTypes.object,
  height: PropTypes.number,
  width: PropTypes.number,
  colorMax: PropTypes.number,
};

export default CapacitanceDisplay;