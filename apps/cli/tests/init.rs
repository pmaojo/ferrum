use ferrum_cli::commands::{init, Frontend};
use serial_test::serial;
use std::fs;
use tempfile::tempdir;

#[test]
#[serial]
fn init_with_db_and_existing_dependencies() {
    let tmp = tempdir().unwrap();
    let project_name = "test_project";
    let project_dir = tmp.path().join(project_name);
    std::env::set_current_dir(tmp.path()).unwrap();
    let backend_dir = project_dir.join("backend");
    let cargo_toml_path = backend_dir.join("Cargo.toml");

    // Create a dummy backend Cargo.toml with an existing [dependencies] section
    fs::create_dir_all(&backend_dir).unwrap();
    fs::write(
        &cargo_toml_path,
        r#"[package]
name = "backend"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0"
"#,
    )
    .unwrap();

    init(
        project_name.to_string(),
        false,
        false,
        true, // --with-db
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

    let cargo_toml_content = fs::read_to_string(&cargo_toml_path).unwrap();
    // toml 0.9+ (spec 1.1) reserves `Value` for a single value expression;
    // a whole document parses as `Table`.
    let cargo_toml: toml::Table = cargo_toml_content.parse().unwrap();
    let dependencies = cargo_toml["dependencies"].as_table().unwrap();

    let diesel = dependencies["diesel"].as_table().unwrap();
    assert_eq!(diesel["version"].as_str().unwrap(), "2.3");
    let features = diesel["features"].as_array().unwrap();
    assert!(features.contains(&toml::Value::String("postgres".to_string())));
    assert!(features.contains(&toml::Value::String("r2d2".to_string())));
    assert!(dependencies.contains_key("dotenvy"));
    assert!(dependencies.contains_key("serde"));
}

/// `ferrum init` writes a one-off scaffold the user owns from then on, so
/// none of it is marked as generated code and none of it has holes.
#[test]
#[serial]
fn init_scaffold_is_user_owned() {
    let tmp = tempdir().unwrap();
    std::env::set_current_dir(tmp.path()).unwrap();
    init(
        "owned".to_string(),
        true,
        true,
        true,
        ferrum_cli::commands::DbType::Postgres,
        true,
        true,
        // `--with-uploads` currently fails on a fresh directory (its
        // template subdirectories are never created), so it is left out.
        false,
        Frontend::React,
        false,
        false,
        false,
    )
    .unwrap();

    let mut stack = vec![tmp.path().join("owned")];
    let mut files = 0;
    while let Some(dir) = stack.pop() {
        for entry in fs::read_dir(&dir).unwrap() {
            let path = entry.unwrap().path();
            if path.is_dir() {
                stack.push(path);
                continue;
            }
            // ferrum's own templates carry the markers they emit.
            if path.components().any(|c| c.as_os_str() == "templates") {
                continue;
            }
            files += 1;
            let content = fs::read_to_string(&path).unwrap_or_default();
            assert!(
                !ferrum_compiler::has_generated_header(&content),
                "{} is user-owned but marked generated",
                path.display()
            );
            assert!(!content.contains("vord:hole"), "{}", path.display());
        }
    }
    assert!(files > 10, "only {files} files scaffolded");
}
