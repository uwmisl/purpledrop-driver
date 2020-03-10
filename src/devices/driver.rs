use tokio::sync::broadcast;

use crate::error::Result;

#[derive(Clone, Debug)]
pub enum CapacitanceEvent {
    Ack,
    Measurement(f32),
    StepperAck,
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

    fn active_capacitance(&self) -> f32;

    fn bulk_capacitance(&self) -> Vec<f32>;
    /// This is getting pretty outside the scope of an HV507 replacement, 
    /// and if this ever hits master we should re-consider how this is setup. 
    fn move_stepper(&mut self, steps: i16, period: u16) -> Result<()>;
}

