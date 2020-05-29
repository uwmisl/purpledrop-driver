import React from 'react';

class Stats extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    return <div className="stats-container">
      <div className="stats"><span>Voltage: {this.props.voltage}V</span></div>
      <div className="stats"><span>Temp0: {this.props.temperatures[0]}&deg;C</span></div>
      <div className="stats"><span>Temp0: {this.props.temperatures[1]}&deg;C</span></div>
      <div className="stats"><span>Temp0: {this.props.temperatures[2]}&deg;C</span></div>
      <div className="stats"><span>Temp0: {this.props.temperatures[3]}&deg;C</span></div>
      
    </div>;
  }
}

Stats.defaultProps = {
  voltage: 120.0,
  temperatures: [21.0, 21.2, 20.9, 20.7],
};

export default Stats;