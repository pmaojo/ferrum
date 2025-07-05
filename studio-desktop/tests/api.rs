use mockito::{Matcher, Server, ServerOpts};
use studio_desktop::api::simulate_flow_async;
use studio_desktop::api::{generate_component_async, validate_yaml_async};

#[test]
fn simulate_flow_sends_payload_and_logs() {
    let opts = ServerOpts {
        port: 0,
        ..Default::default()
    };
    let mut server = Server::new_with_opts(opts);
    std::env::set_var("FERRUM_API_BASE_URL", server.url());
    let _m = server
        .mock("POST", "/simulate/flow")
        .match_header("content-type", "application/json")
        .match_body(Matcher::JsonString("{\"yaml\":\"demo\"}".into()))
        .with_body("{\"text\":\"ok\"}")
        .create();

    futures_lite::future::block_on(async {
        let res = simulate_flow_async("demo").await;
        assert!(res.is_ok());
    });
    _m.assert();
    std::env::remove_var("FERRUM_API_BASE_URL");
}

#[test]
fn generate_component_sends_prompt() {
    let opts = ServerOpts {
        port: 0,
        ..Default::default()
    };
    let mut server = Server::new_with_opts(opts);
    std::env::set_var("FERRUM_API_BASE_URL", server.url());
    let _m = server
        .mock("POST", "/generate/component")
        .match_header("content-type", "application/json")
        .match_body(Matcher::JsonString("{\"text\":\"demo\"}".into()))
        .with_body("{\"yaml\":\"ok\"}")
        .create();

    futures_lite::future::block_on(async {
        let res = generate_component_async("demo").await;
        assert!(res.is_ok());
    });
    _m.assert();
    std::env::remove_var("FERRUM_API_BASE_URL");
}

#[test]
fn validate_yaml_returns_bool() {
    let opts = ServerOpts {
        port: 0,
        ..Default::default()
    };
    let mut server = Server::new_with_opts(opts);
    std::env::set_var("FERRUM_API_BASE_URL", server.url());
    let _m = server
        .mock("POST", "/validate/yaml")
        .match_header("content-type", "application/json")
        .match_body(Matcher::JsonString("{\"yaml\":\"demo\"}".into()))
        .with_body("{\"valid\":true}")
        .create();

    futures_lite::future::block_on(async {
        let res = validate_yaml_async("demo").await;
        assert_eq!(res.unwrap(), true);
    });
    _m.assert();
    std::env::remove_var("FERRUM_API_BASE_URL");
}
