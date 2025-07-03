use bevy::prelude::*;
use mockito::{Matcher, Server, ServerOpts};
use studio_desktop::api::{LogEvent, simulate_flow};

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

    let mut app = App::new();
    app.add_event::<LogEvent>();
    app.add_systems(Update, |mut writer: EventWriter<LogEvent>| {
        let _ = simulate_flow(&mut writer, "demo");
    });
    app.update();
    _m.assert();
    let logs: Vec<String> = app
        .world
        .resource_mut::<Events<LogEvent>>()
        .drain()
        .map(|e| e.0)
        .collect();
    assert!(logs.iter().any(|l| l.contains("/simulate/flow")));
}
