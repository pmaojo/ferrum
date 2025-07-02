use anyhow::Result;
use ferrum_engine::plugins::Plugin;
use ferrum_shared_models::FerrumDsl;

/// Basic example plugin used as a starting point.
pub struct TemplatePlugin;

impl Plugin for TemplatePlugin {
    fn name(&self) -> &'static str {
        "template"
    }

    fn extend_dsl(&self, dsl: &mut FerrumDsl) -> Result<()> {
        if !dsl.app.features.contains(&"template".to_string()) {
            dsl.app.features.push("template".to_string());
        }
        Ok(())
    }
}

/// Creates a boxed plugin instance. This symbol is loaded by Ferrum at runtime.
#[no_mangle]
pub extern "C" fn plugin_create() -> Box<dyn Plugin> {
    Box::new(TemplatePlugin)
}
