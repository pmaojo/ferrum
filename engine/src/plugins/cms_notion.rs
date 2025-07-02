use anyhow::Result;

use ferrum_shared_models::FerrumDsl;

use super::utils::{ensure_env_var, ensure_dep};
use super::Plugin;

/// Stub plugin for Notion CMS integration.
pub struct CmsNotionPlugin;

impl Plugin for CmsNotionPlugin {
    fn name(&self) -> &'static str {
        "cms-notion"
    }

    fn on_init(&self) -> Result<()> {
        ensure_env()?;
        ensure_dependencies()
    }

    fn on_compile(&self) -> Result<()> {
        ensure_env()?;
        ensure_dependencies()
    }

    fn extend_dsl(&self, dsl: &mut FerrumDsl) -> Result<()> {
        if !dsl.app.features.contains(&"cms-notion".to_string()) {
            dsl.app.features.push("cms-notion".to_string());
        }
        if !dsl.resources.iter().any(|r| r.name == "NotionClient") {
            use std::collections::BTreeMap;
            dsl.resources.push(ferrum_shared_models::DslResource {
                name: "NotionClient".to_string(),
                resource_type: "cms-notion".to_string(),
                config: BTreeMap::new(),
            });
        }
        Ok(())
    }
}

fn ensure_env() -> Result<()> {
    ensure_env_var("NOTION_API_TOKEN", "")
}

fn ensure_dependencies() -> Result<()> {
    ensure_dep("notion-sdk", "0.1")
}
