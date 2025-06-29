use ferrum_compiler::{parse_dsl_yaml, project_to_modules};
use std::path::PathBuf;

fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("gen")
        .join(name)
}

#[test]
fn it_expands_auth_feature() {
    let dsl = parse_dsl_yaml(fixture_path("auth_example.yaml")).unwrap();
    let modules = project_to_modules(&dsl);
    assert!(modules.iter().any(|m| m.name == "auth"));
    assert!(modules
        .iter()
        .flat_map(|m| &m.nodes)
        .any(|n| n.id == "authService"));
}
