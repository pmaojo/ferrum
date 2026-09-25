use ferrum_cli::commands::{init, Frontend};
use serial_test::serial;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use tempfile::tempdir;

/// Scaffold a project into the current directory and patch in a stub for the
/// optional `ethercat_rs` crate, so the dependency resolves without the real
/// (crates.io-absent) library. `init` writes relative to the process CWD, so
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

    let stub = dir.join("ethercat_rs");
    fs::create_dir(&stub).unwrap();
    fs::write(
        stub.join("Cargo.toml"),
        "[package]\nname = \"ethercat_rs\"\nversion = \"0.2.0\"\nedition = \"2021\"\n\n[lib]\npath = \"lib.rs\"\n",
    )
    .unwrap();
    fs::write(
        stub.join("lib.rs"),
        "pub struct Master; impl Default for Master { fn default() -> Self { Self } }",
    )
    .unwrap();

    let backend_toml = dir.join("demo/backend/Cargo.toml");
    {
        use std::io::Write as _;
        let mut append = fs::OpenOptions::new()
            .append(true)
            .open(&backend_toml)
            .unwrap();
        writeln!(
            append,
            "\n[patch.crates-io]\nethercat_rs = {{ path = \"{}\" }}",
            stub.display()
        )
        .unwrap();
    }
    backend_toml
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
    assert!(cargo_toml.contains("ethercat = [\"dep:ethercat-rs\"]"));
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
        .arg("build")
        .arg("--manifest-path")
        .arg(&backend_toml)
        .arg("--features")
        .arg("hal,rppal,mqtt,ethercat")
        .status()
        .expect("failed to run cargo build");

    env::set_current_dir(&cwd).unwrap();

    assert!(status.success());
}
