use jsonrpc_core::{Error, ErrorCode};
use jsonrpc_derive::rpc;
use std::sync::{Arc, Mutex};

use crate::purpledrop::{MoveDropResult, PurpleDrop};
use crate::settings::Settings;
use crate::eventbroker::EventBroker;
use crate::board::Board;
use crate::error::Result;
use crate::location::{Direction, Location};

pub struct RpcError(i32, String);

type RpcResult<T> = std::result::Result<T, RpcError>;

impl From<i32> for RpcError {
    fn from(p_err: i32) -> Self {
        Self(p_err, "".to_string())
    }
}

impl From<RpcError> for Error {
    fn from(p_err: RpcError) -> Self {
        let code = ErrorCode::ServerError(p_err.0.into());
        Error{code: code, message: p_err.1, data: None}
    }
}

pub struct PurpleDropRpc {
    purpledrop: Arc<Mutex<PurpleDrop>>,
}

impl PurpleDropRpc {
    pub fn new(settings: Settings, eventbroker: EventBroker) -> Result<PurpleDropRpc> {
        let new_rpc = PurpleDropRpc {
            purpledrop: Arc::new(Mutex::new(PurpleDrop::new(settings, eventbroker.clone())?)),
        };
        Ok(new_rpc)
    }
}

#[rpc(server)]
pub trait Rpc {
    #[rpc(name = "get_board_definition")]
    fn get_board_definition(&self) -> RpcResult<Board>;
    #[rpc(name = "get_bulk_capacitance")]
    fn get_bulk_capacitance(&self) -> RpcResult<Vec<f32>>;
    #[rpc(name = "get_active_capacitance")]
    fn get_active_capacitance(&self) -> RpcResult<f32>;
    #[rpc(name = "set_electrode_pins")]
    fn set_electrode_pins(&self, pins: Vec<u32>) -> RpcResult<()>;
    #[rpc(name = "move_drop")]
    fn move_drop(&self, start: [i32; 2], size: [i32; 2], direction: String) -> RpcResult<MoveDropResult>;
    #[rpc(name = "get_temperatures")]
    fn get_temperatures(&self) -> RpcResult<Vec<f32>>;
    #[rpc(name = "set_pwm_duty_cycle")]
    fn set_pwm_duty_cycle(&self, chan: u8, duty_cycle: f32) -> RpcResult<()>;
}

impl Rpc for PurpleDropRpc {
    fn get_board_definition(&self) -> RpcResult<(Board)> {
        let arc = self.purpledrop.clone();
        let pd = arc.lock().unwrap();
        Ok(pd.board.clone())
    }

    fn get_bulk_capacitance(&self) -> RpcResult<Vec<f32>> {
        let arc = self.purpledrop.clone();
        let pd = arc.lock().unwrap();

        pd.bulk_capacitance().map_err(|e| RpcError(-3, format!("{:?}", e)))
    }

    fn get_active_capacitance(&self) -> RpcResult<f32> {
        let arc = self.purpledrop.clone();
        let pd = arc.lock().unwrap();

        pd.active_capacitance().map_err(|e| RpcError(-6, format!("{:?}", e)))
    }

    fn set_electrode_pins(&self, pins: Vec<u32>) -> RpcResult<()> {
        let mut pin_array = vec![false; PurpleDrop::n_pins()];
        for pin in pins {
            pin_array[pin as usize] = true;
        }
        let arc = self.purpledrop.clone();
        let mut pd = arc.lock().unwrap();
        pd.output_pins(&pin_array);
        
        Ok(())
    }

    fn move_drop(&self, start: [i32; 2], size: [i32; 2], direction: String) -> RpcResult<MoveDropResult> {
        let start = Location{x: start[0], y: start[1]};
        let size = Location{x: size[0], y: size[1]};
        let direction = match Direction::from_str(&direction) {
            Ok(dir) => dir,
            Err(_) => return Err(RpcError(-1, format!("Invalid direction argument: {:?}", direction))),
        };

        let arc = self.purpledrop.clone();
        let mut pd = arc.lock().unwrap();

        futures::executor::block_on(pd.move_drop(start, size, direction))
        .map_err(|e| RpcError(-2, format!("Error executing move drop: {:?}", e)))
    }

    fn get_temperatures(&self) -> RpcResult<Vec<f32>> {
        let arc = self.purpledrop.clone();
        let mut pd = arc.lock().unwrap();

        pd.temperatures().map_err(|e| RpcError(-4, format!("{:?}", e)))
    }

    fn set_pwm_duty_cycle(&self, chan: u8, duty_cycle: f32) -> RpcResult<()> {
        let arc = self.purpledrop.clone();
        let mut pd = arc.lock().unwrap();

        pd.set_pwm_duty_cycle(chan, duty_cycle).map_err(|e| RpcError(-5, format!("{:?}", e)))
    }
}
