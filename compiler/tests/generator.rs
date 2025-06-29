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
            description: None,
            story: None,
            input: vec![],
            output: None,
            depends_on: vec![],
            implements: None,
            view: None,
            schema: None,
            api_name: None,
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
            },
            Node {
                id: "userRepository".into(),
                node_type: NodeType::Adapter,
                description: None,
                story: None,
                input: vec![],
                output: None,
                depends_on: vec![],
                implements: Some("userReaderPort".into()),
                view: None,
                schema: None,
                api_name: None,
            },
            Node {
                id: "userReaderPort".into(),
                node_type: NodeType::Port,
                description: None,
                story: None,
                input: vec![],
                output: None,
                depends_on: vec![],
                implements: None,
                view: None,
                schema: None,
                api_name: None,
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
