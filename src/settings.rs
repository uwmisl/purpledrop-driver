use crate::devices;
use log::*;
use serde::Deserialize;

use std::path::Path;

type BoxedStdError = Box<dyn std::error::Error>;
type StdResult<T, E = BoxedStdError> = std::result::Result<T, E>;

#[derive(Debug, Deserialize)]
pub struct Settings {
    pub board: crate::board::Board,
    pub hv507: devices::hv507::Settings,
    pub mcp4725: Option<devices::mcp4725::Settings>,
    pub pca9685: Option<devices::pca9685::Settings>,
    pub max31865: Option<devices::max31865::Settings>,
}

pub static PD_CONFIG_VAR: &'static str = "PD_CONFIG";
pub static PD_CONFIG_DEFAULT_PATH: &'static str = "/etc/purpledrop/default.toml";

impl Settings {
    pub fn from_file(path: impl AsRef<Path>) -> StdResult<Self> {
        let s = std::fs::read_to_string(path).expect("Couldn't read config file");
        Ok(toml::from_str(&s)?)
    }

    pub fn new() -> StdResult<Self> {
        let path = if let Some(path) = std::env::var_os(PD_CONFIG_VAR) {
            if path.len() == 0 {
                info!("{} empty, using default of {}", PD_CONFIG_VAR, PD_CONFIG_DEFAULT_PATH);
                PD_CONFIG_DEFAULT_PATH.into()
            } else {
                info!("Using {}={:?}", PD_CONFIG_VAR, path);
                path
            }
        } else {
            info!("{} unset, using default of {}", PD_CONFIG_VAR, PD_CONFIG_DEFAULT_PATH);
            PD_CONFIG_DEFAULT_PATH.into()
        };

        Settings::from_file(path)
    }
}