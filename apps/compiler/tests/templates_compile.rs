use ferrum_compiler::{
    compile_dsl, parse_dsl_yaml, project_to_modules, validate_features, validate_modules,
    validate_validations, Generator, ProjectPaths, ValidationError,
};
use std::fs;
use std::path::PathBuf;

fn templates_path() -> PathBuf {
    workspace_root().join("templates")
}

/// `CARGO_MANIFEST_DIR` is `<root>/apps/compiler`, so the workspace root —
/// where `templates/` lives — is two levels up, not one.
fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|apps| apps.parent())
        .expect("compiler crate sits at <root>/apps/compiler")
        .to_path_buf()
}

#[test]
fn generated_handler_and_hook_signatures() {
    let yaml = r#"app:
  name: demo
modules:
  users:
    entity:
      fields:
        email: string
    usecases:
      listUsers:
        input:
          limit: int
        output: User
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let mut dsl = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&mut dsl).unwrap();
    validate_modules(&modules).unwrap();
    validate_features(&dsl, &modules).unwrap();
    validate_validations(&dsl, &modules).unwrap();

    let templates = templates_path();
    let out = tempfile::tempdir().unwrap();
    let mut generator = Generator::new(templates.as_path(), out.path()).unwrap();
    generator.set_modules(modules.clone());
    for m in &modules {
        generator.generate(m).unwrap();
    }
    let paths = ProjectPaths::new(out.path());
    compile_dsl(&dsl, &paths).unwrap();

    let handler = fs::read_to_string(out.path().join("backend/handlers/users.rs")).unwrap();
    assert!(handler.contains("pub async fn listUsers_handler"));
    let hook = fs::read_to_string(out.path().join("frontend/src/hooks/useListUsers.ts")).unwrap();
    assert!(hook.contains("export const useListusers"));
}

#[test]
fn generated_query_contains_functions() {
    let yaml = r#"app:
  name: demo
queries:
  - name: getPosts
    handler: ./backend/queries/getPosts.rs
    entities: [Post]
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let dsl = parse_dsl_yaml(&file).unwrap();
    let out = tempfile::tempdir().unwrap();
    let paths = ProjectPaths::new(out.path());
    compile_dsl(&dsl, &paths).unwrap();

    let rust_file = out.path().join("backend/queries/get_posts.rs");
    let rust_content = fs::read_to_string(rust_file).unwrap();
    assert!(rust_content.contains("pub async fn get_posts"));
    let ts_file = out.path().join("frontend/hooks/useGetPosts.ts");
    let ts_content = fs::read_to_string(ts_file).unwrap();
    assert!(ts_content.contains("function useGetPosts()"));
}

#[test]
fn invalid_dsl_reports_error() {
    let yaml = r#"app:
  name: demo
modules:
  users:
    usecases:
      getUser:
        steps:
          - missingRepo
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let mut dsl = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&mut dsl).unwrap();
    let err = validate_modules(&modules).unwrap_err();
    assert!(matches!(err, ValidationError::UnknownDependency { .. }));
}

