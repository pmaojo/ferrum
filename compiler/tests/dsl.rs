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
forms:
  - name: LoginForm
    submitTo: loginUser
    fields:
      email: string
validations:
  - name: emailIsValid
    appliesTo: user.register.email
    rule: "regex /@/"
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let project = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&project);
    assert_eq!(modules.len(), 3);
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

    // Additional modules for forms and validations
    assert!(modules.iter().any(|m| m.name == "forms"));
    assert!(modules.iter().any(|m| m.name == "validations"));
}

#[test]
fn forms_and_validations_nodes_present() {
    let yaml = r#"app:
  name: demo
forms:
  - name: LoginForm
    submitTo: login
    fields:
      email: string
validations:
  - name: emailIsValid
    appliesTo: demo.login.email
    rule: must_match
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let project = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&project);
    assert!(modules.iter().any(|m| m.name == "forms"));
    assert!(modules.iter().any(|m| m.name == "validations"));
    let all_nodes: Vec<_> = modules.iter().flat_map(|m| &m.nodes).collect();
    assert!(all_nodes
        .iter()
        .any(|n| matches!(n.node_type, ferrum_compiler::NodeType::Form)));
    assert!(all_nodes
        .iter()
        .any(|n| matches!(n.node_type, ferrum_compiler::NodeType::Validation)));
}

#[test]
fn uploads_nodes_present() {
    let yaml = r#"app:
  name: demo
uploads:
  - name: profilePic
    path: /uploads/users
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let project = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&project);
    assert!(modules.iter().any(|m| m.name == "uploads"));
    let all_nodes: Vec<_> = modules.iter().flat_map(|m| &m.nodes).collect();
    assert!(all_nodes
        .iter()
        .any(|n| matches!(n.node_type, ferrum_compiler::NodeType::Upload)));
}

#[test]
fn iot_section_parsed() {
    let yaml = r#"app:
  name: demo
iot:
  - name: sensor
    code: |
      fn read() {}
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let project = parse_dsl_yaml(&file).unwrap();
    assert_eq!(project.iot.len(), 1);
    assert_eq!(project.iot[0].name, "sensor");
}
