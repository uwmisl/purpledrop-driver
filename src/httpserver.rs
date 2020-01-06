use std::error::Error;

use jsonrpc_core::IoHandler;
use jsonrpc_http_server::{
    hyper::{Body, Method, Request, Response},
    RequestMiddlewareAction, ServerBuilder,
};

use prost::Message;
use hyper_staticfile::Static;

use futures::Future;

use crate::settings::Settings;
use crate::eventbroker::EventBroker;
use crate::purpledrop_rpc::{PurpleDropRpc, Rpc};
use crate::websocket::Broadcaster;
use crate::video_client::VideoClient;

use log::*;

fn serve(req: Request<Body>, statik: &Static) -> RequestMiddlewareAction {
    let path = req.uri().path();

    trace!("{:?}", req);

    if path.contains("..") {
        warn!("Found '..' in path!");
        return Response::builder()
            .status(404)
            .body("cannot have '..' in path".into())
            .unwrap()
            .into();
    }

    let method = req.method();
    match (path, method) {
        ("/status", _) => {
            debug!("returning status ok");
            Response::new("Server running OK.".into()).into()
        }
        ("/rpc", _) => {
            debug!("rpc");
            req.into()
        }
        (_, &Method::GET) => match statik.serve(req).wait() {
            Ok(resp) => {
                debug!("returning static file");
                resp.into()
            }
            Err(err) => {
                debug!("failed getting static file");
                Response::builder()
                    .status(404)
                    .body(format!("{:#?}", err).into())
                    .unwrap()
                    .into()
            }
        },
        _ => {
            warn!("bad request");
            Response::builder()
                .status(404)
                .body(format!("{:#?}", req).into())
                .unwrap()
                .into()
        }
    }
}

pub fn run(settings: Settings) -> std::result::Result<(), Box<dyn Error>> {
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

    let server = ServerBuilder::new(io)
        .threads(settings.daemon.threads)
        .request_middleware(move |req| serve(req, &statik))
        .start_http(&settings.daemon.address)
        .expect("Unable to start RPC server");

    debug!("HTTP server created.");

    
    let ws = Broadcaster::new(settings.daemon.websocket)?;
    eventbroker.add_handler(move |event| {
        let mut buf = vec![];
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
    
    server.wait();

    info!("Shutting down");
    Ok(())
}

