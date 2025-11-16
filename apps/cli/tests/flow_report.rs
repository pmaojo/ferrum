use ferrum_cli::commands::flow_report;
use mockito::Server;
use serial_test::serial;
use std::fs;
use tempfile::NamedTempFile;

#[test]
#[serial]
fn flow_report_returns_err_on_http_failure() {
    let mut server = Server::new();
    std::env::set_var("FERRUM_API_BASE_URL", server.url());
    let _m = server
        .mock("POST", "/simulate/flow")
        .with_status(500)
        .create();
    let tmp = NamedTempFile::new().unwrap();
    fs::write(tmp.path(), "test: value").unwrap();
    let result = flow_report(tmp.path().to_path_buf());
    drop(server);
    std::env::remove_var("FERRUM_API_BASE_URL");
    assert!(result.is_err());
}

#[test]
#[serial]
fn flow_report_returns_ok_on_success() {
    let mut server = Server::new();
    std::env::set_var("FERRUM_API_BASE_URL", server.url());
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
    std::env::remove_var("FERRUM_API_BASE_URL");
    assert!(result.is_ok());
}

#[test]
#[serial]
fn flow_report_handles_generic_json_body() {
    let mut server = Server::new();
    std::env::set_var("FERRUM_API_BASE_URL", server.url());
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
    std::env::remove_var("FERRUM_API_BASE_URL");
    assert!(matches!(result, Ok(())));
}
