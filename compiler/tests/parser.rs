use ferrum_compiler::parse_yaml;
use std::fs;

#[test]
fn parse_simple_yaml() {
    let yaml = r#"module: test
nodes:
  - id: ping
    type: usecase
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("test.yaml");
    fs::write(&file, yaml).unwrap();
    let module = parse_yaml(&file).unwrap();
    assert_eq!(module.name, "test");
    assert_eq!(module.nodes.len(), 1);
    assert_eq!(module.nodes[0].id, "ping");
}
