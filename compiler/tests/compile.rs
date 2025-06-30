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

#[test]
fn compile_dsl_creates_mutation_and_routes() {
    let yaml = r#"app:
  name: demo
routes:
  - name: home
    path: /
    to: HomePage
    authRequired: false
pages:
  - name: HomePage
    component: HomePage.tsx
mutations:
  - name: createUser
    handler: ./backend/mutations/create_user.rs
    entities: [User]
    authRequired: true
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let dsl = parse_dsl_yaml(&file).unwrap();
    let out = tempfile::tempdir().unwrap();
    let paths = ProjectPaths::new(out.path());
    compile_dsl(&dsl, &paths).unwrap();
    assert!(out.path().join("backend/mutations/create_user.rs").exists());
    assert!(out.path().join("frontend/hooks/useCreateUser.ts").exists());
    assert!(out.path().join("frontend/routes.tsx").exists());
}

#[test]
fn compile_policies_and_resources() {
    let yaml = r#"app:
  name: demo
policies:
  - name: isAdmin
    guard: check_admin
resources:
  - name: store
    type: s3
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let dsl = parse_dsl_yaml(&file).unwrap();
    let out = tempfile::tempdir().unwrap();
    let paths = ProjectPaths::new(out.path());
    compile_dsl(&dsl, &paths).unwrap();
    assert!(out.path().join("backend/policies/isadmin.rs").exists());
    assert!(out.path().join("backend/resources/store.rs").exists());
}
