import jsonRpc from 'simple-jsonrpc-js'; // Hook-up transport for simple-jsonrpc-js

export function PdRpc() {
  let rpc = new jsonRpc();
  rpc.toStream = (msg) => {
      fetch('/rpc', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
          },
          body: msg,
      }).then(async (response) => {
          if(response.ok) {
            let body = await response.text();
            rpc.messageHandler(body);
          } else {
              console.log("Failed RPC fetch: ", response.statusText);
          }
      }, (reason) => {
          console.log("Failed RPC fetch: ", reason);
      });
  };

  const obj = {
    getBoardDefinition() {
        return rpc.call('get_board_definition');
    },
    getDeviceInfo() {
        return rpc.call('get_device_info');
    },
    getParameterDefinitions() {
        return rpc.call('get_parameter_definitions');
    },
    getParameter(paramIdx) {
        return rpc.call('get_parameter', [paramIdx]);
    },
    setParameter(paramIdx, value) {
        return rpc.call('set_parameter', [paramIdx, value]);
    },
    setElectrodePins(pins) {
        // Send a list of activated pin numbers, e.g. [4, 2, 100] will enable
        // electrode outputs 4, 2, and 100 while disabling all others.
        return rpc.call('set_electrode_pins', [pins]);
    },
  };

  return obj;
}

export default PdRpc;

