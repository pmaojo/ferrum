use ferrum_compiler::{parse_yaml, validate_module, ValidationError};
use std::fs;

#[test]
fn pass_on_valid_dependency() {
    let yaml = r#"module: test
nodes:
  - id: a
    type: usecase
    depends_on: [b]
  - id: b
    type: adapter
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("test.yaml");
    fs::write(&file, yaml).unwrap();
    let module = parse_yaml(&file).unwrap();
    fs::remove_file(&file).unwrap();
    let result = validate_module(&module);
    assert!(result.is_ok());
}

#[test]
fn fails_on_missing_dependency() {
    let yaml = r#"module: test
nodes:
  - id: a
    type: usecase
    depends_on: [b]
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("test.yaml");
    fs::write(&file, yaml).unwrap();
    let module = parse_yaml(&file).unwrap();
    let err = validate_module(&module).unwrap_err();
    assert!(matches!(err, ValidationError::UnknownDependency { .. }));
}

#[test]
fn fails_on_duplicate_ids() {
    let yaml = r#"module: test
nodes:
  - id: a
    type: usecase
  - id: a
    type: adapter
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("test.yaml");
    fs::write(&file, yaml).unwrap();
    let module = parse_yaml(&file).unwrap();
    let err = validate_module(&module).unwrap_err();
    assert!(matches!(err, ValidationError::DuplicateNodeId { .. }));
}
