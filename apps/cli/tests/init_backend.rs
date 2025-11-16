use ferrum_cli::commands::{init, Frontend};
use serial_test::serial;
use std::env;
use std::fs;
use std::process::Command;
use tempfile::tempdir;

/// Ensure that `init` generates a backend Cargo.toml which builds with all IoT features.
#[test]
#[serial]
fn init_backend_builds_with_features() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(&dir).unwrap();

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

    // Provide a minimal stub for the optional `ethercat_rs` crate so the build
    // succeeds even though the real library isn't available on crates.io.
    let stub = dir.path().join("ethercat_rs");
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
    let backend_toml = dir.path().join("demo/backend/Cargo.toml");
    let mut append = std::fs::OpenOptions::new()
        .append(true)
        .open(&backend_toml)
        .unwrap();
    use std::io::Write as _;
    writeln!(
        append,
        "\n[patch.crates-io]\nethercat_rs = {{ path = \"{}\" }}",
        stub.display()
    )
    .unwrap();

    let cargo_toml = fs::read_to_string(dir.path().join("demo/backend/Cargo.toml")).unwrap();
    assert!(cargo_toml.contains("hal = [\"dep:embedded-hal\"]"));
    assert!(cargo_toml.contains("rppal = [\"dep:rppal\"]"));
    assert!(cargo_toml.contains("mqtt = [\"dep:rumqttc\"]"));
    assert!(cargo_toml.contains("ethercat = [\"dep:ethercat-rs\"]"));

    let status = Command::new("cargo")
        .arg("build")
        .arg("--manifest-path")
        .arg(dir.path().join("demo/backend/Cargo.toml"))
        .arg("--features")
        .arg("hal,rppal,mqtt,ethercat")
        .status()
        .expect("failed to run cargo build");

    env::set_current_dir(&cwd).unwrap();

    assert!(status.success());
}
