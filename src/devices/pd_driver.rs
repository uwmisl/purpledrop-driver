use std::time::Duration;
use std::thread;
use serde::Deserialize;
use serialport::prelude::*;
use log::*;

use pd_driver_messages::{
    Parser,
    serialize,
    messages::{
        Message,
        ELECTRODE_ENABLE_ID,
        ElectrodeEnableStruct,
        ActiveCapacitanceStruct,
    },
};

use crate::devices::driver::Driver;
use crate::error::Result;
use crate::eventbroker::{EventBroker, timestamp_now};
use crate::protobuf;

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

struct BulkMeasurementCollector {
    values: [u16; N_PINS],
}

impl BulkMeasurementCollector {
    pub fn add_measurements(&mut self, start_index: usize, values: Vec<u16>, event_broker: &mut EventBroker) {
        for (i, v) in values.iter().enumerate() {
            self.values[i + start_index] = *v;
        }

        // When setting the last message, fire off the event
        if start_index + values.len() == N_PINS {
            let measurements: Vec<protobuf::CapacitanceMeasurement> = self.values.iter().map( |v| {
                protobuf::CapacitanceMeasurement{capacitance: *v as f32, drop_present: false} 
            }).collect();
            let msg = protobuf::BulkCapacitance{
                timestamp: Some(timestamp_now()),
                measurements: measurements
            };
            let event = protobuf::PurpleDropEvent{msg: Some(protobuf::purple_drop_event::Msg::BulkCapacitance(msg))};
            event_broker.send(event);
        }
    }
}

fn receive_thread(mut broker: EventBroker, mut port: Box<dyn SerialPort>) {
    let mut parser: Parser = Parser::new();
    let mut bulk_collector = BulkMeasurementCollector{values: [0; N_PINS]};
    info!("Running pd-driver receive thread");
    loop {
        let mut buf = [0u8; 16];
        let result = port.read(&mut buf);
        if let Err(e) = result {
            match e.kind() {
                std::io::ErrorKind::TimedOut => (),
                _ => {warn!("Error reading from serial port: {:?}", e); ()}
            }
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
                            // TODO: Get QR codes from server and return
                            let pbmsg = protobuf::ActiveCapacitance{
                                timestamp: Some(timestamp_now()),
                                measurement: Some(protobuf::CapacitanceMeasurement{
                                    capacitance: (msg.measurement - msg.baseline) as f32,
                                    drop_present: false,
                                }),
                            };
                            let event = protobuf::PurpleDropEvent{msg: Some(protobuf::purple_drop_event::Msg::ActiveCapacitance(pbmsg))};
                            //broker.send(event);
                            //info!("Active Capacitance: {}, {}", msg.baseline, msg.measurement);
                        },
                        Message::BulkCapacitanceMsg(msg) => {
                            bulk_collector.add_measurements(msg.start_index as usize, msg.values, &mut broker);
                            info!("Bulk Capacitance!");

                        }
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
        let obj = PdDriver { port: port, event_broker, pins: [false; N_PINS] };
        obj.init();
        obj
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
                let bit = 7 - (i % 8);
                values[word] |= 1<<bit;
            }
        }
        let msg = ElectrodeEnableStruct{values};
        let payload: Vec<u8> = msg.into();
        let tx_bytes: Vec<u8> = serialize(ELECTRODE_ENABLE_ID, &payload);
        self.port.write_all(&tx_bytes).unwrap();
    }
}

