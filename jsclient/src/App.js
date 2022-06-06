
import React from 'react';
import {
  BrowserRouter as Router,
  Switch,
  Route,
} from 'react-router-dom';
import ReactTooltip from 'react-tooltip';
import Modal from 'react-modal';
import GridLayout, {WidthProvider} from 'react-grid-layout';
import { Info, ReportProblem } from '@material-ui/icons';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

import PdRpc from 'rpc';
import PdSocket from 'pdsocket';
import Layout from './utils/layout';

import CapacitanceDisplay from './components/CapacitanceDisplay';
import ControlPanel from './components/ControlPanel';
import DraggableBox from './components/DraggableBox';
import LiveView from './components/LiveView';
import ParameterList from './components/ParameterList';
import Preloader from './components/Preloader';
import Stats from './components/Stats';
import Usage from './components/Usage';

import mislLogo from './images/misl-logo.svg';
import uwLogo from './images/uw-logo.png';

Modal.setAppElement('#root');

// Generally, the UI makes no assumptions about what parameters exist, but in
// order to provide an easy power button via a parameter this exception is made.
const HV_ENABLE_PARAM_ID = 10;

// Create a wrapper for the app with setState and setStatePassive
// methods to ease up on the render calls. The event stream sends
// a LOT of events (e.g. 100Hz, or 500Hz). We want to display some
// of these, forcing that many react renderings can be pretty brutal.
function setStateWrapper(component, minRenderPeriod_ms) {
  let timeout = null;
  let accumulatedState = {};

  return {
    setState(state) {
      Object.assign(accumulatedState, state);
      component.setState(accumulatedState);
      accumulatedState = {};
      if(timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
    },
    setStatePassive(state) {
      // Don't set state now, just accumulate it, and set a timeout to make sure we eventually
      // set it on the component. If a non-passive setState call happens in the meantime, that
      // will flush it out sooner
      Object.assign(accumulatedState, state);
      if(!timeout) {
        timeout = setTimeout(() => this.setState({}), minRenderPeriod_ms);
      }
    },
  };
}

// Register an App instance and feed it state updates
function hookup_remote_state(app) {
  let imageObjectUrl = null;
  let imageTimeout = null;

  let stateWrapper = setStateWrapper(app, 500);

  function handle_event(event) {
    if (event.electrodeState) {
      // There are two groups of drive electrodes, A and B, used mostly for feedback controlled drop splitting. 
      // For display purposes here, they are just OR'd together so both groups are highlighted
      let electrodeState = event.electrodeState.driveGroups[0].electrodes.map((elem, i) => {
        return elem || event.electrodeState.driveGroups[1].electrodes[i];
      });
      stateWrapper.setState({
        electrodeState: electrodeState,
      });
    }
    else if(event.image) {
      const imageBlob = new Blob([event.image.imageData]);
      const newImageUrl = URL.createObjectURL(imageBlob);
      stateWrapper.setState({
        image: newImageUrl,
      });
      // Clear any existing timeout, and set a new one
      clearTimeout(imageTimeout);
      imageTimeout = setTimeout(() => {
        stateWrapper.setState({
          image: "",
        });
      }, 3000);
      // Free the previous frame from store
      URL.revokeObjectURL(imageObjectUrl);
      imageObjectUrl = newImageUrl;
    } else if(event.imageTransform) {
      let newTransform = null;
      if (event.imageTransform.transform.length > 0) {
        let t =  event.imageTransform.transform;
        newTransform = [
          [t[0], t[1], t[2]],
          [t[3], t[4], t[5]],
          [t[6], t[7], t[8]],
        ];
      }
      stateWrapper.setStatePassive({
        imageTransform: newTransform,
        imageWidth: event.imageTransform.imageWidth,
        imageHeight: event.imageTransform.imageHeight,
      });
    } else if(event.scanCapacitance) {
      stateWrapper.setStatePassive({
        bulk_capacitance: event.scanCapacitance.measurements,
      });
    } else if(event.hvRegulator) {
      stateWrapper.setStatePassive({
        voltage: event.hvRegulator.voltage,
        vTargetOut: event.hvRegulator.vTargetOut,
      });
    } else if(event.temperatureControl) {
      stateWrapper.setStatePassive({temperatures: event.temperatureControl.temperatures});
    } else if(event.deviceInfo) {
      stateWrapper.setState({
        device_info: {
          connected: event.deviceInfo.connected,
          serial_number: event.deviceInfo.serialNumber,
          software_version: event.deviceInfo.softwareVersion,
        },
      });
    }
  }

  let pdrpc = PdRpc();
  pdrpc.getBoardDefinition().then((resp) => {
    app.setState({
      layout: new Layout(resp.layout),
    });
  });
  pdrpc.getParameterDefinitions().then((resp) => {
    app.setState({
      parameterList: resp.parameters,
    });
    return resp;
  }).then(async (resp) => {
    let paramValues = {};
    for(let i=0; i<resp.parameters.length; i++) {
      let paramId = resp.parameters[i].id;
      paramValues[paramId] = await pdrpc.getParameter(paramId);
    }
    app.setState({
      parameters: paramValues,
    });
  });
  pdrpc.getDeviceInfo().then((resp) => {
    app.setState({
      device_info: resp,
    });
  });

  let socket = PdSocket(handle_event);

  app.setState({pdrpc: pdrpc});

  return {
    disconnect() {
      socket.close();
    },
    setParameter(id, value) {
      return pdrpc.setParameter(id, value);
    },
    refreshParameters() {
      return pdrpc.getParameterDefinitions().then((resp) => {
        app.setState({
          parameterList: resp.parameters,
        });
        return resp;
      }).then(async (resp) => {
        let paramValues = {};
        for(let i=0; i<resp.parameters.length; i++) {
          let paramId = resp.parameters[i].id;
          paramValues[paramId] = await pdrpc.getParameter(paramId);
        }
        app.setState({
          parameters: paramValues,
          parameterDirtyMap: {},
        });
      });
    },
    saveParameters() {
      return pdrpc.setParameter(0xFFFFFFFF, 1);
    },
  };
}

let persistedLayout = {
  defaultLayout: [
    {i: 'Live View', x: 2, y: 0, w: 10, h: 15},
    {i: 'Capacitance', x:12, y:0, w: 5, h: 7},
    {i: 'Stats', x: 12, y:6, w:4,  h:4},
    {i: 'Control', x: 12, y:11, w: 4, h:4},
  ],
  layout: [],
  load() {
    let layout = this.defaultLayout;
    let ls = null;
    if (global.localStorage) {
      try {
        ls = JSON.parse(global.localStorage.getItem("purpledrop-dashboard"));
      } catch (e) {
        /*Ignore*/
      }
      if(ls) {
        layout = ls['grid_layout'];
      }
    }
    return layout;
  },
  save(new_layout) {
    self.layout = new_layout;
    if (global.localStorage) {
      global.localStorage.setItem(
        "purpledrop-dashboard",
        JSON.stringify({
          'grid_layout': new_layout,
        }),
      );
    }
  },
};

const WrappedGridLayout = WidthProvider(GridLayout);
class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      bulk_capacitance: Array(128).fill({capacitance: 0.0, drop_present: false}),
      paramModalOpen: false,
      parameters: {},
      parameterDirtyMap:{},
      device_info: {
        connected: false,
        serial_number: null,
        software_version: null,
      },
    };
    this.openParamModal = this.openParamModal.bind(this);
    this.closeParamModal = this.closeParamModal.bind(this);
    this.openHelpModal = this.openHelpModal.bind(this);
    this.closeHelpModal = this.closeHelpModal.bind(this);
    this.onParameterChange = this.onParameterChange.bind(this);
    this.onParameterSave = this.onParameterSave.bind(this);
    this.onParameterRefresh = this.onParameterRefresh.bind(this);
    this.onHvEnabledChange = this.onHvEnabledChange.bind(this);
  }

  componentDidMount() {
    this.state_handle = hookup_remote_state(this);
  }

  componentDidUpdate() {
    ReactTooltip.rebuild();
  }

  componentWillUnmount() {
    this.state_handle.disconnect();
  }

  openHelpModal() {
    this.setState({helpModalOpen: true});
  }

  closeHelpModal() {
    this.setState({helpModalOpen: false});
  }

  openParamModal() {
    this.setState({paramModalOpen: true});
  }

  closeParamModal() {
    this.setState({paramModalOpen: false});
  }

  onParameterChange(id, newValue) {
    let parameters = this.state.parameters;
    let dirtyMap = this.state.parameterDirtyMap;
    parameters[id] = newValue;
    dirtyMap[id] = true;
    this.setState({
      parameters: parameters,
      parameterDirtyMap: dirtyMap,
    });
  }

  onParameterSave(id) {
    let dirtyMap = this.state.parameterDirtyMap;
    dirtyMap[id] = false;
    this.setState({parameterDirtyMap: dirtyMap});
    return this.state_handle.setParameter(id, this.state.parameters[id]);
  }

  onParameterRefresh() {
    return this.state_handle.refreshParameters();
  }

  onHvEnabledChange(enable) {
    let parameters = this.state.parameters;
    parameters[HV_ENABLE_PARAM_ID] = enable ? 1 : 0;
    this.state_handle.setParameter(HV_ENABLE_PARAM_ID, parameters[HV_ENABLE_PARAM_ID]);
  }

  render() {
    const statusContent = () => {
      if(this.state.device_info.connected) {
        let tipString = `Serial: ${this.state.device_info.serial_number}<br />`;
        tipString += `Software: ${this.state.device_info.software_version}`;
        return <p>Device Status: Connected<span data-for="tooltip" data-tip={tipString}><Info style={{ color: 'green' }}/></span></p>;
      } else {
        return <p>Device Status: Disconnected <ReportProblem style={{ color: 'red' }} /></p>;
      }
    };

    const paramModalStyles = {
      content : {
        top: '50%',
        left: '50%',
        right: 'auto',
        bottom: 'auto',
        marginRight: '-50%',
        transform: 'translate(-50%, -50%)',
      },
    };

    const helpModalStyles = {
      content : {
        top: '50%',
        left: '50%',
        right: 'auto',
        bottom: 'auto',
        marginRight: '-50%',
        transform: 'translate(-50%, -50%)',
      },
    };

    if(!this.state.layout) {
      return <div>
        <Preloader />
      </div>;
    } else {
      return <Router>
        <div>
          <Switch>
            <Route path="/capacitance_test">
              <CapacitanceDisplay capacitance={this.state.bulk_capacitance} layout={this.state.layout} width={400} height={250} />
            </Route>
            <Route path="/liveview_test">
              <LiveView
                image={this.state.image}
                transform={this.state.imageTransform}
                electrodeState={this.state.electrodeState}
                layout={this.state.layout}
                imageWidth={this.state.imageWidth}
                imageHeight={this.state.imageHeight}
                width={400}
                height={250}
                onSetElectrodes={(pins) => {this.state.pdrpc.setElectrodePins(pins);}}
              />
            </Route>
            <Route path="/">
              <Modal
                isOpen={this.state.paramModalOpen}
                onRequestClose={this.closeParamModal}
                contentLabel="Device Parameters"
                style={paramModalStyles}>
                  <h1>Purple Drop Configuration Parameters</h1>
                  <div style={{padding: '5px'}}>
                    <ParameterList
                      onChange={this.onParameterChange}
                      onSave={this.onParameterSave}
                      onRefresh={this.state_handle.refreshParameters}
                      onPersist={this.state_handle.saveParameters}
                      parameterList={this.state.parameterList}
                      parameters={this.state.parameters}
                      parameterDirtyMap={this.state.parameterDirtyMap}
                    />
                    <button className="closeButton" onClick={this.closeParamModal}>Close</button>
                  </div>

              </Modal>
              <Modal
                isOpen={this.state.helpModalOpen}
                onRequestClose={this.closeHelpModal}
                contentLabel="Help"
                style={helpModalStyles}
              >
                <Usage />
              </Modal>
              <ReactTooltip id="tooltip" multiline={true} />
              <div className="page-layout" style={{display: "flex", flexDirection: "column", alignItems: "center"}}>
                <div className='logobanner'>
                    <div><img className='uw-logo' src={uwLogo} /></div>
                    <div><img className='misl-logo' src={mislLogo} /></div>
                </div>
                <div className='title' style={{display: 'flex', justifyContent: 'space-around', width:"100%", maxWidth:"800px"}}>
                  <div style={{display: 'flex',  alignItems: 'center'}}>
                    <button onClick={this.openParamModal}>Parameters</button>
                  </div>
                  <div><h1 style={{textAlign: "center"}}>Purple Drop Dashboard</h1></div>
                  <div style={{display: 'flex',  alignItems: 'center'}}><a href="#"
                      onClick={this.openHelpModal}>Help</a>
                  </div>
                </div>

                </div>
                <div style={{textAlign: 'center'}}>
                  {statusContent()}
                </div>
                <div style={{position: "relative"}}>
                  <WrappedGridLayout
                    className="layout"
                    layout={persistedLayout.load()}
                    onLayoutChange={(layout) => { persistedLayout.save(layout); }}
                    cols={20}
                    rows={20}
                    rowHeight={30}
                    draggableCancel=".draggable-cancel"
                    draggableHandle=".drag-handle">

                    <div style={{ border: '1px solid #dddddd'}} key='Live View'>
                      <DraggableBox title='Live View'>
                        <LiveView
                          image={this.state.image}
                          transform={this.state.imageTransform}
                          electrodeState={this.state.electrodeState}
                          layout={this.state.layout}
                          imageWidth={this.state.imageWidth}
                          imageHeight={this.state.imageHeight}
                          onSetElectrodes={(pins) => {this.state.pdrpc.setElectrodePins(pins);}}
                        />
                      </DraggableBox>
                    </div>

                    <div key='Capacitance'>
                      <DraggableBox title='Capacitance'>
                        <CapacitanceDisplay capacitance={this.state.bulk_capacitance} layout={this.state.layout} />
                      </DraggableBox>
                    </div>

                    <div key='Stats'>
                      <DraggableBox title='Stats'>
                        <Stats voltage={this.state.voltage} temperatures={this.state.temperatures} />
                      </DraggableBox>
                    </div>

                    <div key='Control'>
                      <DraggableBox title='Control Panel'>
                        <ControlPanel 
                          hvEnabled={this.state.parameters[HV_ENABLE_PARAM_ID] == 0 ? false : true}
                          onHvEnabledChange={this.onHvEnabledChange}
                          onCalibrateCapacitance={this.state.pdrpc.calibrateCapacitanceOffset}
                        />
                      </DraggableBox>
                    </div>
                  </WrappedGridLayout>
                </div>
            </Route>
          </Switch>
        </div>
      </Router>;
    }
  }
}

export default App;