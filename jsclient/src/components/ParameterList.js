import React from 'react';
import PropTypes from 'prop-types';
import Parameter from './Parameter';
import './ParameterList.css';

class ParameterList extends React.Component {
  constructor(props) {
    super(props);
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
      <button className="refreshButton" onClick={this.props.onRefresh}>Refresh from Device</button>
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
};

export default ParameterList;