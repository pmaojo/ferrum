use ferrum_engine::plugins::{CmsSanityPlugin, CronPlugin, PluginManager, StripePlugin};
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
