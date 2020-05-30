
import React from 'react';
import {
  BrowserRouter as Router,
  Switch,
  Route,
  Link,
} from 'react-router-dom';
import Modal from 'react-modal';
import {ResizableBox} from 'react-resizable';
import 'react-resizable/css/styles.css';

import PdRpc from 'rpc';
import PdSocket from 'pdsocket';
import Layout from './utils/layout';
import Preloader from './components/Preloader';
import CapacitanceDisplay from './components/CapacitanceDisplay';
import LiveView from './components/LiveView';
import Stats from './components/Stats';
import ParameterList from './components/ParameterList';
import mislLogo from './images/misl-logo.svg';
import uwLogo from './images/uw-logo.png';

Modal.setAppElement('#root');

// Register an App instance and feed it state updates
function hookup_remote_state(app) {
  let imageObjectUrl = null;
  let hvCounter = 0;
  
  function handle_event(event) {

    if (event.electrodeState) {
      app.setState({
        electrodeState: event.electrodeState.electrodes,
      });
    }
    else if(event.image) {
      const imageBlob = new Blob([event.image.imageData]);
      const newImageUrl = URL.createObjectURL(imageBlob);
      app.setState({
        image: newImageUrl,
        imageTimestamp: Date.now(),
      });
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
      app.setState({
        imageTransform: newTransform,
        imageWidth: event.imageTransform.imageWidth,
        imageHeight: event.imageTransform.imageHeight,
      });
    } else if(event.bulkCapacitance) {
      app.setState({
        bulk_capacitance: event.bulkCapacitance.measurements,
      });
    } else if(event.hvRegulator) {
      hvCounter++;
      if((hvCounter % 100) == 0) {
        app.setState({
          voltage: event.hvRegulator.voltage,
          vTargetOut: event.hvRegulator.vTargetOut,
        });
      }
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
          parameterDirtyMap: {},
        });
      });
    }
  };
}

class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      bulk_capacitance: Array(128).fill({capacitance: 0.0, drop_present: false}),
      paramModalOpen: false,
      parameters: {},
      parameterDirtyMap:{},
    };
    this.openParamModal = this.openParamModal.bind(this);
    this.closeParamModal = this.closeParamModal.bind(this);
    this.onParameterChange = this.onParameterChange.bind(this);
    this.onParameterSave = this.onParameterSave.bind(this);
    this.onParameterRefresh = this.onParameterRefresh.bind(this);
  }

  componentDidMount() {
    this.state_handle = hookup_remote_state(this);
  }
  
  componentWillUnmount() {
    this.state_handle.disconnect();
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
    this.state_handle.setParameter(id, this.state.parameters[id])
    let dirtyMap = this.state.parameterDirtyMap;
    dirtyMap[id] = false;
    this.setState({parameterDirtyMap: dirtyMap});
  }

  onParameterRefresh() {
    this.state_handle.refreshParameters();
  }

  render() {
    const paramModalStyles = {
      content : {
        top                   : '50%',
        left                  : '50%',
        right                 : 'auto',
        bottom                : 'auto',
        marginRight           : '-50%',
        transform             : 'translate(-50%, -50%)',
      },
    };

    if(typeof this.state.layout === 'undefined') {
      return <div>
        <Preloader />
      </div>;
    } else {
      return <Router>
        <div>
          <nav>
            <ul>
              <li>
                <Link to="/">Home</Link>
              </li>
              <li>
                <Link to="/capacitance_test">Capacitance Test View</Link>
              </li>
              <li>
                <Link to="/liveview_test">LiveView Test</Link>
              </li>
            </ul>
          </nav>

          {/* A <Switch> looks through its children <Route>s and
              renders the first one that matches the current URL. */}
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
                      parameterList={this.state.parameterList} 
                      parameters={this.state.parameters}
                      parameterDirtyMap={this.state.parameterDirtyMap}
                    />
                    <button className="closeButton" onClick={this.closeParamModal}>Close</button>
                  </div>

              </Modal>
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
                      onClick={() => {
                          // openModal({
                          //     title: '',
                          //     content: usage,
                          //     buttons: [
                          //         {id: 'close', text: 'Close'},
                          //     ],
                          //});
                      }}>Help</a>
                  </div>
                </div>
                <ResizableBox className="box" minConstraints={[250, 250]} width={600} height={525} lockAspectRatio={true}>
                  <LiveView 
                    image={this.state.image} 
                    transform={this.state.imageTransform}
                    electrodeState={this.state.electrodeState}
                    layout={this.state.layout}
                    imageWidth={this.state.imageWidth}
                    imageHeight={this.state.imageHeight}
                    onSetElectrodes={(pins) => {this.state.pdrpc.setElectrodePins(pins);}}
                  />
                </ResizableBox>
                <ResizableBox className="box" minConstraints={[150, 150]} width={400} height={300} lockAspectRatio={true}>
                  <CapacitanceDisplay capacitance={this.state.bulk_capacitance} layout={this.state.layout} width={400} height={400} />
                </ResizableBox>
                <ResizableBox className="box" minConstraints={[150, 150]} width={400} height={300} lockAspectRatio={true}>
                  <Stats voltage={this.state.voltage} />
                </ResizableBox>
              </div>;
            </Route>
          </Switch>
        </div>
      </Router>;
    }
  }
}

export default App;