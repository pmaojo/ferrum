use ferrum_cli::commands::{make_entity, make_job, make_policy, make_resource, make_scaffold};
use serial_test::serial;
use std::{env, fs};
use tempfile::tempdir;

fn write_base_dsl(path: &std::path::Path) {
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, "app:\n  name: demo\n").unwrap();
}

fn templates_path() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("templates")
}

#[test]
#[serial]
fn make_resource_adds_to_dsl_and_generates_file() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(dir.path()).unwrap();

    let file = std::path::PathBuf::from("gen/example.yaml");
    write_base_dsl(&file);

    make_resource("RedisCache".to_string(), "redis".to_string(), file.clone()).unwrap();

    let dsl = ferrum_compiler::parse_dsl_yaml(&file).unwrap();
    assert!(dsl.resources.iter().any(|r| r.name == "RedisCache" && r.resource_type == "redis"));
    assert!(std::path::Path::new("backend/resources/rediscache.rs").exists());

    // Re-running with the same name must fail rather than silently duplicate.
    assert!(make_resource("RedisCache".to_string(), "redis".to_string(), file).is_err());

    env::set_current_dir(cwd).unwrap();
}

#[test]
#[serial]
fn make_job_adds_to_dsl_and_generates_file() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(dir.path()).unwrap();

    let file = std::path::PathBuf::from("gen/example.yaml");
    write_base_dsl(&file);

    make_job(
        "SendDigest".to_string(),
        "0 9 * * MON".to_string(),
        None,
        file.clone(),
    )
    .unwrap();

    let dsl = ferrum_compiler::parse_dsl_yaml(&file).unwrap();
    assert!(dsl.jobs.iter().any(|j| j.name == "SendDigest" && j.schedule == "0 9 * * MON"));
    assert!(std::path::Path::new("backend/jobs/send_digest.rs").exists());

    env::set_current_dir(cwd).unwrap();
}

#[test]
#[serial]
fn make_policy_adds_to_dsl_and_generates_file() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(dir.path()).unwrap();

    let file = std::path::PathBuf::from("gen/example.yaml");
    write_base_dsl(&file);

    make_policy("AdminOnly".to_string(), "role:admin".to_string(), file.clone()).unwrap();

    let dsl = ferrum_compiler::parse_dsl_yaml(&file).unwrap();
    assert!(dsl.policies.iter().any(|p| p.name == "AdminOnly" && p.guard == "role:admin"));
    assert!(std::path::Path::new("backend/policies/adminonly.rs").exists());

    env::set_current_dir(cwd).unwrap();
}

#[test]
#[serial]
fn make_entity_adds_to_dsl_and_generates_real_fields() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(dir.path()).unwrap();

    let file = std::path::PathBuf::from("gen/example.yaml");
    write_base_dsl(&file);

    make_entity(
        "Post".to_string(),
        vec!["title:string".to_string(), "views:int".to_string()],
        None,
        file.clone(),
        Some(templates_path()),
    )
    .unwrap();

    let dsl = ferrum_compiler::parse_dsl_yaml(&file).unwrap();
    assert!(dsl.entities.iter().any(|e| e.name == "Post"
        && e.fields.get("title").map(String::as_str) == Some("string")
        && e.fields.get("views").map(String::as_str) == Some("int")));

    let model = fs::read_to_string("shared-models/post.rs").unwrap();
    assert!(model.contains("pub title: String,"));
    assert!(model.contains("pub views: i32,"));

    let schema = fs::read_to_string("frontend/src/schemas/post.ts").unwrap();
    assert!(schema.contains("title: z.string()"));
    assert!(schema.contains("views: z.number()"));

    // Rejects a bad field spec instead of writing a half-formed entity.
    assert!(make_entity(
        "Broken".to_string(),
        vec!["not-a-pair".to_string()],
        None,
        file.clone(),
        Some(templates_path()),
    )
    .is_err());

    // And refuses a duplicate name.
    assert!(make_entity(
        "Post".to_string(),
        vec![],
        None,
        file,
        Some(templates_path()),
    )
    .is_err());

    env::set_current_dir(cwd).unwrap();
}

#[test]
#[serial]
fn make_scaffold_wires_entity_mutation_and_form_together() {
    let dir = tempdir().unwrap();
    let cwd = env::current_dir().unwrap();
    env::set_current_dir(dir.path()).unwrap();

    let file = std::path::PathBuf::from("gen/example.yaml");
    write_base_dsl(&file);

    make_scaffold(
        "Post".to_string(),
        vec!["title:string".to_string(), "body:text".to_string()],
        file.clone(),
        Some(templates_path()),
    )
    .unwrap();

    let dsl = ferrum_compiler::parse_dsl_yaml(&file).unwrap();
    assert!(dsl.entities.iter().any(|e| e.name == "Post"));
    assert!(dsl.mutations.iter().any(|m| m.name == "createPost" && m.entities == vec!["Post".to_string()]));
    assert!(dsl.forms.iter().any(|f| f.name == "PostForm" && f.submit_to == "createPost"));

    assert!(std::path::Path::new("shared-models/post.rs").exists());
    assert!(std::path::Path::new("backend/mutations/create_post.rs").exists());
    assert!(std::path::Path::new("frontend/hooks/useCreatePost.ts").exists());
    assert!(std::path::Path::new("frontend/src/forms/PostForm.tsx").exists());

    // The form must import the hook the mutation step actually generated -
    // both the name (PascalCase, matching Inflector, not Tera's naive
    // capitalize) and the relative path.
    let form = fs::read_to_string("frontend/src/forms/PostForm.tsx").unwrap();
    assert!(form.contains("import { useCreatePost } from \"../../hooks/useCreatePost\";"));

    env::set_current_dir(cwd).unwrap();
}
