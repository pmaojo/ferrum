use ferrum_compiler::{parse_dsl_yaml, parse_yaml};
use std::fs;

#[test]
fn parse_simple_yaml() {
    let yaml = r#"module: test
nodes:
  - id: ping
    type: usecase
    description: Simple ping use case
    story: |
      As a user
      I want to ping the service
      So that I know it is alive
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("test.yaml");
    fs::write(&file, yaml).unwrap();
    let module = parse_yaml(&file).unwrap();
    assert_eq!(module.name, "test");
    assert_eq!(module.nodes.len(), 1);
    assert_eq!(module.nodes[0].id, "ping");
    assert_eq!(
        module.nodes[0].description.as_deref(),
        Some("Simple ping use case")
    );
    assert!(module.nodes[0]
        .story
        .as_ref()
        .unwrap()
        .contains("ping the service"));
}

#[test]
fn parse_dsl_format() {
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
    assert_eq!(project.app.name, "demo");
    assert!(project.modules.contains_key("user"));
    let user = project.modules.get("user").unwrap();
    assert!(user.entity.is_some());
    assert!(user.usecases.contains_key("hello"));
}

#[test]
fn parse_extended_format() {
    let yaml = r#"app:
  name: ferrusBlog
  title: "Blog Ferrus"
  version: "0.7.0"
  auth:
    userEntity: User
    methods:
      - email
routes:
  - name: Root
    path: /
    to: HomePage
    authRequired: false
pages:
  - name: HomePage
    component: ./frontend/pages/Home.tsx
queries:
  - name: getPosts
    handler: ./backend/queries/getPosts.rs
    entities: [Post]
entities:
  - name: User
    fields:
      id: int
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("ext.yaml");
    fs::write(&file, yaml).unwrap();
    let project = parse_dsl_yaml(&file).unwrap();
    assert_eq!(project.app.title.as_deref(), Some("Blog Ferrus"));
    assert_eq!(project.routes.len(), 1);
    assert_eq!(project.pages.len(), 1);
    assert_eq!(project.queries.len(), 1);
    assert_eq!(project.entities.len(), 1);
    assert!(project.app.auth.is_some());
}

#[test]
fn parse_policies_and_resources() {
    let yaml = r#"app:
  name: demo
policies:
  - name: isAdmin
    guard: check_admin
resources:
  - name: queue
    type: rabbitmq
    config:
      url: amqp://localhost
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("extra.yaml");
    fs::write(&file, yaml).unwrap();
    let project = parse_dsl_yaml(&file).unwrap();
    assert_eq!(project.policies.len(), 1);
    assert_eq!(project.resources.len(), 1);
}
