use ferrum_compiler::{parse_dsl_yaml, parse_yaml};
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

#[test]
fn parse_dsl_format() {
    let yaml = r#"app:
  name: demo
modules:
  user:
    entity:
      fields:
        name: string
    usecases:
      hello:
        input:
          name: string
        output: String
        steps:
          - say_hi
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let project = parse_dsl_yaml(&file).unwrap();
    assert_eq!(project.app.name, "demo");
    assert!(project.modules.contains_key("user"));
    let user = project.modules.get("user").unwrap();
    assert!(user.entity.is_some());
    assert!(user.usecases.contains_key("hello"));
}
