import React from 'react';
import PropTypes from 'prop-types';
import NumericInput from 'react-numeric-input';

class Parameter extends React.Component {
  constructor(props) { 
    super(props);

    this.onSave = this.onSave.bind(this);
    this.updateLocalValue = this.updateLocalValue.bind(this);
  }

  onSave() {
    console.log("Saving param ", this.props.id, " = ", this.props.value);
    if(this.props.onSave) {
      this.props.onSave(this.props.id);
    }
  }

  updateLocalValue(value) {
    if(this.props.onChange) {
      this.props.onChange(this.props.id, value);
    }
  }

  render() {
    let input;
    if(this.props.type == "bool") {
      input = <input 
        type="checkbox" 
        checked={this.props.value != 0}
        onChange={(e) => {this.updateLocalValue(e.target.checked ? 1 : 0);}}
      />;
    } else {
      input = <NumericInput value={this.props.value} onChange={(value) => {this.updateLocalValue(value);}} />;
    }

    return <form className={this.props.dirty ? "dirty" : ""} action="#" onSubmit={this.onSave}>
      <label>
        {this.props.name} {input}
      </label>
      <button type="submit">Save</button>
    </form>;
  }
}

Parameter.propTypes = {
  id: PropTypes.number,
  name: PropTypes.string,
  value: PropTypes.number,
  type: PropTypes.oneOf(["int", "float", "bool"]),
  dirty: PropTypes.bool,
  onSave: PropTypes.func,
  onChange: PropTypes.func,
};

export default Parameter;