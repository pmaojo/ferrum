use ferrum_compiler::{parse_dsl_yaml, project_to_modules};
use std::path::PathBuf;

/// `CARGO_MANIFEST_DIR` is `<root>/apps/compiler`; the DSL fixtures live in
/// `<root>/packages/gen`, two levels up.
fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|apps| apps.parent())
        .expect("compiler crate sits at <root>/apps/compiler")
        .join("packages")
        .join("gen")
        .join(name)
}

#[test]
fn it_expands_auth_feature() {
    let mut dsl = parse_dsl_yaml(fixture_path("auth_example.yaml")).unwrap();
    let modules = project_to_modules(&mut dsl).unwrap();
    assert!(modules.iter().any(|m| m.name == "auth"));
    assert!(modules
        .iter()
        .flat_map(|m| &m.nodes)
        .any(|n| n.id == "authService"));
}

#[test]
fn cron_feature_injects_example_job() {
    let yaml = "app:\n  name: demo\n  features: [cron]\n";
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    std::fs::write(&file, yaml).unwrap();
    let mut dsl = parse_dsl_yaml(&file).unwrap();
    let _modules = project_to_modules(&mut dsl).unwrap();
    assert!(dsl.jobs.iter().any(|j| j.name == "example_job"));
}

#[test]
fn realtime_sse_feature_adds_module_and_route() {
    let yaml = "app:\n  name: demo\n  features: [realtime_sse]\n";
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    std::fs::write(&file, yaml).unwrap();
    let mut dsl = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&mut dsl).unwrap();
    assert!(modules.iter().any(|m| m.name == "realtime_sse"));
    assert!(dsl.routes.iter().any(|r| r.path == "/events"));
}

#[test]
fn uploads_feature_injects_default_upload() {
    let yaml = "app:\n  name: demo\n  features: [uploads]\n";
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    std::fs::write(&file, yaml).unwrap();
    let mut dsl = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&mut dsl).unwrap();
    assert!(modules.iter().any(|m| m.name == "uploads"));
    assert!(modules
        .iter()
        .flat_map(|m| &m.nodes)
        .any(|n| n.node_type == ferrum_compiler::NodeType::Upload));
}
