use anyhow::Result;

use ferrum_shared_models::FerrumDsl;

use super::utils::{copy_dir_if_missing, copy_if_missing};
use super::Plugin;

/// Plugin that scaffolds a basic Leptos frontend crate.
pub struct LeptosPlugin;

impl Plugin for LeptosPlugin {
    fn name(&self) -> &'static str {
        "leptos"
    }

    fn on_init(&self) -> Result<()> {
        ensure_templates()
    }

    fn on_compile(&self) -> Result<()> {
        ensure_templates()
    }

    fn extend_dsl(&self, dsl: &mut FerrumDsl) -> Result<()> {
        if !dsl.app.features.contains(&"leptos".to_string()) {
            dsl.app.features.push("leptos".to_string());
        }
        Ok(())
    }
}

fn ensure_templates() -> Result<()> {
    use std::path::Path;

    let template_dir = Path::new("templates/frontend_leptos/ssr");
    copy_dir_if_missing(template_dir, Path::new("frontend_leptos"))?;
    copy_if_missing(
        include_str!("../../../templates/frontend_leptos/component.rs.tera"),
        "templates/frontend_leptos/component.rs.tera",
    )?;
    copy_if_missing(
        include_str!("../../../templates/frontend_leptos/hook.rs.tera"),
        "templates/frontend_leptos/hook.rs.tera",
    )?;
    copy_if_missing(
        include_str!("../../../templates/frontend_leptos/route.rs.tera"),
        "templates/frontend_leptos/route.rs.tera",
    )?;
    Ok(())
}
