use ferrum_engine::plugins::{LeptosPlugin, PluginManager};
use ferrum_shared_models::FerrumDsl;
use std::fs;
use tempfile::tempdir;

#[test]
fn leptos_plugin_extends_dsl() {
    let yaml = "app:\n  name: demo\n";
    let mut dsl: FerrumDsl = serde_yaml::from_str(yaml).unwrap();
    let mut manager = PluginManager::new();
    manager.register(LeptosPlugin);
    manager.extend_dsl_all(&mut dsl).unwrap();
    assert!(dsl.app.features.contains(&"leptos".to_string()));
}

#[test]
fn leptos_plugin_copies_templates() {
    let dir = tempdir().unwrap();
    fs::create_dir_all(dir.path().join("templates/frontend_leptos/ssr")).unwrap();
    fs::write(
        dir.path().join("templates/frontend_leptos/ssr/Cargo.toml"),
        "[package]\nname = \"demo\"\n",
    )
    .unwrap();

    let yaml = "app:\n  name: demo\n";
    let mut dsl: FerrumDsl = serde_yaml::from_str(yaml).unwrap();
    let mut manager = PluginManager::new();
    manager.register(LeptosPlugin);

    let cwd = std::env::current_dir().unwrap();
    std::env::set_current_dir(dir.path()).unwrap();
    manager.extend_dsl_all(&mut dsl).unwrap();
    manager.init_all().unwrap();
    std::env::set_current_dir(cwd).unwrap();

    assert!(dir.path().join("frontend_leptos/Cargo.toml").exists());
    assert!(dir
        .path()
        .join("templates/frontend_leptos/component.rs.tera")
        .exists());
}
