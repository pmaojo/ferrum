use ferrum_cli::commands::{init, Frontend};
use serial_test::serial;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use tempfile::tempdir;

/// Scaffold a project into the current directory. `init` writes relative to the process CWD, so
/// the caller must have switched into `dir` first.
///
/// Returns the path of the generated backend manifest.
fn scaffold_project(dir: &Path) -> PathBuf {
    init(
        "demo".to_string(),
        false,
        false,
        false,
        ferrum_cli::commands::DbType::Postgres,
        false,
        false,
        false,
        Frontend::React,
        false,
        false,
        false,
    )
    .unwrap();

    dir.join("demo/backend/Cargo.toml")
}

/// `init` must emit a backend manifest carrying every IoT feature flag.
#[test]
#[serial]
fn init_backend_declares_iot_features() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(&dir).unwrap();

    let backend_toml = scaffold_project(dir.path());
    let cargo_toml = fs::read_to_string(&backend_toml).unwrap();

    env::set_current_dir(&cwd).unwrap();

    assert!(cargo_toml.contains("hal = [\"dep:embedded-hal\"]"));
    assert!(cargo_toml.contains("rppal = [\"dep:rppal\"]"));
    assert!(cargo_toml.contains("mqtt = [\"dep:rumqttc\"]"));
    assert!(cargo_toml.contains("ethercat = []"));
}

/// The full-feature build is only meaningful on Linux: `rppal` drives the
/// Raspberry Pi GPIO and the `hal`/`ethercat` features sit on embedded Linux
/// APIs (epoll, eventfd, termios), so this cannot compile on macOS or Windows.
/// Gating it here keeps `cargo test` green on developer machines instead of
/// failing on a platform the code was never meant for.
#[cfg(target_os = "linux")]
#[test]
#[serial]
fn init_backend_builds_with_iot_features() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(&dir).unwrap();

    let backend_toml = scaffold_project(dir.path());

    let status = std::process::Command::new("cargo")
        .arg("check")
        .arg("--manifest-path")
        .arg(&backend_toml)
        .arg("--features")
        .arg("hal,rppal,mqtt,ethercat")
        .status()
        .expect("failed to run cargo check");

    env::set_current_dir(&cwd).unwrap();

    assert!(status.success());
}
