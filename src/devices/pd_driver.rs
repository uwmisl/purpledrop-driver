use std::time::Duration;
use std::thread;
use serde::Deserialize;
use serialport::prelude::*;
use log::*;

use pd_driver_messages::{
    Parser,
    messages::{
        Message,
        ElectrodeEnableStruct,
        ActiveCapacitanceStruct,
    },
};

use crate::devices::driver::Driver;
use crate::error::Result;
use crate::eventbroker::{EventBroker, timestamp_now};

// Number of electrodes controlled by the driver
const N_PINS: usize = 128;

#[derive(Clone, Debug, Deserialize)]
pub struct Settings {
    pub port: String,
}

impl Settings {
    pub fn make(&self, event_broker: EventBroker) -> Result<PdDriver> {
        let s = SerialPortSettings {
            baud_rate: 230400,
            data_bits: DataBits::Eight,
            flow_control: FlowControl::None,
            parity: Parity::None,
            stop_bits: StopBits::One,
            timeout: Duration::from_millis(1),
        };
        let port = serialport::open_with_settings(&self.port, &s)?;
        Ok(PdDriver::new(port, event_broker))
    }
}

pub struct PdDriver {
    port: Box<dyn SerialPort>,
    event_broker: EventBroker,
    pins: [bool; N_PINS],
}

fn receive_thread(broker: EventBroker, mut port: Box<dyn SerialPort>) {
    let mut parser: Parser = Parser::new();
    
    loop {
        let mut buf = [0u8; 16];
        let result = port.read(&mut buf);
        if let Err(e) = result {
            warn!("Error reading from serial port: {:?}", e);
            continue;
        }
        let readlen = result.unwrap();
        if readlen == 0 {
            continue;
        }

        for i in 0..readlen {
            match parser.parse(buf[i]) {
                Some(msg) => {
                    match msg {
                        Message::ActiveCapacitanceMsg(msg) => {
                            info!("Active Capacitance: {}, {}", msg.baseline, msg.measurement);
                        },
                        _ => (),
                    }
                },
                None => (),
            }
        }
    }
}

impl PdDriver {
    pub fn new(port: Box<dyn SerialPort>, event_broker: EventBroker) -> PdDriver {
        PdDriver { port: port, event_broker, pins: [false; N_PINS] }
    }

    pub fn init(&self) {
        // Start a serial port read thread
        let cloned_broker = self.event_broker.clone();
        let cloned_port: Box<dyn SerialPort> = self.port.try_clone().unwrap();
        thread::spawn(move || {
            receive_thread(cloned_broker, cloned_port);
        });
    }
}

impl Driver for PdDriver {

    fn set_frequency(&mut self, _frequency: f64) -> Result<()> {
        // Not yet implemented
        Ok(())
    }

    /// Set all electrodes to inactive
    fn clear_pins(&mut self) {
        for pin in self.pins.iter_mut() {
            *pin = false;
        }
    }

    fn set_pin(&mut self, pin: usize, value: bool) {
        self.pins[pin] = value;
    }
    /// Enable an electrode
    fn set_pin_hi(&mut self, pin: usize) {
        self.pins[pin] = true;
    }

    /// Disable an electrode
    fn set_pin_lo(&mut self, pin: usize) {
        self.pins[pin] = false;
    }

    /// Transmit the new electrode settings to the driver
    fn shift_and_latch(&mut self) {
        let mut values = [0; N_PINS / 8];
        for i in 0..N_PINS {
            if self.pins[i] {
                let word = i / 8;
                let bit = i % 8;
                values[word] |= 1<<bit;
            }
        }
        let msg = ElectrodeEnableStruct{values};
        let tx_bytes: Vec<u8> = msg.into();
        self.port.write_all(&tx_bytes).unwrap();
    }
}

