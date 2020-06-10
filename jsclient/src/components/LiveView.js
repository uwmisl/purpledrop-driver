import React from 'react';
import PropTypes from 'prop-types';
import ElectrodeSvg from './ElectrodeSvg';

import './LiveView.css';

class LiveView extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            brushSize: 1,
            hoverPins: [],
        };
        this.decrementBrushSize = this.decrementBrushSize.bind(this);
        this.incrementBrushSize = this.incrementBrushSize.bind(this);
        this.onMouseOver = this.onMouseOver.bind(this);
        this.onMouseOut = this.onMouseOut.bind(this);
        this.onClick = this.onClick.bind(this);
        this.onKeyDown = this.onKeyDown.bind(this);
    }

    componentDidMount() {
        window.addEventListener('keydown', this.onKeyDown);
    }

    componentWillUnmount() {
        window.removeEventListener('keydown', this.onKeyDown);
    }

    decrementBrushSize() {
        this.setState({brushSize: this.state.brushSize - 1});
    }

    incrementBrushSize() {
        this.setState({brushSize: this.state.brushSize + 1});
    }

    getBrushPins(pin) {
        let pins = this.props.layout.getBrushPins(pin, [this.state.brushSize, this.state.brushSize]);
        if(pins.length == 0) {
            pins.push(pin);
        }
        return pins;
    }
    onMouseOver(pin) {
        let pins = this.getBrushPins(pin);
        this.setState({hoverPins: pins});
    }

    onMouseOut() {
        this.setState({hoverPins: []});
    }

    onClick(e, pin) {
        let active_pins = [];
        // control key means leave currently active alone
        // shift key means deactivate instead of activate
        if(e.ctrlKey || e.shiftKey) {
            for(let i=0; i<this.props.electrodeState.length; i++) {
                if(this.props.electrodeState[i]) {
                    active_pins.push(i);
                }
            }
        }
        let brushPins = this.getBrushPins(pin);

        if(e.shiftKey) {
            active_pins = active_pins.filter((x) => !brushPins.includes(x));
        } else {
            for(let i=0; i<brushPins.length; i++) {
                if(!active_pins.includes(brushPins[i])) {
                    active_pins.push(brushPins[i]);
                }
            }
        }
        if(this.props.onSetElectrodes) {
            this.props.onSetElectrodes(active_pins);
        }
    }

    onKeyDown(event) {
        if (event.defaultPrevented) {
            return; // Do nothing if the event was already processed
        }

        switch (event.key) {
        case 'ArrowDown':
            this.move(0, 1);
            break;
        case 'ArrowUp':
            this.move(0, -1);
            break;
        case 'ArrowLeft':
            this.move(-1, 0);
            break;
        case 'ArrowRight':
            this.move(1, 0);
            break;
        case 'Escape':
            this.props.onSetElectrodes([]);
            break;
        default:
            return; // Quit when this doesn't handle the key event.
        }

        // Cancel the default action to avoid it being handled twice
        event.preventDefault();
    }

    move(dx, dy) {
        let activePins = [];
        for(let i=0; i<this.props.electrodeState.length; i++) {
            if(this.props.electrodeState[i]) {
                activePins.push(i);
            }
        }
        let newPins = [];
        for(let i=0; i<activePins.length; i++) {
            let pinLoc = this.props.layout.findPinLocation(activePins[i]);
            let newLoc = [pinLoc[0] + dx, pinLoc[1] + dy];
            let pin = this.props.layout.getPinAtPos(newLoc[0], newLoc[1]);
            if(pin) {
                newPins.push(pin);
            } else {
                // We ran off the regular grid, so we're going to refuse to move
                // TODO: Could be nice to provide some indication that this happened
                // instead of failing silently
                return;
            }
        }
        this.props.onSetElectrodes(newPins);
    }


    render() {
        let classMap = {};
        for(let i=0; i<128; i++) {
            classMap[i] = "electrode";
            if(this.state.hoverPins.includes(i)) {
                classMap[i] += " hover";
            }
            if(this.props.electrodeState[i]) {
                classMap[i] += " active";
            }
        }
        // Adjust width/height based on whether an image is present. 
        // Couldn't find a CSS only solution to keep the SVG/IMG tag the same size when image was there,
        // but also allow the SVG to grow when no image was there, so conditionally changing the style 
        // to work around.
        let wrapperStyles = {};
        if(!this.props.image) {
            wrapperStyles = {width: '100%', height: '100%'}
        }
        return <div style={{width: '100%', display: 'flex', flexDirection: 'column'}}>
            <div className='electrode-grid-wrapper' style={wrapperStyles}>
                <img className='electrode-grid-img' src={this.props.image || ''} />
                <ElectrodeSvg
                    svgId="electrode-grid-svg"
                    layout={this.props.layout}
                    transform={this.props.transform}
                    classMap={classMap}
                    width={this.props.imageWidth}
                    height={this.props.imageHeight}
                    onMouseOver={this.onMouseOver}
                    onMouseOut={this.onMouseOut}
                    onClick={this.onClick}
                />
            </div>
            <div className="toolbar">
                <button className="brushsize" onClick={() => this.decrementBrushSize()}>Smaller</button>
                <input id="brushsize" type="text" disabled value={this.state.brushSize} name="brushsize" />
                <button className="brushsize" onClick={() => this.incrementBrushSize()}>Bigger</button>
            </div>
        </div>;
    }
}

LiveView.defaultProps = {
    imageWidth: 600,
    imageHeight: 400,
    electrodeState: Array(128).fill(false),
};

LiveView.propTypes = {
    layout: PropTypes.object,
    electrodeState: PropTypes.arrayOf(PropTypes.bool),
    onSetElectrodes: PropTypes.func,
    image: PropTypes.string,
    transform: PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.number)),
    imageHeight: PropTypes.number,
    imageWidth: PropTypes.number,
};

export default LiveView;