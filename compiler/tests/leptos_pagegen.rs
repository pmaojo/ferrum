use ferrum_compiler::{compile_dsl, parse_dsl_yaml, ProjectPaths};
use std::fs;

#[test]
fn leptos_pages_are_generated() {
    let yaml = r#"app:
  name: demo
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
    let generated = out
        .path()
        .join("frontend_leptos/src/pages/home_page.rs");
    assert!(generated.exists());
    let content = fs::read_to_string(generated).unwrap();
    assert!(content.contains("#[component]"));
    assert!(content.contains("pub fn HomePage"));
}
