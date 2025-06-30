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
    policy: isAdmin
pages:
  - name: HomePage
    component: HomePage.tsx
mutations:
  - name: createUser
    handler: ./backend/mutations/create_user.rs
    entities: [User]
    authRequired: true
    policy: isAdmin
policies:
  - name: isAdmin
    guard: check_admin
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
    assert!(out.path().join("frontend/hooks/useIsAdmin.ts").exists());
    assert!(out.path().join("frontend/hooks/usePolicy.ts").exists());
    assert!(out
        .path()
        .join("frontend/components/PolicyGate.tsx")
        .exists());
    assert!(out
        .path()
        .join("frontend/components/PoliciesAdmin.tsx")
        .exists());
    assert!(out.path().join("docs/policies.md").exists());
    let res_file = out.path().join("backend/resources/store.rs");
    assert!(res_file.exists());
    let content = fs::read_to_string(res_file).unwrap();
    assert!(content.contains("aws_sdk_s3") || content.contains("redis"));
}

#[test]
fn compile_components_creates_files() {
    let yaml = r#"app:
  name: demo
components:
  - name: Card
    props:
      - name: title
        type: string
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let dsl = parse_dsl_yaml(&file).unwrap();
    let out = tempfile::tempdir().unwrap();
    let paths = ProjectPaths::new(out.path());
    compile_dsl(&dsl, &paths).unwrap();
    assert!(out.path().join("frontend/components/Card.tsx").exists());
    assert!(out.path().join("frontend/components/index.ts").exists());
}
