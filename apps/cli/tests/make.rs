use ferrum_cli::commands::{make_job, make_policy, make_resource};
use serial_test::serial;
use std::{env, fs};
use tempfile::tempdir;

fn write_base_dsl(path: &std::path::Path) {
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, "app:\n  name: demo\n").unwrap();
}

#[test]
#[serial]
fn make_resource_adds_to_dsl_and_generates_file() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(dir.path()).unwrap();

    let file = std::path::PathBuf::from("gen/example.yaml");
    write_base_dsl(&file);

    make_resource("RedisCache".to_string(), "redis".to_string(), file.clone()).unwrap();

    let dsl = ferrum_compiler::parse_dsl_yaml(&file).unwrap();
    assert!(dsl.resources.iter().any(|r| r.name == "RedisCache" && r.resource_type == "redis"));
    assert!(std::path::Path::new("backend/resources/rediscache.rs").exists());

    // Re-running with the same name must fail rather than silently duplicate.
    assert!(make_resource("RedisCache".to_string(), "redis".to_string(), file).is_err());

    env::set_current_dir(cwd).unwrap();
}

#[test]
#[serial]
fn make_job_adds_to_dsl_and_generates_file() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(dir.path()).unwrap();

    let file = std::path::PathBuf::from("gen/example.yaml");
    write_base_dsl(&file);

    make_job(
        "SendDigest".to_string(),
        "0 9 * * MON".to_string(),
        None,
        file.clone(),
    )
    .unwrap();

    let dsl = ferrum_compiler::parse_dsl_yaml(&file).unwrap();
    assert!(dsl.jobs.iter().any(|j| j.name == "SendDigest" && j.schedule == "0 9 * * MON"));
    assert!(std::path::Path::new("backend/jobs/send_digest.rs").exists());

    env::set_current_dir(cwd).unwrap();
}

#[test]
#[serial]
fn make_policy_adds_to_dsl_and_generates_file() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(dir.path()).unwrap();

    let file = std::path::PathBuf::from("gen/example.yaml");
    write_base_dsl(&file);

    make_policy("AdminOnly".to_string(), "role:admin".to_string(), file.clone()).unwrap();

    let dsl = ferrum_compiler::parse_dsl_yaml(&file).unwrap();
    assert!(dsl.policies.iter().any(|p| p.name == "AdminOnly" && p.guard == "role:admin"));
    assert!(std::path::Path::new("backend/policies/adminonly.rs").exists());

    env::set_current_dir(cwd).unwrap();
}
