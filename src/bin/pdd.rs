use purpledrop::httpserver;
use purpledrop::settings::Settings;
use structopt::StructOpt;

use log::*;

#[derive(StructOpt, Debug)]
pub struct Opts {
    #[structopt(long = "address")]
    address: Option<std::net::SocketAddr>,
    #[structopt(long = "websocket")]
    websocket: Option<std::net::SocketAddr>,
    #[structopt(long = "threads")]
    threads: Option<usize>,
    #[structopt(long = "static")]
    static_dir: Option<String>,
    #[structopt(long = "config")]
    config_file: Option<String>,
    #[structopt(long = "video")]
    video_host: Option<std::net::SocketAddr>,
}

fn main() {
    debug!("");
    let _ = env_logger::try_init();

    let opts = Opts::from_args();

    // Read settings file
    let mut settings = match &opts.config_file {
        Some(path) => Settings::from_file(path).unwrap(),
        None => Settings::new().unwrap(),
    };
    // Override some setting with command flags if provided
    // There's probably some macro-foo to make this more concise...
    if opts.address.is_some() {
        settings.daemon.address = opts.address.unwrap();
    }
    if opts.websocket.is_some() {
        settings.daemon.websocket = opts.websocket.unwrap();
    }
    if opts.threads.is_some() {
        settings.daemon.threads = opts.threads.unwrap();
    }
    if opts.static_dir.is_some() {
        settings.daemon.static_dir = opts.static_dir.unwrap();
    }
    if opts.video_host.is_some() {
        settings.daemon.video_host = opts.video_host;
    }

    httpserver::run(settings).unwrap();
}
