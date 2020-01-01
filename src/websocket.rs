use crate::error::Result;

use std::net::SocketAddr;
use std::sync::mpsc::{channel, Sender};
use std::thread;
use ws; 

struct Server {
}

impl ws::Handler for Server {
    fn on_message(&mut self, msg: ws::Message) -> ws::Result<()> {
        // Do whatever with incoming message; this is intended to be broadcast only 
        println!("Got message: {}", msg);
        Ok(())
    }
}

pub struct Broadcaster {
    msg_in: Sender<Vec<u8>>,
}

impl Broadcaster {
    pub fn new<>(host: SocketAddr) -> ws::Result<Broadcaster> {
        let ws = ws::WebSocket::new(|_| { Server{} } )?;
        let bcast = ws.broadcaster();
        let (msg_in, msg_out) = channel();
        thread::spawn(move || {
            loop {
                let msg = msg_out.recv().unwrap();
                bcast.send(msg).expect("Error sending message");
            }
        });
        thread::spawn(move || {
            ws.listen(host).unwrap();
        });

        Ok(Broadcaster{msg_in})
    }

    pub fn broadcast(&self, msg: &[u8]) -> Result<()> {
        Ok(self.msg_in.send(msg.to_vec())?)
    }
}
