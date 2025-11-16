use ferrum_engine::plugins::utils::{copy_if_missing, ensure_dep};
use std::fs;
use tempfile::tempdir;

#[test]
fn copy_if_missing_creates_and_preserves_file() {
    let dir = tempdir().unwrap();
    let file = dir.path().join("test.txt");
    copy_if_missing("hello", &file).unwrap();
    assert_eq!(fs::read_to_string(&file).unwrap(), "hello");

    fs::write(&file, "exists").unwrap();
    copy_if_missing("new", &file).unwrap();
    assert_eq!(fs::read_to_string(&file).unwrap(), "exists");
}

#[test]
fn ensure_dep_appends_once() {
    let dir = tempdir().unwrap();
    let backend = dir.path().join("backend");
    fs::create_dir_all(&backend).unwrap();
    fs::write(backend.join("Cargo.toml"), "[dependencies]\n").unwrap();

    let cwd = std::env::current_dir().unwrap();
    std::env::set_current_dir(dir.path()).unwrap();
    ensure_dep("demo-crate", "1.0").unwrap();
    ensure_dep("demo-crate", "1.0").unwrap();
    std::env::set_current_dir(cwd).unwrap();

    let content = fs::read_to_string(dir.path().join("backend/Cargo.toml")).unwrap();
    assert_eq!(content.matches("demo-crate").count(), 1);
}
