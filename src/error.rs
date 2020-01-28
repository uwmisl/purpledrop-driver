use anyhow;
pub type Error = anyhow::Error;
pub type Result<T> = anyhow::Result<T>;

#[cfg(target_arch = "arm")]
macro_rules! impl_error {
    ($error:ident, $inner:ty, $variant:ident) => {
        impl From<$inner> for $error {
            fn from(inner: $inner) -> Self {
                $error::$variant(inner)
            }
        }
    };
}

#[cfg(target_arch = "arm")]
#[derive(Debug)]
pub enum HardwareError {
    Gpio(rppal::gpio::Error),
    I2c(rppal::i2c::Error),
    Pwm(rppal::pwm::Error),
    Spi(rppal::spi::Error),
    InvalidPwmChannel(u8),
}

#[cfg(target_arch = "arm")]
impl std::error::Error for HardwareError {}

//pub type Result<T> = std::result::Result<T, Error>;

#[cfg(target_arch = "arm")]
impl_error!(HardwareError, rppal::gpio::Error, Gpio);
#[cfg(target_arch = "arm")]
impl_error!(HardwareError, rppal::i2c::Error, I2c);
#[cfg(target_arch = "arm")]
impl_error!(HardwareError, rppal::pwm::Error, Pwm);
#[cfg(target_arch = "arm")]
impl_error!(HardwareError, rppal::spi::Error, Spi);

#[cfg(target_arch = "arm")]
use std::fmt;
#[cfg(target_arch = "arm")]
impl fmt::Display for HardwareError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            HardwareError::Gpio(inner) => write!(f, "{}", inner),
            HardwareError::I2c(inner) => write!(f, "{}", inner),
            HardwareError::Pwm(inner) => write!(f, "{}", inner),
            HardwareError::Spi(inner) => write!(f, "{}", inner),
            HardwareError::InvalidPwmChannel(chan) => write!(f, "Invalid PWM channel: {}", chan),
        }
    }
}
