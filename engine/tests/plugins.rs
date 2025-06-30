use ferrum_engine::plugins::RealtimeSsePlugin;
use ferrum_engine::plugins::{
    AuthPlugin, CmsNotionPlugin, CmsSanityPlugin, CronPlugin, GraphQLPlugin, PluginManager, StripePlugin,
};
use ferrum_shared_models::FerrumDsl;

#[test]
fn cron_plugin_extends_dsl() {
    let yaml = "app:\n  name: demo\n";
    let mut dsl: FerrumDsl = serde_yaml::from_str(yaml).unwrap();
    let mut manager = PluginManager::new();
    manager.register(CronPlugin);
    manager.extend_dsl_all(&mut dsl).unwrap();
    assert!(dsl.app.features.contains(&"cron".to_string()));
    assert!(dsl.jobs.iter().any(|j| j.name == "example_job"));
}

#[test]
fn stripe_plugin_extends_dsl() {
    let yaml = "app:\n  name: demo\n";
    let mut dsl: FerrumDsl = serde_yaml::from_str(yaml).unwrap();
    let mut manager = PluginManager::new();
    manager.register(StripePlugin);
    manager.extend_dsl_all(&mut dsl).unwrap();
    assert!(dsl.app.features.contains(&"stripe".to_string()));
    assert!(dsl.resources.iter().any(|r| r.name == "StripeClient"));
    assert!(dsl.routes.iter().any(|r| r.name == "stripeWebhook"));
}

#[test]
fn cms_sanity_plugin_extends_dsl() {
    let yaml = "app:\n  name: demo\n";
    let mut dsl: FerrumDsl = serde_yaml::from_str(yaml).unwrap();
    let mut manager = PluginManager::new();
    manager.register(CmsSanityPlugin);
    manager.extend_dsl_all(&mut dsl).unwrap();
    assert!(dsl.app.features.contains(&"cms-sanity".to_string()));
    assert!(dsl.resources.iter().any(|r| r.name == "SanityClient"));
}

#[test]
fn cms_notion_plugin_extends_dsl() {
    let yaml = "app:\n  name: demo\n";
    let mut dsl: FerrumDsl = serde_yaml::from_str(yaml).unwrap();
    let mut manager = PluginManager::new();
    manager.register(CmsNotionPlugin);
    manager.extend_dsl_all(&mut dsl).unwrap();
    assert!(dsl.app.features.contains(&"cms-notion".to_string()));
    assert!(dsl.resources.iter().any(|r| r.name == "NotionClient"));
}

#[test]
fn realtime_sse_plugin_extends_dsl() {
    let yaml = "app:\n  name: demo\n";
    let mut dsl: FerrumDsl = serde_yaml::from_str(yaml).unwrap();
    let mut manager = PluginManager::new();
    manager.register(RealtimeSsePlugin);
    manager.extend_dsl_all(&mut dsl).unwrap();
    assert!(dsl.app.features.contains(&"realtime-sse".to_string()));
}

#[test]
fn auth_plugin_extends_dsl() {
    let yaml = "app:\n  name: demo\n";
    let mut dsl: FerrumDsl = serde_yaml::from_str(yaml).unwrap();
    let mut manager = PluginManager::new();
    manager.register(AuthPlugin);
    manager.extend_dsl_all(&mut dsl).unwrap();
    assert!(dsl.app.features.contains(&"auth".to_string()));
    assert!(dsl.app.auth.is_some());
}

#[test]
fn graphql_plugin_extends_dsl() {
    let yaml = "app:\n  name: demo\n";
    let mut dsl: FerrumDsl = serde_yaml::from_str(yaml).unwrap();
    let mut manager = PluginManager::new();
    manager.register(GraphQLPlugin);
    manager.extend_dsl_all(&mut dsl).unwrap();
    assert!(dsl.app.features.contains(&"graphql".to_string()));
}
