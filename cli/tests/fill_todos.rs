use ferrum_cli::commands::fill_todos_with_pattern;
use mockito::Server;
use serial_test::serial;
use std::fs;
use tempfile::tempdir;

#[test]
fn fill_todos_returns_err_on_invalid_regex() {
    let dir = tempdir().unwrap();
    let result = fill_todos_with_pattern(dir.path().to_path_buf(), "(", "http://localhost:0");
    assert!(result.is_err());
}

#[test]
#[serial]
fn fill_todos_uses_custom_url() {
    let mut server = Server::new();
    let _m_fill = server
        .mock("POST", "/fill-todo")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{ "code": "// done" }"#)
        .create();
    let _m_info = server.mock("POST", "/node-info").with_status(200).create();

    let dir = tempdir().unwrap();
    let file = dir.path().join("test.rs");
    fs::write(&file, "// AI_FILL[test] --context=NODE").unwrap();

    const SIMPLE_PATTERN: &str = r"AI_FILL\[(?P<task>[^\]]+)\] --context=(?P<context>[^\n]+)";
    fill_todos_with_pattern(dir.path().to_path_buf(), SIMPLE_PATTERN, &server.url()).unwrap();
    let contents = fs::read_to_string(&file).unwrap();
    assert!(contents.contains("// done"));
}
