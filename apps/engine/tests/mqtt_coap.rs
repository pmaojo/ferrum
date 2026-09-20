use std::{collections::HashMap, net::SocketAddr, thread, time::Duration};

// `ferrum_engine::services` (the mqtt/coap client wrappers this file
// exercises) has never been built, and neither the `mqtt` nor `coap`
// feature is declared in ferrum-engine's Cargo.toml, so the `#[tokio::test]`
// functions below are permanently inert either way. Gate the import the
// same as the tests themselves so this file compiles instead of failing on
// a crate that doesn't exist.
#[cfg(any(feature = "mqtt", feature = "coap"))]
use ferrum_engine::services;

#[cfg(feature = "coap")]
use coap::{
    request::{CoapRequest, Method},
    server::UdpCoapListener,
    Server,
};
#[cfg(feature = "mqtt")]
use rumqttd::{Broker, Config, ConnectionSettings, ServerSettings};
#[cfg(feature = "coap")]
use tokio::net::UdpSocket;
#[cfg(feature = "coap")]
use tokio::sync::mpsc;

fn unused_port() -> u16 {
    std::net::TcpListener::bind("127.0.0.1:0")
        .unwrap()
        .local_addr()
        .unwrap()
        .port()
}

#[cfg(feature = "mqtt")]
fn start_mqtt_broker(port: u16) -> thread::JoinHandle<()> {
    let mut config = Config::default();
    let mut servers = HashMap::new();
    servers.insert(
        "test".into(),
        ServerSettings {
            name: "test".into(),
            listen: SocketAddr::from(([127, 0, 0, 1], port)),
            tls: None,
            next_connection_delay_ms: 0,
            connections: ConnectionSettings {
                connection_timeout_ms: 100,
                max_payload_size: 1024,
                max_inflight_count: 10,
                auth: None,
                external_auth: None,
                dynamic_filters: true,
            },
        },
    );
    config.v4 = Some(servers);
    thread::spawn(move || {
        let mut broker = Broker::new(config);
        broker.start().unwrap();
    })
}

#[cfg(feature = "coap")]
fn spawn_coap_server(ip: &'static str) -> mpsc::UnboundedReceiver<u16> {
    let (tx, rx) = mpsc::unbounded_channel();
    tokio::spawn(async move {
        let sock = UdpSocket::bind(ip).await.unwrap();
        let addr = sock.local_addr().unwrap();
        let listener = Box::new(UdpCoapListener::from_socket(sock));
        let server = Server::from_listeners(vec![listener]);
        tx.send(addr.port()).unwrap();
        server
            .run(|mut req: Box<CoapRequest<SocketAddr>>| async move {
                let method = *req.get_method();
                if let Some(ref mut resp) = req.response {
                    match method {
                        Method::Get => resp.message.payload = b"ok".to_vec(),
                        Method::Post => resp.message.payload = req.message.payload.clone(),
                        _ => {}
                    }
                }
                req
            })
            .await
            .unwrap();
    });
    rx
}

#[cfg(feature = "mqtt")]
#[tokio::test]
async fn mqtt_connect_publish() {
    let port = unused_port();
    let _broker = start_mqtt_broker(port);
    // allow broker to start
    tokio::time::sleep(Duration::from_millis(200)).await;

    let (client, handle) = services::mqtt::connect("test", "127.0.0.1", port).await;
    services::mqtt::publish(&client, "demo", "hello")
        .await
        .unwrap();
    // give some time for publish
    tokio::time::sleep(Duration::from_millis(50)).await;
    handle.abort();
}

#[cfg(feature = "coap")]
#[tokio::test]
async fn coap_get_post() {
    let mut rx = spawn_coap_server("127.0.0.1:0");
    let port = rx.recv().await.unwrap();
    let url = format!("coap://127.0.0.1:{port}/test");

    let data = services::coap::get(&url).await.unwrap();
    assert_eq!(data, b"ok".to_vec());

    let resp = services::coap::post(&url, b"hi").await.unwrap();
    assert_eq!(resp, b"hi".to_vec());
}
