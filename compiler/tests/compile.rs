use ferrum_compiler::{compile_dsl, parse_dsl_yaml, ProjectPaths};
use std::fs;

#[test]
fn compile_dsl_creates_query_files() {
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
    assert!(out.path().join("backend/queries/get_posts.rs").exists());
    assert!(out.path().join("frontend/hooks/useGetPosts.ts").exists());
}
