use jsonrpc_core::{Error, ErrorCode};
use jsonrpc_derive::rpc;
use std::sync::{Arc, Mutex};

use log::*;

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
    eventbroker: Arc<Mutex<EventBroker>>,
}

impl PurpleDropRpc {
    pub fn new(settings: Settings, eventbroker: EventBroker) -> Result<PurpleDropRpc> {
        let new_rpc = PurpleDropRpc {
            purpledrop: Arc::new(Mutex::new(PurpleDrop::new(settings, eventbroker.clone())?)),
            eventbroker: Arc::new(Mutex::new(eventbroker)),
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
    #[rpc(name = "set_electrode_pins")]
    fn set_electrode_pins(&self, pins: Vec<u32>) -> RpcResult<()>;
    #[rpc(name = "move_drop")]
    fn move_drop(&self, size: [i32; 2], start: [i32; 2], direction: String) -> RpcResult<MoveDropResult>;
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

        match pd.bulk_capacitance() {
            Ok(result) => Ok(result),
            Err(e) => Err(RpcError(-3, format!("{:?}", e))),
        }
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
        warn!("Move drop: {:?} {:?} {:?}", size, start, direction);

        let start = Location{x: start[0], y: start[1]};
        let size = Location{x: size[0], y: size[1]};
        let direction = match Direction::from_str(&direction) {
            Ok(dir) => dir,
            Err(_) => return Err(RpcError(-1, format!("Invalid direction argument: {:?}", direction))),
        };

        let arc = self.purpledrop.clone();
        let mut pd = arc.lock().unwrap();

        let result = match futures::executor::block_on(pd.move_drop(start, size, direction)) {
            Ok(r) => r,
            Err(e) => return Err(RpcError(-2, format!("Error executing move drop: {:?}", e))),
        };

        Ok(result)
    }
}
