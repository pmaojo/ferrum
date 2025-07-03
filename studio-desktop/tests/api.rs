use mockito::{Matcher, Server, ServerOpts};
use std::sync::mpsc::channel;
use studio_desktop::api::{set_log_sender, simulate_flow};

#[test]
fn simulate_flow_sends_payload_and_logs() {
    let opts = ServerOpts {
        port: 8001,
        ..Default::default()
    };
    let mut server = Server::new_with_opts(opts);
    let _m = server
        .mock("POST", "/simulate/flow")
        .match_header("content-type", "application/json")
        .match_body(Matcher::JsonString("{\"yaml\":\"demo\"}".into()))
        .with_body("{\"text\":\"ok\"}")
        .create();

    let (tx, rx) = channel();
    set_log_sender(tx);

    let result = simulate_flow("demo").unwrap();
    assert_eq!(result, "ok");
    _m.assert();

    let log = rx.try_recv().expect("no log sent");
    assert!(log.contains("/simulate/flow"));
}
