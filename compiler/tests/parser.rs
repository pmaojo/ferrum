use ferrum_compiler::parse_yaml;
use std::fs;

#[test]
fn parse_simple_yaml() {
    let yaml = r#"module: test
nodes:
  - id: ping
    type: usecase
    description: Simple ping use case
    story: |
      As a user
      I want to ping the service
      So that I know it is alive
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("test.yaml");
    fs::write(&file, yaml).unwrap();
    let module = parse_yaml(&file).unwrap();
    assert_eq!(module.name, "test");
    assert_eq!(module.nodes.len(), 1);
    assert_eq!(module.nodes[0].id, "ping");
    assert_eq!(
        module.nodes[0].description.as_deref(),
        Some("Simple ping use case")
    );
    assert!(module.nodes[0]
        .story
        .as_ref()
        .unwrap()
        .contains("ping the service"));
}
