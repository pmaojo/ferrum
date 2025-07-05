use ferrum_cli::commands::flow_report;
use mockito::Server;
use std::fs;
use std::sync::{Mutex, OnceLock};
use tempfile::NamedTempFile;

static SERVER: OnceLock<Mutex<Server>> = OnceLock::new();

fn server() -> std::sync::MutexGuard<'static, Server> {
    SERVER
        .get_or_init(|| Mutex::new(Server::new_with_port(8001)))
        .lock()
        .unwrap()
}

#[test]
fn flow_report_returns_err_on_http_failure() {
    let mut server = server();
    let _m = server
        .mock("POST", "/simulate/flow")
        .with_status(500)
        .create();
    let tmp = NamedTempFile::new().unwrap();
    fs::write(tmp.path(), "test: value").unwrap();
    let result = flow_report(tmp.path().to_path_buf());
    drop(server);
    assert!(result.is_err());
}

#[test]
fn flow_report_returns_ok_on_success() {
    let mut server = server();
    let _m = server
        .mock("POST", "/simulate/flow")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{ "text": "ok" }"#)
        .create();

    let tmp = NamedTempFile::new().unwrap();
    fs::write(tmp.path(), "test: value").unwrap();
    let result = flow_report(tmp.path().to_path_buf());
    drop(server);
    assert!(result.is_ok());
}

#[test]
fn flow_report_handles_generic_json_body() {
    let mut server = server();
    let _m = server
        .mock("POST", "/simulate/flow")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{ "foo": "bar" }"#)
        .create();

    let tmp = NamedTempFile::new().unwrap();
    fs::write(tmp.path(), "test: value").unwrap();
    let result = flow_report(tmp.path().to_path_buf());
    drop(server);
    assert!(matches!(result, Ok(())));
}
