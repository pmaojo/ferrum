use anyhow::Result;
pub mod auth;
pub mod auth_oauth;
pub mod auth_password;
pub mod cms_sanity;
pub mod cron;
pub mod graphql;
pub mod realtime_sse;
pub mod stripe;

/// Trait implemented by all Ferrum plugins.
///
/// Plugins can hook into lifecycle events to extend generation
/// or runtime behavior.
pub trait Plugin: Send + Sync {
    /// Name used for logging and identification.
    fn name(&self) -> &'static str;

    /// Called after `ferrum init`.
    fn on_init(&self) -> Result<()> {
        Ok(())
    }

    /// Called after `ferrum compile` finishes.
    fn on_compile(&self) -> Result<()> {
        Ok(())
    }

    /// Allows a plugin to modify the parsed DSL before code generation.
    fn extend_dsl(&self, _dsl: &mut ferrum_shared_models::FerrumDsl) -> Result<()> {
        Ok(())
    }
}

/// Manages the set of loaded plugins and dispatches events.
pub struct PluginManager {
    plugins: Vec<Box<dyn Plugin>>,
}

impl PluginManager {
    /// Create an empty plugin manager.
    pub fn new() -> Self {
        Self {
            plugins: Vec::new(),
        }
    }

    /// Register a new plugin instance.
    pub fn register<P: Plugin + 'static>(&mut self, plugin: P) {
        self.plugins.push(Box::new(plugin));
    }

    /// Trigger the `on_init` hook on all plugins.
    pub fn init_all(&self) -> Result<()> {
        for p in &self.plugins {
            p.on_init()?;
        }
        Ok(())
    }

    /// Trigger the `on_compile` hook on all plugins.
    pub fn compile_all(&self) -> Result<()> {
        for p in &self.plugins {
            p.on_compile()?;
        }
        Ok(())
    }

    /// Allow plugins to mutate the DSL before generation.
    pub fn extend_dsl_all(&self, dsl: &mut ferrum_shared_models::FerrumDsl) -> Result<()> {
        for p in &self.plugins {
            p.extend_dsl(dsl)?;
        }
        Ok(())
    }
}
pub use auth::AuthPlugin;
pub use auth_oauth::AuthOAuthPlugin;
pub use auth_password::AuthPasswordPlugin;
pub use cms_sanity::CmsSanityPlugin;
pub use cron::CronPlugin;
pub use graphql::GraphQLPlugin;
pub use realtime_sse::RealtimeSsePlugin;
pub use stripe::StripePlugin;
