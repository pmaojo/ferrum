use anyhow::Result;
use std::path::Path;
use ferrum_shared_models::FerrumDsl;

pub struct PluginMetadata {
    pub library: String,
}

impl PluginMetadata {
    pub fn from_file(_path: &Path) -> Result<Self> {
        Ok(PluginMetadata {
            library: " ".to_string(),
        })
    }
}

pub struct DynamicPlugin;

impl DynamicPlugin {
    pub fn load(_path: &Path) -> Result<Self> {
        Ok(DynamicPlugin)
    }
}

pub struct GraphQLPlugin;
pub struct AuthPlugin;
pub struct AuthPasswordPlugin;
pub struct AuthOAuthPlugin;
pub struct StripePlugin;
pub struct CronPlugin;
pub struct CmsSanityPlugin;
pub struct CmsNotionPlugin;
pub struct RealtimeSsePlugin;

#[derive(Default)]
pub struct PluginManager;

impl PluginManager {
    pub fn new() -> Self {
        PluginManager
    }

    pub fn register<T>(&mut self, _plugin: T) {
        // TODO: Implement plugin registration
    }

    pub fn compile_all(&self) -> Result<()> {
        Ok(())
    }

    pub fn extend_dsl_all(&self, _dsl: &mut FerrumDsl) -> Result<()> {
        Ok(())
    }

    pub fn init_all(&self) -> Result<()> {
        Ok(())
    }
}
