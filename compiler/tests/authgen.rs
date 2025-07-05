use ferrum_compiler::{parse_dsl_yaml, authgen::generate_auth, ProjectPaths};
use std::{fs, process::Command};
use tempfile::tempdir;

#[allow(deprecated)]
fn setup_auth_project() -> (std::path::PathBuf, std::path::PathBuf) {
    let yaml = "app:\n  name: demo\n  auth:\n    userEntity: User\n";
    let dir = tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let dsl = parse_dsl_yaml(&file).unwrap();
    let paths = ProjectPaths::new(dir.path());
    generate_auth(&dsl, &paths).unwrap();
    (dir.into_path(), paths.backend)
}

fn compile_and_run(backend: &std::path::Path, email: &str, password: &str) -> std::process::Output {
    let main = format!(
        r#"mod auth; 
use auth::{{login, Credentials}}; 
fn main() {{
    match login(Credentials {{ email: String::from("{email}"), password: String::from("{password}") }}) {{
        Ok(tok) => println!("{token}", tok),
        Err(_) => std::process::exit(1),
    }}
}}"#,
        email = email,
        password = password,
        token = "{}"
    );
    fs::write(backend.join("main.rs"), main).unwrap();
    let status = Command::new("rustc")
        .args(["--edition", "2021", "main.rs", "-o", "app"])
        .current_dir(backend)
        .status()
        .unwrap();
    assert!(status.success());
    Command::new(backend.join("app")).output().unwrap()
}

#[test]
fn login_succeeds_with_valid_credentials() {
    let (proj_dir, backend) = setup_auth_project();
    let out = compile_and_run(&backend, "user@example.com", "password");
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.trim() == "token123");
    fs::remove_dir_all(proj_dir).ok();
}

#[test]
fn login_fails_with_wrong_credentials() {
    let (proj_dir, backend) = setup_auth_project();
    let out = compile_and_run(&backend, "user@example.com", "wrong");
    assert!(!out.status.success());
    fs::remove_dir_all(proj_dir).ok();
}
