use ferrum_compiler::{compile_dsl, ProjectPaths};
use ferrum_engine::plugins::{GraphQLPlugin, PluginManager};
use ferrum_shared_models::FerrumDsl;
use tempfile::tempdir;

#[test]
fn compile_after_plugin_creates_schema() {
    let yaml = "app:\n  name: demo\n";
    let mut dsl: FerrumDsl = serde_yaml::from_str(yaml).unwrap();
    let mut manager = PluginManager::new();
    manager.register(GraphQLPlugin);
    manager.extend_dsl_all(&mut dsl).unwrap();

    let dir = tempdir().unwrap();
    let paths = ProjectPaths::new(dir.path());
    compile_dsl(&dsl, &paths).unwrap();

    let cwd = std::env::current_dir().unwrap();
    std::env::set_current_dir(dir.path()).unwrap();
    manager.compile_all().unwrap();
    std::env::set_current_dir(cwd).unwrap();

    assert!(dir.path().join("backend/src/graphql_schema.rs").exists());
}
