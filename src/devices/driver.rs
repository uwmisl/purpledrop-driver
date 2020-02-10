use tokio::sync::broadcast;

use crate::error::Result;

#[derive(Clone, Debug)]
pub enum CapacitanceEvent {
    Ack,
    Measurement(f32),
}

pub type CapacitanceReceiver = broadcast::Receiver<CapacitanceEvent>;

pub trait Driver: Send {
    fn set_frequency(&mut self, frequency: f64) -> Result<()>;
    
    fn clear_pins(&mut self);

    fn set_pin(&mut self, pin: usize, value: bool);

    fn set_pin_hi(&mut self, pin: usize);

    fn set_pin_lo(&mut self, pin: usize);

    fn shift_and_latch(&mut self);

    fn has_capacitance_feedback(&self) -> bool;

    fn capacitance_channel(&self) -> Option<CapacitanceReceiver>;

    fn bulk_capacitance(&self) -> Vec<f32>;
}

