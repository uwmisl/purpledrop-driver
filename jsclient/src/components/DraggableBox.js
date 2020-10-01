import React from 'react';
import PropTypes from 'prop-types';

let DraggableBox = (props) => {
  const wrapperStyles = {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    border: '1px solid #555555',
  };

  const titleStyles = {
    backgroundColor: 'rgba(120,80,200,0.7)',
    width: '100%',
    textAlign: 'center',
  };

  const contentsStyles = {
    flexGrow: 1,
    overflow: 'hidden',
  };

  return <div style={wrapperStyles} key={props.title}>
    <div style={titleStyles} className='drag-handle'>
      <span  >{props.title}</span>
    </div>
    <div style={contentsStyles}>
      {props.children}
    </div>
  </div>;
};

DraggableBox.propTypes = {
  title: PropTypes.string,
  children: PropTypes.arrayOf(PropTypes.element),
};

export default DraggableBox;