use ferrum_cli::commands::{init, Frontend};
use tempfile::tempdir;
use std::env;
use serial_test::serial;

#[test]
#[serial]
fn init_creates_leptos_template_from_anywhere() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(&dir).unwrap();

    init(
        "demo".to_string(),
        false, false, false, false, false, false,
        Frontend::LeptosCsr,
        false, false, false,
    ).unwrap();

    env::set_current_dir(&cwd).unwrap();

    assert!(dir.path().join("demo/frontend_leptos/Cargo.toml").exists());
}
