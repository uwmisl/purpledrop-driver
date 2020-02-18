use std::sync::{Arc, Mutex};
use std::time::Duration;
use std::thread;
use serde::Deserialize;
use serialport::prelude::*;
use tokio::sync::broadcast;
use log::*;

use pd_driver_messages::{
    Parser,
    serialize_msg,
    messages::{
        Message,
        ElectrodeEnableStruct,
        ELECTRODE_ENABLE_ID,
    },
};

use crate::devices::driver::{CapacitanceReceiver, Driver, CapacitanceEvent};
use crate::error::Result;
use crate::eventbroker::{EventBroker, timestamp_now};
use crate::protobuf;

// Number of electrodes controlled by the driver
const N_PINS: usize = 128;
// TODO: Need some calibration procedure to come up with this
const CAP_OFFSET:f32 = -120.0;
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
    event_tx: Arc<Mutex<broadcast::Sender<CapacitanceEvent>>>,
    pins: [bool; N_PINS],
    capacitance_output: Arc<Mutex<([f32; N_PINS], f32)>>,
}

struct BulkMeasurementCollector {
    values: [u16; N_PINS],
}

impl BulkMeasurementCollector {
    pub fn add_measurements<T>(&mut self, start_index: usize, values: Vec<u16>, mut callback: T)
    where
        T: FnMut(Vec<f32>)
    {
        for (i, v) in values.iter().enumerate() {
            self.values[i + start_index] = *v;
        }

        // When setting the last message, fire off the event
        if start_index + values.len() == N_PINS {
            let capacitance = self.values.iter().map(|x| (*x as f32 + CAP_OFFSET) as f32).collect();
            callback(capacitance);
        }
    }
}

fn receive_thread(
    mut broker: EventBroker,
    output_store: Arc<Mutex<([f32; N_PINS], f32)>>,
    event_tx: Arc<Mutex<broadcast::Sender<CapacitanceEvent>>>,
    mut port: Box<dyn SerialPort>,
)
{
    let mut parser: Parser = Parser::new();
    let mut bulk_collector = BulkMeasurementCollector{values: [0; N_PINS]};
    info!("Running pd-driver receive thread");
    loop {
        let mut buf = [0u8; 128];
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
                Ok(result) => {
                    match result {
                        Some(msg) => {
                            match msg {
                                Message::ActiveCapacitanceMsg(msg) => {
                                    let sender = event_tx.lock().unwrap();

                                    let capacitance = (msg.measurement - msg.baseline) as f32 + CAP_OFFSET;
                                    // Send will fail with a SendError if there are no receivers, and this is OK
                                    sender.send(CapacitanceEvent::Measurement(capacitance)).ok();

                                    // store latest sample
                                    let mut output = output_store.lock().unwrap();
                                    output.1 = capacitance;
                                    // let pbmsg = protobuf::ActiveCapacitance{
                                    //     timestamp: Some(timestamp_now()),
                                    //     measurement: Some(protobuf::CapacitanceMeasurement{
                                    //         capacitance: (msg.measurement - msg.baseline) as f32,
                                    //         drop_present: false,
                                    //     }),
                                    // };
                                    //let event = protobuf::PurpleDropEvent{msg: Some(protobuf::purple_drop_event::Msg::ActiveCapacitance(pbmsg))};
                                    //broker.send(event);
                                    //info!("Active Capacitance: {}, {}", msg.baseline, msg.measurement);
                                },
                                Message::BulkCapacitanceMsg(msg) => {
                                    bulk_collector.add_measurements(msg.start_index as usize, msg.values, |values| {
                                        // Send event to broker
                                        let measurements: Vec<protobuf::CapacitanceMeasurement> = values.iter().map( |v| {
                                            protobuf::CapacitanceMeasurement{capacitance: *v as f32, drop_present: false}
                                        }).collect();
                                        let msg = protobuf::BulkCapacitance{
                                            timestamp: Some(timestamp_now()),
                                            measurements: measurements
                                        };
                                        let event = protobuf::PurpleDropEvent{msg: Some(protobuf::purple_drop_event::Msg::BulkCapacitance(msg))};
                                        broker.send(event);

                                        // Store latest sample
                                        let mut output = output_store.lock().unwrap();
                                        for i in 0..N_PINS {
                                            output.0[i] = values[i];
                                        }
                                    });
                                },
                                Message::CommandAckMsg(msg) => {
                                    if msg.acked_id == ELECTRODE_ENABLE_ID {
                                        let sender = event_tx.lock().unwrap();
                                        sender.send(CapacitanceEvent::Ack).ok();
                                    }

                                }
                                _ => (),
                            }
                        },
                        None => (),
                    }
                },
                Err(e) => warn!("Error parsing PdDriver message: {}", e),
            }
        }
    }
}

impl PdDriver {
    pub fn new(port: Box<dyn SerialPort>, event_broker: EventBroker) -> PdDriver {
        let pins = [false; N_PINS];
        let (event_tx, _) = broadcast::channel(256);
        let event_tx = Arc::new(Mutex::new(event_tx));
        let capacitance_output = Arc::new(Mutex::new(([0.0; N_PINS], 0.0)));
        let obj = PdDriver { port, event_broker, event_tx, pins, capacitance_output };
        obj.init();
        obj
    }

    pub fn init(&self) {
        // Start a serial port read thread
        let cloned_broker = self.event_broker.clone();
        let cloned_event_tx = self.event_tx.clone();
        let cloned_output = self.capacitance_output.clone();
        let cloned_port: Box<dyn SerialPort> = self.port.try_clone().unwrap();
        thread::Builder::new()
        .name("PdDriverRx".to_string())
        .spawn(move || {
            receive_thread(cloned_broker, cloned_output, cloned_event_tx, cloned_port);
        }).unwrap();
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
        let tx_bytes: Vec<u8> = serialize_msg(&msg);
        self.port.write_all(&tx_bytes).unwrap();
    }

    fn has_capacitance_feedback(&self) -> bool {
        true
    }

    fn capacitance_channel(&self) -> Option<CapacitanceReceiver> {
        let tx = self.event_tx.lock().unwrap();
        Some(tx.subscribe())
    }

    fn active_capacitance(&self) -> f32 {
        let data = self.capacitance_output.lock().unwrap();
        data.1
    }

    fn bulk_capacitance(&self) -> Vec<f32> {
        let data = self.capacitance_output.lock().unwrap();
        data.0.to_vec()
    }
}

