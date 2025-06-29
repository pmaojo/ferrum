use ferrum_compiler::{parse_dsl_yaml, project_to_modules};
use std::fs;

#[test]
fn convert_dsl_to_modules() {
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
    let modules = project_to_modules(&project);
    assert_eq!(modules.len(), 1);
    let m = &modules[0];
    assert_eq!(m.name, "user");
    assert_eq!(m.nodes.len(), 2); // entity + usecase
    assert!(m
        .nodes
        .iter()
        .any(|n| n.node_type == ferrum_compiler::NodeType::Entity));
    assert!(m
        .nodes
        .iter()
        .any(|n| n.node_type == ferrum_compiler::NodeType::UseCase));
}
