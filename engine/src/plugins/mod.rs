use anyhow::Result;
pub mod graphql;

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
}
pub use graphql::GraphQLPlugin;
