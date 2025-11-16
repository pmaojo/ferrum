use ferrum_compiler::{Field, Generator, Module, Node, NodeType};
use std::path::PathBuf;

fn templates_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("templates")
}

fn basic_entity_module() -> Module {
    Module {
        name: "users".into(),
        nodes: vec![Node {
            id: "user".into(),
            node_type: NodeType::Entity,
            doc: None,
            description: None,
            story: None,
            input: vec![],
            output: None,
            depends_on: vec![],
            implements: None,
            view: None,
            schema: None,
            api_name: None,
            ref_node: None,
        }],
    }
}

#[test]
fn generate_entity_creates_files() {
    let dir = tempfile::tempdir().unwrap();
    let templates = templates_path();
    let generator = Generator::new(templates.as_path(), dir.path()).unwrap();

    generator.generate(&basic_entity_module()).unwrap();

    assert!(dir.path().join("shared-models/user.rs").exists());
    assert!(dir.path().join("frontend/src/schemas/user.ts").exists());
    assert!(dir.path().join("docs/db/user_entity.md").exists());
    assert!(dir.path().join("backend/src/db/models.rs").exists());
    assert!(dir.path().join("backend/src/db/schema.rs").exists());
    assert!(dir.path().join("backend/src/db/mod.rs").exists());
    let migs = std::fs::read_dir(dir.path().join("backend/migrations")).unwrap();
    assert!(migs.count() > 0);
}

#[test]
fn generate_usecase_creates_files() {
    let dir = tempfile::tempdir().unwrap();
    let templates = templates_path();
    let generator = Generator::new(templates.as_path(), dir.path()).unwrap();

    let module = Module {
        name: "users".into(),
        nodes: vec![
            Node {
                id: "getUser".into(),
                node_type: NodeType::UseCase,
                doc: None,
                description: None,
                story: None,
                input: vec![Field {
                    name: "userId".into(),
                    field_type: "uuid".into(),
                }],
                output: Some("User".into()),
                depends_on: vec!["userRepository".into()],
                implements: None,
                view: None,
                schema: None,
                api_name: None,
                ref_node: None,
            },
            Node {
                id: "userRepository".into(),
                node_type: NodeType::Adapter,
                doc: None,
                description: None,
                story: None,
                input: vec![],
                output: None,
                depends_on: vec![],
                implements: Some("userReaderPort".into()),
                view: None,
                schema: None,
                api_name: None,
                ref_node: None,
            },
            Node {
                id: "userReaderPort".into(),
                node_type: NodeType::Port,
                doc: None,
                description: None,
                story: None,
                input: vec![],
                output: None,
                depends_on: vec![],
                implements: None,
                view: None,
                schema: None,
                api_name: None,
                ref_node: None,
            },
        ],
    };

    generator.generate(&module).unwrap();

    assert!(dir.path().join("backend/handlers/users.rs").exists());
    assert!(dir.path().join("backend/routes/users.rs").exists());
    assert!(dir.path().join("frontend/src/hooks/useGetUser.ts").exists());
    assert!(dir
        .path()
        .join("frontend/src/components/GetUser.tsx")
        .exists());
    assert!(dir.path().join("backend/db/users.rs").exists());
    assert!(dir.path().join("backend/ports.rs").exists());
    assert!(dir.path().join("docs/api/getUser.md").exists());
}

#[test]
fn multiple_entities_generate_diesel_code() {
    use ferrum_compiler::{parse_dsl_yaml, project_to_modules};
    use std::fs;

    let yaml = r#"app:
  name: demo
entities:
  - name: Post
    fields:
      title: string
  - name: Comment
    fields:
      text: string
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let mut dsl = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&mut dsl).unwrap();
    let templates = templates_path();
    let generator = Generator::new(templates.as_path(), dir.path()).unwrap();
    for m in modules {
        generator.generate(&m).unwrap();
    }

    let models = fs::read_to_string(dir.path().join("backend/src/db/models.rs")).unwrap();
    let schema = fs::read_to_string(dir.path().join("backend/src/db/schema.rs")).unwrap();
    assert!(models.contains("struct Post"));
    assert!(models.contains("struct Comment"));
    assert!(schema.contains("post (id)"));
    assert!(schema.contains("comment (id)"));
}

#[test]
fn generate_forms_and_validations() {
    use ferrum_compiler::{parse_dsl_yaml, project_to_modules};
    use std::fs;

    let yaml = r#"app:
  name: demo
forms:
  - name: LoginForm
    submitTo: loginUser
    fields:
      email: string
validations:
  - name: emailIsValid
    appliesTo: demo.loginUser.email
    rule: "regex /@/"
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let mut dsl = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&mut dsl).unwrap();
    let templates = templates_path();
    let mut generator = Generator::new(templates.as_path(), dir.path()).unwrap();
    generator.set_modules(modules.clone());
    for m in &modules {
        generator.generate(m).unwrap();
    }

    assert!(dir.path().join("frontend/src/forms/LoginForm.tsx").exists());
    assert!(dir
        .path()
        .join("frontend/src/validations/emailIsValid.ts")
        .exists());
    assert!(dir
        .path()
        .join("backend/src/validations/email_is_valid.rs")
        .exists());
}

#[test]
fn generate_custom_validations_use_custom_module() {
    use ferrum_compiler::{parse_dsl_yaml, project_to_modules};
    use std::fs;

    let yaml = r#"app:
  name: demo
modules:
  user:
    usecases:
      register:
        input:
          email: string
validations:
  - name: corporateEmail
    appliesTo: user.register.email
    rule: custom
"#;
    let dir = tempfile::tempdir().unwrap();
    let file = dir.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let mut dsl = parse_dsl_yaml(&file).unwrap();
    let modules = project_to_modules(&mut dsl).unwrap();
    let templates = templates_path();
    let mut generator = Generator::new(templates.as_path(), dir.path()).unwrap();
    generator.set_modules(modules.clone());
    for m in &modules {
        generator.generate(m).unwrap();
    }

    let backend_val = fs::read_to_string(
        dir.path()
            .join("backend/src/validations/corporate_email.rs"),
    )
    .unwrap();
    assert!(backend_val.contains("pub use custom::corporate_email"));

    let frontend_val = fs::read_to_string(
        dir.path()
            .join("frontend/src/validations/corporateEmail.ts"),
    )
    .unwrap();
    assert!(frontend_val.contains("export { corporateEmail } from './custom'"));

    assert!(dir.path().join("backend/src/validations/custom.rs").exists());
    assert!(dir.path().join("backend/src/validations/mod.rs").exists());
    assert!(dir.path().join("frontend/src/validations/custom.ts").exists());
}
