use crate::eventbroker::{EventBroker, timestamp_now};
use crate::error::{Result};
use crate::protobuf:: {
    PurpleDropEvent,
    purple_drop_event::Msg,
    Image,
    ImageTransform,
};

use log::*;

use serde::Deserialize;

use std::net::SocketAddr;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

struct State {
    connected: bool,
    last_frame: i32,
}

/// Creates thread to monitor video server (pdcam) for new frames and transforms,
/// and publishes data to event broker. 
///
/// If it fails to connect, it will simply wait for a timeout period and try again. 
#[derive(Clone)]
pub struct VideoClient {
    eventbroker: Arc<Mutex<EventBroker>>,
    host: SocketAddr,
    state: Arc<Mutex<State>>,
}

#[derive(Clone, Debug, Deserialize)]
struct TransformResponse {
    transform: Option<Vec<Vec<f32>>>,
    image_width: i32,
    image_height: i32,
}

fn update(host: SocketAddr, state: &mut State, eventbroker: &mut EventBroker, http: &reqwest::blocking::Client) -> Result<()> {
    let resp = http.get(&format!("http://{}/transform", host.to_string())).send()?;
    let transform_resp: TransformResponse = resp.json()?;
    let mut resp = http.get(&format!("http://{}/latest", host.to_string()))
        .header("X-Min-Frame-Number", (state.last_frame + 1).to_string())
        .send()?;
    state.last_frame = resp.headers().get("X-Frame-Number").unwrap().to_str()?.parse()?;
    debug!("Received frame {}", state.last_frame);
    let mut jpeg: Vec<u8> = vec![];
    resp.copy_to(&mut jpeg)?;

    // Build and send ImageTransform event
    let transform = match transform_resp.transform {
        Some(t) => t.concat(),
        None => vec![]
    };
    // TODO: Get QR codes from server and return
    let msg = ImageTransform{
        timestamp: Some(timestamp_now()),
        transform: transform,
        image_width: transform_resp.image_width,
        image_height: transform_resp.image_height,
        qr_codes: vec![],
    };
    let event = PurpleDropEvent{msg: Some(Msg::ImageTransform(msg))};
    eventbroker.send(event);

    // Build and send image event
    let msg = Image {
        timestamp: Some(timestamp_now()),
        image_data: jpeg,
    };
    let event = PurpleDropEvent{msg: Some(Msg::Image(msg))};
    eventbroker.send(event);
    Ok(())
}

fn client_thread(host: SocketAddr, state: Arc<Mutex<State>>, eventbroker: Arc<Mutex<EventBroker>>) {
    let http = reqwest::blocking::Client::new();
    loop {
        let result;
        {
            let mut state = state.lock().unwrap();
            let mut eventbroker = eventbroker.lock().unwrap();
            result = update(host, &mut *state, &mut *eventbroker, &http);
        }
        
        // on success, request again immediately
        // on error, hold off for a period of time
        match result {
            Ok(_) => (),
            Err(e) => {
                warn!("Failed to retrieve video info: {:?}", e);
                // If we fail to read, reset the frame counter to 0. 
                // If the server restarted, the frame counter will have too,
                // and if it didn't, we just might get a duplicate frame
                let mut state = state.lock().unwrap();
                state.last_frame = 0;
                thread::sleep(Duration::from_millis(5000));
            },
        }
    }
}

impl VideoClient {
    pub fn new(eventbroker: EventBroker, host: SocketAddr) -> VideoClient {
        VideoClient{
            eventbroker: Arc::new(Mutex::new(eventbroker.clone())),
            host,
            state: Arc::new(Mutex::new(State{connected: false, last_frame: 0}))}
    }

    pub fn start(&self) {
        let cloned_state = self.state.clone();
        let cloned_host = self.host.clone();
        let cloned_broker = self.eventbroker.clone();
        //let mut cloned_client = Box::new(self.clone());
        thread::spawn(move || {
            client_thread(cloned_host, cloned_state, cloned_broker);
        });
    }
}
