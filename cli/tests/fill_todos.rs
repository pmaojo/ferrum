use ferrum_cli::commands::fill_todos_with_pattern;
use mockito::Server;
use serial_test::serial;
use std::fs;
use std::sync::{Mutex, OnceLock};
use tempfile::tempdir;

const TODO_PATTERN: &str =
    r"// \xE2\x9B\xB3 AI_FILL\[(?P<task>[^\]]+)\] --context=(?P<context>[^\n]+)";

static SERVER: OnceLock<Mutex<Server>> = OnceLock::new();

fn server() -> std::sync::MutexGuard<'static, Server> {
    SERVER
        .get_or_init(|| Mutex::new(Server::new_with_port(8001)))
        .lock()
        .unwrap()
}

#[test]
fn fill_todos_returns_err_on_invalid_regex() {
    let dir = tempdir().unwrap();
    let result = fill_todos_with_pattern(dir.path().to_path_buf(), "(");
    assert!(result.is_err());
}

#[test]
#[serial]
fn fill_todos_rewrites_marker() {
    let mut server = server();
    let _m = server
        .mock("POST", "/fill-todo")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{ "code": "fn filled() {}" }"#)
        .create();
    std::env::set_var("FERRUM_FILL_BASE", &server.url());

    let dir = tempdir().unwrap();
    let file = dir.path().join("test.rs");
    fs::write(
        &file,
        "// \u{00E2}\u{009B}\u{00B3} AI_FILL[do_it] --context=node",
    )
    .unwrap();

    fill_todos_with_pattern(dir.path().to_path_buf(), TODO_PATTERN).unwrap();
    std::env::remove_var("FERRUM_FILL_BASE");
    drop(server);

    let contents = fs::read_to_string(&file).unwrap();
    assert!(contents.contains("fn filled() {}"));
}

#[test]
#[serial]
fn fill_todos_fallback_on_empty_output() {
    let mut server = server();
    server
        .mock("POST", "/fill-todo")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{ "code": "" }"#)
        .create();

    server
        .mock("POST", "/fill-todo")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{ "code": "fn fallback() {}" }"#)
        .create();

    let _info = server.mock("POST", "/node-info").with_status(200).create();
    std::env::set_var("FERRUM_FILL_BASE", &server.url());

    let dir = tempdir().unwrap();
    let file = dir.path().join("test.rs");
    fs::write(
        &file,
        "// \u{00E2}\u{009B}\u{00B3} AI_FILL[do_it] --context=node",
    )
    .unwrap();

    std::env::set_var("FERRUM_TEST_INPUT", "extra info");
    fill_todos_with_pattern(dir.path().to_path_buf(), TODO_PATTERN).unwrap();
    std::env::remove_var("FERRUM_TEST_INPUT");
    std::env::remove_var("FERRUM_FILL_BASE");
    drop(server);

    let contents = fs::read_to_string(&file).unwrap();
    assert!(contents.contains("fn fallback() {}"));
}
