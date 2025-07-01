use ferrum_compiler::{
    parse_dsl_yaml, parse_yaml, project_to_modules, validate_module, validate_validations,
    ValidationError,
};
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

#[test]
fn fails_on_unknown_validation_target() {
    let yaml = r#"app:
  name: demo
forms:
  - name: LoginForm
    submitTo: loginUser
    fields:
      email: string
validations:
  - name: checkEmail
    appliesTo: demo.loginUser.missing
    rule: "regex /@/"
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    std::fs::write(&file, yaml).unwrap();
    let mut dsl = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&mut dsl);
    let err = validate_validations(&dsl, &modules).unwrap_err();
    assert!(matches!(
        err,
        ValidationError::UnknownValidationTarget { .. }
    ));
}
