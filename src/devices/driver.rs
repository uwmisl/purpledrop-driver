use crate::error::Result; 

pub trait Driver: Send {
    fn set_frequency(&mut self, frequency: f64) -> Result<()>;
    
    fn clear_pins(&mut self);

    fn set_pin(&mut self, pin: usize, value: bool);

    fn set_pin_hi(&mut self, pin: usize);

    fn set_pin_lo(&mut self, pin: usize);

    fn shift_and_latch(&mut self);
}