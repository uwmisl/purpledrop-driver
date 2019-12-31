use crate::devices;
use log::*;
use serde::Deserialize;

use std::path::Path;

type BoxedStdError = Box<dyn std::error::Error>;
type StdResult<T, E = BoxedStdError> = std::result::Result<T, E>;

pub static PD_CONFIG_VAR: &'static str = "PD_CONFIG";
pub static PD_CONFIG_DEFAULT_PATH: &'static str = "/etc/purpledrop/default.toml";
pub static PD_STATIC_DIR_DEFAULT_PATH: &'static str = "/usr/share/purpledrop/webroot";

// serde requires a function to return a default value
// There's some talk of taking values, and perhaps some day this will be 
// supported: https://github.com/serde-rs/serde/issues/1030
fn default_address() -> std::net::SocketAddr { "0.0.0.0:80".parse().unwrap() }
fn default_websocket() -> std::net::SocketAddr { "0.0.0.0:2129".parse().unwrap() }
fn default_threads() -> usize { 4 }
fn default_static_dir() -> String { PD_STATIC_DIR_DEFAULT_PATH.to_string() }

#[derive(Clone, Debug, Deserialize)]
pub struct DaemonSettings {
    #[serde(default = "default_address")]
    pub address: std::net::SocketAddr,
    #[serde(default = "default_websocket")]
    pub websocket: std::net::SocketAddr,
    #[serde(default = "default_threads")]
    pub threads: usize,
    #[serde(default = "default_static_dir")]
    pub static_dir: String,
    pub video_host: Option<std::net::SocketAddr>,
}

impl Default for DaemonSettings {
    fn default() -> DaemonSettings {
        DaemonSettings {
            address: default_address(),
            websocket: default_websocket(),
            threads: default_threads(),
            static_dir: default_static_dir(),
            video_host: None,
        }
    }
}

#[derive(Clone, Debug, Deserialize)]
pub struct Settings {
    #[serde(default)]
    pub daemon: DaemonSettings,
    pub board: crate::board::Board,
    pub hv507: devices::hv507::Settings,
    pub mcp4725: Option<devices::mcp4725::Settings>,
    pub pca9685: Option<devices::pca9685::Settings>,
    pub max31865: Option<devices::max31865::Settings>,
}

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

#[cfg(test)]
mod tests {
    use crate::*;
    use crate::settings::*;

    #[test]
    fn test_default_config() {
        let cfg = Settings::from_file("config/default.toml").unwrap();
        assert_eq!(cfg.daemon.static_dir, PD_STATIC_DIR_DEFAULT_PATH);
        assert_eq!(cfg.hv507.frequency, 500.0);
    }
}