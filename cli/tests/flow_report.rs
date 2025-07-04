use ferrum_cli::commands::flow_report;
use mockito::Server;
use std::fs;
use tempfile::NamedTempFile;

#[test]
fn flow_report_returns_err_on_http_failure() {
    let mut server = Server::new_with_port(8001);
    let _m = server
        .mock("POST", "/simulate/flow")
        .with_status(500)
        .create();
    let tmp = NamedTempFile::new().unwrap();
    fs::write(tmp.path(), "test: value").unwrap();
    let result = flow_report(tmp.path().to_path_buf());
    assert!(result.is_err());
}
