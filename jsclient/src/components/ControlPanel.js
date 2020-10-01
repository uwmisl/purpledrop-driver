import React from 'react';
import PropTypes from 'prop-types';
import Switch from 'react-switch';

//import './ControlPanel.css';

class ControlPanel extends React.Component {
  constructor(props) {
    super(props);

    this.onHvEnabledChange = this.onHvEnabledChange.bind(this);
  }

  onHvEnabledChange(value) {
    this.props.onHvEnabledChange(value);
  }

  render() {
    return (
      <div>
        <div style={{display:"flex", alignItems: "center"}}>
          <label style={{margin: '10px'}}>
            High Voltage On:
          </label>
          <Switch onColor="#f00" onChange={this.onHvEnabledChange} checked={this.props.hvEnabled} />
        </div>
        <button id="calibrateCapButton" onClick={this.props.onCalibrateCapacitance}>Re-calibrate capacitance offset</button>
        
      </div>
    );
  }
}

ControlPanel.propTypes = {
  hvEnabled: PropTypes.bool,
  onHvEnabledChange: PropTypes.func,
  onCalibrateCapacitance: PropTypes.func,
};

export default ControlPanel;