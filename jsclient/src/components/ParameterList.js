import React from 'react';
import PropTypes from 'prop-types';
import Parameter from './Parameter';
import './ParameterList.css';

class ParameterList extends React.Component {
  constructor(props) {
    super(props);
    this.onSaveToFlash = this.onSaveToFlash.bind(this);
    this.onRefresh = this.onRefresh.bind(this);
    this.state = {alertMessage: "", error: false};
  }

  onSaveToFlash() {
    this.setState({alertMessage: "Saving...", error: false});
    this.props.onPersist().then(
      () => { this.setState({alertMessage: "Saved"}); },
      (e) => { this.setState({error: true, alertMessage: e.message}); },
    );
  }

  onRefresh() {
    this.setState({alertMessage: "Reading parmeters...", error: false});
    this.props.onRefresh().then(
      () => { this.setState({alertMessage: "Refresh complete"}); },
      (e) => { this.setState({error: true, alertMessage: e.message}); },
    );
  }

  render() {
    let params = [];
    this.props.parameterList.forEach((p) => {
      params.push(
        <Parameter 
          key={p.id}
          id={p.id}
          name={p.name}
          description={p.description}
          type={p.type}
          dirty={this.props.parameterDirtyMap[p.id]}
          value={this.props.parameters[p.id]}
          onSave={this.props.onSave}
          onChange={this.props.onChange}
        />,
      );
    });
    return <div className="parameter-list">
      <button className="refreshButton" onClick={this.onRefresh}>Refresh from Device</button>
      <button className="saveButton" onClick={this.onSaveToFlash}>Save to Flash</button>
      <div className="parameterAlert"><span className={this.state.error ? "error" : ""}>{this.state.alertMessage}</span></div>
      {params}
    </div>;
  }
}

ParameterList.propTypes = {
  parameterList: PropTypes.arrayOf(PropTypes.exact({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    description: PropTypes.string,
    type: PropTypes.oneOf(["float", "int", "bool"]),
  })),
  parameters: PropTypes.arrayOf(PropTypes.number),
  parameterDirtyMap: PropTypes.object,
  onRefresh: PropTypes.func,
  onSave: PropTypes.func,
  onChange: PropTypes.func,
  onPersist: PropTypes.func,
};

export default ParameterList;