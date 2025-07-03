use ferrum_compiler::{compile_dsl, parse_dsl_yaml, ProjectPaths};
use std::fs;

#[test]
fn leptos_routes_are_generated() {
    let yaml = r#"app:
  name: demo
routes:
  - name: home
    path: /
    to: HomePage
pages:
  - name: HomePage
    component: home.rs
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let dsl = parse_dsl_yaml(&file).unwrap();
    let out = tempfile::tempdir().unwrap();
    let paths = ProjectPaths::new(out.path());
    fs::create_dir_all(out.path().join("frontend_leptos")).unwrap();
    compile_dsl(&dsl, &paths).unwrap();
    let generated = out.path().join("frontend_leptos/src/routes.rs");
    assert!(generated.exists());
    let content = fs::read_to_string(generated).unwrap();
    assert!(content.contains("HomePage"));
    assert!(content.contains("\"/\""));
}
