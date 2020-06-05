import React from 'react';
import PropTypes from 'prop-types';

class Stats extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    return <div className="stats-container">
      <div className="stats"><span>Voltage: {Math.round(this.props.voltage*10) / 10}V</span></div>
      <div className="stats"><span>Temp0: {Math.round(this.props.temperatures[0]*10) / 10}&deg;C</span></div>
      <div className="stats"><span>Temp1: {Math.round(this.props.temperatures[1]*10) / 10}&deg;C</span></div>
      <div className="stats"><span>Temp2: {Math.round(this.props.temperatures[2]*10) / 10}&deg;C</span></div>
      <div className="stats"><span>Temp3: {Math.round(this.props.temperatures[3]*10) / 10}&deg;C</span></div>
    </div>;
  }
}

Stats.defaultProps = {
  voltage: 120.0,
  temperatures: [0.0, 0.0, 0.0, 0.0],
};

Stats.propTypes = {
  voltage: PropTypes.number,
  temperatures: PropTypes.arrayOf(PropTypes.number),
};

export default Stats;