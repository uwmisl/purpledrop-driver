use crate::error::{Error, Result};

use jsonrpc_core::IoHandler;
use hyper::{
    {Body, Method, Request, Response, Server, StatusCode},
    service::{make_service_fn, service_fn},
};

use prost::Message;
use hyper_staticfile::Static;
use bytes::buf::Buf;

use crate::settings::Settings;
use crate::eventbroker::EventBroker;
use crate::protobuf;
use crate::purpledrop_rpc::{PurpleDropRpc, Rpc};
use crate::websocket::Broadcaster;
use crate::video_client::VideoClient;

use log::*;

async fn serve(req: Request<Body>, statik: Static, io: IoHandler) -> Result<Response<Body>> {
    let path = req.uri().path();

    trace!("{:?}", req);

    if path.contains("..") {
        warn!("Found '..' in path!");
        return Ok(Response::builder()
            .status(StatusCode::NOT_FOUND)
            .body("cannot have '..' in path".into())
            .unwrap())
    }

    let method = req.method();
    match (path, method) {
        ("/status", _) => {
            debug!("returning status ok");
            Ok(Response::new("Server running OK.".into()))
        }
        ("/rpc", &Method::POST) => {
            debug!("rpc");
            let whole_body = hyper::body::aggregate(req).await?;
            let res = match io.handle_request_sync(std::str::from_utf8(whole_body.bytes()).unwrap()) {
                Some(resp_str) => {
                    Response::builder()
                        .status(200)
                        .body(resp_str.into())
                        .unwrap()
                },
                None => {
                    Response::builder()
                        .status(500)
                        .body("No RPC response".into())
                        .unwrap()
                },
            };
            Ok(res)
        }
        (_, &Method::GET) => {
            let res = match statik.serve(req).await {
                Ok(res) => res,
                Err(e) => {
                    warn!("Error serving static file: {:?}", e);
                    Response::builder()
                        .status(404)
                        .body("File not found".into())
                        .unwrap()
                }
            };
            Ok(res)
        },
        _ => {
            warn!("bad request");
            Ok(Response::builder()
                .status(400)
                .body(format!("{:#?}", req).into())
                .unwrap())
        }
    }
}

pub async fn run(settings: Settings) -> std::result::Result<(), Box<dyn std::error::Error>> {
    debug!("static_dir: {}", settings.daemon.static_dir);
    debug!("threads: {}", settings.daemon.threads);
    debug!("address: {}", settings.daemon.address);

    let mut eventbroker = EventBroker::new();

    let purpledrop = PurpleDropRpc::new(settings.clone(), eventbroker.clone())?;

    debug!("PurpleDrop created.");

    let mut io = IoHandler::default();
    io.extend_with(purpledrop.to_delegate());

    debug!("IoHandler created.");

    let statik = Static::new(&settings.daemon.static_dir);

    let new_service = make_service_fn(move |_| {
        let statik = statik.clone();
        let io = io.clone();
        async {
            Ok::<_, Error>(service_fn(move |req| {
                // Clone again to ensure that client outlives this closure.
                serve(req, statik.to_owned(), io.to_owned())
            }))
        }
    });

    let server = Server::bind(&settings.daemon.address).serve(new_service);

    debug!("HTTP server created.");

    
    let ws = Broadcaster::new(settings.daemon.websocket)?;
    eventbroker.add_handler(move |event| {
        let mut buf = vec![];
        // Don't send active capacitance messages out the websocket
        // They come at a high frequency, and the browser can have a very
        // hard time handling them. 
        // TODO: Ideally, clients could choose which events they want
        // to receive
        let msg = event.clone().msg.unwrap();
        match msg {
            protobuf::purple_drop_event::Msg::ActiveCapacitance(_) => return,
            _ => ()
        };
    
        event.encode(&mut buf).unwrap();
        ws.broadcast(&buf).unwrap();
        
    });
    debug!("Websocket server created.");
    
    let video_client;
    if settings.daemon.video_host.is_some() {
        let video_host = settings.daemon.video_host.unwrap();
        video_client = VideoClient::new(eventbroker.clone(), video_host);
        video_client.start();
        debug!("Video client created.");
    }

    server.await.unwrap();

    info!("Shutting down");
    Ok(())
}

